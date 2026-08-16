# Start here next session

> **Last updated:** 2026-08-15
> **Repository state:** the accuracy release, its two follow-on growth-audit content phases, PR #106 and a six-commit homepage design cycle are **APPLIED and LIVE**; `dist/` is current and byte-identical to a fresh build of `main`.

This is the short operational front door. `docs/project.md` is the detailed source of
truth; dated audit and diversification documents are historical records and should not be
used as current punch lists.

---

## Where things stand in one paragraph

The large accuracy release is **applied, built and committed** — content, the two dependent
code changes, the tests and the regenerated `dist/` landed as one commit so `main` never
held an intermediate state. Every named Report Fraud mention now carries the Scottish
route, consumer advice is nation-specific throughout, all seventeen category hubs are
sourced, and two consolidations are declared on their own records. The 11 August follow-on
work strengthened the priority-guide link graph and aligned five guides with their verified
category hubs; both changes were independently fact-checked before application. The homepage
now begins with a two-route safety triage (check a suspicious message or begin recovery), then
progresses through contact method, safe checks and recent examples. Its durable product and
design references are `PRODUCT.md` and `DESIGN.md` at the repository root.

| | |
|---|---|
| Source records / public guides | 188 / 186, two consolidations |
| Deterministic audit (guides + hubs) | **0 BLOCK / 30 FLAG** (triaged 2026-08-15, below) |
| Offline suites | 152 gate + 131 hub + 52 corpus + 50 Node = **385**, plus canon sync |

**Application was a one-off.** `scripts/release_manifest.py` and
`scripts/release_selftest.py` applied this release and are now **retired**: out of CI, kept
only as the audit trail. Do not reach for them for ordinary work. The safety boundary is
Git, the CI suites and the committed `dist/` snapshot, supported by the validators in
`scripts/corpus.py` and `scripts/canon.py`.

---


## The review trail

Every content change went through `docs/review/<name>.md` and waited for the operator's
`<name>-c.md` fact-check reply. That folder is **gitignored** — the packets and replies
exist on the machine that produced them and are not in git history. Sixty-five replies
across the cycle; reader content was approved in the final six consecutive rounds while
release-control defects were worked out.

**Lesson worth keeping: packets are reissued, never amended in place.** Editing a reviewed
packet changes its identity, so the digest its reply cites stops being reproducible. That
happened once and cost a full reissue to repair.

**Second lesson: the applier became the risk.** 2,800 lines of bespoke transaction
machinery accumulated to apply 168 field edits. It was retired in favour of ordinary Git
diffs validated as one combined state — which is what actually shipped.

## Verified accuracy-release end-state (2026-07-30, historical baseline)

| Scope | Result |
|---|---|
| 185 public guides | 0 BLOCK / 27 FLAG |
| 186 source records | 0 BLOCK / 28 FLAG |
| 13 category hubs | 0 BLOCK / 1 FLAG (disclosed `website` legislation) |
| Default `audit_corpus.py` (guides + hubs) | **0 BLOCK / 29 FLAG** |

The FLAGs are review-tier and **still open**. **No model-backed judge has run on any of this
release.** They were triaged on 2026-08-15 — the current 30 are not 30 problems:

| Group | Count | What it actually needs |
|---|---|---|
| `scale_claim` | 11 | **One house-style decision, not eleven.** All sit in the `hero` field and all have the same shape — "can cost you thousands", "steal thousands from". These are loss-magnitude claims, not victim counts, and the site's own dataset supports them (£1.3bn across 4.06m cases, UK Finance 2026). Accept as hedged framing, or require a cited figure. |
| `legislation` | 15 | **Mechanical checks against a pinned canon.** 11 are "the Consumer Credit Act 1974" — Section 75, whose bounds are already pinned (cash price over £100, not more than £30,000). 2 are "the Online Safety Act 2023" (correct: Royal Assent 26 Oct 2023). 1 "the Consumer Rights Act" (2015, unqualified but not wrong). 1 is the `website` hub. Read each clause against the rule. |
| `report_mailbox` / `source` | 3 | **Genuine external verification.** `spoof@ebay.co.uk` ×2 and `companies.house@notifications.service.gov.uk`. All three are already hedged in prose — the Companies House one exemplary, scoping itself to one dated notice and explicitly denying it is universal or authentication. Confirm the addresses are current. |
| `ncsc_route_scope` | 1 | **The one that looks like a real defect.** `invoice-redirection-scam-checklist` attributes `gov.uk/report-cyber` to the NCSC. That URL is not in `content/sources.json`, which carries NCSC phishing-report and website-report only; `gov.uk/report-cyber` is historically the Report Fraud cyber route. Entity misattribution is BLOCK-tier — check this first. |
| phantom | 1 | `hermes-parcel-scam-text-uk` carries a `scale_claim` flag but declares `consolidated_into: evri-delivery-scam-guide`, so it renders no page. Not reader-facing. |

