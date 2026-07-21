# Beat the Scam: site, content, AdSense and search audit

> **Historical point-in-time audit (2026-07-16).** Subsequent remediation and reviewed releases changed the live corpus. Do not treat unchecked items or counts in this report as current status; use `docs/next-session.md`, `docs/project.md` and `scripts/validate_dist.py`.

**Audit date:** 16 July 2026
**Scope:** all 182 published guides, all category hubs and generated public pages, live deployment, source links, structured data, crawl/index controls, advertising placement, and 90-day Google Search Console performance.

**Implementation update — 16 July 2026:** The Days 1–14 review-readiness batch is now implemented in the working tree: the three hubs are corrected and gated; navigational and sensitive pages are excluded from AdSense code and resource hints; all nine previously unsupported guides now have source lists; confirmed dead source URLs are replaced; `bank-text-codes-not-arriving` is rewritten around troubleshooting intent; internal redirect hops are removed from generated links; and publisher claims are corrected. The production build, deterministic corpus/HTML checks and live LLM-judge self-test all pass. Publishing automation has not been re-enabled as part of this batch.

**Operator-review update:** All 19 review responses were received. Conditional findings were applied, including Ofcom's 15 July replacement guidance, canonical Report Fraud URLs, employment-fee qualifications, the Halifax-to-Lloyds app transition and the additional 7726 message-format gate rule.

## Executive verdict

The site has a strong technical base: clean canonicalization, a complete sitemap, valid structured data, good security headers, a genuine 404 response, a named editor, visible sources, legal/privacy pages, and a working mobile layout. Those are meaningful strengths.

It is **not yet in the safest position to submit or resubmit for AdSense review**. The main risks are editorial, not infrastructural:

1. Three category hubs bypass the article accuracy gate and contain several overbroad or outdated claims.
2. A substantial part of the guide library is thin or highly templated: 52 of 182 guides contain fewer than 800 visible words, 105 have zero or one cited source, and several guide pairs are extremely similar.
3. Auto Ads can run on mostly navigational listing pages and on sensitive sexual-abuse/deepfake topics. Non-personalised ads do not remove content-eligibility risk.
4. Two cited official URLs now return 404, nine guides have no source list, and several recurring regulatory statements need more precise scope and caveats.
5. Search visibility exists, but performance is weak: 50 clicks from 10,071 impressions in the sampled 90-day Search Console window (0.50% CTR; average position 16.7).

The recommended decision is **conditional no-go until the P0 work in this report is complete**. No audit can guarantee AdSense approval or search/AI citations, but these changes would materially reduce the most obvious review risks.

## Audit ratings

These are prioritisation ratings, not Google or AdSense scores.

| Area | Rating | Finding |
|---|---:|---|
| Crawlability and index control | 9/10 | Technically strong; sitemap exactly matches indexable pages. |
| Mobile, security and page integrity | 9/10 | No mobile overflow; strong response headers; proper HTTP 404. |
| Transparency and legal pages | 8/10 | Good disclosure and privacy coverage; a few trust claims overstate the process. |
| Article factual reliability | 7/10 | High-risk automated flags were materially supportable, but sourcing is uneven. |
| Hub and site-wide factual reliability | 4/10 | Important HMRC, bank-text, 7726 and APP reimbursement statements need correction. |
| Originality and depth | 5/10 | Useful library, but too much repeated recovery/reporting copy and several near-duplicates. |
| AdSense readiness | 6/10 | Strong privacy/ads.txt setup; low-value and sensitive-page risks remain. |
| Organic search performance | 4/10 | Some near-page-one visibility, but very low CTR and signs of intent mismatch/cannibalisation. |
| AI answer discoverability | 6/10 | Crawl/schema foundations are good; unique evidence and citation-worthiness are not yet strong enough. |

## What was checked

- Parsed every record in `content/posts.json` and every post manifest.
- Ran the repository's corpus audit against all 182 guides.
- Measured visible copy depth, sources, repeated passages and pairwise textual similarity.
- Parsed all 217 generated HTML files and checked titles, descriptions, canonicals, robots directives, headings, landmarks, image alternatives, JSON-LD, duplicate IDs and local link targets.
- Compared the 216 indexable pages with `sitemap.xml`; the sets match exactly.
- Tested the live site at desktop and 390 x 844 mobile width, including the collapsed navigation.
- Checked live redirects, 404 behaviour, robots.txt, sitemap, ads.txt, llms.txt, security.txt, content types and security headers.
- Requested every cited source URL and investigated failures; anti-bot responses were not automatically classified as broken links.
- Verified the recurring/high-risk claims against current primary sources.
- Reviewed 90 days of Google Search Console page and query data.

