// netlify/functions/subscribe.js
// Step 1 of double opt-in: validate the request and email the visitor a signed
// confirmation link. The address is NOT added to the Resend Audience here — that
// only happens after they click confirm (netlify/functions/confirm-subscribe.js),
// which proves the address belongs to the person who submitted it (stops a third
// party from subscribing someone else's email).
// Reads RESEND_API_KEY, RESEND_AUDIENCE_ID and UNSUBSCRIBE_SECRET (the HMAC key,
// reused to sign confirm links) from the Netlify environment.

// ─── RATE LIMITING ───────────────────────────────────────────────────────────
// In-memory store — resets on cold start. Keyed by IP. Signups are far rarer
// than scam checks, so the ceiling is deliberately low.
const rateLimitStore = new Map();
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const RATE_LIMIT_MAX        = 5;         // 5 signups per IP per minute

function isRateLimited(ip) {
  if (!ip) return false;
  const now   = Date.now();
  const entry = rateLimitStore.get(ip) || { count: 0, windowStart: now };

  if (now - entry.windowStart > RATE_LIMIT_WINDOW_MS) {
    entry.count       = 0;
    entry.windowStart = now;
  }

  entry.count++;
  rateLimitStore.set(ip, entry);

  if (rateLimitStore.size > 5000) {
    for (const [key, val] of rateLimitStore.entries()) {
      if (now - val.windowStart > RATE_LIMIT_WINDOW_MS * 2) {
        rateLimitStore.delete(key);
      }
    }
  }

  return entry.count > RATE_LIMIT_MAX;
}

// ─── DURABLE ABUSE CONTROLS (Netlify Blobs) ──────────────────────────────────
// The in-memory per-IP limiter above resets on cold start and is per-instance,
// so on its own it can't stop newsletter-bombing a victim's inbox from rotating
// IPs. Two durable, shared controls back it up: a per-ADDRESS daily limit (cap
// the confirmation emails any one address can receive per day) and a GLOBAL
// daily send cap. Keys are salted hashes, never the plaintext address. Every
// Blobs call degrades gracefully — if the store is unavailable, the in-memory
// per-IP limiter still applies.
const crypto = require("crypto");
let getStore = null;
try { ({ getStore } = require("@netlify/blobs")); } catch { /* dep/runtime absent — degrade gracefully */ }

const ADDRESS_DAILY_MAX = 5;     // max confirmation emails to one address per 24h window
                                 // (fixed window anchored at the first send, not rolling)
const DAILY_SEND_CAP    = 500;   // max confirmation emails sent across all addresses / UTC day
// Prefer a dedicated RATE_LIMIT_SALT; else reuse UNSUBSCRIBE_SECRET (already
// required by this function) so the per-address hash salt is never the public
// literal. Hashes the address so the abuse-cap store never persists raw emails.
const RL_SALT           = process.env.RATE_LIMIT_SALT || process.env.UNSUBSCRIBE_SECRET || "bts-subscribe-rl-v1";

function blobStore(name) {
  if (!getStore) return null;
  try { return getStore({ name, consistency: "strong" }); }
  catch { return null; }
}

function emailKey(email) {
  return "em:" + crypto.createHash("sha256").update(RL_SALT + "|" + email).digest("hex").slice(0, 32);
}

// Atomic read-modify-write on a Blobs key via compare-and-set (etag), so
// concurrent invocations can't clobber each other's counters. Retries under
// contention; on the last attempt writes unconditionally. Returns the stored
// value, or null if the store is unusable.
async function atomicUpdate(store, key, init, mutate) {
  for (let attempt = 0; attempt < 5; attempt++) {
    let cur = null, etag = null;
    try {
      const meta = await store.getWithMetadata(key, { type: "json" });
      if (meta) { cur = meta.data; etag = meta.etag; }
    } catch { /* treat as absent */ }
    const next = mutate(cur || init());
    const opts = etag ? { onlyIfMatch: etag } : { onlyIfNew: true };
    try {
      const res = await store.setJSON(key, next, opts);
      if (!res || res.modified !== false) return next;
    } catch (e) {
      if (attempt === 4) { try { await store.setJSON(key, next); return next; } catch { return null; } }
    }
  }
  return null;
}

