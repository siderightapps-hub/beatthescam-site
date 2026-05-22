# Beat The Scam — Master Project Document

> The single, authoritative source-of-truth document for the **Beat The Scam** brand, site, infrastructure, monetisation, security, content operations, growth strategy, and ongoing roadmap.
>
> **Audiences this document serves:**
> 1. The current owner (Alex / SideRight Apps) — operational manual.
> 2. Any new Claude Code chat session — drop-in context bootstrap (works alongside `CLAUDE.md`).
> 3. Potential buyers / acquirers — full due-diligence briefing on the asset.
> 4. Contractors, future editors, security reviewers — onboarding pack.
>
> **Last updated:** 2026-05-20
> **Domain age:** ~3 months (registered February 2026)
> **Site state:** 97+ guides published, 17 normalised categories, AI checker live, social channels active
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

1. Publishes plain-English **scam awareness guides** (now 97+ published, with a queue of additional topics being released ~5/day).
2. Offers a **free AI-powered Scam Checker** at `/check/` where users paste suspicious messages and receive a verdict, confidence score, red flags, green flags, recommended actions, and reporting links.
3. Routes users to legitimate UK reporting bodies (Action Fraud / `reportfraud.police.uk`, NCSC, FCA ScamSmart, Take Five, Citizens Advice).
4. Generates revenue via Google AdSense (in review), affiliate partnerships (Experian, Norton, Cifas, Which? Legal), and future newsletter / sponsorship channels.
5. Builds topical authority over the medium-term to rank for UK fraud and scam queries.

### Why this brand has standalone value

- The exact-match keyword domain `beatthescam.com` is short, memorable, and category-defining.
- Consumer fraud is a **YMYL** (your-money-or-your-life) niche with high RPMs once authority is established.
- The site already has 97+ original articles, technical SEO foundation, security A+, schema markup, and an AI utility (scam checker) that competitors don't offer.
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
| `socialmedia@beatthescam.com` | Social platform sign-ups, ElevenLabs, TikTok, YouTube brand account | Active |
| `privacy@beatthescam.com` | GDPR / data protection / right-to-be-forgotten enquiries | Reserved — should be activated |
| `welcome@beatthescam.com` | Newsletter onboarding (future — planned newsletter feature) | Reserved |
| `editorial@beatthescam.com` | Editorial / correction enquiries | Reserved — should be activated |
| `legal@beatthescam.com` | DMCA / takedown / legal notices | Reserved — should be activated |
| `security@beatthescam.com` | Responsible disclosure inbox (security.txt) | Reserved — recommended |
| `siderightapps@gmail.com` | Dev / infra / billing master account (Netlify, GitHub, AdSense, YouTube brand owner) | Active |

> **Recommendation:** activate all five reserved aliases as catch-alls or forwarders before public submission to directories. Many directories and security scanners look for `security@`, `privacy@`, and `abuse@` mailboxes — having them improves trust signals.

### Public contact methods

- Contact page: `https://beatthescam.com/contact/`
- Footer link on every page
- Social: Twitter/X `@BeatTheScamUK`, TikTok `@BeatTheScamUK`, YouTube `Beat The Scam`

---

## 3. Tech Stack & Architecture

| Layer | Choice | Notes |
|---|---|---|
| Site generation | **Custom Python static site generator** (`scripts/build.py`) | NOT Next.js, NOT Hugo, NOT Jekyll. Bespoke Python that reads `content/posts.json` + `content/site.json` and renders into `dist/` using `templates/base.html`. |
| Templating | Single `templates/base.html` shell with `{{placeholder}}` substitution | Simple, fast, no framework dependency. |
| Source of truth (content) | `content/posts.json` | All 97+ guides as JSON records. |
| Hosting / CDN | **Netlify** (Personal plan — $9/month, 1000 build credits) | Auto-deploys on push to `main`. |
| Serverless functions | **Netlify Functions** (`netlify/functions/check-scam.js`) | Proxies the AI scam checker to the Anthropic API. |
| AI for scam checker | **Anthropic Claude — `claude-haiku-4-5-20251001`** | Returns structured JSON verdict. |
| AI for content generation | **Anthropic Claude — `claude-haiku-4-5-20251001`** | Generates 6 sections × 120–180 words + 4 FAQs per guide. |
| Content automation | **GitHub Actions** (`.github/workflows/daily-publish.yml`) | Daily at 06:15 UTC, batch of 5 guides. |
| Analytics | **Google Analytics 4** | ID `G-JXNF856NBF`. |
| Ads | **Google AdSense** | Publisher ID `ca-pub-1606633100797174` — *in review.* |
| Email distribution | Not yet implemented | Planned: ConvertKit / Buttondown / MailerLite for the planned newsletter. |
| Search / SEO | Google Search Console, Bing Webmaster Tools | Site verified. |
| Repository | GitHub (`siderightapps-hub/beatthescam-site`) | Private/public TBD — confirm before sale. |

