#!/usr/bin/env python3
"""
Beat The Scam — One-time Google OAuth Authorisation
====================================================
Run this ONCE on your Mac to authorise Search Console API access.
It will open a browser, you log in with siderightapps@gmail.com,
and it saves a token.json file.

That token.json then gets added to GitHub Secrets so GitHub Actions
can run without a browser.

Usage:
    python3 scripts/auth_google.py
"""

import os
import json
import glob
from pathlib import Path

# ── Find credentials file ─────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]

# Look for client_secret*.json in the repo root
cred_files = list(ROOT.glob("client_secret*.json"))
if not cred_files:
    print("❌ No client_secret*.json file found in the repo root.")
    print("   Make sure your Google OAuth credentials JSON is in:")
    print(f"   {ROOT}/")
    exit(1)

CREDENTIALS_FILE = str(cred_files[0])
TOKEN_FILE = str(ROOT / "token.json")

print(f"✅ Found credentials: {Path(CREDENTIALS_FILE).name}")

# ── OAuth flow ────────────────────────────────────────────────────────────────
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print("❌ Missing libraries. Run:")
    print("   pip3 install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    exit(1)

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

creds = None

# Check if token already exists
if os.path.exists(TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

# If no valid credentials, run the browser auth flow
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        print("🔄 Refreshing expired token...")
        creds.refresh(Request())
    else:
        print()
        print("🌐 Opening browser for Google login...")
        print("   Log in with: siderightapps@gmail.com")
        print("   Then grant access to Search Console")
        print()
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

# Save the token
with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())

print()
print(f"✅ Token saved to: {TOKEN_FILE}")
print()
print("═" * 60)
print("NEXT STEP — Add token to GitHub Secrets:")
print("═" * 60)
print()
print("1. Open token.json and copy ALL the contents")
print("2. Go to GitHub repo → Settings → Secrets → Actions")
print("3. Click 'New repository secret'")
print("4. Name:  GOOGLE_SEARCH_CONSOLE_TOKEN")
print("5. Value: paste the token.json contents")
print("6. Click 'Add secret'")
print()
print("Then run the Search Console script to verify it works:")
print("   python3 scripts/search_console_articles.py --dry-run")
print()

# Test the connection
try:
    from googleapiclient.discovery import build
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp

    http = AuthorizedHttp(creds, http=httplib2.Http())
    service = build("searchconsole", "v1", http=http)

    # List verified sites
    sites = service.sites().list().execute()
    verified = [s["siteUrl"] for s in sites.get("siteEntry", [])
                if s.get("permissionLevel") != "siteUnverifiedUser"]

    print("✅ Connection verified! Sites accessible:")
    for site in verified:
        bts = " ← beatthescam.com" if "beatthescam" in site else ""
        print(f"   {site}{bts}")

    if not any("beatthescam" in s for s in verified):
        print()
        print("⚠️  beatthescam.com not found in your verified sites.")
        print("   Make sure it's verified at search.google.com/search-console")

except Exception as e:
    print(f"⚠️  Connection test failed: {e}")
    print("   Token was saved — try running the main script anyway.")
