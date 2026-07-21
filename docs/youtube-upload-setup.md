# YouTube Shorts auto-upload — one-time OAuth setup

> **HISTORICAL / INACTIVE:** video production was discontinued 2026-06-15. Do not create credentials or revive this workflow unless the owner explicitly restarts the channel. See [`video-pipeline.md`](video-pipeline.md) for the decision record.

Setting up OAuth for `scripts/upload_to_youtube.py` is a 10–15 minute task. You do it once, then every future upload is a single command.

## What you'll create

1. A Google Cloud project with the YouTube Data API v3 enabled.
2. An OAuth 2.0 client (Desktop application).
3. A refresh token via the helper script's browser flow.
4. Three values added to your local `.env`.

You can reuse an existing Google Cloud project if you have one (e.g. the project you used for Search Console). The API + OAuth client are scoped narrowly to YouTube uploads.

---

## Step 1 — Install the Python dependencies

```bash
cd ~/Projects/websites/beatthescam-site
python3 -m pip install google-auth-oauthlib google-api-python-client python-dotenv
```

Use `python3 -m pip` (not bare `pip`) — on macOS, `pip` is often not aliased even when `python3` works fine, and using `python3 -m pip` guarantees the libs install into the same Python the upload script will use.

If you get a *permission denied* error (system Python writing to a system path), add `--user`:

```bash
python3 -m pip install --user google-auth-oauthlib google-api-python-client python-dotenv
```

That installs into `~/Library/Python/3.x/lib/python/site-packages/` — your user site, no sudo needed.

(You already have `python-dotenv` for the Twitter scripts; the other two are new.)

---

## Step 2 — Google Cloud project + API

1. Open https://console.cloud.google.com/
2. Top bar → Project selector → **New Project** → name it "Beat The Scam Video Upload" (or reuse an existing project).
3. Switch into the project.
4. APIs & Services → **Library** → search **"YouTube Data API v3"** → click it → **Enable**.

---

## Step 3 — OAuth consent screen

1. APIs & Services → **OAuth consent screen**.
2. User type: **External** → Create.
3. App information:
   - App name: `Beat The Scam Video Upload`
   - User support email: your email
   - Developer contact email: your email
4. **Scopes** → Add or remove scopes → search `youtube.upload` → tick `.../auth/youtube.upload` → Update → Save and continue.
5. **Test users** → Add your Google account (the one that owns the Beat The Scam YouTube brand account) → Save and continue.
6. Summary → Back to dashboard.
7. **Publish the app.** OAuth consent screen → **Publishing status** → **Publish app** → confirm. This moves the app from "Testing" to **"In production"**. For a single-user tool using only the narrow `youtube.upload` scope, Google does **not** require its formal verification review — you'll see an "unverified app" warning during the consent flow (click through it; see Step 5), but the app stays in production. **This is the important bit: refresh tokens minted while the app is in Production do not expire.** Testing-mode tokens silently die after 7 days, which is what bit us on 2026-05-29. The app is now in Production, so this is a one-time setup.

---

## Step 4 — Create the OAuth client

1. APIs & Services → **Credentials** → **Create credentials** → **OAuth client ID**.
2. Application type: **Desktop app**.
3. Name: `Beat The Scam Local Uploader`.
4. Click **Create**. A dialog shows your **Client ID** and **Client Secret** — copy both somewhere safe.

---

## Step 5 — Get a refresh token

Put the client ID and secret in your `.env`:

```bash
YOUTUBE_CLIENT_ID=<paste from step 4>
YOUTUBE_CLIENT_SECRET=<paste from step 4>
```

Then run the helper:

```bash
python3 scripts/get_youtube_refresh_token.py
```

It will:
- Open your browser.
- Ask you to sign in with the Google account that owns the Beat The Scam YouTube channel.
- Warn that **"the app is not verified"** — click **Advanced** → **Go to Beat The Scam Video Upload (unsafe)**. This is fine; you're authorising your own app.
- Ask for permission to **manage your YouTube account** (specifically: upload videos).
- **Write the refresh token straight into your `.env`** — it replaces any existing `YOUTUBE_REFRESH_TOKEN=` line, or appends one if none exists. (It also prints the token so you can copy it to GitHub Secrets if needed.)

You don't need to copy-paste anything into `.env` by hand — that manual step is exactly where this broke on 2026-05-29 (the helper printed a token but `.env` was never updated, so uploads kept using a stale, expired token). The script now does the write for you. Just confirm the line is there:

