# Beat The Scam — fresh content, AdSense, search and AI audit

**Audit date:** 25 July 2026  
**Code/content baseline:** `391b23d32715af3fddcd8d48f2773f623db6376d` (`origin/main`, clean and fully up to date when the audit began)  
**Production site:** https://beatthescam.com  
**Scope:** 186 guide source records, 185 indexable guides after the documented Hermes consolidation, 17 guide categories, the scam checker, research pages, trust/legal pages, generated feeds and discovery files, and the five Netlify Functions.

This is a new audit of the current repository and live site. It does not carry forward the conclusions of an earlier audit.

## Executive decision

**AdSense resubmission: hold for remediation.**

The site is technically strong and substantially complete: it is crawlable, secure, mobile-usable, well labelled, transparent about ownership, and has working policy/trust pages. The strongest AdSense risk is not the ad implementation. It is **insufficient differentiation between several families of guides**. Some article pairs share hundreds of identical seven-word sequences, including an exact recovery section in multiple shopping guides. Google explicitly asks AdSense applicants for unique, original and valuable content, and warns against cookie-cutter pages.

**Search and AI eligibility: technically ready, competitively weak.**

All important pages can be crawled and indexed, but current Google performance is extremely low. Over the fresh 28-day Search Console window the site recorded **1 click, 649 impressions, 0.15% CTR and an average position of 52.4**. The main constraints are content originality, limited contextual internal linking, thin category architecture, uneven evidence depth, and limited demonstrated external authority—not missing schema or crawler directives.

**Factual accuracy: good overall, but the safety net is broken.**

The fresh full-corpus pass found two confirmed article corrections and one low-impact citation-precision issue. More seriously, the scheduled quarterly fact-checker currently converts model/API failures into a successful run and can report `DRIFT_COUNT=0` while every guide failed to be checked. This must be repaired before the site can credibly rely on its freshness process.

No AdSense, Google, Bing, Gemini, Copilot or Perplexity approval or placement can be guaranteed. The work below removes identifiable risks and strengthens eligibility; it cannot control a third party's final decision.

## What was tested

- Synced and compared the repository with `origin/main`; the audit ran against the current commit.
- Ran the generated-site validator across all HTML, canonical URLs, JSON-LD and local links.
- Audited all guide records for required fields, content depth, sources, dates, quick answers and article-to-article similarity.
- Re-ran the deterministic editorial gate across the whole corpus.
- Ran a web-search-enabled claim re-verification pass across 185 of 186 records. The API allowance ended on the final record; that remaining Instagram giveaway guide and its listed sources were manually reviewed, with no confirmed drift found.
- Checked all 291 unique cited source URLs: 246 returned `200`, one returned `202`, 40 rejected automated access with `403`, and four timed out. None returned `404`, `410` or `5xx`. Three timed-out sources were confirmed current through independent search; one HP fraud-alert page remained machine-inaccessible, while its companion official HP UK support URL returned `200`.
- Checked production status codes, redirects, security headers, robots, sitemap, feeds, `ads.txt`, canonicals, metadata and structured data.
- Inspected representative production pages in desktop and 390 × 844 mobile layouts, including menu behaviour, horizontal overflow, headings, skip navigation and browser-console errors.
- Inspected the current Search Console 28-day search-performance data.
- Reviewed the saved Bing AI Performance export for 18 June–16 July 2026 as analytics evidence, not as an earlier audit conclusion.

The Google PageSpeed Insights API returned a quota error during this audit, so this report does **not** invent or reuse a Lighthouse score. The site's static assets are small, but a current field/Core Web Vitals measurement still needs to be captured.

## Audit scorecard

