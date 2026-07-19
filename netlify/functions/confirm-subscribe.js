// netlify/functions/confirm-subscribe.js
// Step 2 of double opt-in. The visitor clicks the signed link in the
// confirmation email sent by subscribe.js. Only here is the contact actually
// added to the Resend Audience and the welcome email sent.
//
// Security / safety model (mirrors unsubscribe.js):
//  - The link carries an OPAQUE, ENCRYPTED token (AES-256-GCM): the email +
//    expiry are sealed under a key derived from UNSUBSCRIBE_SECRET, so the
//    address can't be read from a captured URL AND can't be swapped without
//    breaking the auth tag. The key is domain-separated by purpose, so a confirm
//    token is NOT usable as an unsubscribe token. The legacy dotted
//    base64url(email).base36(exp).sig (HMAC) format was dual-parsed during the
//    transition and RETIRED 2026-07-09: minting stopped 2026-06-25 and every
//    legacy confirm token carries a signed 7-day expiry, so none can still
//    verify. (unsubscribe.js keeps ITS legacy branch forever — those links
//    have no expiry and must keep working for compliance.)
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

// ─── SINGLE-USE TOKEN GUARD (Netlify Blobs) ───────────────────────────────────
// Confirm tokens stay valid for 7 days, but must work only ONCE. We record a
// consumed token's hash in a durable, shared store; a replay — e.g. an old link
// re-clicked after the user has since unsubscribed — is then refused, so it
// can't silently resurrect a cancelled subscription. Fails OPEN if Blobs is
// down (availability) — the token's signature + expiry still gate it.
let getStore = null;
try { ({ getStore } = require("@netlify/blobs")); } catch { /* dep/runtime absent — degrade gracefully */ }

function blobStore(name) {
  if (!getStore) return null;
  try { return getStore({ name, consistency: "strong" }); }
  catch { return null; }
}

// Canonicalise before hashing: Node's base64url decoder silently drops any
// character outside the base64url alphabet, so a token with junk appended
// (e.g. "token=", "token~", a trailing space) decodes to the IDENTICAL
// bytes — same email, still verifies — but hashing the raw string would give
// each variant a different key, letting the string be replayed indefinitely.
// By the time this runs, verifyConfirmToken has already decoded +
// authenticated the token, so hashing the decoded bytes is safe and collapses
// every such variant onto one key.
function consumedKey(token) {
  const basis = Buffer.from(String(token), "base64url");
  return "ct:" + crypto.createHash("sha256").update(basis).digest("hex").slice(0, 32);
}

// Atomically claim a token. Returns true if this caller claimed it (proceed),
// false if it was already consumed (reject the replay). onlyIfNew makes the
// claim race-safe; fails open if the store is unavailable.
async function consumeConfirmToken(token) {
  const store = blobStore("confirm-consumed");
  if (!store) return true;
  const key = consumedKey(token);
  try {
    const res = await store.setJSON(key, { t: Date.now() }, { onlyIfNew: true });
    if (res && res.modified === false) return false;   // already existed → replay
    return true;
  } catch {
    // Conditional write unsupported/errored — fall back to get-then-set (small
    // race window, acceptable for this control).
    try {
      if (await store.get(key)) return false;
      await store.setJSON(key, { t: Date.now() });
      return true;
    } catch { return true; }   // store unusable → fail open
  }
}

// Release a claimed token so a transient add failure doesn't burn a still-valid
// link (the user can click it again).
async function releaseConfirmToken(token) {
  const store = blobStore("confirm-consumed");
  if (!store) return;
  try { await store.delete(consumedKey(token)); } catch { /* best effort */ }
}

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
// New tokens encrypt their payload under a key derived from UNSUBSCRIBE_SECRET
// (rationale in subscribe.js: the legacy base64url(email)… format leaked the
// address from any captured URL). Confirm tokens are OPENED here; the welcome
// email's unsubscribe token is SEALED here. Keys are domain-separated by purpose
// ("confirm" vs "unsub"), so the two are not interchangeable.
const TOKEN_VERSION = 0x02;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// HKDF-SHA256(UNSUBSCRIBE_SECRET) → 32-byte AES-256 key, domain-separated by purpose.
function tokenKey(purpose) {
  const secret = process.env.UNSUBSCRIBE_SECRET || "";
  if (!secret) return null;
  return Buffer.from(crypto.hkdfSync("sha256", secret, "bts-token-kdf-v2", "aes256gcm:" + purpose, 32));
}

// Seal a payload object → opaque dotless base64url token. "" with no secret.
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

