// node --test netlify/functions/lib/
//
// Pins the checker's inseparable Report Fraud / Police Scotland pair.
//
// The bug this suite exists for: two caps in sequence (`slice(0, 6)` then
// `slice(0, 5)`) meant a Report Fraud link in the FIFTH position had Police
// Scotland spliced in at index 6 and discarded by the final cap, shipping an
// unpaired Report Fraud link that reads as the UK-wide route (operator review,
// 2026-07-29, `hubs-v10-c.md` §3). Every test below therefore exercises Report
// Fraud at every input position, including five- and six-link results.

const test = require("node:test");
const assert = require("node:assert");

const { buildReportingLinks, MAX_REPORTING_LINKS } = require("./reporting-links");
const { REPORT_FRAUD_LINK, POLICE_SCOTLAND_LINK } = require("./canon-routes");

// Stand-ins for check-scam.js's own helpers. The allow-list and the scrubber
// are tested where they live; here they only need to be faithful enough that
// the pairing logic sees realistic input.
const ALLOWED = [
  "gov.uk", "police.uk", "fca.org.uk", "citizensadvice.org.uk", "which.co.uk",
  "ofcom.org.uk", "ico.org.uk", "moneyhelper.org.uk", "victimsupport.org.uk",
  "cifas.org.uk", "stepchange.org", "nationaldebtline.org",
];
const isAllowedReportUrl = (raw) => {
  let u;
  try { u = new URL(raw); } catch { return false; }
  if (u.protocol !== "https:") return false;
  const h = u.hostname.toLowerCase();
  return ALLOWED.some(d => h === d || h.endsWith("." + d));
};
const scrubContact = (s) => s;

const FILLER = [
  { name: "FCA Register", url: "https://www.fca.org.uk/register" },
  { name: "Citizens Advice", url: "https://www.citizensadvice.org.uk/consumer/" },
  { name: "Ofcom", url: "https://www.ofcom.org.uk/scam-calls" },
  { name: "ICO", url: "https://ico.org.uk/make-a-complaint/" },
  { name: "MoneyHelper", url: "https://www.moneyhelper.org.uk/en" },
  { name: "Cifas", url: "https://www.cifas.org.uk/pr" },
  { name: "StepChange", url: "https://www.stepchange.org/" },
];

const REPORT_FRAUD_INPUT = { name: "Action Fraud", url: "https://www.actionfraud.police.uk" };

const urls = (links) => links.map(l => l.url);
const hasPair = (links) =>
  urls(links).includes(REPORT_FRAUD_LINK.url) && urls(links).includes(POLICE_SCOTLAND_LINK.url);

// ── The regression: Report Fraud at every position, every result length ──────

for (let total = 1; total <= 8; total++) {
  for (let position = 0; position < total; position++) {
    test(`Report Fraud at position ${position + 1} of ${total} keeps the Scottish route`, () => {
      const raw = FILLER.slice(0, total - 1);
      raw.splice(position, 0, { ...REPORT_FRAUD_INPUT });
      const out = buildReportingLinks(raw, isAllowedReportUrl, scrubContact);

      assert.ok(out.length <= MAX_REPORTING_LINKS,
        `returned ${out.length} links, cap is ${MAX_REPORTING_LINKS}`);
      assert.ok(hasPair(out),
        `unpaired Report Fraud shipped: ${JSON.stringify(urls(out))}`);

      // The pair must be adjacent, so the two routes read as one instruction.
      const i = urls(out).indexOf(REPORT_FRAUD_LINK.url);
      const j = urls(out).indexOf(POLICE_SCOTLAND_LINK.url);
      assert.strictEqual(j, i + 1, "Police Scotland must sit immediately after Report Fraud");
    });
  }
}

// ── Everything else ──────────────────────────────────────────────────────────

test("a full five-link result with Report Fraud last still pairs", () => {
  const raw = [...FILLER.slice(0, 4), { ...REPORT_FRAUD_INPUT }];
  const out = buildReportingLinks(raw, isAllowedReportUrl, scrubContact);
  assert.strictEqual(out.length, MAX_REPORTING_LINKS);
  assert.ok(hasPair(out));
});

