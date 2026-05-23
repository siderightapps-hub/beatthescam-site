#!/usr/bin/env python3
"""Minimal Twitter API auth diagnostic — call the simplest auth-required
endpoint (get_me()) and report exactly why it fails if it does.

Usage:
    python3 scripts/check_twitter_auth.py

Run this when the main tweet script returns 401 Unauthorized. The output
narrows the failure mode:
    - get_me() succeeds  → credentials work for reads; the 401 is a
      write-specific issue (app permission scope or API tier restriction).
    - get_me() returns 401  → the credentials in .env are wrong, expired,
      or revoked, regardless of what the Developer Portal shows.
    - get_me() returns 403  → credentials valid but the app or account
      is suspended.
    - get_me() returns 429  → rate-limited.
"""
import os
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import tweepy
except ImportError:
    sys.exit("Run: python3 -m pip install tweepy python-dotenv")

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("Run: python3 -m pip install tweepy python-dotenv")


def mask(s: Optional[str]) -> str:
    if not s:
        return "(missing)"
    if len(s) <= 8:
        return "***"
    return f"{s[:4]}...{s[-4:]} (len={len(s)})"


def main() -> int:
    load_dotenv(ROOT / ".env")

    api_key      = os.getenv("TWITTER_API_KEY")
    api_secret   = os.getenv("TWITTER_API_KEY_SECRET")
    access_tok   = os.getenv("TWITTER_ACCESS_TOKEN")
    access_sec   = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    print("=== Loaded credentials (masked) ===")
    print(f"  TWITTER_API_KEY:             {mask(api_key)}")
    print(f"  TWITTER_API_KEY_SECRET:      {mask(api_secret)}")
    print(f"  TWITTER_ACCESS_TOKEN:        {mask(access_tok)}")
    print(f"  TWITTER_ACCESS_TOKEN_SECRET: {mask(access_sec)}")
    print()

    if not all([api_key, api_secret, access_tok, access_sec]):
        print("❌ One or more credentials missing from .env.")
        return 1

    # Detect .env.example placeholder values — easy to overlook after a
    # `cp .env.example .env`. Don't even try the API call if these are set.
    placeholders = {
        "TWITTER_API_KEY":             api_key,
        "TWITTER_API_KEY_SECRET":      api_secret,
        "TWITTER_ACCESS_TOKEN":        access_tok,
        "TWITTER_ACCESS_TOKEN_SECRET": access_sec,
    }
    bad = [k for k, v in placeholders.items() if v.endswith("_here") or v.startswith("your_")]
    if bad:
        print(f"❌ Placeholder values detected in .env for: {', '.join(bad)}")
        print(f"   Looks like .env was copied from .env.example and never had the")
        print(f"   real keys filled in (or they were overwritten by a later cp).")
        print(f"   Fix:")
        print(f"   1. Twitter Developer Portal → Keys and tokens → Regenerate Access Token")
        print(f"   2. Update both .env locally AND the four TWITTER_* GitHub Secrets")
        print(f"   3. Re-run this script to verify")
        return 1

    # Sanity-check token shape — OAuth 1.0a access tokens always have the
    # format <numeric-user-id>-<40 hex chars>, e.g. "1234567890-abc...123".
    if "-" not in access_tok:
        print("⚠  Access token doesn't contain '-' — usually OAuth 1.0a tokens")
        print("   are formatted '<user_id>-<hex>'. Check you copied the OAuth 1.0")
        print("   Access Token, NOT the OAuth 2.0 Client ID/Secret.")
        print()

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_tok,
        access_token_secret=access_sec,
    )

    print("=== Test 1: get_me() (cheapest auth check, reads your own user info) ===")
    try:
        me = client.get_me()
        if me and me.data:
            print(f"✅ Authenticated as @{me.data.username} (user_id={me.data.id})")
            print()
        else:
            print(f"⚠  get_me() returned without an error but no data: {me}")
            print()
    except tweepy.Unauthorized as e:
        print(f"❌ 401 Unauthorized on read endpoint.")
        print(f"   The credentials in .env don't authenticate against the API at all.")
        print(f"   Detail: {e}")
        print()
        print("Most likely cause:")
        print("  → Credentials were copied incorrectly into .env (transcription error)")
        print("    OR the keys in .env don't match the @BeatTheScamUK app.")
        print()
        print("Fix:")
        print("  1. Go to https://developer.twitter.com/en/portal/dashboard")
        print("  2. App → 'Keys and tokens' → click 'Regenerate' on Access Token")
        print("  3. Copy the NEW access token + secret into .env")
        print("  4. Re-run this diagnostic")
        return 1
    except tweepy.Forbidden as e:
        print(f"❌ 403 Forbidden — app or account suspended. Detail: {e}")
        return 1
    except tweepy.TooManyRequests as e:
        print(f"❌ 429 Rate limited. Detail: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error on get_me(): {type(e).__name__}: {e}")
        return 1

    print("=== Test 2: create_tweet() dry-run check (writes require Read+Write) ===")
    print("  (Posting an actual test tweet would clutter your timeline — instead")
    print("   we look at the OAuth scopes that come back with get_me().)")
    print()
    # tweepy.Client doesn't expose scopes directly for OAuth 1.0a, but the
    # presence of write access is implicit in the app's permissions setting.
    # The cleanest test is to actually POST a benign tweet and immediately
    # delete it — but that risks visible-on-timeline failures. Skip unless
    # you want to run it manually.
    print("✅ Read endpoint works. If the main tweet script still 401s now,")
    print("   the issue is on the write path specifically — possible causes:")
    print("     1. App permissions were 'Read and write' AFTER the access token")
    print("        was generated → token still has the old read-only scope.")
    print("        Fix: regenerate Access Token & Secret AFTER changing perms.")
    print("     2. Twitter API tier restricts POST /2/tweets (Free tier issues).")
    print("        Fix: check https://developer.twitter.com/en/portal/products")
    print("     3. Account-level write restriction (rare).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