Re-run the triage with `python3 scripts/audit_corpus.py --no-write` — **always `--no-write`**,
or it rewrites every manifest and churns ~107 of them with the post's date rather than the
audit date.

The retired `hermes-parcel-scam-text-uk` slug is absent from every published and indexable
surface — no page, and nothing in `sitemap.xml`, `rss.xml`, `search.json`, `llms.txt` or
`llms-full.txt`; both URL forms 301 straight to Evri. It is deliberately still present in
raw source (`content/posts.json` keeps the archive record), in `dist/_redirects` as the
rule itself, in the July GSC research dataset as a historical measurement, and in the
regression tests that assert all of the above.

## The nine commits

| Commit | Substance |
|---|---|
| `29598fdf5` | Every named Report Fraud mention must carry a Scottish route; gate covers hub prose |
| `3a6d1f3a6` | Scotland route needs a positive verb; new `check_nation_consumer_routing` (BLOCK) |
| `25852a6c2` | Clause-aware routing; `_sentences()` normalises HTML; CRA canon → four agencies; hub validation fails closed |
| `f936578f5` | Canon guards scoped **per mention** (both had field-wide suppression); `scripts/hub_selftest.py` created; CI wired |
| `db0330aaa` | CRA qualification local to the matched clause; route-shaped `from`; canon/fallback sync; clean-CI hub test |
| `844c03c63` | `_load_canon()` and `load_sources()` fail closed; symmetric drift check; hub test independent of gitignored files |
| `98fc25901` | `police-scotland` as an on-page canon route; canon **structural** validation; 8 visible surfaces scoped; `check-scam.js` inserts Police Scotland deterministically |
| `5b9ea29fb` | One `render_canon_routes()` shared by `ACCURACY_BLOCK` and `JUDGE_SYSTEM`; no hand-typed numbers left in either |
| **canon-hardening** | **`scripts/canon.py` — one validator for gate AND build, by route identity, 17 negative fixtures against both consumers; both hand-maintained fallbacks deleted; generator + checker routes derived from canon via a generated JS bridge; checker route pair hoisted and unit-tested at every position; standalone surfaces rendered from one component (which surfaced 3 more unpaired mentions); hub `<title>` = H1 = schema name; 24-hour recall claim removed; Advice Direct Scotland conflict resolved in canon** |

---

## Canon changes worth knowing

`content/sources.json` now has **18 routes**, carries `nation`/`role`/`brand` identity
fields on the six required ones, and is loaded through **`scripts/canon.py`** — the single
validator and renderer shared by the gate, the build, the generator and (via a generated
JS bridge) the Netlify Functions:

- `police-scotland` is an **on-page** route (`101`, scotland.police.uk)
- Report Fraud label scoped: *England, Wales and Northern Ireland*
- Victim Support relabelled *Victim Support England and Wales Supportline* — its
  `0808 168 9111` line covers England and Wales only
- `advice.scot`, not `advicedirect.scot`
- **Two** Advice Direct Scotland entries: `advice-direct-scotland` (`0808 800 9060`,
  advice.scot, **on-page** — the one prose names) and
  `advice-direct-scotland-consumeradvice` (`0808 164 6000`, consumeradvice.scot, not
  on-page — recorded so the gate does not treat it as invented). GOV.UK prints a different
  one on each of two pages; gov.scot confirms they are two services from one charity.
- There is **no fallback route set** anywhere. An absent or invalid canon stops the build
  and the gate.

`render_canon_routes()` in `content_gate.py` is the **only** place reporting routes are
formatted for prompts. A canon edit changes the rendering and fails tests until every
consumer is updated — pinned by four assertions including a mutation test.

---

## Canon rules that trip models up (all gate-enforced)

- **Report Fraud** covers England, Wales and NI. Scotland → **Police Scotland on 101**.
  Every named mention needs the Scottish route within a two-sentence window.
- **Consumer advice is nation-specific**: Citizens Advice (England and Wales,
  0808 223 1133), Advice Direct Scotland (0808 800 9060), Consumerline NI (0300 123 6262).
  Never "UK-wide". Citing Citizens Advice *research* is not a route.
