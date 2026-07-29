# Start here next session

> **Last updated:** 2026-07-29
> **Repository state:** `main` at `5b9ea29fb`; working tree clean; **`dist/` deliberately stale — see the invariant-1 warning below.**

This is the short operational front door. `docs/project.md` is the detailed source of
truth; dated audit and diversification documents are historical records and should not be
used as current punch lists. The 2026-07-25 session summary that used to head this file is
now history — the release described below supersedes it.

---

## Where things stand in one paragraph

A large accuracy release is **fully prepared but not applied**. Eight commits of gate,
build and CI hardening are on `main`. Five content packets sit in `docs/review/` awaiting
the operator's `-c.md` fact-check replies; a sixth (`FINAL-9-guides-v4`) is already
approved. Applying all six takes the corpus from **176 deterministic BLOCKs to zero**.
Nothing has been written to `content/posts.json` or `content/category-hubs.json`.

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

## The five packets awaiting operator review

All in `docs/review/`, which is **gitignored** — they exist on disk only, so they are not
in git history and will not appear on another machine.

| Packet | New prose since the last reply | Size |
|---|---|---|
| `scotland-routing-v10` | **5 fields** — Yodel description + four `/recovery/` anchors | 147 fields, 89 guides |
| `nation-consumer-routing-v3` | **2 passages** — Facebook FAQ 1 recast, Holiday Club advice/review split | 21 fields, 14 guides |
| `hubs-v10` | **none** — ten records unchanged | 10 new category hubs |
| `legacy-hubs-v5` | **none** — three records unchanged from approved v4 | `sms`, `payment`, `government` |
| `shpock-scam-uk-v10` | **none** — record approved since v5 | 1 guide |

`FINAL-9-guides-v4` (nine guides) is **APPROVED** and ready, but cannot ship alone — it
overlaps the Scotland patch map.

Each packet is a `.md` (human review) + `.json` (applyable payload) pair. Every `-c.md` in
that folder is an operator reply; check its audit-date line before treating it as current.

---

## Release procedure — one atomic session

Order matters and is **cryptographically enforced**, not merely documented.

1. **Verify the FINAL-9 receipts**: `scotland-routing-v10.json` →
   `prerequisite_state.record_digests`. Nine SHA-256 digests over canonical JSON of the
   post-FINAL-9 records. Measured: **0/9 match before FINAL-9, 9/9 after**. Then apply
   `FINAL-9-guides-v4`.
2. Apply `scotland-routing-v10` **+** `shpock-scam-uk-v10` to one proposed corpus —
   mandatory companions, neither releases alone. After all full-record replacements,
   re-assert every overlap `sources_checked_add` URL: a later full-record write must not
   drop the 11 rows across six job guides.
3. **Verify the nation receipts**: `nation-consumer-routing-v3.json` — 14 digests over
   `{quick_answer, sections, faq}` in the post-FINAL-9 + post-Scotland state. 7/14 match
   early because those guides are untouched upstream; 14/14 after. Then apply it.
4. Apply `hubs-v10` **+** `legacy-hubs-v5` — all thirteen hub records land together.
5. **In the same patch as step 4** (splitting it breaks the suite):
   - require a non-empty `sources_checked` for every hub unconditionally;
   - delete the `unsourced_legacy` warning/exemption branch in `validate_category_hubs()`;
   - flip `scripts/hub_selftest.py`'s `legacy_exempt` expectation to `rejects(unreviewed)`;
   - make the hub self-test require the **exact thirteen keys**, dropping the legacy-three
     allowance.
6. Run both self-tests **from a clean checkout**
   (`rm -rf /tmp/cc && mkdir /tmp/cc && git archive HEAD | tar -x -C /tmp/cc`), require
   zero corpus BLOCKs, then **one non-concurrent build**.
7. Re-run the render greps on `dist/` (`**`, `](`, `…`), then commit source, code, tests
   and regenerated `dist/` **together**.

Application contracts require setting `updated` to the **actual application date**, not
the `2026-07-27` placeholder carried in the payloads.

---

## Verified end-state (measured 2026-07-29, published order)

- **0 BLOCK** across 186 source records / 185 indexable guides
- 28 review-tier FLAGs: 14 legislation, 11 scale-claim, 1 source, 1 dated-event, 1 hmrc-channel
- Zero precondition failures; no overlap source rows lost
- Every quick answer ≤60 words; zero bare `/recovery/` paths corpus-wide
- 13 hubs at zero BLOCK, with one disclosed `website` legislation FLAG
- Clean checkout: **103 gate checks + 66 hub checks**, zero failures

"Zero BLOCK" means the deterministic gate is satisfied. The 28 FLAGs remain open editorial
items and **no model-based LLM judge has run on any of this release**.

---

## The eight commits

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

---

## Canon changes worth knowing

`content/sources.json` now has **17 routes** and is the single source of truth for every
prompt, the on-page sidebar and the gate allowlist:

- `police-scotland` is an **on-page** route (`101`, scotland.police.uk)
- Report Fraud label scoped: *England, Wales and Northern Ireland*
- Victim Support relabelled *Victim Support England and Wales Supportline* — its
  `0808 168 9111` line covers England and Wales only
- `advice.scot`, not `advicedirect.scot`

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