// True once this address has already received its daily quota of confirmation
// emails. Increments the per-address counter as part of the check. Fails OPEN
// (returns false) if Blobs is down — the per-IP limiter still applies.
async function addressOverDailyLimit(email) {
  const store = blobStore("subscribe-cooldown");
  if (!store) return false;
  try {
    const now  = Date.now();
    const next = await atomicUpdate(store, emailKey(email),
      () => ({ count: 0, windowStart: now }),
      (cur) => {
        if (now - cur.windowStart > 24 * 3600 * 1000) { cur.count = 0; cur.windowStart = now; }
        cur.count++;
        return cur;
      });
    if (next === null) return false;
    return next.count > ADDRESS_DAILY_MAX;
  } catch { return false; }
}

// Give back one unit of the per-address quota. Called when the confirmation
// send FAILS after the quota was already claimed — the counter deliberately
// increments before the send (so concurrent requests can't race past the
// cap), but counting failed sends would let a burst of Resend 5xxs burn a
// legitimate subscriber's whole daily quota with zero emails delivered.
async function releaseAddressQuota(email) {
  const store = blobStore("subscribe-cooldown");
  if (!store) return;
  try {
    await atomicUpdate(store, emailKey(email),
      () => ({ count: 0, windowStart: Date.now() }),
      (cur) => { cur.count = Math.max(0, cur.count - 1); return cur; });
  } catch { /* best effort */ }
}

// True once today's global confirmation-send cap is reached. Increments the
// counter. Fails OPEN if Blobs is down.
async function overDailySendCap() {
  const store = blobStore("subscribe-spend");
  if (!store) return false;
  try {
    const key  = `sends:${new Date().toISOString().slice(0, 10)}`;
    const next = await atomicUpdate(store, key, () => ({ count: 0 }), (c) => { c.count++; return c; });
    if (next === null) return false;
    return next.count > DAILY_SEND_CAP;
  } catch { return false; }
}

// ─── ALLOWED ORIGINS ─────────────────────────────────────────────────────────
const ALLOWED_ORIGINS = [
  "https://beatthescam.com",
  "https://www.beatthescam.com",
];

function getAllowedOrigin(requestOrigin) {
  if (ALLOWED_ORIGINS.includes(requestOrigin)) return requestOrigin;
  return ALLOWED_ORIGINS[0]; // Default to primary domain
}

// ─── EMAIL VALIDATION ────────────────────────────────────────────────────────
// Deliberately conservative: one @, a dot in the domain, no spaces, length cap.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(email) {
  if (typeof email !== "string") return false;
  if (email.length < 5 || email.length > 254) return false;
  return EMAIL_RE.test(email);
}

// ─── SENDER CONFIG ───────────────────────────────────────────────────────────
const FROM_ADDRESS = "Beat the Scam <alerts@updates.beatthescam.com>";
const REPLY_TO     = "hello@beatthescam.com";
const SITE         = "https://beatthescam.com";

// ─── CONFIRM TOKEN — OPAQUE / ENCRYPTED (AES-256-GCM) ──────────────────────────
// The confirm link ties ONE address to ONE click WITHOUT revealing that address.
// The older base64url(email).base36(exp).sig format was non-forgeable (HMAC) but
// the plaintext email was trivially recoverable from any captured URL — browser
// history, function/CDN logs, the Referer header. So we now mint an OPAQUE token:
// the email + expiry are sealed with AES-256-GCM under a key derived from
// UNSUBSCRIBE_SECRET, yielding a dotless base64url blob that leaks nothing and is
// still tamper-proof (GCM auth tag covers the payload AND the expiry).
// confirm-subscribe.js DUAL-PARSES — it accepts both this new format and the
// legacy dotted format — so confirmation emails already sitting in inboxes keep
// working through the transition. The key is domain-separated by purpose
// ("confirm" vs "unsub"), so a confirm token can't be replayed as an unsubscribe
// token. Fails CLOSED — with no secret, no token is minted and double opt-in
// cannot proceed (we never ship a forgeable token). (crypto required at top.)
const CONFIRM_TTL_SECONDS = 7 * 24 * 3600;   // confirm links expire after 7 days
const TOKEN_VERSION = 0x02;

// HKDF-SHA256(UNSUBSCRIBE_SECRET) → 32-byte AES-256 key, domain-separated by purpose.
function tokenKey(purpose) {
  const secret = process.env.UNSUBSCRIBE_SECRET || "";
  if (!secret) return null;
  return Buffer.from(crypto.hkdfSync("sha256", secret, "bts-token-kdf-v2", "aes256gcm:" + purpose, 32));
}

