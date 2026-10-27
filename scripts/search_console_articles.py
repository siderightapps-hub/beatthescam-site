#!/usr/bin/env python3
"""
Beat The Scam — Search Console Article Generator
=================================================
Pulls trending queries from Google Search Console, finds gaps in existing
content, generates a new article using Claude API, and adds it to posts.json.

Runs daily via GitHub Actions at 07:30 UK time.
Also works locally: python3 scripts/search_console_articles.py [--dry-run]

Credentials:
  Local:  token.json + client_secret*.json in repo root
  CI:     GOOGLE_SEARCH_CONSOLE_TOKEN + GOOGLE_OAUTH_CREDENTIALS env vars
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

from content_gate import run_gate, ACCURACY_BLOCK, quarantine_post, write_manifest
from generate_content_claude import Topic, normalise as normalise_generated_post, save_posts

ROOT       = Path(__file__).resolve().parents[1]
POSTS_FILE = ROOT / "content" / "posts.json"
SITE_FILE  = ROOT / "content" / "site.json"
DOMAIN     = "https://beatthescam.com"
SC_SITE    = "sc-domain:beatthescam.com"

# ── Category mapping ──────────────────────────────────────────────────────────
KEYWORD_CATEGORIES = {
    "whatsapp": "sms", "text": "sms", "sms": "sms", "message": "sms",
    "email": "email", "phishing": "email", "inbox": "email",
    "phone": "phone", "call": "phone", "vishing": "phone",
    "facebook": "social", "instagram": "social", "tiktok": "social",
    "twitter": "social", "linkedin": "social", "social": "social",
    "amazon": "marketplace", "ebay": "marketplace", "gumtree": "marketplace",
    "marketplace": "marketplace", "buying": "marketplace",
    "crypto": "crypto", "bitcoin": "crypto", "investment": "finance",
    "hmrc": "government", "dvla": "government", "gov": "government",
    "passport": "government", "tv licence": "government",
    "royal mail": "sms", "evri": "sms", "delivery": "sms",
    "job": "employment", "recruitment": "employment", "work from home": "employment",
    "dating": "dating", "romance": "dating", "tinder": "dating",
    "paypal": "payment", "bank": "payment", "transfer": "payment",
    "website": "website", "fake website": "website", "url": "website",
    "travel": "travel", "holiday": "travel", "booking": "travel",
    "shopping": "shopping", "refund": "shopping",
    "tech support": "tech", "remote access": "tech", "computer": "tech",
    "broadband": "tech", "bt": "tech", "sky": "tech",
}

def guess_category(query: str) -> str:
    q = query.lower()
    for keyword, cat in KEYWORD_CATEGORIES.items():
        if keyword in q:
            return cat
    return "fraud"

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-")

# ── Auth ──────────────────────────────────────────────────────────────────────
def get_search_console_service():
    """Build Search Console API service from token — works locally and in CI."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import httplib2
        from google_auth_httplib2 import AuthorizedHttp
    except ImportError:
        print("❌ Missing libraries. Run:")
        print("   pip3 install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        sys.exit(1)

    SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
    token_file = ROOT / "token.json"
    creds_file = list(ROOT.glob("client_secret*.json"))

    # CI: load from environment variables
    sc_token = os.getenv("GOOGLE_SEARCH_CONSOLE_TOKEN")

    if sc_token:
        print("🔑 Loading credentials from environment variables (CI mode)")
        token_data = json.loads(sc_token)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    elif token_file.exists():
        print("🔑 Loading credentials from token.json (local mode)")
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    else:
        print("❌ No credentials found. Run: python3 scripts/auth_google.py")
        sys.exit(1)

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        print("🔄 Refreshing expired token...")
        creds.refresh(Request())
        # Save refreshed token locally if possible
        if token_file.exists():
            with open(token_file, "w") as f:
                f.write(creds.to_json())

    http = AuthorizedHttp(creds, http=httplib2.Http())
    return build("searchconsole", "v1", http=http)

# ── Search Console queries ────────────────────────────────────────────────────
def get_trending_queries(service, days: int = 28) -> list:
    """Pull top queries by impressions from Search Console."""
    end_date   = date.today()
    start_date = end_date - timedelta(days=days)

    try:
        response = service.searchanalytics().query(
            siteUrl=SC_SITE,
            body={
                "startDate":  str(start_date),
                "endDate":    str(end_date),
                "dimensions": ["query"],
                "rowLimit":   200,
                "orderBy":    [{"fieldName": "impressions", "sortOrder": "DESCENDING"}],
            }
        ).execute()
    except Exception as e:
        print(f"❌ Search Console API error: {e}")
        return []

    rows = response.get("rows", [])
    queries = []
    for row in rows:
        query      = row["keys"][0]
        impressions = row.get("impressions", 0)
        clicks      = row.get("clicks", 0)
        position    = row.get("position", 100)

        # Focus on queries with decent impressions but room to improve
        if impressions >= 5:
            queries.append({
                "query":       query,
                "impressions": impressions,
                "clicks":      clicks,
                "position":    round(position, 1),
                "ctr":         round(clicks / impressions * 100, 1) if impressions > 0 else 0,
            })

    print(f"📊 Found {len(queries)} queries with 5+ impressions in last {days} days")
    return queries

# ── Gap detection ─────────────────────────────────────────────────────────────
def normalise(text: str) -> str:
    """Normalise text for matching — lowercase, stem plurals."""
    text = text.lower()
    # Simple plural stemming — strip trailing 's' from words
    words = []
    for w in re.findall(r'\b[a-z]{3,}\b', text):
        w = re.sub(r'(?<=.{3})s$', '', w)  # strip trailing s if word > 3 chars
        words.append(w)
    return " ".join(words)

def find_content_gaps(queries: list, posts: list) -> list:
    """Find queries not already well-covered by existing articles."""

    # Build a searchable index of existing content — normalised
    existing_text = normalise(" ".join([
        p.get("title", "") + " " +
        p.get("description", "") + " " +
        p.get("hero", "") + " " +
        " ".join(p.get("keywords", []))
        for p in posts
    ]))

    gaps = []
    for q in queries:
        query_norm = normalise(q["query"])

        # Skip very short queries
        if len(q["query"]) < 8:
            continue

        # Skip branded queries already ranking well
        if q["position"] < 5 and q["clicks"] > 0:
            continue

        # Check coverage using normalised words
        query_words = [w for w in query_norm.split() if len(w) > 3]
        if not query_words:
            continue

        matched_words = sum(1 for w in query_words if w in existing_text)
        coverage = matched_words / len(query_words)

        # If less than 70% of query words are in our content, it's a gap
        if coverage < 0.7:
            gaps.append({
                **q,
                "coverage": round(coverage * 100),
                "category": guess_category(q["query"]),
            })

    gaps.sort(key=lambda x: x["impressions"], reverse=True)
    print(f"🎯 Found {len(gaps)} content gaps")
    return gaps

# ── Article generation ────────────────────────────────────────────────────────
def normalise_search_console_post(data: dict, query: str, category: str, today: str) -> dict:
    """Apply the canonical generated-guide schema to a Search Console draft.

    This pipeline used to assemble its own partial post object. That silently
    diverged after the shared schema gained ``quick_answer``, ``sources_checked``
    and ``updated``: the publication gate correctly quarantined every draft.
    Reusing the canonical normaliser keeps both automated writers on one schema
    and keeps source links canon-derived rather than model-authored.
    """
    return normalise_generated_post(data, Topic(query, query, category), today, strict=True)


def generate_article(query: dict, api_key: str):
    """Generate a complete article for a query gap using Claude API."""
    try:
        from anthropic import Anthropic
    except ImportError:
        print("❌ anthropic not installed. Run: pip3 install anthropic")
        sys.exit(1)

    client   = Anthropic(api_key=api_key)
    q        = query["query"]
    category = query["category"]
    today    = date.today().isoformat()

    print(f"\n✍️  Generating article for: '{q}'")
    print(f"   Category: {category} | Impressions: {query['impressions']} | Position: {query['position']}")

    from generate_content_claude import claude_post
    try:
        return claude_post(Topic(q, q, category), today, "claude-haiku-4-5-20251001", client, [])
    except Exception as exc:
        print(f"Generation held: {type(exc).__name__}")
        return None

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Search Console article generator")
    parser.add_argument("--dry-run",   action="store_true", help="Show gaps without generating")
    parser.add_argument("--days",      type=int, default=28, help="Days of Search Console data")
    parser.add_argument("--min-impr",  type=int, default=5,  help="Minimum impressions threshold")
    parser.add_argument("--limit",     type=int, default=1,  help="Max articles to generate (default 1)")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Load existing posts
    with open(POSTS_FILE, encoding="utf-8") as f:
        posts = json.load(f)

    existing_slugs = {p["slug"] for p in posts}
    print(f"📚 {len(posts)} existing articles loaded")

    # Connect to Search Console
    print("\n🔌 Connecting to Search Console...")
    service = get_search_console_service()

    # Get trending queries
    queries = get_trending_queries(service, days=args.days)
    if not queries:
        print("No queries found — exiting")
        return

    # Find gaps
    gaps = find_content_gaps(queries, posts)
    if not gaps:
        print("✅ No content gaps found — all trending queries are covered")
        return

    print(f"\n📋 Top content gaps:")
    for i, g in enumerate(gaps[:10]):
        print(f"  {i+1:2}. [{g['impressions']:4} impr | pos {g['position']:5.1f} | {g['coverage']}% covered] {g['query']}")

    if args.dry_run:
        print("\n🔍 Dry run — no articles generated")
        return

    # Generate articles for top gaps
    from anthropic import Anthropic
    gate_client = Anthropic(api_key=api_key)
    GATE_MODEL = "claude-haiku-4-5-20251001"

    generated = 0
    for gap in gaps:
        if generated >= args.limit:
            break

        # Skip if slug already exists
        slug = slugify(gap["query"] + " uk scam")
        if slug in existing_slugs:
            print(f"⏭️  Skipping '{gap['query']}' — slug already exists")
            continue

        post = generate_article(gap, api_key)
        if not post:
            print(f"⚠️  Skipping '{gap['query']}' — generation failed")
            continue

        # Accuracy gate — PASS → publish, FAIL → quarantine (never published or tweeted).
        result = run_gate(post, client=gate_client, model=GATE_MODEL, use_llm=True, corpus=posts)
        if not result.passed:
            quarantine_post(post, result, date.today().isoformat())
            print(f"🚫 QUARANTINED '{gap['query']}' — {result.summary()}")
            continue

        # Double-check slug uniqueness
        if post["slug"] in existing_slugs:
            print(f"⏭️  Skipping '{gap['query']}' — generated slug already exists")
            continue

        # Insert at the top (newest first)
        posts.insert(0, post)
        existing_slugs.add(post["slug"])
        generated += 1
        # PASS → write the claim manifest (audit trail; best-effort)
        try:
            write_manifest(post, result, model=GATE_MODEL, today=date.today().isoformat())
        except Exception as e:
            print(f"  [warn] manifest write failed for {post['slug']}: {e}")

        print(f"✅ Added article #{generated}: {post['title']}")

    if generated == 0:
        print("ℹ️  No new articles generated this run")
        return

    # Save posts.json
    save_posts(POSTS_FILE, posts)

    print(f"\n✅ Saved {generated} new article(s) to posts.json")
    print(f"   Total articles: {len(posts)}")

    # Output new slugs for the workflow to use for tweeting
    new_slugs = [posts[i]["slug"] for i in range(generated)]
    print(f"\nNEW_ARTICLE_SLUGS={','.join(new_slugs)}")


if __name__ == "__main__":
    main()
