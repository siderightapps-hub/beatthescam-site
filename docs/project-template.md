# [Project Name] — Master Project Document Template

> **How to use this template:**
> 1. Copy this file to a new project as either `PROJECT.md`, `MASTER.md`, or `CLAUDE.md` (it works as a Claude Code context-bootstrap file).
> 2. Replace every `[…]` placeholder and every "TBD" with project-specific detail.
> 3. Delete any sections that don't apply (e.g. remove "Video Production" for a non-social-media project).
> 4. Keep the section ordering — it matches the natural reading order for a buyer / new contractor / onboarding LLM.
> 5. Update `Last updated` whenever you touch the file.
>
> **This document serves four audiences:**
> 1. **The owner / operator** — operational manual.
> 2. **New Claude Code chat sessions** — drop-in context bootstrap.
> 3. **Potential buyers / acquirers** — due-diligence briefing.
> 4. **Contractors, future editors, security reviewers** — onboarding pack.
>
> **Last updated:** [YYYY-MM-DD]
> **Domain age:** [duration since registration]
> **Site state:** [one-line state — e.g. "MVP live, 30 articles, no monetisation yet"]
> **Maintainer:** [Name] — [Trading entity] (GitHub: `[handle]`)

---

## Table of Contents

1. [Brand & Project Overview](#1-brand--project-overview)
2. [Ownership, Contacts & Email Addresses](#2-ownership-contacts--email-addresses)
3. [Tech Stack & Architecture](#3-tech-stack--architecture)
4. [Repository Structure](#4-repository-structure)
5. [Hosting & Deployment](#5-hosting--deployment)
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

- **Brand name:** [Name]
- **Strapline:** *"[one-sentence positioning statement]"*
- **Live URL:** https://[domain]
- **Country / region focus:** [UK / US / Global / etc.]
- **Vertical:** [niche · sub-niche · sub-niche]
- **Editorial persona / author byline:** [name + role — important for YMYL E-E-A-T]

### Purpose

[2–4 paragraphs describing what the site does, who it helps, and how. Cover:]

1. [Core product / content offering.]
2. [Free tool / utility, if any.]
3. [Audience referral / community routes the site directs users to.]
4. [Revenue model summary.]
5. [Strategic positioning — what topical authority is being built and why.]

### Why this brand has standalone value

- [Domain quality — exact-match keyword? brandable? short? memorable?]
- [Niche characteristics — YMYL? high-RPM vertical? evergreen demand?]
- [Existing assets — content volume, original tooling, social channels, email list.]
- [Strategic acquirer fit — who might want this in 12–24 months?]

---

## 2. Ownership, Contacts & Email Addresses

### Owner

- **Name:** [Owner name — or pseudonym if intentionally separated from public persona]
- **Trading entity:** [Sole trader / Ltd company name]
- **Companies House #:** [if applicable]
- **VAT #:** [if applicable]
- **GitHub:** [github handle]
- **Repository:** [repo URL]

### Email addresses in use (or reserved)

| Address | Purpose | Status |
|---|---|---|
| `hello@[domain]` | General public contact | [Active / Reserved] |
| `socialmedia@[domain]` | Social platform sign-ups, third-party tools | [Active / Reserved] |
| `privacy@[domain]` | GDPR / data protection | [Active / Reserved] |
| `welcome@[domain]` | Newsletter onboarding | [Active / Reserved] |
| `editorial@[domain]` | Editorial / correction enquiries | [Active / Reserved] |
| `legal@[domain]` | DMCA / takedown / legal | [Active / Reserved] |
| `security@[domain]` | Responsible disclosure (security.txt) | [Active / Reserved] |
| `abuse@[domain]` | Abuse reports | [Active / Reserved] |
| `[personal]@gmail.com` | Master dev / infra / billing account | Active |

> **Recommendation:** activate `privacy@`, `security@`, `abuse@`, and `legal@` at minimum before public submission to directories. Many directories and scanners look for these mailboxes — having them improves trust signals.

### Public contact methods

- Contact page: `https://[domain]/contact/`
- Footer link on every page
- Social: [list handles]

---

## 3. Tech Stack & Architecture

| Layer | Choice | Notes |
|---|---|---|
| Site generation | [Next.js / Nuxt / Hugo / Jekyll / Astro / custom Python / WordPress] | [Why this choice] |
| Templating | [Framework / engine] | |
| Source of truth (content) | [DB / JSON / Markdown / CMS] | |
| Hosting / CDN | [Netlify / Vercel / Cloudflare Pages / AWS Amplify / Render] | [Plan + monthly cost] |
| Serverless / API | [Netlify Functions / Vercel Functions / AWS Lambda / Cloud Run] | |
| AI provider (runtime) | [Anthropic / OpenAI / Gemini] — model `[id]` | [What it's used for] |
| AI provider (content gen) | [Anthropic / OpenAI / Gemini] — model `[id]` | |
| Content automation | [GitHub Actions / cron / Zapier / n8n] | |
| Analytics | [GA4 / Plausible / Fathom / Umami] | ID `[…]` |
| Ads | [Google AdSense / Mediavine / Ezoic / Raptive] | Publisher ID `[…]` |
| Email distribution | [ConvertKit / Buttondown / MailerLite / Substack] | |
| Search / SEO | Google Search Console + Bing Webmaster Tools | |
| Repository | GitHub — `[org]/[repo]` | [public / private] |

### Why this stack?

[1–2 paragraphs justifying the choice. Cover cost, scalability, security posture, ops burden.]

---

## 4. Repository Structure

```
[project-name]/
├── scripts/              # Build, generation, automation scripts
├── content/              # Source-of-truth content
├── templates/            # HTML / template files
├── assets/               # Static assets (CSS, JS, images)
├── netlify/              # (if Netlify) functions etc.
├── .github/workflows/    # CI / scheduled jobs
├── dist/ or .next/ or _site/  # Build output
└── README.md
```

[Customise tree to actual project. Annotate critical files.]

### File-level notes

- [Anything sensitive — "Never edit `dist/*.html` directly" type warnings]
- [Auto-generated files that look manual]
- [Manual files that look auto-generated]

---

## 5. Hosting & Deployment

### Plan

- **Provider:** [Netlify / Vercel / etc.]
- **Plan:** [Free / Personal / Pro] — [£X/month]
- **Build minutes / credits:** [N]/month
- **Functions:** [Included / N per month]
- **Bandwidth:** [N GB/month]

### Configuration

| Setting | Value | Notes |
|---|---|---|
| Publish / output directory | `[dist / .next / build]` | [Any gotchas — e.g. for Netlify it MUST be set in the dashboard, not just in `netlify.toml`] |
| Build command | `[npm run build / python build.py]` | |
| Functions directory | `[netlify/functions / api]` | |
| Production branch | `main` | |
| Auto-deploy on push | Yes | ~[N]s deploy time |

### Deployment flow

```
Developer pushes to main  →  [hosting provider] webhook  →  [build steps]  →  Live in ~[N]s
```

### Daily pipeline flow (if applicable)

```
[time UTC]  →  GitHub Actions starts [workflow].yml
            →  git pull --rebase origin main
            →  [content generation step]
            →  [build step]
            →  [verification step — IMPORTANT, prevents silent failures]
            →  git add / commit
            →  pull-rebase + retry loop on push
            →  push to main
            →  auto-deploy
```

> **Critical:** any scheduled pipeline that commits to the same branch as manual work MUST include `git pull --rebase` before commit AND a build-verification step after build. Silent failures are the most expensive bugs.

### Credit / minute usage discipline

[How is usage minimised? Only-deploy-on-change? Caching? Concurrency limits?]

---

## 6. Environment Variables & Secrets

### GitHub repository secrets (Settings → Secrets → Actions)

| Secret | Purpose | Last rotated |
|---|---|---|
| `[KEY]` | [What it does] | [YYYY-MM-DD] |

### Hosting environment variables

| Variable | Purpose | Last rotated |
|---|---|---|
| `[KEY]` | [What it does] | [YYYY-MM-DD] |

### Key rotation policy

- **Cadence:** Rotate every [90 / 180] days minimum.
- **Triggers for immediate rotation:** suspected exposure, departure of a contractor with access, accidental commit, log leak.
- **Rotation playbook:** [link to rotation runbook if any]

### What is NOT stored as a secret

[Public identifiers like AdSense Publisher ID, GA4 measurement ID, public API keys. List them so they don't get rotated unnecessarily and don't get treated as secrets when they don't need to be.]

---

## 7. API Keys & Third-Party Accounts

This is the **complete inventory of every external account** the site depends on.

### [Service name — e.g. Anthropic]

- **Account email:** `[email]`
- **Used for:** [What it does]
- **Models / endpoints in use:** [list]
- **Key locations:** [where the API key is stored]
- **Spend control:** [budget caps, alerts]
- **Documentation:** [URL]

### [Repeat for every service]

Common services to enumerate:
- AI providers (Anthropic, OpenAI, Gemini)
- Google Search Console
- Google Analytics
- Google AdSense
- Google Cloud Console
- VirusTotal
- Twitter / X
- TikTok
- YouTube
- Instagram / Threads / Facebook (Meta)
- LinkedIn
- Reddit
- ElevenLabs (voice)
- Gemini / Midjourney / Stable Diffusion (images)
- CapCut / Descript (video editing)
- Stripe / PayPal (payments)
- ConvertKit / Buttondown / MailerLite (email)
- Cloudflare (DNS / CDN / WAF)
- Affiliate networks (Awin, Impact, CJ, ShareASale, Rakuten)
- DNS registrar
- Domain registrar (if different from DNS)
- SSL certificate provider (if not Let's Encrypt)
- HARO / Featured.com
- Trustpilot (if claimed)

For each: account email, plan, what it's used for, key storage, contact in case of lockout.

---

## 8. Domain, DNS & SSL

| Item | Value |
|---|---|
| Domain | `[domain]` |
| Registrar | [Namecheap / GoDaddy / Cloudflare Registrar] |
| Registration date | [YYYY-MM-DD] |
| Renewal date | [YYYY-MM-DD] — set to auto-renew? Y/N |
| DNS provider | [Netlify / Cloudflare / registrar default] |
| Nameservers | [list] |
| SSL | [Let's Encrypt managed / paid certificate from X] |
| HSTS | `[max-age=…; includeSubDomains; preload]` — submitted to preload list? Y/N |
| TLS rating (SSL Labs) | [grade] |
| DNSSEC | [Enabled / Not configured] |
| Domain lock | [Enabled / Not configured] |

### Subdomains in use

- `www.[domain]` — [301 to apex / serves separately]
- [list other subdomains]

### Subdomains reserved for future

[`app.[domain]`, `mail.[domain]`, `status.[domain]`, etc.]

---

## 9. Analytics & Tracking

### Analytics provider

- **Provider:** [GA4 / Plausible / Fathom]
- **Property / Measurement ID:** `[…]`
- **Events tracked:**
  - `page_view`
  - [custom events]
- **Conversion goals:** [list]

### Tag implementation

[Where in the codebase tags are loaded. Note any CSP implications — e.g. GA4 inline `gtag()` requires `'unsafe-inline'` in `script-src`.]

### Privacy posture

- [IP anonymisation: on/off]
- [Advertising features in GA4: on/off]
- [Cross-site tracking: on/off]
- [How this interacts with the cookie banner — Section 16]

---

## 10. Monetisation — AdSense, Affiliates, Sponsorships

### Channel status table

| Channel | Status | Estimated revenue at scale |
|---|---|---|
| [AdSense / Mediavine / etc.] | [In review / Approved / Live] | [£/mo range] |
| [Affiliate 1] | [Status] | [£/mo] |
| [Newsletter sponsorships] | [Status] | [£/mo per issue] |
| [Direct sponsorships] | [Status] | [£/mo] |

### AdSense / ad network — readiness checklist

- [ ] Privacy Policy page live
- [ ] About page live (with E-E-A-T author byline and methodology)
- [ ] Contact page live
- [ ] Cookie Policy page live
- [ ] `ads.txt` served and Authorised
- [ ] `robots.txt` does not block `Mediapartners-Google` or `AdsBot-Google`
- [ ] Original, regularly-published content
- [ ] Working HTTPS with valid certificate
- [ ] Clear navigation and footer

### Ad unit IDs

```
publisher_id:    [pub-XXXX]
in_article_unit: [unit-id]
sidebar_unit:    [unit-id]
mobile_anchor:   [unit-id]
multiplex_unit:  [unit-id]
```

### Affiliate products / partners

| ID | Product | Categories matched | href status |
|---|---|---|---|
| [id] | [Product name] | [categories] | [Live / Placeholder] |

### Sponsorship / partnership ideas (future)

- [Idea 1]
- [Idea 2]

---

## 11. Content Operations & AI Pipeline

### Current state

- **Published articles / pages:** [count]
- **Queue:** [count] remaining
- **Avg article length:** [words]
- **Structure per article:** [sections × words + FAQs + schema]
- **Reporting links / outbound references:** [policy]

### Daily / scheduled publish pipeline

| Item | Value |
|---|---|
| Workflow file | `[.github/workflows/X.yml]` |
| Schedule | `[cron]` |
| Batch size | [N] per run |
| Queue file | `[path]` |
| Model | `[model id]` |
| Build verification | [What checks happen — required directories, file counts, sentinel files] |
| Push retry | [Strategy] |

### Manual content commands

```bash
[document the actual commands]
```

### Editorial principles

- [Fact verification rules]
- [Language / locale rules]
- [Reading-age target]
- [Mandatory inclusions — reporting routes, disclosures, etc.]
- [AI disclosure stance]

### Topic queue management

[When does the queue need topping up? Where do new topics come from? Who decides?]

---

## 12. Social Media & Video Production

### Channels

| Platform | Handle | Status |
|---|---|---|
| Twitter / X | `[@handle]` | [Active / Reserved] |
| TikTok | `[@handle]` | |
| YouTube | `[channel]` | |
| Facebook | | |
| Instagram | | |
| LinkedIn | | |
| Reddit | | |
| Pinterest | | |

### Video production workflow (if applicable)

[Summarise — script, audio, images, assembly, export, upload. Reference any separate `VideoProductionHandoff.md`.]

### Hashtag template

[Standard tags + category-specific tags]

### Posting schedule

- [Days + times]
- [Pin-first-comment policy]

---

## 13. SEO, GEO & AEO Strategy

This site is engineered for three search modes simultaneously:

- **SEO** — Traditional Google ranking
- **GEO** (Generative Engine Optimization) — being cited by SGE, Gemini, Bing Copilot, ChatGPT, Perplexity
- **AEO** (Answer Engine Optimization) — featured snippets, "People also ask", voice answers

### Current SEO state (Search Console snapshot)

- Impressions: [N] / [period]
- Clicks: [N]
- Average position: [N]
- Indexed: [N] pages
- Not indexed: [N] (breakdown)
- Core Web Vitals: [CrUX status]

### Structural SEO foundations

- [ ] Canonical URLs on every page
- [ ] Schema.org markup: WebSite, Organization, Article, FAQPage, BreadcrumbList
- [ ] OpenGraph + Twitter Card meta on every page
- [ ] Reading time on every article
- [ ] Table of contents on every article
- [ ] Related-articles sidebar (deduped)
- [ ] `sitemap.xml` auto-generated and submitted
- [ ] `robots.txt` tightened against spam patterns
- [ ] Redirects for any URL changes
- [ ] HSTS preload + HTTPS everywhere
- [ ] Mobile-responsive, fast
- [ ] HTTP/2
- [ ] Image lazy-loading

### Priority pages (deserve internal-link concentration)

| Page | Priority | Reasoning |
|---|---|---|
| [/path/] | [Top / High / Medium] | [Why] |

### Near-miss query strategy (highest immediate leverage)

1. Search Console → Performance → Queries → Position < 20
2. Sort by Impressions descending
3. For top 5:
   - Ensure query is in title, H1, first 100 words
   - Compare to top-5 competitors
   - Add 2–3 contextual in-body internal links from related guides

### Hub-page strategy

[Identify head-term targets. Build 600–800 word hub pages with clear scope, common patterns, full article list, action section.]

### Contextual in-body internal linking

Sidebars are weak signals. In-body links from running prose are strong. Audit top guides regularly to add contextual links to related topics.

### GEO (Generative Engine Optimization)

Per Google's [AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide):

- Clear, factual, well-sourced content (AI engines cite sources they trust)
- Schema.org markup (FAQPage especially)
- Author attribution (E-E-A-T)
- Recent review dates
- Plain-English Q&A formatting
- Stable URLs and canonical tags
- No duplicate / near-duplicate content
- No paywalls / interstitials

### AEO (Answer Engine Optimization)

- FAQ schema on every article ✅
- Question-shaped H2/H3 headings
- Concise 40–60 word answers under each question
- Tables, lists, step-by-steps as proper HTML
- "How to…" and "What to do if…" templates

### Title & meta description optimisation

- Front-load the most useful word
- Add the current year to evergreen content
- Meta should answer "what will I learn / what should I do", not summarise

### Page experience

- LCP, INP, CLS targets
- Synthetic Lighthouse scores
- No interstitials beyond compliant cookie banner

---

## 14. Backlinks, Authority & Domain Authority Plan

> **The principle:** authority and content quality are the top two ranking factors. Without backlinks, even excellent content rarely breaks page 1 for competitive queries.

### Foundation backlinks (do these first, in this order)

1. **Niche directories** — [list relevant to vertical]
2. **Profile & citation links** — Crunchbase, About.me, LinkedIn Page, Trustpilot (claim early — defensive), industry-specific profiles
3. **Social mentions** — bio links across all active channels
4. **Reddit participation** — relevant subs; contribute first, link-drop never
5. **Quora** — answer 10–15 high-impression questions in the niche

### Listed directories to submit to

| Directory | Type | Notes |
|---|---|---|
| Google Business Profile | Local / brand | Works even without physical premises |
| Bing Places | Local / brand | Mirror of GBP |
| [vertical-specific 1] | Niche | |
| [vertical-specific 2] | Niche | |

### Niche edits / link insertions (highest ROI)

> *"Niche edits / link insertions are where the real ROI usually comes in. Guest posts should always be part of the strategy, but if you truly want to maximize ROI, start with link insertions first."*

**Process:**
1. Identify blogs / publications with existing relevant articles
2. Polite pitch: "I noticed your article on X. We've published a more detailed walkthrough on [variant] — would you consider adding a link in section Y?"
3. Offer quid-pro-quo only if natural
4. Target 5–10 attempts per week

### Guest posts

- Pitch original [niche] pieces to:
  - [target publication 1]
  - [target publication 2]
- One link from a `.gov`, `.edu`, or trusted vertical publisher is worth fifty random blog comments.

### HARO / Connectively (Featured.com)

- Sign up as a source
- Respond to relevant journalist queries (~5/week)
- Wins come from quick, well-written, attributed responses

### Backlink cadence

> **Consistency matters more than volume.** It's not a one-time activity — it needs to happen regularly over time.

| Tactic | Frequency | Target wins per month |
|---|---|---|
| Directory submissions | 5/week for first 6 weeks, then maintenance | 5–10 |
| Reddit contributions | 3–5/week | 2–4 |
| Quora answers | 2/week | 2–4 |
| Link-insertion outreach | 5–10/week | 1–3 |
| Guest post pitches | 3/week | 1/mo |
| HARO responses | 5/week | 1–2/mo |

### Domain Authority improvement plan

DA isn't a Google metric but is a useful proxy. Realistic 12-month target: DA [N] from current [N]. Path:
- [N] referring domains from contextual links
- [N] links from DA 50+ sources
- Steady internal-link expansion via hub pages
- Continued original content cadence

### Avoiding bad backlink habits

- ❌ No paid PBNs
- ❌ No exact-match anchor-text spam
- ❌ No comment-spam / forum-sig spam
- ❌ No mass-directory-submission services

---

## 15. Target Audience & Brand Voice

### Primary audience

- [Segment 1 — who they are, what they're trying to do *right now*]
- [Segment 2]
- [Segment 3]

### Brand voice

- [Tone — e.g. calm, clear, authoritative, friendly]
- [Practical bias — e.g. always end with "What to do now"]
- [Locale — e.g. UK English, US English, etc.]
- [Reading-age target]
- [AI honesty stance]

### Voice anti-patterns to avoid

- [Clickbait headlines]
- [Sales-y CTAs around free tools]
- [Buried disclosures]
- [Anything outside the voice]

---

## 16. Legal, Compliance, GDPR & Privacy

### Pages

| Page | URL | Status |
|---|---|---|
| Privacy Policy | `/privacy/` | [Live / Missing] |
| Cookie Policy | `/cookies/` | |
| About | `/about/` | |
| Contact | `/contact/` | |
| Terms of Use | `/terms/` | |
| Affiliate Disclosure | `/disclosure/` | |

### GDPR / UK GDPR / Data Protection Act 2018 (or your jurisdiction's equivalent)

- **Data controller:** [Trading entity]
- **Data controller contact:** `privacy@[domain]`
- **Lawful bases used:** [list — legitimate interest, consent, contract, etc.]
- **Data retention:** [what's kept, for how long, how purged]
- **Data processors:** [list — Google, Anthropic, hosting provider, etc.]
- **User rights:** Access, rectification, erasure, restriction, portability, objection. Requests handled via `privacy@[domain]`.
- **Children:** [Site directed at over-13s? AdSense child-directed flag?]
- **International transfers:** [SCCs / UK IDTA / other safeguards]

### PECR / cookie law

- Cookie banner present and blocks non-essential cookies until consent
- "Reject all" as easy as "Accept all"
- Consent stored in [cookie / localStorage] with [duration]

### CCPA / CPRA (if US visitors)

- "Do Not Sell My Info" link in cookie banner
- Opt-out signal honoured

### Editorial / defamation

- [House rules — naming individuals, brand mentions, sourcing]

### Affiliate disclosure (ASA / CMA / FTC)

- Visible disclosure where affiliate links appear
- Specific affiliate-disclosure page recommended

### Accessibility

- WCAG 2.1 AA target
- Quarterly WAVE / axe-core audit
- All images have `alt`
- Colour contrast on body text meets AA

### Trademark & IP

- Trademark filed? [Yes / No — recommend filing in [class numbers]]
- Logo / brand assets — copyright held by [Trading entity]

---

## 17. Security Posture (OWASP & Internet Security)

### Audit status

- **Last audit:** [YYYY-MM-DD]
- **Remediation status:** [Complete / Partial — see remediation document]

### Live scan results

- **securityheaders.com:** [grade]
- **SSL Labs:** [grade]
- **Mozilla Observatory:** [grade]
- **TruffleHog scan of `dist/` + source:** [clean / findings]

### Security headers in production

```
content-security-policy: [policy]
strict-transport-security: max-age=31536000; includeSubDomains; preload
permissions-policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
referrer-policy: strict-origin-when-cross-origin
x-content-type-options: nosniff
x-frame-options: DENY
```

### OWASP Top 10 (2025) coverage

| ID | Risk | Mitigation |
|---|---|---|
| A01 — Broken Access Control | | |
| A02 — Cryptographic Failures | | |
| A03 — Injection | | |
| A04 — Insecure Design | | |
| A05 — Security Misconfiguration | | |
| A06 — Vulnerable Components | | |
| A07 — ID & Auth Failures | | |
| A08 — Software & Data Integrity Failures | | |
| A09 — Logging & Monitoring Failures | | |
| A10 — SSRF | | |

### Application-level security

- CORS locked to production origin
- Rate limiting per IP (e.g. 10/min)
- Input sanitisation on all user-supplied fields
- Output validation before returning to client
- Generic error messages; no stack-trace leakage
- Safe DOM rendering (`createElement` + `textContent`, never `innerHTML` with user data)

### Repository hygiene

- [ ] No `.env` files in git history
- [ ] No exposed keys in built output or source
- [ ] No source maps in production
- [ ] All keys rotated within [90] days
- [ ] Branch protection on `main`
- [ ] Required reviews for PRs (if more than one contributor)

### Re-scan cadence

| Tool | URL | Target | Cadence |
|---|---|---|---|
| Security Headers | https://securityheaders.com/?q=[domain] | A or A+ | Quarterly |
| SSL Labs | https://ssllabs.com/ssltest/analyze.html?d=[domain] | A+ | Quarterly |
| Mozilla Observatory | https://developer.mozilla.org/en-US/observatory/analyze?host=[domain] | B+ or higher | Annually |
| CSP Evaluator | https://csp-evaluator.withgoogle.com/ | No high-risk | After CSP change |

### Internet-security best practices (operational)

- 2FA enabled on every account: GitHub, hosting, Google, AI providers, social platforms, affiliate networks
- Password manager in use (1Password / Bitwarden)
- Recovery codes printed and stored offline
- Backup cadence: git is primary; offline cold backup quarterly
- Domain registrar lock enabled
- DNSSEC enabled
- Domain transfer auth code stored in password manager, not email
- Phishing-resistant 2FA (hardware key) on critical accounts where supported

---

## 18. Site Files: sitemap.xml, robots.txt, ads.txt, llms.txt

### `sitemap.xml`

- Auto-generated by build process? [Y/N]
- Submitted to Google Search Console + Bing Webmaster Tools? [Y/N]
- Excludes 404, redirects, internal files

### `robots.txt`

```
User-agent: *
Allow: /
Disallow: /search/
Disallow: /*.php$
Disallow: /*?l=
Disallow: /api/
Disallow: /.netlify/

Sitemap: https://[domain]/sitemap.xml
```

**Do not block:** `Mediapartners-Google`, `AdsBot-Google`, `Googlebot`, `Bingbot`, `Twitterbot`, `facebookexternalhit`, `LinkedInBot`.

### `ads.txt` (if running ads)

```
google.com, [pub-id], DIRECT, [f08c47fec0942fa0 or relevant TAG-ID]
```

### `llms.txt` *(emerging standard — recommended)*

See [llmstxt.org](https://llmstxt.org/). Tell LLMs what content is canonical and citation-worthy.

```
# [Site name]

> [One-paragraph mission / positioning]

## Core pages

- [About & methodology](https://[domain]/about/)
- [Privacy policy](https://[domain]/privacy/)
- [Primary tool / utility](https://[domain]/[path]/)

## Topic hubs

- [Hub 1](URL): one-line description
- [Hub 2](URL): one-line description

## Optional

- [Sitemap](https://[domain]/sitemap.xml)
```

### `security.txt` *(RFC 9116 — recommended)*

Serve at `/.well-known/security.txt`:

```
Contact: mailto:security@[domain]
Expires: [YYYY-MM-DDTHH:MM:SS.000Z]
Preferred-Languages: en
Canonical: https://[domain]/.well-known/security.txt
Policy: https://[domain]/security-policy/
```

### `humans.txt` *(optional)*

Short credits file at `/humans.txt`. Nice-to-have.

---

## 19. Operational Runbook & Routine Tasks

### Daily (automated)

- [scheduled jobs and what they do]

### Weekly (manual)

- [content publishing cadence]
- [social posting cadence]
- [outreach cadence]
- [inbox triage]

### Monthly

- [hosting credit / usage review]
- [revenue review]
- [affiliate dashboards]
- [content queue top-up]

### Quarterly

- [security re-scans]
- [accessibility audit]
- [key rotation]
- [backup verification]

### Annually

- [trademark / domain renewals]
- [HSTS preload re-verification]
- [full content audit]
- [reapplications to rejected networks]

### Push to GitHub from local (template)

```bash
git remote set-url origin https://YOUR_TOKEN@github.com/[org]/[repo].git

git pull --rebase origin main
git add -A
git commit -m "Your message"
git push origin main

git remote set-url origin https://github.com/[org]/[repo].git
```

Revoke PATs immediately after use.

---

## 20. Known Issues & Watch Points

[Document every gotcha that's bitten the project, with a canonical detection check. Examples to consider:]

1. **Hosting publish-directory dependency** — [if applicable, the Netlify "Publish directory must be set in dashboard, not just toml" issue]
2. **Redirects via toml vs `_redirects`** — [if applicable]
3. **Pipeline git-conflict risk** — mitigated by pull-rebase + retry
4. **Hosting credit cap** — monitor monthly
5. **Approval delays** (AdSense / affiliate networks) — known windows and chase points
6. **Content queue depletion** — top-up trigger
7. **Local environment quirks** — anything that bites only on the local dev machine
8. **Token / scope requirements** — e.g. workflow scope on GitHub PATs

For each, document the **canonical detection command** so future-you can detect regressions in seconds.

---

## 21. Outstanding Roadmap

### This week / next session

- [ ] [Item]

### Near-term (4–8 weeks)

- [ ] [Item]

### Medium-term (8–24 weeks)

- [ ] [Item]

### Long-term (6–12 months)

- [ ] [Item]

---

## 22. Asset Valuation & Acquisition Brief

> Maintained for potential buyer / acquirer briefings.

### What's included

- Domain
- GitHub repository
- All original content
- Any custom tooling / utilities
- Hosting setup (transferable)
- Analytics property
- AdSense Publisher ID (re-verification on transfer)
- Social channels
- Branding assets
- Email list (if any)
- This document + handoff documents

### Valuation matrix

| Scenario | Monthly traffic | Monthly net revenue | Estimated value (30–40× multiple) |
|---|---|---|---|
| Conservative | | | |
| Moderate | | | |
| Strong | | | |
| Premium | | | |

Plus standalone domain value.

### Buyer fit

- [Buyer archetype 1]
- [Buyer archetype 2]
- [Buyer archetype 3]

### Transfer playbook

A separate transfer-playbook document should cover: domain push, hosting team transfer, GitHub repo transfer, analytics property transfer, ad-network transfer (re-verification), social handle transfers, AI provider billing reassignment, password / 2FA handover via password manager export.

---

## 23. Appendix — Reference Material

### Repository quick-reference

```bash
# Navigate
cd ~/Projects/websites/[project]

# Build
[build command]

# Pipeline (manual)
[command]

# Other useful commands
```

### Site config reference

```json
{
  "site_name": "[…]",
  "domain": "https://[domain]",
  "tagline": "[…]",
  "adsense_client": "[…]",
  "contact_email": "[…]",
  "author": "[…]",
  "ga4_id": "[…]"
}
```

### External documentation links

- Google Search fundamentals: https://developers.google.com/search/docs
- Google AI optimization guide: https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- AI provider docs: [URL]
- Hosting provider docs: [URL]
- OWASP Top 10: https://owasp.org/Top10/
- llms.txt standard: https://llmstxt.org/
- security.txt RFC: https://securitytxt.org/
- ICO (UK GDPR): https://ico.org.uk/
- FTC (US): https://www.ftc.gov/business-guidance/privacy-security

### Related internal documents

- `ProjectHandoffDocument.md` (if any)
- `SecurityAuditHandoff.md`
- `VideoProductionHandoff.md` (if applicable)
- Session handoffs (`SessionHandoff-[topic].md`)

---

## Bonus — Using this file as CLAUDE.md for Claude Code

If saved as `CLAUDE.md` at the repo root, Claude Code will automatically load it as project context. To get the most value:

1. **Keep it under 200 lines if used as the literal CLAUDE.md.** If this document is longer, keep this template as `PROJECT.md` and have a thin `CLAUDE.md` that links to it.
2. **Add a "Conventions" section** with explicit do/don'ts for AI-edited code (e.g. "Never edit `dist/*.html` directly", "Always run `git pull --rebase` before committing").
3. **Add a "Commands" cheat-sheet** with the 5–10 commands an AI agent will need most.
4. **Note any environment quirks** that would otherwise need to be re-discovered.

A focused `CLAUDE.md` typically looks like:

```markdown
# [Project] — Agent context

## What this is
[One paragraph]

## Architecture in one diagram
[ASCII / brief]

## Critical files (don't break these)
- `[file]` — [why critical]
- `[file]` — [why critical]

## Commands
- Build: `[cmd]`
- Test: `[cmd]`
- Deploy: `[cmd]`

## Conventions
- [Rule 1]
- [Rule 2]

## Watch points
- [Gotcha 1 + canonical detection check]
- [Gotcha 2]

## Full project context
See `PROJECT.md` for the master document.
```

---

*End of Master Project Template. Copy, customise, deploy. Update at every significant change.*
