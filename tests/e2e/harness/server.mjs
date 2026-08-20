// tests/e2e/harness/server.mjs
// Local end-to-end harness for the two dynamic surfaces. Serves the committed
// dist/ the way Netlify does (static files + the /api/* function routes), and
// invokes the REAL Netlify Function handlers in-process with their two
// upstreams (api.anthropic.com, api.resend.com) stubbed — a test run never
// leaves the machine, never spends API budget, and never sends a real email.
//
// Netlify Blobs is not configured locally, so the functions' durable controls
// (daily caps, single-use confirm guard) fall back / fail open by design; those
// code paths are covered by netlify/functions/lib/atomic-store.test.js instead.
//
// Test hooks, all under /__e2e__/ (never part of the deployed site):
//   GET  /__e2e__/health          200 once up (Playwright webServer gate)
//   GET  /__e2e__/state           {emails:[…captured sends…], audience:{email:{unsubscribed}}}
//   POST /__e2e__/reset           clear captured emails + audience
//   POST /__e2e__/seed-audience   {email, unsubscribed} → pre-seed a contact
//
// Request identity the harness understands:
//   x-e2e-ip header (API tests) or e2e_ip cookie (browser tests) becomes the
//   client IP the functions see, isolating each test from the per-IP limiters.
//
// Origin: the browser's real Origin (http://127.0.0.1:PORT) is rewritten to
// https://beatthescam.com before a handler runs — the same-origin production
// case. Any OTHER Origin passes through untouched, so origin-rejection tests
// can exercise the 403 path.

import http from "node:http";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..", "..", "..");
const DIST = path.join(ROOT, "dist");
const PORT = Number(process.env.E2E_PORT || 8877);

// Env the functions require. Force-set — tests must never see real secrets,
// and with the upstream stubs below nothing real could be reached anyway.
process.env.ANTHROPIC_API_KEY  = "e2e-anthropic-key";
process.env.RESEND_API_KEY     = "e2e-resend-key";
process.env.RESEND_AUDIENCE_ID = "e2e-audience";
process.env.UNSUBSCRIBE_SECRET = "e2e-unsubscribe-secret-8f3c1c9f2ab34d0e";

// ─── Upstream stubs (installed BEFORE the function modules load) ─────────────
const state = {
  emails: [],          // every "sent" email, oldest first
  audience: new Map(), // email -> { unsubscribed }
};

const require_ = createRequire(import.meta.url);
const CANON = require_(path.join(ROOT, "netlify", "functions", "lib", "canon-routes.js"));

function jsonResponse(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { "content-type": "application/json" },
  });
}

// The message text steers the stub, so specs can trigger each path:
//   E2E_UPSTREAM_FAIL → Anthropic 500        E2E_BAD_JSON → non-JSON model text
//   E2E_INJECT → prompt-injected payload      E2E_LEGIT → legitimate verdict
function anthropicText(userText) {
  if (userText.includes("E2E_BAD_JSON")) {
    return "Hmm, this certainly smells like a scam, but I am not JSON.";
  }
  const links = CANON.EXAMPLE_REPORTING_LINKS.map(l => ({ name: l.name, url: l.url }));
  if (userText.includes("E2E_INJECT")) {
    // A prompt-injected reply: attacker link in reporting_links, dialable
    // number + link in the summary, attacker email in a red flag. The function
    // must strip every one before anything reaches the DOM.
    return JSON.stringify({
      verdict: "likely_scam",
      confidence: "high",
      summary: "This is a scam. For a refund call 020 7946 0958 or visit https://evil-fraudhelp.example/recover today.",
      red_flags: ["Tells you to email refunds@evil-fraudhelp.example straight away"],
      green_flags: [],
      recommended_actions: ["Do not reply to the sender"],
      reporting_links: [
        { name: "FraudHelp UK recovery desk", url: "https://evil-fraudhelp.example/report" },
        ...links,
      ],
    });
  }
  if (userText.includes("E2E_LEGIT")) {
    return JSON.stringify({
      verdict: "probably_legitimate",
      confidence: "high", // the function must downgrade this to "low"
      summary: "This looks like a genuine delivery notification from the courier's official domain.",
      red_flags: [],
      green_flags: ["Sender domain matches the courier's official website"],
      recommended_actions: ["Track the parcel by typing the courier's address into your browser yourself"],
      reporting_links: links,
    });
  }
  return JSON.stringify({
    verdict: "likely_scam",
    confidence: "high",
    summary: "This message follows the classic pattern of a parcel-delivery payment scam.",
    red_flags: [
      'Creates urgency with a small "release fee"',
      "Payment link does not match the courier's official domain",
    ],
    green_flags: [],
    recommended_actions: [
      "Do not click the link or pay anything",
      "Forward the text to 7726 so networks can block the sender",
      "Delete the message",
    ],
    reporting_links: links,
  });
}

