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
    pending = [r for r in rows if str(r.get("published", "")).strip().lower() not in {"true", "yes", "1"}]
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
    subprocess.run(cmd, check=True)

    published_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    batch_keywords = {row["keyword"] for row in batch}
    for row in rows:
        if row["keyword"] in batch_keywords and str(row.get("published", "")).strip().lower() not in {"true", "yes", "1"}:
            row["published"] = "true"
            row["published_at"] = published_at
            row["slug"] = slugify(row["keyword"])

    save_queue(queue_path, rows, fieldnames)
    print(f"Published {len(batch)} topic(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
