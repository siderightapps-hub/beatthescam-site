# Start here next session

> **Last updated:** 2026-07-25
> **Repository state:** `main` at `5b935f85e`; production verified live; no open `auto-content` PR at close; working tree clean.

## Since 2026-07-24 (fresh full audit + remediation session, closed 2026-07-25)

- A **fresh 15-agent full audit** (all 186 guides live fact-checked + technical SEO + AdSense readiness + AI visibility) found the corpus near-perfect: 184/186 clean, 3 findings in 2 guides, AdSense verdict PASS_WITH_FIXES with **zero blockers**, no HIGH technical-SEO issues, AI visibility already top-tier. All remediation was operator-approved (7/7 `-c.md` replies) and **shipped live at `5b935f85e`**:
  - Content fixes: `hmrc-tax-refund-text-scam-uk` (GOV.UK dropped the "never notify a rebate by text" absolute in Dec 2024), `instagram-fake-giveaway-scam-uk` (blue tick = legacy notability OR paid Meta Verified; NI number; + missing `sources_checked` — corpus now 185/185 sourced).
  - **Quick answer box on all 185 guides** (`quick_answer` field; verdict-first 35–60-word summary rendered above the Key rule, with `speakable` schema). Operator standing rule: when a guide's content changes, regenerate/recheck its quick answer.
  - **New `/research/uk-scam-statistics/`** — 28 live-verified official records with per-record geography labels, CSV+JSON downloads, Dataset schema (CC BY 4.0). Quarterly refresh due **October 2026**.
  - Guide expansions: dvla-vehicle-tax-text-scam (~1,200 words), halifax-bank-scam-text-uk (incl. Halifax→Lloyds brand-change section — announced 2 Jul 2026, closed to new customers 16 Jul 2026), nhs-appointment-scam-text-uk (genuine-NHS-charges nuance, England-labelled).
  - NPA ad mode extended to advance-fee-scam-uk and fake-online-pharmacy-uk-scam.
- Audit findings that turned out to be non-issues: the "4 thin guides ~300 words" flag was a measurement error (real counts 835–1,119); the 4 keyword-cannibalisation groups have 2–33 GSC impressions and 0 clicks — no consolidation warranted. GSC OAuth token refreshed successfully during the session.

This is the short operational front door. `docs/project.md` is the detailed source of truth; dated audit and diversification documents are historical records and should not be used as current punch lists.

## Current verified baseline

- 186 guide source records; 185 indexable guides after one documented consolidation; all 185 carry `sources_checked` and `quick_answer`.
- 17 normalised categories.
- 228 generated HTML files; 226 indexable canonical pages; zero broken local links at the 2026-07-25 validation.
- 185 entries in `dist/search.json` and seven `/guides/` listing pages.
- AI scam checker, Google CMP, consent-aware GA4 events and Resend double opt-in are live.
- Original public research and its transparent method are live.
- Search Console and Bing AI baseline snapshots are retained under `analytics/search-ai/`.
- Commercial KPI/P&L ledgers and a non-confidential buyer data-room structure are present.
- Review-PR pipeline is unblocked and runs Tue/Fri (reduced from daily on 2026-07-23). The queue has 23 pending topics — roughly 11 weeks at one per run.

## Outstanding work — priority order

### 1. Capture monetisation and conversion evidence

- Check and record the current AdSense dashboard and Policy Centre decision. Repository status remains “unknown/in review”; do not claim approval or revenue without evidence. The 2026-07-24 audit found **no approval blockers** — verify site ownership via the ads.txt method (publisher ID already matches) and consider the spam-PBN disavow before applying.
- Mark `newsletter_signup_confirmed` as a GA4 key event and use `scam_check_success` as the primary product-use event.
- Record current Resend active subscribers, checker use, consented conversions, affiliate clicks and AdSense page views.
- Close `analytics/commercial/monthly-kpis.csv` and `monthly-pnl.csv` every month from dated exports, statements and invoices. Blank means unknown; zero requires evidence.

### 2. Establish the saleable asset perimeter

- Record the exact legal owner/data controller and suitable contact or service address.
- Create an IP ownership declaration and obtain contributor/contractor assignments where needed.
- Run trademark clearance and decide whether to file a UK mark.
- Document processor contracts and the lawful mechanism for any future newsletter/analytics data transfer.

Use `docs/buyer-data-room/` as the working index. Keep credentials, personal data, invoices, tax records and unredacted contracts in a separately controlled deal room.

### 3. Reduce key-person and transfer risk

- Create a credential inventory without copying secrets into Git.
- Confirm two independent administrators and recovery access for every material account.
- Produce a current architecture diagram and monthly operating calendar.
- Run and document a cold-backup restoration test.
- Publish the Google OAuth consent app to production to remove testing-mode token churn.