### Why static + serverless?

- **Zero ongoing server cost** beyond Netlify's flat fee.
- **Instant rollback** via Git history.
- **A+ security** is easier to maintain — no app server attack surface.
- **AI checker is the only dynamic surface** and is isolated as a single serverless function with rate limiting, CORS pinning, and input sanitisation.

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
│   └── tweet_new_articles.py          # Auto-tweet on publish
├── content/
│   ├── posts.json                     # All 97+ published guides (source of truth)
│   ├── site.json                      # Site config (domain, AdSense ID, GA4 ID, etc.)
│   ├── affiliates.json                # Affiliate products config
│   ├── daily-publish-queue.csv        # Pending topics
│   └── topics-claude-template.csv     # Topic template reference
├── templates/
│   └── base.html                      # HTML shell with {{placeholders}}
├── assets/
│   ├── styles.css                     # All site CSS
│   ├── app.js                         # Cookie consent + nav toggle + outbound click tracking
│   └── og-image-v2.png                # OpenGraph default image
├── netlify/
│   └── functions/
│       └── check-scam.js              # Serverless Claude API proxy (rate-limited)
├── .github/
│   └── workflows/
│       └── daily-publish.yml          # GitHub Actions daily content pipeline
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

```
06:15 UTC  →  GitHub Actions starts daily-publish.yml
            →  git pull --rebase origin main   (catches manual pushes)
            →  Calls Claude API → generates 5 guides → updates posts.json
            →  Runs python scripts/build.py → rebuilds dist/
            →  Verifies dist/index.html, dist/robots.txt, dist/_redirects, 50+ guide directories exist
            →  git add -A && commit
            →  Pull-rebase + retry loop on push (up to 3 attempts)
            →  Push to main
            →  Netlify auto-deploys
```

### Credit usage discipline

The daily pipeline is optimised to **only push to GitHub when content has actually changed**, saving ~15 credits/month on empty runs. Monitor monthly credit usage in the Netlify dashboard.

---

## 6. Environment Variables & Secrets

### GitHub repository secrets (Settings → Secrets → Actions)

| Secret | Purpose | Last rotated |
|---|---|---|
| `ANTHROPIC_API_KEY` | Used by `daily-publish.yml` for Claude content generation | 2026-04-28 |
| `TWITTER_API_KEY` | Auto-tweet new articles via `tweet_new_articles.py` | (confirm) |
| `TWITTER_API_SECRET` | Twitter OAuth | (confirm) |
| `TWITTER_ACCESS_TOKEN` | Twitter OAuth | (confirm) |
| `TWITTER_ACCESS_SECRET` | Twitter OAuth | (confirm) |

### Netlify environment variables (Site settings → Environment variables)

| Variable | Purpose | Last rotated |
|---|---|---|
| `ANTHROPIC_API_KEY` | Used by `check-scam.js` serverless function | 2026-04-28 |

### Key rotation policy

- All keys were rotated on **2026-04-28** after a suspected exposure incident.
- Rotation playbook documented in `SecurityAuditHandoff.md`.
- **Cadence going forward:** rotate every 90 days minimum; immediate rotation on any suspected exposure.

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
- **Essential pages confirmed for AdSense:** Privacy Policy ✅ · About ✅ (with E-E-A-T signals) · Contact ✅ · Cookie Policy ✅
- **Crawler access:** `robots.txt` does **not** block `Mediapartners-Google` or `AdsBot-Google`. Confirmed.

