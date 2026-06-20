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

// ─── CONFIRM TOKEN ────────────────────────────────────────────────────────────
// Opaque, non-forgeable token tying a confirm link to ONE address:
//   base64url(email) + "." + base64url(HMAC-SHA256(secret, "confirm:" + email)).
// The "confirm:" prefix means a confirm token is NOT interchangeable with an
// unsubscribe token (which signs the bare email in unsubscribe.js), even though
// both reuse UNSUBSCRIBE_SECRET. Fails CLOSED — with no secret, no token is
// minted and double opt-in cannot proceed (we never ship a forgeable token).
const crypto = require("crypto");
function confirmToken(email) {
  const secret = process.env.UNSUBSCRIBE_SECRET || "";
  if (!secret) return "";
  const e   = Buffer.from(email, "utf8").toString("base64url");
  const sig = crypto.createHmac("sha256", secret).update("confirm:" + email).digest("base64url");
  return `${e}.${sig}`;
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
  };

  // Handle preflight
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers: corsHeaders, body: "" };
  }

  if (event.httpMethod !== "POST") {
    return { statusCode: 405, headers: corsHeaders, body: "Method not allowed" };
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

  // ─── Send the double opt-in confirmation email ─────────────────────────────
  // We do NOT touch the Resend audience here — confirm-subscribe.js adds the
  // contact only after the link is clicked.
  const token      = confirmToken(email);
  const confirmUrl = `${SITE}/api/confirm-subscribe?t=${encodeURIComponent(token)}`;
  try {
    const mailRes = await fetch("https://api.resend.com/emails", {
      method: "POST",
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
    if (!mailRes.ok) {
      console.error("Confirmation email non-OK:", mailRes.status, await mailRes.text());
      return {
        statusCode: 502,
        headers: corsHeaders,
        body: JSON.stringify({ error: "Could not send the confirmation email. Please try again shortly." }),
      };
    }
  } catch (err) {
    console.error("Confirmation email threw:", err);
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
