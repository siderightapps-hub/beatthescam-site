// netlify/functions/check-scam.js
// Proxies scam checker requests to the Anthropic Claude API.
// Set ANTHROPIC_API_KEY in your Netlify environment variables.

// ─── RATE LIMITING ───────────────────────────────────────────────────────────
// In-memory store — resets on cold start. Good enough for basic abuse prevention
// on a serverless function. Keyed by IP address.
const rateLimitStore = new Map();
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX        = 10;        // 10 requests per IP per minute

function isRateLimited(ip) {
  if (!ip) return false;
  const now  = Date.now();
  const entry = rateLimitStore.get(ip) || { count: 0, windowStart: now };

  // Reset window if expired
  if (now - entry.windowStart > RATE_LIMIT_WINDOW_MS) {
    entry.count       = 0;
    entry.windowStart = now;
  }

  entry.count++;
  rateLimitStore.set(ip, entry);

  // Prune old entries periodically to avoid memory leak
  if (rateLimitStore.size > 5000) {
    for (const [key, val] of rateLimitStore.entries()) {
      if (now - val.windowStart > RATE_LIMIT_WINDOW_MS * 2) {
        rateLimitStore.delete(key);
      }
    }
  }

  return entry.count > RATE_LIMIT_MAX;
}

// ─── DURABLE RATE LIMIT + DAILY SPEND CAP (Netlify Blobs) ─────────────────────
// The in-memory limiter above only protects a single warm instance and resets
// on cold start. Netlify Blobs gives a store shared across instances + restarts,
// so the per-IP limit and a global daily spend ceiling actually hold. Every
// Blobs call is guarded: if the store is unavailable the checker still works
// (per-IP falls back to the in-memory limiter; the spend cap fails open).
let getStore = null;
try { ({ getStore } = require("@netlify/blobs")); } catch { /* dep/runtime absent — degrade gracefully */ }

const crypto = require("crypto");

const DAILY_CALL_CAP = 2000; // max Anthropic checker calls per UTC day (abuse / cost guard; tune freely)

// Rate-limit keys are a salted HASH of the IP, never the raw address — so the
// limiter never persists a plaintext IP (the privacy policy promises as much).
// Prefer a dedicated RATE_LIMIT_SALT; otherwise reuse UNSUBSCRIBE_SECRET (already
// required site-wide), so the salt is always a real secret and never the public
// literal — without failing closed and taking the checker offline if it's unset.
const RL_SALT = process.env.RATE_LIMIT_SALT || process.env.UNSUBSCRIBE_SECRET || "bts-checker-rl-v1";
function rlKey(ip) {
  return "ip:" + crypto.createHash("sha256").update(RL_SALT + "|" + ip).digest("hex").slice(0, 32);
}

function blobStore(name) {
  if (!getStore) return null;
  try { return getStore({ name, consistency: "strong" }); }
  catch { return null; }
}

// Atomic read-modify-write on a Blobs key via compare-and-set (etag), so
// concurrent invocations can't clobber each other's increments and slip past a
// limit. Retries a few times under contention; on the final attempt falls back
// to an unconditional write so progress is still recorded. `mutate(cur)` returns
// the next value. Returns the stored value, or null if the store is unusable.
async function atomicUpdate(store, key, init, mutate) {
  for (let attempt = 0; attempt < 5; attempt++) {
    let cur = null, etag = null;
    try {
      const meta = await store.getWithMetadata(key, { type: "json" });
      if (meta) { cur = meta.data; etag = meta.etag; }
    } catch { /* treat as absent and try to create */ }
    const next = mutate(cur || init());
    const opts = etag ? { onlyIfMatch: etag } : { onlyIfNew: true };
    try {
      const res = await store.setJSON(key, next, opts);
      if (!res || res.modified !== false) return next;   // wrote successfully
      // res.modified === false → a racer wrote first; loop and retry with fresh etag
    } catch (e) {
      if (attempt === 4) { try { await store.setJSON(key, next); return next; } catch { return null; } }
    }
  }
  return null;
}