### Google — Cloud Console

- Used minimally — primarily for Search Console API access (planned for the URL-checker future feature with Google Safe Browsing).

### VirusTotal *(planned)*

- For the planned **URL Checker** feature — pasted URLs would be cross-checked against VirusTotal + Google Safe Browsing, then results fed to Claude for a plain-English verdict.

### Twitter / X

- **Handle:** `@BeatTheScamUK`
- **API access tier:** Free or Basic (confirm)
- **OAuth credentials:** stored as GitHub Secrets for `tweet_new_articles.py`
- **Posting frequency:** On every new article publish + manual video posts

### TikTok

- **Handle:** `@BeatTheScamUK`
- **Account email:** `socialmedia@beatthescam.com`
- **Posting:** Manual upload from CapCut → camera roll → TikTok app (per `VideoProductionHandoff.md`)
- **API:** Not currently used (no automated posting)

### YouTube

- **Channel:** Beat The Scam (Brand Account)
- **Owner Google account:** `siderightapps@gmail.com`
- **Channel handle:** TBC
- **Posting:** Manual upload of Shorts via the YouTube Studio interface
- **API:** Not currently used

### ElevenLabs (voice generation)

- **Account email:** `socialmedia@beatthescam.com`
- **Plan:** Starter ($6/month)
- **Voice in use:** Daniel (British male) — changed from Grace
- **Used for:** Voiceovers in Shorts/TikTok videos

### Gemini (image generation)

- **Used for:** Generating per-clip images for video production (UK-specific scene details — see `VideoProductionHandoff.md` Section 3 Step 3)

### CapCut

- **Used for:** Video assembly, auto-captions, background music, end card insertion

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
| Registrar | (confirm — likely Namecheap / GoDaddy / Cloudflare Registrar) |
| Registration date | February 2026 |
| DNS provider | Netlify DNS (or registrar default — confirm) |
| Nameservers | Netlify (`dns1.p01.nsone.net` etc., confirm in registrar) |
| SSL | Let's Encrypt via Netlify managed HTTPS |
| HSTS | `max-age=31536000; includeSubDomains; preload` — **submitted to HSTS preload list** |
| TLS rating | **SSL Labs A+** (TLS 1.3, modern cipher suites) |

### Subdomains in use

- `www.beatthescam.com` → 301 redirect to apex `beatthescam.com`

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

---

## 10. Monetisation — AdSense, Affiliates, Sponsorships

### Channel status table

| Channel | Status (2026-05-20) | Estimated revenue at scale |
|---|---|---|
| **Google AdSense** | In review since ~2026-04-21 | £30–£900/mo depending on traffic |
| **Experian IdentityPlus (via Awin)** | Awin rejected, reapply 2026-06-12+ | £50–£300/mo if approved |
| **Norton 360 (via Impact/CJ)** | Impact verified, CJ application in progress | £50–£250/mo if approved |
| **Which? Legal (direct outreach)** | Email outreach drafted | £30–£150/mo if approved |
| **Cifas Protective Registration** | Direct outreach planned | £20–£100/mo (lower commission tier) |
| **Newsletter sponsorships** | Newsletter not built yet | £100–£500/mo per sponsored issue once list >2,000 |
| **Direct sponsorships** | None yet | Untapped — security SaaS brands relevant |

### AdSense — readiness checklist

- [x] Privacy Policy page live (`/privacy/`)
- [x] About page live (`/about/`) with E-E-A-T author byline, methodology, source list, AI disclosure, review date
- [x] Contact page live (`/contact/`)
- [x] Cookie Policy page live (`/cookies/`)
- [x] `ads.txt` served and Authorised at `/ads.txt`
- [x] `robots.txt` does not block `Mediapartners-Google` or `AdsBot-Google`
- [x] Original, regularly-published content (97+ guides, daily publishing pipeline)
- [x] Working HTTPS with valid certificate
- [x] Site has clear navigation and footer

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
- Sponsored email blast inside the future newsletter

---