async function stubAnthropic(init) {
  const req = JSON.parse(init.body);
  const userText = String(req?.messages?.[0]?.content || "");
  if (userText.includes("E2E_UPSTREAM_FAIL")) {
    return new Response("upstream boom", { status: 500 });
  }
  return jsonResponse({ content: [{ type: "text", text: anthropicText(userText) }] });
}

async function stubResend(url, init) {
  const method = (init.method || "GET").toUpperCase();
  const p = url.pathname;

  if (p === "/emails" && method === "POST") {
    const mail = JSON.parse(init.body);
    const to = Array.isArray(mail.to) ? mail.to : [mail.to];
    if (to.some(a => String(a).includes("fail-send"))) {
      return jsonResponse({ message: "e2e simulated send failure" }, 500);
    }
    state.emails.push({
      to, subject: mail.subject, html: mail.html, text: mail.text,
      headers: mail.headers || null,
    });
    return jsonResponse({ id: `e2e-mail-${state.emails.length}` });
  }

  if (/^\/audiences\/[^/]+\/contacts$/.test(p) && method === "POST") {
    const { email } = JSON.parse(init.body);
    // Real Resend 409s on an existing contact; confirm-subscribe then PATCHes
    // it back to subscribed — mirroring that here keeps the reactivation path honest.
    if (state.audience.has(email)) {
      return new Response("contact already exists", { status: 409 });
    }
    state.audience.set(email, { unsubscribed: false });
    return jsonResponse({ id: `e2e-contact-${state.audience.size}` });
  }

  const m = p.match(/^\/audiences\/[^/]+\/contacts\/(.+)$/) || p.match(/^\/contacts\/(.+)$/);
  if (m && (method === "PATCH" || method === "PUT")) {
    const email = decodeURIComponent(m[1]);
    const body = JSON.parse(init.body);
    const cur = state.audience.get(email) || { unsubscribed: false };
    cur.unsubscribed = !!body.unsubscribed;
    state.audience.set(email, cur);
    return jsonResponse({ id: "e2e-contact-patched" });
  }

  return jsonResponse({ message: `e2e stub: unhandled Resend call ${method} ${p}` }, 400);
}

globalThis.fetch = async (input, init = {}) => {
  const url = new URL(typeof input === "string" ? input : input.url);
  if (url.hostname === "api.anthropic.com") return stubAnthropic(init);
  if (url.hostname === "api.resend.com") return stubResend(url, init);
  // Anything else is a bug (or a new upstream the stubs don't know about yet) —
  // fail loudly rather than let a test touch the real network.
  console.error(`[e2e] BLOCKED unexpected upstream fetch: ${url.href}`);
  return jsonResponse({ error: `e2e harness: unexpected upstream ${url.hostname}` }, 599);
};

// ─── The real function handlers (loaded after env + fetch stubs) ─────────────
const FUNCTIONS = {
  "check-scam":        require_(path.join(ROOT, "netlify", "functions", "check-scam.js")).handler,
  "subscribe":         require_(path.join(ROOT, "netlify", "functions", "subscribe.js")).handler,
  "confirm-subscribe": require_(path.join(ROOT, "netlify", "functions", "confirm-subscribe.js")).handler,
  "unsubscribe":       require_(path.join(ROOT, "netlify", "functions", "unsubscribe.js")).handler,
};

// Mirrors the /api/* rules from netlify.toml + dist/_redirects.
const API_ROUTES = {
  "/api/check-scam":        "check-scam",
  "/api/subscribe":         "subscribe",
  "/api/confirm-subscribe": "confirm-subscribe",
  "/api/unsubscribe":       "unsubscribe",
};

