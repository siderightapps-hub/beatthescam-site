# Master Documentation — Summary

> Created: 2026-05-20
> Last reviewed: 2026-07-19
> Companion summary to `project.md` and `project-template.md`.

---

## What was produced

| # | File | Purpose | Audience |
|---|---|---|---|
| 0 | [`next-session.md`](next-session.md) | **Fast-start punch list — read this first when opening a new session.** Covers the verified baseline, priorities and operating rules. | Owner · Codex/Claude sessions |
| 1 | [`project.md`](project.md) | Complete, project-specific source-of-truth for the Beat The Scam website | Owner · Codex/Claude sessions · potential buyers · contractors |
| 2 | [`project-template.md`](project-template.md) | Generic, reusable template for any future website project — also doubles as a baseline `CLAUDE.md` for Claude Code | Future projects |
| 3 | [`video-pipeline.md`](video-pipeline.md) | **HISTORICAL** — video production pipeline (Pillow text cards + ElevenLabs + MoviePy). Video was **discontinued 2026-06-15**; kept for reference only | Historical reference |
| 3b | [`dns-hardening-checklist.md`](dns-hardening-checklist.md) | DNS / email-auth / TLS operator runbook (DMARC, DKIM, CAA, DNSSEC, HSTS) — tranche F of the 2026-06-22 Executive Verdict | Owner · DNS work |
| 4 | [`youtube-upload-setup.md`](youtube-upload-setup.md) | **HISTORICAL / INACTIVE** OAuth setup for the discontinued upload workflow | Historical reference |
| 5 | [`daily-publish.md`](daily-publish.md) | Daily-publish operational runbook | Pipeline debugging |
| 6 | [`search-ai-measurement.md`](search-ai-measurement.md) | Monthly Search Console and Bing AI visibility measurement method | Owner · growth analysis · buyers |
| 7 | [`buyer-data-room/README.md`](buyer-data-room/README.md) | Non-confidential diligence index, asset perimeter and transfer-readiness evidence map | Owner · advisers · potential buyers |
| 8 | [`site-content-adsense-search-audit-2026-07-16.md`](site-content-adsense-search-audit-2026-07-16.md) and [`site-content-adsense-search-audit-2026-07-17.md`](site-content-adsense-search-audit-2026-07-17.md) | **HISTORICAL** point-in-time audit evidence; not the current task list | Audit trail |
| 9 | `README.md` *(this file)* | Quick-reference index, summary of what the documents cover, and "where do I look for X?" map | All audiences |

**The fastest way to start a new session** is to open `docs/next-session.md`. It has been written specifically to be the front door for resuming work and links into the other docs on demand.

---

## How the documents relate

```
┌────────────────────────────────────────────────────────────┐
│  project.md                      │
│  ────────────────────────────────────────                  │
│  The single source-of-truth for Beat The Scam.             │
│  Updated whenever anything material changes.               │
│                                                            │
│  Consolidates / supersedes:                                │
│   ├─ ProjectHandoffDocument.md                             │
│   ├─ SecurityAuditHandoff.md                               │
│   ├─ SessionHandoff-SEOHygieneAndBullet-ListBugFix.md      │
│   ├─ SessionHandoff-SEOHygieneBullet-…-HouseKeeping.md     │
│   └─ video-pipeline.md  (referenced, not merged)   │
└──────────────────────────────┬─────────────────────────────┘
                               │ inspired
                               ▼
┌────────────────────────────────────────────────────────────┐
│  project-template.md                                      │
│  ────────────────────────────────                          │
│  Same structure, placeholders instead of facts.            │
│  Copy → new project → fill in → live.                      │
│  Doubles as a baseline agent-instruction document.         │
└────────────────────────────────────────────────────────────┘
```

The former root handoff documents have already been retired and are no longer present. `video-pipeline.md`, dated audits and the completed diversification plan remain as **historical records**. Update `project.md` for durable facts and `next-session.md` for the current operational state; do not create a second independent current-status list.