| Area | Result | Decision |
|---|---:|---|
| Crawlability and indexation | Pass | 226 indexable canonicals, clean sitemap/canonicals, no broken local links |
| Site rendering and navigation | Pass | Desktop/mobile navigation works; no sampled console errors or horizontal overflow |
| Security and production headers | Pass | Strong live CSP, HSTS and related headers; correct `200`/`301`/`404` behaviour |
| Ownership and trust | Pass | Author, About, contact, editorial, corrections, methodology, privacy and cookie information are available |
| Ad implementation | Pass with dashboard checks outstanding | Correct `ads.txt`; ads excluded or limited on sensitive and trust/tool pages |
| Factual accuracy | Pass with corrections | Two confirmed content corrections; one legal-title precision issue |
| Ongoing fact-check reliability | **Fail** | Quarterly workflow can silently report success when checks fail |
| Content originality | **Fail for AdSense resubmission** | Five article pairs exceed 0.30 seven-word-shingle similarity; top pair is 0.538 |
| Contextual internal linking | Needs major work | 98 guides contain no contextual guide link; 113 receive no contextual body link |
| Category/topic architecture | Needs major work | Only 3 of 17 categories have substantive editorial hubs |
| Google organic performance | Weak | 1 click / 649 impressions / average position 52.4 in the audited 28-day window |
| Bing/Copilot citation visibility | Promising, not equivalent to traffic | Saved export: 11,481 citations, 97 cited pages, 118 sampled grounding queries |
| Gemini/Perplexity eligibility | Pass at crawler level | Google indexing prerequisites are met; `PerplexityBot` is allowed by the wildcard rule |

## P0 — resolve before requesting another AdSense review

### 1. Rewrite or consolidate the highly duplicated guide families

The audit compared normalized article bodies using seven-word shingles. Exact titles, descriptions and quick answers are unique, but body copy is not sufficiently differentiated in several clusters.

| Similarity | Shared 7-word sequences | Guide A | Guide B |
|---:|---:|---|---|
| 0.538 | 601 | `asos-copycat-scam-uk` | `fake-ray-ban-website-scam-uk` |
| 0.442 | 519 | `fake-nike-website-uk` | `asos-copycat-scam-uk` |
| 0.419 | 512 | `fake-nike-website-uk` | `fake-ray-ban-website-scam-uk` |
| 0.330 | 522 | `tinder-scam-uk` | `bumble-romance-scam-uk` |
| 0.323 | 411 | `tsb-bank-scam-text-messages-uk` | `nationwide-scam-text-uk` |
| 0.287 | 429 | `monzo-scam-transfer-uk` | `starling-bank-scam-uk` |
| 0.215 | 314 | `lloyds-bank-scam-text` | `natwest-fraud-text-message-scam-uk` |
| 0.214 | 297 | `package-holiday-scam-uk` | `fake-airline-ticket-scam-uk` |
| 0.213 | 343 | `santander-email-scam-uk` | `natwest-phishing-email-uk` |

There are 5 pairs at or above 0.30, 9 at or above 0.20, and 14 at or above 0.15. In the ASOS/Ray-Ban and Nike/ASOS comparisons, the recovery section is identical; their reporting and FAQ sections are also heavily reused. Similar exact or near-exact recovery text appears in bank-guide pairs.

This is the clearest current AdSense-review risk. Google's official guidance says:

- AdSense content should be high-quality, original and attract an audience: https://support.google.com/adsense/answer/9724?hl=en
- Pages should provide unique and interesting content and a reason to visit: https://support.google.com/adsense/answer/7299563?hl=en-uk
- Cookie-cutter approaches with little original value are discouraged: https://support.google.com/adsense/answer/23921?hl=en
- Generating many pages without added value can violate the scaled-content-abuse policy: https://developers.google.com/search/docs/fundamentals/using-gen-ai-content

**Required remediation**

1. Rework all 14 pairs above the 0.15 threshold, starting with the shopping, dating and bank clusters.
2. Write each affected page from the specific user's decision problem, not from a shared article shell.
3. Add organisation- or scam-specific evidence: exact current verification route, realistic redacted message pattern, unique attack sequence, platform-specific reporting flow, distinct recovery constraints, and a dated primary-source conclusion.
4. Remove generic repeated FAQs where a concise shared recovery guide plus a contextual link would serve users better.
5. Merge or redirect pages where the search intent and practical answer are genuinely indistinguishable.
6. Pause high-volume automated publication until the generator/gate can detect within-corpus similarity before publication.

Do not solve this by merely changing synonyms. The page needs distinct information and user value.

### 2. Repair the quarterly fact-reverification workflow

Two independent defects were reproduced in `scripts/fact_reverify.py`:

