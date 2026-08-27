// node --test netlify/functions/lib/
//
// scrubContact() redacts contact details a prompt-injected message could
// plant in the checker's model-authored narrative text. It had zero test
// coverage until a manual scan (2026-08-27) found two real bypasses — this
// suite pins the fix and guards against the class of bug recurring.

const test = require("node:test");
const assert = require("node:assert");

const { scrubContact, SAFE_SHORTCODES } = require("./scrub-contact");

const REDACTED_CONTACT = "[contact removed — verify via an official source]";
const REDACTED_LINK = "[link removed — verify via an official source]";
const REDACTED_NUMBER = "[number removed — use the number on your card or the official website]";

// ── Baseline redaction still works ────────────────────────────────────────

test("a plain email is redacted", () => {
  assert.strictEqual(scrubContact("contact scammer@fake-support.com now"),
    `contact ${REDACTED_CONTACT} now`);
});

test("an official gov.uk email survives", () => {
  const s = "forward it to phishing@hmrc.gov.uk";
  assert.strictEqual(scrubContact(s), s);
});

test("a scheme link is redacted", () => {
  assert.strictEqual(scrubContact("visit https://evil-fraudhelp.example/pay"),
    `visit ${REDACTED_LINK}`);
});

test("a bare official host mention survives", () => {
  const s = "report it at reportfraud.police.uk today";
  assert.strictEqual(scrubContact(s), s);
});

test("a bare non-official host mention is redacted", () => {
  assert.strictEqual(scrubContact("visit evil-fraudhelp.example for a refund"),
    `visit ${REDACTED_LINK} for a refund`);
});

test("a plain UK landline/mobile number is redacted", () => {
  assert.strictEqual(scrubContact("call 07911123456 now"), `call ${REDACTED_NUMBER} now`);
});

test("a formatted number with dashes/brackets is redacted", () => {
  // The regex matches from the leading digit, not the opening bracket — a
  // pre-existing quirk (unrelated to this fix), not a leak: no digits survive.
  assert.strictEqual(scrubContact("call (0791) 112-3456 now"), `call (${REDACTED_NUMBER} now`);
});

test("safety shortcodes are never redacted", () => {
  for (const code of SAFE_SHORTCODES) {
    const s = `call ${code} for help`;
    assert.strictEqual(scrubContact(s), s, `${code} should survive`);
  }
});

// ── Bypasses found 2026-08-27 — now fixed ─────────────────────────────────

test("a fully space-separated phone number is redacted", () => {
  assert.strictEqual(scrubContact("call 0 7 9 1 1 1 2 3 4 5 6 now"), `call ${REDACTED_NUMBER} now`);
});

test("an email spaced around @ and . is redacted", () => {
  assert.strictEqual(scrubContact("email scammer @ fake-support . com now"),
    `email ${REDACTED_CONTACT} now`);
});

test("an email obfuscated with (at)/(dot) is redacted", () => {
  assert.strictEqual(scrubContact("email scammer(at)fake-support(dot)com"),
    `email ${REDACTED_CONTACT}`);
});

test("an email obfuscated with [at]/[dot] is redacted", () => {
  assert.strictEqual(scrubContact("email scammer[at]fake-support[dot]com"),
    `email ${REDACTED_CONTACT}`);
});

test("a long separator-heavy number no longer leaks trailing digits", () => {
  const out = scrubContact("call 0044 7911 123456 now");
  assert.strictEqual(out, `call ${REDACTED_NUMBER} now`);
  assert.ok(!/\d/.test(out), `trailing digits leaked: ${out}`);
});

// ── Normalisation stays narrow — ordinary prose is untouched ─────────────

test("ordinary prose with 'at' and periods is not mangled", () => {
  const s = "We arrived at the bank at 3pm. The scam claimed you owe £500.";
  assert.strictEqual(scrubContact(s), s);
});

test("a normal sentence-final period is not treated as email-shaped", () => {
  const s = "This message is a scam. Do not reply.";
  assert.strictEqual(scrubContact(s), s);
});

test("non-string input returns an empty string", () => {
  assert.strictEqual(scrubContact(null), "");
  assert.strictEqual(scrubContact(undefined), "");
  assert.strictEqual(scrubContact(42), "");
});