## 11. Content Operations & AI Pipeline

### Current state

- **Published guides:** 97+ across 17 normalised categories
- **Queue:** ~77 remaining topics in `content/daily-publish-queue.csv` (~15 days at 5/day)
- **Avg article length:** 900–1,200 words (post-rewrite of 20 thin guides)
- **Structure per article:** 6 sections × 120–180 words + 4 FAQs + sidebar (Fast checks, Related guides, Report this scam, Checker CTA, Affiliate card) + FAQ schema
- **Reporting links:** All updated from `actionfraud.police.uk` → `reportfraud.police.uk`

### Daily publish pipeline

| Item | Value |
|---|---|
| Workflow file | `.github/workflows/daily-publish.yml` |
| Schedule | Daily at **05:07 UTC** (06:07 BST) — moved off popular minute/hour slots to reduce GitHub-Actions scheduling delay. Cron is best-effort, not on-time. |
| Batch size | **1 guide per run** (was 5 until 2026-05-22; reduced to keep velocity sane and avoid burying posts) |
| Queue file | `content/daily-publish-queue.csv` |
| Model | `claude-haiku-4-5-20251001` |
| Build verification | Fails workflow if `dist/index.html`, `dist/robots.txt`, `dist/_redirects` missing OR <50 guide dirs |
| Push retry | `git pull --rebase` + 3 attempts with 5s sleep on rejection |

### Search Console article generator (parallel pipeline)

- Runs at **05:23 UTC** daily (was 06:30 UTC until 2026-05-22). Off popular slots to reduce delay; queued behind `daily-publish` via shared `concurrency: content-pipeline` group.
- Pulls trending queries from Search Console
- Identifies content gaps (queries with impressions but no matching guide)
- Generates new article via Claude API
- Adds to `posts.json`, rebuilds, commits, pushes
- Tweets new article via `tweet_new_articles.py`

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

- **No fabricated statistics.** All stats verified against Action Fraud, NCSC, FCA, UK Finance, Which?, named surveys.
- **UK-first language.** Pounds sterling, UK reporting routes, UK phone scam patterns (HMRC, DVLA, Royal Mail, BT).
- **Plain English.** No legal jargon. Read-aloud test for every section.
- **Always include reporting routes.** Every article links to `reportfraud.police.uk`.
- **AI disclosure** on the About page is explicit and honest.

### Topic queue management

When `content/daily-publish-queue.csv` drops below 20 topics, add new ones in batch — use Search Console gap analysis and current scam news (NCSC alerts, Action Fraud bulletins, Which? scam tracker) as the source.

---

## 12. Social Media & Video Production

### Channels

| Platform | Handle | Status |
|---|---|---|
| Twitter / X | `@BeatTheScamUK` | Active — auto-posts on article publish |
| TikTok | `@BeatTheScamUK` | Active — 3 videos published, M/W/F cadence |
| YouTube | `Beat The Scam` (Brand Account) | Active — 3 Shorts published |
| Facebook | Reserved | Not yet active |
| Instagram | Reserved | Not yet active |
| LinkedIn | Reserved | Not yet active |
| Reddit | Personal account used carefully in r/Scams and r/UKPersonalFinance | See Section 14 |

### Video production workflow (summary — full detail in `VideoProductionHandoff.md`)

1. **Script** — Claude pulls article from `posts.json`, verifies stats, generates 30s or 60s timed script
2. **Audio** — ElevenLabs (Daniel, British male), 43–58s target
3. **Images** — Gemini with UK-specific scene prompts; **first frame must be a human face showing emotion** (critical retention rule)
4. **Assembly** — CapCut: hard cuts, -20dB background music, auto-captions, Ken Burns on long clips, end card
5. **Export & upload** — TikTok (AI content toggle ON), YouTube Shorts (Altered content YES), then `python3 scripts/tweet_new_articles.py --slug ...`

### Hashtag template

Standard tags: `#ScamAlert #UKScam #ScamAwareness #FraudAlert #BeatTheScam`

### Posting schedule

