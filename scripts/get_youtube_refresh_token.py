#!/usr/bin/env python3
"""One-time OAuth flow to mint a YouTube upload refresh token.

Run this once after creating a Desktop OAuth client in Google Cloud Console
(see docs/youtube-upload-setup.md). It opens a browser, walks you through
consent, and prints the refresh token. Add the printed token to your .env
as YOUTUBE_REFRESH_TOKEN — subsequent uploads use it without further prompts.

Usage:
  YOUTUBE_CLIENT_ID=<id> YOUTUBE_CLIENT_SECRET=<secret> \\
    python3 scripts/get_youtube_refresh_token.py

Or set those two in .env beforehand and just run the script.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow


REPO_ROOT = Path(__file__).resolve().parent.parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not client_id or not client_secret:
        sys.exit(
            "ERROR: set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in your .env\n"
            "(or export them in your shell) before running this script.\n"
            "See docs/youtube-upload-setup.md."
        )

    client_config = {
        "installed": {
            "client_id":     client_id,
            "client_secret": client_secret,
            "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
            "token_uri":     "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    # access_type=offline + prompt=consent forces issuance of a refresh token
    # even if you've previously authorised this client.
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
        open_browser=True,
        success_message="OK — you can close this tab.",
    )

    if not creds.refresh_token:
        sys.exit(
            "ERROR: no refresh token returned. Try revoking access at\n"
            "https://myaccount.google.com/permissions and re-running."
        )

    print()
    print("=" * 60)
    print("Add this line to your .env file:")
    print("=" * 60)
    print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 60)
    print()
    print("Test it:")
    print("  python3 scripts/upload_to_youtube.py <slug> --dry-run")


if __name__ == "__main__":
    main()