async function invokeFunction(name, req, res, urlObj, bodyBuf) {
  const headers = { ...req.headers };

  const localOrigin = `http://${req.headers.host}`;
  if (headers.origin === localOrigin) headers.origin = "https://beatthescam.com";

  const cookieIp = /(?:^|;\s*)e2e_ip=([^;]+)/.exec(req.headers.cookie || "")?.[1];
  headers["x-nf-client-connection-ip"] =
    headers["x-e2e-ip"] || cookieIp || "203.0.113.77";

  const queryStringParameters = {};
  for (const [k, v] of urlObj.searchParams) queryStringParameters[k] = v;

  const event = {
    httpMethod: req.method,
    headers,
    queryStringParameters,
    body: bodyBuf.length ? bodyBuf.toString("utf8") : "",
  };

  let out;
  try {
    out = await FUNCTIONS[name](event);
  } catch (err) {
    console.error(`[e2e] function ${name} threw:`, err);
    out = { statusCode: 500, headers: {}, body: "harness: function threw" };
  }
  res.writeHead(out.statusCode || 200, out.headers || {});
  res.end(out.body || "");
}

// ─── Static file serving from dist/ ──────────────────────────────────────────
const MIME = {
  ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
  ".mjs": "text/javascript", ".json": "application/json", ".xml": "application/xml",
  ".txt": "text/plain; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".ico": "image/x-icon",
  ".webmanifest": "application/manifest+json", ".woff2": "font/woff2",
};

function notFound(res) {
  const f = path.join(DIST, "404.html");
  res.writeHead(404, { "content-type": "text/html; charset=utf-8" });
  if (fs.existsSync(f)) fs.createReadStream(f).pipe(res);
  else res.end("Not found");
}

function serveStatic(res, urlPath) {
  let file = path.normalize(path.join(DIST, decodeURIComponent(urlPath)));
  if (file !== DIST && !file.startsWith(DIST + path.sep)) return notFound(res);
  let st = fs.existsSync(file) ? fs.statSync(file) : null;
  if (st?.isDirectory()) {
    if (!urlPath.endsWith("/")) {
      res.writeHead(301, { location: urlPath + "/" });
      return res.end();
    }
    file = path.join(file, "index.html");
    st = fs.existsSync(file) ? fs.statSync(file) : null;
  }
  if (!st || !st.isFile()) return notFound(res);
  res.writeHead(200, { "content-type": MIME[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
}

// ─── Server ──────────────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
  try {
    const urlObj = new URL(req.url, `http://${req.headers.host || `127.0.0.1:${PORT}`}`);
    const p = urlObj.pathname;

    if (p === "/__e2e__/health") { res.writeHead(200); return res.end("ok"); }
    if (p === "/__e2e__/state") {
      res.writeHead(200, { "content-type": "application/json" });
      return res.end(JSON.stringify({
        emails: state.emails,
        audience: Object.fromEntries(state.audience),
      }));
    }
    if (p.startsWith("/__e2e__/") && req.method === "POST") {
      const chunks = [];
      for await (const c of req) chunks.push(c);
      const body = Buffer.concat(chunks).toString("utf8");
      if (p === "/__e2e__/reset") {
        state.emails.length = 0;
        state.audience.clear();
        res.writeHead(200); return res.end("reset");
      }
      if (p === "/__e2e__/seed-audience") {
        const { email, unsubscribed } = JSON.parse(body);
        state.audience.set(email, { unsubscribed: !!unsubscribed });
        res.writeHead(200); return res.end("seeded");
      }
    }

    const fn = API_ROUTES[p];
    if (fn) {
      const chunks = [];
      let size = 0;
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 1024 * 1024) { res.writeHead(413); return res.end("harness: body too large"); }
        chunks.push(chunk);
      }
      return invokeFunction(fn, req, res, urlObj, Buffer.concat(chunks));
    }

    if (req.method !== "GET" && req.method !== "HEAD") { res.writeHead(405); return res.end(); }
    return serveStatic(res, p);
  } catch (err) {
    console.error("[e2e] harness error:", err);
    try { res.writeHead(500); res.end("harness error"); } catch { /* already sent */ }
  }
});

if (!fs.existsSync(path.join(DIST, "index.html"))) {
  console.error(`[e2e] dist/index.html not found under ${DIST} — run python3 scripts/build.py first (never while another build is running).`);
  process.exit(1);
}
server.listen(PORT, "127.0.0.1", () => {
  console.log(`[e2e] serving ${DIST} + function routes on http://127.0.0.1:${PORT}`);
});
