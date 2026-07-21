# Start here next session

> **Last updated:** 2026-07-21
> **Repository state:** `main` at `d1ccf8e72` (PR #62 daily publish merged, auto-tweet recorded); production verified; no open `auto-content` PR at close.

This is the short operational front door. `docs/project.md` is the detailed source of truth; dated audit and diversification documents are historical records and should not be used as current punch lists.

## Current verified baseline

- 184 guide source records; 183 indexable guides after one documented consolidation.
- 17 normalised categories.
- 225 generated HTML files; 223 indexable canonical pages; 649 JSON-LD blocks; zero broken local links at the 2026-07-21 validation.
- 183 entries in `dist/search.json` and seven `/guides/` listing pages.
- AI scam checker, Google CMP, consent-aware GA4 events and Resend double opt-in are live.
- Original public research and its transparent method are live.
- Search Console and Bing AI baseline snapshots are retained under `analytics/search-ai/`.
- Commercial KPI/P&L ledgers and a non-confidential buyer data-room structure are present.
- Daily review-PR pipeline is unblocked. The queue has 26 pending topics, approximately 26 publishing days at one per day.

## Outstanding work — priority order

### 1. Capture monetisation and conversion evidence

- Check and record the current AdSense dashboard and Policy Centre decision. Repository status remains “unknown/in review”; do not claim approval or revenue without evidence.
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

## Smaller external-account checks

- Change Semrush Position Tracking from Spain/Spanish to United Kingdom/English if still wrong.
- Confirm X/Twitter API credentials exist in GitHub Secrets before relying on post-merge tweeting.
- Recheck PageSpeed after the latest site-wide build.
- Verify current affiliate-program applications; recommendations remain unpaid until documentary approval and tracking URLs exist.

## Recent completed work

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
- The builder does not support Markdown links or `**bold**` in guide bodies. Check rendered output.
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
