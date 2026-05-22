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
import subprocess
import sys
from datetime import datetime, timedelta
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


def _create_macos_reminder(slug: str, video_id: str) -> bool:
    """Create a macOS Reminders entry to upload the video to TikTok.

    Schedules for 07:30 local time today if that's still in the future, else
    07:30 tomorrow. Reminder syncs to your iPhone via iCloud Reminders.

    Silently no-ops on non-macOS platforms. Returns True on success, False
    on failure (osascript missing, Reminders permission denied, or another
    error). The first run on a fresh Mac prompts for "osascript wants to
    control Reminders" — grant once, all future runs are silent.
    """
    if sys.platform != "darwin":
        return False

    # Schedule for 07:30 local time. If past 07:30 already today, push to
    # the same time tomorrow — the project's preferred posting window is
    # 07:30-09:00 UK BST.
    now = datetime.now()
    target = now.replace(hour=7, minute=30, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)

    title = f"Upload {slug} to TikTok"
    body_lines = [
        f"YouTube: https://youtube.com/shorts/{video_id}",
        f"Video: out/videos/{slug}.mp4",
        f"Caption + hashtags: out/videos/{slug}.upload.md (see TikTok section)",
        "Music: TikTok 'Breaking News' commercial sound",
        "AI-generated content: toggle ON",
    ]
    body = "\n".join(body_lines)

    # AppleScript string literals don't support backslash escapes. Embed
    # newlines via 'linefeed' concatenation; escape double quotes literally.
    def esc(s: str) -> str:
        return (
            s.replace("\\", "\\\\")
             .replace('"', '\\"')
             .replace("\n", '" & linefeed & "')
        )

    script = (
        "set theDate to current date\n"
        f"set year of theDate to {target.year}\n"
        f"set month of theDate to {target.month}\n"
        f"set day of theDate to {target.day}\n"
        f"set hours of theDate to {target.hour}\n"
        f"set minutes of theDate to {target.minute}\n"
        "set seconds of theDate to 0\n"
        "tell application \"Reminders\"\n"
        f"    make new reminder with properties {{name:\"{esc(title)}\", body:\"{esc(body)}\", remind me date:theDate}}\n"
        "end tell\n"
    )

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return True
        # Common failure mode: first run prompts for permission and the
        # user hasn't granted yet. Surface the stderr so they can fix.
        print(f"⚠ Could not create Reminder ({result.stderr.strip() or 'unknown'})")
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def upload(slug: str, *, public: bool = False, dry_run: bool = False) -> None:
    mp4   = OUT_VIDEOS / f"{slug}.mp4"
    md    = OUT_VIDEOS / f"{slug}.upload.md"
    thumb = OUT_VIDEOS / f"{slug}.thumbnail.jpg"

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
    if thumb.exists():
        print(f"thumbnail:   {thumb.name} ({thumb.stat().st_size // 1024} KB)")
    else:
        print(f"thumbnail:   (none — YouTube will auto-pick the hook frame)")

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
    print("✅ Video uploaded.")
    print(f"   Shorts URL: https://youtube.com/shorts/{video_id}")
    print(f"   Studio:     https://studio.youtube.com/video/{video_id}/edit")

    # Custom thumbnail upload (non-fatal on failure — the video is up either way).
    # Custom thumbnails require a verified YouTube account (phone confirmation).
    # If your account isn't verified, this step fails with a 403; the video
    # is still successfully uploaded and YouTube uses the auto-selected
    # hook-frame thumbnail instead.
    if thumb.exists():
        print()
        print("Uploading thumbnail...")
        try:
            yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg"),
            ).execute()
            print(f"✅ Thumbnail set ({thumb.name})")
        except Exception as e:
            print(f"⚠ Thumbnail upload failed (video upload itself was fine): {e}")
            print(f"  If this is a 403, your YouTube account needs phone verification.")
            print(f"  Set the thumbnail manually in Studio for now.")

    # Schedule a TikTok-upload reminder via macOS Reminders (syncs to iPhone
    # via iCloud). No-ops silently on non-macOS platforms.
    if _create_macos_reminder(slug, video_id):
        print()
        print("📌 TikTok upload reminder added to macOS Reminders for 07:30 (today/tomorrow).")
        print("   It includes the YouTube URL, video path, and a link to the .upload.md.")

    print()
    print("Next steps in Studio:")
    print("  1. Confirm 'Altered content: Yes' is set (AI voice — required disclosure)")
    print("  2. Add to your 'Scam Alerts' playlist (or create one)")
    if not public:
        print("  3. After 24h review, change visibility from Unlisted → Public")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Upload a rendered short to YouTube Shorts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="One-time OAuth setup: docs/youtube-upload-setup.md",
    )
    p.add_argument(
        "slug",
        nargs="?",
        help="Article slug (also the MP4 filename in out/videos/)",
    )
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
    p.add_argument(
        "--test-reminder",
        action="store_true",
        help=(
            "Create a one-off test macOS Reminder and exit. Use this on first run"
            " to grant 'osascript wants to control Reminders' permission without"
            " burning a real upload."
        ),
    )
    args = p.parse_args()

    load_dotenv(REPO_ROOT / ".env")

    if args.test_reminder:
        test_slug = args.slug or "test-reminder-from-script"
        print(f"Creating test Reminder for slug={test_slug!r}...")
        if _create_macos_reminder(test_slug, "TEST_VIDEO_ID"):
            print("✅ Test Reminder created. Open the Reminders app and you should")
            print("   see 'Upload {} to TikTok' scheduled for 07:30.".format(test_slug))
            print("   Delete it once you've verified it's there.")
            sys.exit(0)
        else:
            print("❌ Reminder creation failed.")
            print("   First-time? macOS may have just popped up an authorization dialog")
            print("   asking 'osascript wants to control Reminders'. Click OK and re-run.")
            sys.exit(1)

    if not args.slug:
        p.error("slug is required (unless --test-reminder is set)")

    upload(args.slug, public=args.public, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
