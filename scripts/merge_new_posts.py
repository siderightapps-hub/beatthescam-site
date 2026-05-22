#!/usr/bin/env python3
"""Merge new post entries from a saved snapshot into the current posts.json.

Used by CI to recover from rebase conflicts caused by concurrent pipeline runs
(daily-publish + daily-search-console both touching dist/sitemap.xml and
posts.json). The recovery path is:

  1. cp content/posts.json /tmp/posts-ours.json     (snapshot our work)
  2. git reset --hard origin/main                   (drop our broken commit)
  3. python scripts/merge_new_posts.py /tmp/posts-ours.json content/posts.json
  4. python scripts/build.py                        (regenerate dist/ cleanly)
  5. commit + push

The merge takes all entries from `base` (origin/main — most recent, canonical)
plus any entries from `ours` whose `slug` is not already in `base`. Order:
base entries first, our additions appended.

Exits 0 always; prints a one-line summary. If nothing needs merging, the file
on disk is untouched.
"""
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: merge_new_posts.py <ours.json> <base.json>", file=sys.stderr)
        return 2

    ours_path = Path(sys.argv[1])
    base_path = Path(sys.argv[2])

    with ours_path.open() as f:
        ours = json.load(f)
    with base_path.open() as f:
        base = json.load(f)

    if not isinstance(ours, list) or not isinstance(base, list):
        print("ERROR: both files must contain a JSON list", file=sys.stderr)
        return 2

    base_slugs = {
        p.get("slug") for p in base
        if isinstance(p, dict) and p.get("slug")
    }
    additions = [
        p for p in ours
        if isinstance(p, dict) and p.get("slug") and p["slug"] not in base_slugs
    ]

    if not additions:
        print("merge_new_posts: nothing to merge (no slugs in ours that aren't in base)")
        return 0

    merged = base + additions
    with base_path.open("w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
        f.write("\n")

    slugs = [p["slug"] for p in additions]
    print(f"merge_new_posts: added {len(additions)} entry/entries: {slugs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
