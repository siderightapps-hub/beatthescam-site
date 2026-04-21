"""
rewrite_thin_guides.py
Rewrites existing thin guides (under a word count threshold) using Claude.
Run once to bring all short guides up to quality standard.

Usage:
  ANTHROPIC_API_KEY=your_key python3 scripts/rewrite_thin_guides.py \
    --posts content/posts.json \
    --threshold 400 \
    --limit 20
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

# Reuse generation logic from generate_content_claude
sys.path.insert(0, str(Path(__file__).parent))
from generate_content_claude import (
    Topic, claude_post, load_posts, save_posts, slugify
)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def section_word_count(post: dict) -> int:
    return sum(len((t + " " + b).split()) for t, b in post.get("sections", []))


def main() -> int:
    parser = argparse.ArgumentParser(description="Rewrite thin guides using Claude")
    parser.add_argument("--posts",     required=True, help="Path to posts.json")
    parser.add_argument("--threshold", type=int, default=400,
                        help="Rewrite guides with fewer words than this (default: 400)")
    parser.add_argument("--limit",     type=int, default=20,
                        help="Max guides to rewrite in one run (default: 20)")
    parser.add_argument("--model",     default=DEFAULT_MODEL)
    parser.add_argument("--dry-run",   action="store_true",
                        help="List guides that would be rewritten without doing it")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 1

    posts     = load_posts(args.posts)
    all_slugs = [p["slug"] for p in posts]

    # Find thin guides, sorted by word count ascending
    thin = sorted(
        [p for p in posts if section_word_count(p) < args.threshold],
        key=section_word_count
    )[:args.limit]

    if not thin:
        print(f"No guides under {args.threshold} words. Nothing to rewrite.")
        return 0

    print(f"Found {len(thin)} guides under {args.threshold} words (limit: {args.limit}):\n")
    for p in thin:
        wc = section_word_count(p)
        print(f"  {wc:4d}w  {p['slug']}")

    if args.dry_run:
        print("\n[dry-run] No changes made.")
        return 0

    print()

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    today  = date.today().isoformat()

    rewritten = 0
    for post in thin:
        slug = post["slug"]
        print(f"  rewrite  {slug} …", end=" ", flush=True)
        try:
            topic = Topic(
                keyword=post.get("keywords", [slug.replace("-", " ")])[0],
                entity=_guess_entity(post),
                category=post.get("category", "website"),
            )
            new_post = claude_post(topic, today, args.model, client, all_slugs)
            # Preserve the original slug so URLs don't change
            new_post["slug"] = slug

            # Replace in posts list
            posts = [p for p in posts if p["slug"] != slug]
            posts.append(new_post)
            all_slugs = [p["slug"] for p in posts]

            wc = section_word_count(new_post)
            print(f"ok ({wc}w)")
            rewritten += 1
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)

    save_posts(args.posts, posts)
    print(f"\nDone: rewrote {rewritten}/{len(thin)} guides in {args.posts}")
    return 0


def _guess_entity(post: dict) -> str:
    """Extract likely entity name from post title or keywords."""
    title    = post.get("title", "")
    keywords = post.get("keywords", [])
    # Try to find a proper noun in the title (capitalised word)
    import re
    caps = re.findall(r'\b([A-Z][a-z]{2,})\b', title)
    # Exclude common words
    skip = {"How", "What", "When", "Where", "Why", "The", "This", "That",
            "Spot", "Avoid", "Stay", "Safe", "Guide", "Warning", "Signs",
            "UK", "Scam", "Scams", "Check", "Beat"}
    for word in caps:
        if word not in skip:
            return word
    # Fall back to first keyword
    if keywords:
        return str(keywords[0]).title()
    return title[:30]


if __name__ == "__main__":
    raise SystemExit(main())
