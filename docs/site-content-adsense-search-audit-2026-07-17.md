# Beat the Scam: content, AdSense, search and AI-discovery audit

**Audit date:** 17 July 2026
**Scope:** the current source corpus, generated site and live production site. Previous audit documents were deliberately not used.

## Remediation update — 18 July 2026

The immediate technical and factual blockers identified below have now been addressed in the source and rebuilt site:

- corrected the DPD, online-retailer, PayPal, APP reimbursement, Section 75 and Amazon claims;
- expanded the deterministic content gate so those unsafe formulations cannot silently return;
- replaced the broad public fact-check promise with an accurate description of the implemented checks and removed inferred self-review schema;
- removed advertising from the homepage and author page, and added `noindex,follow` plus ad suppression to the 12 thin guides pending substantive editorial work;
- consolidated the Hermes guide into the Evri guide with a permanent redirect;
- reduced article keyword chips and made ambiguous auto-link phrases require an explicit canonical owner;
- published a corrections policy and material-corrections log at `/corrections/`;
- tested consent persistence and reopening in a clean local browser session, including a 390px mobile viewport;
- rebuilt and crawled the generated site: zero broken internal references, valid JSON-LD, and exact sitemap/canonical parity across 204 indexable URLs.

The site should still not be resubmitted solely on the strength of these mechanical remediations. Two editorial/trust requirements remain: complete the bank and other high-overlap cluster rewrites with genuinely brand-specific evidence, and supply the operator's exact legal/controller name plus a suitable postal or service address. A full primary-source editorial pass across every retained guide remains the longer-running quality programme described below.

## Executive verdict

**Do not resubmit the site to AdSense yet.** The technical foundation is strong, but the editorial corpus presently creates a material “low-value / scaled content” risk and contains several high-impact factual overstatements. Those same weaknesses are also likely to limit organic growth and selection as a source in AI-generated answers.

The site is not far from being a credible publication. It has unusually good technical hygiene for a small static site: all indexable URLs are represented in the sitemap, canonicals are consistent, internal URLs resolve, structured data parses, security headers are strong, and the live desktop and mobile experience is clean. The issue is not basic SEO plumbing. It is whether each page demonstrates enough independent value, precision and accountable expertise to deserve indexing and monetisation.

### Readiness by area

| Area | Verdict | Main reason |
|---|---|---|
| Crawlability and indexation | Strong | Clean canonicals, robots, sitemap parity, no broken internal links |
| On-page technical SEO | Strong | Unique metadata, one H1 per page, valid JSON-LD, clear navigation |
| Content originality | High risk | Large repeated recovery blocks and clusters with 50–83% phrase overlap |
| Factual accuracy | High risk until corrections land | Several current primary sources contradict absolute statements on live guides |
| Trust / YMYL signals | Needs work | Transparent authorship, but no demonstrated consumer-fraud expert review and an overstated QA claim |
| AdSense policy readiness | Not ready | Thin/templated pages plus ads on the homepage and author page |
| Google/Bing growth | Constrained | Existing impressions show opportunity, but CTR and intent matching are weak |
| AI answer visibility | Constrained | Good crawl access, but insufficiently distinctive evidence and too much duplication |

No audit can guarantee AdSense approval or rankings. This report identifies the changes most likely to remove avoidable review risk and improve the site's evidence quality.

## What was audited

- All **182 guide records** across 17 categories in `content/posts.json`.
- All **218 generated HTML files**, comprising 217 indexable canonical URLs and the search surface.
- Titles, descriptions, headings, canonicals, robots directives, sitemap membership, structured data, internal links, assets and duplicate metadata.
- Guide length, cited-source count, claim patterns, repeated sentences and pairwise five-word phrase overlap across all 16,471 guide pairs.
- All **252 unique cited external URLs** with an automated response check. Bot-protected responses were not mislabelled as broken links.
- Live desktop and 390px mobile rendering of the homepage, representative long and short guides, methodology and author pages.
- Ad insertion rules, consent implementation, analytics, `ads.txt`, `robots.txt`, `llms.txt`, sitemap generation and IndexNow implementation.
- Current Google Search Console performance for the preceding 90 days.
- Targeted primary-source verification of legal, payments, courier, reporting, consumer-rights and platform claims most capable of causing harm.

