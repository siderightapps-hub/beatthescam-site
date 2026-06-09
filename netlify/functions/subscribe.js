// netlify/functions/subscribe.js
// Adds a newsletter subscriber to a Resend Audience and sends a welcome email.
// Reads RESEND_API_KEY and RESEND_AUDIENCE_ID from the Netlify environment.

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

const WELCOME_HTML = `<!doctype html>
<html lang="en-GB">
<body style="margin:0;padding:0;background:#f3f6fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#102033;">
  <div style="max-width:560px;margin:0 auto;padding:32px 20px;">
    <div style="background:#0b1220;border-radius:16px 16px 0 0;padding:24px 28px;">
      <span style="color:#ffffff;font-size:20px;font-weight:800;letter-spacing:-.02em;">Beat the Scam</span>
    </div>
    <div style="background:#ffffff;border:1px solid #dbe5ef;border-top:0;border-radius:0 0 16px 16px;padding:28px;">
      <h1 style="margin:0 0 14px;font-size:22px;line-height:1.3;">You're on the list &#9989;</h1>
      <p style="margin:0 0 16px;font-size:16px;line-height:1.6;color:#5b6878;">
        Thanks for subscribing. You'll get plain-English scam alerts and new guides as the latest tactics appear &mdash; the checks you can run in under a minute before you click, pay, or share anything.
      </p>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.6;color:#5b6878;">
        Got a suspicious text, email, or call right now? Run it through our free AI scam checker:
      </p>
      <p style="margin:0 0 28px;">
        <a href="https://beatthescam.com/check/" style="display:inline-block;background:#1d4ed8;color:#ffffff;text-decoration:none;font-weight:700;font-size:16px;padding:13px 22px;border-radius:999px;">Check a message &rarr;</a>
      </p>
      <p style="margin:0;font-size:14px;line-height:1.6;color:#5b6878;">
        Reply to this email any time &mdash; it reaches a real person. You can unsubscribe from any newsletter with one click.
      </p>
    </div>
    <p style="margin:18px 0 0;font-size:12px;line-height:1.6;color:#8a97a6;text-align:center;">
      Beat the Scam &middot; Independent UK consumer-protection guides<br>
      Educational content only &mdash; not legal or financial advice.
    </p>
  </div>
</body>
</html>`;

const WELCOME_TEXT = `You're on the list.

Thanks for subscribing to Beat the Scam. You'll get plain-English scam alerts and new guides as the latest tactics appear — the checks you can run in under a minute before you click, pay, or share anything.

Got a suspicious text, email, or call? Run it through our free AI scam checker:
https://beatthescam.com/check/

Reply to this email any time — it reaches a real person. You can unsubscribe from any newsletter with one click.

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

  // Auth / config
  const apiKey     = process.env.RESEND_API_KEY;
  const audienceId = process.env.RESEND_AUDIENCE_ID;
  if (!apiKey || !audienceId) {
    console.error("RESEND_API_KEY or RESEND_AUDIENCE_ID not set");
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
      body: JSON.stringify({ ok: true }),
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

  // ─── Add the contact to the Resend audience ────────────────────────────────
  try {
    const addRes = await fetch(`https://api.resend.com/audiences/${audienceId}/contacts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${apiKey}`,
      },
      body: JSON.stringify({ email, unsubscribed: false }),
    });

    if (!addRes.ok) {
      const errText = await addRes.text();
      // A duplicate contact is not a user-facing error — they're already in.
      const isDuplicate = addRes.status === 409 || /already\s*exists|duplicate/i.test(errText);
      if (!isDuplicate) {
        console.error("Resend add-contact error:", addRes.status, errText);
        return {
          statusCode: 502,
          headers: corsHeaders,
          body: JSON.stringify({ error: "Could not complete signup. Please try again shortly." }),
        };
      }
      // Already subscribed — succeed silently without re-sending the welcome.
      return {
        statusCode: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json", "Cache-Control": "no-store" },
        body: JSON.stringify({ ok: true, already: true }),
      };
    }
  } catch (err) {
    console.error("Resend add-contact threw:", err);
    return {
      statusCode: 502,
      headers: corsHeaders,
      body: JSON.stringify({ error: "Could not complete signup. Please try again shortly." }),
    };
  }

  // ─── Send the welcome email (best-effort — never fail the signup on this) ───
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
        subject: "You're on the list — Beat the Scam alerts",
        html: WELCOME_HTML,
        text: WELCOME_TEXT,
      }),
    });
    if (!mailRes.ok) {
      console.error("Welcome email non-OK:", mailRes.status, await mailRes.text());
    }
  } catch (err) {
    // Log but still report success — the contact is saved either way.
    console.error("Welcome email failed (non-fatal):", err);
  }

  return {
    statusCode: 200,
    headers: { ...corsHeaders, "Content-Type": "application/json", "Cache-Control": "no-store" },
    body: JSON.stringify({ ok: true }),
  };
};