// Durable per-IP limiter. Returns true (limited) / false (ok), or null when the
// store is unavailable so the caller can fall back to the in-memory limiter.
async function durableRateLimited(ip) {
  const store = blobStore("checker-ratelimit");
  if (!store || !ip) return null;
  try {
    const now = Date.now();
    const next = await atomicUpdate(store, rlKey(ip),
      () => ({ count: 0, windowStart: now }),
      (cur) => {
        if (now - cur.windowStart > RATE_LIMIT_WINDOW_MS) { cur.count = 0; cur.windowStart = now; }
        cur.count++;
        return cur;
      });
    if (next === null) return null;   // store failed — caller falls back to in-memory
    return next.count > RATE_LIMIT_MAX;
  } catch (err) {
    console.error("Blobs rate-limit error (falling back to in-memory):", err);
    return null;
  }
}

// Global daily spend cap. Checks-and-increments today's call counter; returns
// true once the cap is reached (caller should refuse). Fails OPEN on store
// errors — the per-IP limit still applies, so availability wins over a perfect cap.
async function overDailyCap() {
  const store = blobStore("checker-spend");
  if (!store) return false;
  try {
    // calls:YYYY-MM-DD keyed on the UTC date: the cap resets at midnight UTC
    // (01:00/02:00 UK time), so a UK "day" deliberately spans two counters.
    const key = `calls:${new Date().toISOString().slice(0, 10)}`;
    const next = await atomicUpdate(store, key, () => ({ count: 0 }), (c) => { c.count++; return c; });
    if (next === null) return false;            // store failed — fail open (availability > perfect cap)
    return next.count > DAILY_CALL_CAP;
  } catch (err) {
    console.error("Blobs spend-cap error (failing open):", err);
    return false;
  }
}

// ─── ALLOWED MESSAGE TYPES ───────────────────────────────────────────────────
const ALLOWED_TYPES = new Set([
  "SMS or text message",
  "email",
  "phone call",
  "website or URL",
  "job offer",
  "social media message",
  "investment opportunity",
  "other message",
]);

// ─── ALLOWED ORIGINS ─────────────────────────────────────────────────────────
const ALLOWED_ORIGINS = [
  "https://beatthescam.com",
  "https://www.beatthescam.com",
];

function getAllowedOrigin(requestOrigin) {
  if (ALLOWED_ORIGINS.includes(requestOrigin)) return requestOrigin;
  return ALLOWED_ORIGINS[0]; // Default to primary domain
}

// ─── ALLOWED REPORTING DOMAINS ───────────────────────────────────────────────
// The checker renders model-produced reporting links as trusted guidance, so a
// prompt-injected message could otherwise smuggle an attacker-controlled URL
// into the UI. We only forward links whose host is (or is a subdomain of) an
// official UK reporting/consumer-protection domain. Base domains cover their
// subdomains: e.g. "police.uk" allows actionfraud./reportfraud./met.police.uk,
// and "gov.uk" allows ncsc./nationalcrimeagency.gov.uk.
const ALLOWED_REPORT_DOMAINS = [
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
  return ALLOWED_REPORT_DOMAINS.some(
    d => host === d || host.endsWith("." + d)
  );
}

// ─── SCRUB MODEL-AUTHORED FREE TEXT ──────────────────────────────────────────
// The model's narrative fields (summary, flags, recommended_actions) are shown
// to the user as guidance. A prompt-injected message could try to plant an
// attacker-controlled phone number, link, or email there (reporting_links are
// separately host-allowlisted, but the free text is not). We redact contact
// details a victim might act on, while preserving the genuine UK reporting
// shortcodes (999/101/159/7726…) and official gov.uk reporting addresses.
const SAFE_SHORTCODES = new Set(["999", "112", "101", "105", "111", "159", "7726"]);

function scrubContact(s) {
  if (typeof s !== "string") return "";
  return s
    // Emails: keep official *.gov.uk reporting addresses, redact everything else.
    .replace(/\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b/gi,
      m => /@([\w-]+\.)*gov\.uk$/i.test(m) ? m : "[contact removed — verify via an official source]")
    // Clickable-looking links (scheme / www. / host-with-path). Bare brand
    // mentions like "gov.uk" with no path stay as plain text.
    .replace(/\b(?:https?:\/\/|www\.)\S+/gi, "[link removed — verify via an official source]")
    .replace(/\b[\w-]+(?:\.[\w-]+)+\/\S+/gi, "[link removed — verify via an official source]")
    // Dialable phone numbers (UK 0…, international +…, or "44…" written
    // without the + — an injection can drop the prefix to dodge the scrub).
    // Short safety codes are ≤4 digits and never start 0/+/44, so they
    // survive; full numbers are redacted.
    .replace(/\+\d[\d\s().-]{6,}\d|\b0\d[\d\s().-]{5,12}\d|\b44[\d\s().-]{8,}\d/g, (m) => {
      const digits = m.replace(/\D/g, "");
      return (digits.length < 7 || SAFE_SHORTCODES.has(digits))
        ? m : "[number removed — use the number on your card or the official website]";
    });
}

