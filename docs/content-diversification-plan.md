# Content Diversification Plan

**Created:** 2026-06-26
**Trigger:** 4th external audit flagged 178/190 guides sharing one six-section outline (AdSense scaled-content risk).
**Inputs:** live 90-day Search Console pull (`scripts/gsc_report.py`, token refreshed 2026-06-26) + corpus structure analysis + the ~12 already-diversified in-corpus exemplars.

> **Status:** IN PROGRESS. This doc is the work-list.
>
> **Decisions locked 2026-06-26:** (1) **Full diversification, in impression order** — apply the complete §4 recipe to each page top-down by impressions (not a title-only CTR sprint). (2) **Specimens are illustrative-only** — clearly-labelled paraphrased examples from known scam patterns; no live links, no invented numbers/sender IDs. (3) First page built as the reference template, then sign-off, then rollout.

---

## 1. Diagnosis (what the data actually says)

90-day totals: **9,731 impressions / 49 clicks / 0.50% CTR / avg pos 15.5**.

The audit framed this as a *structure* problem ("178 pages share the same outline"). The traffic data shows that's only half of it — there are **two distinct failure modes** with different fixes:

| Mode | Symptom in GSC | Fix | Speed of payoff |
|---|---|---|---|
| **A — CTR leak** | Ranks page 1 (pos <15), high impressions, ~0 clicks | Title + meta + first-FAQ rewrite to match query intent | **Fast** (days–weeks) |
| **B — Rank stall** | Lots of impressions but pos 20–70 | Depth/diversification + internal links to climb | Slow (weeks–months) |

The AdSense "scaled content" risk overlaps with Mode B: de-templating a page also makes it rank-worthy. So a single edit pass per page can serve both goals.

**Traffic is concentrated in one vertical** — ~80% of impressions are **UK SMS/text scams**: courier (DPD, Yodel, Evri, Hermes, UPS, Royal Mail) + bank text (Halifax, Lloyds, NatWest, Barclays, Santander) + government (NHS, DVLA, HMRC, council tax, Universal Credit). This is where every hour of editing should go first. (Confirms the standing "proven vertical = UK SMS scams" read.)

**Internal benchmark:** `nhs-appointment-scam-text-uk` already converts at **1.9% CTR** (12 clicks / 626 impr, pos 7.3) — ~6× the site average. Its title matches intent precisely ("NHS Appointment Scam Text Messages: UK Warning Signs & How to Report"). That's the bar for the others.

**The single biggest opportunity *and* the single biggest trap in the dataset:** the query *"halifax text messages not arriving"* — **1,744 impressions, position 4.1, ZERO clicks** — lands on `bank-text-codes-not-arriving`. Tempting to rename the page around "Halifax", **but prior test-learning says don't:** it ranks #3 for its money term (title changes risk the rank) and the intent is partly bank-support — Halifax's *own* support pages legitimately win that click, so the CTR ceiling is genuinely uncertain. Treat it as a meta-description + Halifax-named-FAQ experiment with a capped, unproven upside — not a sure double in clicks.

---

## 2. The two clearest "scaled content" tells (concrete, fixable)

1. **Identical six-section outline on 178/190 guides:**
   `What is this scam? → Warning signs → How it works step by step → How to verify → What to do if you've interacted → Reporting in the UK`
2. **Near-identical first FAQ** across the top pages — *"Is [Brand] a legitimate bank/organisation, or is it all a scam?"* (Halifax, Lloyds, NHS, DVLA, NatWest, Barclays, Santander, HMRC, Evri…). One is even broken: Barclays reads *"is this scam always a scam?"*. **Nobody searches this** — it wastes the highest-value on-page slot (first FAQ → People-Also-Ask/rich-result candidate) AND is an obvious template fingerprint.

Fixing #2 across the top 30 is a fast, high-value de-templating win on its own.

---

## 3. Prioritised work-list (top ~30 by impressions)

`✅` = section structure already diversified (only needs title/meta/FAQ + internal links, NOT re-sectioning). `—` = still on the generic outline.

