// netlify/functions/lib/allowed-domains.js
//
// The security allow-list for model-produced reporting links, extracted from
// check-scam.js so it can be unit-tested against the canon.
//
// The checker renders model-produced reporting links as trusted guidance, so a
// prompt-injected message could otherwise smuggle an attacker-controlled URL
// into the UI. We only forward links whose host is (or is a subdomain of) an
// official UK reporting/consumer-protection domain. Base domains cover their
// subdomains: e.g. "police.uk" allows actionfraud./reportfraud./met.police.uk,
// and "gov.uk" allows ncsc./nationalcrimeagency.gov.uk.
//
// CANON_REQUIRED_HOSTS is unioned in below: every host serving an on_page route
// in content/sources.json. www.advice.scot is a required consumer-advice route
// and was NOT in this hand-maintained list, so a valid Advice Direct Scotland
// link was silently discarded from checker results (operator review,
// 2026-07-30). The security allow-list stays broader than the canon — it also
// covers Which?, Ofcom, the ombudsmen and the debt charities — but it can no
// longer be NARROWER than the routes the site is required to offer.

const { CANON_REQUIRED_HOSTS } = require("./canon-routes");

const ALLOWED_REPORT_DOMAINS = [
  // Generated from content/sources.json: every host serving an on_page route.
  // The list may be BROADER than the canon; it may never be narrower.
  ...CANON_REQUIRED_HOSTS,
  "gov.uk",
  "police.uk",
  "fca.org.uk",
  "citizensadvice.org.uk",
  "which.co.uk",
  "ofcom.org.uk",
  "ico.org.uk",
  "takefive-stopfraud.org.uk",
  "moneyhelper.org.uk",
  "victimsupport.org.uk",
  "cifas.org.uk",
  "financial-ombudsman.org.uk",
  "pensions-ombudsman.org.uk",
  "stepchange.org",
  "nationaldebtline.org",
];

function isAllowedReportUrl(raw) {
  let u;
  try {
    u = new URL(raw);
  } catch {
    return false;
  }
  if (u.protocol !== "https:") return false;
  const host = u.hostname.toLowerCase();
  return ALLOWED_REPORT_DOMAINS.some(d => host === d || host.endsWith("." + d));
}

module.exports = { ALLOWED_REPORT_DOMAINS, isAllowedReportUrl };
