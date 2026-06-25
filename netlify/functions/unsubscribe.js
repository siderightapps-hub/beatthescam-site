// netlify/functions/unsubscribe.js
// One-click + confirm-page unsubscribe for the newsletter welcome email.
// Marks the contact unsubscribed in the Resend Audience (the same global
// suppression list future Broadcasts honour). RFC 8058 one-click compatible.
//
// Security / safety model:
//  - The link carries an OPAQUE, ENCRYPTED token (AES-256-GCM): the email is
//    sealed under a key derived from UNSUBSCRIBE_SECRET, so a recipient can only
//    unsubscribe THEIR OWN address — the email can't be read from a captured URL
//    and can't be swapped without breaking the auth tag. We DUAL-PARSE: the
//    legacy base64url(email).sig (HMAC) format is still accepted so unsubscribe
//    links already delivered keep working (compliance) during the transition.
//  - GET NEVER mutates state — it only renders a confirm page. Only POST
//    performs the unsubscribe, so email link-prefetchers / security scanners
//    (which issue GET on every link) cannot auto-unsubscribe a recipient.
//    Gmail/Yahoo's one-click button issues a POST, which is the intended path.
//  - Fails CLOSED: with no UNSUBSCRIBE_SECRET set, tokens are neither minted
//    (subscribe.js) nor accepted here.

const crypto = require("crypto");

const RESEND_BASE   = "https://api.resend.com";
const CONTACT_EMAIL = "hello@beatthescam.com";

// ─── RATE LIMITING (per IP) ───────────────────────────────────────────────────
const rateLimitStore = new Map();
const RATE_LIMIT_WINDOW_MS = 60 * 1000;
const RATE_LIMIT_MAX        = 20;

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

// ─── OPAQUE TOKEN CRYPTO (AES-256-GCM) ────────────────────────────────────────
// Unsubscribe tokens are now opaque: the email is encrypted under a key derived
// from UNSUBSCRIBE_SECRET, so the address can't be recovered from a captured URL
// (browser history, logs, Referer) — the legacy base64url(email).sig format
// leaked it. The key is domain-separated by purpose, so a confirm token can't be
// used to unsubscribe. (crypto is required once at the top of the file.)
const TOKEN_VERSION = 0x02;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// HKDF-SHA256(UNSUBSCRIBE_SECRET) → 32-byte AES-256 key, domain-separated by purpose.
function tokenKey(purpose) {
  const secret = process.env.UNSUBSCRIBE_SECRET || "";
  if (!secret) return null;
  return Buffer.from(crypto.hkdfSync("sha256", secret, "bts-token-kdf-v2", "aes256gcm:" + purpose, 32));
}

// Open an opaque token → payload object, or null if malformed / tampered /
// sealed for a different purpose / minted under a different secret.
function openToken(purpose, token) {
  const key = tokenKey(purpose);
  if (!key) return null;
  const buf = Buffer.from(String(token), "base64url");
  if (buf.length < 1 + 12 + 16 + 2) return null;          // version + iv + tag + ≥2 ct bytes
  if (buf[0] !== TOKEN_VERSION) return null;
  const iv  = buf.subarray(1, 13);
  const ct  = buf.subarray(13, buf.length - 16);
  const tag = buf.subarray(buf.length - 16);
  try {
    const decipher = crypto.createDecipheriv("aes-256-gcm", key, iv);
    decipher.setAAD(Buffer.from("bts-token-v2:" + purpose, "utf8"));
    decipher.setAuthTag(tag);
    const dt = Buffer.concat([decipher.update(ct), decipher.final()]);
    return JSON.parse(dt.toString("utf8"));
  } catch { return null; }
}

// ─── TOKEN — DUAL-PARSE (new opaque + legacy dotted) ───────────────────────────
// Returns the verified email, or null if missing / malformed / bad signature /
// secret unset (fail closed). A token containing "." is the LEGACY
// base64url(email).sig (HMAC) format — still in welcome emails already delivered
// — and is HMAC-verified; a dotless token is the new AES-256-GCM format.
function verifyToken(t) {
  const secret = process.env.UNSUBSCRIBE_SECRET || "";
  if (!t || !secret) return null;
  return String(t).includes(".") ? verifyTokenLegacy(t) : verifyTokenV2(t);
}

function verifyTokenV2(t) {
  const p = openToken("unsub", t);
  if (!p || typeof p.e !== "string") return null;
  if (p.e.length > 254 || !EMAIL_RE.test(p.e)) return null;
  return p.e;
}

function verifyTokenLegacy(t) {
  const secret = process.env.UNSUBSCRIBE_SECRET || "";
  const parts = String(t).split(".");
  if (parts.length !== 2) return null;
  const [e, sig] = parts;
  let email;
  try { email = Buffer.from(e, "base64url").toString("utf8"); } catch { return null; }
  if (!email || email.length > 254 || !EMAIL_RE.test(email)) return null;
  const expected = crypto.createHmac("sha256", secret).update(email).digest("base64url");
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  return email;
}

