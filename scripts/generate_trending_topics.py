#!/usr/bin/env python3
"""
generate_trending_topics.py

Pulls rising scam-related queries from Google Trends (UK) and appends
any new topics to content/daily-publish-queue.csv.

Usage:
    pip install pytrends --break-system-packages
    python3 scripts/generate_trending_topics.py

Run manually whenever you want to refresh the queue with trending topics,
or add to a weekly GitHub Actions cron job.
"""

import csv
import re
import time
import random
import sys
from pathlib import Path

try:
    from pytrends.request import TrendReq
except ImportError:
    print("pytrends not installed. Run: pip install pytrends --break-system-packages")
    sys.exit(1)

# ─── CONFIG ──────────────────────────────────────────────────────────────────

ROOT       = Path(__file__).parent.parent
QUEUE_FILE = ROOT / "content" / "daily-publish-queue.csv"

# Category mapping — if any of these words appear in a trending term,
# assign it to the corresponding category
CATEGORY_HINTS = {
    "email":      ["email", "phishing", "gmail", "outlook"],
    "sms":        ["text", "sms", "message", "whatsapp"],
    "phone":      ["call", "phone", "ring", "vishing", "telephone"],
    "payment":    ["bank transfer", "bacs", "faster payment", "monzo", "revolut", "wise", "starling"],
    "crypto":     ["bitcoin", "crypto", "nft", "ethereum", "binance", "coinbase", "blockchain"],
    "government": ["hmrc", "dvla", "nhs", "dwp", "gov.uk", "council", "passport", "visa"],
    "employment": ["job", "work", "recruitment", "cv", "salary", "remote work", "employer"],
    "shopping":   ["ticket", "shop", "buy", "order", "delivery", "parcel"],
    "marketplace":["facebook marketplace", "ebay", "gumtree", "vinted", "depop", "autotrader"],
    "dating":     ["romance", "dating", "tinder", "bumble", "hinge", "relationship"],
    "social":     ["instagram", "facebook", "tiktok", "twitter", "linkedin", "snapchat", "youtube"],
    "travel":     ["holiday", "flight", "hotel", "booking", "airbnb", "visa", "travel"],
    "finance":    ["investment", "pension", "isa", "trading", "forex", "bond", "shares", "stock"],
    "tech":       ["tech support", "microsoft", "apple", "windows", "mac", "remote access", "qr"],
    "website":    ["website", "fake site", "lookalike", "clone site", "domain"],
    "fraud":      ["identity", "impersonation", "fraud", "fake", "counterfeit"],
    "utility":    ["energy", "electric", "gas", "water", "broadband", "boiler", "solar"],
}

# Seed queries — Trends will find related rising queries for each
SEED_QUERIES = [
    "scam uk",
    "fraud uk",
    "phishing uk",
    "fake text uk",
    "bank scam uk",
]

# How many rising queries to pull per seed
RESULTS_PER_SEED = 20

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower().strip()).strip("-")


def guess_category(keyword: str) -> str:
    kw = keyword.lower()
    for category, hints in CATEGORY_HINTS.items():
        if any(hint in kw for hint in hints):
            return category
    return "fraud"  # default


def load_existing_slugs() -> set:
    if not QUEUE_FILE.exists():
        return set()
    with open(QUEUE_FILE, newline="", encoding="utf-8") as f:
        return {row["slug"] for row in csv.DictReader(f) if row.get("slug")}


def is_scam_related(term: str) -> bool:
    """Filter — only keep terms that look like scam/fraud queries."""
    scam_words = [
        "scam", "fraud", "fake", "phishing", "smishing", "vishing",
        "impersonat", "hoax", "spam", "suspicious", "warning", "alert",
        "dodgy", "con ", " con", "rip off", "rogue"
    ]
    term_lower = term.lower()
    return any(w in term_lower for w in scam_words)


def fetch_rising_queries(pytrends, seed: str) -> list[str]:
    """Return rising related queries for a seed term (UK, past 90 days)."""
    try:
        pytrends.build_payload(
            [seed],
            cat=0,
            timeframe="today 3-m",
            geo="GB",
            gprop=""
        )
        related = pytrends.related_queries()
        rising = related.get(seed, {}).get("rising")
        if rising is None or rising.empty:
            return []
        return rising["query"].tolist()[:RESULTS_PER_SEED]
    except Exception as e:
        print(f"  Warning: failed to fetch trends for '{seed}': {e}")
        return []


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("Connecting to Google Trends (UK)...")
    pytrends = TrendReq(hl="en-GB", tz=0, timeout=(10, 25), retries=2, backoff_factor=0.5)

    existing_slugs = load_existing_slugs()
    print(f"Existing queue slugs: {len(existing_slugs)}")

    candidates = []
    for seed in SEED_QUERIES:
        print(f"Fetching rising queries for: '{seed}'")
        queries = fetch_rising_queries(pytrends, seed)
        print(f"  Got {len(queries)} results")
        for q in queries:
            if is_scam_related(q):
                candidates.append(q)
        # Polite delay to avoid rate limiting
        time.sleep(random.uniform(2.5, 4.5))

    # Deduplicate candidates
    seen = set()
    unique_candidates = []
    for c in candidates:
        key = slugify(c)
        if key not in seen and key not in existing_slugs:
            seen.add(key)
            unique_candidates.append(c)

    print(f"\nNew scam-related trending topics found: {len(unique_candidates)}")
    if not unique_candidates:
        print("No new topics to add.")
        return

    # Build new rows
    new_rows = []
    for keyword in unique_candidates:
        # Append "UK" if not already present
        if "uk" not in keyword.lower():
            keyword = keyword.strip() + " UK"
        slug = slugify(keyword)
        if slug in existing_slugs:
            continue
        category = guess_category(keyword)
        new_rows.append({
            "keyword":      keyword,
            "entity":       "Unknown",
            "category":     category,
            "published":    "",
            "published_at": "",
            "slug":         slug,
        })
        existing_slugs.add(slug)
        print(f"  + [{category}] {keyword}")

    if not new_rows:
        print("All trending topics already in queue.")
        return

    # Append to CSV
    fieldnames = ["keyword", "entity", "category", "published", "published_at", "slug"]
    write_header = not QUEUE_FILE.exists()
    with open(QUEUE_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    print(f"\nAdded {len(new_rows)} new topics to {QUEUE_FILE}")
    print("Run 'python3 scripts/build.py' then push to deploy.")


if __name__ == "__main__":
    main()