// Seal a small payload object into an opaque, dotless base64url token:
// base64url( version(1) || iv(12) || ciphertext || tag(16) ). Returns "" with no
// secret (fail closed). The version byte + purpose are bound as GCM AAD.
function sealToken(purpose, payload) {
  const key = tokenKey(purpose);
  if (!key) return "";
  const iv     = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  cipher.setAAD(Buffer.from("bts-token-v2:" + purpose, "utf8"));
  const pt  = Buffer.from(JSON.stringify(payload), "utf8");
  const ct  = Buffer.concat([cipher.update(pt), cipher.final()]);
  const tag = cipher.getAuthTag();
  return Buffer.concat([Buffer.from([TOKEN_VERSION]), iv, ct, tag]).toString("base64url");
}

function confirmToken(email) {
  return sealToken("confirm", { e: email, x: Math.floor(Date.now() / 1000) + CONFIRM_TTL_SECONDS });
}

// ─── CONFIRMATION EMAIL ────────────────────────────────────────────────────────
const CONFIRM_HTML = `<!doctype html>
<html lang="en-GB">
<body style="margin:0;padding:0;background:#f3f6fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#102033;">
  <div style="max-width:560px;margin:0 auto;padding:32px 20px;">
    <div style="background:#0b1220;border-radius:16px 16px 0 0;padding:24px 28px;">
      <span style="color:#ffffff;font-size:20px;font-weight:800;letter-spacing:-.02em;">Beat the Scam</span>
    </div>
    <div style="background:#ffffff;border:1px solid #dbe5ef;border-top:0;border-radius:0 0 16px 16px;padding:28px;">
      <h1 style="margin:0 0 14px;font-size:22px;line-height:1.3;">Confirm your subscription</h1>
      <p style="margin:0 0 16px;font-size:16px;line-height:1.6;color:#5b6878;">
        Someone (hopefully you) asked to subscribe this address to Beat the Scam scam alerts. Tap the button to confirm and start receiving them.
      </p>
      <p style="margin:0 0 28px;">
        <a href="__CONFIRM_URL__" style="display:inline-block;background:#1d4ed8;color:#ffffff;text-decoration:none;font-weight:700;font-size:16px;padding:13px 22px;border-radius:999px;">Confirm subscription &rarr;</a>
      </p>
      <p style="margin:0;font-size:14px;line-height:1.6;color:#5b6878;">
        Didn't request this? Just ignore this email — nothing happens unless you confirm, and you won't be added to any list.
      </p>
    </div>
    <p style="margin:18px 0 0;font-size:12px;line-height:1.6;color:#8a97a6;text-align:center;">
      Beat the Scam &middot; Independent UK consumer-protection guides<br>
      Educational content only &mdash; not legal or financial advice.
    </p>
  </div>
</body>
</html>`;

