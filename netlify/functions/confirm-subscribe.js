// netlify/functions/confirm-subscribe.js
// Step 2 of double opt-in. The visitor clicks the signed link in the
// confirmation email sent by subscribe.js. Only here is the contact actually
// added to the Resend Audience and the welcome email sent.
//
// Security / safety model (mirrors unsubscribe.js):
//  - The link carries an HMAC-signed token, so only the address that was
//    submitted can be confirmed — it can't be swapped without invalidating the
//    signature. The token signs "confirm:<email>", so it is NOT usable as an
//    unsubscribe token (which signs the bare email). Verified with timingSafeEqual.
//  - GET NEVER mutates state — it only renders a confirm page. Only POST adds
//    the contact, so email link-prefetchers / security scanners (which GET every
//    link) cannot auto-confirm a subscription — which is the whole point of
//    double opt-in.
//  - Fails CLOSED: with no UNSUBSCRIBE_SECRET set, tokens are neither minted
//    (subscribe.js) nor accepted here.

const crypto = require("crypto");

const RESEND_BASE   = "https://api.resend.com";
const CONTACT_EMAIL = "hello@beatthescam.com";
const FROM_ADDRESS  = "Beat the Scam <alerts@updates.beatthescam.com>";
const REPLY_TO      = "hello@beatthescam.com";
const SITE          = "https://beatthescam.com";

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

// ─── TOKEN ────────────────────────────────────────────────────────────────────
// Returns the verified email, or null if the token is missing / malformed / has
// a bad signature / the secret is unset (fail closed). Signs "confirm:<email>".
function verifyConfirmToken(t) {
  const secret = process.env.UNSUBSCRIBE_SECRET || "";
  if (!t || !secret) return null;
  const parts = String(t).split(".");
  if (parts.length !== 2) return null;
  const [e, sig] = parts;
  let email;
  try { email = Buffer.from(e, "base64url").toString("utf8"); } catch { return null; }
  if (!email || email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return null;
  const expected = crypto.createHmac("sha256", secret).update("confirm:" + email).digest("base64url");
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  return email;
}

// Unsubscribe token for the welcome email's one-click link — signs the BARE
// email, matching what unsubscribe.js verifies.
function unsubToken(email) {
  const secret = process.env.UNSUBSCRIBE_SECRET || "";
  if (!secret) return "";
  const e   = Buffer.from(email, "utf8").toString("base64url");
  const sig = crypto.createHmac("sha256", secret).update(email).digest("base64url");
  return `${e}.${sig}`;
}

// ─── RESEND ───────────────────────────────────────────────────────────────────
// Add (or re-activate) the contact in the audience. A duplicate is success —
// the end state we want is "subscribed". Returns true on success.
async function addContact(email) {
  const apiKey     = process.env.RESEND_API_KEY;
  const audienceId = process.env.RESEND_AUDIENCE_ID;
  if (!apiKey || !audienceId || !email) return false;
  try {
    const res = await fetch(`${RESEND_BASE}/audiences/${audienceId}/contacts`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
      body: JSON.stringify({ email, unsubscribed: false }),
    });
    if (res.ok) return true;
    const txt = await res.text();
    if (res.status === 409 || /already\s*exists|duplicate/i.test(txt)) return true;
    console.error("confirm add-contact non-ok:", res.status, txt.slice(0, 300));
    return false;
  } catch (err) {
    console.error("confirm add-contact threw:", err);
    return false;
  }
}

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
        Your subscription is confirmed. You'll get plain-English scam alerts and new guides as the latest tactics appear &mdash; the checks you can run in under a minute before you click, pay, or share anything.
      </p>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.6;color:#5b6878;">
        Got a suspicious text, email, or call right now? Run it through our free AI scam checker:
      </p>
      <p style="margin:0 0 28px;">
        <a href="https://beatthescam.com/check/" style="display:inline-block;background:#1d4ed8;color:#ffffff;text-decoration:none;font-weight:700;font-size:16px;padding:13px 22px;border-radius:999px;">Check a message &rarr;</a>
      </p>
      <p style="margin:0;font-size:14px;line-height:1.6;color:#5b6878;">
        Reply to this email any time &mdash; it reaches a real person.
      </p>
      __UNSUB_HTML__
    </div>
    <p style="margin:18px 0 0;font-size:12px;line-height:1.6;color:#8a97a6;text-align:center;">
      Beat the Scam &middot; Independent UK consumer-protection guides<br>
      Educational content only &mdash; not legal or financial advice.
    </p>
  </div>
