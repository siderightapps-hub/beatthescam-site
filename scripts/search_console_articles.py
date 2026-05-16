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
    sc_creds = os.getenv("GOOGLE_OAUTH_CREDENTIALS")

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
def find_content_gaps(queries: list, posts: list) -> list:
    """Find queries not already well-covered by existing articles."""

    # Build a searchable index of existing content
    existing_text = " ".join([
        p.get("title", "") + " " +
        p.get("description", "") + " " +
        " ".join(p.get("keywords", []))
        for p in posts
    ]).lower()

    gaps = []
    for q in queries:
        query = q["query"].lower()

        # Skip very short queries
        if len(query) < 8:
            continue

        # Skip branded queries already ranking well
        if q["position"] < 5 and q["clicks"] > 0:
            continue

        # Check if existing content covers this query
        query_words = [w for w in query.split() if len(w) > 3]
        matched_words = sum(1 for w in query_words if w in existing_text)
        coverage = matched_words / len(query_words) if query_words else 1

        # If less than 60% of query words are in our content, it's a gap
        if coverage < 0.6:
            gaps.append({
                **q,
                "coverage": round(coverage * 100),
                "category": guess_category(query),
            })

    # Sort by impressions (highest opportunity first)
    gaps.sort(key=lambda x: x["impressions"], reverse=True)
    print(f"🎯 Found {len(gaps)} content gaps")
    return gaps

# ── Article generation ────────────────────────────────────────────────────────
def generate_article(query: dict, api_key: str) -> dict | None:
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

    prompt = f"""You are writing a scam awareness guide for beatthescam.com, a UK consumer protection website.

Write a complete guide about: "{q}"

CRITICAL RULES — violations will cause the article to be rejected:
- Write ONLY about verified, documented UK scams
- Do NOT invent statistics, victim numbers, or financial losses
- If you cite a figure, it must be from Action Fraud, FCA, Which?, NCSC, or UK Finance
- If you cannot verify a stat, describe the scam pattern without figures
- All content must be UK-specific (use £ not $, UK reporting numbers, UK organisations)
- Action Fraud number: 0300 123 2040 | Spam texts: 7726

OUTPUT FORMAT — respond with a single valid JSON object only, no other text:
{{
  "title": "Specific UK-focused title including the scam type (max 80 chars)",
  "description": "2-sentence description explaining what this guide covers and who it helps (max 160 chars)",
  "hero": "1-sentence hook describing the scam threat (max 120 chars)",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6"],
  "sections": [
    ["What is this scam?", "130-180 word explanation of the scam and how it works in the UK"],
    ["How it works — step by step", "- Step 1: ...\n- Step 2: ...\n- Step 3: ...\n- Step 4: ...\n- Step 5: ..."],
    ["Warning signs to look for", "- Warning sign one\n- Warning sign two\n- Warning sign three\n- Warning sign four\n- Warning sign five\n- Warning sign six"],
    ["What to do if you receive one", "- Action one\n- Action two\n- Action three\n- Action four\n- Action five"],
    ["How to protect yourself", "130-180 word paragraph with practical prevention advice"],
    ["How to report it", "Explain how to report to Action Fraud (0300 123 2040 or actionfraud.police.uk), forward suspicious texts to 7726, and contact your bank immediately if money was lost."]
  ],
  "faq": [
    ["Question 1 someone would Google about this scam?", "Clear, specific answer (60-100 words)"],
    ["Question 2?", "Clear, specific answer (60-100 words)"],
    ["Question 3?", "Clear, specific answer (60-100 words)"],
    ["Question 4?", "Clear, specific answer (60-100 words)"]
  ]
}}"""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences if present
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)

        # Validate required fields
        required = ["title", "description", "hero", "keywords", "sections", "faq"]
        for field in required:
            if field not in data:
                print(f"❌ Missing field in response: {field}")
                return None

        if len(data["sections"]) < 4:
            print(f"❌ Too few sections: {len(data['sections'])}")
            return None

        # Build the full post object
        post = {
            "slug":        slugify(data["title"]),
            "title":       data["title"],
            "description": data["description"],
            "hero":        data["hero"],
            "date":        today,
            "category":    category,
            "keywords":    data["keywords"],
            "sections":    data["sections"],
            "faq":         data["faq"],
        }

        print(f"   ✅ Generated: {post['title'][:60]}")
        print(f"   Slug: {post['slug']}")
        return post

    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print(f"   Raw response: {raw[:200]}")
        return None
    except Exception as e:
        print(f"❌ Generation error: {e}")
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

        # Double-check slug uniqueness
        if post["slug"] in existing_slugs:
            print(f"⏭️  Skipping '{gap['query']}' — generated slug already exists")
            continue

        # Insert at the top (newest first)
        posts.insert(0, post)
        existing_slugs.add(post["slug"])
        generated += 1

        print(f"✅ Added article #{generated}: {post['title']}")

    if generated == 0:
        print("ℹ️  No new articles generated this run")
        return

    # Save posts.json
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {generated} new article(s) to posts.json")
    print(f"   Total articles: {len(posts)}")

    # Output new slugs for the workflow to use for tweeting
    new_slugs = [posts[i]["slug"] for i in range(generated)]
    print(f"\nNEW_ARTICLE_SLUGS={','.join(new_slugs)}")


if __name__ == "__main__":
    main()