- The default `claude-sonnet-5` call includes `temperature=0`. The current model rejects that parameter.
- The response parser only strips a Markdown fence when it wraps the entire response. A response containing short prose followed by fenced JSON fails `json.loads`.

The exception handler records each failure, but the script still returns exit code 0. `DRIFT_COUNT` counts only successful findings, so a run in which every guide failed can emit `DRIFT_COUNT=0`; the GitHub workflow then accepts it and can open a misleading “0 drifted” review PR.

**Required remediation**

1. Remove unsupported sampling parameters for the default model.
2. Parse the JSON object robustly or require schema-constrained output.
3. Add retry/backoff for transient failures and a controlled concurrency limit.
4. Emit an explicit error count and fail the job if any guide remains unchecked after retries.
5. Make the workflow validate `ERROR_COUNT=0` before committing a report.
6. Add a self-test covering prose-plus-fenced-JSON, malformed JSON, rate-limit failure and a fully failed run.
7. Run a three-guide smoke test, then a complete corpus run, before relying on the quarterly automation again.

The fresh compatibility pass examined 186 records, with one final API-allowance failure and seven raw model findings. Manual primary-source adjudication reduced those to the confirmed findings below.

### 3. Apply the confirmed factual corrections through operator review

No published article was edited by this audit.

| Guide | Finding | Verdict |
|---|---|---|
| `yodel-scam-text-messages` | The guide directs readers to the Yodel app/site for tracking and fraud contact. The Yodel by InPost app stopped being available on 17 July 2026; tracking and support moved to the InPost app/site. | **Confirmed material drift** |
| `halifax-bank-scam-text-uk` | The guide says the Halifax-to-Lloyds change was announced on 2 July 2026. Lloyds Banking Group's press release is dated 1 July 2026. | **Confirmed minor error** |
| `bitcoin-atm-scam-uk` | The regulation is referred to by a shortened title that omits “(Information on the Payer)”. | **Low-impact citation precision** |
| `hmrc-phone-call-scam-uk` | Model suggested every real automated tax-debt call must contain a taxpayer reference. | **Rejected**: only a secondary Which? statement was found; current primary HMRC guidance does not establish that universal test |
| `advance-fee-scam-uk` | Model suggested changing the current average loss from £255 to £260. | **Rejected**: the current FCA consumer page says £255; £260 is from an older campaign release |

Primary evidence:

- Yodel by InPost app retirement: https://www.yodel.co.uk/help-centre/can-i-still-use-my-yodel-by-inpost-app
- Halifax announcement: https://www.lloydsbankinggroup.com/media/press-releases/2026/lloyds-banking-group/halifax-rebrand-to-lloyds.html
- FCA current £255 figure: https://www.fca.org.uk/consumers/loan-fee-fraud
- HMRC's current phone-contact guidance: https://www.gov.uk/guidance/check-if-a-phone-call-youve-received-from-hmrc-is-genuine
- Full regulation title: https://www.legislation.gov.uk/uksi/2017/692

Fresh review packets were created for the two article corrections. Content should not be changed until the matching operator reply is received.

### 4. Fix the deterministic gate's false positive and source-evidence gap

The corpus gate reports `0345 172 0088` in the TalkTalk guide as a BLOCK-tier invented number. It is a current number on TalkTalk's own contact page, so this is a gate/canon defect rather than a live-content defect:

https://community.talktalk.co.uk/t5/Articles/How-to-contact-TalkTalk-Broadband/ta-p/2230529

The gate also flags `companies.house@notifications.service.gov.uk`. Current Companies House guidance confirms that genuine messages end in `.gov.uk`, but the exact mailbox was not located on the public primary-source pages checked during this audit. Treat it as an **evidence gap**, not a confirmed false statement. Either obtain a current Companies House source for that exact address or remove the address-specific claim in favour of the documented `.gov.uk` rule:

https://www.gov.uk/guidance/reporting-scams-pretending-to-be-from-companies-house

The other deterministic flags were checked against current primary sources and were not confirmed as errors. In particular, the HMRC wording correctly distinguishes genuine HMRC text campaigns from requests for financial information:

https://www.gov.uk/guidance/check-if-a-text-message-youve-received-from-hmrc-is-genuine

