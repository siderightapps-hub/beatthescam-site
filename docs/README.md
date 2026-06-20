# Master Documentation — Summary

> Created: 2026-05-20
> Companion summary to `project.md` and `project-template.md`.

---

## What was produced

| # | File | Purpose | Audience |
|---|---|---|---|
| 0 | [`next-session.md`](next-session.md) | **Fast-start punch list — read this first when opening a new chat.** Covers where things stand, what to do next, and what data to bring. ~3-minute read. | Owner · new Claude chats |
| 1 | [`project.md`](project.md) | Complete, project-specific source-of-truth for the Beat The Scam website | Owner · new Claude chats · potential buyers · contractors |
| 2 | [`project-template.md`](project-template.md) | Generic, reusable template for any future website project — also doubles as a baseline `CLAUDE.md` for Claude Code | Future projects |
| 3 | [`video-pipeline.md`](video-pipeline.md) | The canonical video production pipeline (Pillow text cards + ElevenLabs + MoviePy) including cross-platform analytics methodology | Video production work |
| 4 | [`youtube-upload-setup.md`](youtube-upload-setup.md) | One-time OAuth setup for `scripts/upload_to_youtube.py` | Setup only |
| 5 | [`daily-publish.md`](daily-publish.md) | Daily-publish operational runbook | Pipeline debugging |
| 6 | `README.md` *(this file)* | Quick-reference index, summary of what the documents cover, and "where do I look for X?" map | All audiences |

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
│  project-template.md                          │
│  ────────────────────────────────                          │
│  Same structure, placeholders instead of facts.            │
│  Copy → new project → fill in → live.                      │
│  Doubles as a baseline CLAUDE.md.                          │
└────────────────────────────────────────────────────────────┘
```

The five existing handoff documents (`ProjectHandoffDocument.md`, `SecurityAuditHandoff.md`, the two `SessionHandoff-…` files, and `video-pipeline.md`) remain useful as **historical records** of specific work sessions, but going forward the **master document is the canonical reference**. Update the master first, the session handoffs second.

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
| 12 | Social Media & Video Production | Posting cadence, hashtag templates |
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
- **Asset valuation matrix** — 30–40× multiple math + standalone domain value
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
| What's the next video topic? | `video-pipeline.md` Section 2 |
| Which schema types are deployed? | Section 13 |
| What's the cookie consent posture? | Section 16 |

---

## Recommended next actions

> **For the next-session focus**, see [`next-session.md`](next-session.md) — it has the punch list, the data you need to gather, and the order to tackle it in.

Pulled forward from `project.md` Section 21:

### Next session — primary focus

- [ ] **Cross-platform video + Twitter analytics review** — first proper post-publish review of YouTube Shorts + TikTok + Instagram Reels + X data side-by-side. See `docs/video-pipeline.md` Section 11 for the methodology.
- [ ] **Backlinks push** — start the structured outreach cadence in `project.md` Section 14. Authority Score 2 → 10+ is the single biggest remaining growth lever.

### Secondary (slot in as bandwidth allows)
- [ ] Semrush Position Tracking — swap Spain → UK (1-min dashboard task)
- [ ] Activate `privacy@`, `security@`, `editorial@`, `legal@` mailbox aliases (DNS task)
- [ ] Confirm Twitter API keys are stored as GitHub Secrets
- [ ] Build out the top 3 category hub pages (600–800 words each)
- [ ] Find a workable video music bed (`assets/audio/news-bed.mp3` empty)
- [ ] Awin reapply (window opens 2026-06-12) + CJ follow-up + direct affiliate outreach
- [ ] AdSense approval chase

### Recently completed (2026-06-04) — fully captured in `project.md` Section 21
- ✅ `/terms/` full UK rewrite (E&W + Scotland + NI)
- ✅ Named author + cross-publication E-E-A-T (Alex Bacsa, real headshot, `sameAs` to 3 sister pubs)
- ✅ `/author/` page generated
- ✅ `/.well-known/security.txt` (RFC 9116) live
- ✅ GSC failing-validation URL triage (1 fix, 9 already resolved)
- ✅ Mobile LCP optimisation (AdSense preconnect)
- ✅ PageSpeed baseline captured (mobile 92–97 Performance across pages)

### Near-term (4–8 weeks)
- Near-miss query optimisation pass
- Contextual in-body internal-linking sweep across top 30 guides
- Foundation backlinks (5/week directory submissions, Reddit/Quora cadence)
- Affiliate `href` replacement as programmes approve

### Medium-term (8–24 weeks)
- URL Checker feature (VirusTotal + Google Safe Browsing)
- ~~Email newsletter launch~~ — ✅ **LIVE** (Resend, double opt-in)
- First guest-post placement on DA 40+ UK publication
- Trademark filing

---

## How to use these documents going forward

### For the owner

1. **Update `project.md` first** whenever anything material changes — keys rotated, affiliate approved, security re-scanned, new section in the build pipeline, etc.
2. Then optionally write a thin `SessionHandoff-[topic].md` for the session-specific narrative.
3. Update `Last updated:` at the top of the master document on every meaningful change.

### For Claude Code / new chat sessions

Paste the relevant section(s) of `project.md` into the chat. If using Claude Code on this repo, point Claude at the file directly with `@project.md` or place a thin `CLAUDE.md` at the repo root that links to it.

### For potential buyers

Share `project.md` Sections 1, 2, 3, 7, 10, 13, 22, and 23 first. Hold Sections 6 (secrets) and 17 (security details) back until under NDA.

### For starting the next project

Copy `project-template.md` to the new project's repo as `PROJECT.md` (or `CLAUDE.md`), then walk down section-by-section, filling in placeholders. The template is the fastest way to start a new project with the same operational maturity as Beat The Scam.

---

## Document versioning

- **v1.4 — 2026-06-04** — Technical-build closeout. Added [`next-session.md`](next-session.md) as the fast-start front door for resuming work. `project.md` updates: top header + new "Recently completed (2026-06-04 session)" block (Terms rewrite, named author E-E-A-T, security.txt, GSC URL triage, AdSense preconnect, Lighthouse baseline), Section 9 gains PageSpeed Insights subsection with baseline numbers + API rate-limit gotcha, Section 18 `security.txt` flipped Live, Section 21 "This week / next session" refocused on the two primary growth items (cross-platform analytics review + backlinks push). README's "What was produced" table now includes all 6 docs with relative links + flags next-session.md as the front door.
- **v1.3 — 2026-05-30** — Three-front session: Instagram channel activated (`@beatthescamuk`), full Semrush remediation pass (Site Health 96% → 98%, AI Search 88% → 99%, 454 issue-instances cleared), Google disavow file uploaded for 66 toxic domains. project.md gains Section 14 Disavow Policy subsection + Section 9 Semrush subsection.
- **v1.2 — 2026-05-22 (afternoon)** — Three further capability ships:
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

*End of Summary. The three documents (`project.md`, `project-template.md`, `README.md`) plus `video-pipeline.md` together replace the entire ad-hoc handoff document set as the canonical project documentation. The prior session handoffs (`beatthescam-chat-handoff.md`, the in-flight `SessionHandoff-*` markdown files at repo root, `ProjectHandoffDocument.md`, `SecurityAuditHandoff.md`, `Template.md`) can be deleted — every fact from them that's still load-bearing is now in this canonical set.*