```bash
grep YOUTUBE_REFRESH_TOKEN .env
```

---

## Step 5b — Grant macOS Reminders permission (first run only)

`upload_to_youtube.py` creates a macOS Reminder ("Upload `<slug>` to TikTok" at 07:30) after every successful upload. The first time it runs, macOS will pop up a permission dialog: **"osascript wants to control Reminders"**. To grant this without burning a real upload:

```bash
python3 scripts/upload_to_youtube.py --test-reminder
```

Click **OK** on the permission dialog. A test reminder appears in the Reminders app — delete it once verified. All future uploads will create reminders silently.

## Step 6 — Test it

```bash
# Validate metadata without uploading
python3 scripts/upload_to_youtube.py facebook-marketplace-scam-uk --dry-run
```

Expected output:

```
slug:        facebook-marketplace-scam-uk
file:        facebook-marketplace-scam-uk.mp4 (29 MB)
title:       Facebook Marketplace Scams UK: 3 Warning Signs Before You Pay #Shorts
description: Spotted a bargain on Facebook Marketplace? Stop before you pay...
tags:        18 tag(s): Facebook Marketplace scam, ...
privacy:     unlisted (Education / Made for kids: NO)

(dry-run — metadata parsed OK, no upload performed)
```

If that's clean, run it for real:

```bash
# Upload as Unlisted — review in Studio before going public
python3 scripts/upload_to_youtube.py facebook-marketplace-scam-uk

# Or upload as Public immediately
python3 scripts/upload_to_youtube.py facebook-marketplace-scam-uk --public
```

The script will print the Shorts URL on success, then attempt to upload the brand-aligned thumbnail (1280×720 JPEG generated by `scripts/generate_video.py`) via `yt.thumbnails().set()`. Custom thumbnails require a phone-verified YouTube channel — if your channel isn't verified, this step 403s but the video upload itself stays successful. Verify the channel via Studio → Settings → Channel → Feature eligibility → Phone verification to unlock auto-thumbnail uploads. Finally, the script creates a **macOS Reminder** to upload to TikTok at 07:30 BST tomorrow (syncs to iPhone via iCloud).

---

## How it picks up metadata

The uploader reads `out/videos/{slug}.upload.md` and looks for the standard YouTube-shorts section blocks that `scripts/generate_video.py` writes alongside the MP4:

- `### Title (...)` followed by a fenced code block → video title
- `### Description (...)` followed by a fenced code block → description body
- `### Tags (...)` followed by a fenced code block → comma-separated tags

Everything from `## TikTok upload` onwards in the .upload.md is ignored, so TikTok-specific blocks don't bleed into the YouTube upload.

---

## Common gotchas

- **`invalid_grant` / "Token has been expired or revoked"** — this is the 7-day Testing-mode expiry. **Fixed permanently by publishing the app to Production** (Step 3.7) — production tokens don't expire. If you somehow still hit it, just re-run `scripts/get_youtube_refresh_token.py`; it re-mints the token and writes it straight into `.env` (no manual paste). Note: the `.env` token's file mtime doesn't change unless the script rewrites it, so if a re-auth "didn't take", check that the helper actually finished and wrote the new line (`grep YOUTUBE_REFRESH_TOKEN .env`).
- **Quota** — YouTube Data API gives you 10,000 units/day by default. An upload costs 1,600 units. So you can upload up to ~6 videos per day from this project before hitting the quota. More than enough for daily-cadence content.
- **Wrong channel** — if you've signed into a different Google account than the one that owns the Beat The Scam channel, the upload lands on the wrong channel. Sign out of other Google accounts in your default browser, OR use a private window for `get_youtube_refresh_token.py`.
- **The script worked locally but fails in CI later** — the `.env` file doesn't ship to GitHub Actions. When wiring this into a workflow, store `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and `YOUTUBE_REFRESH_TOKEN` as repository secrets and reference them via `env:` blocks.

---

## Future automation — GitHub Actions

Once it works locally, you can wire it into CI:

1. Add the three values to **Settings → Secrets and variables → Actions**.
2. Create `.github/workflows/daily-video.yml` that runs after `daily-publish.yml`, renders + uploads the slug.
3. Use `--public` if you're confident in the pipeline, or `--unlisted` (default) for a daily-review queue.

That's a follow-up — local upload is fine for daily cadence today.
