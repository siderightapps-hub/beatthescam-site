# Beat The Scam — Video Production Handoff
> Use this file to initialise a new Claude chat for video production.
> Last updated: 2026-05-16 | Videos published: 3

---

## 1. Project Overview

**Site:** https://beatthescam.com
**Repo:** https://github.com/siderightapps-hub/beatthescam-site
**Owner:** Alex (GitHub: siderightapps-hub)

**Social accounts:**
- Twitter/X: @BeatTheScamUK
- TikTok: @BeatTheScamUK
- YouTube: Beat The Scam (Brand Account under siderightapps@gmail.com)

**Emails:**
- Social/tools: socialmedia@beatthescam.com
- Dev/infra: siderightapps@gmail.com

---

## 2. ⚠️ Content Calendar — Start Every Session Here

### Current status (update this each session)

| # | Video | TikTok | YouTube Shorts | Twitter |
|---|---|---|---|---|
| 1 | ISP Impersonation Scams (BT, Sky, Virgin Media) | ✅ | ✅ | ✅ |
| 2 | WhatsApp "Hi Mum" Scam | ✅ | ✅ | ✅ |
| 3 | Royal Mail Text Scam | ✅ | ✅ | ✅ |
| 4 | HMRC Tax Refund Scam | ⬜ | ⬜ | ⬜ |
| 5 | Facebook Marketplace Scam | ⬜ | ⬜ | ⬜ |
| 6 | Police Impersonation Scam Call | ⬜ | ⬜ | ⬜ |
| 7 | QR Code Parking Scam | ⬜ | ⬜ | ⬜ |
| 8 | DVLA Vehicle Tax Text Scam | ⬜ | ⬜ | ⬜ |
| 9 | PayPal Email Scam | ⬜ | ⬜ | ⬜ |
| 10 | Puppy Scam UK | ⬜ | ⬜ | ⬜ |
| 11 | Bank Impersonation Phone Scam | ⬜ | ⬜ | ⬜ |
| 12 | Pig Butchering / Tinder Investment Scam | ⬜ | ⬜ | ⬜ |

**Posting schedule:** Daily (Mon–Sun, one video per day — changed from M/W/F on 2026-05-22)
**Next video:** HMRC Tax Refund Scam

---

## 3. Video Production Workflow

### Step 1 — Script
Tell Claude which article to use. Claude will:
- Pull the article content from posts.json
- Verify all statistics against live sources
- Generate a timed script (30s or 60s)
- Confirm all stats are verified before proceeding

**Script format:**
```
[HOOK — 3 sec] Opens with shocking/relatable statement
[PROBLEM — 8 sec] Context, verified UK statistics, named sources
[RED FLAG 1 — 4 sec] Specific, visual red flag
[RED FLAG 2 — 4 sec] Specific, visual red flag
[RED FLAG 3 — 4 sec] Specific, visual red flag
[CTA — 7 sec] Action + beatthescam.com + link in bio
```

### Step 2 — Audio (ElevenLabs)
- Account: socialmedia@beatthescam.com
- Plan: Starter ($6/month)
- Voice: Daniel — British Male (changed from Grace, 2026-05)
- Paste script → generate → download MP3
- Two generations produced — pick the better one
- Target: 43–58 seconds audio

### Step 3 — Images (Gemini)
Claude provides exact prompts for each clip.

**⚠️ Critical rules for Gemini prompts:**
- Always ask Gemini for UK-specific setting details
- UK plug sockets, radiators, terraced houses through windows
- Newspapers: Guardian, Daily Mail
- Mugs: PG Tips, Union Jack
- **FIRST CLIP MUST BE A HUMAN FACE showing emotion** — not an object
- Keep character consistent across all clips (same person, same setting)
- If Gemini blocks a prompt (scam text content), rephrase and add the text as a CapCut overlay instead

### Step 4 — CapCut Assembly
1. Import audio + images
2. Add auto-captions
3. Add background music at **-20dB**
4. **Hard cuts between clips** (no fades between clips)
5. Fade in at very start (0.3s), fade into end card only
6. Add on-screen text overlays for key stats/red flags
7. Add Ken Burns slow zoom on any clip held for 10+ seconds
8. End card: `beatthescam-tiktok-endcard.png` (already generated)

**Clip timing process:**
- Listen to audio and note exact timestamps for each section
- Give timestamps to Claude → Claude gives exact duration per clip

### Step 5 — Export & Upload

