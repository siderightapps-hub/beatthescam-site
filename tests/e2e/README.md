# End-to-end tests (Playwright)

Browser-level tests for the site's two dynamic surfaces:

- **`specs/check.spec.mjs`** — the `/check/` AI scam checker: verdict rendering,
  the canon reporting-link allow-list as seen in the DOM, the contact scrubber
  (prompt-injection containment), the never-high-confidence-safe rule, graceful
  upstream failure, and the API contract (origin rejection, method/size/rate
  limits, no-store headers).
- **`specs/newsletter.spec.mjs`** — the newsletter double opt-in end to end:
  footer form → captured confirmation email → real AES-GCM token round-trip →
  GET-never-mutates confirm page → contact added + RFC 8058 welcome email →
  one-click unsubscribe → reactivation on re-confirm. Plus honeypot, client
  validation, invalid tokens, send-failure and hostile-origin paths.

## How it works

`harness/server.mjs` serves the committed `dist/` the way Netlify does (static
files + the `/api/*` routes) and invokes the **real** function handlers from
`netlify/functions/` in-process. Their two upstreams are stubbed at the
`fetch` layer — `api.anthropic.com` (steered by `E2E_*` markers in the checker
message) and `api.resend.com` (captures "sent" emails and the audience) — and
the browser context aborts every non-localhost request. The suite therefore
needs **no network, no secrets, and no Netlify CLI**, spends no API budget,
and can never send a real email. Env secrets are force-overwritten with dummy
values, so a local `.env` is never read.

## Running

```
cd tests/e2e
npm install                      # once
npx playwright install chromium  # once
npx playwright test
```

Requires a built `dist/` (`python3 scripts/build.py` from the repo root) —
and never run that build, or this suite, while another build is in flight
(CLAUDE.md invariant 3). The harness only ever **reads** `dist/`.

## Not covered here (by design)

- **Netlify Blobs durable controls** — the daily spend caps, per-address
  quota, and single-use confirm-token guard need a Blobs store and fail
  open/fall back locally. Their logic is unit-tested in
  `netlify/functions/lib/atomic-store.test.js` (`node --test`).
- **The real Anthropic model and Resend delivery** — deliberately stubbed.
- **Legacy dotted unsubscribe tokens** — the dual-parse branch predates this
  suite and keeps working for compliance; it is exercised only in production.