## P1 — content and architecture work with the highest ranking upside

### 5. Build a real contextual internal-link graph

Related-guide widgets prevent technical orphaning, but the article bodies are weakly connected:

- **98 of 185** indexable guides have no contextual link to another guide in their sections or FAQs.
- **113 of 185** receive no contextual body link from another guide.
- The median number of contextual guide links per article is zero.

Google says internal links and descriptive anchor text help users and Google understand pages, and that important pages should be linked from another relevant page:

https://developers.google.com/search/docs/crawling-indexing/links-crawlable

**Required remediation**

- Build intentional clusters around parcel texts, bank impersonation, APP recovery, marketplace selling, romance fraud, crypto recovery, job scams, government impersonation and tech support.
- Give each important guide at least one genuinely useful contextual inbound link and link out where a deeper guide answers the next likely question.
- Use descriptive, natural anchor text. Do not insert a fixed quota or keyword-stuffed link blocks.
- Link specific recovery wording to the central recovery material instead of copying the same recovery section into many pages.

### 6. Expand the category layer from listings into useful hubs

Only `sms`, `payment` and `government` have hand-authored category hubs. The remaining **14 of 17 categories** are largely generated descriptions plus cards.

Create user-task-led hubs for at least:

- bank/phone impersonation
- marketplace buying and selling
- email phishing
- travel and ticket scams
- fake shopping sites
- employment scams
- crypto and investment scams
- romance/social scams
- utility and home-improvement scams

Each hub should explain the category's distinct patterns, provide a decision tree or comparison, cite current aggregate evidence, and route users to the smallest relevant set of guides. A hub should not be a longer keyword list.

### 7. Strengthen claim-to-source coverage

The corpus has 382 source references covering 291 unique URLs, including substantial GOV.UK, NCSC, FCA, PSR, Ofcom and police material. However:

- 90 guides have only one listed source.
- 60 have two.
- Seven guides combine fewer than 600 body/FAQ words with a single source.

One source can be sufficient for a narrow claim. It is not sufficient evidence for every legal, financial, recovery and organisation-specific claim on many YMYL pages.

Recommended implementation:

- Map sources to the individual sections or claims they support rather than showing only an undifferentiated source block.
- Prefer current primary sources; use secondary reporting only for context that has no primary publication.
- Record `checked_on` dates and an editorial reviewer for high-stakes claims.
- Preserve a visible correction history for material changes.
- Do not invent expert credentials. If an external legal, banking or fraud-prevention reviewer is added, identify the real person and scope of review.

Bing's current AI guidance also recommends clear structure, evidence and current claims:

https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview

### 8. Improve the shortest guides by intent, not by a word target

Article sections plus FAQs have:

- minimum: 366 words
- median: 873 words
- mean: 890 words
- maximum: 3,108 words
- 26 guides below 600 words
- 61 guides below 800 words

Google explicitly says it does not have a preferred word count. Do not bulk-pad these pages. Review whether the page completely solves its specific task, contains original evidence and deserves to exist separately:

https://developers.google.com/search/docs/fundamentals/creating-helpful-content

The highest-priority short/single-source reviews include `dhgate-scam-uk-review`, `glastonbury-accommodation-scam-uk`, `wedding-photographer-scam-uk`, `share-fraud-uk`, `student-finance-scam-uk`, `benefits-fraud-text-scam-uk` and `booking-com-scam-uk`.

### 9. Add evidence of first-hand editorial work

The trust shell is good, but many guides still read like text-only template outputs. Add useful, privacy-safe evidence where it materially helps:

- redacted real scam-message examples with the red flags annotated
- screenshots of official reporting flows, dated and checked for reuse permission
- small comparison tables for genuine versus scam contact patterns
- original charts from the site's UK scam statistics dataset
- concise “what changed” notes when organisations rebrand or reporting rules change
- a transparent explanation of how automation assists research and how a person checks claims

Google specifically encourages clear “Who, How and Why” information for automated or AI-assisted content and gives extra weight to trust on financial-safety topics:

https://developers.google.com/search/docs/fundamentals/creating-helpful-content

### 10. Use Search Console data to focus the next editorial cycle

