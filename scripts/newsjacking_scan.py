#!/usr/bin/env python3
"""
newsjacking_scan.py — surface fast-moving UK scam news for same-day content.

generate_trending_topics.py finds evergreen rising search terms (Google
Trends, ~90-day window). This script is the reactive counterpart: it polls
Google News RSS (no API key) for UK scam/fraud coverage published in the
last few days, clusters similar headlines, and scores each cluster on
newsworthiness (source count + recency + scam-keyword density) so an
operator can decide whether a fast reactive guide/alert is worth writing.

It NEVER auto-publishes and by default only prints a report. Candidates
that clear --min-score can optionally be appended to the daily-publish
queue (same schema as generate_trending_topics.py) with --append, where
they flow through the normal human-review-gated pipeline like any other
queued topic.

    python3 scripts/newsjacking_scan.py                  # report only
    python3 scripts/newsjacking_scan.py --append          # also queue high scorers
    python3 scripts/newsjacking_scan.py --min-score 3 --days 3

Stdlib only (urllib + xml.etree) — no extra dependency, unlike pytrends.
"""
import argparse
import csv
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
QUEUE_FILE = ROOT / "content" / "daily-publish-queue.csv"
POSTS_FILE = ROOT / "content" / "posts.json"

RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-GB&gl=GB&ceid=GB:en"

# Seed queries — each pulled independently; results are pooled then clustered.
SEED_QUERIES = [
    "scam warning UK",
    "fraud alert UK",
    "text scam UK",
    "bank scam UK",
    "HMRC scam",
    "DVLA scam",
    "impersonation scam UK",
    "Action Fraud OR \"Report Fraud\" warning",
]

USER_AGENT = "Mozilla/5.0 (compatible; BeatTheScamNewsjackingScan/1.0)"

# Duplicated from generate_trending_topics.py rather than imported: that
# module hard-exits at import time if pytrends isn't installed, which this
# stdlib-only script shouldn't require.
CATEGORY_HINTS = {
    "email": ["email", "phishing", "gmail", "outlook"],
    "sms": ["text", "sms", "message", "whatsapp"],
    "phone": ["call", "phone", "ring", "vishing", "telephone"],
    "payment": ["bank transfer", "bacs", "faster payment", "monzo", "revolut", "wise", "starling"],
    "crypto": ["bitcoin", "crypto", "nft", "ethereum", "binance", "coinbase", "blockchain"],
    "government": ["hmrc", "dvla", "nhs", "dwp", "gov.uk", "council", "passport", "visa"],
    "employment": ["job", "work", "recruitment", "cv", "salary", "remote work", "employer"],
    "shopping": ["ticket", "shop", "buy", "order", "delivery", "parcel"],
    "marketplace": ["facebook marketplace", "ebay", "gumtree", "vinted", "depop", "autotrader"],
    "dating": ["romance", "dating", "tinder", "bumble", "hinge", "relationship"],
    "social": ["instagram", "facebook", "tiktok", "twitter", "linkedin", "snapchat", "youtube"],
    "travel": ["holiday", "flight", "hotel", "booking", "airbnb", "visa", "travel"],
    "finance": ["investment", "pension", "isa", "trading", "forex", "bond", "shares", "stock"],
    "tech": ["tech support", "microsoft", "apple", "windows", "mac", "remote access", "qr"],
    "website": ["website", "fake site", "lookalike", "clone site", "domain"],
    "fraud": ["identity", "impersonation", "fraud", "fake", "counterfeit"],
    "utility": ["energy", "electric", "gas", "water", "broadband", "boiler", "solar"],
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower().strip()).strip("-")


def guess_category(keyword: str) -> str:
    kw = keyword.lower()
    for category, hints in CATEGORY_HINTS.items():
        if any(hint in kw for hint in hints):
            return category
    return "fraud"

# Words too generic to anchor a cluster on (kept lowercase).
STOPWORDS = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "is", "are",
    "uk", "scam", "scams", "fraud", "warning", "warns", "warning:", "alert",
    "new", "how", "what", "after", "over", "as", "with", "from", "you",
    "your", "this", "that", "it", "be", "has", "have", "up", "out", "by",
}


def fetch_rss(query: str) -> list[dict]:
    url = RSS_URL.format(query=urllib.request.quote(query))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  Warning: fetch failed for '{query}': {e}", file=sys.stderr)
        return []
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as e:
        print(f"  Warning: parse failed for '{query}': {e}", file=sys.stderr)
        return []

    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        if not title:
            continue
        items.append({"title": title, "pub_date": pub_date, "source": source, "seed": query})
    return items


