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

const DAILY_CALL_CAP = 2000; // max Anthropic checker calls per UTC day (abuse / cost guard; tune freely)

function blobStore(name) {
  if (!getStore) return null;
  try { return getStore({ name, consistency: "strong" }); }
  catch { return null; }
}

// Durable per-IP limiter. Returns true (limited) / false (ok), or null when the
// store is unavailable so the caller can fall back to the in-memory limiter.
async function durableRateLimited(ip) {
  const store = blobStore("checker-ratelimit");
  if (!store || !ip) return null;
  try {
    const now = Date.now();
    const key = `ip:${ip}`;
    const cur = (await store.get(key, { type: "json" })) || { count: 0, windowStart: now };
    if (now - cur.windowStart > RATE_LIMIT_WINDOW_MS) { cur.count = 0; cur.windowStart = now; }
    cur.count++;
    await store.setJSON(key, cur);
    return cur.count > RATE_LIMIT_MAX;
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
    const key = `calls:${new Date().toISOString().slice(0, 10)}`; // calls:YYYY-MM-DD (UTC)
    const cur = (await store.get(key, { type: "json" })) || { count: 0 };
    if (cur.count >= DAILY_CALL_CAP) return true;
    cur.count++;
    await store.setJSON(key, cur);
    return false;
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

// ─── HANDLER ─────────────────────────────────────────────────────────────────
exports.handler = async function(event) {
  const requestOrigin = event.headers["origin"] || event.headers["Origin"] || "";
  const allowedOrigin = getAllowedOrigin(requestOrigin);

  const corsHeaders = {
    "Access-Control-Allow-Origin":  allowedOrigin,
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Vary": "Origin",
  };

  // Handle preflight
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers: corsHeaders, body: "" };
  }

  if (event.httpMethod !== "POST") {
    return { statusCode: 405, headers: corsHeaders, body: "Method not allowed" };
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
    {"name": "Report Fraud (Police)", "url": "https://www.reportfraud.police.uk"},
    {"name": "Forward to 7726 (SMS spam)", "url": "https://www.ncsc.gov.uk/collection/phishing-scams/report-scam-text-messages"}
  ]
}

Rules:
- red_flags and green_flags must be specific to the content provided, not generic.
- recommended_actions must be concrete and actionable, not generic advice.
- reporting_links should include only UK-relevant links appropriate to the scam type.
- If verdict is probably_legitimate, red_flags may be empty but still list any minor concerns.
- Always include at least one recommended_action even for legitimate messages.
- Do not output anything outside the JSON object.`;

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
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
      console.error("Claude returned non-JSON:", text);
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
    // attacker-controlled URL as trusted reporting guidance.
    const safeLinks = Array.isArray(parsed.reporting_links)
      ? parsed.reporting_links.filter(
          l => l && typeof l.url === "string" && isAllowedReportUrl(l.url)
        )
      : [];

    const result = {
      verdict:             verdict,
      confidence:          finalConfidence,
      summary:             typeof parsed.summary === "string"
                             ? parsed.summary.slice(0, 500) : "",
      red_flags:           Array.isArray(parsed.red_flags)
                             ? parsed.red_flags.slice(0, 6).map(String) : [],
      green_flags:         Array.isArray(parsed.green_flags)
                             ? parsed.green_flags.slice(0, 6).map(String) : [],
      recommended_actions: Array.isArray(parsed.recommended_actions)
                             ? parsed.recommended_actions.slice(0, 5).map(String) : [],
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
    console.error("Function error:", err);
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Internal error" }),
    };
  }
};
