# Beat The Scam — Master Project Document

> The single, authoritative source-of-truth document for the **Beat The Scam** brand, site, infrastructure, monetisation, security, content operations, growth strategy, and ongoing roadmap.
>
> **Audiences this document serves:**
> 1. The current owner (Alex / SideRight Apps) — operational manual.
> 2. Any new Claude Code chat session — drop-in context bootstrap (works alongside `CLAUDE.md`).
> 3. Potential buyers / acquirers — full due-diligence briefing on the asset.
> 4. Contractors, future editors, security reviewers — onboarding pack.
>
> **Last updated:** 2026-07-10
> **Domain age:** ~5 months (registered February 2026)
> **Site state:** 181 guides published (grows ~1/day via the gated cron, net of occasional consolidations — see `docs/content-diversification-plan.md` for the current count), 17 normalised categories, AI checker live (durable rate limit + daily spend cap), newsletter live (Resend, **double opt-in** + signed one-click unsubscribe), UK/EEA ad+analytics consent via Google's certified CMP, llms.txt + security.txt deployed, full UK Terms (E&W + Scotland + NI), named author E-E-A-T (Alex Bacsa) with cross-publication identity (CloudFintech + Tuning Digital + SalesTap + LinkedIn). **Video production (YouTube Shorts + TikTok + Instagram Reels) was discontinued 2026-06-15** — it built neither domain authority nor backlinks; see `docs/video-pipeline.md`. Semrush Site Health **98%**, AI Search Health **99%**, Lighthouse mobile Performance **92–97** / Accessibility **95–98** / Best Practices **92** / SEO **100** across homepage, guide, author pages. ~191 residual Semrush warnings all from Google's AdSense CDN (irreducible third-party floor). **Technical build is mature and stable.** Editorial accuracy is now defence-in-depth: autonomous publishing is gated (deterministic + LLM judge), reporting routes are validated against a verified source canon (`content/sources.json`), every guide carries a claim manifest (`content/manifests/`), and a weekly audit digest surfaces flag-tier claims for human review — see the content-accuracy section.
> **Maintainer:** Alex — SideRight Apps (GitHub: `siderightapps-hub`)

---

## Table of Contents