// ─── RESEND ───────────────────────────────────────────────────────────────────
// Mark the contact unsubscribed. Tries the audience-scoped path first
// (documented, and we hold the audience id), then the non-scoped contact path
// as a fallback. A 404 (contact already gone) is treated as success — the end
// state is what we want, and the op is idempotent.
async function markUnsubscribed(email) {
  const apiKey     = process.env.RESEND_API_KEY;
  const audienceId = process.env.RESEND_AUDIENCE_ID;
  if (!apiKey || !email) return false;

  const enc     = encodeURIComponent(email);
  const body    = JSON.stringify({ unsubscribed: true });
  const headers = { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` };

  const urls = [];
  if (audienceId) urls.push(`${RESEND_BASE}/audiences/${audienceId}/contacts/${enc}`);
  urls.push(`${RESEND_BASE}/contacts/${enc}`);

  for (const url of urls) {
    try {
      const res = await fetch(url, { method: "PATCH", headers, body });
      if (res.ok || res.status === 404) return true;
      console.error("unsubscribe PATCH non-ok:", res.status, url, (await res.text()).slice(0, 300));
    } catch (err) {
      console.error("unsubscribe PATCH threw:", url, err);
    }
  }
  return false;
}

// ─── PAGES ────────────────────────────────────────────────────────────────────
function page(title, bodyHtml) {
  return `<!doctype html><html lang="en-GB"><head><meta charset="utf-8">`
    + `<meta name="viewport" content="width=device-width,initial-scale=1">`
    + `<meta name="robots" content="noindex"><title>${title} — Beat the Scam</title></head>`
    + `<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;max-width:560px;margin:56px auto;padding:0 20px;color:#102033;line-height:1.6;">`
    + `<h1 style="font-size:22px;margin:0 0 16px;">Beat the Scam</h1>${bodyHtml}`
    + `<p style="font-size:14px;margin-top:28px;"><a href="https://beatthescam.com/" style="color:#1d4ed8;">Return to the site</a></p>`
    + `</body></html>`;
}

// Security headers for the function-rendered HTML pages. netlify.toml [[headers]]
// do not reliably reach function responses here (Section 20 gotcha), so they are
// set explicitly. These pages use only inline-style attributes and a same-origin
// form — no scripts, no external resources — so the CSP can be strict.
const SECURITY_HEADERS = {
  "Content-Security-Policy":
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; " +
    "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
};

function htmlResponse(statusCode, body) {
  return {
    statusCode,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex",
      ...SECURITY_HEADERS,
    },
    body,
  };
}

// Plain-text edge responses (429/405) get the same security header set + no-store
// as the HTML pages — netlify.toml headers don't reliably reach functions here.
function textResponse(statusCode, body, extraHeaders) {
  return {
    statusCode,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex",
      ...SECURITY_HEADERS,
      ...(extraHeaders || {}),
    },
    body,
  };
}

// ─── HANDLER ──────────────────────────────────────────────────────────────────
exports.handler = async function(event) {
  const clientIp =
    event.headers["x-nf-client-connection-ip"] ||
    event.headers["x-forwarded-for"]?.split(",")[0].trim() ||
    "";
  if (isRateLimited(clientIp)) {
    return textResponse(429, "Too many requests", { "Retry-After": "60" });
  }

  const token = (event.queryStringParameters && event.queryStringParameters.t) || "";
  const email = verifyToken(token);

  // ─── One-click (RFC 8058): the mail client POSTs to the List-Unsubscribe URL,
  //     or our own confirm form POSTs here. This is where state actually changes.
  if (event.httpMethod === "POST") {
    let ok = false;
    if (email) ok = await markUnsubscribed(email);
    else console.error("unsubscribe POST with invalid/missing token");
    // Return 200 so the mail client marks the action handled; real backend
    // failures are logged above (observable in Netlify function logs) rather
    // than silently swallowed.
    return htmlResponse(
      200,
      ok
        ? page("Unsubscribed", `<p style="font-size:16px;">You've been unsubscribed. You won't receive further emails from Beat the Scam.</p>`)
        : page("Unsubscribe", `<p style="font-size:16px;">We couldn't fully process that just now. If you keep receiving emails, reply to any of them or email <a href="mailto:${CONTACT_EMAIL}" style="color:#1d4ed8;">${CONTACT_EMAIL}</a> and we'll remove you.</p>`)
    );
  }

  if (event.httpMethod !== "GET") {
    return textResponse(405, "Method not allowed");
  }

  // ─── GET: render a confirm page only. NEVER mutates (prefetch/scanner-safe).
  if (!email) {
    return htmlResponse(200, page("Unsubscribe",
      `<p style="font-size:16px;">This unsubscribe link is invalid or has expired. Email <a href="mailto:${CONTACT_EMAIL}" style="color:#1d4ed8;">${CONTACT_EMAIL}</a> and we'll remove you right away.</p>`));
  }
  const action = `/api/unsubscribe?t=${encodeURIComponent(token)}`;
  return htmlResponse(200, page("Unsubscribe",
    `<p style="font-size:16px;">Unsubscribe from Beat the Scam alerts?</p>`
    + `<form method="POST" action="${action}" style="margin-top:20px;">`
    + `<button type="submit" style="background:#1d4ed8;color:#fff;border:0;border-radius:999px;font-size:16px;font-weight:700;padding:12px 22px;cursor:pointer;">Confirm unsubscribe</button>`
    + `</form>`
    + `<p style="font-size:13px;color:#5b6878;margin-top:16px;">Changed your mind? Just close this page — nothing happens until you confirm.</p>`));
};