</body>
</html>`;

const WELCOME_TEXT = `You're on the list.

Your subscription to Beat the Scam is confirmed. You'll get plain-English scam alerts and new guides as the latest tactics appear — the checks you can run in under a minute before you click, pay, or share anything.

Got a suspicious text, email, or call? Run it through our free AI scam checker:
https://beatthescam.com/check/

Reply to this email any time — it reaches a real person.
__UNSUB_TEXT__
Beat the Scam · Independent UK consumer-protection guides
Educational content only — not legal or financial advice.`;

async function sendWelcome(email) {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) return;
  const token     = unsubToken(email);
  const unsubUrl  = token ? `${SITE}/api/unsubscribe?t=${encodeURIComponent(token)}` : "";
  const unsubHtml = unsubUrl
    ? `<p style="margin:14px 0 0;font-size:12px;line-height:1.6;color:#8a97a6;">Don't want these emails? <a href="${unsubUrl}" style="color:#1d4ed8;">Unsubscribe</a>.</p>`
    : "";
  const unsubText = unsubUrl ? `Unsubscribe: ${unsubUrl}` : "";
  try {
    const res = await fetch(`${RESEND_BASE}/emails`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
      body: JSON.stringify({
        from: FROM_ADDRESS,
        to: [email],
        reply_to: REPLY_TO,
        subject: "You're on the list — Beat the Scam alerts",
        html: WELCOME_HTML.replace("__UNSUB_HTML__", unsubHtml),
        text: WELCOME_TEXT.replace("__UNSUB_TEXT__", unsubText),
        ...(unsubUrl ? { headers: {
          "List-Unsubscribe": `<${unsubUrl}>`,
          "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        } } : {}),
      }),
    });
    if (!res.ok) console.error("Welcome email non-OK:", res.status, (await res.text()).slice(0, 300));
  } catch (err) {
    console.error("Welcome email failed (non-fatal):", err);
  }
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

function htmlResponse(statusCode, body) {
  return {
    statusCode,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex",
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
    return { statusCode: 429, headers: { "Retry-After": "60", "Cache-Control": "no-store" }, body: "Too many requests" };
  }

  const token = (event.queryStringParameters && event.queryStringParameters.t) || "";
  const email = verifyConfirmToken(token);

  // ─── POST: this is where the contact is actually added + welcomed. Reached by
  //     our own confirm-page form submit.
  if (event.httpMethod === "POST") {
    if (!email) {
      return htmlResponse(200, page("Confirm subscription",
        `<p style="font-size:16px;">This confirmation link is invalid or has expired. Please subscribe again from <a href="https://beatthescam.com/" style="color:#1d4ed8;">beatthescam.com</a>.</p>`));
    }
    const added = await addContact(email);
    if (added) await sendWelcome(email);
    return htmlResponse(200,
      added
        ? page("Subscribed", `<p style="font-size:16px;">You're confirmed and on the list &#9989; Check your inbox for a welcome email.</p>`)
        : page("Confirm subscription", `<p style="font-size:16px;">We couldn't finish that just now. Please try again, or email <a href="mailto:${CONTACT_EMAIL}" style="color:#1d4ed8;">${CONTACT_EMAIL}</a>.</p>`)
    );
  }

  if (event.httpMethod !== "GET") {
    return { statusCode: 405, headers: { "Cache-Control": "no-store" }, body: "Method not allowed" };
  }

  // ─── GET: render a confirm page only. NEVER mutates (prefetch/scanner-safe).
  if (!email) {
    return htmlResponse(200, page("Confirm subscription",
      `<p style="font-size:16px;">This confirmation link is invalid or has expired. Please subscribe again from <a href="https://beatthescam.com/" style="color:#1d4ed8;">beatthescam.com</a>.</p>`));
  }
  const action = `/api/confirm-subscribe?t=${encodeURIComponent(token)}`;
  return htmlResponse(200, page("Confirm subscription",
    `<p style="font-size:16px;">Confirm your subscription to Beat the Scam scam alerts?</p>`
    + `<form method="POST" action="${action}" style="margin-top:20px;">`
    + `<button type="submit" style="background:#1d4ed8;color:#fff;border:0;border-radius:999px;font-size:16px;font-weight:700;padding:12px 22px;cursor:pointer;">Confirm subscription</button>`
    + `</form>`
    + `<p style="font-size:13px;color:#5b6878;margin-top:16px;">Didn't request this? Just close this page — nothing happens until you confirm.</p>`));
};
