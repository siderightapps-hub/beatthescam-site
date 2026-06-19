// netlify/functions/csp-report.js
// First-party collector for Content-Security-Policy violation reports.
//
// Receives reports from both browser mechanisms, both POSTed same-origin
// (so no CORS dance is needed):
//   - Reporting API     (report-to / Reporting-Endpoints) → application/reports+json
//                         body is an array of {type:"csp-violation", body:{...}}
//   - Legacy report-uri (older browsers)                  → application/csp-report
//                         body is a single {"csp-report": {...}} object
// It logs a minimal, PII-light summary of each violation to the Netlify
// function logs (observable in the dashboard) and returns 204. There is no
// datastore — the goal is visibility into what the CSP is blocking, not
// long-term analytics. If aggregation/dashboards ever justify a new
// sub-processor, repoint the /api/csp-report endpoint at a third-party
// collector and delete this function.
//
// Privacy: the client IP is used only for in-memory rate limiting and is NEVER
// logged; document/blocked URLs are reduced to origin+path (query/fragment
// stripped) and length-capped, so report logs can't accumulate PII.

// ─── RATE LIMITING (per IP) ───────────────────────────────────────────────────
// Reports can arrive once per blocked resource per page view, so the ceiling is
// higher than the form endpoints. Over-limit reports are dropped silently (still
// 204) and NOT logged, so one noisy/abusive client can't flood the logs.
const rateLimitStore = new Map();
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX        = 30;        // 30 reports per IP per minute

function isRateLimited(ip) {
  if (!ip) return false;
  const now = Date.now();
  const entry = rateLimitStore.get(ip) || { count: 0, windowStart: now };
  if (now - entry.windowStart > RATE_LIMIT_WINDOW_MS) {
    entry.count = 0;
    entry.windowStart = now;
  }
  entry.count++;
  rateLimitStore.set(ip, entry);
  if (rateLimitStore.size > 5000) {
    for (const [k, v] of rateLimitStore.entries()) {
      if (now - v.windowStart > RATE_LIMIT_WINDOW_MS * 2) rateLimitStore.delete(k);
    }
  }
  return entry.count > RATE_LIMIT_MAX;
}

// ─── LIMITS ────────────────────────────────────────────────────────────────────
// CSP reports are a few hundred bytes; anything large is junk or abuse. Reject
// oversized bodies before parsing so we never buffer/parse attacker-sized JSON.
const MAX_BODY_BYTES   = 16 * 1024; // 16 KB
const MAX_PER_REQUEST  = 10;        // Reporting API batches — cap logged items.

// Our own origins. A report whose document is on some OTHER host is noise/abuse
// (genuine reports only fire on our pages) and is dropped.
const SITE_HOSTS = ["beatthescam.com", "www.beatthescam.com"];

// Reduce a URL to origin + path (no query/fragment) and cap its length, so we
// never persist query-string PII or unbounded strings into the logs.
function tidyUrl(value) {
  if (typeof value !== "string" || !value) return "";
  try {
    const u = new URL(value);
    return (u.origin + u.pathname).slice(0, 256);
  } catch {
    // Not an absolute URL (e.g. "inline", "eval", "self") — keep the keyword.
    return value.split(/[?#]/)[0].slice(0, 256);
  }
}

// True when the report's document URL is present AND points at a host that
// isn't ours. Absent/unparseable document → kept (some clients omit it).
function isForeignReport(v) {
  const doc = v["document-uri"] || v.documentURL || "";
  if (!doc) return false;
  try {
    return !SITE_HOSTS.includes(new URL(doc).hostname);
  } catch {
    return false;
  }
}

// Pull the fields worth logging out of one violation, tolerant of both the
// legacy csp-report shape (kebab-case keys) and the Reporting API shape
// (camelCase keys).
function summarise(v) {
  if (!v || typeof v !== "object") return null;
  const directive =
    v["effective-directive"] || v.effectiveDirective ||
    v["violated-directive"]  || v.violatedDirective  || "";
  const summary = {
    directive: String(directive).slice(0, 128),
    blocked:   tidyUrl(v["blocked-uri"]  || v.blockedURL  || ""),
    document:  tidyUrl(v["document-uri"] || v.documentURL || ""),
  };
  const disposition = v.disposition;
  if (disposition) summary.disposition = String(disposition).slice(0, 16);
  // Inline/eval violations carry a source location worth keeping (file:line).
  const src = v["source-file"] || v.sourceFile;
  if (src) {
    summary.source = tidyUrl(src);
    const line = Number(v["line-number"] || v.lineNumber);
    if (line) summary.line = line;
  }
  return summary;
}

// ─── HANDLER ──────────────────────────────────────────────────────────────────
exports.handler = async function(event) {
  // Reports are delivered same-origin by the user agent, so no CORS headers are
  // needed; answer a stray preflight cheaply just in case.
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers: { "Cache-Control": "no-store" }, body: "" };
  }
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, headers: { "Cache-Control": "no-store" }, body: "Method not allowed" };
  }

  // From here on always answer 204 — the browser ignores the response body, and
  // a collector should never surface an error. Problems are logged, not returned.
  const ok = { statusCode: 204, headers: { "Cache-Control": "no-store" }, body: "" };

  // Rate limit on the unspoofable Netlify edge IP; the IP itself is never logged.
  const clientIp =
    event.headers["x-nf-client-connection-ip"] ||
    event.headers["x-forwarded-for"]?.split(",")[0].trim() ||
    "";
  if (isRateLimited(clientIp)) return ok;

  const raw = event.body || "";
  if (!raw || Buffer.byteLength(raw, "utf8") > MAX_BODY_BYTES) return ok;

  let parsed;
  try { parsed = JSON.parse(raw); } catch { return ok; }

  // Normalise both delivery shapes into a flat list of violation objects.
  let violations = [];
  if (Array.isArray(parsed)) {
    // Reporting API: [{type:"csp-violation", body:{...}}, ...]
    violations = parsed
      .filter(r => r && (!r.type || r.type === "csp-violation" || r.type === "csp"))
      .map(r => r.body || r);
  } else if (parsed && parsed["csp-report"]) {
    // Legacy report-uri: {"csp-report": {...}}
    violations = [parsed["csp-report"]];
  } else if (parsed && typeof parsed === "object") {
    violations = [parsed];
  }

  for (const v of violations.slice(0, MAX_PER_REQUEST)) {
    if (isForeignReport(v)) continue;
    const summary = summarise(v);
    if (summary && (summary.directive || summary.blocked)) {
      console.warn("CSP-REPORT", JSON.stringify(summary));
    }
  }

  return ok;
};