Fresh 28-day baseline:

- clicks: 1
- impressions: 649
- CTR: 0.15%
- average position: 52.4

The most actionable near-page-one/page-two signals in the small sample are:

- NHS appointment scam guide: 26 impressions, average position 15.6
- bank verification codes guide: 9 impressions, average position 12.4
- scam checker: 8 impressions, average position 5.5
- About page: 12 impressions, average position 7.8
- homepage: 13 impressions, average position 2.3

Do not overfit to one- or two-impression queries. First improve the NHS and bank-code pages' originality, evidence, title/snippet fit and contextual links; then compare a clean 28-day period after recrawl.

The old `/mandate-fraud/` and BT support URLs still appear in Search Console, but the audited production redirects are correct `301`s. Keep the redirects, remove any remaining internal references, and request recrawl after related changes.

## P2 — technical and growth improvements

### 11. Keep the strong technical foundation

Fresh validation result:

> `OK — 228 HTML files; 226 indexable canonicals; 843 JSON-LD blocks; 0 broken local links`

Also confirmed:

- 185 records in `search.json`
- required `dist/index.html`, `dist/robots.txt` and `dist/_redirects` present
- correct canonical, H1 and meta description on every indexable page
- unique guide Open Graph images
- valid Article, Breadcrumb, WebPage and visible FAQ markup on sampled guides
- sitemap referenced in `robots.txt`
- `PerplexityBot` allowed through `User-agent: *` / `Allow: /`
- working IndexNow implementation and workflow
- no sampled browser-console errors
- no mobile horizontal overflow
- mobile menu and skip link work

Perplexity recommends allowing `PerplexityBot`, which the current wildcard rule already does:

https://docs.perplexity.ai/docs/resources/perplexity-crawlers

### 12. Treat special AI files and schema as secondary

The site publishes a 52 KB `llms.txt` and a roughly 1.06 MB `llms-full.txt`. They can remain available, but they are not a substitute for indexation, evidence or authority. Google states that AI Overviews and AI Mode use the same SEO foundations and require no special AI file or special schema:

https://developers.google.com/search/docs/appearance/ai-features

Likewise:

- `FAQPage` remains valid when it matches visible content, but Google normally shows FAQ rich results only for well-known government and health sites. Do not spend a major work cycle trying to increase FAQ schema volume: https://developers.google.com/search/blog/2023/08/howto-faq-changes
- `speakable` is a beta feature aimed at topical news answers on Google Assistant, not evidence of Gemini ranking. Keep it valid, but do not count it as a material AI-visibility advantage: https://developers.google.com/search/docs/appearance/structured-data/speakable

### 13. Preserve and monitor Bing/Copilot visibility correctly

The saved Bing Webmaster Tools export for 18 June–16 July 2026 reports:

- 11,481 citations
- 97 cited pages
- 118 sampled grounding queries
- average cited pages: 52.9 per day

This is encouraging coverage, but Bing explicitly says citation counts do not indicate page rank, authority, role or placement in an answer. It is not traffic or endorsement:

https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview

Keep:

- canonical-only XML sitemap with accurate `lastmod`
- deploy-time IndexNow submission for added, changed and removed URLs
- Bing Webmaster Tools indexing/recommendation monitoring
- evidence-backed headings, tables and concise answers

Bing's current guidance links these same foundations to Copilot and grounding eligibility:

https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a

### 14. Capture current field performance

The local payload is lean—the shared JavaScript is about 6.5 KB uncompressed and the sampled HTML is modest—but that does not prove Core Web Vitals.

After the PageSpeed quota resets:

1. Capture mobile PageSpeed/CrUX for the homepage, a guide, a category, `/check/` and the research page.
2. Record LCP, INP and CLS at the 75th percentile where field data exists.
3. Check the impact of Auto Ads and the CMP, not just the ad-free first render.
4. Re-test after any new article imagery.

### 15. Correct minor metadata/date hygiene