1. [Brand & Project Overview](#1-brand--project-overview)
2. [Ownership, Contacts & Email Addresses](#2-ownership-contacts--email-addresses)
3. [Tech Stack & Architecture](#3-tech-stack--architecture)
4. [Repository Structure](#4-repository-structure)
5. [Hosting & Deployment (Netlify)](#5-hosting--deployment-netlify)
6. [Environment Variables & Secrets](#6-environment-variables--secrets)
7. [API Keys & Third-Party Accounts](#7-api-keys--third-party-accounts)
8. [Domain, DNS & SSL](#8-domain-dns--ssl)
9. [Analytics & Tracking](#9-analytics--tracking)
10. [Monetisation — AdSense, Affiliates, Sponsorships](#10-monetisation--adsense-affiliates-sponsorships)
11. [Content Operations & AI Pipeline](#11-content-operations--ai-pipeline)
12. [Social Media & Video Production](#12-social-media--video-production)
13. [SEO, GEO & AEO Strategy](#13-seo-geo--aeo-strategy)
14. [Backlinks, Authority & Domain Authority Plan](#14-backlinks-authority--domain-authority-plan)
15. [Target Audience & Brand Voice](#15-target-audience--brand-voice)
16. [Legal, Compliance, GDPR & Privacy](#16-legal-compliance-gdpr--privacy)
17. [Security Posture (OWASP & Internet Security)](#17-security-posture-owasp--internet-security)
18. [Site Files: sitemap.xml, robots.txt, ads.txt, llms.txt](#18-site-files-sitemapxml-robotstxt-adstxt-llmstxt)
19. [Operational Runbook & Routine Tasks](#19-operational-runbook--routine-tasks)
20. [Known Issues & Watch Points](#20-known-issues--watch-points)
21. [Outstanding Roadmap](#21-outstanding-roadmap)
22. [Asset Valuation & Acquisition Brief](#22-asset-valuation--acquisition-brief)
23. [Appendix — Reference Material](#23-appendix--reference-material)

---

## 1. Brand & Project Overview

### Identity

- **Brand name:** Beat The Scam
- **Strapline:** *"Scam alerts, plain-English checks, and practical guides to help people verify suspicious emails, texts, websites, calls, and offers."*
- **Live URL:** https://beatthescam.com
- **Country focus:** United Kingdom (UK consumer protection)
- **Vertical:** Consumer protection · Cybersecurity · Personal finance safety · Fraud awareness
- **Editorial persona:** "Beat the Scam Editorial Team" (collective byline — the earlier "James Carter" pseudonym has been retired)

### Purpose

A free, UK-focused consumer-protection publication that:

1. Publishes plain-English **scam awareness guides** (now 181 published, with a queue of additional topics being released ~1/day).
2. Offers a **free AI-powered Scam Checker** at `/check/` where users paste suspicious messages and receive a verdict, confidence score, red flags, green flags, recommended actions, and reporting links.
3. Routes users to legitimate UK reporting bodies (Report Fraud / `reportfraud.police.uk`, NCSC, FCA Firm Checker, Take Five, Citizens Advice).
4. Generates revenue via Google AdSense (in review), affiliate partnerships (Experian, Norton, Cifas, Which? Legal), and future newsletter / sponsorship channels.
5. Builds topical authority over the medium-term to rank for UK fraud and scam queries.

### Why this brand has standalone value

- The exact-match keyword domain `beatthescam.com` is short, memorable, and category-defining.
- Consumer fraud is a **YMYL** (your-money-or-your-life) niche with high RPMs once authority is established.
- The site already has 189 original articles, technical SEO foundation, security A+, schema markup, and an AI utility (scam checker) that competitors don't offer.
- The brand is portable: it could be acquired by a consumer-finance publisher, a cybersecurity SaaS vendor, an insurance / identity-protection brand, or a UK media group.

---

## 2. Ownership, Contacts & Email Addresses

### Owner

- **Name:** Alex (full identity intentionally separated from public persona)
- **Trading entity:** SideRight Apps
- **GitHub:** [siderightapps-hub](https://github.com/siderightapps-hub)
- **Repository:** https://github.com/siderightapps-hub/beatthescam-site

### Email addresses in use (or reserved)

| Address | Purpose | Status |
|---|---|---|
| `hello@beatthescam.com` | General public contact (footer + Contact page) | Active |
| `socialmedia@beatthescam.com` | Social platform sign-ups, ElevenLabs, TikTok, YouTube brand account, Instagram | Active |
| `privacy@beatthescam.com` | GDPR / data protection / right-to-be-forgotten enquiries; also the DMARC aggregate-report address (`dmarc@` is an alias of this) | Active (activated 2026-07-13) |
| `welcome@beatthescam.com` | Reserved for newsletter onboarding, but not actually referenced anywhere — the newsletter sends from a separate Resend subdomain (`alerts@updates.beatthescam.com`, see `subscribe.js`'s `FROM_ADDRESS`), not this address | Active mailbox, unused in code |
| `editorial@beatthescam.com` | Editorial / correction enquiries — intended purpose, but every "editorial contact"/correction paragraph in build.py currently points to `contact_email` (`hello@`) instead; never wired in | Active mailbox, unused in code |
| `legal@beatthescam.com` | DMCA / takedown / legal notices — already wired into the Terms/copyright paragraphs via `legal_email` | Active (activated 2026-07-13) |
| `security@beatthescam.com` | Responsible disclosure inbox (security.txt) — already wired in | Active (activated 2026-07-13) |
| `abuse@beatthescam.com` | Not in code anywhere; exists per this doc's own recommendation below (directories/scanners look for it as a trust signal) | Active |
| `siderightapps@gmail.com` | Dev / infra / billing master account (Netlify, GitHub, AdSense, YouTube brand owner) | Active |

> All reserved aliases were activated 2026-07-13. `welcome@` and `editorial@` are live mailboxes but not yet referenced by any code path — see the notes above if that should change.

### Public contact methods

- Contact page: `https://beatthescam.com/contact/`
- Footer link on every page
- Social: Twitter/X `@BeatTheScamUK`, TikTok `@BeatTheScamUK`, Instagram `@beatthescamuk`, YouTube `Beat The Scam`

---

## 3. Tech Stack & Architecture

| Layer | Choice | Notes |
|---|---|---|
| Site generation | **Custom Python static site generator** (`scripts/build.py`) | NOT Next.js, NOT Hugo, NOT Jekyll. Bespoke Python that reads `content/posts.json` + `content/site.json` and renders into `dist/` using `templates/base.html`. |
| Templating | Single `templates/base.html` shell with `{{placeholder}}` substitution | Simple, fast, no framework dependency. |
| Source of truth (content) | `content/posts.json` | All 181 guides as JSON records (grows ~1/day via the gated daily cron). |
| Hosting / CDN | **Netlify** (Personal plan — $9/month, 1000 build credits) | Auto-deploys on push to `main`. |
| Serverless functions | **Netlify Functions** (5: `check-scam`, `subscribe`, `confirm-subscribe`, `unsubscribe`, `csp-report`) | AI checker proxy + double opt-in newsletter (subscribe/confirm/unsubscribe) + CSP violation collector. Functions now carry a `package.json` (`@netlify/blobs`). |
| AI for scam checker | **Anthropic Claude — `claude-haiku-4-5-20251001`** | Returns structured JSON verdict. Durable per-IP rate limit + daily spend cap (`DAILY_CALL_CAP=2000`/UTC-day) via Netlify Blobs. |
| AI for content generation | **Anthropic Claude — `claude-haiku-4-5-20251001`** | Generates 6 sections × 120–180 words + 4 FAQs per guide, gated by `scripts/content_gate.py` before publish. |
| Content automation | **GitHub Actions** (`.github/workflows/daily-publish.yml`) | Daily at 05:07 UTC, batch of 1, gated by the accuracy gate. |
| Analytics | **Google Analytics 4** | ID `G-JXNF856NBF`. Consent via Google Consent Mode driven by the certified CMP. |
| Ads | **Google AdSense** | Publisher ID `ca-pub-1606633100797174`. UK/EEA consent via Google's certified CMP (Privacy & messaging). |
| Email distribution | **Resend** (live, double opt-in) | Audiences + transactional confirm/welcome/unsubscribe emails via `subscribe.js`/`confirm-subscribe.js`/`unsubscribe.js`. |
| Search / SEO | Google Search Console, Bing Webmaster Tools | Site verified. |
| Repository | GitHub (`siderightapps-hub/beatthescam-site`) | Public — confirmed 2026-07-04 via `gh repo view`. |

### Why static + serverless?

- **Zero ongoing server cost** beyond Netlify's flat fee.
- **Instant rollback** via Git history.
- **A+ security** is easier to maintain — no app server attack surface.
- **Dynamic surfaces are five small, isolated serverless functions** (AI checker, newsletter subscribe/confirm/unsubscribe, CSP report collector) — each with rate limiting, CORS/origin pinning, and input sanitisation; no app server.

---

## 4. Repository Structure

```
beatthescam-site/
├── scripts/
│   ├── build.py                       # Main static site builder — DO NOT overwrite carelessly
│   ├── generate_content_claude.py     # Claude API content generator (daily pipeline)
│   ├── rewrite_thin_guides.py         # One-shot script to rewrite short guides
│   ├── run_daily_publish.py           # Daily pipeline orchestrator
│   ├── search_console_articles.py     # Pulls SC queries → finds content gaps → generates articles
│   ├── tweet_new_articles.py          # Auto-tweet on publish
│   ├── content_gate.py                # Content accuracy gate (deterministic + LLM judge)
│   ├── audit_corpus.py                # Re-audits the whole corpus on demand
│   ├── audit_digest.py                # Weekly audit digest emailer
│   ├── gate_selftest.py               # Live self-test for the accuracy gate
│   ├── fact_reverify.py               # Quarterly corpus-wide re-verification (deterministic re-scan + web-search LLM pass) — never edits posts.json
│   └── ...                            # + 13 more: auth_google.py, check_twitter_auth.py, generate_trending_topics.py, generate_video.py, get_youtube_refresh_token.py, gsc_report.py, merge_new_posts.py, add_bank_codes_post.py, recover_courier_guides.py, recover_purged_pages_2.py, upload_to_youtube.py (see `ls scripts/` for the full current list)
├── content/
│   ├── posts.json                     # All 189 published guides (source of truth)
│   ├── site.json                      # Site config (domain, AdSense ID, GA4 ID, etc.)
│   ├── affiliates.json                # Affiliate products config
│   ├── daily-publish-queue.csv        # Pending topics
│   ├── topics-claude-template.csv     # Topic template reference
│   ├── sources.json                   # Verified source canon (reporting phones/emails) — gate + on-page "Report this scam" block derive from this
│   ├── manifests/                     # Per-guide claim manifests (content/manifests/<slug>.json) — audit record of high-stakes claims detected by the gate
│   ├── fact-reverify-reports/         # Quarterly drift reports (content/fact-reverify-reports/<YYYY>-Q<N>.md) written by scripts/fact_reverify.py
│   ├── category-hubs.json             # Category hub page config
│   └── tweeted_posts.json             # Dedupe ledger for auto-tweet
├── templates/
│   └── base.html                      # HTML shell with {{placeholders}}
├── assets/
│   ├── styles.css                     # All site CSS
│   ├── app.js                         # Cookie consent (defers to Google CMP; custom banner fallback) + nav toggle + outbound click tracking
│   └── og-image-v2.png                # OpenGraph default image
├── netlify/
│   └── functions/
│       ├── check-scam.js              # Serverless Claude API proxy (rate-limited)
│       ├── subscribe.js               # Newsletter signup (step 1, double opt-in)
│       ├── confirm-subscribe.js       # Newsletter confirm (step 2) + welcome email
│       ├── unsubscribe.js             # One-click + form unsubscribe
│       └── csp-report.js              # CSP violation report collector
├── .github/
│   └── workflows/
│       ├── daily-publish.yml          # Daily content pipeline (05:07 UTC) — opens a review PR
│       ├── daily-search-console.yml   # Search Console content-gap pipeline (05:23 UTC) — opens a review PR
│       ├── tweet-on-publish.yml       # Fires on merge-to-main touching posts.json — tweets added slugs
│       ├── weekly-audit.yml           # Digests recent claim manifests' flag-tier claims for human review
│       ├── fact-reverify.yml          # Quarterly (1 Jan/Apr/Jul/Oct) — corpus-wide drift re-check, opens a review PR (label fact-audit)
│       ├── gate-selftest.yml          # Manual workflow_dispatch — runs the content gate's live self-test
│       └── codeql.yml                 # CodeQL SAST for JS + Python
├── package.json                       # JS deps for Netlify Functions only (@netlify/blobs)
├── package-lock.json                  # JS deps for Netlify Functions only (@netlify/blobs)
├── netlify.toml                       # Netlify config — security headers, redirects
├── dist/                              # Built site (committed, served by Netlify)
│   ├── _redirects                     # Auto-generated 301s for category slug normalisation
│   ├── robots.txt                     # Auto-generated
│   ├── sitemap.xml                    # Auto-generated
│   └── (all rendered pages)
├── README.md
└── (handoff documents — this file, security audit, session handoffs, etc.)
```

### File-level notes

- `posts.json` is the single source of truth. **Never edit `dist/*.html` directly** — it will be overwritten on the next build.
- `_redirects` is auto-generated by `build.py` from the `CATEGORY_CANON` dict. Do not edit manually.
- `netlify.toml` redirects only work reliably for the `/api/check-scam` rewrite and the `/*` 404 catch-all — category redirects must live in `_redirects` (see Section 20).

---

## 5. Hosting & Deployment (Netlify)

### Plan

- **Netlify Personal plan** — $9/month
- **Build credits:** 1,000/month
- **Functions:** Included
- **Bandwidth:** 100GB/month (well within current usage)

### Configuration

| Setting | Value | Notes |
|---|---|---|
| Publish directory | `dist` | **Critical — must be set in dashboard, NOT just in `netlify.toml`.** See Section 20. |
| Build command | *(blank)* | Site is pre-built and committed. |
| Functions directory | `netlify/functions` | |
| Branch deploys | Main only | |
| Production branch | `main` | |
| Auto-deploy | On push to `main` | ~30s deploy time |

### Deployment flow

```
Developer pushes to main  →  GitHub webhook  →  Netlify pulls repo  →  Serves dist/  →  Live in ~30s
                                              ↳  Bundles netlify/functions/* into Lambda
```

### Daily pipeline flow

**Human-review gate (2026-06-25):** the cron no longer pushes straight to `main`. It opens a pull request instead — nothing publishes, gets ads, or is tweeted until the operator merges it.

```
05:07 UTC  →  GitHub Actions starts daily-publish.yml
            →  Calls Claude API → generates 1 guide → content_gate.py (deterministic + LLM judge); FAIL → quarantine; PASS → write content/manifests/<slug>.json → updates posts.json
            →  Runs python scripts/build.py → rebuilds dist/
            →  Verifies dist/index.html, dist/robots.txt, dist/_redirects, 50+ guide directories exist
            →  git checkout -b auto/daily-publish-<date>-<run_id>
            →  git commit && git push origin <branch>
            →  gh pr create --base main --label auto-content
            →  Operator reviews and merges the PR
            →  Netlify auto-deploys from the merge
            →  (separately) tweet-on-publish.yml fires on that merge push and tweets the added slug(s) — diff-based, ≤3-slug cap, deduped via tweeted_posts.json
```

There is no rebase-retry loop anymore: each cron run branches fresh off `main` and pushes a brand-new branch, so there is nothing to conflict with on push.

### Credit usage discipline

The daily pipeline is optimised to **only push to GitHub when content has actually changed**, saving ~15 credits/month on empty runs. Monitor monthly credit usage in the Netlify dashboard.

---

## 6. Environment Variables & Secrets

### GitHub repository secrets (Settings → Secrets → Actions)

| Secret | Purpose | Last rotated |
|---|---|---|
| `ANTHROPIC_API_KEY` | Used by `daily-publish.yml` for Claude content generation | 2026-04-28 |
| `TWITTER_API_KEY` | Auto-tweet new articles via `tweet_new_articles.py` | (confirm) |
| `TWITTER_API_KEY_SECRET` | Twitter OAuth | (confirm) |
| `TWITTER_ACCESS_TOKEN` | Twitter OAuth | (confirm) |
| `TWITTER_ACCESS_TOKEN_SECRET` | Twitter OAuth | (confirm) |
| `GOOGLE_SEARCH_CONSOLE_TOKEN` + `GOOGLE_OAUTH_CREDENTIALS` | Search Console gap pipeline | (confirm) |

> The four `TWITTER_*` secrets are consumed by **`tweet-on-publish.yml`** (fires on merge-to-`main`, not by either daily content cron directly). `GOOGLE_SEARCH_CONSOLE_TOKEN`/`GOOGLE_OAUTH_CREDENTIALS` are consumed by the separate **`daily-search-console.yml`** cron.

### Local-only env vars (`.env` in repo root, gitignored)

| Variable | Purpose | Notes |
|---|---|---|
| `ELEVENLABS_API_KEY` | Voiceover for `scripts/generate_video.py` | Restricted scope: TTS / Voices / Models / User only. Current key rotated **2026-05-18/19** after an earlier key was leaked in chat. |
| `ELEVENLABS_VOICE_ID` | Optional voice override (default Daniel `3WqHLnw80rOZqJzW9YRB`) | British male newsreader |
| `ELEVENLABS_MODEL_ID` | Optional model override (default `eleven_v3`) | |
| `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET` + `YOUTUBE_REFRESH_TOKEN` | YouTube Shorts auto-upload (`scripts/upload_to_youtube.py`) | One-time OAuth flow — `docs/youtube-upload-setup.md` |

### Worktree `.env` sync

Git worktrees each have their own `.env` (gitignored). Two clean options to keep them in sync — pick one once and stick with it:

```bash
# Option A: symlink (per new worktree)
cd <worktree> && ln -s ../../../.env .env

# Option B: shell helper in ~/.zshrc
worktree-env() { cp ~/Projects/websites/beatthescam-site/.env .env; }
```

### Netlify environment variables (Site settings → Environment variables)

| Variable | Purpose | Last rotated |
|---|---|---|
| `ANTHROPIC_API_KEY` | Used by `check-scam.js` (checker) and the content-generation scripts. The checker also enforces a durable per-IP rate limit + daily spend cap (`DAILY_CALL_CAP=2000`/UTC-day) via **Netlify Blobs** (auto-provisioned — no extra secret). | 2026-04-28 |
| `RESEND_API_KEY` | Newsletter (now **double opt-in**): `subscribe.js` sends the confirmation email; `confirm-subscribe.js` adds the Resend Audience contact + sends the welcome email after the link is clicked. | 2026-06-09 (added) |
| `RESEND_AUDIENCE_ID` | Target Resend Audience (used by `confirm-subscribe.js` to add the contact, `unsubscribe.js` to suppress it). All three of `RESEND_API_KEY`/`RESEND_AUDIENCE_ID`/`UNSUBSCRIBE_SECRET` are now required for signup — missing any returns `500 "Service not configured"`. Get the ID from Resend → Audiences → the `</>` snippet (NOT the domain ID). | 2026-06-09 (added) |
| `UNSUBSCRIBE_SECRET` | Root secret for newsletter tokens. As of **2026-06-25 the tokens are opaque/encrypted (AES-256-GCM)** — the email (+ 7-day expiry for confirm) is sealed under an **HKDF-derived key**, domain-separated per purpose (confirm vs unsubscribe, so the two aren't interchangeable), so a captured URL no longer leaks the address (the prior HMAC format embedded a reversible `base64url(email)`). Both functions **dual-parse** the legacy HMAC formats so links already sent keep working. Any long random string — `openssl rand -hex 32`. **REQUIRED for signup (fails closed):** unset → `subscribe.js` returns `500` rather than minting a token. **Do NOT rotate casually** — it invalidates EVERY live confirm/unsubscribe link (new *and* legacy). | 2026-06-09 (added); AES-GCM 2026-06-25 |

### Key rotation policy

- All keys were rotated on **2026-04-28** after a suspected exposure incident.
- **Cadence going forward:** rotate every 90 days minimum; immediate rotation on any suspected exposure.

### Key rotation history

| Date | Key | Trigger | Action |
|---|---|---|---|
| 2026-04-28 | `ANTHROPIC_API_KEY` (both GitHub Secrets + Netlify env) | Suspected exposure | Rotated both copies; verified all dependent workflows |
| 2026-05-18/19 | `ELEVENLABS_API_KEY` (local `.env`) | Earlier key `sk_be296…` leaked in chat output when a `sed` redaction failed against a malformed file. | User revoked the key in the ElevenLabs dashboard mid-session and created a replacement with restricted scope (TTS / Voices / Models / User only). |

**Lesson logged:** when running redaction commands against `.env` files, verify the file content is well-formed first (no stray BOMs, no CRLF artifacts). A failed redact that prints the raw file to stdout has the same effect as no redact at all.

### What is NOT stored as a secret

- AdSense Publisher ID (public — appears in HTML).
- GA4 measurement ID (public — appears in HTML).
- Affiliate placeholder URLs (in `content/affiliates.json` — public).

---

## 7. API Keys & Third-Party Accounts

This is the **complete inventory of every external account** the site depends on.

### Anthropic (Claude)

- **Account email:** `siderightapps@gmail.com`
- **Used for:** Scam Checker (live runtime), daily content generation pipeline, Search Console article generator.
- **Models in use:**
  - `claude-haiku-4-5-20251001` — content generation, scam checker (cost-optimised)
- **Key locations:** GitHub Secrets + Netlify environment variables.
- **Spend control:** Anthropic Console budget alerts configured.
- **Documentation:** https://docs.anthropic.com

### Google — Search Console

- **Property:** `https://beatthescam.com`
- **Verification method:** DNS TXT record
- **Used for:** Indexing reports, query performance, sitemap submission, content gap analysis (via `search_console_articles.py`).

### Bing Webmaster Tools

- **Status:** site DNS-verified.
- **Recommended setup path:** "Import from Google Search Console" — one click in Bing Webmaster, re-uses the existing GSC verification + sitemap.
- `bing_site_verification` field in `content/site.json` is currently empty (DNS verification means no meta tag is needed).

### Google — Analytics 4

- **Property name:** Beat The Scam
- **Measurement ID:** `G-JXNF856NBF`
- **Used for:** Pageview tracking, outbound click tracking (via `assets/app.js`), conversion goals (scam checker submissions).
- **Tracker placement:** `templates/base.html` — loaded on every page.

### Google — AdSense

- **Publisher ID:** `ca-pub-1606633100797174`
- **Status:** **In review** (review restarted ~2026-04-21 after `ads.txt` was fixed; typical 3–14 day window).
- **Auto Ads:** Enabled in dashboard, pending site approval to begin serving.
- **ads.txt** at `https://beatthescam.com/ads.txt` — verified Authorised.
- **Ad units:** None manually placed yet; relying on Auto Ads. Once approved, plan to add:
  - In-article unit (mid-article, after section 2)
  - Sidebar unit (article pages, below "Related guides")
  - Anchor / sticky-footer mobile unit
- **Essential pages confirmed for AdSense:** Privacy Policy ✅ · About ✅ (with E-E-A-T signals) · Contact ✅ · Cookie Policy ✅ · Terms ✅ · Disclaimer ✅
- **Crawler access:** `robots.txt` does **not** block `Mediapartners-Google` or `AdsBot-Google`. Confirmed.

### Google — Cloud Console

- Used minimally — primarily for Search Console API access (planned for the URL-checker future feature with Google Safe Browsing).

### VirusTotal *(planned)*

- For the planned **URL Checker** feature — pasted URLs would be cross-checked against VirusTotal + Google Safe Browsing, then results fed to Claude for a plain-English verdict.

### Twitter / X

- **Handle:** `@BeatTheScamUK`
- **API access tier:** Free or Basic (confirm)
- **OAuth credentials:** stored as GitHub Secrets for `tweet_new_articles.py`
- **Posting frequency:** On every new article publish (via `tweet-on-publish.yml`, fires on merge to `main`)

### TikTok

**[DISCONTINUED 2026-06-15]** — video production stopped; this account is dormant, not actively posting. Left below for historical reference.

- **Handle:** `@BeatTheScamUK`
- **Account email:** `socialmedia@beatthescam.com`
- **Posting (historical):** Manual upload from CapCut → camera roll → TikTok app (per `video-pipeline.md`)
- **API:** Not used (no automated posting)

### YouTube

**[DISCONTINUED 2026-06-15]** — Shorts production stopped; this channel is dormant, not actively posting. Left below for historical reference.

- **Channel:** Beat The Scam (Brand Account)
- **Owner Google account:** `siderightapps@gmail.com`
- **Channel handle:** TBC
- **Posting (historical):** Manual upload of Shorts via the YouTube Studio interface
- **API:** Not used

### ElevenLabs (voice generation)

**[DISCONTINUED 2026-06-15 — key deleted, plan should be downgraded/cancelled]**

- **Account email:** `socialmedia@beatthescam.com`
- **Plan:** Starter ($6/month) — should be downgraded/cancelled now that the key is deleted
- **Voice used:** Daniel (British male) — changed from Grace
- **Used for (historical):** Voiceovers in Shorts/TikTok videos

### Gemini (image generation)

[DISCONTINUED — stated use case (video image generation) no longer applies since video production stopped 2026-06-15; confirm with operator whether the account itself needs downgrading]

- **Used for (historical):** Generating per-clip images for video production (UK-specific scene details — see `video-pipeline.md` Section 3 Step 3)

### CapCut

**[DISCONTINUED 2026-06-15]** — video production stopped; this tool is no longer in active use.

- **Used for (historical):** Video assembly, auto-captions, background music, end card insertion

> **Note (applies to Impact.com, Awin, and CJ Affiliate below):** `content/affiliates.json`'s actual live product links (Experian, Cifas, Which? Legal, Norton) are currently direct/untracked URLs, NOT routed through any of these three affiliate networks — regardless of each account's individual application status below. No affiliate commission is currently being captured through them yet.

### Impact.com (affiliate network)

- **Status:** Account created, site verified via meta tag
- **Programmes pending:** Norton 360 (via Impact)

### Awin (affiliate network)

- **Status:** Application rejected on first attempt (new domain). **Reapply window: 2026-06-12 onwards** (~4–6 weeks post rejection) with Search Console traffic evidence.
- **Programmes targeted:** Experian IdentityPlus

### CJ Affiliate (Commission Junction)

- **Status:** Application in progress; publisher description submitted
- **Programmes targeted:** Norton 360 (alternative route), Which? Legal

### Direct affiliate outreach (planned)

- Experian (via Awin)
- Norton (via Impact / CJ)
- Which? Legal (direct email outreach drafted)
- Cifas (direct via cifas.org.uk/contact)

---

## 8. Domain, DNS & SSL

| Item | Value |
|---|---|
| Domain | `beatthescam.com` |
| Registrar | **Dynadot** |
| Registration date | February 2026 |
| DNS provider | **Dynadot DNS** (nameservers `ns1.dyna-ns.net` / `ns2.dyna-ns.net`); apex A record → Netlify `75.2.60.5`. NOT Netlify DNS. |
| SSL | Let's Encrypt via Netlify managed HTTPS |
| HSTS | `max-age=63072000; includeSubDomains; preload` — **submitted to HSTS preload list 2026-06-22 (pending inclusion)** |
| TLS rating | **SSL Labs A+** (TLS 1.3, modern cipher suites) |

### Email authentication & DNS hardening (status 2026-06-22)

Full operator runbook: [`docs/dns-hardening-checklist.md`](dns-hardening-checklist.md). All records are edited in the **Dynadot** control panel.

| Control | Status | Notes |
|---|---|---|
| SPF | ✅ strong | `v=spf1 include:spf.protection.outlook.com -all` (apex on Microsoft 365) |
| DKIM (M365, apex mail) | ✅ 2048-bit, both selectors | `selector1/2._domainkey` CNAMEs; rotated to 2048 (Defender, 2026-06-22); **selector 1 malformed-CNAME corrected 2026-06-25** (3rd-audit finding) — both selectors now sign |
| DKIM (Resend, newsletter) | ✅ 1024-bit (Resend max) | `resend._domainkey.updates`; **Resend offers no 2048 option (confirmed 2026-06-25) — closed, not pending**; 1024 passes DMARC |
| DMARC | ⚠️ `p=none` + reporting | `rua=mailto:dmarc@beatthescam.com` (alias of `privacy@`). Ramp to quarantine→reject is the next step, after ~1–2 wks of clean reports showing BOTH M365 and Resend pass |
| CAA | ✅ live | `0 issue/issuewild "letsencrypt.org"` + `0 iodef "mailto:dmarc@beatthescam.com"` |
| DNSSEC | ❌ not enabled | Blocked: Dynadot only offers DNSSEC with third-party nameservers. Deferred unless DNS is moved. |

Email: apex on **Microsoft 365** (MX `beatthescam-com.mail.protection.outlook.com`); newsletter sends via **Resend** from `updates.beatthescam.com`.

### Subdomains in use

- `www.beatthescam.com` → 301 redirect to apex `beatthescam.com`
- `updates.beatthescam.com` → Resend newsletter sending domain (SPF/DKIM)

### Subdomains reserved for future

- `mail.beatthescam.com` — for transactional email (newsletter)
- `app.beatthescam.com` — reserved if checker grows into a dedicated SPA
- `status.beatthescam.com` — reserved for status page

---

## 9. Analytics & Tracking

### Google Analytics 4

- **Measurement ID:** `G-JXNF856NBF`
- **Events tracked:**
  - `page_view` (standard)
  - `outbound_click` (custom — fires on any `a[target="_blank"]` or non-same-domain link)
  - *(planned)* `scam_check_submitted`, `affiliate_click`, `newsletter_signup`
- **Conversion goals:** TBC — recommend setting "scam check submitted" as a key event.

### Tag implementation

GA4 `gtag.js` loads inline via `templates/base.html`. This is one of the reasons the CSP must allow `'unsafe-inline'` in `script-src` (see Section 17).

### Privacy posture

- GA4 IP anonymisation is on by default (post-GA4).
- No advertising/remarketing features enabled in GA4 admin (keeps consent obligations lighter).
- See Section 16 for cookie banner and consent treatment.

### Semrush (SEO + backlink audit + site audit)

- **Project:** `beatthescam.com` (single project, free tier).
- **Position Tracking:** target country was initially set to **Spain (Spanish)** in error — this needs swapping to **United Kingdom (English)** in the Position Tracking settings (delete the existing target and re-add UK — the free tier's 1-target limit blocks adding a 2nd before deleting the 1st).
- **Site Audit baseline (2026-05-30 after this session's remediation):**
  - Site Health **98%** (was 96% before fix pass)
  - AI Search Health **99%** (was 88% — biggest gain from llms.txt + cleaner heading hierarchy + sentence-split paragraphs)
  - Errors **0** · Warnings **192**
  - **191 of 192 warnings are unfixable** — Google's `pagead2.googlesyndication.com/.../adsbygoogle.js` flagged as "uncompressed" on every page. We don't control Google's CDN compression headers. Accept as inherent to running AdSense.
  - The 1 remaining genuine warning is "low word count" on a page already rewritten in source — will clear on next re-crawl.
- **Backlink Audit (Disavow Policy):** see Section 14 — Beatthescam.com has an active Google disavow file as of 2026-05-30.
- **Cadence:** re-run the Site Audit + Backlink Audit weekly; check the dashboard before any push that materially changes templates or rendered HTML.

### Looker Studio (optional)

Semrush exposes a Looker Studio connector under the Site Audit "Export" menu. Not wired up. Worth doing if/when we want a single dashboard combining GSC + GA4 + Semrush.

### PageSpeed Insights / Lighthouse

- **Baseline captured 2026-06-04 (all mobile, post-fix):**

  | Page | Perf | A11y | Best Practices | SEO | Notable lab metric |
  |---|---:|---:|---:|---:|---|
  | Homepage | 92 | 98 | 92 | 100 | FCP 2.4s, LCP 2.9s (amber — pre-preconnect-fix) |
  | Sample guide (FB Marketplace) | 97 | 95 | 92 | 100 | FCP 0.8s, LCP 2.4s, TBT 130ms, **CLS 0** |
  | Author page (`/author/`) | 97 | 96 | 92 | 100 | FCP 0.8s, LCP 2.1s |

- **CLS = 0 on guide pages** is genuinely exceptional — static-HTML approach pays off. Lab metrics on guide + author pages are all green.
- **The persistent Best Practices 92** is AdSense's `adsbygoogle.js` (third-party script, served without certain headers Google's own scoring expects). Unfixable without removing AdSense.
- **Re-check cadence:** spot-check the homepage + a fresh guide on PageSpeed monthly, and after any material template or third-party script change. URL pattern: `https://pagespeed.web.dev/analysis?url=<encoded-url>`.
- **API rate-limit gotcha:** the public PageSpeed Insights API (`googleapis.com/pagespeedonline/v5/runPagespeed`) is aggressively rate-limited per IP for anonymous callers — Three sequential calls from a single IP returned HTTP 429. For automated re-checks, get a free API key at <https://console.cloud.google.com/apis> (PageSpeed Insights API) and pass it as `&key=...`. Manual checks via `pagespeed.web.dev/analysis` UI have no such limit.

---

## 10. Monetisation — AdSense, Affiliates, Sponsorships

### Channel status table

⚠️ Table dated 2026-05-20 — re-verify each row's status, especially Awin (reapply window has since opened).

| Channel | Status (2026-05-20) | Estimated revenue at scale |
|---|---|---|
| **Google AdSense** | In review since ~2026-04-21 | £30–£900/mo depending on traffic |
| **Experian IdentityPlus (via Awin)** | Awin rejected, reapply 2026-06-12+ (reapply window opened 2026-06-12 — confirm with operator whether this happened) | £50–£300/mo if approved |
| **Norton 360 (via Impact/CJ)** | Impact verified, CJ application in progress | £50–£250/mo if approved |
| **Which? Legal (direct outreach)** | Email outreach drafted | £30–£150/mo if approved |
| **Cifas Protective Registration** | Direct outreach planned | £20–£100/mo (lower commission tier) |
| **Newsletter sponsorships** | Newsletter live (Resend, double opt-in) — list size TBC | £100–£500/mo per sponsored issue once list >2,000 |
| **Direct sponsorships** | None yet | Untapped — security SaaS brands relevant |

### AdSense — readiness checklist

- [x] Privacy Policy page live (`/privacy/`)
- [x] About page live (`/about/`) with E-E-A-T author byline, methodology, source list, AI disclosure, review date
- [x] Contact page live (`/contact/`)
- [x] Cookie Policy page live (`/cookies/`)
- [x] `ads.txt` served and Authorised at `/ads.txt`
- [x] `robots.txt` does not block `Mediapartners-Google` or `AdsBot-Google`
- [x] Original, regularly-published content (181 guides, gated daily publishing pipeline)
- [x] Working HTTPS with valid certificate
- [x] Site has clear navigation and footer

### Ad serving policy (per-page — added 2026-06-22)

The AdSense tag is **no longer hardcoded on every page**. `templates/base.html` carries an `{{ads_head}}` placeholder filled per-page by `_ads_head()` in `build.py`, driven by an `ads_mode`:

- **`none`** — the `/check/` tool is **excluded from Auto Ads entirely** (`render_check_page` passes `ads_mode="none"`).
- **`npa`** — pages about debt / insolvency / money-recovery serve **non-personalised ads** regardless of consent (`requestNonPersonalizedAds=1`), because Google restricts ad personalisation based on negative financial status. Matched by `post_ads_mode()` against slug/title/category/keywords (leading word-boundary regex; ~6 guides: debt-management, debt-relief, iva-scam, crypto-recovery, recovery-room, refund-recovery).
- **`default`** — standard Auto Ads tag (personalisation still gated by the CMP / Consent Mode).

To widen/narrow the NPA set, edit `_SENSITIVE_FINANCE_TERMS` in `build.py`.

### Ad unit IDs

Currently relying on **Auto Ads** — no individually-named ad units exist yet. Once approved, manual placements to consider:

| Unit position | Recommended size | Format |
|---|---|---|
| In-article (after section 2) | Responsive | Native — display |
| Sidebar (article right rail, below "Related guides") | 300×600 / responsive | Display |
| Sticky anchor (mobile only) | 320×50 → 320×100 | Anchor |
| Below FAQ schema block (article foot) | Responsive | Native — multiplex |

Once units are created, **add their IDs here:**

```
adsense_publisher_id: ca-pub-1606633100797174
in_article_unit:      <add after creation>
sidebar_unit:         <add after creation>
mobile_anchor_unit:   <add after creation>
multiplex_unit:       <add after creation>
```

### Affiliate products live in `content/affiliates.json`

| ID | Product | Categories matched | href status |
|---|---|---|---|
| `experian-identity` | Experian IdentityPlus | payment, fraud, website, email, sms, phone, finance | Placeholder — replace when Awin approves |
| `cifas-protective` | Cifas Protective Registration | fraud, payment, finance, email | Placeholder — replace on direct outreach approval |
| `which-legal` | Which? Legal | payment, marketplace, shopping, travel, employment | Placeholder — replace on direct outreach approval |
| `norton-360` | Norton 360 | tech, website, email, social, crypto | Placeholder — replace when Impact/CJ approves |

### Sponsorship / partnership ideas (future)

- Sponsored "Editor's Pick" sections within category hub pages
- Co-branded annual "UK Scam Trends Report" with an identity-protection brand
- Sponsored email blast inside the newsletter (once list size supports it)

---

## 11. Content Operations & AI Pipeline

### Major completed milestones

- **2026-04-30** — Security audit + remediation (Section 17).
- **2026-05-01/02** — SEO hygiene + bullet-list bug fix + housekeeping sweep (category redirects, robots.txt, About-page E-E-A-T).
- **2026-05-18/19** — 14-item structural SEO sweep landed on commit `b09a9d1`: sentence-aware meta descriptions; duplicate slug disambiguation (177→180 indexable guides); BreadcrumbList + HowTo + ItemList schema; per-post Open Graph images (Pillow-generated 1200×630 in `dist/assets/og/`); pagination of `/guides/` at 30/page with `rel=prev/next`; `hreflang=en-GB`; sitemap lastmod per category; RSS discovery in `<head>`; related-posts cross-category scoring. Plus editorial-integrity pass — removed the fabricated "James Carter" editor persona, switched article schema author to `Organization`, added Action Fraud / NCSC / Citizens Advice citations to every guide footer.
- **2026-05-19** — Video generation pipeline built (`scripts/generate_video.py`); HMRC Tax Rebate first publish hit 210 YouTube Shorts views.
- **2026-05-21** — `daily-publish` + `daily-search-console` pipelines serialised via `concurrency: content-pipeline` group; rebase-conflict recovery rewritten; batch size dropped 5 → 1.
- **2026-05-22** — Video pipeline extended with `HOOK_TEMPLATES` topic-family classification + per-family verify copy + `shorten_warning()` v2 (clause-aware trim). YouTube Shorts auto-upload (`scripts/upload_to_youtube.py`) shipped.
- **2026-05-22 (later)** — Auto-generated brand-aligned thumbnails (1280×720 JPEG, per-family `thumbnail_text`, auto-uploaded via `yt.thumbnails().set()`). `shorten_warning()` hardened: ellipsis fallback removed entirely — function now NEVER cuts mid-phrase, returns full original sentence if no clean clause boundary exists. macOS Reminders integration in `upload_to_youtube.py` — auto-creates a "Upload <slug> to TikTok" reminder for 07:30 local time on every successful upload (syncs to iPhone via iCloud).

### Current state

- **Published guides:** 181 across 17 normalised categories
- **Queue:** ~30 remaining topics in `content/daily-publish-queue.csv` (~30 days at 1/day)
- **Avg article length:** 900–1,200 words (post-rewrite of 20 thin guides)
- **Structure per article:** 6 sections × 120–180 words + 4 FAQs + sidebar (Fast checks, Related guides, Report this scam, Checker CTA, Affiliate card) + FAQ schema
- **Reporting links & brand:** `reportfraud.police.uk`, branded **"Report Fraud"** throughout the canon (`content/sources.json`) and every template surface (guide footer, `/check/`, `/about/`, `/terms/`, `/contact/`, `/disclaimer/`, `humans.txt`) — fixed 2026-07-10; the link had been migrated earlier but ~15 hardcoded spots in `build.py` plus the canon `name`/`info_url` fields still said "Action Fraud" / `actionfraud.police.uk` until then. **Guide prose sweep also done (2026-07-10, `f70802f41` / PR #56):** every rendered field (`sections`/`faq`/`title`/`description`) in `content/posts.json` is now "Report Fraud"-branded and `dist/` carries zero `actionfraud.police.uk` links. The only remaining "Action Fraud" strings in `posts.json` sit in the dead, never-rendered legacy `content` field (169 guides — harmless, see the legacy-field gotcha) plus the intentional "(formerly Action Fraud)" parenthetical the canon report block renders on-page. See `docs/content-diversification-plan.md` §8.

### Daily publish pipeline

| Item | Value |
|---|---|
| Workflow file | `.github/workflows/daily-publish.yml` |
| Schedule | Daily at **05:07 UTC** (06:07 BST) — moved off popular minute/hour slots to reduce GitHub-Actions scheduling delay. Cron is best-effort, not on-time. |
| Batch size | **1 guide per run** (was 5 until 2026-05-22; reduced to keep velocity sane and avoid burying posts) |
| Queue file | `content/daily-publish-queue.csv` |
| Model | `claude-haiku-4-5-20251001` |
| Build verification | Fails workflow if `dist/index.html`, `dist/robots.txt`, `dist/_redirects` missing OR <50 guide dirs |
| Publish flow (since 2026-06-25) | Generate → gate → build → **opens a review PR** (branch `auto/daily-publish-<date>-<run_id>`, label `auto-content`). Does **not** push/commit to `main` directly — a human must merge. No rebase-retry loop: each cron branches fresh off `main`, so there's nothing to conflict with. |

### Search Console article generator (parallel pipeline)

- Runs at **05:23 UTC** daily (was 06:30 UTC until 2026-05-22). Off popular slots to reduce delay; queued behind `daily-publish` via shared `concurrency: content-pipeline` group.
- Pulls trending queries from Search Console
- Identifies content gaps (queries with impressions but no matching guide)
- Generates new article via Claude API, runs it through the accuracy gate, and rebuilds
- **Opens a review PR** (branch `auto/search-console-<date>-<run_id>`, label `auto-content`) — does not commit/push to `main` directly, same as `daily-publish`
- Nothing publishes, gets ads, or is tweeted until the operator merges the PR

On merge, a **separate** workflow, `tweet-on-publish.yml`, tweets the slug(s) added by that push (diff-based against `content/posts.json`, ≤3-slug cap, deduped via `content/tweeted_posts.json`) — tweeting is no longer a step either generator runs itself.

### Manual content commands

```bash
# Generate content from queue
ANTHROPIC_API_KEY=your_key python3 scripts/generate_content_claude.py \
  content/daily-publish-queue.csv \
  --posts content/posts.json \
  --mode claude \
  --model claude-haiku-4-5-20251001

# Rewrite thin guides
ANTHROPIC_API_KEY=your_key python3 scripts/rewrite_thin_guides.py \
  --posts content/posts.json \
  --threshold 400 \
  --limit 10 \
  --model claude-haiku-4-5-20251001

# Build the site
python3 scripts/build.py
```

### Editorial principles

- **No fabricated statistics.** All stats verified against Report Fraud, NCSC, FCA, UK Finance, Which?, named surveys.
- **UK-first language.** Pounds sterling, UK reporting routes, UK phone scam patterns (HMRC, DVLA, Royal Mail, BT).
- **Plain English.** No legal jargon. Read-aloud test for every section.
- **Always include reporting routes.** Every article links to `reportfraud.police.uk`.
- **AI disclosure** on the About page is explicit and honest.

### Topic queue management

When `content/daily-publish-queue.csv` drops below 20 topics, add new ones in batch — use Search Console gap analysis and current scam news (NCSC alerts, Report Fraud bulletins, Which? scam tracker) as the source.

---

## 12. Social Media & Video Production

> ⛔ **Video production DISCONTINUED 2026-06-15.** YouTube Shorts + TikTok video was stopped — it built neither domain authority nor backlinks for a search/reference asset, and the manual time went to the operator's main bet (the "31 Years" YouTube channel). Production was fully manual (no cron automated it), so nothing was disabled in the repo — the scripts below (`generate_video.py`, `upload_to_youtube.py`) remain for reference but are **no longer in active use**. The BTS ElevenLabs voiceover key was deleted. Rationale: `docs/video-pipeline.md`. The **only active social channel is X/Twitter** (auto-posts on publish). The daily written-guide pipeline is unaffected and remains the authority engine.

### Channels

| Platform | Handle | Status |
|---|---|---|
| Twitter / X | `@BeatTheScamUK` | ✅ Active — auto-posts on article publish |
| TikTok | `@BeatTheScamUK` | ⛔ Video discontinued 2026-06-15 (3 videos published before stop) |
| YouTube | `Beat The Scam` (Brand Account) | ⛔ Video discontinued 2026-06-15 (3 Shorts published before stop) |
| Facebook | Reserved | Not active |
| Instagram | `@beatthescamuk` | ⛔ Video discontinued 2026-06-15 |
| LinkedIn | Reserved | Not active |
| Reddit | Personal account used carefully in r/Scams and r/UKPersonalFinance | See Section 14 |

### Video production workflow (HISTORICAL — discontinued 2026-06-15; full detail in `video-pipeline.md`)

> Retained for reference only. The pipeline was never automated by a cron, so it is simply no longer run. The old Gemini-character-image / CapCut workflow had earlier been retired on 2026-05-22. When it was active, the workflow was one command per video:

```bash
python3 scripts/generate_video.py <slug>            # render MP4 from posts.json
python3 scripts/upload_to_youtube.py <slug>         # auto-upload Unlisted
# TikTok upload remains manual via tiktok.com web
```

The pipeline ([`scripts/generate_video.py`](scripts/generate_video.py)):

- Reads any post from `content/posts.json` by slug.
- Renders 8 Pillow text cards (Hook → Promise → 3 Signs → Verify → CTA → End card) on the brand palette (`#0b1220` navy, `#3a86ff` accent, `#ff5c5c` alert red).
- Synthesises voiceover via **ElevenLabs Daniel V3** (British male newsreader, voice ID `3WqHLnw80rOZqJzW9YRB`).
- Picks topic-correct hook + verify copy via `HOOK_TEMPLATES` + `SLUG_FAMILIES` (`message` / `marketplace` / `family_message` / `call` families).
- Trims warning text via `shorten_warning()` (clause-aware, handles `using/via/by X, Y, Z` lists + `but/and/or/within` connectors).
- Outputs 1080×1920 H.264 MP4 at ~45s, ~28MB, to `out/videos/<slug>.mp4` (gitignored).
- Renders per-card frames + audio for debug at `out/videos/<slug>-frames/` and `out/videos/<slug>-audio/`.

YouTube auto-upload ([`scripts/upload_to_youtube.py`](scripts/upload_to_youtube.py)) reads the MP4 + the `.upload.md` sidecar, uploads via the YouTube Data API v3 (Unlisted by default for 24h review, `--public` to publish immediately). After the video upload, it also auto-uploads the brand thumbnail (1280×720 JPEG) via `yt.thumbnails().set()` and creates a **macOS Reminder** ("Upload `<slug>` to TikTok" at 07:30 local time) so the remaining manual TikTok step doesn't get forgotten. Reminder syncs to iPhone via iCloud. One-time OAuth setup: `docs/youtube-upload-setup.md` (~15 min). First-run macOS permission grant: `python3 scripts/upload_to_youtube.py --test-reminder`.

### Hashtag template

Standard tags: `#ScamAlert #UKScam #ScamAwareness #FraudAlert #BeatTheScam`

### Posting schedule (historical — video discontinued)

When video was active: daily (Mon–Sun), best window 07:30–09:00 UK BST. No longer run.

### Video calendar (historical — video discontinued)

The 12-video plan was abandoned at 3 published (ISP Impersonation, WhatsApp "Hi Mum", Royal Mail Text) when video was discontinued 2026-06-15.

---

## 13. SEO, GEO & AEO Strategy

This site is engineered for three search modes simultaneously:

- **SEO** — Traditional Google ranking
- **GEO** (Generative Engine Optimization) — being cited by SGE, Gemini, Bing Copilot, ChatGPT, Perplexity
- **AEO** (Answer Engine Optimization) — appearing in featured snippets, "People also ask", and voice answers

### Current SEO state (Search Console snapshot 2026-04-30)

⚠️ This snapshot is from 2026-04-30 and is now stale. A more recent 90-day pull (token refreshed 2026-06-26, via `scripts/gsc_report.py`) is recorded in `docs/content-diversification-plan.md` §1: 9,731 impressions / 49 clicks / 0.50% CTR / average position 15.5 — a substantially better picture than the figures below. See that doc for the current numbers; re-pull via `gsc_report.py` for anything more recent than 2026-06-26.

- Impressions: 1,850 / 3 months
- Clicks: 3 (CTR 0.2%)
- Average position: 24.1
- Indexed: 96 pages
- Not indexed: 42 (28 "discovered – currently not indexed", 10 404s now redirected, 3 page-with-redirect now resolved, 1 crawled-not-indexed)
- Core Web Vitals: no CrUX data yet (insufficient traffic)

### Structural SEO foundations (✅ already in place)

- Canonical URLs on every page
- Schema.org markup: `WebSite`, `Organization`, `Article`, `FAQPage`, `BreadcrumbList`, **`ItemList`** (category + paginated guide indices), **`HowTo`** (on posts with clear numbered steps — ~2 of 180 qualify; conservative emission)
- OpenGraph + Twitter Card meta on every page; **per-post 1200×630 OG image** generated by Pillow into `dist/assets/og/{slug}.png`
- `hreflang="en-GB"` + `x-default`; `og:locale="en_GB"` on every page
- Reading time on every article
- Table of contents on every article
- Related-guides sidebar (cross-category scoring — shared keywords count, not just same category)
- **Pagination of `/guides/`** at 30/page (currently 6 pages) with `rel=prev/next` + per-page canonicals
- `sitemap.xml` auto-generated, **per-category `lastmod` reflects newest member** (not build date); submitted to Search Console + Bing Webmaster Tools
- `robots.txt` tightened (blocks `/search/`, `*.php`, `?l=` spam patterns)
- Category 301s deployed via `dist/_redirects`
- **RSS discovery** via `<link rel="alternate" type="application/rss+xml">` in `<head>`
- HSTS preload + HTTPS everywhere
- Mobile-responsive, fast (no JS frameworks, minimal assets)
- HTTP/2 via Netlify
- Image lazy-loading where applicable
- **Linkified bare `/guides/...` paths** in article body — AI-generated raw paths become real `<a>` tags via the slug→title map

### Priority pages (deserve internal-link concentration)

| Page | Priority | Reasoning |
|---|---|---|
| `/check/` — Scam Checker | **Top** | Unique tool, conversion engine, primary differentiator |
| Category hubs (`/categories/payment/`, `/categories/sms/`, `/categories/email/`, etc.) | **High** | Head-term targets ("payment scams uk", "email scams uk") |
| Top 10 highest-impression guides (per Search Console) | **High** | Already attracting traffic — push to page 1 |
| `/about/` | Medium | E-E-A-T signal carrier; supports YMYL ranking |

### Near-miss query strategy (highest immediate leverage)

Near-miss query strategy:

1. In Search Console → Performance → Queries, filter to **Position < 20**
2. Sort by Impressions descending
3. For top 5: ensure query appears in title, H1, first 100 words
4. Compare to position 1–5 competitors — match depth, examples, schema
5. Add 2–3 contextual in-body internal links from related guides using the query as anchor text
6. Position 15 → 8 typically multiplies clicks 5–10×

### Category hub strategy

The 17 categories normalised in `CATEGORY_CANON` give us 17 potential head-term ranking pages. **Top 3 categories by article count should be built out first** as 600–800 word hubs:
- Clear scope statement
- 3–4 paragraphs on common patterns
- Full link list to every guide in category
- "What to do" section with reporting links

### Contextual in-body internal linking

Sidebars are weak signals. In-body links from running prose are strong. Every time a guide mentions a related concept (e.g. "spoofed sender addresses"), link the phrase to the dedicated guide.

### GEO (Generative Engine Optimization)

Per Google's [AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), the same fundamentals that win in Search also win in AI Overviews and SGE. Specific actions:

- **Clear, factual, well-sourced content.** AI engines cite sources they trust.
- **Schema.org markup** — already in place (`FAQPage` especially).
- **Author attribution** (E-E-A-T) — now in place via the "Beat the Scam Editorial Team" collective byline.
- **Recent review dates** — "Last reviewed: May 2026" on About; should be extended to article pages.
- **Plain-English question-and-answer formatting** — already in FAQ blocks.
- **Stable URLs and canonical tags** — already in place.
- **Avoid duplicate / near-duplicate content** — guides are individually written per topic.
- **No paywalls / interstitials** — accessible content.

### AEO (Answer Engine Optimization)

- **FAQ schema on every guide** ✅
- **Question-shaped H2/H3 headings** ("What is a Royal Mail text scam?") — already used
- **Concise 40–60 word answers immediately under each question** — used in FAQs
- **Tables, lists, step-by-steps** — rendered as proper HTML (`<ul>`, `<ol>`, `<table>`) so featured-snippet eligible
- **"How to spot…" and "What to do if…" templates** — already standard

### Title & meta description optimisation

- Front-load the most useful word ("PayPal scam" not "How to spot a PayPal scam")
- Add the current year to evergreen guides ("…in 2026") — lifts CTR ~10–15%
- Meta description should answer "what will I learn / what should I do", not summarise

### Page experience

- LCP, FID/INP, CLS — no live CrUX data yet but synthetic Lighthouse scores 90+ across the board
- No interstitials or pop-overs (other than the cookie banner)
- Minimal third-party JS (GA4 + AdSense are the only externals)

---

## 14. Backlinks, Authority & Domain Authority Plan

> **The principle:** authority and content quality are the top two ranking factors for a YMYL site like this one. Without backlinks, even excellent content rarely breaks page 1 for competitive UK fraud queries.

### Foundation backlinks (do these first, in this order)

1. **Niche directories**
   - Citizens Advice partner / referral lists
   - GetSafeOnline resource lists
   - Take Five partner page
   - Report Fraud / NCSC public resource directories
   - National Trading Standards-affiliated lists
   - UK consumer-affairs blog rolls

2. **Profile & citation links**
   - About.me profile
   - Crunchbase organization (if registered as a business)
   - LinkedIn Page (Beat The Scam)
   - Trustpilot business profile (claim early — defensive)
   - Producthunt (if AI scam checker is positioned as a product)
   - Hacker News "Show HN" once newsletter or URL checker ships

3. **Social mentions**
   - Twitter / X bio link ✅
   - TikTok bio link ✅
   - Instagram bio link ✅ (`beatthescam.com`)
   - YouTube channel "About" link ✅
   - Pinterest (when that channel activates)

4. **Reddit participation** *(carefully, organically)*
   - **r/Scams** — answer questions with genuine help; link only when directly relevant
   - **r/UKPersonalFinance** — same approach
   - **r/AskUK** — answer scam questions
   - **Rule:** be a contributor first, link-dropper never. Reddit can become a major traffic source done correctly, or a permanent ban done badly.

5. **Quora**
   - Answer 10–15 high-impression UK-scam questions
   - One link in profile, in-answer links only when directly cited as source

### Listed directories to submit to

| Directory | Type | Notes |
|---|---|---|
| Google Business Profile | Local / brand | Even though there's no physical location, "service area" profiles work for online services |
| Bing Places | Local / brand | Mirror of GBP |
| DMOZ-style UK directories | Vertical | Open Directory Project successors |
| UK Consumer Rights Directory | Niche | Direct manual submission |
| Money Saving Expert forum signature | Niche | Account profile only |
| Citizens Advice resource page | Niche | Worth direct outreach |
| Which? Conversation resource pages | Niche | Worth direct outreach |

### Niche edits / link insertions (highest ROI per the brief)

> Per the brief: *"niche edits/link insertions are where the real ROI usually comes in. Guest posts should always be part of the strategy, but if you truly want to maximize ROI, start with link insertions first."*

**Process:**
1. Identify UK consumer-finance / cybersecurity blogs with existing articles on scams (e.g. "Top 10 scams of 2026")
2. Email the author / editor with a polite pitch: "I noticed your article on X. We've published a more detailed walkthrough on the [specific scam variant] — would you consider adding a link in section Y?"
3. Offer a quid-pro-quo only if it's natural (a link from your site to theirs in a relevant guide)
4. Target 5–10 attempts per week

**Targets:**
- MoneySavingExpert (extremely hard but high authority)
- Which?
- LovingMoney, ThisIsMoney, MoneyWeek
- Consumer-finance bloggers
- UK cybersecurity bloggers (Graham Cluley, Sophos News, BleepingComputer guests)

### Guest posts

- Pitch original UK-focused fraud trend pieces to:
  - UK personal finance bloggers
  - UK cybersecurity publications
  - Local newspaper online sections (a single piece in a regional Reach plc title can be huge)
- One link from a `.gov.uk`, `.ac.uk`, or trusted UK finance publisher is worth more than fifty random blog comments.

### HARO / Connectively (now Featured.com)

- Sign up as a source
- Respond to UK journalist queries about scams (~5 attempts/week)
- Wins come from quick, well-written, attributed responses

### Backlink cadence

> **Consistency matters more than volume.** Per the brief: *"Getting backlinks is important, but consistency matters even more. It's not a one-time activity — it needs to happen regularly over time."*

| Tactic | Frequency | Target wins per month |
|---|---|---|
| Directory submissions | 5/week for first 6 weeks, then maintenance | 5–10 links |
| Reddit contributions | 3–5 posts/comments per week | 2–4 links (when natural) |
| Quora answers | 2/week | 2–4 links |
| Link-insertion outreach | 5–10 emails/week | 1–3 placements |
| Guest post pitches | 3/week | 1 placement/month |
| HARO responses | 5/week | 1–2 quotes/month |

### Domain Authority improvement plan

DA isn't a Google metric but is a useful proxy. Realistic 12-month target: **DA 25–35** from current ~5–10. Path:
- 50+ referring domains from contextual links
- 5+ links from DA 50+ sources (Which?, MoneySavingExpert, a regional newspaper)
- Steady internal-link expansion via category hubs
- Continued original content (>200 guides by month 12)

### Disavow Policy ✅ Live since 2026-05-30

The site has an active Google disavow file. Background and the rules for future maintenance:

**Why we have one.** Young domains get passively pulled onto "aged-domain marketplace" scrape lists within months of registration. Semrush flagged 53 toxic backlinks (out of 112 analysed) on 2026-05-30, all from the same class of source: `all-aged-domains.com`, `mail.domainanalysis.org`, `mail.linksnatcher.com`, `wonvision.com`, `jobsapp.info` etc. — all "Where to buy aged domains and backlinks" scraper aggregators. We did not buy links; the site was scraped onto these lists automatically.

**What we disavowed.** 66 domains at the **domain level** (so any future link from those same farms is also ignored). The active file is `disavow_beatthescam.com_20260530.txt` — keep a copy under `~/Downloads/` and re-export from Semrush whenever it changes.

**Where it lives.** Disavow is uploaded at https://search.google.com/search-console/disavow-links — the tool is hidden, not in the main Search Console nav. Note: **the disavow tool only works on a URL-prefix property**, not on a Domain property. We added `https://beatthescam.com/` as a URL-prefix property in Search Console specifically to enable this (the Domain property `beatthescam.com` remains the primary).

**THE RULE for future updates (this is the one to remember).** Every upload **REPLACES** the previous file — not appends. So:
1. In Semrush → Backlink Audit → Disavow tab → click **Export to .txt** to get the *full* current list
2. Upload that full file to the disavow tool (it overwrites the previous)
3. **Never** edit by hand and never upload a partial list — you'd accidentally un-disavow everything missing

**When to re-do.** Re-export + re-upload once a month, or any time a new Semrush audit flags 5+ new high-toxicity sources. The "Download list" button in Search Console always shows the currently-active file as a sanity check.

**What this fixes vs. doesn't.** Disavow tells Google to ignore those links for ranking — links still exist on the spam sites, Semrush will keep showing them in "Backlinks" (Semrush ≠ Google). Authority Score does **not** lift from disavowing — aged-domain spam never passes authority anyway. Real lift comes from earning quality backlinks (the work above).

### Avoiding bad backlink habits

- ❌ No paid PBNs
- ❌ No exact-match anchor-text spam ("UK scam checker" anchored hundreds of times)
- ❌ No comment-spam / forum-sig spam
- ❌ No directory-submission services that hit 500+ low-quality directories

---

## 15. Target Audience & Brand Voice

### Primary audience

- **UK adults 35–75** who have just received a suspicious message and are trying to verify it *right now*.
- **Adult children of older parents** searching on behalf of a relative who's been targeted.
- **People who've already been scammed** looking for reporting routes and next steps.
- **Journalists / researchers** looking for clean, citable explanations of scam patterns.

### Brand voice

- **Calm, clear, not alarmist.** Scam victims feel ashamed; the tone must be reassuring, not patronising.
- **Practical.** Every guide ends with "What to do now" steps and reporting links.
- **British.** Spelling, currency, agencies, examples — all UK.
- **Plain English.** Reading age ~12. No legal jargon.
- **Honest about AI.** The About page openly discloses Claude-assisted drafting.

### Voice anti-patterns to avoid

- "You won't believe…" or any clickbait headline structure
- Fear-mongering statistics without sources
- Sales-y CTAs around the scam checker (it's free; positioning it as a product undermines trust)
- Affiliate disclosures buried at the end of articles

---

## 16. Legal, Compliance, GDPR & Privacy

### Pages

| Page | URL | Status |
|---|---|---|
| Privacy Policy | `/privacy/` | Live |
| Cookie Policy | `/cookies/` | Live |
| About | `/about/` | Live — with E-E-A-T signals (editor byline, methodology, AI disclosure, sources, last reviewed date) |
| Contact | `/contact/` | Live |
| Terms of Use | `/terms/` | Live |
| Disclaimer | `/disclaimer/` | Live — not professional advice, AI-checker limits, liability (added 2026-06-24) |
| Affiliate Disclosure | Inside Terms (§ Advertising and product recommendations) + Disclaimer | Currently unpaid editorial picks (`rel="nofollow"`); add a dedicated page only if paid affiliates go live |

### GDPR / UK GDPR / Data Protection Act 2018

- **Data controller:** SideRight Apps (Alex)
- **Data controller contact:** `privacy@beatthescam.com` (activate this alias)
- **Lawful bases used:**
  - **Legitimate interest** for GA4 analytics (with IP anonymisation)
  - **Consent** for AdSense personalised ads + analytics in the UK/EEA, collected via **Google's certified CMP** (AdSense → Privacy & messaging, IAB TCF) driving Google Consent Mode
  - **Contract / legitimate interest** for the scam checker (user-initiated submission)
- **Data retention:**
  - Scam checker submissions: **not stored** (stateless function — Anthropic processes, returns, discarded)
  - Analytics: GA4 default retention (14 months)
  - Newsletter: **live (double opt-in via Resend)** — address + consent kept until the subscriber unsubscribes; recommend a periodic inactive purge
- **Data processors:**
  - Google (GA4, AdSense)
  - Anthropic (scam checker AI inference — see Anthropic's UK/EU data residency posture)
  - Netlify (hosting)
  - GitHub (source code, not user data)
- **User rights:** Access, rectification, erasure, restriction, portability, objection. Requests handled via `privacy@beatthescam.com`.
- **Children:** Site is not directed at under-13s; AdSense `tagForChildDirectedTreatment` is not set.
- **International transfers:** Google + Anthropic both operate transfers under SCCs / UK IDTA.

### PECR (UK cookie law)

- Consent for **non-essential** cookies (GA4, AdSense) in the UK/EEA is collected by **Google's certified CMP** (AdSense → Privacy & messaging), which drives Google Consent Mode (both "advertising" and "analytics" consent-mode toggles enabled). Reject-all ("Do not consent") is enabled for all EEA+UK+CH countries.
- `assets/app.js` **defers** to the CMP when a TCF API is present (`window.__tcfapi`/`window.googlefc`): the custom banner stays hidden and the footer "Cookie settings" reopens the CMP. The custom banner in `app.js` is now only the **fallback** for regions where Google's message isn't shown.
- Consent Mode defaults are denied; tags load but stay cookieless until consent (Advanced consent mode pattern).

### CCPA / CPRA (US California)

- Limited applicability — but providing a "Do Not Sell My Info" link is good practice if AdSense personalised ads are used
- Recommend adding a CCPA-flavoured opt-out in the cookie banner

### Editorial / defamation

- Never name specific individuals as scammers without verified law-enforcement / court sources
- Use generic patterns ("a caller claiming to be from HMRC") not named victims
- Be careful with brand names — say "scammers impersonating BT" not "BT scams" (BT is the victim, not the perpetrator)

### Affiliate disclosure

- ASA / CMA require disclosure of affiliate / paid relationships
- Currently disclosed inside About and at the foot of relevant articles
- **Recommendation:** add visible "Some links on this page are affiliate links" near the top of any article rendering an affiliate card

### Accessibility

- Site is mobile-responsive
- Colour contrast meets WCAG AA on body text
- All images have `alt` attributes
- **Recommendation:** run a WAVE / axe-core audit quarterly; aim for WCAG 2.1 AA across the board

### Trademark & IP

- "Beat The Scam" trademark — **not currently registered**. Recommend filing a UK IPO trademark in class 41 (educational services) and 42 (online software / AI services).
- Logo / brand assets — copyright owned by SideRight Apps.

---

## 17. Security Posture (OWASP & Internet Security)

### Audit status

- **Original audit:** 2026-04-29 → remediation completed 2026-04-30
- **Executive Verdict (external) round 1:** 2026-06-19 → 06-21 (gate hardening, editorial-accuracy layer, E-tier checker/newsletter/consent)
- **Executive Verdict (external) round 2:** 2026-06-22 — content accuracy (charity/DWP), editorial-honesty wording, function-response security headers, expiring confirm tokens, checker-logging privacy fix, supply-chain (lockfile + Dependabot + CodeQL), AdSense per-page ad policy, privacy-policy precision, DNS/email hardening (DMARC reporting, CAA, HSTS preload, M365 DKIM 2048). All A–E remediated & live; DNS ramp items tracked in `dns-hardening-checklist.md`.
- **Executive Verdict (external) round 3:** 2026-06-24 → 06-25 — function hardening (non-allow-listed `Origin` → 403; salted-hash per-IP keys + atomic compare-and-set Blobs counters; single-use confirm tokens; durable per-address + global newsletter abuse caps; 16KB body cap before parse; 20s `AbortController` upstream timeout → 504; `no-store` on every response); CSP `frame-ancestors 'none'` + `X-XSS-Protection: 0`; all GitHub Actions SHA-pinned; content gate now BLOCKs ClearScore/CallCredit-as-CRA + National-Fraud-Database→Cifas and FLAGs US-style fraud-alert/HMRC-channel absolutes; corpus content sweep (ClearScore→TransUnion, US-style "fraud alert"→Cifas Protective Registration, ~67 guides); new `/disclaimer/` page; `/check/` de-thinned (~900 words, still ad-free); 16 dead internal links repointed; honesty/consent/affiliate/freshness fixes. Live on origin/main 2026-06-25.
- **Status:** All code/content audit items remediated or verified; DNS/email-auth nearly complete — DKIM (M365 both selectors + Resend) and CAA/HSTS done; only the **DMARC enforcement ramp** (in testing at `p=none`) and optional **DNSSEC** remain. Resend DKIM stays 1024-bit (Resend offers no 2048 — closed). See `dns-hardening-checklist.md`.

### Live scan results

- **securityheaders.com:** **A** (capped by `'unsafe-inline'` requirement of AdSense + GA4)
- **SSL Labs:** **A+** (TLS 1.3, HSTS preload deployed)
- **Mozilla Observatory:** not run; the above were sufficient
- **TruffleHog (manual grep):** no matches across `dist/` or source

### Security headers in production

```
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' [Google AdSense + GA4 hosts]; … object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests; …
strict-transport-security: max-age=63072000; includeSubDomains; preload
permissions-policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
referrer-policy: strict-origin-when-cross-origin
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 0   # legacy header intentionally OFF (obsolete; "1; mode=block" can introduce XS-Leaks)
cross-origin-opener-policy: same-origin-allow-popups
reporting-endpoints: csp-endpoint="https://beatthescam.com/api/csp-report"
```

**Netlify Function responses** (these come from the function bundle, NOT netlify.toml — which doesn't reliably reach function responses): the HTML pages `confirm-subscribe.js` / `unsubscribe.js` set their own strict per-page headers (`default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'` CSP + X-Frame-Options DENY + nosniff + `no-referrer` + Permissions-Policy + 2yr HSTS, added 2026-06-22); the JSON functions (`check-scam`, `subscribe`, `csp-report`) add `nosniff` + `no-referrer`.

### OWASP Top 10 (2025) coverage

| ID | Risk | Mitigation in this site |
|---|---|---|
| A01 — Broken Access Control | Public site; no auth routes exist | N/A |
| A02 — Cryptographic Failures | TLS 1.3, HSTS preload, no PII stored | ✅ |
| A03 — Injection | Scam checker sanitises `type` field; no SQL; no shell calls | ✅ |
| A04 — Insecure Design | Stateless function, no user accounts | ✅ |
| A05 — Security Misconfiguration | netlify.toml headers verified; Server header noted (Netlify-managed) | ✅ |
| A06 — Vulnerable Components | Static site + minimal Node functions; **`package-lock.json` pins deps, `requirements-claude.txt` upper-bounded, Dependabot (npm+pip+actions) + CodeQL (JS+Python) added 2026-06-22** | ✅ |
| A07 — ID & Auth Failures | No auth in scope | N/A |
| A08 — Software & Data Integrity Failures | No CDN scripts beyond Google's; SRI not viable on AdSense; lockfile + Dependabot + CodeQL now cover dependency integrity | Partial (documented) |
| A09 — Logging & Monitoring Failures | No user accounts; Netlify function logs; **checker no longer logs raw model output (could echo user-submitted text — fixed 2026-06-22)** | Acceptable |
| A10 — SSRF | Function only calls Anthropic API; user input never used as URL | ✅ |

### Application-level security (scam checker function)

- ✅ **Origin enforced server-side:** a non-allow-listed `Origin` is rejected with **403** — CORS headers alone only hide the response from a browser; a non-browser client (curl, script) ignores them
- ✅ Rate limiting: 10/min/IP, 429 on breach — **durable via Netlify Blobs** (shared across instances/cold starts); the per-IP key is a **salted SHA-256 hash** (raw IPs are never stored) and the counter is **atomic** (compare-and-set via etag, so concurrent requests can't bypass it); falls back to in-memory if Blobs is unavailable
- ✅ **Daily spend cap:** `DAILY_CALL_CAP=2000` Anthropic calls/UTC-day (atomic Blobs counter, fails open) — bounds cost from a multi-IP burst
- ✅ **Request hardening:** 16KB body-size cap **before** `JSON.parse`; 20s `AbortController` timeout on the Anthropic call (→504); `Cache-Control: no-store` on **every** response (incl. errors/limits)
- ✅ Input sanitisation: `type` stripped of non-alphanumerics
- ✅ Output validation: verdict shape verified before returning
- ✅ Error handling: generic 500s only, no stack-trace leakage
- ✅ Safe DOM rendering: `createElement` + `textContent`; reporting links restricted to an **allow-list of official UK reporting domains** (not just any `https://`)

### Newsletter functions (subscribe / confirm-subscribe / unsubscribe)

- ✅ Double opt-in; per-IP rate limit; origin allow-list; honeypot
- ✅ **Confirm tokens now carry a signed 7-day expiry** (3-part `email.exp.sig`, HMAC over `"confirm:"+email+":"+exp`) — a captured link stops working after it lapses (2026-06-22)
- ✅ **Confirm tokens are single-use** — consumed in Netlify Blobs on first confirm (released on add-failure so a transient error doesn't burn a valid link); a replayed 7-day link can no longer silently resurrect an unsubscribed contact (reactivation via PATCH-on-duplicate now needs a **fresh** token)
- ✅ **Durable abuse caps** (subscribe): per-address daily limit + global daily send cap (Blobs, hashed key) bound newsletter-bombing that rotating IPs would slip past the per-IP limit; non-allow-listed `Origin` → **403**; 16KB body cap; `no-store` on all responses
- ✅ GET renders a confirm page only (scanner/prefetch-safe); POST mutates

### Repository hygiene

- ✅ No `.env` files in git history
- ✅ No exposed keys in `dist/` or source
- ✅ No source maps in production
- ✅ API keys rotated 2026-04-28 after suspected exposure
- ✅ **`package-lock.json` + upper-bounded `requirements-claude.txt`; Dependabot (npm + pip + github-actions) + CodeQL SAST (JS + Python) — added 2026-06-22**

### Watch points (do NOT regress)

1. **Netlify publish directory** must remain set to `dist`. If it's "Not set", all `netlify.toml` headers silently stop applying. Canonical check:
   ```bash
   curl -sI https://beatthescam.com/assets/styles.css | grep -i cache-control
   # Expected: cache-control: public, max-age=31536000, immutable
   ```
2. **`'unsafe-inline'` in CSP** — required for AdSense + GA4. Path to A+ is per-request nonces via Netlify Edge Functions. Deferred until revenue justifies the engineering time.

### Re-scan cadence

| Tool | URL | Target | Cadence |
|---|---|---|---|
| Security Headers | https://securityheaders.com/?q=beatthescam.com | A or A+ | Quarterly |
| SSL Labs | https://ssllabs.com/ssltest/analyze.html?d=beatthescam.com | A+ | Quarterly |
| Mozilla Observatory | https://developer.mozilla.org/en-US/observatory/analyze?host=beatthescam.com | B+ or higher | Annually |
| CSP Evaluator | https://csp-evaluator.withgoogle.com/ | No high-risk findings beyond known `'unsafe-inline'` | After any CSP change |

### Internet-security best practices (operational)

- 2FA enabled on: GitHub, Netlify, Google, Anthropic Console, Awin, Impact, CJ, ElevenLabs, TikTok, YouTube
- Password manager in use (recommend 1Password / Bitwarden)
- Recovery codes printed and stored offline
- Backup of `posts.json`, `affiliates.json`, `site.json`, `templates/`, `scripts/`, `assets/` — git is primary; secondary cold backup recommended (S3 + offline drive quarterly)
- Domain registrar lock enabled
- DNSSEC **not enabled** — blocked on Dynadot (requires third-party nameservers); deferred unless DNS is moved (see Section 8 + `dns-hardening-checklist.md`)
- Domain transfer auth code stored in password manager, not email

---

## 18. Site Files: sitemap.xml, robots.txt, ads.txt, llms.txt

### `sitemap.xml`

- Auto-generated by `build.py`
- Lists all guides + category pages + the home page + `/check/` + legal pages
- Submitted to Google Search Console and Bing Webmaster Tools
- Excludes 404, `_redirects`, `robots.txt`

### `robots.txt`

Current contents (auto-generated by `build.py`):

```
User-agent: *
Allow: /
Disallow: /search/
Disallow: /*.php$
Disallow: /*?l=
Disallow: /api/
Disallow: /.netlify/

Sitemap: https://beatthescam.com/sitemap.xml
```

**Important — do not block:** `Mediapartners-Google`, `AdsBot-Google`, `Googlebot`, `Bingbot`, `Twitterbot`, `facebookexternalhit`, `LinkedInBot`. The current config is permissive to these by default.

### `ads.txt`

```
google.com, pub-1606633100797174, DIRECT, f08c47fec0942fa0
```

- Served at `https://beatthescam.com/ads.txt`
- AdSense dashboard shows as **Authorised**

### `llms.txt` ✅ Live since 2026-05-30

[`llms.txt`](https://llmstxt.org/) is the emerging standard for telling LLM crawlers (ChatGPT, Claude, Perplexity, Gemini) what content on the site is canonical and citation-worthy. **Live at https://beatthescam.com/llms.txt** — generated by `scripts/build.py` from `content/posts.json` on every build.

Structure: a brief site description, then categories listed (with guide counts), then every guide grouped by category with title + URL + description, then an "Optional" section for About/Contact/Privacy. Line count will drift with corpus size — check `dist/search.json` for the exact current figure (181 entries as of 2026-07-10).

Impact: AI Search Health jumped from 88% → 99% in the Semrush audit on the next crawl after deployment.

**Editing:** don't hand-edit `dist/llms.txt` — it's regenerated every build. Change the structure or copy in `scripts/build.py` (search for `llms.txt — markdown index`).

### `security.txt` ✅ Live since 2026-06-04

[RFC 9116](https://securitytxt.org/) compliant. **Live at https://beatthescam.com/.well-known/security.txt** — auto-generated by `scripts/build.py` so the `Expires` field always stays under the 1-year RFC ceiling without manual upkeep (bumps to `today+335 days` on every build).

Current contents:

```
Contact: mailto:security@beatthescam.com
Contact: https://beatthescam.com/contact/
Expires: <today+335 days, ISO 8601>
Preferred-Languages: en
Canonical: https://beatthescam.com/.well-known/security.txt
```

**To change:** edit the `security_txt = ...` block in `scripts/build.py` (search for "security.txt (RFC 9116)"). Already using the dedicated `security@` alias, activated 2026-06-09 (`content/site.json`'s `security_email` key, rendered here by `build.py`). PGP signing not implemented — major publishers (Google, GitHub, Cloudflare) don't sign theirs either; defer unless a real vuln-disclosure programme starts.

### `humans.txt` *(optional — nice-to-have)*

A short credits file at `/humans.txt`. Useful for buyers / future contractors. Optional.

---

## 19. Operational Runbook & Routine Tasks

### Daily (automated)

- ✅ 05:07 UTC — Daily AI publish workflow: generates from the queue, runs `content_gate.py`, builds, then **opens a review PR** (label `auto-content`) instead of publishing directly — nothing goes live until the operator merges it.
- ✅ 05:23 UTC — Search Console article generator: same gate → build → **review PR** flow (fails loudly on a dead GSC token, doesn't silently no-op).
- ✅ Tweet on publish — handled by a separate workflow, `tweet-on-publish.yml`, triggered by the post-merge push to `main` (not by either daily cron itself); tweets only the slug(s) added in that push.

### Weekly (automated)

- ✅ Monday 06:00 UTC — Weekly editorial audit digest (`.github/workflows/weekly-audit.yml`) emails flag-tier claims from recent guides for human review.

### Weekly (manual)

- Reply to any contact-form / `hello@` emails
- Reddit / Quora — 3–5 contributions per week
- Outreach — 5–10 link-insertion / guest-post emails per week
- Search Console — glance at queries, look for new near-miss opportunities

### Monthly

- Review Netlify build credit usage
- Review AdSense earnings (once approved)
- Review affiliate dashboards (Awin, Impact, CJ)
- Add 30+ new topics to `content/daily-publish-queue.csv` if running low
- Quarterly: re-run security scans (see Section 17)

### Quarterly

- ✅ 1st of Jan/Apr/Jul/Oct, 09:00 UTC — Fact re-verification (`.github/workflows/fact-reverify.yml`) re-checks the whole live corpus against current primary sources and opens a review PR (label `fact-audit`) — review and merge/close it
- Security re-scan (Security Headers, SSL Labs)
- Accessibility audit (WAVE / axe-core)
- WCAG 2.1 AA spot-checks
- Review and rotate API keys
- Review and update affiliate `href` values
- Backup `content/` and `assets/` to offline cold storage

### Annually

- Trademark renewal (once filed)
- Domain renewal — set to auto-renew
- HSTS preload re-verification
- Full content audit — kill or rewrite any guide >18 months old
- Reapply to any rejected affiliate networks

### Push to GitHub from local

```bash
# Set authenticated remote (PAT with repo + workflow scopes)
git remote set-url origin https://YOUR_TOKEN@github.com/siderightapps-hub/beatthescam-site.git

# Pull, commit, push
git pull --rebase origin main
git add -A
git commit -m "Your message"
git push origin main

# Clear token from remote immediately after
git remote set-url origin https://github.com/siderightapps-hub/beatthescam-site.git
```

Revoke PATs after use at github.com → Settings → Developer settings → Personal access tokens.

---

## 20. Known Issues & Watch Points

1. **Netlify publish directory dependency.** The dashboard's *Publish directory* must be set to `dist`. If "Not set", `netlify.toml` `[[headers]]` blocks silently stop applying. **Canonical check:** `curl -sI https://beatthescam.com/assets/styles.css | grep -i cache-control` must return `public, max-age=31536000, immutable`.

2. **`netlify.toml` redirects only work for the two grandfathered rules.** `[[redirects]]` works for the original `/api/check-scam` rewrite and the catch-all 404, but **any newly added toml rule is silently ignored at the edge** — not just category 301s. Confirmed 2026-06-09: the freshly added `/api/subscribe` → function rewrite 404'd from toml while `/.netlify/functions/subscribe` resolved fine. **Workaround (always):** put every new redirect/rewrite in `dist/_redirects` (auto-generated by `build.py`). API `200` rewrites are emitted at the **top** of that file because first-match-wins and a rewrite must precede any catch-all. Do **not** add new `[[redirects]]` to `netlify.toml` expecting them to work.

3. **Daily pipeline git-conflict risk — RESOLVED 2026-05-21.** Both `daily-publish` (now 05:07 UTC) and `daily-search-console` (now 05:23 UTC) regenerate `dist/sitemap.xml` from `posts.json`. When daily-publish overran the 15-minute window the two ran concurrently, the second push hit a rebase conflict on `dist/sitemap.xml`, and the previous "stash + checkout + stash-pop" recovery branch failed because `dist/` is derived (not authored) content and can't be merged. **Fix:**
   - Both workflows now share a `concurrency: group: content-pipeline, cancel-in-progress: false` block — GitHub Actions queues them instead of letting them race.
   - The rebase-conflict recovery path was rewritten to: snapshot our `content/*` changes to `/tmp/`, `git reset --hard origin/main`, merge new posts back in via `scripts/merge_new_posts.py` (matches by slug), rebuild `dist/` from scratch via `scripts/build.py`, then commit + push. `dist/` is never merged.
   - **Canonical detection:** if a workflow run fails with "CONFLICT (content): Merge conflict in dist/sitemap.xml" the concurrency group is misconfigured. Both workflows must reference the same group name.

4. **Daily pipeline git-conflict risk (human-during-pipeline).** A manual push during a pipeline run can still trigger the rebase-conflict path. Now handled by the same snapshot/reset/rebuild recovery — should self-heal up to 3 retries.

   **GitHub-Actions scheduled cron is best-effort, not on-time.** The `schedule:` event docs explicitly state runs can be delayed by hours during periods of high load — and "high load" includes the start of every hour and popular minute slots (`:00`, `:15`, `:30`, `:45`). Example seen on 2026-05-21: a `'30 6 * * *'` cron fired at 10:09 UTC, 3.5 hours late. Mitigations: (a) use off-peak minute and hour slots — current schedules are `'7 5'` and `'23 5'`; (b) don't rely on exact ordering between two crons — use the `concurrency:` group to queue them; (c) for guaranteed-time execution, point an external cron service at the GitHub `repository_dispatch` API endpoint.

5. **Netlify credit usage cap.** 1,000 credits/month. Pipeline only deploys when `dist/` changes. Monitor monthly.

6. **AdSense approval delay.** Site has been in review since ~2026-04-21 (re-started after `ads.txt` fix) — well past the original "chase after 14 days" trigger as of 2026-07-04. Chase now if still pending; current status can't be verified from the repo.

7. **Awin rejected.** Reapply window opened 2026-06-12 with Search Console traffic data — that date has passed (today is 2026-07-04); confirm with the operator whether the reapply happened.

8. **Content queue depletion.** ~30 topics remaining in `content/daily-publish-queue.csv` at 1/day (the daily-publish cron's actual rate — verified against the CSV: 214 rows, 30 not yet published) = ~30 days. Add new topics before queue empties.

9. **Local Mac keyboard interference.** Some pasted commands containing `build.py` were silently converted to markdown link format on the local laptop. Workaround: tab-completion or rename file when running locally. CI is unaffected.

10. **GitHub PAT must include `workflow` scope** to modify `.github/workflows/*.yml`. Default `repo`-only tokens fail.

11. **`'unsafe-inline'` CSP trade-off.** Capped at security-headers grade A. Path to A+ is per-request nonces via Edge Functions — deferred.

12. **Bullet-list rendering bug.** Fixed in both renderer (`build.py`) and generator (`generate_content_claude.py`). Layer 3 (cleaning the broken-shape data already in `posts.json`) is optional — not urgent.

13. **Experian affiliate URL is unstable.** The `experian-identity` entry in `content/affiliates.json` deliberately points to the **main consumer landing** `https://www.experian.co.uk/consumer/` rather than a product-specific page. On 2026-05-30 we discovered Experian had retired their standalone product URLs (`/consumer/identity-plus.html`, `/identity-protection.html`, `/free-credit-score.html`, etc. all 404) and only the main consumer landing returns 200. HEAD-checked nine plausible candidates before settling on the landing. **If you ever update this URL, run a quick `curl -I` HEAD-check first** — Experian's URL scheme is JS-driven and they restructure regularly. A future swap to a more specific page is fine as long as you verify it's live first. The dead URL previously generated **84 broken-link warnings** (one entry, fanned out across every affiliate-matched guide page) in the Semrush audit.

14. **Google Disavow tool requires URL-prefix property, not Domain property.** Search Console disavow tool flat-refuses Domain properties ("Domain properties are not supported at this time"). We added `https://beatthescam.com/` as a URL-prefix property specifically to enable disavow uploads — leave it verified. See Section 14 Disavow Policy.

15. **Semrush "uncompressed JS/CSS" is unfixable AdSense.** ~191 pages flagged because Google serves `pagead2.googlesyndication.com/.../adsbygoogle.js` without the compression header Semrush expects. We don't control Google's CDN. Don't waste cycles trying to clear this warning — only path is removing AdSense (irrational) or lazy-loading the AdSense script (small revenue trade-off). Site Health is otherwise 98% — that 191 is the irreducible floor.

16. **Mailbox aliases — DONE 2026-06-09.** `abuse@`, `hello@`, `legal@`, `privacy@`, `security@`, `socialmedia@` are all live and routed to dedicated inboxes, driven by `content/site.json` keys `security_email`/`privacy_email`/`legal_email` (`security.txt` + contact page → `security@`; Privacy/Cookie policies → `privacy@`; Terms/copyright → `legal@`; general/editorial stays on `hello@`). No open item here — see `docs/next-session.md` for anything DNS-level still tracked.

17. **No `/terms/` page audit confirmed.** Verify it exists and is current.

18. **No formal trademark filing.** Recommend UK IPO classes 41 + 42.

19. **GSC OAuth token expires ~weekly (Testing-mode app).** Google expires refresh tokens after ~7 days when the OAuth consent screen is in "Testing", rotting BOTH the local `token.json` AND the `GOOGLE_SEARCH_CONSOLE_TOKEN` CI secret on the same clock. Symptom: `invalid_grant: Token has been expired or revoked`. **(Fixed 2026-06-20)** `daily-search-console.yml` previously wrapped generation in `|| true`, so an expired CI token silently produced nothing without failing the run; it now captures the exit code and **fails the step loudly** with a GitHub error annotation, so a dead gap pipeline is visible. **Re-auth:** `python3 scripts/auth_google.py` (browser), then copy the new `token.json` into the CI secret. **Permanent fix:** publish the OAuth consent screen to "In production". (3 `client_secret*.json` files exist in the repo root — only the `758467619755…` ones are Desktop clients; `auth_google.py` now prefers a Desktop client and falls back to browser login on a dead refresh token.)

20. **Check GSC demand before deleting pages for AdSense.** The 2026-05-24 "low value content" purge 301'd the site's HIGHEST-demand URLs (`dpd-delivery-scam-text` = 1,905 impr / pos 10.2, plus yodel/ups) to a thin category page, collapsing the courier cluster within ~2 weeks (resurrected 2026-06-05 via `scripts/recover_courier_guides.py`). The sin was *thinness* (<300-word stubs), not the topic — pull `scripts/gsc_report.py` before purging anything.

21. **The video music bed must never deploy.** `assets/audio/news-bed.mp3` is a licensed local render asset; most free-stock-music licenses forbid redistributing the raw file. `build.py`'s assets→dist copytree excludes `assets/audio/` (+ `*.mp3/wav/aac`), and `.gitignore` excludes `assets/audio/`. Don't remove either guard. Off-site brand assets live in `brand/` (also not copied to `dist/`).

22. **LinkedIn caps Company-Page creation (~7-day rolling window).** Creating several pages in a week (e.g. for sister publications) trips a "wait 7 days to create more pages" limit. Personal-profile edits are not limited.

23. **Newsletter is double opt-in (2026-06-20) — `UNSUBSCRIBE_SECRET` is now required for signup.** `subscribe.js` no longer adds the contact; it emails an opaque (encrypted) confirm link and `confirm-subscribe.js` adds the contact + sends the welcome only after the link is clicked (GET = confirm page, POST = mutate, like `unsubscribe.js`). The confirm token is purpose-bound (NOT interchangeable with the unsubscribe token; opaque AES-256-GCM format as of 2026-06-25 — see #28). Consequence: if `UNSUBSCRIBE_SECRET` is unset, signups now **500** (previously they only shipped without an unsubscribe link). The front-end success copy says "check your inbox to confirm", not "you're in".

24. **The repo now has a `package.json` (functions only) — the first JS dependency.** `@netlify/blobs` backs the checker's durable rate limit + `DAILY_CALL_CAP=2000`/day spend cap. Netlify installs function deps when bundling; this does NOT add a static-site build step (`dist/` is still published as-is). Blobs is auto-provisioned (no secret); every Blobs call is guarded so the checker degrades to in-memory limiting if Blobs is down. Don't delete `package.json` thinking the repo is "pure Python" — the functions need it.

25. **UK/EEA consent is Google's certified CMP, not the custom banner.** AdSense → Privacy & messaging serves the certified CMP (driving Consent Mode; both advertising + analytics consent-mode toggles ON; "Do not consent" ON for all EEA+UK+CH). `assets/app.js` defers to it (`window.__tcfapi`/`window.googlefc`) and hides the custom banner in-region — the custom banner is only a fallback elsewhere (app.js polls ~2.5s for the CMP before falling back, so it doesn't flash). Don't "fix" the custom banner to manage ad consent again. **CSP gotcha (hit 2026-06-21):** the CMP loads from `fundingchoicesmessages.google.com` and was CSP-blocked, so the custom banner showed instead of Google's message. Fix = allow-list that domain in `script-src`, `frame-src`, `img-src` AND `connect-src` (now done in `netlify.toml`). netlify.toml header edits only reach the edge after a Netlify **"Clear cache and deploy"**.

26. **Editorial accuracy layer = canon + manifests + weekly digest (2026-06-21).** `content/sources.json` is the VERIFIED canon of official UK reporting routes — the single source of truth for the gate's allowed phone numbers/reporting emails AND `build.py`'s on-page "Report this scam" block. Don't hard-code an org number or reporting route anywhere else; add verified ones to the canon (the gate `check_sources` FLAGS non-canon gov/police reporting emails for review — it already found a stale `*.gsi.gov.uk` address). On a gate PASS, each generator writes `content/manifests/<slug>.json` (an audit record of detected high-stakes claims — NOT a bibliography; the model has no internet so it never cites). `scripts/audit_corpus.py` re-audits all guides; the **Weekly editorial audit** Action (`scripts/audit_digest.py`) emails flag-tier claims for review. Legislation / dated-event / non-canon-source detectors are FLAG-tier (recorded, never blocking) — don't make them block (most legislation refs are correct). After any `content_gate.py` change, run the **Gate self-test** Action.

27. **AdSense is per-page now — don't re-hardcode the tag (2026-06-22).** `base.html` uses an `{{ads_head}}` placeholder; `_ads_head()`/`post_ads_mode()` in `build.py` emit no ads on `/check/` and non-personalised ads on debt/insolvency/recovery pages. If you "restore" a hardcoded `adsbygoogle.js` in the template you'll re-enable personalised ads on negative-financial-status pages (a Google policy issue) and put ads back on `/check/`. Tune the NPA set via `_SENSITIVE_FINANCE_TERMS`. Note: the comment block in `base.html` must NOT contain the literal `{{ads_head}}` token — it gets substituted and can break the HTML comment (caught + fixed during the 2026-06-22 work).

28. **Function security headers live in the function code, not netlify.toml (2026-06-22).** `confirm-subscribe.js`/`unsubscribe.js` set their own `SECURITY_HEADERS` const on HTML responses (netlify.toml headers don't reliably reach function responses — see gotcha #2).
    - **Newsletter tokens are OPAQUE (AES-256-GCM) as of 2026-06-25** — email (+ 7-day expiry for confirm) sealed under an HKDF key from `UNSUBSCRIBE_SECRET`, domain-separated per purpose. Replaced the leaky `base64url(email).base36(exp).sig` HMAC format (non-forgeable but the plaintext email was recoverable from a captured URL — 3rd-audit finding). The mint/verify halves must stay in sync on the inlined `sealToken`/`openToken` helpers: `subscribe.js`↔`confirm-subscribe.js` (confirm) and `confirm-subscribe.js`↔`unsubscribe.js` (unsub).
    - **Dual-parse** keeps the legacy dotted HMAC formats working (discriminator: opaque tokens are **dotless**, legacy contain `.`) — don't break it while legacy links are live.
    - **Cleanup asymmetry (important):** the legacy *confirm* branch (`verifyConfirmTokenLegacy`) can be deleted 7 days after deploy (confirm TTL expires all legacy confirm links); the legacy *unsubscribe* branch (`verifyTokenLegacy`) must stay **indefinitely** — those links never expire and must keep working for compliance unless `UNSUBSCRIBE_SECRET` is rotated (which itself breaks all live links — a deliberate choice only).

29. **Supply-chain files exist now — keep them (2026-06-22).** `package-lock.json` (commit it), `requirements-claude.txt` upper bounds, `.github/dependabot.yml`, `.github/workflows/codeql.yml`. Actions are **SHA-pinned** (full commit SHA + `# vN` comment, since 2026-06-24) so Dependabot's `github-actions` updater still tracks them; keep new workflow steps SHA-pinned the same way (the 2026-06-25 PR-gate + `tweet-on-publish.yml` steps follow this).

30. **`audit_corpus.py` preserves manifest `model` provenance (2026-06-22).** A bare re-audit used to rewrite every `content/manifests/*.json` with `model: null`, wiping the model the generator recorded. It now reads the existing manifest's `model` and passes it through. The 187 legacy manifests remain `null` ON PURPOSE (the original model was never recorded — don't backfill a guessed value).

31. **`@netlify/blobs` is pinned `~10.1.0` ON PURPOSE — don't bump to 10.2.0+ (2026-06-25).** The functions' atomic counters/tokens use the conditional-write API (`onlyIfMatch`/`onlyIfNew`/`setJSON`→`{modified}`), which **only exists in v10+** — under the old `^8.1.0` pin (resolving to 8.2.0, where `setJSON`→`void` and `SetOptions={metadata?}`) every CAS was a **silent no-op** (rate limits, spend cap, send caps, single-use confirm tokens all degraded to last-write-wins). `~10.1.0` is the newest version with the CAS API but BEFORE `@netlify/otel` enters (at 10.2.0), which pulls an OpenTelemetry chain with **6 moderate `npm audit` vulns**. So `~10.1.0` = CAS API + `npm audit` clean (34 pkgs). If Dependabot proposes ≥10.2.0, **decline** until Netlify fixes the upstream OTel vulns. 10.1.0 ships CJS + Node≥16, so no function-code change was needed.

32. **The content crons open a review PR — they do NOT commit to `main` (2026-06-25).** `daily-publish.yml`/`daily-search-console.yml` now `checkout -b auto/… → push → gh pr create` (label `auto-content`); nothing publishes, gets ads, or is tweeted until the operator merges (Google policy: auto-generated content must be reviewed before monetisation). **Prereq ✅ ENABLED 2026-06-25:** repo setting *Settings→Actions→General→"Allow GitHub Actions to create and approve pull requests"* is on, and the workflows set `permissions: pull-requests:write` + `issues:write`. Auto-tweet moved to **`tweet-on-publish.yml`** (trigger: push→main touching `content/posts.json` = post-merge; tweets only slugs ADDED in that push; **≤3-slug cap + `tweeted_posts.json` dedupe** so a bulk merge can't mass-tweet). The old rebase-conflict recovery in the crons is GONE (each branches off fresh `main` and pushes a new branch — no main-push to conflict).

33. **Gate forward-guards + checker scrubber added by the 3rd audit (2026-06-25).** `content_gate.py` `_post_text` now also covers section **headings, title, keywords** (claims there are now checked). New `check_recurring_accuracy()` adds 4 **FLAG**-tier guards — CRM-code (outdated; APP reimbursement is mandatory since 7 Oct 2024), 7726-attributed-to-NCSC (it's the mobile networks; NCSC = report@phishing.gov.uk for email), US "credit freeze", and the sextortion/deepfake "no-proof = fake" threat-dismissal heuristic — so new/locale drafts can't reproduce the audit's content errors (all FLAG → corpus stays 0 block-tier; run the **Gate self-test** Action after this lands). A 5th FLAG guard — the FCA's retired **"ScamSmart"** branding (canon: FCA Firm Checker) — was added 2026-07-09, so `check_recurring_accuracy()` now carries **5** guards. `check-scam.js` `scrubContact()` redacts prompt-injected phone/URL/email from the model's free-text fields (reporting_links stay host-allowlisted); preserves UK shortcodes + `*.gov.uk` emails. Salt now `RATE_LIMIT_SALT || UNSUBSCRIBE_SECRET || literal` (no public-known salt, no fail-closed).

34. **`build.py` has no Markdown renderer beyond backtick-code + bare-path auto-link (found 2026-07-10, during the content diversification project's final batches).** Confirmed by reading the code: article prose only supports backtick `` `code` `` spans and `linkify_bare_paths()`, which converts a literal bare `/guides/slug/` path into `<a href="...">{target page's own title}</a>` — it always substitutes the target's own title as link text, never custom text. Two real bugs this caused, both already live on published pages before being caught: (a) `[text](/guides/slug/)` bracket-link syntax isn't interpreted at all — the brackets are left as literal text while the bare path inside still gets auto-linkified, producing broken output like `[label](<a href="...">Real Title</a>)`; found on 6 already-published pages across 2 batches, fixed by rewriting to bare-path prose. (b) `**bold**` markdown has zero render support and shows as literal asterisks; found on 41 spots across 7 pages, including the core `is-this-website-a-scam` reference page. **Never use bracket-link syntax or bold markdown in article prose** — write bare `/guides/slug/` paths directly and phrase the sentence so the target's own (often long) title reads naturally as the visible link text; use plain, emphasis-free prose instead of bold. **Standard checks now, run against all of `dist/` after any content edit** (not caught by `content_gate.py`, which checks facts, not rendering): grep rendered HTML for literal `**` and for the regex `\[[a-zA-Z][^\]]*\]\(/guides/`, alongside the existing "…" truncation grep. Full detail: `docs/content-diversification-plan.md` §8's batch-20 entry.

35. **`content_gate.py` only runs ONCE, at generation time — it has no mechanism to notice a LIVE guide's facts going stale later (added 2026-07-11).** The 2026-07-10 manual full-corpus audit (16 parallel web-search agents) found real drift in guides that had been live for months: a PSTN switch-off date that moved, a retired Microsoft mailbox, a wrong CMA court-order date, a mis-routed reporting email — none of it caught by the generation-time gate or the 7-day-window weekly digest. `scripts/fact_reverify.py` + `.github/workflows/fact-reverify.yml` (quarterly, 1st of Jan/Apr/Jul/Oct) close that gap: Pass A re-runs `content_gate.run_gate(use_llm=False)` across the ENTIRE corpus regardless of publish date (surfaces old unresolved FLAG-tier claims the weekly digest's 7-day window never resurfaces); Pass B sends one Claude call per guide with the `web_search_20250305` server tool enabled, instructed to verify checkable claims (dates, figures, reporting routes, legal citations, "X was retired/rebranded") against current primary UK sources and report ONLY confirmed drift (an unverifiable claim is left alone, never guessed at). Both passes write one report to `content/fact-reverify-reports/<YYYY>-Q<N>.md` and open a PR labelled **`fact-audit`** — deliberately NOT `auto-content`, because `daily-publish.yml`'s backlog guard skips generation while any `auto-content` PR is open, and a fact-audit PR under review shouldn't pause daily publishing. This script/workflow NEVER edits `posts.json`/manifests/`dist/` — same human-review-gated contract as everything else, and the same pattern already proven on the sister publication `tuningdigital`'s `fact-reverify.yml`.

36. **`content_gate.py`'s legislation-citation regex lacked a word boundary after "Act" (fixed 2026-07-10, PR #53).** `_LEGISLATION_RES` matched `[A-Z]\w+ Act` with nothing requiring a boundary after "Act", so it flagged ordinary words like "Actually"/"Action"/"Active" whenever preceded by 1–5 capitalised words after "The"/"the" — hit on a draft title "...What the Software Actually Does", which the gate flagged as if it cited "the Software Act". Fixed with a trailing `\b`; genuine citations ("the Fraud Act 2006", "the Consumer Credit Act 1974") already had a natural word boundary after "Act" so detection is unaffected.

### Anti-patterns — don't regress these

Decisions reached in prior sessions that future Claude sessions should preserve, not re-litigate:

- **Don't re-add a named editor pseudonym.** A fabricated "James Carter" persona was created earlier and explicitly retired on 2026-05-19. Article schema uses `Organization` author (`"Beat the Scam Editorial Team"`). Fabricated bylines are explicitly flagged against quality signals in Google's YMYL guidance. Only swap to a named editor if the owner provides a real person with verifiable consumer-affairs credentials.
- **Don't add phonetic overrides for HMRC / DVLA / NCSC** in `generate_video.py`'s `PHONETIC_OVERRIDES`. We tried `H. M. R. C.` (V3 elided the R) and `aitch em are see` (too rushed) — settled on bare `HMRC` because V3 handles common UK acronyms natively. Only phonetic-override genuinely tricky brand names (`Revolut` → `Rev-uh-loot`, `Evri` → `Ev-ree`).
- **Don't change the video catchphrase to an exclamation.** "Beat the Scam!" sounded too energetic. Declarative period — "Remember — Beat the Scam." — is what shipped.
- **Don't change the video voice ID without asking.** Daniel (`3WqHLnw80rOZqJzW9YRB`) was chosen after A/B against Grace.
- **Don't ship videos to `dist/`.** Video output lives at `out/videos/` (gitignored). Anything in `dist/` deploys to Netlify and would bloat the site.
- **Don't push uncommitted changes.** Default is local-only — wait for explicit "commit and push" from the owner before pushing to `main`.
- **Don't try to merge `dist/sitemap.xml` (or any derived file) during rebase recovery.** Pipeline rebase-conflict logic snapshots `content/*`, hard-resets to `origin/main`, merges via `scripts/merge_new_posts.py`, then rebuilds `dist/` from scratch via `build.py`. Don't revert to stash/checkout/pop logic.
- **Don't replace the static end card** (`assets/video/end-card.png`) with a generated one. The owner-provided designed image is more on-brand than anything generatable from text alone.

---

## 21. Outstanding Roadmap

### Recently completed (2026-07-04 → 2026-07-10 — content diversification project FINISHED, AdSense approval audit, full audit, rendering-bug fixes)

- **Content diversification project COMPLETE (batches 15–20, 2026-07-04 → 2026-07-10):** 167 pages total de-templated from the generic 6-section outline (up from 89 across batches 1–14) — **a fresh full-corpus scan confirms zero guides remain on the generic template.** Several near-duplicate consolidations resolved along the way (`mandate-fraud-uk-businesses`→`invoice-fraud-uk-businesses`, `windows-tech-support-scam-uk`→`microsoft-support-scam-uk-guide`, `push-payment-fraud-uk`→`bank-transfer-scam-uk`, others). Every batch's draft went through an independent operator fact-check before commit, which caught genuine factual errors (not just imprecision) in nearly every batch — see `docs/content-diversification-plan.md` §8 for the full per-batch detail. **Two corpus-wide rendering bugs found and fixed** while drafting the final batches: `build.py` has no renderer at all for `[text](/guides/slug/)` markdown-link syntax (only bare `/guides/slug/` paths auto-linkify, always substituting the target page's own title as link text) or `**bold**` markdown — both had been silently shipping broken/literal markup on several already-published pages across multiple batches; both are now standard checks in the build-verification routine, alongside the existing meta-description-truncation grep.
- **AdSense approval audit (2026-07-06):** site confirmed to pass all AdSense hard gates; privacy opt-out disclosures fixed and pushed live.
- **Full audit remediation (2026-07-09):** ~30 fixes pushed live (self-test passed, cache cleared); daily-publish review-PR backlog cleared.
- **Build/gate hardening (2026-07-09/10):** `build.py`'s linkifiers no longer substitute inside HTML attribute values; the build now fails outright if a live guide slug is shadowed by a forced `ARTICLE_REDIRECTS` 301 (was a silent footgun); `make_base()` does single-pass token substitution so literal `{{tokens}}` quoted in article text can't be expanded; `seo_description()` no longer produces a double-ellipsis or over-length output; 54 stale meta descriptions rewritten into the 130–160 char window; `content_gate.py`'s legislation-citation regex gained a word boundary after "Act" so it no longer flags ordinary words like "Actually" as a legislation citation.

### Recently completed (2026-06-24 → 2026-07-04 — third audit remediation, opaque tokens, human-review PR gate, content diversification, canon fix)

- **Round 3 remediation (2026-06-24/25):** fixed a critical Netlify Blobs SDK version mismatch (code used the v10 CAS API but `package.json` pinned v8, making every "atomic" rate-limit control a silent no-op) — repinned `~10.1.0`; Node 20→22; checker `scrubContact()` redacts prompt-injected contact details from model free-text; gate gained 4 new FLAG guards (CRM-code, 7726→NCSC, credit-freeze, threat-dismissal) and now reads headings/title/keywords too; legal pages excluded from ads, non-personalised-ads scope broadened to sextortion/romance/identity; 50 guides content-fixed (CRM→mandatory APP reimbursement, US-style fraud-alert/credit-freeze→Cifas, 7726→mobile networks, Companies House domain/absolutes, safety-critical sextortion/deepfake "no-proof≠fake" reframe).
- **Newsletter tokens hardened (2026-06-25):** confirm/unsubscribe tokens replaced with opaque AES-256-GCM (HKDF-derived, per-purpose keys) instead of a leaky base64url(email) format; dual-parse keeps legacy links working (unsubscribe indefinitely, for compliance; confirm for its 7-day TTL only); confirm tokens are now single-use (Netlify Blobs).
- **Content pipelines moved to human review (2026-06-25):** `daily-publish.yml`/`daily-search-console.yml` no longer commit to `main` — each opens a review PR (`auto-content` label) that the operator merges; auto-tweet moved to a separate `tweet-on-publish.yml` firing on merge (diff-based, ≤3-slug cap, deduped).
- **Content diversification (2026-06-26 → 2026-07-04):** 14 batches (89 pages) de-templated from the generic 6-section outline flagged by the 4th external audit as an AdSense scaled-content risk; full history and methodology in `docs/content-diversification-plan.md`.
- **Gate/canon fix (2026-07-04, PR #37):** added the Revenge Porn Helpline to `content/sources.json`'s canon, closing 2 BLOCK-tier findings that had crept in on two intimate-image-abuse guides ahead of the canon entry existing.

### Recently completed (2026-06-22 — second Executive Verdict remediation, A–E live)

A fresh external "Executive Verdict" audit surfaced further items; all code/content tranches (A–E) are remediated, deployed, and verified live. DNS (tranche F) is in progress — see `dns-hardening-checklist.md`.

- [x] **Content accuracy.** Fixed the charity guide (false "all UK charities must be registered / not legitimate if unlisted" → £5,000-income + CIO rule; dead `.gsi.gov.uk` email) and the DWP benefits-text guide ("DWP number on bank card", single "DWP account" vagueness, SMS reporting route). Web-verified vs GOV.UK / Charity Commission / DWP. Corpus swept — errors were isolated.
- [x] **Editorial honesty.** Softened author bio off "every recommendation verified… before it ships"; per-post footer now describes the automated gate + Published/Updated date (not an implied human review); `audit_corpus.py` preserves manifest `model` provenance instead of nulling it.
- [x] **Function/security hardening.** Checker no longer logs raw model output; confirm/unsubscribe HTML pages get full security headers; confirm tokens now expire (signed 7-day) + reactivate-on-duplicate.
- [x] **Supply chain.** `package-lock.json`, upper-bounded `requirements-claude.txt`, Dependabot (npm+pip+actions) + CodeQL (JS+Python).
- [x] **AdSense + privacy.** `/check/` excluded from Auto Ads; non-personalised ads on debt/insolvency/recovery pages; privacy policy discloses cookies/web beacons/IP/identifiers + the NPA treatment.
- [~] **DNS/email (tranche F, nearly done).** Done: DMARC reporting (`p=none`+rua), CAA, HSTS preload submitted, M365 DKIM→2048 (**both selectors — selector 1 fixed 2026-06-25**), Resend DKIM **closed at 1024** (Resend offers no 2048). Pending: DMARC quarantine→reject ramp (in testing now), DNSSEC (blocked on Dynadot; optional). Full status: `dns-hardening-checklist.md`.

### Recently completed (2026-06-19 → 06-21 — Executive Verdict remediation round 1, closed)

- [x] **Accuracy gate hardened + corpus cleaned.** Added a deterministic absolute-claim check (the LLM judge alone had leaked invented stats + "no footage exists" into a gated sextortion guide); cleaned 46 guides of hardcoded org phone numbers; new legislation / dated-event / non-canon-reporting-email detectors (FLAG-tier). Corpus passes the gate with 0 block-tier claims.
- [x] **Editorial-accuracy system built.** Verified source canon `content/sources.json` (single source of truth for the gate's allow-lists AND `build.py`'s on-page reporting block); per-guide **claim manifests** (`content/manifests/`, written on every gated publish); `scripts/audit_corpus.py` (re-audit all) + **weekly audit digest** (`scripts/audit_digest.py`, `.github/workflows/weekly-audit.yml` — emails flag-tier claims via Resend). Human review is the digest (tiered), not per-article blocking — preserves the autonomous model. The verdict's deeper "claim manifests + human approval for high-stakes claims" recommendation, done without LLM-authored (hallucinated) citations.
- [x] **Checker, newsletter, consent hardened (E-tier).** Reporting-link domain allow-list in `check-scam.js`; durable per-IP rate limit + `DAILY_CALL_CAP=2000`/day spend cap via Netlify Blobs (first `package.json`); newsletter **double opt-in** (`subscribe` → `confirm-subscribe`); UK/EEA consent via **Google's certified CMP** (CSP allow-listed, app.js defers to it).
- [x] **Quality + hygiene.** Site-wide search (lean `search.json`); 53 de-dangled SEO titles; affiliate cards "Sponsored"→"Recommended" (`rel=nofollow`, unpaid); Search Console workflow fails loudly (no more `|| true`); Anthropic 30-day retention disclosed; full docs reconciliation.
- [x] **Last residuals closed.** Malformed model output no longer publishes a thin fallback guide (quarantines instead — `generate_content_claude.py`); **privacy notice completed to the ICO "right to be informed" checklist** (controller, lawful bases, consent withdrawal, all rights, right to complain to the ICO, automated-decisions + transfers); fixed 4 real content errors the audit surfaced — 3 stale/wrong reporting routes (decommissioned `*.gsi.gov.uk`, non-existent `abuse@justice.gov.uk`, OISC→IAA) and a mis-cited Act (Section 75 is the **Consumer Credit Act 1974**, not the Consumer Rights Act). **No open defects from round 1 remained** (a second external verdict on 2026-06-22 surfaced the further items in the block above, now also remediated).

### Recently completed (2026-06-05 → 06-07 session)

- [x] **Reclaimed the courier guides killed by the AdSense purge.** A live GSC review (new read-only `scripts/gsc_report.py`) found the site's highest-demand URLs had been 301'd to a thin category page by the 2026-05-24 purge — `dpd-delivery-scam-text` alone had **1,905 impressions at pos 10.2**. Resurrected **DPD / Yodel / UPS** as full ~1,000-word guides at their original URLs (`scripts/recover_courier_guides.py`), removed from `ARTICLE_REDIRECTS`, live. Lesson logged in Section 20.
- [x] **Search Console auth + tooling fixed.** Re-authed the GSC OAuth token (was `invalid_grant`), refreshed the `GOOGLE_SEARCH_CONSOLE_TOKEN` CI secret, and fixed `scripts/auth_google.py` (deterministic Desktop-client selection + browser-fallback on a dead refresh token). New `scripts/gsc_report.py` for read-only query/page/near-miss pulls.
- [x] **Cross-platform video analytics verdict.** TikTok ~4s avg watch / ~1% completion (high reach, instant swipe-away); YouTube Shorts 14–49s / 35%+ (the format works); Instagram + X negligible reach. **Verdict: platform fit, not a broken hook — YouTube Shorts + the site are the two real channels.** Running one TikTok creative A/B (`generate_video.py --motion-hook`, a fade-in-from-black hook reveal) on the F1 video to confirm before deprioritising TikTok; result ~2026-06-14.
- [x] **Video-pipeline bugs fixed for good.** `shorten_warning()` was truncating warnings mid-list ("…bank transfer, gift cards" dropping "or cryptocurrency"); rewrote it with a universal dangling-word stripper + first-sentence preference + list-strand guard — audited to **0 breaks across all 168 posts** (was 20). Added the music bed (`assets/audio/news-bed.mp3`, −20 dB) **and** a deploy guard so the licensed file never ships (`build.py` excludes `assets/audio/`, gitignored).
- [x] **Tier 1 backlink / citation foundation built.** Self-serve citations live — About.me, Trustpilot, Owler, F6S — plus a refreshed LinkedIn personal profile (banner, headline, About, Experience) **and** a new Company Page. Three trusted-body affiliations sent (Take Five, Friends Against Scams, Get Safe Online). Author role standardised to **"Founder & Editor"** everywhere (`content/site.json`). Tracked in new `docs/outreach-log.md` + `docs/outreach-templates.md`.
- [x] **`CLAUDE.md`** added for Claude Code onboarding; **`brand/`** folder added for off-site marketing assets (logos, LinkedIn banners).

### Previously completed (2026-06-04 session)

- [x] **`/terms/` full UK best-practice rewrite** (commit `4ccff539`) — 130 → 891 words, 12 H2 sections. Adds the legally meaningful gaps: visible "Last updated" date (tracked via `TERMS_LAST_UPDATED` in build.py), affiliate disclosure (UK ASA CAP Code), AdSense disclosure (Google publisher T&Cs), acceptable use, IP/copyright, limitation of liability with statutory carve-outs, changes-to-Terms clause, and a tri-jurisdictional governing-law clause (**England & Wales** primary, **Scots law** for Scottish residents with Scottish courts non-exclusive, **Northern Ireland courts** non-exclusive for NI residents). AI scam checker carve-out + Action Fraud (since rebranded "Report Fraud") reporting route included.
- [x] **GSC failing-validation URL triage** (commit `2d57d2e0`) — of the 10 "Not found (404)" URLs flagged on 2026-06-04, only 1 needed an on-site fix: dead `/guides/crypto-investment-scam-uk-guide/` → article-redirect to live `crypto-investment-scams-uk-protection` in `ARTICLE_REDIRECTS`. The other 9 were already resolved by earlier work (etsy resurrection, 6 old-category-slug redirects, 2 spam `/search/portal.php` URLs blocked by robots.txt) — they were just waiting on GSC to re-crawl. Server-error (5xx) `refund-scam-uk` was transient Netlify hiccup; now returns 200 via existing redirect.
- [x] **Named author + cross-publication E-E-A-T** (commits `df970801`, `a5149502`, `12da2b75`) — promoted `author` from "Beat the Scam Editorial Team" (Organization) to **Alex Bacsa** (Person) with `@type: Person`, `jobTitle`, `image`, and full `sameAs` array (LinkedIn + CloudFintech `/author` + TuningDigital `/about` + SalesTap `/about`) on every guide's schema.org JSON-LD. Built `/author/` page mirroring CloudFintech's structure — hero with role + based-in, headshot, bio, expertise badges, "Also publishes on" 3-card grid, social links. About page intro rewritten to introduce Alex + sister publications inline. Headshot: real photo, centre-square-cropped to 400×400 PNG, optimised 514KB → 67KB. Sniper-scope-on-silhouette SVG (inherited from TuningDigital) retired here — wrong polarity for a consumer-protection brand.
- [x] **`/.well-known/security.txt`** (commit `c9a051e1`) — RFC 9116 compliant, auto-generated by build.py with rolling `Expires` (today+335d) so it never silently expires.
- [x] **Mobile LCP optimisation** (commit `3ff7ff4a`) — upgraded `pagead2.googlesyndication.com` and `tpc.googlesyndication.com` from `dns-prefetch` to `preconnect` with crossorigin. Lighthouse baseline before fix: homepage mobile FCP 2.4s / LCP 2.9s (amber). Expected post-deploy: FCP ≤ 1.8s / LCP ≤ 2.5s (green).
- [x] **PageSpeed Insights baseline captured** — homepage 92, sample-guide 97, author 97 (all mobile, all green). Guide page CLS = 0 (exceptional). One known amber pre-fix: homepage FCP/LCP (preconnect commit above is the targeted fix). Re-check after Netlify deploys.

### Previously completed (2026-05-30 session)

- [x] **`llms.txt` generation added to `build.py`** — live at `/llms.txt`, regenerated every build (see Section 18). AI Search Health 88% → 99%.
- [x] **YouTube OAuth setup complete** — `scripts/upload_to_youtube.py` works end-to-end; OAuth app moved to Production so refresh tokens no longer expire on the 7-day Testing cycle. Helper script auto-writes `YOUTUBE_REFRESH_TOKEN` straight into `.env`.
- [x] **Instagram channel activated** — `@beatthescamuk` (Creator account, bio link to beatthescam.com). Every `.upload.md` now carries a paste-ready Reels block (same 1080×1920 MP4 as Shorts/TikTok — zero re-render).
- [x] **Semrush remediation pass** — Site Health 96% → 98%, AI Search Health 88% → 99%. Cleared 84 broken-link warnings (single dead Experian affiliate URL), 157 "paragraphs too long" warnings (added sentence-aware paragraph splitter in `build.py`), 6 "poor heading hierarchy" on listing pages (added `<h2>` between H1 and card grid), 7 "no anchor text" warnings (nested-anchor guard in `apply_internal_links`). Minified `dist/assets/styles.css` + `app.js`. 191 residual "uncompressed" warnings are Google's AdSense CDN — irreducible.
- [x] **Google disavow file uploaded** — 66 domains (Section 14 Disavow Policy). Added URL-prefix Search Console property `https://beatthescam.com/` to enable the tool.

### This week / next session

Superseded by [`docs/next-session.md`](next-session.md), which is updated far more frequently — maintaining the same status in two places is what let this subsection go stale. Check that file for the current punch list.

### Near-term (4–8 weeks)

- [ ] Near-miss query optimisation pass (top 5 queries from Search Console)
- [ ] Contextual in-body internal-linking sweep across top 30 guides
- [ ] Replace placeholder `href` values in `affiliates.json` as programmes approve
- [ ] Reapply to Awin (window opens 2026-06-12)
- [ ] Follow up CJ Affiliate
- [ ] Direct outreach: Experian, Norton, Which? Legal, Cifas
- [ ] AdSense approval — chase if still pending after 2026-05-25
- [ ] Foundation backlinks: niche directory submissions (5/week for 6 weeks)
- [ ] Reddit / Quora cadence — 3–5/week

### Medium-term (8–24 weeks)

- [ ] **URL Checker feature** — integrate VirusTotal + Google Safe Browsing into the scam checker. Biggest single SEO/PR opportunity on the site.
- [ ] **Email newsletter** — list-building for direct revenue + domain value. Provider TBD (ConvertKit / Buttondown / MailerLite).
- [ ] **"Was this guide helpful?" widget** — Yes/No micro-feedback for dwell-time signals and editorial improvement.
- [ ] First guest-post placement on a DA 40+ UK publication
- [ ] HARO / Featured.com responses → first quoted-source placement
- [ ] Trademark filing (UK IPO classes 41 + 42)
- [ ] WCAG 2.1 AA accessibility audit
- [ ] Set up offline cold backup cadence

### Long-term (6–12 months)

- [ ] CSP nonces via Netlify Edge Functions → security-headers A+
- [ ] Scaled content (>200 guides)
- [ ] Sponsored "UK Scam Trends 2026" report (co-branded with an identity-protection brand)
- [ ] Mobile-app conversation: standalone scam-checker app potential
- [ ] Multilingual: Welsh-language pages for Welsh consumer-protection coverage

---

## 22. Asset Valuation & Acquisition Brief

> Maintained for potential buyer / acquirer briefings.

### What's included

- Domain: `beatthescam.com` (exact-match keyword, ~3 months old, no penalties, clean WHOIS)
- GitHub repository (`siderightapps-hub/beatthescam-site`) — full transfer
- 189 original UK-focused guides in `content/posts.json`
- AI scam checker (live, rate-limited, secured)
- Daily content generation pipeline (GitHub Actions + Anthropic Claude)
- Netlify hosting setup (transferable)
- Google Analytics 4 property
- Google AdSense Publisher ID (in review — will need re-verification on transfer)
- Social channels: Twitter `@BeatTheScamUK`, TikTok `@BeatTheScamUK`, Instagram `@beatthescamuk`, YouTube "Beat The Scam"
- 3 published Shorts/TikToks (and assets)
- All branding assets (logo variants, OG image, banners, end card)
- This document and all session handoff documents

### Valuation matrix

| Scenario | Monthly traffic | Monthly net revenue | Estimated value (30–40× multiple) |
|---|---|---|---|
| Conservative | 2,000–5,000 visits | £30–£80 (AdSense only) | £1,000–£3,000 |
| Moderate | 10,000–25,000 visits | £250–£700 (AdSense + 1–2 affiliates) | £8,000–£25,000 |
| Strong | 40,000–80,000 visits | £900–£2,200 (AdSense + 3–4 affiliates) | £30,000–£80,000 |
| Premium (with URL checker + newsletter) | 80,000+ visits | £2,500–£5,000+ | £80,000–£200,000+ |

Plus the **standalone domain value** (`beatthescam.com` as an exact-match keyword in the consumer-finance / cybersecurity vertical) — comparable category-defining domains have sold for £5,000–£25,000 alone.

### Buyer fit

- UK identity-protection brand (Experian, Cifas, CreditExpert)
- Cybersecurity SaaS (Norton, McAfee, Bitdefender) wanting UK consumer footprint
- UK insurance group with fraud-related product lines
- Consumer-finance media group (MoneyWeek, Which?, MoneySavingExpert competitors)
- UK media holding company building a portfolio

### Transfer playbook

A separate transfer-playbook document should cover: domain push, Netlify team transfer, GitHub repo transfer, GA4 property transfer, AdSense publisher transfer (re-verification required), social handle transfers (TikTok via support, YouTube via Brand Account swap, Twitter via email change), Anthropic billing reassignment, ElevenLabs reassignment, password / 2FA handover via password manager export.

---

## 23. Appendix — Reference Material

### Repository quick-reference

```bash
# Navigate
cd ~/Projects/websites/beatthescam-site

# Build
python3 scripts/build.py

# Daily pipeline (manual)
ANTHROPIC_API_KEY=… python3 scripts/run_daily_publish.py

# Tweet article
python3 scripts/tweet_new_articles.py --slug <slug>

# Preview tweet without posting
python3 scripts/tweet_new_articles.py --slug <slug> --dry-run

# Search Console gap (dry run)
python3 scripts/search_console_articles.py --dry-run
```

### `site.json` reference

```json
{
  "site_name": "Beat the Scam",
  "domain": "https://beatthescam.com",
  "tagline": "Scam alerts, plain-English checks, and practical guides to help people verify suspicious emails, texts, websites, calls, and offers.",
  "adsense_client": "ca-pub-1606633100797174",
  "contact_email": "hello@beatthescam.com",
  "author": "Beat the Scam Editorial Team",
  "twitter": "@beatthescam",
  "ga4_id": "G-JXNF856NBF"
}
```

### Category canonical map (from `build.py`)

`CATEGORY_CANON` normalises display labels to lowercase keys. Examples:
- "Marketplace Scams" → `marketplace`
- "Text Message Scams" → `sms`
- "Government Impersonation Scams" → `government`

Display labels in `CATEGORY_LABELS`; descriptions in `CATEGORY_DESCRIPTIONS`.

### External documentation links

- Google Search fundamentals: https://developers.google.com/search/docs
- Google AI optimization guide: https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- Anthropic API docs: https://docs.anthropic.com
- Netlify docs: https://docs.netlify.com
- OWASP Top 10: https://owasp.org/Top10/
- llms.txt standard: https://llmstxt.org/
- security.txt RFC: https://securitytxt.org/
- ICO (UK GDPR): https://ico.org.uk/

### Related internal documents

- `video-pipeline.md` — video production workflow & calendar (HISTORICAL — video discontinued 2026-06-15)
- `dns-hardening-checklist.md` — DNS / email-auth / TLS operator runbook (DMARC, DKIM, CAA, DNSSEC, HSTS) — tranche F of the 2026-06-22 Executive Verdict
- `project-template.md` — generic template extracted from this document

---

*End of Master Project Document. Maintained as the single source-of-truth. Update at the start of any meaningful change, and at the end of any significant session.*
