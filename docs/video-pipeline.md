# Beat The Scam — Video Production Handoff

> Single source-of-truth for the video pipeline. Pipeline rewrite landed 2026-05-22 — drop the Gemini-character workflow entirely; the new text-card pipeline is now canonical.
>
> **Last updated:** 2026-05-22
> **Videos published:** 5 (3 on the old Gemini workflow + HMRC + today's FB Marketplace + Hi Mum recreate)
> **Canonical pipeline:** `scripts/generate_video.py` (text cards, ElevenLabs Daniel V3, Pillow + MoviePy)

---

## 1. Project Overview

**Site:** https://beatthescam.com
**Repo:** https://github.com/siderightapps-hub/beatthescam-site
**Owner:** Alex (GitHub: `siderightapps-hub`)

**Social accounts:**
- Twitter/X: `@BeatTheScamUK`
- TikTok: `@BeatTheScamUK`
- YouTube: Beat The Scam (Brand Account under `siderightapps@gmail.com`)

**Emails:**
- Social/tools: `socialmedia@beatthescam.com`
- Dev/infra: `siderightapps@gmail.com`

---

## 2. ⚠️ Content Calendar — Start Every Session Here

### Published — what's already shipped

View counts last refreshed **2026-05-26**.

| # | Video | Slug | TikTok | YouTube Shorts | Twitter | Pipeline | Notes |
|---|---|---|---|---|---|---|---|
| 1 | ISP Impersonation Scams (BT, Sky, Virgin Media) | `isp-impersonation-scam-bt-sky-virgin-media` | ✅ (14) | ✅ (11) | ✅ | Old (Gemini) | Niche topic, low ceiling — leave as-is. |
| 2 | WhatsApp "Hi Mum" Scam (original) | `whatsapp-family-emergency-scam` | ✅ (1) | ✅ (175) | ✅ | Old (Gemini) | Old TikTok hook killed it (1 view); YouTube doing fine. Superseded on TikTok by row 5b. |
| 3 | Royal Mail Text Scam | `royal-mail-text-scam-uk` | ✅ (249) | ✅ (15) | ✅ | Old (Gemini) | Strong TikTok — leave as-is. |
| 4 | HMRC Tax Rebate Email Scam | `hmrc-tax-rebate-email-scam` | ✅ (255) | ✅ (210) | ✅ | **New (text cards)** | First proof-of-concept for the no-image pipeline. Best YouTube performer. |
| 5 | Facebook Marketplace Scam | `facebook-marketplace-scam-uk` | ✅ (268) | ✅ (1) | ✅ | **New (text cards)** | Validated text-card hook on TikTok (268 views). YouTube still finding its feet. |
| 5b | WhatsApp "Hi Mum" recreate (TikTok-only) | `whatsapp-family-emergency-scam` | ✅ (281) | (skip — original on YT works) | (existing) | **New (text cards)** | **Hypothesis validated — text-card recreate jumped from 1 → 281 TikTok views.** Same script + audio, different format. |
| 6 | Glastonbury Ticket Scam | `glastonbury-ticket-scam-uk` | ✅ (posted 2026-05-27) | ✅ (posted 2026-05-27) | (pending) | **New (ticket_resale family)** | First seasonal/topical render. Glasto starts 24 June. Backfill view counts ~29 May to validate seasonal+topical hypothesis (TikTok 48h target: 300+; YT 7-day target: 100+). |
| 7 | Fake Festival Ticket Scam (generic) | `fake-festival-ticket-scam-uk` | ✅ (posted 2026-05-28) | ✅ (posted 2026-05-28) | (pending) | **New (ticket_resale family)** | Wide-net companion to row 6 — Reading, Leeds, Wireless, Parklife, TRNSMT, Latitude, Boomtown. Tests whether second-tier festivals get more reach going wide vs per-festival. |
| 8 | Festival camping gear (Vinted) scam | `festival-camping-equipment-vinted-scam` | ✅ (posted 2026-05-29) | ✅ (posted 2026-05-29) | ✅ (auto, 28 May) | **New (marketplace family)** | Article auto-published 28 May, video shipped 29 May. First render after the marketplace verify copy was made platform-agnostic + topic shortened to "festival gear". YT: youtube.com/shorts/I_00psb_Ft0 |

### Next 14 days — summer schedule

All videos pulled from articles **already published** on the site. Hook copy is auto-handled by the topic-family classifier in `scripts/generate_video.py`. Render one per day with:

```bash
python3 scripts/generate_video.py <slug>
python3 scripts/upload_to_youtube.py <slug>
# Then upload to TikTok manually using the .upload.md
```

| Day | Slug | Topical hook | Family |
|---|---|---|---|
| Mon 26 May | `glastonbury-ticket-scam-uk` | Glasto −28 days | `ticket_resale` ✅ shipped 27 May (TT + YT) |
| Tue 27 May | `fake-festival-ticket-scam-uk` | Generic festival cover (Reading, Leeds, Wireless, Parklife, TRNSMT) | `ticket_resale` ✅ shipped 28 May (TT + YT) |
| Wed 28 May | `festival-camping-equipment-vinted-scam` | Subbed in for airbnb — freshest seasonal article | `marketplace` ✅ shipped 29 May (TT + YT) |
| Thu 29 May (today) | `airbnb-scam-uk-listings` | Staycation season builds (carried over) | `marketplace` |
| Fri 30 May | `viagogo-scam-uk` | Resale platform peak | `ticket_resale` |
| Sat 31 May | `stubhub-ticket-scam-uk` | Same | `ticket_resale` |
| Sun 1 Jun | `concert-ticket-scam-uk-2026` | Wider net — any UK arena gig | `ticket_resale` |
| Mon 2 Jun | `fake-airline-ticket-scam-uk` | Travel season ramp | `ticket_resale` |
| Tue 3 Jun | `rightmove-rental-scam-uk` | Summer rental fraud peak | `marketplace` |
| Wed 4 Jun | `holiday-let-scam-uk` | Same | `marketplace` |
| Thu 5 Jun | `package-holiday-scam-uk` | TUI/Jet2 wave | `message` |
| Fri 6 Jun | `passport-renewal-scam-uk` | Pre-travel admin anxiety | `message` |
| Sat 7 Jun | `ukvi-visa-scam-uk` | Same | `message` |
| Sun 8 Jun | `visa-application-scam-uk` | Same | `message` |
| Mon 9 Jun | (pick from new queue articles by then) | New seasonal content | varies |

### Deferred — autumn/winter slots

Original calendar items deprioritised until autumn 2026 (low summer search intent):

- Police Impersonation Scam Call
- QR Code Parking Scam
- DVLA Vehicle Tax Text Scam
- PayPal Email Scam (year-round, but plenty of other topical content first)
- Puppy Scam UK
- Bank Impersonation Phone Scam
- Pig Butchering / Tinder Investment Scam

**Posting schedule:** Daily (Mon–Sun, one video per day — changed from M/W/F on 2026-05-22)
**Best time:** 07:30–09:00 UK BST
**Today's render:** see the "Today" row above. The 14-day plan is published-article-driven; the daily-publish queue is separately filling the catalogue with new seasonal articles (Glastonbury accommodation → festival camping → Reading tickets → Wimbledon → F1 → airport transfer → TUI → Jet2 → holiday compensation → solar panel → driveway cowboy → bank holiday parcel → wedding venue → wedding photographer) so by mid-June this calendar can extend with fresh content too.

---

## 3. The new pipeline (canonical from 2026-05-22)

### One-command render

```bash
cd ~/Projects/websites/beatthescam-site
python3 scripts/generate_video.py <slug>
```

That single command does **everything**: pulls the article from `content/posts.json`, generates 8 text cards (Pillow), synthesises 8 voice clips (ElevenLabs Daniel V3), assembles via MoviePy with Ken Burns + crossfades, encodes a 1080×1920 H.264 MP4 at ~45s runtime, **and renders a brand-aligned 1280×720 thumbnail JPEG**.

Outputs:

```
out/videos/<slug>.mp4              # 1080×1920, 30fps, ~25-30 MB (the deliverable)
out/videos/<slug>.thumbnail.jpg    # 1280×720, JPEG ~65 KB (auto-uploaded by upload_to_youtube.py)
out/videos/<slug>-frames/          # PNG per scene (visual debug)
out/videos/<slug>-audio/           # MP3 per scene (audio debug)
out/videos/<slug>.upload.md        # hand-written upload metadata (currently manual)
```

`out/` is gitignored — videos never ship to Netlify or git.

### One-command upload to YouTube Shorts

```bash
# After OAuth one-time setup (see docs/youtube-upload-setup.md):
python3 scripts/upload_to_youtube.py <slug>             # Unlisted (review in Studio)
python3 scripts/upload_to_youtube.py <slug> --public    # Public immediately
python3 scripts/upload_to_youtube.py <slug> --dry-run   # Validate metadata, don't upload
python3 scripts/upload_to_youtube.py --test-reminder    # First-run: grant macOS Reminders permission
```

Reads `out/videos/<slug>.upload.md` for title / description / tags. Auto-sets category=Education, language=en-GB, made-for-kids=NO. After video upload succeeds, **also auto-uploads the brand thumbnail** via `yt.thumbnails().set()` (requires phone-verified YouTube account — fails non-fatally if not verified, video upload itself remains successful), and **creates a macOS Reminder** titled "Upload <slug> to TikTok" scheduled for 07:30 BST tomorrow (syncs to iPhone via iCloud).

### TikTok upload (still manual)

TikTok's Content Posting API requires app approval, which isn't worth it at current volume. Workflow per video:

1. Open the MP4 in macOS Quick Look, end-to-end check
2. AirDrop / iCloud the file to phone OR upload via tiktok.com web
3. Paste caption + hashtags from `out/videos/<slug>.upload.md` "TikTok upload" section
4. Cover: pick the hook frame (red bar) or a strong sign frame
5. Music: add TikTok's "Breaking News" commercial sound (same as HMRC — adds production polish)
6. Toggle: AI-generated content **ON**, Allow Duet/Stitch ON, Public
7. Post → immediately pin the first comment from the upload.md template

---

## 4. Storyboard — 8 scenes per video

Hardcoded in `scripts/generate_video.py` (`build_scripts()`). All cards use the brand palette: navy `#0b1220` background, accent blue `#3a86ff`, alert red `#ff5c5c`.

| # | Scene | Eyebrow | Duration | Content |
|---|---|---|---|---|
| 1 | Hook | "SCAM ALERT" (red) | ~5s | Topic-family-specific hook (see Section 5) |
| 2 | Promise | "IN THIS SHORT" | ~4s | Big "3" + "warning signs to spot" |
| 3 | Sign 1 of 3 | "SIGN 1 OF 3" | ~6s | First warning from article section 2 |
| 4 | Sign 2 of 3 | "SIGN 2 OF 3" | ~6s | Second warning |
| 5 | Sign 3 of 3 | "SIGN 3 OF 3" | ~6s | Third warning |
| 6 | Verify | "DO THIS INSTEAD" | ~6s | Topic-family-specific verify advice |
| 7 | CTA | "FULL GUIDE AT" | ~3s | Full article title + beatthescam.com |
| 8 | End card | (static) | 4.5s | `assets/video/end-card.png` + "Remember — Beat the Scam." |

Each card has 4% Ken Burns zoom across its duration; 0.35s CrossFadeIn between cards.

---

## 5. Topic-family templates (`HOOK_TEMPLATES`)

`scripts/generate_video.py` classifies each slug into a topic family and picks topic-correct hook + verify copy. Slug → family map in `SLUG_FAMILIES`; copy in `HOOK_TEMPLATES`. Default family is `message` (the proven HMRC template — never change without evidence).

| Family | Used for | Hook copy | Verify copy |
|---|---|---|---|
| `message` (default) | HMRC, DVLA, NCSC, Royal Mail, TV Licensing, banks, generic phishing | "Got a {topic} message? Don't tap that link." | "Verify through the official site yourself — never via the link." |
| `marketplace` | Facebook Marketplace, eBay, Vinted, Gumtree, Shpock, Depop | "Spotted a {topic} bargain? Stop — it might be a scam." | "Pay through Marketplace. Never bank transfer to a stranger." |
| `family_message` | WhatsApp Hi Mum / new-number / family-emergency | `'Hi Mum, I've lost my phone — can you send £200?' Stop.` | "Call your family on their old number. Don't send a penny yet." |
| `call` | Bank impersonation calls, police impersonation, courier fraud | "A {topic} call asking you to move money? Hang up." | "Hang up. Call your bank back on the number from your card." |

To add a new family: extend both `HOOK_TEMPLATES` and `SLUG_FAMILIES`. Each template can use `{topic}`, `{n}`, `{sign_word}` placeholders.

---

## 6. Pinned configuration (don't change without intention)

| Setting | Value | Where |
|---|---|---|
| Voice | **Daniel** — `3WqHLnw80rOZqJzW9YRB` | `scripts/generate_video.py` constant |
| Model | `eleven_v3` | constant |
| Resolution | 1080 × 1920 | `W, H` constants |
| Frame rate | 30 fps | `FPS` |
| Background | `#0b1220` (matches site theme) | `BG` |
| Accent | `#3a86ff` (brand blue) | `ACCENT` |
| Alert | `#ff5c5c` (red for hook) | `ALERT_RED` |
| Catchphrase | "Remember — Beat the Scam." (declarative period, NOT exclamation) | end-card scene |
| End-card min duration | 4.5s | scene definition |
| Warning trim max | 90 chars | `shorten_warning()` default |
| Music level | -20 dB (factor 0.1) | `build_video()` |

Changeable via env vars: `ELEVENLABS_API_KEY` (required), `ELEVENLABS_VOICE_ID` (override), `ELEVENLABS_MODEL_ID` (override).

Changeable via CLI: `--no-music`, `--music PATH`, `--out-dir DIR`.

---

## 7. The `shorten_warning()` trim function

Article warning sentences are often too long for cards. The trim cascades through these steps:

1. **Drop parentheticals** `(e.g., ...)`
2. **Drop em-dash continuations** `main point — elaboration`
3. **Drop `using/via/by/through X, Y, Z` lists** (2+ items) — fixed FB Marketplace sign 3's `"...using bank…"` bug
4. **Drop quoted examples + their lead-in** — `"like 'X' or 'Y'"` strings
5. **Cut at latest clause boundary** within 90 chars — accepts commas, semicolons, OR connector words (`but / and / or / so / within / during / after / before / throughout / around`) — fixed Hi Mum's `"didn't expect…"`, `"about the new…"`, `"to an urgent…"` bugs
6. **Never cut mid-phrase.** If no clean clause boundary exists, **return the full original sentence intact** rather than ellipsis-truncate. The pre-2026-05-22 word-boundary-plus-ellipsis fallback (`"bank…"` / `"didn't expect…"`) was deleted entirely — there is no longer any code path that produces a mid-phrase cut. Trade-off: slightly longer audio per scene in the rare case a warning has no clause boundaries within 90 chars. Acceptable because (a) all observed warnings cut cleanly at clause boundaries, and (b) viewer comprehension > millimetre runtime savings.

Output is used for BOTH on-card display text AND voiceover speech.

---

## 8. Editorial guardrails (don't repeat these mistakes)

Lessons from prior sessions — explicit so future Claude sessions don't regress:

1. **Don't re-add a named editor pseudonym.** Earlier session invented "James Carter" as a fabricated UK consumer-affairs editor. We retired that and use Organization byline ("Beat the Scam Editorial Team"). Fabricated bylines are explicitly penalised under Google's YMYL E-E-A-T guidance. Only add a named editor if the user provides a real person with real credentials.
2. **Don't add phonetic overrides for HMRC / DVLA / NCSC.** We tried `H. M. R. C.` (V3 elided the R), then `aitch em are see` (too rushed). Settled on bare `HMRC` — V3 handles common UK acronyms natively. Re-adding overrides regresses.
3. **Don't switch the catchphrase to exclamation.** "Beat the Scam!" sounded too energetic. Declarative period preferred.
4. **Don't change voice ID without asking.** Daniel was chosen after A/B against Grace.
5. **Don't ship videos to `dist/`.** They'd auto-deploy to Netlify and bloat the site. Output lives at `out/videos/` (gitignored).
6. **Don't push uncommitted changes.** User explicitly asked for "commit and one push" — default is local-only until the user asks for the push.

---

## 9. Music bed — current state

- **Active slot:** `assets/audio/news-bed.mp3` — **empty** (no file)
- **Behaviour when empty:** voice-only render, no music
- **Two candidates rejected so far:** one too cinematic, one too sleepy. Both kept in `assets/audio/candidates/` for reference.
- **TikTok workaround:** add TikTok's "Breaking News" commercial sound in the upload editor. Commercial-cleared for TikTok use only.
- **YouTube workaround:** uploads silent (voice-only) until a track is dropped at `assets/audio/news-bed.mp3` and videos are re-rendered.

**Active search strategy** for finding a workable track:
- YouTube Audio Library: Mood = "Dark", Genre = "Electronic" or "Cinematic"
- Pixabay search terms: `documentary tension`, `investigation`, `cybersecurity`
- Target: "vigilant, deliberate, investigative — not alarmist"
- Or: generate via Lyria / MusicFX with the same brief

---

## 10. Analytics — what's working so far

As of 2026-05-22:

| Video | Platform | Views | Notes |
|---|---|---|---|
| HMRC Tax Rebate (new pipeline) | YouTube Shorts | **210** | Best performer — proves the text-card format. |
| WhatsApp Hi Mum (old Gemini) | YouTube Shorts | 175 | Content is good — TikTok hook killed it on TT (1 view). Today's recreate uses the new pipeline. |
| WhatsApp Hi Mum (old Gemini) | TikTok | 1 | Object first-frame killed retention. Recreated today with text-card hook. |
| ISP/BT/Sky/Virgin (old Gemini) | YouTube | 9 | Niche topic, decent retention, low reach. |
| ISP/BT/Sky/Virgin (old Gemini) | TikTok | 14 | Same. |
| Royal Mail (old Gemini) | TikTok | 234 | Original surprise hit. |

**Key insight:** the new text-card pipeline (HMRC: 210 YT views) significantly outperforms the old Gemini-character pipeline (ISP: 9 YT views). Hypothesis being tested today with FB Marketplace + Hi Mum recreate: text-card format = better TikTok retention than character images.

---

## 11. Cost per video (current)

- **ElevenLabs:** ~$0.055/video on Creator tier (~30 chars/card × 8 cards = ~240 chars/video; tier gives 100,000 chars/month = ~400 videos)
- **Local CPU:** ~45s on M-series MacBook Air
- **GPU:** none needed
- **Storage:** ~30 MB per video, all in `out/videos/` (gitignored)
- **YouTube API quota:** 1,600 units per upload, daily limit 10,000 units = ~6 uploads/day (more than enough for daily cadence)

---

## 12. Hashtag templates

**Standard tags (every video):** `#ScamAlert #UKScam #ScamAwareness #FraudAlert #BeatTheScam`

**Category-specific add-ons:**

| Category | Tags |
|---|---|
| SMS/Text | `#TextScam #SMSScam #DeliveryScam` |
| Phone | `#PhoneScam #VishingUK` |
| Email | `#EmailScam #PhishingUK` |
| Government | `#HMRCScam #DVLAScam #GovScam` |
| WhatsApp | `#WhatsAppScam #HiMumScam #NewNumberScam` |
| Marketplace | `#FacebookMarketplace #MarketplaceScam #OnlineShopping` |
| Banking | `#BankScam #BankFraud` |
| Tech | `#TechScam #RemoteAccess` |

**TikTok hashtag strategy** (10 tags total):
- 3 broad/discovery: `#fyp #scamalert #ukscam`
- 3 topic-specific
- 2 brand: `#beatthescam #scamawareness`
- 2 audience: `#ukconsumer #fraudprevention` (or `#parentsoftiktok` for family-message videos)

**TikTok pinned first comment — HARD 150-character limit.** TikTok truncates comments at 150 characters (YouTube has no such limit, so YT pinned comments can be longer). When drafting the `### Pinned first comment` block in a `.upload.md`, count the characters and keep it ≤150 including spaces, emoji and the `beatthescam.com` mention. This bit us on the Glastonbury and festival videos where the first drafts ran 160–165 chars and had to be re-cut. Quick check before handing the comment over:

```bash
python3 -c "print(len('''💬 Save this before festival season. Pay ONLY through buyer protection — never bank transfer. beatthescam.com — full guide in bio.'''))"
```

If it prints >150, trim. Drop the leading emoji first (saves ~2), then shorten the CTA ("full guide in bio" → "guide in bio").

### Instagram Reels (third platform — paste-ready, manual for now)

Every `.upload.md` should carry an `## Instagram Reels` section after the TikTok block. **The same MP4 works unchanged** — 1080×1920 / 9:16 / ~45s *is* the Reels spec, so there's no re-render. The YouTube uploader ignores everything that isn't its own `### Title`/`### Description`/`### Tags` blocks, so an Instagram section is parser-safe (don't reuse those three heading labels inside it — use `### Caption` / `### Settings` / `### Pinned first comment` like TikTok).

Instagram-specific rules when drafting the Reels caption:
- **Front-load the hook** — only the first ~125 chars show before the "… more" fold. Lead with the question/red-flag, not hashtags.
- **Hashtags: 3–5, in the caption.** The "30 hashtags" era is over; Instagram itself now recommends 3–5 relevant tags. Use brand + topic (e.g. `#vintedscam #festivalscam #ukscams #scamawareness #fraudprevention`).
- **No clickable links** in captions → CTA stays "link in bio" (same constraint as TikTok).
- **Audio for reach:** Reels favours trending audio. Either add a trending track at low volume in-app (so the voiceover still reads) or keep original audio. Watch commercial-use limits as with TikTok's "Breaking News" sound.
- **Cover:** reuse the hook frame or the 1280×720 thumbnail.
- **Posting:** manual via the IG app, or schedule free in **Meta Business Suite** (needs the account linked to a Facebook Page). Full Graph API auto-publish is deferred — it needs Meta app review for `instagram_content_publish` and pulls the video from a public URL, so the MP4 would have to be hosted. Same defer-until-cadence-justifies call we made for TikTok.

Status: **`@beatthescamuk` Instagram is LIVE as of 2026-05-30** — Creator account, profile pic (favicon mark), bio link to beatthescam.com, 4 Reels seeded (Facebook Marketplace, Glastonbury tickets, festival tickets, festival gear). Worked example with the Reels block: `out/videos/festival-camping-equipment-vinted-scam.upload.md`.

---

## Cross-platform analytics review — queued for next session

The site now publishes the **same 1080×1920 MP4** to three platforms off one render: **YouTube Shorts** (auto, via `upload_to_youtube.py`), **TikTok** (manual), **Instagram Reels** (manual). That makes the next analytics review the first like-for-like cross-platform comparison we've had — and it lines up with the open first-second-retention question we parked.

What to pull when there's ~7 days of post-publish data:

| Platform | Where | Key metrics |
|---|---|---|
| YouTube Shorts | YouTube Studio → Content → individual Short → Analytics | Views, average view duration, **% viewed**, watch time |
| TikTok | TikTok app → Analytics (requires Creator/Pro account, free) → individual video | Views, average watch time, **completion rate**, full-video views |
| Instagram Reels | Instagram app → Insights on each Reel (Creator-account-only) | Plays, **initial plays (= first-second retention proxy)**, accounts reached, watch time |
| X / Twitter | analytics.twitter.com → per-post View analytics (manual — free API tier doesn't expose this) | Impressions, link clicks, engagement rate |

Note on X specifically: free X API v2 (which `tweet_new_articles.py` uses) is **post-only** — no programmatic analytics access. Tweet metrics require Basic tier ($100/mo+). At our scale the right call is **manual pull from the native dashboard** alongside the video numbers, not paid API.

The retention question to answer: *if all three platforms show heavy first-second drop-off, the hook is the problem (test alternative openers — kinetic text reveal, shocking-number open, curiosity-gap question); if Reels holds better than Shorts/TikTok, it's audience/platform fit and we double down on Reels-first creative.*

---

## 13. Open follow-ups

- [ ] **Find a working music bed.** Two rejections; current state is voice-only. Acceptable but limits feel.
- [ ] **Auto-generate `.upload.md` files via Claude API.** Currently hand-written. A small Claude Haiku call (~$0.001 each) could draft title/description/tags from the post + render duration.
- [ ] **GitHub Actions workflow `daily-video.yml`** — render + upload the latest daily-publish slug automatically. Depends on YouTube OAuth secrets being added to the repo.
- [ ] **TikTok automated upload.** Requires either the Content Posting API (app approval needed) or a third-party scheduler (Buffer / Publer / Postiz). Defer until content cadence justifies.
- [ ] **Per-video music bed by category.** Calm for "info", urgent for "alert", investigative for "fraud" — once 3-5 trusted tracks exist.
- [ ] **Burned-in subtitles.** TikTok auto-captions on upload work; on-card text already covers silent viewers. Worth doing if accessibility audit flags it.

---

## 14. Quick commands cheat-sheet

```bash
# Navigate
cd ~/Projects/websites/beatthescam-site

# Render a video (any slug from posts.json)
python3 scripts/generate_video.py facebook-marketplace-scam-uk
python3 scripts/generate_video.py facebook-marketplace-scam-uk --no-music

# A/B test a different voice
ELEVENLABS_VOICE_ID=oWAxZDx7w5VEj9dCyTzz python3 scripts/generate_video.py <slug>

# Upload to YouTube Shorts
python3 scripts/upload_to_youtube.py <slug> --dry-run     # validate metadata
python3 scripts/upload_to_youtube.py <slug>               # Unlisted
python3 scripts/upload_to_youtube.py <slug> --public      # Public immediately

# One-time YouTube OAuth setup
python3 scripts/get_youtube_refresh_token.py

# Tweet an article (existing pipeline)
python3 scripts/tweet_new_articles.py --slug <slug>
python3 scripts/tweet_new_articles.py --slug <slug> --dry-run

# Build the site (separate concern — not video)
python3 scripts/build.py
```

---

## 15. Worktree `.env` note

Git worktrees each have their own local `.env` since the file is gitignored. Two clean options to keep them in sync:

```bash
# Option A: symlink in each new worktree
cd <worktree>
ln -s ../../../.env .env

# Option B: shell helper in ~/.zshrc
worktree-env() { cp ~/Projects/websites/beatthescam-site/.env .env; }
```

Either works. Not implemented automatically — pick one once and stick with it.

---

## 16. Next-session checklist

When starting a new video session:

- [ ] Review Section 2 (Content Calendar) — which video is next?
- [ ] Run `python3 scripts/generate_video.py <slug>`
- [ ] Open the MP4 (`out/videos/<slug>.mp4`) and watch end-to-end
- [ ] Check the hook frame is on-brand (`out/videos/<slug>-frames/01-hook.png`)
- [ ] Upload to YouTube: `python3 scripts/upload_to_youtube.py <slug>`
- [ ] Upload to TikTok manually (`out/videos/<slug>.mp4` → tiktok.com web)
- [ ] Use TikTok's "Breaking News" commercial sound
- [ ] Toggle AI-generated content ON on both platforms
- [ ] Paste the first pinned comment from `out/videos/<slug>.upload.md`
- [ ] Tweet: `python3 scripts/tweet_new_articles.py --slug <slug>`
- [ ] Update Section 2 calendar with ✅
- [ ] Watch 1h / 24h / 48h analytics — compare retention curve to HMRC's

---

*Last updated: 2026-05-22. Replaces the previous Gemini-character-image workflow entirely. Paste this whole file into a new Claude chat to bootstrap video production work.*