- **Credit reference agencies**: Experian, Equifax, TransUnion are the three **main**
  agencies; MoneyHelper also lists **Crediva**. Never "the three CRAs" / "all three" /
  "the other two" as exhaustive. ClearScore is an app; CallCredit is the obsolete
  TransUnion name.
- **Victim Support** `0808 168 9111` = England and Wales only.
- **National Debtline** phone/webchat = England and Wales. Use StepChange or MoneyHelper's
  debt advice locator for a UK-safe route.
- **Help to Claim** is delivered by Citizens Advice (England and Wales) and Citizens Advice
  Scotland; NI administers Universal Credit separately via nidirect. It is **not** the
  consumer helpline — do not substitute Consumerline there.
- **Trading Standards referral is conditional** — "may refer or share relevant complaint
  information", never "passes reports to".
- Section 75: cash price **more than** £100 and no more than £30,000.
- APP reimbursement: eligible Faster Payments/CHAPS from 7 Oct 2024, £85,000 cap,
  up-to-£100 excess (not for vulnerable consumers), 13-month limit.

---

## Operator workflow (non-negotiable)

Every content change goes into `docs/review/<name>.md` as a **self-contained** packet and
waits for the operator's `<name>-c.md` fact-check reply before being applied. Never commit
content on the strength of your own verification. Packets must embed the full prose — a
pointer to a scratch file is not self-contained.

Lessons that cost real rework this cycle:

- **Read every changed field end to end.** Property checks (gate clean, valid HTML, no
  markdown residue) passed semantically broken text at least four times — dangling
  fragments, a lowercase sentence start after a full stop, a duplicated clause.
- **Never claim a test result you have not reproduced from a clean checkout.** A 66/66 hub
  result was working-copy-only; a clean `git archive` gave 56 PASS / 10 FAIL because the
  test read gitignored `docs/review/`. CI was red while that number was cited as evidence.
- **Check the link the text already carries before "fixing" an attribution.** An NCSC
  citation looked unsupported against the wrong NCSC page; the sentence already linked the
  right one and was accurate.
- **A filename in an array is not enforcement.** Order claims need digests.
- New guard regexes produce false positives at corpus scale — "the three-dot menu",
  phrasal-verb "on", lowercase "report fraud", `from` in a citation. Always run a new guard
  over the whole corpus and read the hits before trusting it.

---

## Current growth and operations queue

- **Indexing monitoring:** Search Console validation is already running for the eight legacy
  redirect-error URLs. Do not submit a second validation. Re-verified 2026-08-15: seven
  representative legacy URLs (gumtree, romance slow-burn, romance-scams and ticket-scams
  categories, concert-ticket-2, hmrc-tax-refund-checklist, refund-scam) each resolve in a
  **single 301 hop to a 200**, no chains and no loops — the condition the validation tests
  still holds. **The validation state itself is UI-only:** the Search Console API exposes
  Search Analytics, URL Inspection, Sitemaps and Sites, and none of them return the
  "Validation started / passed / failed" state, so that has to be read in the Search Console
  interface. `scripts/gsc_report.py` is analytics-only and its OAuth token refreshed cleanly
  on 2026-08-15. Continue to monitor the 21 `Crawled - currently not indexed` and 49 `Discovered -
  currently not indexed` URLs as a group, not by repeatedly requesting indexing.
- **Category hubs:** there are no missing hub records: `content/category-hubs.json` contains
  all 17 normalised categories. The next hub work is a quality/traffic review using current
  Search Console and Bing data, not bulk creation of more hubs.
- **Authority and KPI evidence:** refresh the Search Console Links and Bing inbound-link
  exports; add dated GA4, AdSense, Resend and affiliate snapshots to the buyer data room;
  then run a small, relevant outreach batch against the UK scam-statistics resource. The
  10 August Ahrefs Basic screenshot is a baseline only: Health Score 100, DR 2, 222
  referring domains, about 2K visitors and no measured organic traffic/keywords.
- **First Search Console opportunity:** monitor `/guides/bank-text-codes-not-arriving/`.
  In the current three-month view, `halifax text messages not arriving` has 1,237 impressions
  at average position 3.3 but zero clicks. A live SERP check found Halifax's own help and
  status pages plus People-also-ask/AI surfaces ahead of general guidance, while the Beat The
  Scam title already matches the query. Do not rewrite the page or create a competing guide
  without a material new user need; compare again after a clean 28-day window.
- **Quarterly fact-checker:** run `python3 scripts/fact_reverify.py --limit 3` smoke test,
  then a full corpus run. This spends API credit and needs the operator's approval.