- **Daily (Mon–Sun)** — best window **07:30–09:00 UK BST**. Changed from M/W/F to daily on 2026-05-22 — daily cadence is generally rewarded more on both TikTok and YouTube Shorts.
- Pin first comment immediately after posting on TikTok and YouTube

### Video calendar

12-video plan running through ~Week 4. Current progress: 3 of 12 published (ISP Impersonation, WhatsApp "Hi Mum", Royal Mail Text). Next: HMRC Tax Refund Scam. Full calendar in `VideoProductionHandoff.md` Section 2.

---

## 13. SEO, GEO & AEO Strategy

This site is engineered for three search modes simultaneously:

- **SEO** — Traditional Google ranking
- **GEO** (Generative Engine Optimization) — being cited by SGE, Gemini, Bing Copilot, ChatGPT, Perplexity
- **AEO** (Answer Engine Optimization) — appearing in featured snippets, "People also ask", and voice answers

### Current SEO state (Search Console snapshot 2026-04-30)

- Impressions: 1,850 / 3 months
- Clicks: 3 (CTR 0.2%)
- Average position: 24.1
- Indexed: 96 pages
- Not indexed: 42 (28 "discovered – currently not indexed", 10 404s now redirected, 3 page-with-redirect now resolved, 1 crawled-not-indexed)
- Core Web Vitals: no CrUX data yet (insufficient traffic)

### Structural SEO foundations (✅ already in place)

- Canonical URLs on every page
- Schema.org markup: `WebSite`, `Organization`, `Article`, `FAQPage`, `BreadcrumbList`
- OpenGraph + Twitter Card meta on every page
- Reading time on every article
- Table of contents on every article
- Related-guides sidebar (4 deduped by topic)
- `sitemap.xml` auto-generated and submitted to Search Console
- `robots.txt` tightened (blocks `/search/`, `*.php`, `?l=` spam patterns)
- Category 301s deployed via `dist/_redirects`
- HSTS preload + HTTPS everywhere
- Mobile-responsive, fast (no JS frameworks, minimal assets)
- HTTP/2 via Netlify
- Image lazy-loading where applicable

### Priority pages (deserve internal-link concentration)

| Page | Priority | Reasoning |
|---|---|---|
| `/check/` — Scam Checker | **Top** | Unique tool, conversion engine, primary differentiator |
| Category hubs (`/categories/payment/`, `/categories/sms/`, `/categories/email/`, etc.) | **High** | Head-term targets ("payment scams uk", "email scams uk") |
| Top 10 highest-impression guides (per Search Console) | **High** | Already attracting traffic — push to page 1 |
| `/about/` | Medium | E-E-A-T signal carrier; supports YMYL ranking |

### Near-miss query strategy (highest immediate leverage)

Per the SEO ranking section in `SessionHandoff-SEOHygieneBullet-ListBug-HouseKeeping.md`:

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
   - Action Fraud / NCSC public resource directories
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
   - YouTube channel "About" link ✅
   - Pinterest / Instagram (when those channels activate)

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
| Terms of Use | `/terms/` | (confirm — if missing, add) |
| Affiliate Disclosure | Currently inside Privacy/About | Recommend a dedicated `/disclosure/` page once affiliates go live |

### GDPR / UK GDPR / Data Protection Act 2018

- **Data controller:** SideRight Apps (Alex)
- **Data controller contact:** `privacy@beatthescam.com` (activate this alias)
- **Lawful bases used:**
  - **Legitimate interest** for GA4 analytics (with IP anonymisation)
  - **Consent** for AdSense personalised ads (via the cookie banner)
  - **Contract / legitimate interest** for the scam checker (user-initiated submission)
- **Data retention:**
  - Scam checker submissions: **not stored** (stateless function — Anthropic processes, returns, discarded)
  - Analytics: GA4 default retention (14 months)
  - Newsletter: TBD when launched — recommend 24 months inactive purge
