#!/usr/bin/env python3
"""Upload a rendered short to YouTube as a Shorts video.

Reads the MP4 from out/videos/{slug}.mp4 and metadata from
out/videos/{slug}.upload.md (the title / description / tags blocks that
scripts/generate_video.py companion docs already contain). Uploads via
YouTube Data API v3.

Defaults to **Unlisted** so you can review the upload before going public —
pass --public to publish immediately.

Required environment (in .env or shell):
  YOUTUBE_CLIENT_ID
  YOUTUBE_CLIENT_SECRET
  YOUTUBE_REFRESH_TOKEN

One-time setup: see docs/youtube-upload-setup.md

Usage:
  python3 scripts/upload_to_youtube.py facebook-marketplace-scam-uk
  python3 scripts/upload_to_youtube.py whatsapp-family-emergency-scam --public
  python3 scripts/upload_to_youtube.py <slug> --dry-run
"""
import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_VIDEOS = REPO_ROOT / "out" / "videos"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def parse_upload_md(path: Path) -> dict:
    """Extract YouTube title / description / tags from the .upload.md file.

    Expects the standard structure written by recent renders:

        ### Title (under 100 chars — paste verbatim)
        ```
        <title>
        ```

        ### Description (paste into the description box)
        ```
        <description>
        ```

        ### Tags (paste into the Tags field — comma-separated)
        ```
        <comma-separated tags>
        ```

    The TikTok caption block appears later under "## TikTok upload" so we
    only consume the first occurrence of each label to avoid cross-contamination.
    """
    text = path.read_text()

    # Trim everything from "## TikTok upload" onwards so the TikTok caption
    # blocks don't shadow the YouTube ones if labels happen to match.
    yt_section = re.split(r"^##\s+TikTok\s+upload", text, maxsplit=1, flags=re.M | re.I)[0]

    def grab(label: str) -> Optional[str]:
        pattern = rf"###\s+{re.escape(label)}[^\n]*\n+```\s*\n(.+?)\n```"
        m = re.search(pattern, yt_section, re.DOTALL | re.I)
        return m.group(1).strip() if m else None

    title = grab("Title")
    description = grab("Description")
    tags_text = grab("Tags")
    tags = [t.strip() for t in (tags_text or "").split(",") if t.strip()]
    return {"title": title, "description": description, "tags": tags}


def authenticate() -> Credentials:
    """Build google.oauth2 Credentials from refresh-token env vars."""
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    missing = [
        k for k, v in {
            "YOUTUBE_CLIENT_ID": client_id,
            "YOUTUBE_CLIENT_SECRET": client_secret,
            "YOUTUBE_REFRESH_TOKEN": refresh_token,
        }.items() if not v
    ]
    if missing:
        sys.exit(
            f"ERROR: missing env var(s): {', '.join(missing)}\n"
            f"See docs/youtube-upload-setup.md for one-time OAuth setup."
        )
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )


def upload(slug: str, *, public: bool = False, dry_run: bool = False) -> None:
    mp4 = OUT_VIDEOS / f"{slug}.mp4"
    md  = OUT_VIDEOS / f"{slug}.upload.md"

    if not mp4.exists():
        sys.exit(
            f"ERROR: {mp4} not found.\n"
            f"Render the video first: python3 scripts/generate_video.py {slug}"
        )
    if not md.exists():
        sys.exit(
            f"ERROR: {md} not found.\n"
            f"Metadata file is required. Check out/videos/ for the .upload.md."
        )

    meta = parse_upload_md(md)
    if not meta["title"] or not meta["description"]:
        sys.exit(
            f"ERROR: could not parse title / description from {md}\n"
            f"Make sure the file has '### Title' and '### Description' headings"
            f" followed by fenced code blocks."
        )

    size_mb = mp4.stat().st_size // (1024 * 1024)
    print(f"slug:        {slug}")
    print(f"file:        {mp4.name} ({size_mb} MB)")
    print(f"title:       {meta['title']}")
    print(f"description: {meta['description'].splitlines()[0][:120]}...")
    print(f"tags:        {len(meta['tags'])} tag(s): {', '.join(meta['tags'][:5])}{'...' if len(meta['tags']) > 5 else ''}")
    print(f"privacy:     {'public' if public else 'unlisted'} (Education / Made for kids: NO)")

    if dry_run:
        print("\n(dry-run — metadata parsed OK, no upload performed)")
        return

    creds = authenticate()
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": meta["title"][:100],          # YouTube hard limit
            "description": meta["description"][:5000],  # YouTube hard limit
            "tags": meta["tags"][:30],             # YouTube practical limit (500 char total)
            "categoryId": "27",                    # Education
            "defaultLanguage": "en-GB",
            "defaultAudioLanguage": "en-GB",
        },
        "status": {
            "privacyStatus": "public" if public else "unlisted",
            "selfDeclaredMadeForKids": False,
            "license": "youtube",
            "embeddable": True,
        },
    }

    media = MediaFileUpload(str(mp4), mimetype="video/mp4", resumable=True)

    print("\nUploading (resumable, ~30-60s)...")
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}% uploaded")

    video_id = response["id"]
    print()
    print("✅ Uploaded.")
    print(f"   Shorts URL: https://youtube.com/shorts/{video_id}")
    print(f"   Studio:     https://studio.youtube.com/video/{video_id}/edit")
    print()
    print("Next steps in Studio:")
    print("  1. Confirm 'Altered content: Yes' is set (AI voice — required disclosure)")
    print("  2. Set thumbnail to the hook frame if auto-selection looks off")
    print("  3. Add to your 'Scam Alerts' playlist (or create one)")
    if not public:
        print("  4. After 24h review, change visibility from Unlisted → Public")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Upload a rendered short to YouTube Shorts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="One-time OAuth setup: docs/youtube-upload-setup.md",
    )
    p.add_argument("slug", help="Article slug (also the MP4 filename in out/videos/)")
    p.add_argument(
        "--public",
        action="store_true",
        help="Publish as Public immediately (default: Unlisted for 24h review)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse metadata and validate without uploading",
    )
    args = p.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    upload(args.slug, public=args.public, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
