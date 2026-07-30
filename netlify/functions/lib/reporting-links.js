// netlify/functions/lib/reporting-links.js
//
// Builds the checker's `reporting_links` from the model's raw output.
//
// Extracted from check-scam.js so the pairing rule is testable. The previous
// inline version applied TWO caps — `safeLinks.slice(0, 6)` and then
// `reporting_links: safeLinks.slice(0, 5)` — so a Report Fraud link occupying
// the fifth position had Police Scotland spliced in at index 6 and immediately
// discarded by the final cap. The function could therefore still ship an
// unpaired Report Fraud link, which is exactly the geography failure the
// deterministic insert exists to prevent (operator review, 2026-07-29,
// `hubs-v10-c.md` §3).
//
// The rule now is: normalise, deduplicate, RESERVE capacity for the pair, then
// apply ONE final cap.

const {
  REPORT_FRAUD_LINK,
  POLICE_SCOTLAND_LINK,
  REPORT_FRAUD_HOSTS,
  POLICE_SCOTLAND_HOSTS,
} = require("./canon-routes");

const MAX_REPORTING_LINKS = 5;

function hostOf(url) {
  try {
    return new URL(url).hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    return null;
  }
}

// The model's training data predates the Dec 2025 Action Fraud → Report Fraud
// rebrand, so it still emits actionfraud.police.uk links and "Action Fraud"
// naming. Rewrite both deterministically rather than relying on the prompt.
// The approved label carries the GEOGRAPHY: "Report Fraud (Police)" reads as a
// UK-wide route and strands a Scottish reader on a self-contained action link.
function canonicalise(link) {
  const host = hostOf(link.url);
  if (host === null) return link;
  if (REPORT_FRAUD_HOSTS.includes(host)) return { ...REPORT_FRAUD_LINK };
  if (POLICE_SCOTLAND_HOSTS.includes(host)) return { ...POLICE_SCOTLAND_LINK };
  return link;
}

/**
 * @param {unknown} rawLinks         the model's `reporting_links`
 * @param {(url: string) => boolean} isAllowedReportUrl  host allow-list check
 * @param {(text: string) => string} scrubContact        free-text redaction
 * @returns {{url: string, name: string}[]}
 */
function buildReportingLinks(rawLinks, isAllowedReportUrl, scrubContact) {
  if (!Array.isArray(rawLinks)) return [];

  // 1. Normalise: allow-list the host, canonicalise the pair, scrub the label.
  //    scrubContact runs BEFORE the length cap so a redaction match cannot be
  //    truncated away by the slice.
  const normalised = rawLinks
    .filter(l => l && typeof l.url === "string" && isAllowedReportUrl(l.url))
    .map(canonicalise)
    .map(l => ({ url: l.url, name: scrubContact(String(l.name || "")).slice(0, 120) }));

  // 2. Deduplicate by URL. Canonicalisation collapses actionfraud.police.uk and
  //    reportfraud.police.uk onto one link, so a model that emitted both would
  //    otherwise spend two of the five slots on the same destination.
  const seen = new Set();
  const links = [];
  for (const l of normalised) {
    if (seen.has(l.url)) continue;
    seen.add(l.url);
    links.push(l);
  }

  // 3. Reserve capacity for the pair BEFORE capping, by HOISTING it to the
  //    front. Inserting Police Scotland next to Report Fraud in place is not
  //    enough: when the model returns six or more links and Report Fraud is
  //    fifth or later, Report Fraud itself sits at or beyond the cap, so the
  //    partner is trimmed no matter where it is spliced in. Reserving a slot by
  //    dropping one other link has the same hole. Only pinning both to slots 0
  //    and 1 makes "never unpaired" true at every input position and length —
  //    which is the right priority anyway: the police route is the primary UK
  //    reporting action, and the model's ordering of the remaining links
  //    carries no editorial weight.
  const at = links.findIndex(l => l.url === REPORT_FRAUD_LINK.url);
  if (at !== -1) {
    const rest = links.filter(
      l => l.url !== REPORT_FRAUD_LINK.url && l.url !== POLICE_SCOTLAND_LINK.url
    );
    links.length = 0;
    links.push({ ...REPORT_FRAUD_LINK }, { ...POLICE_SCOTLAND_LINK }, ...rest);
  }

  // 4. ONE cap. The second `slice(0, 5)` that used to run on the result is what
  //    discarded the Scottish route; there is now exactly one place a link can
  //    be dropped, and step 3 guarantees the pair is never in it.
  return links.slice(0, MAX_REPORTING_LINKS);
}

module.exports = { buildReportingLinks, MAX_REPORTING_LINKS, hostOf };