---

## What's in the Beat The Scam Master Document — section map

| Section | Topic | When you need this |
|---|---|---|
| 1 | Brand & Project Overview | Onboarding a new collaborator; pitching to buyers |
| 2 | Ownership, Contacts & Email Addresses | Activating mailbox aliases, GDPR contact lookup |
| 3 | Tech Stack & Architecture | Understanding the build, choosing where to make a change |
| 4 | Repository Structure | Finding the right file |
| 5 | Hosting & Deployment (Netlify) | Deploy debugging, credit usage planning |
| 6 | Environment Variables & Secrets | Key rotation, troubleshooting failed builds |
| 7 | API Keys & Third-Party Accounts | The full inventory of external dependencies — critical for transfers |
| 8 | Domain, DNS & SSL | Domain transfer, DNS changes, SSL renewals |
| 9 | Analytics & Tracking | Reading GA4, setting up new events |
| 10 | Monetisation | AdSense status, affiliate onboarding, ad unit IDs |
| 11 | Content Operations & AI Pipeline | Running manual pipelines, debugging the daily workflow |
| 12 | Social Media & Video Production (video discontinued 2026-06-15) | Posting cadence, hashtag templates |
| 13 | SEO, GEO & AEO Strategy | All three search-mode strategies; near-miss query work |
| 14 | Backlinks, Authority & DA Plan | Outreach cadence, directory submissions, niche edits, Reddit/Quora |
| 15 | Target Audience & Brand Voice | Editorial decisions, voice-check |
| 16 | Legal, Compliance, GDPR & Privacy | Data requests, consent (Google certified CMP), affiliate disclosure |
| 17 | Security Posture (OWASP) | Re-scan checklist, OWASP coverage matrix, recurring checks |
| 18 | Site Files (sitemap, robots, ads, llms, security.txt) | Each canonical site file, including emerging standards |
| 19 | Operational Runbook | Daily / weekly / monthly / quarterly / annual cadence |
| 20 | Known Issues & Watch Points | Every gotcha that's bitten the project — read before making changes |
| 21 | Outstanding Roadmap | What's next this week / 4–8 weeks / 8–24 weeks / 6–12 months |
| 22 | Asset Valuation & Acquisition Brief | Buyer-facing briefing material |
| 23 | Appendix | Quick command reference, JSON config, external docs, related internal docs |

---

## What's in the Template — same structure, made generic

The Template mirrors the Beat The Scam document section-by-section but replaces specifics with `[placeholders]` and `TBD`s, and adds:

- **Generic API-key checklist** of services any modern content site touches (AI providers, analytics, ads, social, affiliates, registrars, security tools).
- **Generic backlink playbook** that adapts to any vertical.
- **GEO / AEO checklist** aligned to Google's AI optimization guide.
- **`llms.txt` and `security.txt` templates** ready to paste in.
- **A bonus closing section** on how to use the file as a `CLAUDE.md` for Claude Code — covering the trade-off between long-form `PROJECT.md` + thin `CLAUDE.md` vs single file.

---

## What's covered that wasn't explicitly in Template.md

The brief asked to "add any other information that I may have missed." Items added that weren't in the original list:

- **`llms.txt`** — emerging standard for LLM citation guidance ([llmstxt.org](https://llmstxt.org/))
- **`security.txt`** — RFC 9116 responsible-disclosure file
- **`humans.txt`** — optional credits file
- **HSTS preload** — explicit submission to the browser preload list
- **DNSSEC + domain registrar lock** — registrar-level hardening
- **Subdomain reservations** — `mail.`, `app.`, `status.`, etc. for future use
- **AEO** (Answer Engine Optimization) — alongside SEO and GEO
- **Near-miss query strategy** — the highest-leverage SEO move for sub-page-1 traffic
- **Niche edits vs guest posts ROI ranking** — captured per the brief's emphasis
- **Reddit / Quora cadence with anti-pattern warnings** — "be a contributor first, link-dropper never"
- **HARO / Featured.com** — explicit listing
- **Evidence-led acquisition brief** — current asset perimeter, verified baseline, valuation policy and sale-readiness gaps
- **Buyer-fit archetypes** — UK ID-protection, cybersecurity SaaS, insurance, consumer-finance media
- **Transfer playbook** — pointer to a separate dedicated document
- **Operational cadence** broken into daily / weekly / monthly / quarterly / annual
- **OWASP Top 10 mapping table** explicitly for each item
- **Re-scan checklist with canonical detection commands** — so regressions are caught in seconds
- **Email alias rationale** — why `privacy@`, `security@`, `abuse@`, `legal@` matter even on a small site
- **Trademark guidance** — UK IPO class 41 + 42 for educational + AI services
- **Accessibility (WCAG 2.1 AA)** — quarterly audit cadence
- **Editorial anti-patterns** — clickbait, fear-mongering, sales-y CTAs around free tools
- **Schema markup explicitly listed** by type — `WebSite`, `Organization`, `Article`, `FAQPage`, `BreadcrumbList`

---

## Where to look for what — quick "find by question" map

| Question | Look in |
|---|---|
| What's the AdSense Publisher ID? | Section 10 (also Section 7) |
| What's the GA4 measurement ID? | Section 9 |
| Where's the API key stored? | Section 6 |
| Who's the data controller for GDPR requests? | Section 16 |
| What's the security re-scan cadence? | Section 17 |
| What's the next AdSense chase date? | Section 20 / Section 21 |
| When can we reapply to Awin? | Section 10 / Section 21 |
| What's the daily publish schedule? | Section 11 |
| What does the daily pipeline do step-by-step? | Section 5 |
| Why does Netlify need `dist` set in the dashboard? | Section 20 (gotcha #1) |
| How do I push from local? | Section 19 |
| What's the valuation today? | Section 22 |
| Which directories should I submit to? | Section 14 |
| Which schema types are deployed? | Section 13 |
| What's the cookie consent posture? | Section 16 |

---

## Recommended next actions

[`next-session.md`](next-session.md) is the sole current punch list. At the 2026-07-19 documentation review, its priorities are: capture monetisation/conversion evidence; establish the saleable asset perimeter; reduce key-person and transfer risk; complete the evidence-gated DMARC ramp; earn authority and continue measurable research; and keep the human-review publishing queue healthy.

Do not copy that checklist into another document. Durable facts and dated history belong in `project.md`; workstream methods belong in their runbooks; completed audits and the diversification plan remain historical evidence.

---

## How to use these documents going forward

### For the owner

1. **Update `project.md` first** whenever anything material changes — keys rotated, affiliate approved, security re-scanned, new section in the build pipeline, etc.
2. Update `next-session.md` when the verified baseline or priorities change.
3. Update the relevant specialist runbook or buyer-data-room register when its evidence changes.
4. Update `Last updated:` at the top of the master document on every meaningful change.

### For Codex, Claude Code and new sessions

Read the root instruction file first, then [`next-session.md`](next-session.md) and only the relevant section(s) of `project.md`. This repository intentionally keeps root `AGENTS.md` (discovered by Codex) and `CLAUDE.md` (used by Claude tooling) as exact byte-for-byte duplicates. Update both together and verify with `cmp -s AGENTS.md CLAUDE.md`.

### For potential buyers

Share `project.md` Sections 1, 2, 3, 7, 10, 13, 22, and 23 first. Hold Sections 6 (secrets) and 17 (security details) back until under NDA.

### For starting the next project

Copy `project-template.md` to the new project's repo as `PROJECT.md` (or `CLAUDE.md`), then walk down section-by-section, filling in placeholders. The template is the fastest way to start a new project with the same operational maturity as Beat The Scam.

---

## Document versioning

- **v1.5 — 2026-07-19** — Refreshed the operational-document index, added the Search/AI measurement and buyer data-room workstreams, clarified historical audit status, and documented the exact `AGENTS.md`/`CLAUDE.md` mirror policy for Codex and Claude sessions.
- **v1.4 — 2026-06-04** — Technical-build closeout. Added [`next-session.md`](next-session.md) as the fast-start front door for resuming work. `project.md` updates: top header + new "Recently completed (2026-06-04 session)" block (Terms rewrite, named author E-E-A-T, security.txt, GSC URL triage, AdSense preconnect, Lighthouse baseline), Section 9 gains PageSpeed Insights subsection with baseline numbers + API rate-limit gotcha, Section 18 `security.txt` flipped Live, Section 21 "This week / next session" refocused on the two primary growth items (cross-platform analytics review + backlinks push). README's "What was produced" table now includes all 6 docs with relative links + flags next-session.md as the front door.
- **v1.3 — 2026-05-30** — Three-front session: Instagram channel activated (`@beatthescamuk`), full Semrush remediation pass (Site Health 96% → 98%, AI Search 88% → 99%, 454 issue-instances cleared), Google disavow file uploaded for 66 toxic domains. project.md gains Section 14 Disavow Policy subsection + Section 9 Semrush subsection.
- **v1.2 — 2026-05-22 (afternoon)** — Three further capability ships:
  - **Auto-thumbnail generation + auto-upload.** `scripts/generate_video.py` now renders a brand-aligned 1280×720 JPEG sidecar; `scripts/upload_to_youtube.py` uploads it via `yt.thumbnails().set()` after the video upload (non-fatal on phone-verification failure). Per-family `thumbnail_text` in `HOOK_TEMPLATES` keeps copy topic-correct.
  - **Never-cut-mid-sentence guarantee.** `shorten_warning()`'s ellipsis-fallback step was deleted entirely. If no clean clause boundary exists within 90 chars, the function returns the full original sentence. Eliminates the `"bank…"` / `"didn't expect…"` failure mode by construction, not by best-effort.
  - **macOS Reminders integration.** `scripts/upload_to_youtube.py` creates a "Upload `<slug>` to TikTok" reminder for 07:30 local time after every successful upload — closes the only manual step remaining in the daily pipeline. Syncs to iPhone via iCloud. New `--test-reminder` flag to grant the first-time macOS permission prompt.
- **v1.1 — 2026-05-22** — Folded in the contents of the prior session's `beatthescam-chat-handoff.md` (now deletable) plus today's pipeline work:
  - `video-pipeline.md` **rewritten** for the new `scripts/generate_video.py` text-card pipeline; the old Gemini-character / CapCut workflow is retired.
  - `scripts/upload_to_youtube.py` + `scripts/get_youtube_refresh_token.py` + `docs/youtube-upload-setup.md` added.
  - Master doc Section 6: ElevenLabs key rotation history added (2026-05-18/19 leak event); local `.env` variables documented; worktree `.env` sync options.
  - Master doc Section 7: Bing Webmaster Tools entry added.
  - Master doc Section 11: 5-bullet "Major completed milestones" timeline added (security audit, SEO hygiene, 14-item SEO sweep, video pipeline build, daily-publish concurrency fix, video-pipeline extensions).
  - Master doc Section 12: video workflow replaced — one-command render + one-command upload.
  - Master doc Section 13: SEO structural foundations expanded (per-post OG images, ItemList/HowTo schema, pagination, RSS discovery, hreflang, sitemap lastmod, linkified guide paths).
  - Master doc Section 20: **anti-patterns section added** — explicit guardrails so future sessions don't re-litigate the James Carter pseudonym, HMRC phonetics, video catchphrase, voice ID, dist-merge logic.
  - Master doc Section 21: 8 pending GSC URLs follow-up + Etsy-style resurrection pattern + music-bed search added.

Future updates should bump the version and note what changed.

---

*End of summary. Current status lives in `next-session.md` and `project.md`; operational detail lives in the linked runbooks; dated audits and retired pipeline documents remain historical evidence rather than current task lists.*
