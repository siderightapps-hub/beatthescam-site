# Fact re-verification report — 2026-Q3-remainder

Generated 2026-07-31 · model `claude-sonnet-5` · 71 guides examined.

**No facts were edited.** This report only records what the deterministic gate and a web-search-enabled Claude pass found — apply any corrections by hand, then merge this PR (or close it to discard). See the reviewer checklist at the bottom.

## Summary

- Deterministic re-scan: 0 BLOCK-tier, 4 FLAG-tier (across the whole corpus, not just guides published this week)
- Web-verified drift (Pass B): 2 finding(s)

## A2. Deterministic FLAG-tier issues (corpus-wide, any age)

| Slug | Check | Claim |
|---|---|---|
| ebay-listing-fee-scam-uk | report_mailbox | tells the reader to report to 'spoof@ebay.co.uk', which is not in content/sources.json. Verify it a… |
| cruise-scam-uk | legislation | makes a legal/legislation claim ('the Consumer Credit Act 1974') — verify it is accurate. |
| cruise-scam-uk | legislation | makes a legal/legislation claim ('the Consumer Rights Act') — verify it is accurate. |
| facebook-dating-scam-uk | legislation | makes a legal/legislation claim ('the Consumer Credit Act') — verify it is accurate. |

## B. Web-verified drift

| Slug | Claim in guide | Issue | Correct value | Source | Confidence |
|---|---|---|---|---|---|
| smart-meter-scam-call-uk | The UK has been rolling out smart meters since 2011, and genuine installations are still taking pla… | This claim is inaccurate for Northern Ireland, where the smart meter rollout has not yet begun and … | Smart meter installations are ongoing in Great Britain, but no smart electricity meters have yet be… | https://www.consumercouncil.org.uk/consumers/help-consumers… | high |
| hsbc-bank-scam-call-uk | waiting a few minutes first | HSBC's own current guidance does not say to wait minutes before calling back; it specifies a much s… | HSBC advises: hang up properly, wait 15 seconds, make sure the line is disconnected, then wait anot… | https://www.hsbc.co.uk/help/security-centre/fraud-guide/com… | medium |

## Reviewer checklist

- [ ] For each Section B finding, confirm the correct value against its cited source
- [ ] Edit the guide's `sections`/`faq` in `content/posts.json` by hand — never the legacy `content` field (it is never rendered)
- [ ] Never use `[text](/guides/slug/)` bracket-links or `**bold**` in article prose — `build.py` has no Markdown renderer for either (see CLAUDE.md invariant 6)
- [ ] For any Section A1/A2 item, add the verified route to `content/sources.json` or fix the prose per the check's `detail`
- [ ] Run `python3 scripts/build.py` and grep `dist/` for `](`, `**`, and `…` before committing
- [ ] If a reporting route or phone number changed, update `content/sources.json` (canon) so `content_gate.py` and `build.py`'s on-page reporting block stay in sync