// ─── HANDLER ─────────────────────────────────────────────────────────────────
exports.handler = async function(event) {
  const requestOrigin = event.headers["origin"] || event.headers["Origin"] || "";
  const allowedOrigin = getAllowedOrigin(requestOrigin);

  const corsHeaders = {
    "Access-Control-Allow-Origin":  allowedOrigin,
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Vary": "Origin",
    // Set here too — netlify.toml [[headers]] do not reliably reach function
    // responses on this site (Section 20 gotcha). no-store on EVERY response
    // (incl. errors/limits), so nothing here is ever cached.
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
  };

  // Handle preflight
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers: corsHeaders, body: "" };
  }

  if (event.httpMethod !== "POST") {
    return { statusCode: 405, headers: corsHeaders, body: "Method not allowed" };
  }

  // Enforce origin server-side: CORS headers only stop a *browser* from reading
  // the response — a non-browser client (curl, script, server) ignores them and
  // would still run up the Anthropic bill. Reject a present-but-unlisted Origin
  // outright. A missing Origin (same-origin posts, non-browser clients) is
  // allowed through; the per-IP limit and daily cap still bound it.
  if (requestOrigin && !ALLOWED_ORIGINS.includes(requestOrigin)) {
    return { statusCode: 403, headers: corsHeaders, body: JSON.stringify({ error: "Forbidden" }) };
  }

  // Rate limiting — check client IP
  // x-nf-client-connection-ip is set by Netlify's own edge and cannot be spoofed
  // by a caller; it takes priority over x-forwarded-for which can be forged.
  const clientIp =
    event.headers["x-nf-client-connection-ip"] ||
    event.headers["x-forwarded-for"]?.split(",")[0].trim() ||
    event.headers["x-real-ip"] ||
    event.requestContext?.identity?.sourceIp ||
    "";

  // Durable per-IP limit when Netlify Blobs is available; otherwise the
  // in-memory limiter. durableRateLimited() returns null when the store is down.
  const durable = await durableRateLimited(clientIp);
  const limited = durable === null ? isRateLimited(clientIp) : durable;
  if (limited) {
    return {
      statusCode: 429,
      headers: { ...corsHeaders, "Retry-After": "60" },
      body: JSON.stringify({ error: "Too many requests. Please wait a moment and try again." }),
    };
  }

  // Auth
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("ANTHROPIC_API_KEY not set");
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Service not configured" }),
    };
  }

  // Cap total body size BEFORE parsing — never allocate/parse a multi-MB payload
  // (field-length caps below only apply post-parse). 16KB >> the 3000-char cap.
  if ((event.body || "").length > 16 * 1024) {
    return { statusCode: 413, headers: corsHeaders, body: JSON.stringify({ error: "Request too large" }) };
  }

  // Parse and validate input
  let message, type;
  try {
    const body = JSON.parse(event.body);
    message = (body.message || "").trim().slice(0, 3000);
    const rawType = (body.type || "").replace(/[^a-zA-Z0-9 ]/g, "").slice(0, 100);
    type    = ALLOWED_TYPES.has(rawType) ? rawType : "other message";
  } catch {
    return {
      statusCode: 400,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Invalid request body" }),
    };
  }

  if (!message || message.length < 5) {
    return {
      statusCode: 400,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Message too short" }),
    };
  }

  // Global daily spend ceiling — refuse politely once the cap is reached, so a
  // burst of traffic from many IPs can't run up an unbounded Anthropic bill.
  if (await overDailyCap()) {
    return {
      statusCode: 503,
      headers: { ...corsHeaders, "Retry-After": "3600", "Content-Type": "application/json" },
      body: JSON.stringify({ error: "The free checker is very busy right now. Please try again later." }),
    };
  }

  const SYSTEM = `You are a UK consumer protection expert specialising in scam detection. You help ordinary people decide whether a message, email, URL, phone call, or job offer is likely to be fraudulent.

Analyse the provided content and respond ONLY with a valid JSON object — no markdown fences, no preamble, no trailing text. Use exactly this structure:

{
  "verdict": "likely_scam" | "possibly_scam" | "probably_legitimate" | "unclear",
  "confidence": "high" | "medium" | "low",
  "summary": "One clear sentence summarising your finding.",
  "red_flags": ["Specific red flag 1", "Specific red flag 2"],
  "green_flags": ["Reassuring sign 1"],
  "recommended_actions": ["Specific action 1", "Specific action 2", "Specific action 3"],
  "reporting_links": [
    {"name": "Report Fraud — England, Wales and Northern Ireland", "url": "https://www.reportfraud.police.uk"},
    {"name": "Police Scotland on 101 — Scotland", "url": "https://www.scotland.police.uk/contact-us/non-emergencies/"},
    {"name": "Forward to 7726 (SMS spam)", "url": "https://www.ncsc.gov.uk/collection/phishing-scams/report-scam-text-messages"}
  ]
}

Rules:
- Police fraud reporting is NATION-SPECIFIC and both routes must be offered together. "Report Fraud" (reportfraud.police.uk, 0300 123 2040) covers England, Wales and Northern Ireland ONLY. A reader in Scotland, or reporting a crime that happened there, uses Police Scotland on 101 (scotland.police.uk). Never present Report Fraud as the UK-wide route, and never give it without the Scottish alternative in the same list.
- Report Fraud replaced Action Fraud in December 2025 — never call it "Action Fraud" except as a parenthetical former name, and always link https://www.reportfraud.police.uk, never actionfraud.police.uk.
- Consumer advice is nation-specific too: Citizens Advice covers England and Wales, Advice Direct Scotland covers Scotland, Consumerline covers Northern Ireland. Never present Citizens Advice as a UK-wide helpline.
- red_flags and green_flags must be specific to the content provided, not generic.
- recommended_actions must be concrete and actionable, not generic advice.
- reporting_links should include only UK-relevant links appropriate to the scam type.
- If verdict is probably_legitimate, red_flags may be empty but still list any minor concerns.
- Always include at least one recommended_action even for legitimate messages.
- Do not output anything outside the JSON object.`;

  // Bound the upstream call so a hung Anthropic connection can't pin the function
  // open until the platform's hard timeout. AbortController → 504 below.
  const ac = new AbortController();
  const upstreamTimeout = setTimeout(() => ac.abort(), 20000);
  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      signal: ac.signal,
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-haiku-4-5-20251001",
        max_tokens: 1024,
        system: SYSTEM,
        messages: [
          {
            role: "user",
            content: `Please analyse this ${type}:\n\n${message}`,
          },
        ],
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      console.error("Anthropic API error:", response.status, err);
      return {
        statusCode: 502,
        headers: corsHeaders,
        body: JSON.stringify({ error: "Upstream API error" }),
      };
    }

    const data = await response.json();
    const text = (data.content || []).find(b => b.type === "text")?.text || "";

    // Strip markdown code fences if Claude wraps the response
    const clean = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim();

    let parsed;
    try {
      parsed = JSON.parse(clean);
    } catch {
      // Do NOT log `text` — model output can echo user-submitted content, which
      // would contradict the "not stored" promise. Log only a non-sensitive shape.
      console.error("Claude returned non-JSON (len=%d)", text.length);
      return {
        statusCode: 502,
        headers: corsHeaders,
        body: JSON.stringify({ error: "Invalid response from AI" }),
      };
    }

    // Validate verdict enum
    const verdict = ["likely_scam", "possibly_scam", "probably_legitimate", "unclear"]
      .includes(parsed.verdict) ? parsed.verdict : "unclear";

    const confidence = ["high", "medium", "low"]
      .includes(parsed.confidence) ? parsed.confidence : "medium";

    // Never claim high confidence that something is safe — scam tactics evolve
    const finalConfidence = verdict === "probably_legitimate" ? "low" : confidence;

    // Sanitise reporting_links — forward only links to official UK reporting
    // domains (allowlisted), so a prompt-injected message cannot surface an
    // attacker-controlled URL as trusted reporting guidance. The link TEXT is
    // free-form model output too, so scrub it the same as summary/red_flags/etc:
    // otherwise a prompt-injected response could plant a fake phone number or
    // "act now" instruction as the trusted anchor text of a legitimate gov.uk
    // link. scrubContact runs before the length cap so a redaction match can't
    // be truncated away by the slice.
    // Canonicalise the fraud-reporting service link: the model's training data
    // predates the Dec 2025 Action Fraud → Report Fraud rebrand, so it still
    // emits actionfraud.police.uk links and "Action Fraud" naming. Rewrite both
    // deterministically rather than relying on the prompt rule alone.
    // The label must also carry the GEOGRAPHY. "Report Fraud (Police)" reads as a
    // UK-wide route and strands a Scottish reader on a self-contained action link
    // (operator review, 2026-07-29).
    const REPORT_FRAUD_LINK = {
      url: "https://www.reportfraud.police.uk",
      name: "Report Fraud — England, Wales and Northern Ireland",
    };
    const POLICE_SCOTLAND_LINK = {
      url: "https://www.scotland.police.uk/contact-us/non-emergencies/",
      name: "Police Scotland on 101 — Scotland",
    };
    const canonicaliseReportFraud = (l) => {
      try {
        const host = new URL(l.url).hostname.toLowerCase();
        if (host === "actionfraud.police.uk" || host === "www.actionfraud.police.uk" ||
            host === "reportfraud.police.uk" || host === "www.reportfraud.police.uk") {
          return { ...REPORT_FRAUD_LINK };
        }
        if (host === "scotland.police.uk" || host === "www.scotland.police.uk") {
          return { ...POLICE_SCOTLAND_LINK };
        }
      } catch { /* leave non-URL values for the allowlist filter to drop */ }
      return l;
    };
    let safeLinks = Array.isArray(parsed.reporting_links)
      ? parsed.reporting_links
          .filter(l => l && typeof l.url === "string" && isAllowedReportUrl(l.url))
          .map(canonicaliseReportFraud)
          .map(l => ({ url: l.url, name: scrubContact(String(l.name || "")).slice(0, 120) }))
      : [];
    // Never surface Report Fraud without the Scottish route beside it. Done
    // deterministically so a prompt rule alone cannot be the only guarantee.
    const hasHost = (h) => safeLinks.some(l => {
      try { return new URL(l.url).hostname.toLowerCase().replace(/^www\./, "") === h; }
      catch { return false; }
    });
    if (hasHost("reportfraud.police.uk") && !hasHost("scotland.police.uk")) {
      const at = safeLinks.findIndex(l => l.url === REPORT_FRAUD_LINK.url);
      safeLinks.splice(at + 1, 0, { ...POLICE_SCOTLAND_LINK });
    }
    safeLinks = safeLinks.slice(0, 6);

    const result = {
      verdict:             verdict,
      confidence:          finalConfidence,
      // scrub BEFORE slicing (same rule as link names above): slicing first can
      // cut a phone number at the cap boundary to under the 7-digit redaction
      // floor, letting the partial number through.
      summary:             typeof parsed.summary === "string"
                             ? scrubContact(parsed.summary).slice(0, 500) : "",
      red_flags:           Array.isArray(parsed.red_flags)
                             ? parsed.red_flags.slice(0, 6).map(x => scrubContact(String(x)).slice(0, 300)) : [],
      green_flags:         Array.isArray(parsed.green_flags)
                             ? parsed.green_flags.slice(0, 6).map(x => scrubContact(String(x)).slice(0, 300)) : [],
      recommended_actions: Array.isArray(parsed.recommended_actions)
                             ? parsed.recommended_actions.slice(0, 5).map(x => scrubContact(String(x)).slice(0, 300)) : [],
      reporting_links:     safeLinks.slice(0, 5),
    };

    return {
      statusCode: 200,
      headers: {
        ...corsHeaders,
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
      body: JSON.stringify(result),
    };
  } catch (err) {
    if (err && err.name === "AbortError") {
      console.error("Anthropic API timeout (aborted after 20s)");
      return {
        statusCode: 504,
        headers: corsHeaders,
        body: JSON.stringify({ error: "The checker timed out. Please try again in a moment." }),
      };
    }
    console.error("Function error:", err);
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Internal error" }),
    };
  } finally {
    clearTimeout(upstreamTimeout);
  }
};
