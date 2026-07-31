# Fact re-verification report — 2026-Q3-targeted

Generated 2026-07-31 · model `claude-sonnet-5` · 16 guides examined.

**No facts were edited.** This report only records what the deterministic gate and a web-search-enabled Claude pass found — apply any corrections by hand, then merge this PR (or close it to discard). See the reviewer checklist at the bottom.

## Summary

- Deterministic re-scan: 0 BLOCK-tier, 15 FLAG-tier (across the whole corpus, not just guides published this week)
- Web-verified drift (Pass B): 4 finding(s)

## A2. Deterministic FLAG-tier issues (corpus-wide, any age)

| Slug | Check | Claim |
|---|---|---|
| is-this-website-a-scam | legislation | makes a legal/legislation claim ('the Consumer Credit Act 1974') — verify it is accurate. |
| tinder-scam-uk | scale_claim | unsourced scale claim in the hero. Either attribute it to a published figure (the site's own /resea… |
| companies-house-email-scam-uk | source | cites a non-canon official reporting email 'companies.house@notifications.service.gov.uk'. Verify i… |
| binance-impersonation-scam-uk | dated_event | asserts a dated event involving an authority ('FCA-authorised, and Binance announced in October 202… |
| fake-nike-website-uk | legislation | makes a legal/legislation claim ('the Consumer Credit Act 1974') — verify it is accurate. |
| asos-copycat-scam-uk | legislation | makes a legal/legislation claim ('the Consumer Credit Act 1974') — verify it is accurate. |
| fake-ugg-website-uk | legislation | makes a legal/legislation claim ('the Consumer Credit Act') — verify it is accurate. |
| viagogo-scam-uk | scale_claim | unsourced scale claim in the hero. Either attribute it to a published figure (the site's own /resea… |
| concert-ticket-scam-uk | legislation | makes a legal/legislation claim ('the Consumer Credit Act') — verify it is accurate. |
| concert-ticket-scam-uk | scale_claim | unsourced scale claim in the hero. Either attribute it to a published figure (the site's own /resea… |
| deepfake-video-scam-uk | legislation | makes a legal/legislation claim ('the Online Safety Act 2023') — verify it is accurate. |
| deepfake-video-scam-uk | legislation | makes a legal/legislation claim ('the Online Safety Act') — verify it is accurate. |
| fake-ray-ban-website-scam-uk | legislation | makes a legal/legislation claim ('the Consumer Credit Act 1974') — verify it is accurate. |
| fake-pandora-website-uk-scam | legislation | makes a legal/legislation claim ('the Consumer Credit Act') — verify it is accurate. |
| hmrc-self-assessment-scam-uk | hmrc_channel | blanket 'HMRC never texts/emails/links you' — HMRC runs genuine SMS/email campaigns and genuine tex… |

## B. Web-verified drift

| Slug | Claim in guide | Issue | Correct value | Source | Confidence |
|---|---|---|---|---|---|
| fake-nike-website-uk | Advice Direct Scotland in Scotland on 0808 800 9060 | This phone number for Advice Direct Scotland is outdated; GOV.UK's current consumer rights page and… | Advice Direct Scotland's current phone number is 0808 164 6000 | https://www.gov.uk/consumer-protection-rights | high |
| fake-ugg-website-uk | Advice Direct Scotland in Scotland on 0808 800 9060 | The phone number given for Advice Direct Scotland's consumer advice service is incorrect; official … | 0808 164 6000 | https://consumeradvice.scot/contact/ | high |
| fake-ray-ban-website-scam-uk | Advice Direct Scotland in Scotland on 0808 800 9060 | The number given for Scotland's consumer advice service (consumeradvice.scot) is stale; official Ad… | 0808 164 6000 (consumeradvice.scot / Advice Direct Scotland consumer helpline) | https://www.consumeradvice.scot/contact-us/ | high |
| fake-pandora-website-uk-scam | Advice Direct Scotland in Scotland on 0808 800 9060 | The phone number given for Advice Direct Scotland's consumer helpline is incorrect; current primary… | 0808 164 6000 | https://www.gov.scot/news/new-consumer-advice-service-launc… | high |

### Other guides repeating the same drifted claim

- **fake-nike-website-uk**'s finding on "Advice Direct Scotland in Scotland on 0808 800 9060" also appears in: companies-house-email-scam-uk, fake-ugg-website-uk, fake-ray-ban-website-scam-uk, fake-pandora-website-uk-scam
- **fake-ugg-website-uk**'s finding on "Advice Direct Scotland in Scotland on 0808 800 9060" also appears in: companies-house-email-scam-uk, fake-nike-website-uk, fake-ray-ban-website-scam-uk, fake-pandora-website-uk-scam
- **fake-ray-ban-website-scam-uk**'s finding on "Advice Direct Scotland in Scotland on 0808 800 9060" also appears in: companies-house-email-scam-uk, fake-nike-website-uk, fake-ugg-website-uk, fake-pandora-website-uk-scam
- **fake-pandora-website-uk-scam**'s finding on "Advice Direct Scotland in Scotland on 0808 800 9060" also appears in: companies-house-email-scam-uk, fake-nike-website-uk, fake-ugg-website-uk, fake-ray-ban-website-scam-uk

## Reviewer checklist

- [ ] For each Section B finding, confirm the correct value against its cited source
- [ ] Edit the guide's `sections`/`faq` in `content/posts.json` by hand — never the legacy `content` field (it is never rendered)
- [ ] Never use `[text](/guides/slug/)` bracket-links or `**bold**` in article prose — `build.py` has no Markdown renderer for either (see CLAUDE.md invariant 6)
- [ ] For any Section A1/A2 item, add the verified route to `content/sources.json` or fix the prose per the check's `detail`
- [ ] Run `python3 scripts/build.py` and grep `dist/` for `](`, `**`, and `…` before committing
- [ ] If a reporting route or phone number changed, update `content/sources.json` (canon) so `content_gate.py` and `build.py`'s on-page reporting block stay in sync

---

## Operator adjudication — 2026-07-31

**All four Section B findings are FALSE POSITIVES.** Reviewed and dismissed; no edit made.

Every one is the same claim — that `0808 800 9060` for Advice Direct Scotland is "outdated"
or "incorrect", correct value `0808 164 6000`. All four were labelled **high** confidence.

Re-checked directly against the primary pages today:

| Page | Scotland number it publishes |
|---|---|
| `gov.uk/consumer-advice` — **the page the guides cite** | **`0808 800 9060`** |
| `gov.uk/consumer-protection-rights` | `0808 164 6000` |

Both numbers are genuine and both are current. They are two different services run by the
same charity: advice.scot's general advice line, and the separately branded
consumeradvice.scot consumer helpline. This was established on 2026-07-30 and both are in
`content/sources.json`; only the `on_page` one reaches reader prose, so nobody is given two
Scottish helplines in one sentence.

The checker found the second number on one GOV.UK page and inferred the first was stale. That
is the same inference made and then corrected during the July review cycle. **Acting on it
would have broken the deliberate citation↔number alignment built into
`nation-consumer-routing-v5`**, where the nation numbers are attributed to `/consumer-advice`
and the conditional Trading Standards referral separately to `/consumer-protection-rights`.

Also noted: `consumeradvice.scot` — cited by the checker as a source — still fails TLS
certificate validation (`unable to verify the first certificate`), unchanged since
2026-07-30. It should not be treated as a verifiable source while that persists.

**Score for this pass: 16 guides web-verified, 0 real drift, 4 false positives.** The
`confidence: high` label is not reliable on its own and must not gate an automatic edit.
