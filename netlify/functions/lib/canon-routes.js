// GENERATED FILE — DO NOT EDIT BY HAND.
//
// Rendered from content/sources.json by scripts/sync_canon_js.py. The canon is
// the single source of truth for every reporting route on this site; this
// module is how the Netlify Functions read it. Edit content/sources.json and
// re-run the script. `scripts/sync_canon_js.py --check` runs in the offline
// self-test, so a stale copy fails CI.

const REPORT_FRAUD_LINK = {
  "url": "https://www.reportfraud.police.uk",
  "name": "Report Fraud — England, Wales and Northern Ireland"
};

const POLICE_SCOTLAND_LINK = {
  "url": "https://www.scotland.police.uk/contact-us/non-emergencies/",
  "name": "Police Scotland on 101 — Scotland"
};

// Hosts that canonicalise to each of the pair, so a model-emitted variant
// (actionfraud.police.uk, a bare host, a deep link) resolves to the approved label.
const REPORT_FRAUD_HOSTS = [
  "actionfraud.police.uk",
  "reportfraud.police.uk"
];

const POLICE_SCOTLAND_HOSTS = [
  "scotland.police.uk"
];

// Every host serving an on_page canon route. check-scam.js unions these into
// its security allow-list, so a required reporting route can never be filtered
// out of a checker result — www.advice.scot was, silently, until 2026-07-30.
const CANON_REQUIRED_HOSTS = [
  "www.advice.scot",
  "www.citizensadvice.org.uk",
  "www.ncsc.gov.uk",
  "www.nidirect.gov.uk",
  "www.reportfraud.police.uk",
  "www.scotland.police.uk"
];

// Every on_page canon report_url, so a test can assert each one survives.
const CANON_ONPAGE_URLS = [
  "https://www.advice.scot/",
  "https://www.citizensadvice.org.uk/consumer/scams/reporting-a-scam/",
  "https://www.ncsc.gov.uk/collection/phishing-scams",
  "https://www.nidirect.gov.uk/contacts/consumerline",
  "https://www.reportfraud.police.uk",
  "https://www.scotland.police.uk/contact-us/non-emergencies/"
];

const NCSC_REPORT_EMAIL = "report@phishing.gov.uk";

const SMS_SHORTCODE = "7726";

const EXAMPLE_REPORTING_LINKS = [
  {
    "url": "https://www.reportfraud.police.uk",
    "name": "Report Fraud — England, Wales and Northern Ireland"
  },
  {
    "url": "https://www.scotland.police.uk/contact-us/non-emergencies/",
    "name": "Police Scotland on 101 — Scotland"
  },
  {
    "url": "https://www.ncsc.gov.uk/collection/phishing-scams/report-scam-text-messages",
    "name": "Forward to 7726 (SMS spam)"
  }
];

const PROMPT_ROUTE_RULES = [
  "Police fraud reporting is NATION-SPECIFIC and both routes must be offered together. \"Report Fraud\" (https://www.reportfraud.police.uk, 0300 123 2040) covers England, Wales and Northern Ireland ONLY. A reader in Scotland, or reporting a crime that happened there, uses Police Scotland on 101 (https://www.scotland.police.uk/contact-us/non-emergencies/). Never present Report Fraud as the UK-wide route, and never give it without the Scottish alternative in the same list.",
  "Report Fraud replaced Action Fraud in December 2025 — never call it \"Action Fraud\" except as a parenthetical former name, and always link https://www.reportfraud.police.uk, never actionfraud.police.uk.",
  "Consumer advice is nation-specific too: Citizens Advice in England and Wales, Advice Direct Scotland in Scotland, or Consumerline in Northern Ireland. Never present Citizens Advice as a UK-wide helpline."
];

module.exports = {
  REPORT_FRAUD_LINK,
  POLICE_SCOTLAND_LINK,
  REPORT_FRAUD_HOSTS,
  POLICE_SCOTLAND_HOSTS,
  NCSC_REPORT_EMAIL,
  SMS_SHORTCODE,
  EXAMPLE_REPORTING_LINKS,
  PROMPT_ROUTE_RULES,
  CANON_REQUIRED_HOSTS,
  CANON_ONPAGE_URLS,
};
