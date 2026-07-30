# Start here next session

> **Last updated:** 2026-07-30
> **Repository state:** the accuracy release is **APPLIED** and `dist/` is current.

This is the short operational front door. `docs/project.md` is the detailed source of
truth; dated audit and diversification documents are historical records and should not be
used as current punch lists.

---

## Where things stand in one paragraph

The large accuracy release is **applied, built and committed** — content, the two dependent
code changes, the tests and the regenerated `dist/` landed as one commit so `main` never
held an intermediate state. Every named Report Fraud mention now carries the Scottish
route, consumer advice is nation-specific throughout, all thirteen category hubs are
sourced, and one consolidation (`hermes-parcel-scam-text-uk` → `evri-delivery-scam-guide`)
is declared on its own record.

| | |
|---|---|
| Source records / public guides | 186 / 185, one consolidation |
| Deterministic audit (guides + hubs) | **0 BLOCK / 29 FLAG** |
| Offline suites | 152 gate + 131 hub + 52 corpus + 50 Node = **385**, plus canon sync |

**Application was a one-off.** `scripts/release_manifest.py` and
`scripts/release_selftest.py` applied this release and are now **retired**: out of CI, kept
only as the audit trail. Do not reach for them for ordinary work. The safety boundary is
Git, the CI suites and the committed `dist/` snapshot, supported by the validators in
`scripts/corpus.py` and `scripts/canon.py`.

---

## CRITICAL: `dist/` is stale right now (invariant-1 breach)

Five commits changed `scripts/` and `content/` with **zero `dist/` files**. 185 committed
pages still render the old `Report Fraud (Action Fraud)` sidebar, while
`content/sources.json` now says `Report Fraud (formerly Action Fraud) — England, Wales and
Northern Ireland` and adds a `police-scotland` on-page route.

Nothing is broken live, because Netlify serves the stale committed `dist/`. But source and
served output disagree. This was a deliberate deferral — the operator instructed *"do not
build this incomplete packet"* — and the fix is the **single non-concurrent build at the
end of the release** (step 6 below). Do not do a partial build to tidy up; it ships half a
release and produces a confusing diff.

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

## Verified end-state (as committed)

| Scope | Result |
|---|---|
| 185 public guides | 0 BLOCK / 27 FLAG |
| 186 source records | 0 BLOCK / 28 FLAG |
| 13 category hubs | 0 BLOCK / 1 FLAG (disclosed `website` legislation) |
| Default `audit_corpus.py` (guides + hubs) | **0 BLOCK / 29 FLAG** |

The 29 FLAGs are review-tier: 14 legislation, 11 scale-claim, 1 source, 1 dated-event,
1 HMRC-channel, plus the hub legislation flag. They are recorded for human verification and
**still open**. **No model-backed judge has run on any of this release.**

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

## Still queued after this release

- **Nine linked-guide consistency packets** — guides whose live text should match the new
  hubs: `gumtree-scam-uk-guide`, `preloved-scam-uk`, `fake-online-pharmacy-uk-scam`,
  `iva-scam-uk`, `ponzi-scheme-uk-warning`, `google-voice-verification-scam`,
  `charity-donation-scam-checklist`, `viagogo-scam-uk`, `chargeback-scam-uk`.
- **Quarterly fact-checker**: `python3 scripts/fact_reverify.py --limit 3` smoke test, then
  a full corpus run. Spends the API key — operator's call.
- **PageSpeed / Core Web Vitals** capture (quota-limited).
- **UK scam statistics** refresh due **October 2026** (`content/uk-scam-statistics.json`).

## Operator decisions outstanding

- **Run the model-backed judge?** Nothing in this release has had one. Note the judge
  prompt itself was excusing unscoped routes until `5b9ea29fb`, so running it on a sample
  *after* the release is more informative than before.
- **Restart content generation?** Both crons have `schedule:` commented out (the key
  itself, not just the cron line), preserving `workflow_dispatch`. Paused at the operator's
  request until audits came back clean; this release is what clean looks like.
- **Re-submit to AdSense?** Deferred by the operator. Duplication blockers are resolved and
  the corpus will be gate-clean.

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

- 186 guide source records; 185 indexable guides after one documented consolidation; all
  185 carry `sources_checked` and `quick_answer`.
- 17 normalised categories. **3 hubs live; 10 more pending in `hubs-v10`.**
- AI scam checker, Google CMP, consent-aware GA4 events and Resend double opt-in are live.
- `/research/uk-scam-statistics/` is live with 28 official records.
- Review-PR pipeline runs Tue/Fri — **currently paused**, see decisions above.