### 4. Complete the DMARC enforcement ramp

- Review accumulated `dmarc@` aggregate reports and confirm Microsoft 365 plus Resend pass alignment.
- If clean, ramp `p=quarantine; pct=25` → 50 → 100, then `p=reject; sp=reject`.
- Recheck HSTS preload inclusion. DNSSEC remains optional because Dynadot DNS does not support it without a nameserver migration.

Do not infer current DNS state from the repository; recheck live records before changing them. Exact staged records are in `docs/dns-hardening-checklist.md`.

### 5. Earn authority and continue measurable research

- Complete the Friends Against Scams organisation application.
- Follow up Tier 2 outreach and record actual outcomes.
- Start Featured.com/ResponseSource and a consistent expert-contribution cadence.
- Publish the next recurring scam-trend report from retained, dated source snapshots and compare GSC/Bing citation effects against the July baseline.

No earned editorial backlink is currently recorded in `docs/outreach-log.md`; do not infer a win from a sent pitch.

### 6. Maintain the publishing pipeline

- Review or close each `auto-content` PR within 24 hours; one open PR pauses both content crons.
- Add an evidence-led queue tranche before the remaining 26 topics are exhausted.
- Keep hand-written or substantively corrected guides behind the `docs/review/<slug>.md` → operator `-c.md` approval gate.
- Run the quarterly full-corpus factual reverification workflow and resolve its `fact-audit` PR separately from daily content.
- **Refresh `/research/uk-scam-statistics/` quarterly (next: October 2026)** — update `content/uk-scam-statistics.json` from re-verified primary sources (PSR dashboard, ONS bulletin; UK Finance each June, Fraudscape each March, GASA each November), then rebuild. Re-verify the Halifax→Lloyds transition wording and the 159 participant list at the same time.
- When a guide's content changes, regenerate or recheck its `quick_answer` rather than carrying it forward (operator rule, 2026-07-25).

## Smaller external-account checks

- Change Semrush Position Tracking from Spain/Spanish to United Kingdom/English if still wrong.
- Confirm X/Twitter API credentials exist in GitHub Secrets before relying on post-merge tweeting.
- Recheck PageSpeed after the latest site-wide build.
- Verify current affiliate-program applications; recommendations remain unpaid until documentary approval and tracking URLs exist.

## Recent completed work

- 2026-07-25: full-audit remediation shipped (`5b935f85e`) — 3 content fixes, quick answers ×185 with speakable schema, UK scam statistics research page, three guide expansions, NPA stems; all operator-approved and verified live.
- PR #61: Hinge romance guide fact-checked, reconciled, merged and verified live; content backlog guard cleared.
- Twelve held guides passed operator review and returned to index/search/sitemap discovery.
- Consent-aware checker, newsletter and recommendation events shipped.
- Confirmed newsletter signup now has a dedicated noindex, ad-free success page.
- Original Bing/Search Console research report and transparent methodology published.
- Commercial ledgers, acquisition brief and buyer data-room structure created.
- Full production validation: canonical/index controls, local links, schema and Markdown residue checks pass.

## Non-negotiable operating rules

- `dist/` is committed and is exactly what Netlify serves. Rebuild before every source/content release; never hand-edit it.
- Never run two `scripts/build.py` processes concurrently.
- Use `sections` and `faq` in `content/posts.json`; the legacy `content` field does not render.
- The builder renders only a narrow Markdown subset in guide bodies: backtick code spans and **internal root-relative** `[text](/path/)` links. External markdown links and `**bold**` render as literal characters. Check rendered output.
- New redirects and function rewrites belong in generated `dist/_redirects`, not new `netlify.toml` redirect blocks.
- Pushes to `main` deploy automatically. Netlify header changes require “Clear cache and deploy”.
- `AGENTS.md` and `CLAUDE.md` must remain byte-for-byte identical.

## Start commands

```bash
git fetch origin
git status -sb
git rev-list --left-right --count HEAD...origin/main
python3 scripts/audit_corpus.py --no-write
python3 scripts/build.py
python3 scripts/validate_dist.py
git diff --check
cmp -s AGENTS.md CLAUDE.md
```

## Reference map

- Master architecture/runbook/gotchas: `docs/project.md`
- Agent instructions: `AGENTS.md` and `CLAUDE.md` (identical)
- Daily publishing: `docs/daily-publish.md`
- DNS ramp: `docs/dns-hardening-checklist.md`
- Outreach: `docs/outreach-log.md`
- Search/AI measurement: `docs/search-ai-measurement.md`
- Commercial measurement: `analytics/commercial/README.md`
- Buyer diligence: `docs/buyer-data-room/README.md`