test("a six-link result with Report Fraud fifth still pairs", () => {
  const raw = [...FILLER.slice(0, 4), { ...REPORT_FRAUD_INPUT }, FILLER[4]];
  const out = buildReportingLinks(raw, isAllowedReportUrl, scrubContact);
  assert.strictEqual(out.length, MAX_REPORTING_LINKS);
  assert.ok(hasPair(out));
});

test("actionfraud.police.uk is rewritten to the Report Fraud canon link and label", () => {
  const out = buildReportingLinks([{ ...REPORT_FRAUD_INPUT }], isAllowedReportUrl, scrubContact);
  assert.strictEqual(out[0].url, REPORT_FRAUD_LINK.url);
  assert.strictEqual(out[0].name, REPORT_FRAUD_LINK.name);
});

test("the canon labels carry their geography", () => {
  assert.match(REPORT_FRAUD_LINK.name, /England, Wales and Northern Ireland/);
  assert.match(POLICE_SCOTLAND_LINK.name, /Scotland/);
});

test("both spellings of Report Fraud collapse to one slot", () => {
  const raw = [
    { name: "Action Fraud", url: "https://www.actionfraud.police.uk" },
    { name: "Report Fraud", url: "https://www.reportfraud.police.uk" },
    ...FILLER.slice(0, 3),
  ];
  const out = buildReportingLinks(raw, isAllowedReportUrl, scrubContact);
  assert.strictEqual(urls(out).filter(u => u === REPORT_FRAUD_LINK.url).length, 1);
  assert.ok(hasPair(out));
});

test("an already-paired result is left alone and not duplicated", () => {
  const raw = [
    { name: "Report Fraud", url: "https://www.reportfraud.police.uk" },
    { name: "Police Scotland", url: "https://www.scotland.police.uk/contact-us/non-emergencies/" },
    ...FILLER.slice(0, 2),
  ];
  const out = buildReportingLinks(raw, isAllowedReportUrl, scrubContact);
  assert.strictEqual(urls(out).filter(u => u === POLICE_SCOTLAND_LINK.url).length, 1);
  assert.strictEqual(out.length, 4);
});

test("Police Scotland alone is not forced to carry Report Fraud", () => {
  const raw = [{ name: "Police Scotland", url: "https://www.scotland.police.uk/contact-us/non-emergencies/" }];
  const out = buildReportingLinks(raw, isAllowedReportUrl, scrubContact);
  assert.deepStrictEqual(urls(out), [POLICE_SCOTLAND_LINK.url]);
});

test("no Report Fraud link means no insertion", () => {
  const out = buildReportingLinks(FILLER.slice(0, 3), isAllowedReportUrl, scrubContact);
  assert.strictEqual(urls(out).includes(POLICE_SCOTLAND_LINK.url), false);
});

test("attacker-controlled and non-https hosts are dropped before pairing", () => {
  const raw = [
    { name: "Claim your refund", url: "https://evil.example.com/refund" },
    { name: "Insecure", url: "http://www.reportfraud.police.uk" },
    { name: "Not a URL", url: "javascript:alert(1)" },
    { ...REPORT_FRAUD_INPUT },
  ];
  const out = buildReportingLinks(raw, isAllowedReportUrl, scrubContact);
  assert.deepStrictEqual(urls(out), [REPORT_FRAUD_LINK.url, POLICE_SCOTLAND_LINK.url]);
});

test("non-array and empty input return an empty list", () => {
  for (const bad of [undefined, null, "links", 42, {}]) {
    assert.deepStrictEqual(buildReportingLinks(bad, isAllowedReportUrl, scrubContact), []);
  }
  assert.deepStrictEqual(buildReportingLinks([], isAllowedReportUrl, scrubContact), []);
});

test("a scrubbed link label is truncated after scrubbing, not before", () => {
  const redact = (s) => s.replace(/\d{7,}/g, "[removed]");
  const raw = [{ name: "Call 07700900123 now — " + "x".repeat(200), url: "https://www.fca.org.uk/register" }];
  const out = buildReportingLinks(raw, isAllowedReportUrl, redact);
  assert.ok(!/\d{7,}/.test(out[0].name));
  assert.ok(out[0].name.length <= 120);
});
