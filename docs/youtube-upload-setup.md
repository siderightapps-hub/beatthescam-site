# YouTube Shorts auto-upload — one-time OAuth setup

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
6. Summary → Back to dashboard. Publishing status will stay "Testing" — that's fine for a single-user tool. The token doesn't expire while the app is in Testing as long as you re-mint it before the 7-day refresh-token expiry window. (See step 6 if you ever need to refresh.)

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
- Print the refresh token to your terminal.

Add the printed token to `.env`:

```bash
YOUTUBE_REFRESH_TOKEN=<paste from terminal>
```

---

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

The script will print the Shorts URL on success.

---

## How it picks up metadata

The uploader reads `out/videos/{slug}.upload.md` and looks for the standard YouTube-shorts section blocks that `scripts/generate_video.py` writes alongside the MP4:

- `### Title (...)` followed by a fenced code block → video title
- `### Description (...)` followed by a fenced code block → description body
- `### Tags (...)` followed by a fenced code block → comma-separated tags

Everything from `## TikTok upload` onwards in the .upload.md is ignored, so TikTok-specific blocks don't bleed into the YouTube upload.

---

## Common gotchas

- **`invalid_grant` after a few weeks** — Google rotates refresh tokens for "Testing" OAuth apps after 7 days of non-use. If your refresh token expires, just re-run `scripts/get_youtube_refresh_token.py` and update `.env`. Or move the OAuth app to "In production" (you'd need verification for that, not worth it for a single-user tool).
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
