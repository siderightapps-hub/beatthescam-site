// netlify/functions/check-scam.js
// Proxies scam checker requests to the Anthropic Claude API.
// Set ANTHROPIC_API_KEY in your Netlify environment variables.

// Reporting routes are NOT defined here. lib/canon-routes.js is generated from
// content/sources.json by scripts/sync_canon_js.py and kept in sync by a
// committed self-test, so the checker cannot drift from the canon that drives
// the site, the gate and the generator (operator review, 2026-07-29).
const { EXAMPLE_REPORTING_LINKS, PROMPT_ROUTE_RULES, CANON_REQUIRED_HOSTS } =
  require("./lib/canon-routes");
const { buildReportingLinks } = require("./lib/reporting-links");

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
let getStore = null, connectLambda = null;
try { ({ getStore, connectLambda } = require("@netlify/blobs")); } catch { /* dep/runtime absent — degrade gracefully */ }

const crypto = require("crypto");

const DAILY_CALL_CAP = 2000; // max Anthropic checker calls per UTC day (abuse / cost guard; tune freely)

// Rate-limit keys are a salted HASH of the IP, never the raw address — so the
// limiter never persists a plaintext IP (the privacy policy promises as much).
// Prefer a dedicated RATE_LIMIT_SALT; otherwise reuse UNSUBSCRIBE_SECRET (already
// required site-wide), so the salt is always a real secret and never the public
// literal — without failing closed and taking the checker offline if it's unset.
const RL_SALT = process.env.RATE_LIMIT_SALT || process.env.UNSUBSCRIBE_SECRET || "bts-checker-rl-v1";
if (!process.env.RATE_LIMIT_SALT && !process.env.UNSUBSCRIBE_SECRET) {
  // Neither secret is set — the salt fell back to a literal visible in source,
  // silently weakening the "salted hash, never raw IP" privacy guarantee for
  // the rate-limit store. Not fatal (availability wins), but the operator
  // should notice and set RATE_LIMIT_SALT or UNSUBSCRIBE_SECRET.
  console.warn("check-scam: RL_SALT fell back to the hardcoded literal — set RATE_LIMIT_SALT or UNSUBSCRIBE_SECRET.");
}
function rlKey(ip) {
  return "ip:" + crypto.createHash("sha256").update(RL_SALT + "|" + ip).digest("hex").slice(0, 32);
}

function blobStore(name) {
  if (!getStore) return null;
  try { return getStore({ name, consistency: "strong" }); }
  catch { return null; }
}

// Compare-and-set counter writes live in one tested module — see
// lib/atomic-store.js. This was a duplicated copy until 2026-08-19.
const { atomicUpdate } = require("./lib/atomic-store");

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
// true once the cap is reached (caller should refuse). This must fail CLOSED:
// a per-instance in-memory IP limit cannot bound a distributed caller during a
// Blobs outage, so failing open would remove the only global cost control.
async function overDailyCap() {
  const store = blobStore("checker-spend");
  if (!store) return true;
  try {
    // calls:YYYY-MM-DD keyed on the UTC date: the cap resets at midnight UTC
    // (01:00/02:00 UK time), so a UK "day" deliberately spans two counters.
    const key = `calls:${new Date().toISOString().slice(0, 10)}`;
    const next = await atomicUpdate(store, key, () => ({ count: 0 }), (c) => { c.count++; return c; });
    if (next === null) return true;
    return next.count > DAILY_CALL_CAP;
  } catch (err) {
    console.error("Blobs spend-cap error (refusing checker request):", err);
    return true;
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
// Extracted to lib/allowed-domains.js so it can be unit-tested against the
// canon. It unions CANON_REQUIRED_HOSTS — every host serving an on_page route
// in content/sources.json — because www.advice.scot was a required
// consumer-advice route missing from the hand-maintained list, so a valid
// Advice Direct Scotland link was silently discarded from checker results
// (operator review, 2026-07-30).
const { isAllowedReportUrl } = require("./lib/allowed-domains");

// ─── SCRUB MODEL-AUTHORED FREE TEXT ──────────────────────────────────────────
// Extracted to lib/scrub-contact.js so it can be unit-tested — see that file
// for what it does and why (operator review, 2026-08-27 security audit).
const { scrubContact } = require("./lib/scrub-contact");

// ─── HANDLER ─────────────────────────────────────────────────────────────────
exports.handler = async function(event) {
  // Lambda compatibility mode does not auto-inject the Blobs environment —
  // without this, getStore() throws on every call and every durable cap
  // below silently fails open. Must run before any blobStore() call.
  if (connectLambda) { try { connectLambda(event); } catch { /* degrade gracefully */ } }

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
  "reporting_links": ${JSON.stringify(EXAMPLE_REPORTING_LINKS.map(l => ({ name: l.name, url: l.url })))}
}

Rules:
${PROMPT_ROUTE_RULES.map(r => "- " + r).join("\n")}
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
    // free-form model output too, so it is scrubbed the same as
    // summary/red_flags/etc: otherwise a prompt-injected response could plant a
    // fake phone number or "act now" instruction as the trusted anchor text of a
    // legitimate gov.uk link.
    //
    // Canonicalisation, deduplication, the inseparable Report Fraud / Police
    // Scotland pair and the ONE final cap all live in lib/reporting-links.js so
    // the pairing rule is unit-tested at every input position. The routes
    // themselves come from lib/canon-routes.js, generated from
    // content/sources.json — the checker no longer keeps its own copy.
    const safeLinks = buildReportingLinks(parsed.reporting_links, isAllowedReportUrl, scrubContact);

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
      // Already capped inside buildReportingLinks(). A second slice here is
      // what discarded the Scottish route when Report Fraud landed in the
      // fifth position.
      reporting_links:     safeLinks,
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