This was a corpus-wide machine-assisted audit plus primary-source verification of high-risk claims. It is not a substitute for a solicitor or regulated financial professional reviewing every legal sentence.

## Critical corrections before AdSense review

### 1. DPD payment advice is factually unsafe

The live DPD guide says:

> “Genuine DPD delivery texts do not ask for payment by text.”

It also says a genuine DPD text “never asks for a fee.” DPD's current international support page says DPD may notify a recipient by SMS or email with a secure payment link where duties or taxes are due. A standard redelivery-fee text remains a common scam, but the guide's universal rule is false.

**Required replacement:** distinguish a standard redelivery fee from genuine import duties/taxes. Tell readers to avoid an unexpected message link and independently enter the parcel number through DPD's official site or app. Do not teach “any payment link equals fraud.”

**Page:** `/guides/dpd-delivery-scam-text/`
**Source:** [DPD international support](https://international.dpd.co.uk/support)

### 2. The website-checking guide treats incorporated-company signals as universal

The guide says a legitimate UK retailer publishes a registered company number, that a real retailer appears at Companies House with directors and filed accounts, that genuine retailers shoot their own photography, and that a genuine retailer responds within a working day.

Those are not universal tests. Sole traders are legitimate retailers but are not Companies House companies; a newly incorporated company will not have years of filed accounts; genuine retailers can use supplier photography; and response time is not a legal or reliable legitimacy threshold. The official distance-selling rules require business identity and contact information, not a company number in every case.

**Required replacement:** frame each as a contextual signal, not proof. Check Companies House only if the business claims to be a limited company. Add sole-trader and newly incorporated-business caveats. Remove the photography and one-working-day assertions unless supported by a defined study.

**Page:** `/guides/is-this-website-a-scam/`
**Source:** [GOV.UK online and distance selling rules](https://www.gov.uk/online-and-distance-selling-for-businesses/distance-selling)

### 3. PayPal's dispute deadline is oversimplified

The same guide tells readers to open a PayPal Goods and Services dispute “within 180 days.” PayPal's current UK Buyer Protection terms give 180 days for Item Not Received, but a Significantly Not as Described dispute must be opened by the earlier of 30 days after delivery or 180 days after payment.

**Required replacement:** state the two deadline rules and tell readers to check the Resolution Centre immediately rather than wait.

**Source:** [PayPal UK Buyer Protection terms](https://www.paypal.com/uk/legalhub/buyer-protection?locale.x=en_US)

### 4. APP reimbursement timing needs its full qualification

Multiple guides imply that an eligible victim is refunded within five business days unless gross negligence applies. The Payment Systems Regulator says firms normally have five business days, but they can stop the clock to request information and must reach an outcome within a maximum of 35 business days. Scope, exclusions, vulnerability rules, the possible excess and the £85,000 cap also matter.

**Required replacement:** create one maintained, source-backed APP component and use it everywhere. The short form should say “normally within five business days, but an investigation can extend the outcome to a maximum of 35 business days; eligibility and exclusions apply.”

**Source:** [PSR APP fraud reimbursement protections](https://www.psr.org.uk/information-for-consumers/app-fraud-reimbursement-protections/)

### 5. Two Section 75 formulations need correction

- The concert-ticket guide later describes the range as “£100 to £30,000.” The statutory cash price is **over £100** and no more than £30,000, subject to the debtor-creditor-supplier relationship and other conditions.
- The holiday-compensation guide says “card payments” in that range may qualify. Section 75 is not a generic card-payment protection; it applies to qualifying credit arrangements, commonly eligible credit-card purchases.

**Required replacement:** use “a qualifying credit purchase with a cash price over £100 and no more than £30,000,” followed by the relationship caveat. Keep chargeback separate and do not present it as a legal right.

**Pages:** `/guides/concert-ticket-scam-uk/`, `/guides/holiday-compensation-scam-uk/`

### 6. Amazon's “does not cold-call” claim is stronger than the cited evidence

The Amazon phone-call guide repeatedly says Amazon does not cold-call customers about orders, security or refunds. Amazon's published anti-scam guidance supports stronger, narrower statements: it will not ask for an OTP or confidential information by phone, and account/order details should be verified in the user's account. It does not support the blanket proposition that every unsolicited Amazon call is fraudulent.

**Required replacement:** “Treat an unexpected call as unverified. Hang up and check the order or message in your Amazon account; never provide an OTP, install remote-access software, buy gift cards or move money.”

**Source:** [Amazon UK suspicious-phone-call guidance](https://digprjsurvey.amazon.co.uk/csad/help/node/T3rnIphp327SSKYl8e)

### 7. The methodology promise exceeds what the quality gate demonstrates

The methodology page says the automated gate catches unconditional safety guarantees and every guide is fact-checked. The current deterministic audit detected only 11 claim items, while a separate corpus sweep found 491 instances of high-risk absolute wording across 149 guides. The false DPD rule passed the gate.

**Required action:** either improve the gate so it actually inventories and requires evidence for absolutes, amounts, deadlines, reporting routes, legislation and platform policies, or soften the public methodology claim. A review log should record reviewer, source, claim, verification date and next-review date. “Fact-checked” should mean a check that can be evidenced.

## Corpus-wide quality findings

### Thin and lightly sourced pages

Guide-specific section and FAQ text has a median of about **954 words**. However:

- 2 guides have fewer than 400 words;
- 12 have fewer than 500 words;
- 45 have fewer than 700 words;
- 113 have fewer than 1,000 words;
- 93 of 182 guides cite only one source.

Word count is not a ranking factor by itself. The risk is that several short pages are also formulaic and do not add reporting, screenshots, tested checks, examples, data or first-hand expertise.

**First thin-content queue:**

1. `printer-support-scam-uk` — 311 words
2. `paypal-friends-family-scam-uk` — 366
3. `microsoft-account-suspended-email-scam-uk` — 409
4. `aliexpress-scam-or-legit-uk-guide` — 433
5. `ceo-fraud-email-scam-uk` — 450, one source
6. `conveyancing-fraud-uk` — 471
7. `dhgate-scam-uk-review` — 475, one source
8. `companies-house-scam-letter-uk` — 490
9. `fake-wifi-hotspot-scam-uk` — 490
10. `council-housing-scam-uk` — 495, one source
11. `glastonbury-accommodation-scam-uk` — 496, one source
12. `talktalk-scam-call-uk` — 498

Before resubmission, either materially improve these pages with distinct evidence and examples, consolidate them into stronger guides, or temporarily `noindex` and remove ads from them. Padding them with more template prose is not a solution.

### Scaled repetition and search-intent cannibalisation

The audit found **67 exact sentences** used in at least three guides. The same APP reimbursement sentence appears in 65 guides; a closely related bank-transfer sentence appears in 64. Across all guide pairs:

- 711 pairs share at least 20% of the smaller guide's five-word phrases;
- 145 pairs share at least 25%;
- 50 pairs share at least 30%;
- 19 pairs share at least 40%;
- 9 pairs share at least 50%.

Highest-overlap examples include:

- Evri / Hermes parcel scams — 83%
- ASOS copycat / fake Ray-Ban — 80%
- fake Nike / ASOS copycat — 71%
- Monzo / Starling — 65%
- TSB / Nationwide — 63%
- Tinder / Bumble — 59%
- Lloyds / Halifax — 58%
- crypto investment / bitcoin — 49%

Some shared recovery instructions are appropriate, but the amount of repeated language makes the pages look like brand substitution at scale. It also makes it harder for Google, Bing and answer engines to determine which page is the canonical expert source for a question.

**Required action:**

1. Consolidate Hermes into the Evri guide with a redirect and a short historic-name section.
2. Decide a canonical page for every overlapping bank, marketplace, courier and fake-retailer intent.
3. Move universal recovery information into one authoritative recovery hub. On individual guides, summarise only the relevant steps and link to that hub.
4. Rewrite retained brand pages around genuinely brand-specific evidence: official sender domains/numbers, message examples, account-verification paths, fee policies and reporting channels.
5. Freeze publication of additional templated brand variants until the retained clusters are distinct.

### Keyword chips and internal linking

The mobile article header displays up to seven keyword-like chips before substantive content. They look search-engine-led and push the useful answer below the fold. Keep two or three reader-oriented labels at most.

The automatic internal-linker also assigns the phrase “remote access scam UK” to the ISP impersonation guide instead of the dedicated remote-access guide because duplicate keywords are resolved by first match. There are 33 duplicated keyword phrases, so this is unlikely to be the only wrong destination.

**Required action:** introduce an explicit canonical owner for duplicate anchor phrases, or exclude ambiguous keyword anchors from automatic linking. Add a build test asserting the expected destination for every duplicated phrase.

## AdSense readiness

Google's published guidance asks for original, high-quality content with clear navigation and warns against ads on low-value or navigation-focused screens. The site meets the navigation requirement but is exposed on content value.

Current generated ad placement:

- 184 of 218 HTML pages include AdSense.
- Most legal and trust pages are ad-free, which is good.
- The homepage and author page include ads.
- Three substantive category hubs include ads.
- Three sensitive AI/deepfake/sextortion guides are ad-free; several money-loss pages request non-personalised ads.

**Pre-review changes:**

1. Remove ads from the homepage and author page. The homepage is primarily a navigation/discovery screen; the author page is a trust disclosure. Neither needs to carry review risk.
2. Remove ads from every page below the quality threshold until it is rewritten.
3. Keep category ads only where the hub contains substantial unique editorial guidance, not just cards.
4. Avoid ads adjacent to urgent recovery actions, fraud reporting links or text that could be mistaken for a recommended service.
5. Review Auto ads settings and exclude trust, legal, checker and recovery-critical URLs.
6. Test the Google-certified consent message in a fresh UK/EEA browser profile. Confirm that reject is as easy as accept and that GA4/personalised-ad storage does not occur before consent. The persisted audit browser session could not prove first-visit behaviour.
7. Clarify the controller's legal identity in the privacy notice. “SideRight Apps” plus an email is present, but if it is a trading name, name the individual or registered entity behind it and provide a complete service/contact address appropriate to that entity.

Relevant policy sources: [AdSense eligibility](https://support.google.com/adsense/answer/9724?hl=en), [site readiness](https://support.google.com/adsense/answer/7299563?hl=en-EN), [approval problems](https://support.google.com/adsense/answer/81904?hl=en), and [publisher inventory value](https://support.google.com/adsense/answer/10502938?hl=en-GB).

## Search-engine findings

### Technical positives

- 217 sitemap URLs exactly match the 217 indexable canonical URLs.
- No duplicate title, description or canonical was found.
- No missing title, meta description, canonical or robots directive was found.
- Every HTML page has exactly one H1.
- All JSON-LD parsed successfully.
- No broken internal URL or missing referenced local asset was found.
- All 182 guides expose Article, FAQ and breadcrumb data; hub schema is also present.
- `ads.txt` contains the expected Google publisher record.
- `robots.txt` allows ordinary crawlers and does not block Google, Bing or Perplexity.
- Security headers include HSTS and a restrictive CSP.
- Desktop and 390px mobile layouts have no visible overflow or console errors in the tested pages.

FAQ schema is valid but should not be treated as a traffic strategy. Google stopped showing FAQ rich results on 7 May 2026 and removed the feature's documentation in June 2026. Keep an on-page FAQ only where it is useful to readers; retaining `FAQPage` markup may help non-Google consumers interpret the page, but it will not produce a Google FAQ rich result. Source: [Google Search documentation update](https://developers.google.com/search/updates#removing-faq-rich-result).

### Search Console evidence: opportunity with weak click capture

In the last 90 days the site received **50 clicks from 10,108 impressions**, a **0.49% CTR**, at an average position of **16.9**. This is enough data to show that the site is being discovered, but snippets and intent matching are underperforming.

Notable examples:

- “halifax text messages not arriving” — 1,744 impressions, 0 clicks, average position 4.1
- DPD guide — 1,957 impressions, 5 clicks, average position 11.3
- bank text-codes guide — 1,628 impressions, 4 clicks, average position 3.3
- Halifax guide — 809 impressions, 5 clicks, average position 13.3
- NHS appointment guide — 647 impressions, 12 clicks, average position 7.4
- DVLA vehicle-tax guide — 204 impressions, 0 clicks, average position 9.7

The Halifax query is informational/troubleshooting intent, not necessarily scam intent. The current page should either answer that legitimate non-arrival problem clearly and early, or stop targeting it. Rewriting a title to chase the query without satisfying it would worsen user signals.

**90-day search plan:**

1. Correct factual issues before changing titles.
2. Rewrite the top five impression pages around the actual query intent visible in Search Console.
3. Give each cluster one canonical intent and merge overlapping pages.
4. Add original evidence: annotated scam-message examples, verified sender/domain tables, official process screenshots where permitted, and dated change logs.
5. Monitor legacy redirected slugs still appearing in Search Console and confirm their redirects, canonical targets and indexing state.
6. Run PageSpeed Insights or Lighthouse from an unthrottled environment before review. The public PSI API returned a quota error during this audit, so no score is claimed here.
7. Update the build/deploy process to submit changed URLs to IndexNow. The repository generates an IndexNow key file but contains no URL-submission request; a key file alone does not notify Bing.

Google's guidance emphasises people-first content, clear authorship and substantial original value. It also says generating many pages without added value can violate the scaled-content policy. Sources: [helpful content guidance](https://developers.google.com/search/docs/fundamentals/creating-helpful-content), [generative AI guidance](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content?hl=en), and [spam policies](https://developers.google.com/search/docs/essentials/spam-policies).

## Visibility in Gemini, Copilot, Perplexity and other answer engines

There is no reliable “AI SEO” switch. The durable requirements are crawlability, indexability, unique information, explicit evidence, stable entities and passages that can be confidently cited.

What already helps:

- Crawl access is open.
- Pages have stable canonicals and dates.
- Article/Breadcrumb schema is valid.
- The author and editorial process are disclosed.
- `llms.txt` exposes a readable site inventory for services that choose to use it. Google explicitly says an `llms.txt` file is not needed for Google Search and has no positive or negative effect on Google visibility or rankings.

What limits citation selection:

- Near-duplicate pages blur which URL is authoritative.
- Many pages rely on one source and then make claims beyond that source.
- Repeated generic recovery prose offers little reason to cite this site over the regulator or impersonated brand.
- The author page is transparent but does not establish consumer-protection, legal or financial subject-matter expertise.
- `reviewedBy` currently names the same author on modified articles, which can imply independent review where there is none.

**Required actions:**

1. Omit `reviewedBy` unless another named person genuinely reviewed the page. If an expert reviews it, publish their qualifications and review scope.
2. Build a small advisory/reviewer panel for legal, banking and cyber claims, or restrict each page to clearly sourced educational guidance.
3. Put a dated “verified facts” table on brand pages: claim, current official answer, official source, checked date.
4. Add primary evidence and state uncertainty explicitly. Answer engines favour passages that can be grounded, not confident unsupported prose.
5. Use Bing Webmaster Tools' IndexNow and AI Performance reports to see which URLs are cited and for which grounding queries.
6. Verify that Google's Search generative-AI control remains set to “Include” (the default, currently rolling out to a subset of owners). Google-Extended governs model training uses; it is not the switch for Google Search AI-feature grounding. Source: [Search generative AI control](https://support.google.com/webmasters/answer/16908024?hl=en).
7. Keep PerplexityBot allowed. The current wildcard `Allow: /` already does this; no special rule is required.

Google states that normal SEO requirements apply to its AI features and that no special schema is needed: [Google AI features and your website](https://developers.google.com/search/docs/appearance/ai-features). Bing recommends accurate sitemaps, meaningful `lastmod` values and IndexNow for AI-powered discovery: [Bing on sitemaps and AI search](https://blogs.bing.com/webmaster/July-2025/Keeping-Content-Discoverable-with-Sitemaps-in-AI-Powered-Search). Bing also exposes citation and grounding-query data in [AI Performance](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview). Perplexity documents its crawler controls at [Perplexity crawlers](https://docs.perplexity.ai/docs/resources/perplexity-crawlers).

## Trust and legal surfaces

Positives:

- The author is named and the use of AI is disclosed.
- The site says it is educational, not legal or financial advice.
- Methodology, privacy, cookies, terms, disclaimer, contact and author pages exist.
- Sources and checked dates are visible on articles.
- Affiliate recommendations disclose that no commission is paid.

Improvements:

- Replace a broad “fact-checked” badge/claim with a review status that has an auditable record.
- Do not use the same author as `reviewedBy` merely because a guide was updated.
- Clarify the legal identity behind SideRight Apps and ensure controller contact details are complete.
- Publish a corrections policy and visible correction history for material changes.
- Explain how readers can submit a correction, and commit to a response target without presenting it as proof of legitimacy.
- Add a page-level “last verified” date separate from a cosmetic modification date.

The ICO says privacy information should identify the controller, give contact details, explain purposes/lawful bases, retention, recipients, transfers and rights. The current notice covers most substantive fields; the identity clarification is the main gap. Source: [ICO privacy-information requirements](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/what-privacy-information-should-we-provide/).

## External-source health

The corpus contains 252 unique cited external URLs. Automated checks returned:

- 208 normal HTTP 200 responses;
- 1 HTTP 202;
- 37 HTTP 403 bot-protection responses;
- 2 Amazon 503 bot responses;
- 1 UGG 406 response;
- 3 inconclusive transport/time-out results.

No normally responding citation was confirmed broken. The 44 protected or inconclusive URLs require a browser/manual recheck and should not be called broken solely from the status code. Add a scheduled citation checker that understands redirects and records “bot protected” separately from “broken.”

## Prioritised implementation sequence

### Blockers — complete before AdSense resubmission

1. Correct the DPD, website-checking, PayPal, APP, Section 75 and Amazon claims above.
2. Change the methodology promise or make the fact-check gate match it.
3. Remove ads from homepage, author and all thin/under-review guides.
4. Rewrite, merge or temporarily noindex the 12 sub-500-word guides.
5. Consolidate the highest-overlap clusters, starting with Hermes/Evri and the bank guides.
6. Test consent from a clean UK/EEA session and document the result.
7. Clarify the controller identity and publish a corrections policy.

### High-impact growth work — next 30 days

1. Rebuild the DPD, bank-text-codes, Halifax, NHS and DVLA pages around Search Console intent.
2. Fix ambiguous automatic internal links.
3. Add IndexNow submissions to the publish workflow.
4. Create a single maintained recovery hub and remove repeated long recovery blocks from brand guides.
5. Add page-level evidence tables and actual verified examples.

#### Growth implementation update — 18 July 2026

The five priority guides have now been rebuilt around their distinct query intent. The DPD, Halifax, NHS and DVLA pages answer the “is this genuine?” question without treating every message as fraudulent; the bank-code page now serves legitimate passcode-troubleshooting intent and points scam-intent users to the separate Halifax guide. Each page has newly checked primary sources and a page-specific evidence snapshot. Reconstructed examples are labelled as such and are not represented as messages received by the publisher.

A new ad-free `/recovery/` hub now owns the reusable post-scam actions, payment-route guidance, reporting routes and evidence-preservation checklist. Article emergency panels link to that maintained resource, and duplicated APP-fraud and identity-protection paragraphs were removed from the guide corpus. Controlled internal Markdown links were added so editorial links remain explicit instead of being inferred from ambiguous phrases.

IndexNow is integrated into the publish workflow. The submission script calculates added, changed and deleted public URLs from the Git change set, excludes current noindex pages, supports dry runs and retryable responses, and batches the result through the official IndexNow endpoint after pushes to `main`. The key-verification file is published at its declared location.

The rebuilt site now includes 169 published guides across 17 categories. Browser checks covered the recovery hub and all five priority guides at desktop and mobile widths; the recovery page remains ad-free, the guide evidence blocks render correctly, and the final 390px test reports no document overflow.

### Authority work — next 60–90 days

1. Obtain qualified review for high-stakes legal, financial and regulatory guidance.
2. Publish original datasets or recurring scam-message trend reports, with a transparent method.
3. Earn links and mentions from UK consumer, cyber-safety, local-authority and community organisations through useful research rather than generic outreach.
4. Use Bing AI Performance and Search Console to measure citations, queries, consolidation effects and CTR.

## Resubmission gate

Submit to AdSense only when all of the following are true:

- [ ] Every confirmed factual correction in this report is live.
- [ ] No ad is served on homepage, author, legal, checker or under-review/thin pages.
- [ ] The 12 thinnest pages have been improved, merged or noindexed.
- [ ] The largest duplicate clusters have one clear canonical intent.
- [ ] The public methodology accurately describes the implemented process.
- [ ] Every live article has enough primary sourcing for its material claims.
- [ ] The consent flow has passed a clean-session test before any non-essential storage.
- [ ] Controller identity and correction contact are unambiguous.
- [ ] A fresh crawl reports no internal errors, invalid schema or sitemap drift.
- [ ] A manual sample of at least one guide per category passes the same editorial checklist.

At that point the site will have a substantially stronger AdSense case and a better foundation for traditional search and AI citations. The next gains should come from consolidation, proof and original utility—not from publishing more pages.