This was a systematic check of every guide plus primary-source verification of the recurring and high-risk claim classes. It is not a legal opinion, and no finite audit can prove every unrestricted sentence in 182 articles correct forever. Laws, bank procedures, reporting routes and platform policies need scheduled rechecking.

## P0: complete before AdSense review

### 1. Correct and gate the category hubs

`content/category-hubs.json` is not covered by the article content gate. This has allowed stronger claims than the current official guidance supports.

#### SMS hub

Problematic claims include:

- “Real bank texts ... never contain a link.”
- A broad statement that banks, couriers and government bodies do not send links or requests by text.
- “All major UK networks” support 7726.

These should become behaviour-based warnings, not claims about the mere presence of a link. Genuine organisations sometimes send links. The safe distinction is whether the message requests sensitive information, payment, credentials or urgent action and whether the user independently verifies it. Current Ofcom guidance says a suspicious **SMS** text can be forwarded to 7726 free of charge; RCS, iMessage and app messages should use the relevant built-in reporting tools. See [Ofcom's current scam-message guidance](https://www.ofcom.org.uk/phones-and-broadband/scam-calls-and-messages/what-to-do-about-a-scam-call-text-or-message).

#### Government hub

The claims “HMRC never notifies a tax refund ... by text or email containing a link” and the corresponding FAQ answer “No” are too absolute. Current HMRC guidance says it sends genuine text messages, some of which contain GOV.UK information or webchat links, and describes Self Assessment repayment messages. HMRC says it will not ask for personal or financial information by text. Use that narrower rule and direct readers to independent verification through GOV.UK or their tax account. See [HMRC's current genuine-text guidance](https://www.gov.uk/guidance/check-if-a-text-message-youve-received-from-hmrc-is-genuine).

#### Payment hub

“UK banks must reimburse most victims, usually within five days” omits material scope. The mandatory protections apply to qualifying UK-to-UK Faster Payments and CHAPS APP claims made by eligible consumers, microenterprises and charities. Exclusions, a possible £100 excess, a normal five-business-day timetable, stop-clock provisions, a £85,000 cap and a 13-month claim limit can apply. Replace the blanket statement with a concise scoped version linked to the [Payment Systems Regulator consumer guidance](https://www.psr.org.uk/information-for-consumers/app-fraud-reimbursement-protections/).

Add category hubs, homepage FAQs and reusable site copy to the same deterministic and editorial gates used for guides.

### 2. Pause volume publishing and repair the low-value cohort

Google permits responsible use of generative AI, but publishing many pages without additional user value can fall within scaled-content abuse. Google AdSense also restricts ads on screens with no or low-value publisher content. See [Google's generative-AI content guidance](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content) and [Google Publisher Policies](https://support.google.com/adsense/answer/10502938?hl=en).

Corpus evidence:

- 52/182 guides have fewer than 800 visible words.
- 105/182 guides have zero or one cited source.
- 9 guides have no source list at all.
- 89 guide pairs have a token-set similarity above 0.42.
- The same APP reimbursement statement appears in roughly 65 guides.
- Several recovery/reporting paragraphs repeat verbatim or nearly verbatim across the library.

Do not make “daily publishing” the current objective. First improve, consolidate or noindex the weakest pages. Each retained guide should add topic-specific evidence: real scam wording or annotated examples, a decision table, the exact official reporting/recovery route, current primary sources, and details that could not be pasted unchanged into another guide.

The nine currently unsourced guides are:

- `work-from-home-scam-uk`
- `is-temu-a-scam`
- `facebook-marketplace-fake-buyer-scam-uk`
- `mystery-shopper-scam-uk`
- `data-entry-job-scam-uk`
- `military-romance-scam-uk`
- `fake-nike-website-scam-uk`
- `holiday-let-scam-uk`
- `festival-lineup-email-scam-uk`

### 3. Tighten AdSense placement

Keep ad code off:

- the 404 page, search/check utility, privacy, cookies, disclaimer and other utility/legal pages;
- category/listing pages unless they contain substantial original editorial content;
- sextortion, non-consensual intimate-image and sexualised deepfake-abuse guides during the review period and preferably thereafter.

The first group is already mostly handled well. The remaining risk is that Auto Ads can run on the guides index and non-hub category listings, which are primarily navigational. Sensitive pages currently request non-personalised ads, but that only affects personalisation; it does not make all subject matter eligible.

Continue to keep ads visually distinct from navigation and scam-reporting calls to action. The present `ads.txt` publisher line is valid.

### 4. Repair sources and require a minimum evidence standard

Confirmed 404 source URLs:

1. The old NCSC business-email-compromise PDF used by `invoice-redirection-scam-checklist` and `invoice-fraud-uk-businesses`. Replace it with the live [NCSC business payment fraud guidance](https://www.ncsc.gov.uk/section/respond-recover/business-payment-fraud).
2. The old TfL “new private hire regulations” page used by `airport-transfer-taxi-scam-uk`. Replace it with a current TfL licensing/private-hire source after confirming the exact claim it supports.

Also replace the old Action Fraud courier-fraud link with the current [Report Fraud courier fraud page](https://www.reportfraud.police.uk/courier-fraud/).

Set a publication rule of at least two relevant sources for factual service, legal or recovery claims, with at least one primary source wherever one exists. A source count alone is not enough: each source should visibly support a specific claim.

## Fact-check results

The repository audit flagged 11 high-interest claims for review: nine legislation-related statements, one source-address statement and one HMRC-channel statement. The flagged article claims were materially supportable, with the qualifications below.

| Claim class | Result | Required treatment |
|---|---|---|
| HMRC bank details by text | Substantively correct | Prefer HMRC's exact rule: it will not ask for personal or financial information in a text. Do not extend this to “HMRC never sends links/texts.” |
| Companies House sender address | Verified | The official 17 March 2026 notice identifies `companies.house@notifications.service.gov.uk`; retain the date/context because sender display alone does not prove legitimacy. |
| Pension transfer red/amber flags | Verified | The checks apply under the transfer safeguards introduced from 30 November 2021; link the current regulator guidance. |
| Deepfake creation/request offences | Verified with jurisdiction caveat | Relevant provisions commenced on 6 February 2026 and apply to England and Wales. Do not present this as one uniform UK offence. Cite the commencement instrument. |
| Section 75 thresholds and intermediary caveat | Materially correct | Use the precise statutory/FCA threshold wording and explain the debtor-creditor-supplier relationship; do not imply every card-funded transaction qualifies. |

Primary references include the [Companies House security-issue email notice](https://www.gov.uk/government/publications/email-to-registered-companies-about-the-webfiling-security-issue), [Pensions Regulator transfer-request guidance](https://www.thepensionsregulator.gov.uk/en/document-library/scheme-management-detailed-guidance/administration-detailed-guidance/dealing-with-transfer-requests), [deepfake commencement instrument](https://www.legislation.gov.uk/uksi/2026/31/pdfs/uksi_20260031_en.pdf), [Data (Use and Access) Act explanatory notes](https://www.legislation.gov.uk/ukpga/2025/18/notes/division/5/index.htm), and [FCA Section 75 guidance](https://www.fca.org.uk/freedom-information/information-how-consumer-credit-act-1974-s75-applies-travel-services-payments-september-2021).

### Recurring claims that should be made more precise

- **APP reimbursement:** do not reduce the rule to “banks must refund within five days.” State payment rails, claimant eligibility, exceptions, possible excess, cap and stop-clock at least once on a canonical explainer; link shorter guides to it.
- **Report Fraud:** use the current service name and official reporting routes. Its reporting service and contact details are described on the [official reporting page](https://www.reportfraud.police.uk/reporting-a-fraud/).
- **FCA verification:** tell readers to use the FCA Firm Checker/Register independently, not a link supplied by a caller. See [FCA scam protection guidance](https://www.fca.org.uk/consumers/protect-yourself-scams).
- **Bank and government messages:** avoid “never sends a link” rules. Teach readers to stop, open the official app/site independently and never disclose codes or credentials.
- **Platform protection:** distinguish platform policies from legal rights; policies and eligibility can change.

## Originality, overlap and cannibalisation

High-similarity pairs that need human consolidation/rewrite decisions include:

| Guides | Similarity |
|---|---:|
| Evri vs Hermes delivery scams | 0.804 |
| ASOS copycat vs fake Ray-Ban websites | 0.796 |
| Monzo vs Starling scam texts | 0.779 |
| TSB vs Nationwide scam texts | 0.759 |
| Fake Nike vs ASOS copycat websites | 0.750 |
| Fake Nike vs fake Ray-Ban websites | 0.749 |
| Tinder vs Bumble scams | 0.739 |
| Lloyds vs Halifax scam texts | 0.715 |
| Santander email vs NatWest phishing | 0.650 |

Shared reporting and recovery boilerplate inflates these figures, so similarity alone is not a deletion rule. Use Search Console query overlap, backlinks and user intent before consolidating. Where two pages answer the same intent with the same advice, retain the stronger URL, merge unique material and redirect the weaker one. Where brands genuinely require separate guides, replace generic paragraphs with brand-specific evidence and official controls.

The clearest live intent problem is `bank-text-codes-not-arriving`: it received about 1,523 impressions at average position 3.1 for “halifax text messages not arriving” but no clicks, while the Halifax scam page also competes for related terms. The troubleshooting page contains unsupported operational statements about SMS gateways, carrier filtering and HMRC/NHS peak-load issues. Rewrite it to directly answer delivery/troubleshooting intent with reliable service-specific evidence, clearly separate “message not received” from scam detection, and remove unsupported examples.

## Search performance and priorities

Ninety-day Search Console totals sampled during the audit:

- **Clicks:** 50
- **Impressions:** 10,071
- **CTR:** 0.50%
- **Average position:** 16.7

Top opportunity pages:

| Page | Impressions | Clicks | Avg. position | Priority |
|---|---:|---:|---:|---|
| DPD delivery scam text | 1,956 | 5 | 11.3 | Add original examples/evidence and test title/meta for “fake DPD text” intent. |
| Bank text codes not arriving | 1,628 | 4 | 3.3 | Fix severe intent mismatch and Halifax overlap. |
| Halifax scam text | 807 | 5 | 13.3 | Differentiate scam intent from delivery troubleshooting. |
| Lloyds scam text | 711 | 3 | 8.8 | Improve snippet and brand-specific value. |
| NHS scam text | 647 | 12 | 7.4 | Protect/improve with current NHS-specific sources and examples. |
| DVLA vehicle-tax scam | 204 | 0 | 9.7 | Rewrite title/meta around the exact query and add current DVLA evidence. |

There are at least 27 query opportunities with average positions between 5 and 20. The next growth cycle should update the top ten existing pages rather than add more URLs. Measure query-to-page fit, CTR and conversions to official reporting/checking resources after each change.

Search Console also still shows impressions for historical redirected slugs. Update the remaining internal links to their final canonical targets, inspect the final URLs in Search Console and request recrawling where justified.

## Technical SEO findings

### Passed

- 216 indexable generated pages and 216 unique sitemap URLs; exact match.
- No duplicate titles, meta descriptions or canonical URLs.
- One H1 and one main landmark on each generated HTML page.
- All JSON-LD blocks parse successfully.
- No generated image is missing alternative text.
- HTTPS, apex-host and old-path redirects work.
- Missing pages return HTTP 404, not a soft 404.
- CSP, HSTS, frame denial, MIME sniff protection, referrer policy, permissions policy and cross-origin opener policy are present.
- `robots.txt`, `sitemap.xml`, `ads.txt`, `llms.txt` and `security.txt` are accessible with appropriate content types.
- The mobile navigation works at 390 px and there is no horizontal overflow.

### Improvements

1. Replace four internal redirect hops with direct links. The affected destinations include the current bank-transfer scam, DVLA email scam, bank/police impersonation and Windows tech-support URLs.
2. Shorten the disclaimer meta description (currently about 172 characters).
3. Add source URLs to Article JSON-LD using an appropriate `citation` representation where the source directly supports the article.
4. Remove automatic `reviewedBy` markup when the reviewer is merely the same person as the author and no distinct review occurred. Structured data should describe the visible editorial process, not imply independent review.
5. Keep FAQ markup for semantic clarity, but do not plan around FAQ rich results; Google generally limits those results to well-known authoritative government and health sites.
6. Ensure `dateModified` changes only when the visible article received a substantive update. The corpus has large clusters of identical update dates, which can look like batch freshness rather than meaningful maintenance.
7. The IndexNow key file is deployed, but no submission workflow was found. Submit changed canonical URLs at deploy time, then monitor IndexNow status and Bing's AI Performance reporting. See [Bing's IndexNow guidance](https://blogs.bing.com/webmaster/September-2024/IndexNow-When-and-How-Websites-Should-Notify-Search-Engines), [sitemap guidance for AI-powered search](https://blogs.bing.com/webmaster/July-2025/Keeping-Content-Discoverable-with-Sitemaps-in-AI-Powered-Search), and [Bing AI Performance](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview).

## Trust and publisher statements

- The About page is unusually transparent about the named editor, AI-assisted drafting and editorial process. Retain that disclosure.
- “Every recommendation ... official authority” is too strong because some sources are commercial or secondary. Say that primary official sources are preferred and clearly distinguish secondary explanatory sources.
- “New guide published daily by an editorial team” in `llms.txt` does not accurately match a single named editor and AI-assisted process. Use “independent publication with AI-assisted drafting and editorial review,” and only promise a publication cadence that is consistently true.
- The author bio claim that scams cost UK households “tens of millions a year” is vague and understates broader fraud losses while lacking a source. Replace it with a sourced statistic tied to a defined year/category, or remove it.
- Add a visible corrections policy and article-level “last fact-checked” notation only when a real fact check occurred.

## AI search and answer-engine visibility

There is no reliable switch that guarantees inclusion or citation by Gemini, Copilot, Perplexity or other answer tools. `llms.txt` is an unofficial discovery aid, not a ranking standard. The durable strategy is to make pages crawlable, precise and worth citing.

Priorities:

1. Publish unique, verifiable artefacts: annotated scam-message examples, exact decision trees, comparison tables, timelines and jurisdiction-specific recovery rules.
2. Cite primary sources next to the claims they support and expose citations in structured data where appropriate.
3. Keep stable canonical URLs, dates and authorship accurate.
4. Use Bing Webmaster Tools' AI Performance reporting for Copilot/Bing visibility; use Search Console query data for Google/Gemini search surfaces.
5. Make concise answers extractable, but keep the surrounding qualifications that prevent unsafe overgeneralisation.
6. Earn independent mentions and links from relevant consumer, community, cyber-safety and local-authority sources. Technical files alone do not establish authority.

## Recommended delivery plan

### Days 1-14: review readiness

- Correct the three category hubs and put them under the accuracy gate.
- Remove ad eligibility from navigational and sensitive-content pages.
- Repair the confirmed broken sources and source the nine unsupported guides.
- Rewrite `bank-text-codes-not-arriving` and separate it from Halifax scam intent.
- Replace remaining internal redirect links.
- Correct the About/author/llms.txt publisher claims.

### Days 15-45: quality consolidation

- Manually review the 52 sub-800-word guides and the top similarity clusters.
- Merge/noindex pages that do not have a distinct search intent or unique value.
- Upgrade the top ten Search Console opportunity pages with original examples, primary sources and better snippets.
- Add source minimums and claim-specific citation checks to the content gate.
- Run a fresh build and repeat the full HTML/source-link audit.

### Days 46-90: authority and measurement

- Implement deploy-time IndexNow submission.
- Track Search Console and Bing AI Performance by updated URL and query.
- Build a small number of reference-grade scam resources that external sites would reasonably cite.
- Pursue relevant editorial links/mentions; avoid bulk or paid link schemes.
- Apply or reapply for AdSense only after the low-value cohort and ad-placement rules have been addressed.

## AdSense pre-application checklist

- [ ] Category-hub factual corrections are live.
- [ ] All indexable factual guides have credible, claim-relevant sources.
- [ ] Confirmed 404 sources are replaced.
- [ ] Navigational/utility and sensitive-abuse pages cannot request ads.
- [ ] Thin/near-duplicate pages have been improved, merged or noindexed.
- [ ] About, contact, privacy, cookies, disclaimer and corrections information are accurate and easy to reach.
- [ ] No publisher statement overstates the team, review process or update cadence.
- [ ] Mobile and desktop ad layouts have been visually checked after ads load.
- [ ] A fresh crawl finds no broken internal links, schema errors or accidental indexability changes.
- [ ] Search Console has no unresolved manual action or security issue.

Passing every item improves readiness but does not guarantee approval; AdSense review decisions remain Google's.