- The UK scam-statistics page's meta description is 220 characters; shorten it to a complete, specific search snippet.
- The research methodology title is 61 characters; this is low priority, but it can be tightened.
- Ten indexable guides lack `updated`: `chargeback-scam-uk`, `gumtree-scam-uk-guide`, `yodel-scam-text-messages`, `ups-delivery-scam-text-messages-uk`, `viagogo-scam-uk`, `holiday-club-scam-uk`, `cruise-scam-uk`, `facebook-dating-scam-uk`, `whatsapp-stranger-scam-uk`, `instagram-fake-giveaway-scam-uk`.
- Add an `updated` date only after a substantive editorial recheck. Do not change dates merely to simulate freshness.

## AdSense-specific findings

### What is already in good shape

- Live `ads.txt` returns the expected direct publisher record.
- Privacy, cookie, About, contact, corrections, methodology and other trust/legal pages are live.
- The scam checker and trust/legal pages do not contain ads.
- Across 185 guide pages, the generated policy is 159 default-ad pages, 23 non-personalised-ad pages and 3 no-ad pages.
- AI voice, sextortion and deepfake guides are ad-free; sensitive finance/identity/recovery/romance topics are treated more cautiously.
- The live ad code is present on monetised guide/category pages and absent from the homepage by design.
- Navigation is clear and works on desktop and mobile.

### What cannot be verified from the public site

Before resubmission, the owner must check inside AdSense:

- the exact rejection reason and Sites status
- duplicate-account or identity/payment verification issues
- Policy Centre issues
- invalid-traffic warnings
- the certified CMP's current UK/EEA configuration
- Auto Ads page exclusions and any Better Ads/Ad Experience warnings

Google reviews the whole site and may take two to four weeks:

https://support.google.com/adsense/answer/7584263?hl=en

## Recommended delivery sequence

### Week 1 — unblock accuracy and review safety

1. Obtain operator replies for Yodel and Halifax, then apply approved corrections and rebuild `dist/`.
2. Repair and test `fact_reverify.py`; make any remaining error fail the workflow.
3. Correct the TalkTalk gate canon and adjudicate the Companies House exact sender address.
4. Add a corpus-similarity check to the publishing gate.

### Weeks 2–3 — remove AdSense originality risk

1. Rewrite or consolidate the five pairs above 0.30.
2. Continue through all 14 pairs above 0.15.
3. Replace repeated recovery/reporting copy with concise unique guidance plus useful contextual links.
4. Re-run similarity, factual, source and generated-site validation.

### Weeks 3–5 — improve organic architecture

1. Create the highest-value 8–10 missing category hubs.
2. Build contextual links so every priority guide has a useful inbound path.
3. Strengthen claim-level citations on single-source YMYL pages.
4. Improve the NHS and bank-code near-miss pages from Search Console.

### Weeks 5–8 — grow authority

1. Turn the original UK scam-statistics dataset into citeable charts, downloadable tables and quarterly briefs.
2. Conduct source-relevant outreach to consumer journalists, charities, councils, libraries, banks and digital-safety organisations.
3. Capture Search Console Links and Bing inbound-link data; this audit did not have a dependable third-party backlink index.
4. Monitor Google clicks/impressions, Bing/Copilot citations and real referral sessions separately.

## Resubmission checklist

Do not request another AdSense review until all P0 boxes are complete.

- [ ] Two confirmed factual corrections approved, applied and rebuilt
- [ ] Quarterly fact checker fails closed and passes full-corpus verification
- [ ] TalkTalk false positive fixed; Companies House exact mailbox evidenced or removed
- [ ] All article pairs above 0.15 reviewed; highest-similarity families rewritten or consolidated
- [ ] Corpus-similarity check added to publication gate
- [ ] Contextual link plan implemented for priority clusters
- [ ] At least the highest-value missing category hubs completed
- [ ] Current mobile PageSpeed/CWV captured with ads and CMP active
- [ ] AdSense Sites status, Policy Centre, duplicate-account status, CMP and page exclusions checked
- [ ] Clean build and generated-site validation passed; regenerated `dist/` committed

## Bottom line

The website does not need more schema, more generic articles or an arbitrary word-count expansion. It needs fewer template-like passages, stronger claim-level evidence, a fact-check workflow that cannot silently fail, and a clearer topic/link architecture. Those changes are the shortest path to a credible AdSense resubmission and to better visibility in Google, Bing, Gemini, Copilot and Perplexity.
