# Fact-check audit — 11 July 2026

> **Historical point-in-time audit (2026-07-11).** Later remediation, corpus releases and live validation supersede the open recommendations and counts below. Preserve this file as audit evidence; use `docs/next-session.md`, `docs/project.md` and `scripts/validate_dist.py` for current status.

## Executive result

This is a fresh audit of the 181 guide records in `content/posts.json` and the 181 generated guide pages in `dist/guides/`.

The live domain could not be reached from the available browser/network paths during this run, so live-page parity and live rendering could not be independently confirmed. The findings below therefore apply to the committed corpus and generated pages, with live verification explicitly pending.

## Corpus checks

- Guides audited: 181
- Date range: 21 April 2026 to 5 July 2026
- Guides carrying an update date: 166
- Generated guide pages: 181
- Deterministic accuracy-gate block findings: 0
- Deterministic review flags: 10
  - legislation: 5
  - source/contact address: 4
  - HMRC channel: 1

The deterministic gate is a screening control, not an independent fact check. It does not prove that an article is accurate.

## Findings requiring editorial action

### High priority — Section 75 wording

106 guides mention Section 75. Most use appropriately qualified wording, but these statements are too broad and should be corrected:

- `is-this-website-a-scam`: “for any purchase between £100 and £30,000” and “Debit cards ... qualify for chargeback ... weaker than Section 75”. Section 75 depends on a qualifying credit agreement and debtor–creditor–supplier relationship; chargeback is a card-scheme process, not an equivalent statutory entitlement.
- `concert-ticket-scam-uk`: “Purchases over £100 are protected under Section 75”. This should say qualifying credit-card purchases with a cash price over £100 and not more than £30,000, subject to the statutory relationship and transaction facts.
- `fake-pandora-website-uk-scam`: “between £100 and £30,000 ... jointly responsible” needs the same qualifying-purchase caveat.

### High priority — APP reimbursement wording

89 guides mention APP fraud reimbursement. The recurring wording is broadly consistent with current PSR guidance, but every instance should retain “eligible”, “subject to limits and exclusions”, and “ask your bank to assess the claim”. The `gumtree-scam-uk-guide` sentence saying “most UK banks may be able to help” is materially less precise than the newer wording and should be standardised.

Current PSR guidance supports protections from 7 October 2024 for eligible payments, a 13-month reporting window, reimbursement normally within 5 business days, an £85,000 maximum, and a possible excess of up to £100. It also explains that firms may apply exclusions and that the claim is assessed by the payment firm.

### Medium priority — absolute organisation claims

159 guides contain absolute or near-absolute language such as “never”, “always”, “does not”, or “will not” about named organisations. These claims should be retained only where the organisation’s current official guidance supports the exact wording; otherwise use safer wording such as “an unexpected request for… is a warning sign” and direct readers to the organisation’s official contact route.

### Review flags from the publication gate

The existing flag list is:

- `hmrc-self-assessment-scam-uk`: HMRC never asks to confirm bank details by text.
- `is-this-website-a-scam`: Consumer Credit Act 1974.
- `pension-liberation-scam-uk`: “legally required to”.
- `concert-ticket-scam-uk`: Consumer Credit Act.
- `deepfake-video-scam-uk`: Online Safety Act 2023.
- `fake-pandora-website-uk-scam`: Consumer Credit Act.
- `companies-house-email-scam-uk`: `phishing@companieshouse.gov.uk`.
- `companies-house-scam-letter-uk`: `phishing@companieshouse.gov.uk`.
- `deed-fraud-uk-property-scam`: `reportafraud@landregistry.gov.uk`.
- `hmrc-self-assessment-scam-uk`: `branddefence@hmrc.gov.uk`.

The contact addresses were confirmed against current official guidance. HMRC’s current guidance supports `phishing@hmrc.gov.uk`, text reporting to `60599`, and `branddefence@hmrc.gov.uk` for suspicious social-media accounts. Companies House supports `phishing@companieshouse.gov.uk`; HM Land Registry supports `reportafraud@landregistry.gov.uk`.

## Evidence and citation quality

The article bodies do not provide article-level source citations for the factual claims. The site-wide reporting block links to official channels, but a reader cannot see which source supports a particular company policy, legal statement, date, or historical claim. That makes future independent verification and correction difficult.

## Recommended next action

1. Correct the three Section 75 overstatements and standardise the APP wording.
2. Review the five legal/statutory flags and the 159 absolute organisation-policy claims.
3. Add a compact “Sources checked” block or inline source links to each guide, at least for legal, regulatory, contact-channel, dated, and named-organisation claims.
4. Re-run the audit once the live domain is reachable and compare the live sitemap/page count against `dist/`.

## Official references checked

- PSR APP reimbursement guidance: https://www.psr.org.uk/information-for-consumers/app-fraud-reimbursement-protections/
- GOV.UK internet scams and phishing reporting: https://www.gov.uk/report-suspicious-emails-websites-phishing
- HMRC scam reporting: https://www.gov.uk/report-suspicious-emails-websites-phishing/report-scam-HMRC-messages-calls-social-media
- HMRC scam identification: https://www.gov.uk/guidance/identify-hmrc-related-scam-phone-calls-emails-and-text-messages
- Companies House scam reporting: https://www.gov.uk/guidance/reporting-scams-pretending-to-be-from-companies-house
- HM Land Registry property fraud: https://www.gov.uk/protect-land-property-from-fraud