- **Data processors:**
  - Google (GA4, AdSense)
  - Anthropic (scam checker AI inference — see Anthropic's UK/EU data residency posture)
  - Netlify (hosting)
  - GitHub (source code, not user data)
- **User rights:** Access, rectification, erasure, restriction, portability, objection. Requests handled via `privacy@beatthescam.com`.
- **Children:** Site is not directed at under-13s; AdSense `tagForChildDirectedTreatment` is not set.
- **International transfers:** Google + Anthropic both operate transfers under SCCs / UK IDTA.

### PECR (UK cookie law)

- Cookie banner required for **non-essential** cookies (GA4, AdSense)
- Consent UI lives in `assets/app.js`
- Banner blocks non-essential tags until consent given (verify implementation)
- "Reject all" must be as easy as "Accept all"

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

> Full detail in `SecurityAuditHandoff.md`. This section is the executive summary.

### Audit status

- **Original audit:** 2026-04-29
- **Remediation completed:** 2026-04-30
- **Status:** ✅ All actionable items remediated or verified

### Live scan results

- **securityheaders.com:** **A** (capped by `'unsafe-inline'` requirement of AdSense + GA4)
- **SSL Labs:** **A+** (TLS 1.3, HSTS preload deployed)
- **Mozilla Observatory:** not run; the above were sufficient
- **TruffleHog (manual grep):** no matches across `dist/` or source

### Security headers in production

```
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' [Google AdSense + GA4 hosts]; …
strict-transport-security: max-age=31536000; includeSubDomains; preload
permissions-policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
referrer-policy: strict-origin-when-cross-origin
x-content-type-options: nosniff
x-frame-options: DENY
```

Full CSP string in `SecurityAuditHandoff.md` Section 1.

### OWASP Top 10 (2021) coverage

| ID | Risk | Mitigation in this site |
|---|---|---|
| A01 — Broken Access Control | Public site; no auth routes exist | N/A |
| A02 — Cryptographic Failures | TLS 1.3, HSTS preload, no PII stored | ✅ |
| A03 — Injection | Scam checker sanitises `type` field; no SQL; no shell calls | ✅ |
| A04 — Insecure Design | Stateless function, no user accounts | ✅ |
| A05 — Security Misconfiguration | netlify.toml headers verified; Server header noted (Netlify-managed) | ✅ |
| A06 — Vulnerable Components | Static site + 1 minimal Node function; dependencies minimal | ✅ |
| A07 — ID & Auth Failures | No auth in scope | N/A |
| A08 — Software & Data Integrity Failures | No CDN scripts beyond Google's; SRI not viable on AdSense | Partial (documented) |
| A09 — Logging & Monitoring Failures | No user accounts; Netlify provides function logs | Acceptable |
| A10 — SSRF | Function only calls Anthropic API; user input never used as URL | ✅ |

### Application-level security (scam checker function)

- ✅ CORS locked to `https://beatthescam.com`
- ✅ IP-based rate limiting: 10/min/IP, 429 on breach
- ✅ Input sanitisation: `type` stripped of non-alphanumerics
- ✅ Output validation: verdict shape verified before returning
- ✅ Error handling: generic 500s only, no stack-trace leakage
- ✅ Safe DOM rendering: `createElement` + `textContent`; `https://` prefix validation on links

### Repository hygiene

- ✅ No `.env` files in git history
- ✅ No exposed keys in `dist/` or source
- ✅ No source maps in production
- ✅ API keys rotated 2026-04-28 after suspected exposure

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
- DNSSEC enabled (confirm)
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

### `llms.txt` *(NEW — recommended)*

[`llms.txt`](https://llmstxt.org/) is an emerging standard for telling LLMs what content on the site is canonical and citation-worthy. **Currently not deployed.** Recommended next step.

Suggested content for `https://beatthescam.com/llms.txt`:

```
# Beat The Scam

> UK consumer-protection publication providing plain-English scam awareness guides and a free AI-powered scam checker. All content is original, fact-checked against UK government sources, and edited by Beat The Scam Editorial Team.

## Core pages

- [About & methodology](https://beatthescam.com/about/): How we research, write, and verify our content; AI use disclosure.
- [Privacy policy](https://beatthescam.com/privacy/)
- [Free scam checker](https://beatthescam.com/check/): Paste a suspicious message; receive a verdict.

## Topic hubs

- [Payment scams](https://beatthescam.com/categories/payment/)
- [SMS / text scams](https://beatthescam.com/categories/sms/)
- [Email / phishing scams](https://beatthescam.com/categories/email/)
- [Government impersonation scams](https://beatthescam.com/categories/government/)
- [Marketplace scams](https://beatthescam.com/categories/marketplace/)
- (… one line per category …)

## Optional

- [Sitemap (full URL list)](https://beatthescam.com/sitemap.xml)
```

Add generation of `llms.txt` to `build.py` from the category list.

### `security.txt` *(NEW — recommended)*

[`security.txt` RFC 9116](https://securitytxt.org/) lets researchers know how to report issues. Currently not deployed. Recommended.

Suggested content for `https://beatthescam.com/.well-known/security.txt`:

```
Contact: mailto:security@beatthescam.com
Expires: 2027-05-20T00:00:00.000Z
Preferred-Languages: en
Canonical: https://beatthescam.com/.well-known/security.txt
Policy: https://beatthescam.com/security-policy/
```

(Sign the file with a PGP signature once a key is published.)

### `humans.txt` *(optional — nice-to-have)*

A short credits file at `/humans.txt`. Useful for buyers / future contractors. Optional.

---

## 19. Operational Runbook & Routine Tasks

### Daily (automated)

- ✅ 06:15 UTC — Daily AI publish workflow
- ✅ 06:30 UTC — Search Console article generator
- ✅ Tweet on every publish

### Weekly (manual)

- Mon / Wed / Fri — publish a new TikTok + YouTube Short (per video calendar)
- Reply to any contact-form / `hello@` emails
- Reddit / Quora — 3–5 contributions per week
- Outreach — 5–10 link-insertion / guest-post emails per week
- Search Console — glance at queries, look for new near-miss opportunities

### Monthly

- Review Netlify build credit usage
- Review AdSense earnings (once approved)
- Review affiliate dashboards (Awin, Impact, CJ)
- Add 30+ new topics to `content/daily-publish-queue.csv` if running low
- Update video calendar
- Quarterly: re-run security scans (see Section 17)

### Quarterly

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

> Carried forward and consolidated from `ProjectHandoffDocument.md`, `SecurityAuditHandoff.md`, `SessionHandoff-SEOHygieneAndBullet-ListBugFix.md`, `SessionHandoff-SEOHygieneBullet-ListBug-HouseKeeping.md`.

1. **Netlify publish directory dependency.** The dashboard's *Publish directory* must be set to `dist`. If "Not set", `netlify.toml` `[[headers]]` blocks silently stop applying. **Canonical check:** `curl -sI https://beatthescam.com/assets/styles.css | grep -i cache-control` must return `public, max-age=31536000, immutable`.

2. **`netlify.toml` redirects don't apply for category paths.** `[[redirects]]` works for `/api/check-scam` and the catch-all 404 but silently fails for `/categories/...-scams/*` patterns. Workaround: use `dist/_redirects` (auto-generated by `build.py`).

3. **Daily pipeline git-conflict risk — RESOLVED 2026-05-21.** Both `daily-publish` (06:15 UTC) and `daily-search-console` (06:30 UTC) regenerate `dist/sitemap.xml` from `posts.json`. When daily-publish overran the 15-minute window the two ran concurrently, the second push hit a rebase conflict on `dist/sitemap.xml`, and the previous "stash + checkout + stash-pop" recovery branch failed because `dist/` is derived (not authored) content and can't be merged. **Fix:**
   - Both workflows now share a `concurrency: group: content-pipeline, cancel-in-progress: false` block — GitHub Actions queues them instead of letting them race.
   - The rebase-conflict recovery path was rewritten to: snapshot our `content/*` changes to `/tmp/`, `git reset --hard origin/main`, merge new posts back in via `scripts/merge_new_posts.py` (matches by slug), rebuild `dist/` from scratch via `scripts/build.py`, then commit + push. `dist/` is never merged.
   - **Canonical detection:** if a workflow run fails with "CONFLICT (content): Merge conflict in dist/sitemap.xml" the concurrency group is misconfigured. Both workflows must reference the same group name.

4. **Daily pipeline git-conflict risk (human-during-pipeline).** A manual push during a pipeline run can still trigger the rebase-conflict path. Now handled by the same snapshot/reset/rebuild recovery — should self-heal up to 3 retries.

   **GitHub-Actions scheduled cron is best-effort, not on-time.** The `schedule:` event docs explicitly state runs can be delayed by hours during periods of high load — and "high load" includes the start of every hour and popular minute slots (`:00`, `:15`, `:30`, `:45`). Example seen on 2026-05-21: a `'30 6 * * *'` cron fired at 10:09 UTC, 3.5 hours late. Mitigations: (a) use off-peak minute and hour slots — current schedules are `'7 5'` and `'23 5'`; (b) don't rely on exact ordering between two crons — use the `concurrency:` group to queue them; (c) for guaranteed-time execution, point an external cron service at the GitHub `repository_dispatch` API endpoint.

5. **Netlify credit usage cap.** 1,000 credits/month. Pipeline only deploys when `dist/` changes. Monitor monthly.

6. **AdSense approval delay.** Site has been in review since ~2026-04-21 (re-started after `ads.txt` fix). Chase mid-week if still pending after 14 days.

7. **Awin rejected.** Reapply 2026-06-12 onwards with Search Console traffic data.

8. **Content queue depletion.** ~77 topics remaining at 5/day = ~15 days. Add new topics before queue empties.

9. **Local Mac keyboard interference.** Some pasted commands containing `build.py` were silently converted to markdown link format on the local laptop. Workaround: tab-completion or rename file when running locally. CI is unaffected.

10. **GitHub PAT must include `workflow` scope** to modify `.github/workflows/*.yml`. Default `repo`-only tokens fail.

11. **`'unsafe-inline'` CSP trade-off.** Capped at security-headers grade A. Path to A+ is per-request nonces via Edge Functions — deferred.

12. **Bullet-list rendering bug.** Fixed in both renderer (`build.py`) and generator (`generate_content_claude.py`). Layer 3 (cleaning the broken-shape data already in `posts.json`) is optional — not urgent.

13. **No `llms.txt` yet.** Recommended next addition. See Section 18.

14. **No `security.txt` yet.** Recommended next addition. See Section 18.

15. **`privacy@`, `security@`, `editorial@`, `legal@` mailboxes not active.** Recommend activating as catch-alls or forwarders.

16. **No `/terms/` page audit confirmed.** Verify it exists and is current.

17. **No formal trademark filing.** Recommend UK IPO classes 41 + 42.

---

## 21. Outstanding Roadmap

> Carried forward from `ProjectHandoffDocument.md` Section 7 and updated.

### This week / next session

- [ ] Activate `privacy@`, `security@`, `editorial@`, `legal@` mailbox aliases
- [ ] Add `llms.txt` generation to `build.py`
- [ ] Add `/.well-known/security.txt`
- [ ] Verify `/terms/` page exists and is current
- [ ] Confirm Twitter API keys are stored as GitHub Secrets
- [ ] Build out the top 3 category hub pages (600–800 words each)

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
- 97+ original UK-focused guides in `content/posts.json`
- AI scam checker (live, rate-limited, secured)
- Daily content generation pipeline (GitHub Actions + Anthropic Claude)
- Netlify hosting setup (transferable)
- Google Analytics 4 property
- Google AdSense Publisher ID (in review — will need re-verification on transfer)
- Social channels: Twitter `@BeatTheScamUK`, TikTok `@BeatTheScamUK`, YouTube "Beat The Scam"
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

- `ProjectHandoffDocument.md` — original project handoff (2026-04-30)
- `SecurityAuditHandoff.md` — full security remediation record (2026-04-30)
- `SessionHandoff-SEOHygieneAndBullet-ListBugFix.md` — 2026-05-01 session
- `SessionHandoff-SEOHygieneBullet-ListBug-HouseKeeping.md` — 2026-05-02 session
- `VideoProductionHandoff.md` — video production workflow & calendar
- `WebsiteProject-MasterTemplate.md` — generic template extracted from this document

---

*End of Master Project Document. Maintained as the single source-of-truth. Update at the start of any meaningful change, and at the end of any significant session.*
