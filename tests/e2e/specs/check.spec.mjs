// E2E: the /check/ AI scam checker — real page JS + real check-scam.js handler,
// Anthropic stubbed by the harness (steered via E2E_* markers in the message).
import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";

// Assert DOM links against the function's REAL allow-list, so the test tracks
// the canon instead of a hand-copied host list.
const { isAllowedReportUrl } = createRequire(import.meta.url)(
  "../../../netlify/functions/lib/allowed-domains.js");

let n = 0;
test.beforeEach(async ({ context, baseURL }) => {
  // Unique per-test client IP → no cross-test rate-limit bleed.
  await context.addCookies([
    { name: "e2e_ip", value: `check-${Date.now()}-${++n}`, url: baseURL },
  ]);
  // Pre-decide the cookie choice so the fallback consent bar never overlays,
  // and seal the browser: only the harness origin is reachable (no GA/AdSense/CMP).
  await context.addInitScript(() => {
    try { localStorage.setItem("bts_cookie_pref_v1", "rejected"); } catch {}
  });
  await context.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, r => r.abort());
});

async function submit(page, message) {
  await page.goto("/check/");
  await page.fill("#scamInput", message);
  await page.click("#checkBtn");
}

test("returns a verdict with canon-approved reporting links, announced accessibly", async ({ page }) => {
  await submit(page, "Your Royal Mail parcel is on hold. Pay 1.45 to release it: rm-parcel-uk.example/pay");

  const result = page.locator("#resultContent");
  await expect(result).toBeVisible();
  await expect(page.locator(".checker-verdict")).toContainText("Likely a scam");
  await expect(page.locator(".checker-confidence")).toContainText("high confidence");
  await expect(result).toContainText("parcel-delivery payment scam");
  // The 7726 shortcode must SURVIVE the contact scrubber (safe-code allow-list).
  await expect(result).toContainText("Forward the text to 7726");

  const hrefs = await result.locator("a").evaluateAll(as => as.map(a => a.href));
  expect(hrefs.length).toBeGreaterThan(0);
  for (const href of hrefs) {
    expect(isAllowedReportUrl(href), `${href} must be a canon-approved reporting host`).toBe(true);
  }

  // The async result is announced: the result column is the live region and
  // takes focus (regression guard for the "silent async result" a11y fix).
  await expect(page.locator("#resultCol")).toHaveAttribute("aria-live", "polite");
  await expect(page.locator("#resultCol")).toBeFocused();
});

test("never presents 'probably legitimate' with high confidence", async ({ page }) => {
  await submit(page, "E2E_LEGIT Hi, your parcel arrives tomorrow, no action needed from you.");
  await expect(page.locator(".checker-verdict")).toContainText("Probably legitimate");
  // The stub replies confidence:"high"; the function must downgrade to low.
  await expect(page.locator(".checker-confidence")).toContainText("low confidence");
});

test("prompt-injected links, numbers and emails never reach the result", async ({ page }) => {
  await submit(page, "E2E_INJECT You have won a refund, contact our recovery desk now to claim it.");

  const result = page.locator("#resultContent");
  await expect(result).toBeVisible();
  await expect(page.locator(".checker-verdict")).toContainText("Likely a scam");

  // The attacker host appears in the stubbed model output three ways
  // (reporting link, summary URL, red-flag email) — none may survive.
  expect(await result.innerHTML()).not.toContain("evil-fraudhelp.example");
  await expect(result).toContainText("[number removed");
  await expect(result).toContainText("[link removed");
  await expect(result).toContainText("[contact removed");

  // …while the genuine canon links are still offered.
  const hrefs = await result.locator("a").evaluateAll(as => as.map(a => a.href));
  expect(hrefs.length).toBeGreaterThan(0);
  for (const href of hrefs) expect(isAllowedReportUrl(href)).toBe(true);
});

test("an upstream failure shows the graceful error message", async ({ page }) => {
  await submit(page, "E2E_UPSTREAM_FAIL something suspicious happened to me today");
  await expect(page.locator("#resultContent")).toContainText("could not be reached right now");
});

test.describe("API contract", () => {
  const ip = () => ({ "x-e2e-ip": `api-${Date.now()}-${Math.random().toString(36).slice(2)}` });

  test("rejects a hostile Origin outright (server-side, not just CORS)", async ({ request }) => {
    const res = await request.post("/api/check-scam", {
      headers: { origin: "https://evil.example", ...ip() },
      data: { message: "is this message a scam or not?", type: "email" },
    });
    expect(res.status()).toBe(403);
  });

  test("rejects wrong method, short message, and oversized body", async ({ request }) => {
    expect((await request.get("/api/check-scam")).status()).toBe(405);

    const short = await request.post("/api/check-scam", {
      headers: ip(), data: { message: "hey", type: "email" },
    });
    expect(short.status()).toBe(400);

    const big = await request.post("/api/check-scam", {
      headers: { "content-type": "application/json", ...ip() },
      data: JSON.stringify({ message: "x".repeat(20_000), type: "email" }),
    });
    expect(big.status()).toBe(413);
  });

  test("returns 502 when the model replies with non-JSON", async ({ request }) => {
    const res = await request.post("/api/check-scam", {
      headers: ip(),
      data: { message: "E2E_BAD_JSON please analyse this strange message", type: "email" },
    });
    expect(res.status()).toBe(502);
    expect((await res.json()).error).toBe("Invalid response from AI");
  });

  test("responses are never cacheable", async ({ request }) => {
    const res = await request.post("/api/check-scam", {
      headers: ip(),
      data: { message: "please check this suspicious text for me", type: "SMS or text message" },
    });
    expect(res.status()).toBe(200);
    expect(res.headers()["cache-control"]).toBe("no-store");
    expect(res.headers()["x-content-type-options"]).toBe("nosniff");
  });

  test("per-IP rate limit trips at the 11th call with Retry-After", async ({ request }) => {
    const headers = { "x-e2e-ip": `ratelimit-${Date.now()}` };
    let last;
    for (let i = 0; i < 11; i++) {
      last = await request.post("/api/check-scam", {
        headers,
        data: { message: "check this message for scam signals please", type: "email" },
      });
    }
    expect(last.status()).toBe(429);
    expect(last.headers()["retry-after"]).toBe("60");
  });
});
