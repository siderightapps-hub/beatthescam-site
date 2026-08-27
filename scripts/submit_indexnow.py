#!/usr/bin/env python3
"""Submit added, changed, and removed public URLs through IndexNow.

The build already publishes the stable verification key. This script computes
the URL delta between a Git ref and the current checkout, then sends one batch
to the shared IndexNow endpoint. It has no third-party dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
HOST = "beatthescam.com"
ORIGIN = f"https://{HOST}"
KEY = "b3c8e1f2a94d7056"
KEY_LOCATION = f"{ORIGIN}/{KEY}.txt"
DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow"


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def posts_at(ref: str | None) -> dict[str, dict]:
    if ref:
        result = git("show", f"{ref}:content/posts.json")
        if result.returncode != 0:
            return {}
        raw = result.stdout
    else:
        raw = (ROOT / "content" / "posts.json").read_text(encoding="utf-8")
    try:
        return {p["slug"]: p for p in json.loads(raw) if p.get("slug")}
    except (json.JSONDecodeError, TypeError, KeyError):
        return {}


def public_signature(post: dict) -> str:
    """Ignore bookkeeping fields that cannot change the rendered guide."""
    omitted = {"manifest", "review_notes"}
    return json.dumps(
        {k: v for k, v in post.items() if k not in omitted},
        sort_keys=True,
        ensure_ascii=False,
    )


def html_path_to_url(path: str) -> str | None:
    if not path.startswith("dist/") or not path.endswith(".html"):
        return None
    relative = path.removeprefix("dist/")
    if relative == "index.html":
        return ORIGIN + "/"
    if relative == "404.html":
        return None
    if relative.endswith("/index.html"):
        return ORIGIN + "/" + relative.removesuffix("index.html")
    return ORIGIN + "/" + relative


def changed_urls(before: str) -> list[str]:
    urls: set[str] = set()
    old_posts = posts_at(before)
    new_posts = posts_at(None)
    for slug in sorted(set(old_posts) | set(new_posts)):
        old = old_posts.get(slug)
        new = new_posts.get(slug)
        if old is None or new is None or public_signature(old) != public_signature(new):
            urls.add(f"{ORIGIN}/guides/{slug}/")

    result = git("diff", "--name-status", before, "HEAD", "--", "dist")
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            columns = line.split("\t")
            if len(columns) < 2:
                continue
            status, path = columns[0], columns[-1]
            url = html_path_to_url(path)
            if not url:
                continue
            # Deleted URLs must be submitted so engines discover the redirect
            # or removal. Existing noindex pages are intentionally omitted.
            local = ROOT / path
            if not status.startswith("D") and local.exists():
                text = local.read_text(encoding="utf-8", errors="replace")
                if re.search(r'<meta[^>]+name="robots"[^>]+content="noindex', text, re.I):
                    continue
            urls.add(url)

    return sorted(urls)


def all_sitemap_urls() -> list[str]:
    text = (ROOT / "dist" / "sitemap.xml").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"<loc>(https://beatthescam\.com/[^<]*)</loc>", text)))


def submit(urls: list[str], endpoint: str, attempts: int = 3) -> None:
    if len(urls) > 10_000:
        raise ValueError("IndexNow accepts at most 10,000 URLs per request")
    payload = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "BeatTheScam-IndexNow/1.0"},
        method="POST",
    )
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=30) as response:
                if response.status not in (200, 202):
                    raise RuntimeError(f"unexpected IndexNow status {response.status}")
                print(f"IndexNow accepted {len(urls)} URL(s) with HTTP {response.status}")
                return
        except HTTPError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt == attempts:
                raise RuntimeError(f"IndexNow returned HTTP {exc.code}") from exc
        except URLError as exc:
            if attempt == attempts:
                raise RuntimeError(f"IndexNow request failed: {exc.reason}") from exc
        time.sleep(5 * attempt)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", help="Git ref immediately before the deployed change")
    parser.add_argument("--all", action="store_true", help="Submit every current sitemap URL")
    parser.add_argument("--dry-run", action="store_true", help="Print URLs without notifying IndexNow")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args()

    if args.all:
        urls = all_sitemap_urls()
    elif args.before:
        # GitHub sends the all-zero SHA for "before" on a push that creates a
        # branch (no prior commit exists) — not an error, just nothing to diff.
        if set(args.before) <= {"0"}:
            print("No prior commit (branch creation) — nothing to diff, skipping")
            return 0
        if git("cat-file", "-e", f"{args.before}^{{commit}}").returncode != 0:
            # A genuinely unreachable ref (rewritten history, force-push) — degrade to
            # notifying nothing rather than failing the whole job silently on every
            # push until someone happens to check the Actions tab (found 2026-08-27).
            print(f"Before-ref is unavailable: {args.before} — skipping this delta", file=sys.stderr)
            return 0
        urls = changed_urls(args.before)
    else:
        parser.error("provide --before or --all")

    if not urls:
        print("No public URL changes to submit")
        return 0
    if args.dry_run:
        print("\n".join(urls))
        print(f"Dry run: {len(urls)} URL(s)")
        return 0
    submit(urls, args.endpoint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
