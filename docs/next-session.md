# Start here next session

> **Last updated:** 2026-07-30
> **Repository state:** `main` at the canon-hardening commit; working tree clean;
> **`dist/` deliberately stale — see the invariant-1 warning below.**

This is the short operational front door. `docs/project.md` is the detailed source of
truth; dated audit and diversification documents are historical records and should not be
used as current punch lists. The 2026-07-25 session summary that used to head this file is
now history — the release described below supersedes it.

---

## Where things stand in one paragraph

A large accuracy release is **fully prepared but not applied**. Nine commits of gate,
build and CI hardening are on `main` — the ninth closed every integration blocker the
operator raised in the five `-c.md` replies dated 2026-07-29. **Six** packets now sit in `docs/review/`
awaiting the operator's replies — `scotland-routing-v14`, `shpock-scam-uk-v14`,
`nation-consumer-routing-v8`, `hubs-v14`, `legacy-hubs-v9` and
`consolidation-metadata-v4`; `FINAL-9-guides-v4` remains approved. Applying all seven
takes the corpus to **zero deterministic BLOCKs at BOTH scopes** — 185 public guides and
186 source records — from 176 today. Nothing has been written to
`content/posts.json` or `content/category-hubs.json`.

**Application is now a tool, not a procedure.** `scripts/release_manifest.py` applies
every packet in order and refuses each stage unless the live corpus digest equals that
stage's recorded `expects`. Read its module docstring before doing anything by hand.

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

| Packet | Reader content | What changed since the reply |
|---|---|---|
| `scotland-routing-v14` | unchanged (147 fields, 202 source rows) | receipt key list made explicit incl. lookup-only `slug`; gate scopes separated |
| `shpock-scam-uk-v14` | unchanged | cross-method digest "match" retracted; stable vs applied receipts split; stale HTTP block removed |
| `nation-consumer-routing-v8` | **3 passages changed** | Timeshare FAQ 3 reworded; 2 Victim Support evidence rows added; Pandora/Ray-Ban referral sentences rewritten so the numbers stay and the citation is fixed |
| `consolidation-metadata-v4` | one metadata field | `consolidated_into` on the Hermes record — consolidation now defines the public corpus |
| `hubs-v14` | unchanged (10 records) | all ten integration amendments now landed in code, with per-item evidence |
| `legacy-hubs-v9` | **1 passage changed** | duplicate Evri/Hermes courier anchor merged into `Evri (formerly Hermes)` |

`FINAL-9-guides-v4` (nine guides) is **APPROVED** and ready, but cannot ship alone — it
overlaps the Scotland patch map.

Each packet is a `.md` (human review) + `.json` (applyable payload) pair. Every `-c.md` in
that folder is an operator reply; check its audit-date line before treating it as current.
`release-manifest.json` is generated, not reviewed.

### Resolved since the 2026-07-29 replies

- **Advice Direct Scotland.** Not a conflict: `0808 800 9060` is advice.scot, `0808 164 6000`
  is the separate Scottish-Government-funded consumeradvice.scot service run by the same
  charity (gov.scot confirms). Both in the canon; only the `on_page` one reaches prose.
  `nation-consumer-routing-v5` restores the numbers in the two referral sentences and fixes
  the citation instead of dropping them.
- **The 2 Evri/Hermes similarity BLOCKs.** Gone. Consolidation is now declared on the record
  and defines the public corpus, so an archive record that never renders is outside the
  duplicate-page question by construction. `--include-consolidated` still surfaces the 54%
  pair on request.

## Release procedure — one atomic session

Order is **cryptographically enforced** by `scripts/release_manifest.py`, whose receipt is
a SHA-256 digest over the **whole corpus** after each stage. A per-packet digest over the
fields a packet touches cannot prove what happened to records it does not name — that was
the defect in every v10 packet, and `nation-consumer-routing-v3`'s 14 hashes passed
identically in five different corpus states.

```bash
python3 scripts/release_manifest.py --verify              # where is the tree?
python3 scripts/release_manifest.py --apply --date $(date +%F)
```

Stages, in order, with the corpus digest each expects and produces:

| Stage | Packets | Expects | Produces |
|---|---|---|---|
| `final9` | `FINAL-9-guides-v4` | `496b0d63…` | `4b3090bd…` |
| `scotland-shpock` | `scotland-routing-v14` + `shpock-scam-uk-v14` | `4b3090bd…` | `f76b69aa…` |
| `nation` | `nation-consumer-routing-v8` | `f76b69aa…` | `e9a7c221…` |
| `hubs` | `hubs-v14` + `legacy-hubs-v9` | `e9a7c221…` | `e9a7c221…` (hubs only) |
| `consolidation` | `consolidation-metadata-v4` | `e9a7c221…` | `26d57904…` |

The applier asserts every `old` value before writing, checks each `sections`/`faq` index
against its recorded heading, re-asserts overlap source rows after all full-record writes
(11 rows across six job guides would otherwise be lost), and refuses to overwrite a hub
that has acquired `sources_checked` since the patch was written.

The hub and consolidation code changes are **carried by their packets** as `code_patch`
entries, so they are applied and receipted by the tool rather than done by hand.



Then, from a clean checkout
(`rm -rf /tmp/cc && mkdir /tmp/cc && git archive HEAD | tar -x -C /tmp/cc`):

```bash
python3 scripts/gate_quickanswer_selftest.py
python3 scripts/hub_selftest.py
python3 scripts/corpus_selftest.py          # includes a real build into a TEMP dir (~6 min)
python3 scripts/release_selftest.py         # PRE-APPLICATION: run this BEFORE --apply
python3 scripts/sync_canon_js.py --check
node --test "netlify/functions/lib/*.test.js"
```

**Run `release_selftest.py` BEFORE applying** — it emits and applies from the baseline, so
it is a pre-application proof, not a fifth post-application suite. The four suites above plus
canon sync are the post-application check.

**Two stages carry a `code_patch`.** `hubs-v14` deletes the `unsourced_legacy` exemption and
requires the exact thirteen keys; `consolidation-metadata-v4` removes the static Hermes
redirect and empties `PENDING_MIGRATION`. The applier executes them with the content in **one transaction**: every byte staged,
originals journalled to disk, all files replaced, full rollback on any handled failure, and
`--recover` for an interrupted run. It imports the *staged* `corpus.py` to derive the real
post-patch maps rather than trusting the packet's declaration.

`release_manifest.py --apply` now **requires** the manifest and compares the
`{posts, hubs}` pair before *and* after every stage, verifies packet identity and a
`code_baseline` digest over the release-critical scripts, and rejects an unknown
`--stage`. Comparing only the posts digest let an after-nation tree report as "after
hubs" and the consolidation stage apply with all ten hub records absent.

Then **one non-concurrent build**, the render greps on `dist/` (`**`, `](`, `…`), and one
commit carrying source, code, tests and regenerated `dist/` together.

## Verified end-state (measured 2026-07-30 by dry-running the full order)

Reported **by scope**, because the two corpora give different answers and combining them
was a finding in three separate replies:

| Scope | BLOCK | FLAG |
|---|---|---|
| 185 public guides | **0** | 27 — 14 legislation, 10 scale-claim, 1 source, 1 dated-event, 1 hmrc-channel |
| 186 source records | **0** | 28 — as above, plus 1 scale-claim |
| 186, `--include-consolidated` | 2 — the Evri ↔ Hermes pair, on request | 28 |

The two scopes now agree. The Evri/Hermes similarity is still measurable — it is a real 54%
overlap between a live guide and its own archive copy — but an archive record that never
renders is not a duplicate *page*, so it no longer BLOCKs publication.

- Zero precondition failures; 202/202 Scotland source rows appended, 0 lost
- Quick answers 185/185, all 45–60 words; `sources_checked` 185/185
- 13 hubs at zero BLOCK, with one disclosed `website` legislation FLAG; all 13 sourced
- Internal guide links: 0 unresolved. Raw `**` / external markdown links / description
  ellipses: 0 / 0 / 0
- Clean checkout: **152 gate + 101 hub + 53 corpus + 24 release + 50 node = 380 checks**, zero failures,
  with `docs/review/` genuinely absent. The fast path (`corpus_selftest.py --no-build`)
  plus canon sync. `release_selftest.py` runs 24 synthetic-fixture checks there and 26
  with the local packets. On the fully APPLIED state the four suites are **384**.

"Zero BLOCK" means the deterministic gate is satisfied. The 28 FLAGs remain open editorial
items and **no model-based LLM judge has run on any of this release**.

---

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
