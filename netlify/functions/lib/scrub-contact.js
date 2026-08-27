// netlify/functions/lib/scrub-contact.js
//
// Extracted from check-scam.js so it can be unit-tested (operator review,
// 2026-08-27 security audit) — this had zero test coverage while its sibling
// security modules (reporting-links, atomic-store) did, and that gap let two
// real bypasses ship silently until a manual scan caught them.
//
// The model's narrative fields (summary, flags, recommended_actions) are shown
// to the user as guidance. A prompt-injected message could try to plant an
// attacker-controlled phone number, link, or email there (reporting_links are
// separately host-allowlisted, but the free text is not). We redact contact
// details a victim might act on, while preserving the genuine UK reporting
// shortcodes (999/101/159/7726…) and official gov.uk reporting addresses.

const { ALLOWED_REPORT_DOMAINS } = require("./allowed-domains");

const SAFE_SHORTCODES = new Set(["999", "112", "101", "105", "111", "159", "7726"]);

// De-obfuscate the low-effort tricks a prompt-injected message can use to
// dodge contact-shaped regexes: spacing every character out ("0 7 9 1 1…",
// "user @ evil . com"), or spelling the separator ("user(at)evil(dot)com").
// This only COLLAPSES separators inside patterns that are already digit- or
// symbol-shaped — it never touches ordinary prose, so it can't over-redact.
function deobfuscate(s) {
  return s
    // "digit space" repeated 5+ times then a final digit — the only shape
    // that survives is a run where literally every digit is separated, which
    // ordinary prose never produces. Collapses to a plain digit run so the
    // phone regex below can see it as one number.
    .replace(/\b(?:\d[ \t]){5,}\d\b/g, m => m.replace(/[ \t]/g, ""))
    // "(at)" / "[at]" and "(dot)" / "[dot]" are unambiguous obfuscation
    // markers — never legitimate prose — safe to normalize unconditionally.
    .replace(/\s*[([]\s*at\s*[)\]]\s*/gi, "@")
    .replace(/\s*[([]\s*dot\s*[)\]]\s*/gi, ".")
    // A bare space on BOTH sides of "@" or "." is not standard English
    // punctuation (a sentence-ending period is followed, not preceded, by
    // whitespace), so collapsing it is safe and closes "user @ evil . com".
    .replace(/(\S)\s+@\s+(\S)/g, "$1@$2")
    .replace(/(\S)\s+\.\s+(\S)/g, "$1.$2");
}

function scrubContact(s) {
  if (typeof s !== "string") return "";
  return deobfuscate(s)
    // Emails: keep official *.gov.uk reporting addresses, redact everything else.
    .replace(/\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b/gi,
      m => /@([\w-]+\.)*gov\.uk$/i.test(m) ? m : "[contact removed — verify via an official source]")
    // Clickable-looking links (scheme / www. / host-with-path).
    .replace(/\b(?:https?:\/\/|www\.)\S+/gi, "[link removed — verify via an official source]")
    .replace(/\b[\w-]+(?:\.[\w-]+)+\/\S+/gi, "[link removed — verify via an official source]")
    // Bare host-like mentions with no scheme/www/path (e.g. "visit
    // evil-fraudhelp.example") matched neither rule above and survived as
    // plain, non-clickable — but still trusted-looking — narrative text. Redact
    // any domain-shaped token unless it resolves to a known official host
    // (the same allow-list that gates structured reporting links), so a
    // genuine "gov.uk" / "reportfraud.police.uk" mention stays readable.
    .replace(/\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b/gi, (m) => {
      const host = m.toLowerCase();
      return ALLOWED_REPORT_DOMAINS.some(d => host === d || host.endsWith("." + d))
        ? m : "[link removed — verify via an official source]";
    })
    // Dialable phone numbers (UK 0…, international +…, or "44…" written
    // without the + — an injection can drop the prefix to dodge the scrub).
    // Short safety codes are ≤4 digits and never start 0/+/44, so they
    // survive; full numbers are redacted. The interior-length cap is generous
    // (not open-ended, to bound worst-case regex work) — 12 was too tight and
    // left trailing digits of longer separator-heavy numbers unredacted
    // (e.g. "0044 7911 123456").
    .replace(/\+\d[\d\s().-]{6,25}\d|\b0\d[\d\s().-]{5,20}\d|\b44[\d\s().-]{8,25}\d/g, (m) => {
      const digits = m.replace(/\D/g, "");
      return (digits.length < 7 || SAFE_SHORTCODES.has(digits))
        ? m : "[number removed — use the number on your card or the official website]";
    });
}

module.exports = { scrubContact, SAFE_SHORTCODES };