// ─── CONFIRM TOKEN ────────────────────────────────────────────────────────────
// Returns the verified email, or null if the token is missing / malformed / has
// a bad auth tag / has EXPIRED / the secret is unset (fail closed).
// The legacy dotted HMAC format is no longer accepted (retired 2026-07-09):
// minting stopped 2026-06-25 and its signed 7-day expiry means every legacy
// confirm link had lapsed by 2026-07-02, so the branch was pure dead weight
// (and its HMAC-over-decoded-email construction was malleable in ways the
// single-use guard couldn't key on).
function verifyConfirmToken(t) {
  const secret = process.env.UNSUBSCRIBE_SECRET || "";
  if (!t || !secret) return null;
  const p = openToken("confirm", t);
  if (!p || typeof p.e !== "string") return null;
  if (p.e.length > 254 || !EMAIL_RE.test(p.e)) return null;
  if (!Number.isFinite(p.x) || p.x * 1000 < Date.now()) return null;   // expired / malformed
  return p.e;
}

// Unsubscribe token for the welcome email's one-click link — now OPAQUE
// (AES-256-GCM), so a freshly-sent welcome email never embeds a recoverable
// address. unsubscribe.js dual-parses, so the bare-email legacy links previously
// minted keep working too.
function unsubToken(email) {
  return sealToken("unsub", { e: email });
}

// ─── RESEND ───────────────────────────────────────────────────────────────────
// Every Resend call gets an 8s timeout — well inside Netlify's ~10s function
// kill. Without it, a hung addContact after consumeConfirmToken means the
// platform kills the function before releaseConfirmToken runs, permanently
// burning a single-use link that was never actually used.
const RESEND_TIMEOUT_MS = 8000;
function fetchWithTimeout(url, opts) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), RESEND_TIMEOUT_MS);
  return fetch(url, { ...opts, signal: ctrl.signal }).finally(() => clearTimeout(timer));
}

// Add (or re-activate) the contact in the audience. A duplicate is success —
// the end state we want is "subscribed". Returns true on success.
async function addContact(email) {
  const apiKey     = process.env.RESEND_API_KEY;
  const audienceId = process.env.RESEND_AUDIENCE_ID;
  if (!apiKey || !audienceId || !email) return false;
  const auth = { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` };
  try {
    const res = await fetchWithTimeout(`${RESEND_BASE}/audiences/${audienceId}/contacts`, {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ email, unsubscribed: false }),
    });
    if (res.ok) return true;
    const txt = await res.text();
    if (res.status === 409 || /already\s*exists|duplicate/i.test(txt)) {
      // Existing contact — POST won't re-activate a previously unsubscribed
      // address, so PATCH it back to subscribed. This makes re-confirming a
      // reliable resubscribe instead of a silent no-op.
      try {
        const patch = await fetchWithTimeout(
          `${RESEND_BASE}/audiences/${audienceId}/contacts/${encodeURIComponent(email)}`,
          { method: "PATCH", headers: auth, body: JSON.stringify({ unsubscribed: false }) }
        );
        if (patch.ok) return true;
        console.error("confirm reactivate non-ok:", patch.status, (await patch.text()).slice(0, 300));
        return false;
      } catch (e) {
        console.error("confirm reactivate threw:", e);
        return false;
      }
    }
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
    const res = await fetchWithTimeout(`${RESEND_BASE}/emails`, {
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

function redirectResponse(location) {
  return {
    statusCode: 303,
    headers: {
      "Location": location,
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex",
      ...SECURITY_HEADERS,
    },
    body: "",
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
  const email = verifyConfirmToken(token);

  // ─── POST: this is where the contact is actually added + welcomed. Reached by
  //     our own confirm-page form submit.
  if (event.httpMethod === "POST") {
    if (!email) {
      return htmlResponse(200, page("Confirm subscription",
        `<p style="font-size:16px;">This confirmation link is invalid or has expired. Please subscribe again from <a href="https://beatthescam.com/" style="color:#1d4ed8;">beatthescam.com</a>.</p>`));
    }
    // Enforce single-use BEFORE mutating: a replayed link (e.g. re-clicked after
    // the user later unsubscribed) is refused here, so it can't silently
    // reactivate a cancelled subscription. Released again if the add fails, so a
    // transient error doesn't burn a still-valid link.
    const fresh = await consumeConfirmToken(token);
    if (!fresh) {
      return htmlResponse(200, page("Already confirmed",
        `<p style="font-size:16px;">This confirmation link has already been used &#9989; If you previously unsubscribed and want Beat the Scam alerts again, please <a href="https://beatthescam.com/" style="color:#1d4ed8;">subscribe again</a>.</p>`));
    }
    const added = await addContact(email);
    if (added) {
      await sendWelcome(email);
      return redirectResponse("/newsletter-confirmed/");
    }
    await releaseConfirmToken(token);   // add failed — let them retry the same link
    return htmlResponse(200, page("Confirm subscription",
      `<p style="font-size:16px;">We couldn't finish that just now. Please try again, or email <a href="mailto:${CONTACT_EMAIL}" style="color:#1d4ed8;">${CONTACT_EMAIL}</a>.</p>`));
  }

  if (event.httpMethod !== "GET") {
    return textResponse(405, "Method not allowed");
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
