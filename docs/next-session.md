# Start here next session

> **Last touched:** 2026-07-10 — **Content diversification project COMPLETE.** Batches 15–20 finished the job — 167 pages total de-templated (up from 89 at the last handoff), and a fresh full-corpus scan confirms **zero guides remain on the generic six-section template** that started this project on 2026-06-26. Full history + methodology in [`content-diversification-plan.md`](content-diversification-plan.md), which stays the authoritative record for this workstream. **Two corpus-wide rendering bugs found and fixed while drafting the final batches**: `build.py` has no renderer at all for `[text](/guides/slug/)` markdown-link syntax (only bare `/guides/slug/` paths auto-linkify, always substituting the target page's own title as link text) or `**bold**` markdown — both had silently shipped broken/literal markup on several already-published pages across multiple batches; both are now standard checks in the build-verification routine (grep rendered `dist/` for stray `**` and `[text](/guides/` patterns, alongside the existing "…" truncation grep). Corpus is **181 guides** (net of several near-duplicate consolidations found along the way, e.g. `mandate-fraud-uk-businesses`→`invoice-fraud-uk-businesses` — see the diversification doc for the exact arithmetic). **Also since the last handoff:** an AdSense approval audit (2026-07-06) confirmed the site passes all hard gates (privacy opt-out disclosures fixed, pushed live); a full audit (2026-07-09) landed ~30 fixes; a small regex fix (PR #53) corrected a content-gate false-positive ("Act" matching inside "Actually"). **Next focus, now that the diversification backlog is cleared:** (1) **DMARC ramp** — the 2026-07-04 note below said this was "likely ready to check", but there's no record of it actually happening since, so verify the current `p=` value in DNS before assuming progress (see §1 below + `dns-hardening-checklist.md`); (2) **outreach Tier 2/3 monitoring** — same caveat, check `outreach-log.md` for what's actually landed since 2026-07-04 before assuming the cadence continued unattended; (3) if new guides ever land off the bespoke template again (daily-publish cron, a manual edit reverting to old habits), rerun the exact-heading-match scan documented in the diversification plan's batch 19/20 entries early, rather than letting a backlog re-accumulate.
>
> **Prior — Last touched:** 2026-07-04 — **Content diversification batches 11–14 merged & live** (40 pages de-templated/consolidated across PRs #29–31, #33, #34, #36 since this doc was last touched 2026-06-25); full detail + running total in [`content-diversification-plan.md`](content-diversification-plan.md), which has become the dominant recent workstream and is updated far more often than this file. **Also:** PR #37 fixed a gate/canon gap — `deepfake-video-scam-uk`/`sextortion-email-scam-uk` cited the Revenge Porn Helpline (0345 6000 459, verified against revengepornhelpline.org.uk) for intimate-image-abuse support, added 2026-06-25 before that number existed in `content/sources.json`'s canon, so it silently sat as a ticking BLOCK-tier gate finding until this session's `audit_corpus.py` run caught it — now added to canon, corpus back to 0 BLOCK-tier. Corpus is **189 guides** (see the diversification doc for the exact batch-14 arithmetic). Housekeeping: the merged feature branch was deleted (local + remote). **Next focus, in order:** (1) `content-diversification-plan.md`'s own RESUME line — lead with a fresh `gsc_report.py` pull (~mid-July) to see whether batches 1–14 have started ranking, since the generic-outline-with-impressions pool is nearly exhausted; (2) **DMARC ramp is likely ready to check now** — reporting has been on since 2026-06-22 (12+ days as of today, past the "wait 1–2 weeks" gate below), so pull the `dmarc@` aggregate reports and, if both M365 and Resend show pass+alignment, ramp to `p=quarantine`; (3) monitor Tier 2 outreach replies and keep Tier 3 (HARO/Reddit/Quora) moving (item 2 below is otherwise unchanged). The 2026-06-25 audit-remediation entry below is kept for history.
>
> **Prior — Last touched:** 2026-06-25 — **3rd external audit ("BTS AUDIT.md") remediated & verified locally; NOT yet committed/pushed.** Next session = **adding additional locations (geo/i18n expansion)** — the operator will kick that off once re-audits come back clean. This round (full detail in memory `audit-round3-remediation`): **(1)** confirmed + fixed the **critical Netlify Blobs SDK mismatch** — code used the v10 CAS API (`onlyIfMatch`/`onlyIfNew`/`modified`) but `package.json` pinned `^8.1.0`, so every "atomic" control was a silent no-op; repinned **`~10.1.0`** (newest with CAS, before the `@netlify/otel` vuln chain → `npm audit`=0; functions unchanged). **(2)** Node 20→**22**. **(3)** Checker `scrubContact()` redacts prompt-injected phone/URL/email from model free-text; salt chains to `UNSUBSCRIBE_SECRET`. **(4)** Gate now reads headings/title/keywords + 4 new FLAG guards (CRM-code, 7726→NCSC, credit-freeze, threat-dismissal). **(5)** Legal pages no-ads, NPA broadened to sextortion/romance/identity, honest "Fact-checked by Alex Bacsa" line on reviewed guides. **(6) Crons now open a human-review PR instead of committing to `main`** (`auto-content` label); auto-tweet moved to `tweet-on-publish.yml` (post-merge, ≤3-slug cap + dedupe). **(7) 50 guides content-fixed** (CRM→mandatory APP reimbursement, US fraud-alert/credit-freeze→Cifas, 7726→mobile networks, Companies House absolutes+domain, brand-domain absolutes, NFB→Cifas; **safety-critical** sextortion/deepfake "no-proof≠fake" reframe). Build clean (190 posts, all sanity checks pass). **USER ACTIONS done since (2026-06-25):** ✅ repo "Allow GitHub Actions to create/approve PRs" enabled; ✅ **DKIM selector 1** corrected (both M365 selectors sign); ✅ Resend DKIM **closed at 1024** (Resend offers no 2048 — vendor limit, passes DMARC). **STILL OPEN:** DMARC enforcement ramp (in testing at `p=none`); DNSSEC (optional, blocked on Dynadot); HSTS preload inclusion (re-check); run **Gate self-test** Action (gate changed); **commit this round + "Clear cache and deploy"**. Full DNS status: `dns-hardening-checklist.md`.
>
> **Prior — Last touched 2026-06-22:** **2nd Executive Verdict remediated (tranches A–E) & live; DNS hardening (tranche F) in progress.** A fresh external review surfaced more items, all code/content now fixed + deployed + verified live: charity & DWP content errors corrected (web-verified), author-bio honesty, **function-response security headers**, **expiring (7-day) confirm tokens** + reactivate-on-duplicate, checker no longer logs raw model output, supply chain (**`package-lock.json` + Dependabot + CodeQL**), **`/check/` excluded from ads + non-personalised ads on debt/recovery pages**, privacy-policy precision (web beacons/identifiers). **DNS done:** DMARC reporting (`p=none`+rua=dmarc@), CAA, HSTS preload submitted, M365 DKIM→2048. **DNS pending:** DMARC quarantine→reject ramp (after ~1–2 wks clean reports), Resend DKIM→2048 (support ticket; low priority), DNSSEC (blocked on Dynadot). Full DNS status: [`dns-hardening-checklist.md`](dns-hardening-checklist.md). DNS is at **Dynadot**.
>
> **Round 1 (2026-06-21) — Executive Verdict closed & live.** Worked an external review end-to-end: hardened the accuracy gate (deterministic absolute-claim check after the LLM judge leaked fabricated stats into a sextortion guide) + cleaned the corpus (46 hardcoded org phone numbers); checker reporting-link domain allow-list; site-wide search (lean `search.json`); de-dangled 53 SEO titles; affiliate cards "Sponsored"→"Recommended" (unpaid); **E-tier:** durable checker rate-limit + `DAILY_CALL_CAP=2000`/day spend cap via Netlify Blobs (first `package.json`), **newsletter → double opt-in**, **Google certified CMP** for UK/EEA consent (app.js defers to it). **Then built the editorial-accuracy system:** verified source canon (`content/sources.json` — single source of truth for the gate's allow-lists AND the on-page reporting block), per-guide **claim manifests** (`content/manifests/`), and a **weekly audit digest** (`.github/workflows/weekly-audit.yml`, emails flag-tier claims via Resend). **Closed the last residuals:** malformed model output no longer publishes a thin fallback guide (quarantines instead); privacy notice completed to the ICO checklist; and the audit itself caught **4 real content errors** (3 stale/wrong reporting emails + a mis-cited Act → Consumer Credit Act 1974). All pushed & live; gate self-test green. Full detail: `docs/project.md` (Section 20 gotchas 22–25, content-accuracy section) + memories `content-pipeline-safety-hold` + `e-tier-hardening-pending-push` + `executive-verdict-remediation`. (Round 1 left no open defects; the 2026-06-22 round 2 above then added another pass — see top.)
> **✅ Newsletter (double opt-in, LIVE & verified):** capture → **confirmation email** → click → welcome → one-click unsubscribe, all confirmed working. `RESEND_API_KEY` + `RESEND_AUDIENCE_ID` + `UNSUBSCRIBE_SECRET` all set in Netlify (the secret is now **required for signup** and also signs the confirm link).
> **✅ Tier 2 outreach sent** (2026-06-10): Lovemoney, Money to the Masses, This Is Money, MoneyMagpie, Graham Cluley — all logged in [`outreach-log.md`](outreach-log.md). Be Clever With Your Cash = deliberately skipped (auto-spams link asks). **When replies land, log the outcome (✅ live / ✖ declined) in the log.**
> **Next focus:** (1) **DNS DMARC ramp** — after ~1–2 wks, read the `dmarc@` aggregate reports, confirm BOTH M365 and Resend pass, then go `quarantine` (pct ramp) → `reject` (values in `dns-hardening-checklist.md`); (2) **monitor + respond to Tier 2 replies** over the next ~1-2 weeks; (3) start **Tier 3 — Featured.com/HARO** (answer ~5 UK scam queries/week → journalist quotes) and the **Reddit/Quora cadence** (templates in [`outreach-templates.md`](outreach-templates.md)); (4) chase AdSense + affiliate hrefs; (5) optional/low-priority: DNSSEC only if DNS moves off Dynadot. (Resend DKIM is closed at 1024 — no 2048 option; M365 DKIM both selectors done.) **For future newsletters:** send as Resend **Broadcasts** + `{{{RESEND_UNSUBSCRIBE_URL}}}` footer token (Resend handles unsubscribe automatically there; the welcome email self-hosts it because that token does NOT work on `/emails`).
> **What you need from yourself:** a Featured.com (HARO) account for Tier 3; otherwise nothing blocking.

This doc is the **fast-start punch list** for the next session — read it before re-opening anything else and you'll be productive in 2 minutes instead of 20.

The exhaustive context lives in `docs/project.md`. This file is the index.

---

## Where things stand (as of last close)

- **Done 2026-06-05→09** (full detail in `project.md` §21): reclaimed the DPD/Yodel/UPS courier guides **plus a 2nd purged batch** (Amazon-call / chargeback / Gumtree / Google-Voice) the AdSense purge had 301'd away; built the **top-3 category hubs** (SMS, Payment, Government pillar pages — `content/category-hubs.json`); fixed GSC auth + added `scripts/gsc_report.py`; reached the cross-platform video verdict (**YouTube Shorts + the site win**); fixed the `shorten_warning` truncation bug; built the **Tier 1 citation/E-E-A-T foundation** (`docs/outreach-log.md`).
- **Newsletter (double opt-in since 2026-06-20):** sitewide email-capture band (above the footer on every page) → `subscribe.js` emails an HMAC-signed confirm link (adds nobody yet) → `confirm-subscribe.js` adds the Resend Audience contact + sends the welcome only on confirm (GET=confirm page, POST=mutate, scanner-safe) → `unsubscribe.js`. All hardened (rate limit, origin allow-list, consent + honeypot). **Routing gotcha:** every `/api/*` rewrite (`subscribe`, `confirm-subscribe`, `unsubscribe`, `csp-report`) lives in `dist/_redirects` (emitted by `build()`), NOT `netlify.toml` — new toml `[[redirects]]` beyond the grandfathered `/api/check-scam` rule are silently ignored at the edge here.
- **Site Health 98%**, **AI Search Health 99%**, Lighthouse mobile 92–97 / SEO 100. Technical build is mature and stable; the open surface is editorial accuracy (now gated + source-canon-validated + claim manifests + weekly audit), not infrastructure. ~191 residual Semrush warnings are Google's AdSense CDN (irreducible).
- **181 guides** (grows ~1/day via the gated cron, net of consolidations — see `docs/content-diversification-plan.md` for the current count), 17 categories, daily publish via GitHub Actions. **Content diversification project complete 2026-07-10** — zero guides remain on the generic template. **Video production discontinued 2026-06-15** (built no authority/backlinks — see `docs/video-pipeline.md`).
- **E-E-A-T:** Alex Bacsa named author across all guides + `/author/` page, role standardised to "Founder & Editor" everywhere, `sameAs` to LinkedIn + 3 sister pubs. Disavow file (66 domains), security.txt, llms.txt, full UK Terms all live.

If anything in the above feels stale on re-read, the canonical source is `docs/project.md` Section 21 "Recently completed".

---

## 1. DNS DMARC ramp — ⏳ NEXT (wait ~1–2 weeks first)

> **Why first / why wait:** this is the one DNS item with real delivery risk, so it must NOT be rushed. DMARC is at `p=none` with reporting on (since 2026-06-22). Before enforcing, let ~1–2 weeks of `dmarc@beatthescam.com` aggregate reports accumulate and confirm BOTH senders pass alignment: **Microsoft 365** (apex mail) and **Resend** (newsletter from `updates.`). Enforcing early would quarantine your own subscriber mail.

### What to bring to the session

- The DMARC aggregate (`rua`) reports landing at `dmarc@` (alias of `privacy@`). If raw XML is hard to read, paste a few into a DMARC report viewer (e.g. dmarcian / MXToolbox) first, or forward them here.

### What we'll do

1. Confirm M365 and Resend both show SPF and/or DKIM **pass + alignment** across the reports.
2. If clean, move to `p=quarantine; pct=25` → ramp `50` → `100` (exact records in [`dns-hardening-checklist.md`](dns-hardening-checklist.md) §1).
3. Then `p=reject; sp=reject`.
4. Optional low-priority cleanup: reconsider DNSSEC only if DNS ever moves off Dynadot. (**Resend DKIM is closed at 1024** — Resend offers no 2048 option; it passes DMARC. **M365 DKIM is done** — both selectors sign after the 2026-06-25 selector-1 fix.)

### Reference doc

- [`dns-hardening-checklist.md`](dns-hardening-checklist.md) — full status + exact record values for every step.

---

## 2. Backlinks & outreach push — Tier 1 ✅ DONE, Tier 2 next

> **Tier 1 (citations/foundation) complete** — see `docs/outreach-log.md`: About.me, Trustpilot, Owler, F6S, LinkedIn personal + company pages all live; Take Five / FAS / Get Safe Online affiliations sent. **Next = Tier 2 link insertions** (the real dofollow lever): pitch the courier/bank-text guides to UK money blogs that already cover these scams. Shortlist + 3 templates ready in `docs/outreach-templates.md`. Original playbook kept below.

> **Why this matters:** Authority Score is **2**. The technical SEO ceiling has been hit. The single biggest growth lever remaining is **earning quality backlinks**, which is pure outreach work that cannot be automated.

### Reference doc

Full playbook is `docs/project.md` Section 14 "Backlinks, Authority & Domain Authority Plan". Read it once before the session.

### What to bring to the session

| Item | Where to get it |
|---|---|
| **Target list** (5-10 UK consumer-finance / fraud-prevention sites) | We'll build this together in the session — bring any sites you already read or admire |
| **HARO / Featured.com account** | Sign up at <https://featured.com/> (free) — takes 2 minutes |
| **Spreadsheet for outreach tracking** | Either your existing Project Tracker (.xlsx) or a fresh sheet — columns: domain, contact name, email, date contacted, response, link earned (Y/N) |
| **Personal email** to send outreach from | The `hello@beatthescam.com` mailbox or a personal address that doesn't go to spam filters |

### Per-week cadence target (Section 14)

| Tactic | Frequency | Target wins/month |
|---|---|---|
| Directory submissions | 5/week × 6 weeks then maintenance | 5–10 links |
| Reddit r/Scams + r/UKPersonalFinance contributions | 3–5/week | 2–4 links (natural mentions) |
| Quora answers | 2/week | 2–4 links |
| Link-insertion outreach (email pitches) | 5–10/week | 1–3 placements |
| Guest post pitches | 3/week | 1 placement/month |
| HARO responses | 5/week | 1–2 quotes/month |

### What to expect from this session's Claude work

We'll:
1. Triage a starter list of **20-30 UK target sites** by relevance and reach-difficulty
2. Draft **3 email templates** (cold outreach, link-insertion, guest-post pitch) you can paste and personalise
3. Pick the first 5 directories to submit to + walk through the submission process
4. Set up the Reddit/Quora cadence with the topical angles you'll lead with
5. Optionally extend `docs/project.md` with an outreach-log section so wins are tracked over time

---

## 3. Smaller items if time allows

Pulled forward from `docs/project.md` Section 21 in priority order. None are blocking.

- [ ] **Semrush Position Tracking** — swap Spain (Spanish) → United Kingdom (English). Dashboard task, 1 minute. The free tier's 1-target limit means delete-then-add (not add-then-delete).
- [x] **Activate mailbox aliases — DONE 2026-06-09.** `abuse@`, `hello@`, `legal@`, `privacy@`, `security@`, `socialmedia@` are all live. Site copy now routes to dedicated inboxes (driven by new `site.json` keys `security_email`/`privacy_email`/`legal_email`): `security.txt` + contact page → `security@`; Privacy Policy + Cookie Policy → `privacy@`; Terms-legal + copyright → `legal@`; general/editorial/corrections stay on `hello@`. About/Terms now names **Alex Bacsa, Founder & Editor** as the editorial decision-maker (was "editorial team").
- [ ] **Confirm Twitter API keys** are stored in GitHub Secrets (not just `.env`) — currently risk-zone if a daily-publish ever fails on a Twitter-keys-missing path.
- [ ] **Top 3 category hub pages** (600–800 words each) — editorial work. Pick the three highest-traffic categories from GSC and expand the existing landing page bodies.
- [ ] **PageSpeed re-check** — confirm the homepage's pre-deploy amber FCP/LCP cleared after the 2026-06-04 preconnect commit landed. URL: <https://pagespeed.web.dev/analysis?url=https%3A%2F%2Fbeatthescam.com%2F>.

---

## How to start the next session in 30 seconds

**Open Claude and paste:**

> Picking up from last session — see `docs/next-session.md`. Today I want to do [analytics review / backlinks kickoff / both]. I have [data ready / questions about X / dashboard tabs open]. Let's go.

That's it. Claude reads this doc first, knows the state, and dives straight into productive work.

---

## What this doc is NOT

- **Not** the canonical reference for site state — that's `docs/project.md` (1400+ lines, full history)
- **Not** the runbook — that's `docs/daily-publish.md` (operational details for the daily pipeline)
- **Not** the video pipeline docs — that's `docs/video-pipeline.md` (full pipeline + analytics methodology)
- **Not** the YouTube setup guide — that's `docs/youtube-upload-setup.md` (one-time OAuth setup)

This doc is **the front door**. Read it, then the others on demand.
