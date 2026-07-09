import argparse
import csv
import datetime as dt
import subprocess
import sys
from pathlib import Path

REQUIRED_COLUMNS = ["keyword", "entity", "category", "published", "published_at", "slug"]


def load_queue(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    for col in REQUIRED_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)
    normalized = []
    for row in rows:
        out = {k: row.get(k, "") for k in fieldnames}
        normalized.append(out)
    return normalized, fieldnames


def save_queue(path: Path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_topics(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword", "entity", "category"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "keyword": row["keyword"],
                "entity": row["entity"],
                "category": row["category"],
            })


def slugify(text: str) -> str:
    import re
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def parse_marker(text: str, key: str) -> list:
    """Read the `KEY=a,b,c` line the generator prints (last one wins)."""
    vals: list = []
    for line in text.splitlines():
        if line.startswith(key + "="):
            payload = line[len(key) + 1:].strip()
            vals = [s for s in payload.split(",") if s]
    return vals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--topics", required=True)
    parser.add_argument("--posts", required=True)
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    args = parser.parse_args()

    queue_path = Path(args.queue)
    topics_path = Path(args.topics)
    posts_path = Path(args.posts)

    rows, fieldnames = load_queue(queue_path)
    pending = [r for r in rows if str(r.get("published", "")).strip().lower() not in {"true", "yes", "1", "quarantined", "skipped"}]
    batch = pending[: max(args.batch_size, 0)]

    if not batch:
        print("No pending topics found")
        return 0

    write_topics(topics_path, batch)

    cmd = [
        sys.executable,
        "scripts/generate_content_claude.py",
        str(topics_path),
        "--posts",
        str(posts_path),
        "--mode",
        "claude",
        "--model",
        args.model,
        "--date",
        dt.date.today().isoformat(),
    ]
    # Capture the generator's stdout so we can see which posts actually passed
    # the accuracy gate. Only gate-PASSED posts are marked published + tweeted;
    # quarantined posts are set aside for review (not retried, not broadcast).
    try:
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        # Echo the captured output before re-raising — otherwise a generator
        # crash leaves the CI log with a bare traceback and no gate/quarantine
        # context to diagnose from.
        if e.stdout:
            sys.stdout.write(e.stdout)
        if e.stderr:
            sys.stderr.write(e.stderr)
        raise
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)

    # post slugs (real URLs) → tweeting; topic slugs → marking the right queue rows
    # (the model's chosen slug can differ from slugify(keyword)).
    published_slugs = parse_marker(proc.stdout, "GATE_PUBLISHED")
    published_topics = set(parse_marker(proc.stdout, "GATE_PUBLISHED_TOPICS"))
    quarantined_topics = set(parse_marker(proc.stdout, "GATE_QUARANTINED_TOPICS"))
    skipped_topics = set(parse_marker(proc.stdout, "GATE_SKIPPED_TOPICS"))

    published_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    batch_keywords = {row["keyword"] for row in batch}
    for row in rows:
        if row["keyword"] not in batch_keywords:
            continue
        if str(row.get("published", "")).strip().lower() in {"true", "yes", "1", "quarantined", "skipped"}:
            continue
        rslug = slugify(row["keyword"])
        if rslug in published_topics:
            row["published"], row["published_at"], row["slug"] = "true", published_at, rslug
        elif rslug in quarantined_topics:
            # Gate-failed: set aside for manual review. Excluded from pending so
            # it is not auto-retried, and it is never tweeted.
            row["published"], row["published_at"], row["slug"] = "quarantined", published_at, rslug
        elif rslug in skipped_topics:
            # A guide with this slug already exists (e.g. a duplicate queue entry,
            # or it predates the queue system). Resolved — not retried, not tweeted —
            # but distinct from "quarantined" since nothing was gate-failed.
            row["published"], row["published_at"], row["slug"] = "skipped", published_at, rslug
        # else: generation errored (produced no post) — leave pending to retry.

    save_queue(queue_path, rows, fieldnames)
    print(f"Published {len(published_topics)} topic(s); quarantined {len(quarantined_topics)} for review; "
          f"skipped {len(skipped_topics)} (already exists)")

    # Only gate-PASSED slugs are emitted for tweeting (daily-publish.yml greps
    # `^NEW_ARTICLE_SLUGS=`). Quarantined content is never broadcast.
    if published_slugs:
        print(f"NEW_ARTICLE_SLUGS={','.join(published_slugs)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