def parse_pubdate(raw: str):
    try:
        return datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def cluster_key(title: str) -> str:
    """Collapse near-duplicate headlines onto a shared key: the most
    distinctive shared word (e.g. an entity name) plus a scam/fraud stem,
    so 'Halifax warns of new text scam' and 'New Halifax scam targets
    customers' land in the same cluster."""
    words = re.findall(r"[a-z][a-z'-]{2,}", title.lower())
    significant = [w for w in words if w not in STOPWORDS]
    return significant[0] if significant else title.lower()[:30]


def load_existing_slugs() -> set:
    slugs = set()
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE, newline="", encoding="utf-8") as f:
            slugs |= {row["slug"] for row in csv.DictReader(f) if row.get("slug")}
    if POSTS_FILE.exists():
        import json
        posts = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
        slugs |= {p.get("slug", "") for p in posts}
    return slugs


def score_cluster(items: list[dict], now: datetime) -> dict:
    sources = {i["source"] for i in items if i["source"]}
    dates = [d for d in (parse_pubdate(i["pub_date"]) for i in items) if d]
    most_recent = max(dates) if dates else None
    age_hours = (now - most_recent).total_seconds() / 3600 if most_recent else 999

    # Newsworthiness rubric: distinct outlets matter more than raw item
    # count (avoids one syndicated wire story scoring high); very recent
    # coverage is weighted up; a single unnamed source scores low.
    score = len(sources) * 2
    if age_hours <= 24:
        score += 3
    elif age_hours <= 72:
        score += 1
    if len(items) >= 4:
        score += 1

    return {
        "headline": items[0]["title"],
        "item_count": len(items),
        "source_count": len(sources),
        "sources": sorted(sources),
        "age_hours": round(age_hours) if most_recent else None,
        "score": score,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan Google News RSS for fast-moving UK scam stories")
    ap.add_argument("--days", type=int, default=5, help="ignore items older than this many days")
    ap.add_argument("--min-score", type=int, default=4, help="minimum score to report/queue")
    ap.add_argument("--append", action="store_true",
                    help="append candidates above --min-score to daily-publish-queue.csv")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.days)

    print("Fetching Google News RSS for UK scam/fraud coverage...")
    pooled = []
    for seed in SEED_QUERIES:
        items = fetch_rss(seed)
        print(f"  '{seed}': {len(items)} items")
        pooled.extend(items)

    clusters = defaultdict(list)
    for item in pooled:
        d = parse_pubdate(item["pub_date"])
        if d and d < cutoff:
            continue
        clusters[cluster_key(item["title"])].append(item)

    scored = [score_cluster(v, now) for v in clusters.values()]
    scored.sort(key=lambda r: r["score"], reverse=True)

    existing_slugs = load_existing_slugs()
    candidates = [
        r for r in scored
        if r["score"] >= args.min_score and slugify(r["headline"]) not in existing_slugs
    ]

    print(f"\n{len(scored)} clusters from {len(pooled)} raw items. "
          f"{len(candidates)} score >= {args.min_score} and aren't already queued/published.\n")

    for r in candidates[:args.top]:
        age = f"{r['age_hours']}h ago" if r["age_hours"] is not None else "undated"
        print(f"[score {r['score']}] {r['headline']}")
        print(f"    {r['item_count']} items, {r['source_count']} sources ({', '.join(r['sources'][:4])}), {age}")

    if not args.append:
        if candidates:
            print("\nRun with --append to queue these for the human-review-gated publish pipeline.")
        return 0

    new_rows = []
    for r in candidates[:args.top]:
        keyword = r["headline"]
        if "uk" not in keyword.lower():
            keyword += " UK"
        slug = slugify(keyword)
        if slug in existing_slugs:
            continue
        new_rows.append({
            "keyword": keyword,
            "entity": "Unknown",
            "category": guess_category(keyword),
            "published": "",
            "published_at": "",
            "slug": slug,
        })
        existing_slugs.add(slug)

    if not new_rows:
        print("\nNothing new to queue.")
        return 0

    fieldnames = ["keyword", "entity", "category", "published", "published_at", "slug"]
    write_header = not QUEUE_FILE.exists()
    with open(QUEUE_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"\nAppended {len(new_rows)} newsjacking candidates to {QUEUE_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