const CONFIRM_TEXT = `Confirm your subscription

Someone (hopefully you) asked to subscribe this address to Beat the Scam scam alerts. Open the link below to confirm and start receiving them:

__CONFIRM_URL__

Didn't request this? Just ignore this email — nothing happens unless you confirm, and you won't be added to any list.

Beat the Scam · Independent UK consumer-protection guides
Educational content only — not legal or financial advice.`;

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
    // responses on this site (Section 20 gotcha). no-store on EVERY response.
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

  // Enforce origin server-side: CORS headers only stop a browser from reading the
  // response; a non-browser client ignores them and could still trigger sends.
  // Reject a present-but-unlisted Origin. A missing Origin is allowed through.
  if (requestOrigin && !ALLOWED_ORIGINS.includes(requestOrigin)) {
    return { statusCode: 403, headers: corsHeaders, body: JSON.stringify({ error: "Forbidden" }) };
  }

  // Rate limiting — x-nf-client-connection-ip is set by Netlify's edge and
  // cannot be spoofed by a caller; prefer it over the forgeable x-forwarded-for.
  const clientIp =
    event.headers["x-nf-client-connection-ip"] ||
    event.headers["x-forwarded-for"]?.split(",")[0].trim() ||
    event.headers["x-real-ip"] ||
    "";

  if (isRateLimited(clientIp)) {
    return {
      statusCode: 429,
      headers: { ...corsHeaders, "Retry-After": "60" },
      body: JSON.stringify({ error: "Too many requests. Please wait a moment and try again." }),
    };
  }

  // Auth / config. UNSUBSCRIBE_SECRET is required: it signs the confirm link, so
  // without it double opt-in cannot run (fail closed rather than add unconfirmed).
  const apiKey     = process.env.RESEND_API_KEY;
  const audienceId = process.env.RESEND_AUDIENCE_ID;
  const secret     = process.env.UNSUBSCRIBE_SECRET;
  if (!apiKey || !audienceId || !secret) {
    console.error("RESEND_API_KEY / RESEND_AUDIENCE_ID / UNSUBSCRIBE_SECRET not all set");
    return {
      statusCode: 500,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Service not configured" }),
    };
  }

  // Cap total body size BEFORE parsing — never allocate/parse a multi-MB payload.
  if ((event.body || "").length > 16 * 1024) {
    return { statusCode: 413, headers: corsHeaders, body: JSON.stringify({ error: "Request too large" }) };
  }

  // Parse and validate input
  let email, consent, honeypot;
  try {
    const body = JSON.parse(event.body || "{}");
    email    = (body.email || "").trim().toLowerCase().slice(0, 254);
    consent  = body.consent === true || body.consent === "true" || body.consent === "on";
    honeypot = (body.website || "").trim();
  } catch {
    return {
      statusCode: 400,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Invalid request body" }),
    };
  }

  // Honeypot — a bot filled the hidden field. Pretend success, do nothing.
  if (honeypot) {
    return {
      statusCode: 200,
      headers: { ...corsHeaders, "Content-Type": "application/json", "Cache-Control": "no-store" },
      body: JSON.stringify({ ok: true, pending: true }),
    };
  }

  if (!isValidEmail(email)) {
    return {
      statusCode: 400,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Please enter a valid email address." }),
    };
  }

  if (!consent) {
    return {
      statusCode: 400,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Please tick the consent box to subscribe." }),
    };
  }

  // Durable anti-abuse, layered on the per-IP limiter: silently absorb once an
  // address has had its daily quota of confirmations (pretend success, send
  // nothing — same as the honeypot path, so a bomber can't tell), and refuse new
  // sends once the global daily cap is hit. Together these bound inbox-bombing
  // that rotating IPs would otherwise slip past the per-IP limiter.
  if (await addressOverDailyLimit(email)) {
    return {
      statusCode: 200,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      body: JSON.stringify({ ok: true, pending: true }),
    };
  }
  if (await overDailySendCap()) {
    return {
      statusCode: 503,
      headers: { ...corsHeaders, "Retry-After": "3600", "Content-Type": "application/json" },
      body: JSON.stringify({ error: "We're sending a lot of confirmations right now. Please try again later." }),
    };
  }

  // ─── Send the double opt-in confirmation email ─────────────────────────────
  // We do NOT touch the Resend audience here — confirm-subscribe.js adds the
  // contact only after the link is clicked.
  // confirmToken() can only return "" when UNSUBSCRIBE_SECRET is unset, which
  // the config check above already 500s on — if that check ever moves below
  // this point, an empty `t=` link would be emailed silently.
  const token      = confirmToken(email);
  const confirmUrl = `${SITE}/api/confirm-subscribe?t=${encodeURIComponent(token)}`;
  try {
    // 8s timeout, well inside Netlify's ~10s function kill, so the failure
    // path (incl. the quota release) always gets to run.
    const ctrl  = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8000);
    let mailRes;
    try {
      mailRes = await fetch("https://api.resend.com/emails", {
        method: "POST",
        signal: ctrl.signal,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          from: FROM_ADDRESS,
          to: [email],
          reply_to: REPLY_TO,
          subject: "Confirm your Beat the Scam subscription",
          html: CONFIRM_HTML.replace(/__CONFIRM_URL__/g, confirmUrl),
          text: CONFIRM_TEXT.replace(/__CONFIRM_URL__/g, confirmUrl),
        }),
      });
    } finally {
      clearTimeout(timer);
    }
    if (!mailRes.ok) {
      // Slice the error body — Resend validation errors can echo the recipient
      // address, and function logs should never hold more of it than needed.
      console.error("Confirmation email non-OK:", mailRes.status, (await mailRes.text()).slice(0, 300));
      await releaseAddressQuota(email);
      return {
        statusCode: 502,
        headers: corsHeaders,
        body: JSON.stringify({ error: "Could not send the confirmation email. Please try again shortly." }),
      };
    }
  } catch (err) {
    console.error("Confirmation email threw:", err);
    await releaseAddressQuota(email);
    return {
      statusCode: 502,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Could not send the confirmation email. Please try again shortly." }),
    };
  }

  return {
    statusCode: 200,
    headers: { ...corsHeaders, "Content-Type": "application/json", "Cache-Control": "no-store" },
    body: JSON.stringify({ ok: true, pending: true }),
  };
};