- **UK scam statistics:** refresh is due **October 2026** (`content/uk-scam-statistics.json`).

## Operator decisions outstanding

- **Run the model-backed judge?** Nothing in this release has had one. Note the judge
  prompt itself was excusing unscoped routes until `5b9ea29fb`, so running it on a sample
  *after* the release is more informative than before.
- ~~**Restart content generation?**~~ **RESOLVED — the crons are running.** This entry said
  both had `schedule:` commented out; that is no longer true and had gone stale by at least
  two days. Verified 2026-08-15: both `daily-publish.yml` and `daily-search-console.yml`
  carry an active `schedule:`, and the search-console cron generated PR #106 on 2026-08-14,
  merged 2026-08-15. **Do not "restart" them.** The live obligation is the backlog guard:
  both crons skip generation while any `auto-content` PR is open, so a review PR left open
  stalls the pipeline and the queue re-picks the same topics. Next run Tue 2026-08-18.
- **Re-submit to AdSense?** Do not resubmit. On 11 August the AdSense site review was already
  active ("Getting ready"), with payment profile, ads settings, ads.txt and certified CMP
  confirmed and no current Policy Centre restriction. Wait for Google's decision.

---

## Practical gotchas

- `docs/review/` is **gitignored** — packets and replies are local-only.
- Never run two builds concurrently; `rmtree(dist/)` races corrupt output.
- After a local build, `git checkout -- dist/assets/og/` restores the OG images — local
  renders differ byte-wise from CI's and produce ~185 spurious modified files.
- `AGENTS.md` and `CLAUDE.md` are byte-identical twins; change both and verify with
  `cmp -s AGENTS.md CLAUDE.md`.
- The permission classifier (`claude-sonnet-5[1m]`) was intermittently unavailable on
  2026-07-29, blocking Bash in **auto** mode. **Manual mode bypasses it and worked
  reliably**; Read/Edit/Write are unaffected either way.

---

## Current verified baseline (unchanged from 2026-07-25 unless noted)

- 188 guide source records; 186 indexable guides after two documented consolidations; all
  carry `sources_checked` and `quick_answer`.
- 17 normalised categories and **17 authored, sourced hub records**. This means the category
  layer exists everywhere; it does not mean every hub has equal search demand or outreach value.
- AI scam checker, Google CMP, consent-aware GA4 events and Resend double opt-in are live.
- `/research/uk-scam-statistics/` is live with 28 official records.
- Review-PR pipeline runs Tue/Fri and is **live**, not paused. Next run Tue 2026-08-18.

## Homepage design cycle (2026-08-15)

Six commits, all live, driven by three `/impeccable critique` runs that scored the homepage
26 → 28 → 31 out of 40. Fourteen of the fifteen priority issues they raised are shipped.

| Commit | Substance |
|---|---|
| `1b7d7501b` | Consent bar no longer covers the end of the page; dead `#cookieStatus` removed |
| `8a1657e61` | Protective Red off taxonomy onto the pale-blue chip; white focus ring on dark surfaces; first `forced-colors` block; checker CTA lifted out of the collapsing nav; two-column card stage 760–1100px |
| `c630e0348` | Consent bar stops seizing focus on the unrequested timer (WCAG 3.2.5); `--line-control` pair for form-control boundaries |
| `3e14df67e` | Checker verdict strip on the homepage — the first appearance of red/amber/green on a page that had 401 blue instances and none of them; category-diverse featured guides; mobile menu focus order |
| `b17f14ce6` | `<ol>`/`<ul>` semantics on the checklist and channel nav; human-readable dates in `<time>`; 24×24 consent target; callout switches to the pale wash below 1100px |
| `4f4c12c71` | Consent bar reads as a layer rather than more hero (was 1.00:1 against it); 150px → 131px on short phones; `.impeccable/` gitignored |

**Still open from that cycle:** the "Verify independently" hero callout has no destination.
There is nothing honest to link to — `content/sources.json` carries reporting and
consumer-advice routes only, and the corpus has no general verification guide. A packet is
drafted at `docs/review/verify-organisation-genuine-uk.md` awaiting a `-c.md` reply. Note
the packet's own last question: there is a real argument the callout should stay link-free,
since its instruction is to stop following links other people supply.

`DESIGN.md`'s layout section was corrected in `b17f14ce6` — it had claimed the nav folds at
760px when it folds at 1100px, and the CSS is right (the full link set plus the checker
action needs ~1089px against the 992px available at 1024).