### Tier 1 — page-1 rankers leaking clicks (Mode A — do first, fastest ROI)
| Slug | Impr | Pos | Clk | Div? | Primary fix |
|---|---|---|---|---|---|
| `bank-text-codes-not-arriving` | 1624 | 3.3 | 4 | ✅ | **Meta + FAQ only — do NOT touch the title** (ranks #3 for its money term; prior test-learning warns a title change risks the rank). Add a Halifax-named FAQ/section to match the query. ⚠️ CTR ceiling is uncertain: "not arriving" is partly bank-support intent that Halifax's own pages win — treat as a capped CTR test, not a guaranteed win. |
| `dpd-delivery-scam-text` | 1927 | 10.7 | 5 | ✅ | Title/meta CTR tune; FAQ from real DPD queries ("fake dpd text", "redelivery fee") |
| `halifax-bank-scam-text-uk` | 789 | 12.2 | 5 | — | Kill "is Halifax legitimate" FAQ; trim 290-char meta; bespoke sections |
| `lloyds-bank-scam-text` | 708 | 8.7 | 3 | — | Same recipe; pos 8.7 = strong CTR upside |
| `nhs-appointment-scam-text-uk` | 626 | 7.3 | 12 | — | **Protect the title** (it's the CTR champ); diversify body + FAQ for AdSense only |
| `dvla-vehicle-tax-text-scam` | 204 | 9.7 | 0 | — | Pos 9.7 + 0 clicks = pure title/meta/FAQ problem |
| `natwest-fraud-text-message-scam-uk` | 161 | 13.1 | 2 | — | Full recipe |
| `barclays-bank-text-scam-uk` | 137 | 10.4 | 2 | — | Full recipe; fix broken FAQ wording |
| `evri-delivery-scam-guide` | 96 | 14.4 | 0 | — | Full recipe |

### Tier 2 — high impressions, ranking page 3–7 (Mode B — diversify + internal links)
| Slug | Impr | Pos | Div? | Note |
|---|---|---|---|---|
| `santander-email-scam-uk` | 132 | 13.5 | — | Border Tier1/2 |
| `hermes-parcel-scam-text-uk` | 118 | 20.7 | — | Consolidate courier cluster via internal links |
| `amazon-order-scam-email-checklist` | ~170 | 21.8 | — | Also absorbs `amazon-scam-email-uk` (301'd in) |
| `royal-mail-text-scam-uk` | ~105 | 47.7 | — | Absorbs `royal-mail-text-scam-guide` (301'd in) |
| `hmrc-tax-refund-text-scam-uk` | 104 | 25.5 | — | High-intent gov query cluster |
| `bt-broadband-scam-calls-uk` | 96 | 31.1 | — | Internal-link to the diversified `isp-impersonation-...` hub |
| `indeed-job-scam-uk` | 90 | 21.6 | — | Employment cluster |
| `amazon-phone-call-scam-uk` | 125 | 54.6 | ✅ | Structure done — needs internal links to climb, not re-section |

### Tier 3 — mid-impression generic pages (de-template for AdSense breadth)
`council-tax-scam-text-uk` · `tinder-scam-uk` · `ebay-scam-buyer-protection-uk` · `tiktok-shop-scam-uk` · `bumble-romance-scam-uk` · `bank-transfer-scam-uk` · `wish-scam-uk-review` · `dvla-scam-email-awareness` · `hmrc-tax-rebate-email-scam` · `recruitment-agency-scam-uk` · `data-entry-job-scam-uk` · `universal-credit-scam-uk` · `whatsapp-scam-family-message-uk` · `military-romance-scam-uk`

That's ~31 pages = the "top 20–50 by traffic" the audit recommended, ordered by real impressions.

---

## 4. Per-page recipe (one pass per page → one rebuild → one PR)

Model on the existing bespoke exemplars (`amazon-phone-call-scam-uk`, `gumtree-scam-uk-guide`, `chargeback-scam-uk`).

1. **Title** → match the page's dominant GSC query intent. **Budget: ~58 chars** for guides — as of 2026-06-26 `seo_title()` drops the " | Beat the Scam" suffix on guide `<title>`s (it's kept on home/category), so guides get the near-full 60-char cap. Keep titles ≤~58 so they don't truncate. *Before:* "Halifax Bank Scam Text Messages UK: How to Spot & Avoid Them" (truncated to "…How to Spot") → *After:* "Halifax Scam Texts: How to Spot a Fake Halifax SMS (UK)" (55, fits).
2. **Meta description** → ≤155 chars, **answer-led** not threat-led. (Several top pages run 250–290 chars and truncate.)
3. **First FAQ + 1–2 more** → seeded from that page's **actual GSC queries** (kill every "Is [brand] legitimate?").
4. **Bespoke section headings** → name the specific entity/scam (replace the generic six).
5. **One concrete specimen** → a paraphrased, clearly-illustrative example of the real text/email. *(The model has no internet — specimens are operator-supplied/approved, never invented. See open question 1.)*
6. **Entity-specific "what genuine contact looks like"** → real sender IDs / numbers **from `content/sources.json` canon only**.
7. **Scenario-specific "if you already…"** → paid / clicked / shared a code / replied.
8. **"Last checked YYYY-MM-DD" + reviewer line** → satisfies AdSense "reviewed/curated" expectation.
9. **Internal links** → anchor text = a near-miss query, pointing at the page that ranks for it (the GSC report's "NEAR-MISS / BACKLINK TARGETS" list).

---

## 5. Guardrails (non-negotiable)

- Edit `title` / `description` / `sections` / `faq` in `content/posts.json` → run `python3 scripts/build.py` → **never hand-edit `dist/`**.
- Every change must pass `scripts/content_gate.py`; high-stakes claims get recorded in `content/manifests/<slug>.json`; phones/emails/reporting routes come **only** from `content/sources.json`.
- **No invented** sender IDs, phone numbers, legislation, or specimens containing live links.
- **Reporting brand:** use **"Report Fraud"** (GOV.UK's current wording, operator-verified 2026-06-26) at `reportfraud.police.uk` / `0300 123 2040` for **England & Wales**; **Scotland → Police Scotland (101)**. ⚠️ The on-page "Report this scam" sidebar block is auto-generated from `content/sources.json` `report_label`, currently **"Action Fraud (UK)"** — so body and block names will diverge until the canon decision is made (see §7).

### Accuracy refinements — apply to EVERY bank/SMS page (from the 2026-06-26 reference review)

- **159 wording:** "connects you safely and directly to your bank" — NOT "to your bank's fraud team" (too specific; Stop Scams UK only lists the bank as a 159 destination).
- **In-app verification:** never claim a genuine SMS "will show up in the app." Say: check the app/website for recent activity/messages, and **if you can't verify it there, contact the bank directly** — don't conclude "fake" from app absence alone.
- **Links:** don't assert the bank does/doesn't send SMS links (unverified for SMS). Use: "a link alone is not proof either way — never use a text link to log in, verify details, enter codes, or move money."
- **"Dear Customer" / generic greeting:** a weak signal for SMS (stronger for email — genuine bank texts are often short). Caveat it; don't lead on it.
- **APP reimbursement:** "since 7 Oct 2024, most APP fraud victims can claim reimbursement for UK transfers over Faster Payments/CHAPS, subject to limits and exclusions, with a claiming deadline." Don't say "banks must reimburse most APP fraud" unqualified. **Update (operator fact-check 2026-06-26):** the specific PSR figures were sourced and ARE now included, attributed to "the PSR rules" — **£85,000 max claim, up to £100 excess, 13-month claim window**. ⚠️ Point-in-time: re-check if the PSR changes the cap/excess/window.
- **Bank phishing email:** add the bank's **verified** report address where known (e.g. Halifax `security@halifax.co.uk`); never invent one. (Not gov.uk/police.uk, so the gate won't flag it — accuracy is on us.)

*Round 2 (2026-06-26 operator review):*
- **Link domain:** do NOT say "the link isn't `<brand>.co.uk` → fake." Banks use more than one genuine owned domain (e.g. Halifax `halifax-online.co.uk`), so judging by domain alone is wrong. State it as "a lookalike or unusual domain," then give the durable rule: *never use a link from the message to log in, verify, enter a code, or move money — open the app or type the address yourself.* (Exception: **government** — `gov.uk` IS the sole genuine domain, so DVLA/HMRC pages can keep "only genuine address ends in gov.uk".)
- **Error tells:** "Small errors **can be clues**," not "give it away" — polished, error-free scams are common, so a tidy message proves nothing.
- **7726 wording:** "Forward the text to 7726 — it is free, and it reports the message to your mobile provider, which can investigate and take action." (Don't overstate "trace and block the sender.")
- **UK nations:** Report Fraud (`reportfraud.police.uk` / `0300 123 2040`) covers **England, Wales & Northern Ireland**; **Scotland → Police Scotland (101)**. Cover all four nations, don't imply E/W/Scotland is the whole UK.
- Ship through the review habit; after build, sanity-check `dist/index.html`, `dist/robots.txt`, `dist/_redirects` exist and `dist/guides/` has ≥50 dirs.

---

## 6. Cadence & measurement

**Suggested sequence (recommended): a "CTR sprint" first.** Do Tier 1 as a **title + meta + first-FAQ pass only** (no re-sectioning) — ~9 pages in one session, fastest measurable traffic gain. Then Tier 2/3 deeper diversification at ~5 pages/week.

**Re-pull `gsc_report.py` every 2–4 weeks.** Targets:
- Tier-1 CTR: from ~0.3% → toward the NHS-page benchmark (**1.9%**).
- Capture the "halifax … not arriving" query (1,744 impr, pos 4, 0 clk → any clicks is a win).
- Section-sequence uniqueness: **12/190 → 40+/190**.
- First-FAQ duplication: **eliminated** across the top 30.

**AdSense stop-criterion:** top ~50 pages each visibly bespoke (unique outline + a real specimen + query-driven FAQ + reviewer note).

---

## 7. Open questions (decide before execution)

1. **Specimens** — can you supply/approve real paraphrased text examples for the bank/courier pages, or should they stay generic-illustrative? (Strongest "added value" signal vs. fastest to ship.)
2. **Sequence** — CTR-sprint-first (recommended) vs. full-diversify in impression order?
3. **Batch size & review** — how many pages per PR, and who reviews before merge?
4. **Cannibalisation call** — `bank-text-codes-not-arriving` (troubleshooting intent) vs `halifax-bank-scam-text-uk` (scam-text intent) target overlapping "Halifax text" queries. Keep distinct (recommended) or consolidate?
5. **Title truncation (corpus-wide)** — ✅ RESOLVED 2026-06-26: chose the global fix — `seo_title(brand=False)` for guides drops the brand suffix, fixing the audit's awkward-title finding across all 190 pages (e.g. Microsoft page `<title>` "…How to Spot Fake | Beat the Scam" → "Microsoft Support Scam UK: How to Spot Fake Support Calls").

---

## 8. Progress log

**2026-06-26 — code-format + internal-links round (all 6, gate 0/0, build verified).** Example scam domains now plain reserved `.example` (no `[.]` defang, no link) shown in `<code>`; `build.py` gained inline-code rendering (`` `…` `` → `<code>`, applied to section bodies + post FAQ; phones left un-backticked so `tel:` links survive; search.json/RSS use description only, so no backtick leak — verified). Editorial in-body links added: **website-checker (`/guides/is-this-website-a-scam/`) in §5 on all six**; **one sibling-bank link in §6 on the four bank-SMS pages only** (Halifax↔Lloyds, NatWest↔Barclays) — none in DVLA/Santander bodies (DVLA bank links appear only in the auto "related" sidebar, which is fine).

**2026-06-26 — operator fact-check round (all 6 pages, gate 0/0, build verified).** Operator independently fact-checked every page against the banks'/DVLA's own pages, PSR, NCSC, Stop Scams UK & GOV.UK (sources cited in each `docs/review/<slug>-c.md`), and the verified content was applied to `posts.json`. Key sourced additions: NatWest **88355**, Santander **phishing@/smishing@santander.co.uk**, banks' own "we'll never ask…" wording, **PSR APP figures** (£85k/£100/13mo), "159 covers 99% of UK current accounts", "report to Report Fraud if you lost money/shared info/were hacked". Corrections: **`security@halifax.co.uk` removed** (unverifiable), example domains defanged (`…[.]example`), `GBP`→`£`. **`build.py` renderer upgraded** to support mixed prose+bullets in a section body (backward-compatible — verified untouched pages unchanged) so the fact-checked §5 lists render as `<p>` intro + `<ul>` + `<p>` caveat. Internal `/guides/` links were dropped by the fact-check (auto "related" block still links) — pending decision to re-add.

**Completed (21 pages):** Batch 1 (PR #12, merged+live) — `halifax-bank-scam-text-uk`, `lloyds-bank-scam-text`, `dvla-vehicle-tax-text-scam`, `natwest-fraud-text-message-scam-uk`, `barclays-bank-text-scam-uk`, `santander-email-scam-uk` (+ Barclays `.example` hotfix PR #13). Batch 2 (PR #14, merged; §5-bullets polish PR #15) — `amazon-order-scam-email-checklist`, `hermes-parcel-scam-text-uk`, `royal-mail-text-scam-uk`, `hmrc-tax-refund-text-scam-uk`, `evri-delivery-scam-guide`. Batch 3 (PR #16, merged) — `bt-broadband-scam-calls-uk`, `indeed-job-scam-uk`, `council-tax-scam-text-uk`, `ebay-buyer-scam-uk`, `tinder-scam-uk`. Batch 4 (PR #19) — `nhs-appointment-scam-text-uk` (the CTR champ, was missed), `natwest-phishing-email-uk`, `tiktok-shop-scam-uk`, `bumble-romance-scam-uk`, `wish-scam-uk-review`. **+ global:** `seo_title` suffix-drop on guides; canon `report_label` → "Report Fraud (Action Fraud)"; renderer mixed-prose+bullets + inline-`code`; `faq_schema`/`howto_schema` strip code backticks (no JSON-LD leak); category stragglers `Email/Text Message Scams` → `email`/`sms`; eBay `buyer-protection` redirect re-pointed to the guide.

- **2026-06-28 — Batch 4 (5 pages, PR #19; gate 0/0; build verified).** `nhs-appointment-scam-text-uk` (gov SMS), `natwest-phishing-email-uk` (bank email), `tiktok-shop-scam-uk` (shopping), `bumble-romance-scam-uk` (dating), `wish-scam-uk-review` (marketplace review). **NHS was the CTR champ (629 impr / pos 7.3) missed in batch 1** — title phrasing preserved, body/FAQ de-templated. GSC re-pull confirmed aggregate CTR still 0.50% (too early to read batches 1–3; re-check in 2–4 wks). Fact-check corrections: **TikTok Shop** — dropped an unverifiable "buyer protection only on checkout" claim → reframed around the in-app order trail + PayPal Goods&Services vs Friends&Family; **NatWest email** — added verified `phishing@natwest.com` (+ "emails include part of your name/postcode"); **Wish** — softened "common" frequency wording, noted Wish doesn't accept bank transfers, in-app refund (30d) + chargeback; **NHS** — "free except limited circumstances sanctioned by Parliament", keeps that genuine NHS reminder texts exist; **Bumble** — sensitive romance/pig-butchering (Report Fraud + FINRA). One NHS §7 reword to avoid the 7726→NCSC attribution flag.
- **2026-06-26 — Batch 3 (5 pages, PR #16; gate 0/0; build verified).** `bt-broadband-scam-calls-uk` (telecoms phone), `indeed-job-scam-uk` (jobs), `council-tax-scam-text-uk` (gov SMS), `ebay-buyer-scam-uk` (marketplace), `tinder-scam-uk` (dating, sensitive). Four new verticals; phone/romance specimens are paraphrased patterns (no `.example` domain). Fact-check corrections: **Indeed** — dropped the over-absolute "never charge" (agencies can't charge work-finding fees, but a basic DBS check can have a real fee → "don't pay a recruiter to secure/unlock a job; verify checks officially"); **Council tax** — fixed the page's wrong HMRC framing (it's local councils, `gov.uk/find-local-council`); **eBay** — added verified `spoof@ebay.co.uk`, Money Back Guarantee is on-platform-only; **Tinder** — sensitive/non-blaming, pig-butchering crypto angle, links romance + sextortion guides. **`build.py`:** re-pointed the dead `ebay-scam-buyer-protection-uk` redirect (was → marketplace category) to `ebay-buyer-scam-uk`, recovering ~63 impr of "buyer protection" demand.

- **2026-06-26 — Batch 2 (5 pages, PR #14; gate 0/0; build verified).** `amazon-order-scam-email-checklist` (email), `hermes-parcel-scam-text-uk`, `royal-mail-text-scam-uk`, `evri-delivery-scam-guide` (courier), `hmrc-tax-refund-text-scam-uk` (gov). New-vertical routing: NO 159; Amazon → **`reportascam@amazon.com`** (operator-corrected from `stop-spoofing@`) + NCSC; couriers → official tracking, **Hermes→Evri (Mar 2022)** cross-linked, Evri "only ever a tracking link" guidance; Royal Mail → accurate customs "Fee to Pay" nuance (it CAN notify by SMS/email) + `reportascam@royalmail.com`; HMRC → `phishing@hmrc.gov.uk` + `60599` + Personal Tax Account, avoids the gate-flagged "HMRC never texts" blanket. Operator fact-checked against couriers'/Amazon's/HMRC's own pages, NCSC, GOV.UK, PSR (sources in `docs/review/*-c.md`). **`build.py`:** schema builders strip inline-`code` backticks (JSON-LD was leaking them — invisible to users, messy for crawlers).

- **2026-06-26 — `seo_title()` global fix (DONE).** Guides now render `<title>` without the " | Beat the Scam" suffix (`brand=False` in `render_post`; home/category unchanged), giving ~58 chars of usable title and ending truncations on whole phrases. Fixes the audit's "How to Spot Fake" dangling-title finding corpus-wide. Takes effect on next `build.py` run.
- **2026-06-26 — `halifax-bank-scam-text-uk` (reference page, DONE).** First full-recipe page, built as the template for sign-off. Changes: bespoke 7-section outline (was generic 6); illustrative fake-text specimen; **159 (Stop Scams UK)** added as the primary verify route; Sender-ID **spoofing** reframe replacing the misleading "50050 is the official code, trust it" claim; mandatory **APP reimbursement (7 Oct 2024)** replacing the old voluntary-CRM framing; Cifas Protective Registration + correct CRAs; 5 unique query-driven FAQs replacing the templated "Is Halifax a legitimate bank?"; title cut to fit the 44-char budget; `updated: 2026-06-26` for a visible "Updated" date + schema `dateModified` ("last checked" signal); internal links to `lloyds-bank-scam-text` + `is-this-website-a-scam`. **Deterministic gate: PASS (0 block / 0 flag). Build + render verified** (bullets, auto-linked paths, tel-link, FAQ). LLM-judge pass deferred to CI/PR (no local API key). `dist/` reverted after verification (local OG renders differ from CI — known gotcha).
- **2026-06-26 — Round-2 refinements across all 6 done pages (gate re-passed 0/0).** Domain reframe (banks use >1 owned domain; durable "never use a message link to log in/verify/enter code/move money"); "errors can be clues" (polished scams common); simpler 7726 wording; **Northern Ireland** added to reporting (Report Fraud = E/W/NI, Scotland = Police Scotland). DVLA keeps `gov.uk`-only (accurate for gov). Codified in the Round-2 refinements list above.
- **2026-06-26 — Batch 1 (5 pages, DONE; gate 0/0 each; build verified).** `lloyds-bank-scam-text`, `dvla-vehicle-tax-text-scam`, `natwest-fraud-text-message-scam-uk`, `barclays-bank-text-scam-uk`, `santander-email-scam-uk`. Each fully de-templated (bespoke headings + intro specimen + query-driven FAQ) with per-vertical adaptation: **bank pages use 159**; **DVLA (gov) uses GOV.UK, no 159**; **Santander is the email variant** (fake-email specimen, hover-the-link guidance, `report@phishing.gov.uk` primary, "Dear Customer" treated as a valid email signal). NatWest/Barclays "genuine short code" claims replaced with the spoofing reframe. Verified: canon "Report Fraud (Action Fraud)" block, DVLA 0×159, titles untruncated, templated FAQ removed. Content written distinct per bank (not name-swapped). LLM-judge deferred to CI/PR. `dist/` reverted (OG gotcha).
- **2026-06-26 — Halifax operator review (7 corrections applied, gate re-passed 0/0).** Softened in-app verification; reframed the link FAQ (no SMS-link assertion); caveated the "Dear Customer" sign; 159 → "safely and directly to your bank"; "Report Fraud" + England/Wales vs Scotland split; qualified APP reimbursement (Faster Payments/CHAPS, limits/exclusions, deadline); added `security@halifax.co.uk`. Codified as the "Accuracy refinements" list above for the rollout. **Pending: canon `report_label` decision (§7 open Q).**
