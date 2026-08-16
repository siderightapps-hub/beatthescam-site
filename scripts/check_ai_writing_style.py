#!/usr/bin/env python3
"""
check_ai_writing_style.py — flag LLM prose tells across the published corpus.

The content gate (content_gate.py) checks factual accuracy, not writing style.
Nothing else in the pipeline catches the stock LLM cliches that make guides
read as machine-written: overused verbs/transitions ("delve", "leverage",
"robust", "furthermore"), stock AI opener/closer phrasing, and em-dash
overuse. This is a deterministic, stdlib-only heuristic scan for a human
editorial pass — it does not block publication and writes nothing.

    python3 scripts/check_ai_writing_style.py                # whole corpus
    python3 scripts/check_ai_writing_style.py --slug foo-bar # one guide
    python3 scripts/check_ai_writing_style.py --top 10       # worst N only

Scores are relative flags, not a verdict — a single "delve" in a 900-word
guide is not a problem; a guide flagged high should get a human read.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Verbs/adjectives/connectors that show up disproportionately in LLM output
# relative to human-written UK consumer content (adapted from published
# AI-writing-detection wordlists, e.g. Grammarly/Microsoft style guidance).
OVERUSED_WORDS = [
    "delve", "delving", "leverage", "leveraging", "robust", "seamless",
    "seamlessly", "furthermore", "moreover", "underscore", "underscores",
    "underscoring", "boast", "boasts", "boasting", "navigate", "navigating",
    "landscape", "tapestry", "realm", "testament", "pivotal", "paramount",
    "multifaceted", "holistic", "synergy", "unleash", "unlock", "unlocking",
    "elevate", "elevating", "game-changer", "game changer", "cutting-edge",
    "in today's world", "in today's digital age", "it is important to note",
    "it's important to note", "it is worth noting", "when it comes to",
    "in the realm of", "in the world of", "at the end of the day",
]

# Stock AI opener/closer phrasing (checked against the first/last sentence
# of each section body).
CLICHE_OPENERS = [
    r"^in an? (increasingly )?\w+ world",
    r"^in today'?s (fast-paced|digital|modern)",
    r"^as \w+ continues? to evolve",
    r"^with the rise of",
]
CLICHE_CLOSERS = [
    r"in conclusion,?",
    r"to sum up,?",
    r"ultimately,? (it'?s|it is|staying|remember)",
    r"by staying (informed|vigilant|aware)",
]


def guide_text(post: dict) -> list[str]:
    """Return every body paragraph as separate strings (sections + faq)."""
    chunks = []
    for sec in post.get("sections", []):
        if isinstance(sec, list) and len(sec) == 2:
            chunks.append(sec[1])
    for qa in post.get("faq", []):
        if isinstance(qa, list) and len(qa) == 2:
            chunks.append(qa[1])
    return [c for c in chunks if isinstance(c, str) and c.strip()]


def score_guide(post: dict) -> dict:
    chunks = guide_text(post)
    full_text = "\n".join(chunks)
    lower = full_text.lower()
    word_count = len(full_text.split())

    word_hits = {}
    for w in OVERUSED_WORDS:
        n = lower.count(w)
        if n:
            word_hits[w] = n
    word_total = sum(word_hits.values())

    em_dash_count = full_text.count("—") + full_text.count("--")

    opener_hits = closer_hits = 0
    for chunk in chunks:
        sentences = re.split(r"(?<=[.!?])\s+", chunk.strip())
        if not sentences:
            continue
        first, last = sentences[0].lower(), sentences[-1].lower()
        if any(re.search(p, first) for p in CLICHE_OPENERS):
            opener_hits += 1
        if any(re.search(p, last) for p in CLICHE_CLOSERS):
            closer_hits += 1

    # Rate per 1,000 words so long/short guides are comparable.
    denom = max(word_count, 1) / 1000
    rate = (word_total + em_dash_count + opener_hits + closer_hits) / denom

    return {
        "slug": post.get("slug", "unknown"),
        "word_count": word_count,
        "cliche_words": word_hits,
        "cliche_word_total": word_total,
        "em_dash_count": em_dash_count,
        "cliche_openers": opener_hits,
        "cliche_closers": closer_hits,
        "rate_per_1000_words": round(rate, 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Heuristic scan for LLM prose tells")
    ap.add_argument("--posts", default="content/posts.json")
    ap.add_argument("--slug", help="scan a single guide by slug")
    ap.add_argument("--top", type=int, default=20, help="show the N worst-scoring guides")
    ap.add_argument("--min-words", type=int, default=150,
                    help="skip guides shorter than this (score is noisy on stubs)")
    args = ap.parse_args()

    posts_path = ROOT / args.posts if not Path(args.posts).is_absolute() else Path(args.posts)
    posts = json.loads(posts_path.read_text(encoding="utf-8"))

    if args.slug:
        posts = [p for p in posts if p.get("slug") == args.slug]
        if not posts:
            print(f"No guide with slug '{args.slug}'")
            return 1

    results = [
        score_guide(p) for p in posts
        if not p.get("consolidated_into") and len(" ".join(guide_text(p)).split()) >= args.min_words
    ]
    results.sort(key=lambda r: r["rate_per_1000_words"], reverse=True)

    shown = results if args.slug else results[:args.top]
    for r in shown:
        print(f"{r['slug']}  rate={r['rate_per_1000_words']}/1k words  "
              f"words={r['word_count']}  cliches={r['cliche_word_total']}  "
              f"em-dash={r['em_dash_count']}  opener={r['cliche_openers']}  closer={r['cliche_closers']}")
        if r["cliche_words"]:
            top_words = sorted(r["cliche_words"].items(), key=lambda kv: kv[1], reverse=True)[:6]
            print(f"    top terms: {', '.join(f'{w}x{n}' for w, n in top_words)}")

    if results:
        avg = sum(r["rate_per_1000_words"] for r in results) / len(results)
        print(f"\nScanned {len(results)} guides. Corpus average rate: {round(avg, 2)}/1k words.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