**TikTok:**
- Export from CapCut to camera roll (never use CapCut's direct share)
- Upload manually from camera roll
- Add caption + hashtags (Claude provides these)
- Toggle: AI-generated content ON
- Pin first comment immediately after posting

**YouTube Shorts:**
- Upload same MP4 file
- Claude provides: title, description, tags
- Settings: Education category, Not made for kids, Altered content YES, Public
- Add related video (link to most relevant previous Short)

**Twitter/X:**
```bash
python3 scripts/tweet_new_articles.py --slug [article-slug]
```
Run from beatthescam-site folder on Mac.

---

## 4. Key Lessons Learned

### Hook rule (most important)
**First frame = human face showing emotion.**
Videos opening with objects (phone on table, router) get 1-3 second average watch time.
Videos opening with a person's face get 10-20 second average watch time.
Always start with the "concerned person" clip, not the "object" clip.

### Script length
- 30-second script generates ~43-58 seconds of audio at natural pace
- Don't fight it — use it as a 60-second video
- TikTok and YouTube Shorts both support up to 60 seconds

### Statistics rule
All stats must be verified before inclusion. Claude checks each one against:
- Action Fraud / reportfraud.police.uk
- FCA (fca.org.uk)
- NCSC (ncsc.gov.uk)
- UK Finance (ukfinance.org.uk)
- Which? (which.co.uk)
- Named surveys with methodology

Never use unverified figures. If a stat can't be verified, describe the pattern without a number.

### Audio levels
- Voiceover: 0dB
- Background music: -20dB
- Sound effects: -15dB

### Posting timing
Best time to post: **07:30–09:00 UK BST**
Post **daily** (Mon–Sun) for consistent algorithmic signals — daily cadence is generally rewarded more than every-other-day on both TikTok and YouTube Shorts.

---

## 5. Analytics Benchmarks (as of 2026-05-16)

| Video | Platform | Views | Avg Watch | Notes |
|---|---|---|---|---|
| ISP Scam | YouTube Shorts | 6 | 0:49 (103%) | Excellent retention, low reach |
| WhatsApp Hi Mum | YouTube Shorts | 171 | 0:09 (16.5%) | Good reach, weak hook |
| Royal Mail | TikTok | 234 | 3.25s | Good reach, weak hook (object first frame) |

**Key insight:** Retention matters more than views at this stage. The ISP video's 103% retention (people replaying) is the strongest signal — YouTube will keep distributing it.

---

## 6. File Locations

| File | Location |
|---|---|
| End card (TikTok/Shorts) | `beatthescam-tiktok-endcard.png` — already in Claude outputs |
| Twitter/X profile picture | `beatthescam-logo-twitter-profile-400px.png` |
| YouTube banner | `beatthescam-youtube-banner.png` |
| YouTube profile picture | `beatthescam-logo-youtube-profile-800px.png` |
| OG image (site) | `/assets/og-image-v2.png` in repo |

---

## 7. Automation Running

| Automation | Schedule | Status |
|---|---|---|
| Daily article publish (5/day from queue) | 06:15 UTC daily | ✅ Running |
| Search Console article generator | 06:30 UTC daily | ✅ Running |
| Twitter auto-poster (on publish) | Triggered by SC pipeline | ✅ Running |

**Search Console pipeline:**
- Pulls trending queries → finds content gaps → generates article via Claude API
- Adds to posts.json → rebuilds site → commits → Netlify deploys → tweets
- Fully automated — no manual intervention needed

---

## 8. Hashtag Templates

**Standard tags (all videos):**
`#ScamAlert #UKScam #ScamAwareness #FraudAlert #BeatTheScam`

**Category tags:**
| Category | Tags |
|---|---|
| SMS/Text | `#TextScam #SMSScam #DeliveryScam` |
| Phone | `#PhoneScam #VishingUK` |
| Email | `#EmailScam #PhishingUK` |
| Government | `#HMRCScam #DVLAScam #GovScam` |
| WhatsApp | `#WhatsAppScam #HiMumScam` |
| Marketplace | `#FacebookMarketplace #OnlineScam` |
| Banking | `#BankScam #BankFraud` |
| Tech | `#TechScam #RemoteAccess` |

**First pinned comment template:**
```
💬 Share this with [target audience]. [Single protective action]. beatthescam.com — full guide in bio.
```

---

## 9. Quick Commands

```bash
# Navigate to repo
cd ~/Projects/websites/beatthescam-site

# Pull latest
git pull origin main

# Tweet a specific article
python3 scripts/tweet_new_articles.py --slug [slug-here]

# Preview tweet without posting
python3 scripts/tweet_new_articles.py --slug [slug-here] --dry-run

# Check Search Console gaps (dry run)
python3 scripts/search_console_articles.py --dry-run

# Build site locally
python3 scripts/build.py

# Commit and push
git add -A && git commit -m "Message" && git push origin main
```

---

## 10. Next Session Checklist

When starting a new video session:

- [ ] Review Section 2 (Content Calendar) — which video is next?
- [ ] Ask Claude to generate the script for that video
- [ ] Confirm all stats are verified before generating audio
- [ ] Generate audio in ElevenLabs (Daniel voice)
- [ ] Get Gemini prompts from Claude — remember first frame = human face
- [ ] Assemble in CapCut — hard cuts, -20dB music, Ken Burns on long clips
- [ ] Export to camera roll
- [ ] Upload to TikTok (AI content label ON)
- [ ] Upload to YouTube Shorts (Altered content YES)
- [ ] Tweet: `python3 scripts/tweet_new_articles.py --slug [slug]`
- [ ] Pin first comment on TikTok and YouTube
- [ ] Update Section 2 calendar with ✅

---

*Last updated: 2026-05-16. Paste this file into a new Claude chat to continue video production from where you left off.*
