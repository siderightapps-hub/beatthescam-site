#!/usr/bin/env python3
"""
Beat The Scam — Twitter / X Auto-Poster
========================================
Reads content/posts.json, detects articles not yet tweeted,
and posts them to @BeatTheScamUK one at a time.

Run manually:       python3 scripts/tweet_new_articles.py
Run on new article: add to your publish workflow
Seed existing posts (mark all as done without tweeting):
                    python3 scripts/tweet_new_articles.py --seed

Credentials: copy .env.example → .env and fill in your keys.
NEVER commit .env to git.
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    import tweepy
except ImportError:
    print("tweepy not installed. Run:  pip install tweepy python-dotenv")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv not installed. Run:  pip install tweepy python-dotenv")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT          = Path(__file__).resolve().parents[1]
POSTS_FILE    = ROOT / "content" / "posts.json"
TWEETED_FILE  = ROOT / "content" / "tweeted_posts.json"
SITE_DOMAIN   = "https://beatthescam.com"

# ── Category → hashtags map ───────────────────────────────────────────────────
CATEGORY_TAGS = {
    "phone":       "#PhoneScam",
    "sms":         "#TextScam",
    "email":       "#EmailScam",
    "crypto":      "#CryptoScam",
    "marketplace": "#OnlineScam",
    "dating":      "#RomanceScam",
    "employment":  "#JobScam",
    "government":  "#HMRCScam",
    "tech":        "#TechScam",
    "payment":     "#BankScam",
    "social":      "#SocialMediaScam",
    "website":     "#FakeWebsite",
    "shopping":    "#ShoppingScam",
    "travel":      "#TravelScam",
    "finance":     "#InvestmentScam",
    "fraud":       "#FraudAlert",
    "utility":     "#EnergyScam",
    "crypto":      "#CryptoScam",
}

# ── Tweet composer ────────────────────────────────────────────────────────────
def build_tweet(post: dict) -> str:
    """
    Compose a tweet under 280 characters.
    Format:
        ⚠️ {title}
        {short description}
        👉 {url}
        #ScamAlert #UK {category_tag}
    """
    title       = post["title"]
    description = post.get("description", post.get("hero", ""))
    slug        = post["slug"]
    category    = post.get("category", "fraud").lower()
    url         = f"{SITE_DOMAIN}/guides/{slug}/?utm_source=twitter&utm_medium=social&utm_campaign=article&utm_content=v3"
    cat_tag     = CATEGORY_TAGS.get(category, "#ScamAlert")
    base_tags   = f"#ScamAlert #UKScam {cat_tag}"

    # Try full description first, then truncate
    for desc_limit in [120, 80, 40, 0]:
        if desc_limit > 0:
            desc = description[:desc_limit].rsplit(" ", 1)[0] + "…" if len(description) > desc_limit else description
            body = f"⚠️ {title}\n\n{desc}\n\n👉 {url}\n\n{base_tags}"
        else:
            body = f"⚠️ {title}\n\n👉 {url}\n\n{base_tags}"

        if len(body) <= 280:
            return body

    # Last resort — truncate title
    short_title = title[:100].rsplit(" ", 1)[0] + "…"
    return f"⚠️ {short_title}\n\n👉 {url}\n\n{base_tags}"[:280]


# ── Tweeted posts tracker ─────────────────────────────────────────────────────
def load_tweeted() -> dict:
    if TWEETED_FILE.exists():
        with open(TWEETED_FILE) as f:
            return json.load(f)
    return {}

def save_tweeted(tweeted: dict):
    with open(TWEETED_FILE, "w") as f:
        json.dump(tweeted, f, indent=2)

# ── Twitter client ────────────────────────────────────────────────────────────
def get_client():
    load_dotenv(ROOT / ".env")
    api_key             = os.getenv("TWITTER_API_KEY")
    api_secret          = os.getenv("TWITTER_API_KEY_SECRET")
    access_token        = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    creds = {
        "TWITTER_API_KEY":             api_key,
        "TWITTER_API_KEY_SECRET":      api_secret,
        "TWITTER_ACCESS_TOKEN":        access_token,
        "TWITTER_ACCESS_TOKEN_SECRET": access_token_secret,
    }
    missing = [k for k, v in creds.items() if not v]
    if missing:
        print(f"❌ Missing keys in .env: {', '.join(missing)}")
        print(f"   Copy .env.example → .env and fill in your credentials.")
        sys.exit(1)

    # Detect .env.example placeholder values so we fail with a clear message
    # instead of getting a confusing 401 from Twitter. This trap exists because
    # `cp .env.example .env` over an existing .env is an easy mistake to make
    # when adding new sections to the template (it happened on 2026-05-22 when
    # the ElevenLabs section was added — wiped the Twitter values).
    placeholders = [k for k, v in creds.items() if v and (
        v.endswith("_here") or v.startswith("your_") or v == "sk_your_key_here"
    )]
    if placeholders:
        print(f"❌ Placeholder values detected in .env for: {', '.join(placeholders)}")
        print(f"   Looks like .env was copied from .env.example without filling in")
        print(f"   the real keys. Fix:")
        print(f"   1. Get the real values from https://developer.twitter.com/en/portal/dashboard")
        print(f"   2. Replace the 'your_*_here' lines in .env with the real keys.")
        print(f"   3. Re-run: python3 scripts/check_twitter_auth.py to verify.")
        sys.exit(1)

    return tweepy.Client(
        consumer_key        = api_key,
        consumer_secret     = api_secret,
        access_token        = access_token,
        access_token_secret = access_token_secret,
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Beat The Scam Twitter auto-poster")
    parser.add_argument("--seed", action="store_true",
                        help="Mark all existing articles as tweeted WITHOUT posting them")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview tweets without posting")
    parser.add_argument("--limit", type=int, default=5,
                        help="Max new tweets to send per run (default: 5)")
    parser.add_argument("--slug", type=str,
                        help="Tweet a specific article by slug only")
    parser.add_argument("--force", action="store_true",
                        help="With --slug, tweet even if already recorded in tweeted_posts.json")
    args = parser.parse_args()

    # Load posts — deduplicate by slug
    with open(POSTS_FILE) as f:
        posts = json.load(f)
    seen = set()
    deduped = []
    for p in posts:
        if p["slug"] not in seen:
            deduped.append(p)
            seen.add(p["slug"])
    if len(deduped) < len(posts):
        print(f"⚠️  Skipping {len(posts) - len(deduped)} duplicate slug(s)")
    posts = deduped

    tweeted = load_tweeted()

    # ── Seed mode — mark all done, no posting ─────────────────────────────────
    if args.seed:
        count = 0
        for post in posts:
            slug = post["slug"]
            if slug not in tweeted:
                tweeted[slug] = {"tweeted_at": "seeded", "tweet_id": None}
                count += 1
        save_tweeted(tweeted)
        print(f"✅ Seeded {count} articles as already tweeted (nothing was posted).")
        print(f"   Going forward, only NEW articles added to posts.json will be tweeted.")
        return

    # ── Find unposted articles ─────────────────────────────────────────────────
    if args.slug:
        # Specific slug only
        to_tweet = [p for p in posts if p["slug"] == args.slug]
        if not to_tweet:
            print(f"❌ Slug '{args.slug}' not found in posts.json")
            sys.exit(1)
        # --slug bypasses the "all unposted" filter below, so without this
        # check it never consults tweeted_posts.json — re-running the CI
        # workflow (e.g. after its own push step failed) would re-tweet the
        # same slug every time.
        if args.slug in tweeted and not args.force:
            print(f"✅ '{args.slug}' is already recorded as tweeted — skipping (use --force to re-tweet).")
            return
    else:
        # All unposted, newest first (posts.json is newest-first)
        to_tweet = [p for p in posts if p["slug"] not in tweeted][:args.limit]

    if not to_tweet:
        print("✅ No new articles to tweet. All up to date.")
        return

    print(f"📋 {len(to_tweet)} article(s) to tweet:\n")

    # ── Preview / dry run ─────────────────────────────────────────────────────
    for post in to_tweet:
        tweet_text = build_tweet(post)
        print(f"  [{post['slug']}]")
        print(f"  Characters: {len(tweet_text)}/280")
        print(f"  {'─' * 60}")
        print(f"  {tweet_text}")
        print()

    if args.dry_run:
        print("🔍 Dry run — nothing posted.")
        return

    # ── Confirm before posting ────────────────────────────────────────────────
    if not args.slug:
        confirm = input(f"Post {len(to_tweet)} tweet(s) to @BeatTheScamUK? [y/N] ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            return

    # ── Post to Twitter ───────────────────────────────────────────────────────
    client = get_client()
    posted = 0

    for post in to_tweet:
        tweet_text = build_tweet(post)
        slug       = post["slug"]
        try:
            response = client.create_tweet(text=tweet_text)
            tweet_id = response.data["id"]
            tweeted[slug] = {
                "tweeted_at": datetime.utcnow().isoformat(),
                "tweet_id":   tweet_id,
                "title":      post["title"],
            }
            save_tweeted(tweeted)
            print(f"  ✅ Posted: {post['title'][:60]}")
            print(f"     https://x.com/BeatTheScamUK/status/{tweet_id}")
            posted += 1

            # Respect rate limits — wait 3s between tweets
            if posted < len(to_tweet):
                time.sleep(3)

        except tweepy.TweepyException as e:
            print(f"  ❌ Failed to post '{slug}': {e}")

    print(f"\n✅ Done — {posted}/{len(to_tweet)} tweets posted.")


if __name__ == "__main__":
    main()
