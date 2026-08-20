// E2E: the newsletter double opt-in — the site-wide footer form (assets/app.js)
// through the real subscribe.js / confirm-subscribe.js / unsubscribe.js
// handlers, with Resend stubbed by the harness. The stub captures every "sent"
// email, so the tests walk the genuine token round-trip: the confirm link is
// extracted from the captured confirmation email exactly as a reader would use it.
import { test, expect } from "@playwright/test";

const CONFIRM_LINK_RE = /https:\/\/beatthescam\.com(\/api\/confirm-subscribe\?t=[^\s"<]+)/;

async function getState(request) {
  return (await request.get("/__e2e__/state")).json();
}

let n = 0;
test.beforeEach(async ({ context, baseURL, request }) => {
  await request.post("/__e2e__/reset");
  await context.addCookies([
    { name: "e2e_ip", value: `nl-${Date.now()}-${++n}`, url: baseURL },
  ]);
  await context.addInitScript(() => {
    try { localStorage.setItem("bts_cookie_pref_v1", "rejected"); } catch {}
  });
  await context.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, r => r.abort());
});

async function subscribeAs(page, email) {
  await page.goto("/");
  await page.fill("#nl-email", email);
  await page.check("#nl-consent");
  await page.click("#nl-submit");
}

test("full double opt-in: subscribe → confirm email → confirm page → audience + welcome → one-click unsubscribe", async ({ page, request }) => {
  const email = `e2e-${Date.now()}@example.com`;

  // 1. Subscribe from the site-wide footer form.
  await subscribeAs(page, email);
  const msg = page.locator("#nl-msg");
  await expect(msg).toContainText("Almost there");
  await expect(msg).toHaveClass(/is-success/);

  // 2. Exactly one confirmation email "sent"; the audience is still untouched.
  let st = await getState(request);
  expect(st.emails).toHaveLength(1);
  expect(st.emails[0].to).toEqual([email]);
  expect(st.emails[0].subject).toBe("Confirm your Beat the Scam subscription");
  expect(Object.keys(st.audience)).toHaveLength(0);

  // 3. Extract the confirm link a reader would click (rebased onto the harness).
  const link = st.emails[0].text.match(CONFIRM_LINK_RE);
  expect(link, "confirmation email must contain a confirm link").toBeTruthy();

  // 4. GET renders the confirm page and must NOT subscribe (prefetch/scanner safety).
  await page.goto(link[1]);
  await expect(page.locator("body")).toContainText("Confirm your subscription to Beat the Scam scam alerts?");
  st = await getState(request);
  expect(Object.keys(st.audience)).toHaveLength(0);
  expect(st.emails).toHaveLength(1); // and no welcome email yet

  // 5. POST (the page's own button) adds the contact and redirects.
  await page.click("button[type=submit]");
  await page.waitForURL("**/newsletter-confirmed/");
  await expect(page.locator("[data-newsletter-confirmed='true']")).toBeAttached();

  st = await getState(request);
  expect(st.audience[email]).toEqual({ unsubscribed: false });
  expect(st.emails).toHaveLength(2);
  const welcome = st.emails[1];
  expect(welcome.to).toEqual([email]);
  expect(welcome.subject).toContain("You're on the list");

  // 6. The welcome email is RFC 8058 one-click-unsubscribe compliant — and the
  //    link works: POST flips the contact to unsubscribed.
  expect(welcome.headers["List-Unsubscribe-Post"]).toBe("List-Unsubscribe=One-Click");
  const unsub = String(welcome.headers["List-Unsubscribe"] || "")
    .match(/<https:\/\/beatthescam\.com(\/api\/unsubscribe\?t=[^>]+)>/);
  expect(unsub, "welcome email must carry a List-Unsubscribe URL").toBeTruthy();

  const res = await request.post(unsub[1], {
    headers: { "content-type": "application/x-www-form-urlencoded" },
    data: "List-Unsubscribe=One-Click",
  });
  expect(res.status()).toBe(200);
  expect(await res.text()).toContain("been unsubscribed");
  st = await getState(request);
  expect(st.audience[email]).toEqual({ unsubscribed: true });
});

test("re-confirming a previously unsubscribed address reactivates it", async ({ page, request }) => {
  const email = `resub-${Date.now()}@example.com`;
  await request.post("/__e2e__/seed-audience", { data: { email, unsubscribed: true } });

  await subscribeAs(page, email);
  await expect(page.locator("#nl-msg")).toContainText("Almost there");

  const st1 = await getState(request);
  const link = st1.emails[0].text.match(CONFIRM_LINK_RE);
  await page.goto(link[1]);
  await page.click("button[type=submit]");
  await page.waitForURL("**/newsletter-confirmed/");

  // Resend 409s the duplicate POST; the function must PATCH it back to subscribed.
  const st2 = await getState(request);
  expect(st2.audience[email]).toEqual({ unsubscribed: false });
});

test("an invalid or tampered confirm token shows the safe error and never mutates", async ({ page, request }) => {
  await page.goto("/api/confirm-subscribe?t=AAAAnot-a-real-token");
  await expect(page.locator("body")).toContainText("invalid or has expired");

  const post = await request.post("/api/confirm-subscribe?t=AAAAnot-a-real-token");
  expect(await post.text()).toContain("invalid or has expired");

  const st = await getState(request);
  expect(Object.keys(st.audience)).toHaveLength(0);
  expect(st.emails).toHaveLength(0);
});

test("client-side validation blocks bad input before any request is made", async ({ page, request }) => {
  await page.goto("/");
  await page.fill("#nl-email", "not-an-email");
  await page.check("#nl-consent");
  await page.click("#nl-submit");
  await expect(page.locator("#nl-msg")).toContainText("valid email address");

  await page.fill("#nl-email", "someone@example.com");
  await page.uncheck("#nl-consent");
  await page.click("#nl-submit");
  await expect(page.locator("#nl-msg")).toContainText("tick the box");

  const st = await getState(request);
  expect(st.emails).toHaveLength(0);
});

test("honeypot submissions pretend success and send nothing", async ({ page, request }) => {
  await page.goto("/");
  await page.evaluate(() => {
    document.getElementById("nl-website").value = "https://spam.example";
  });
  await page.fill("#nl-email", `bot-${Date.now()}@example.com`);
  await page.check("#nl-consent");
  await page.click("#nl-submit");
  await expect(page.locator("#nl-msg")).toContainText("Almost there");

  const st = await getState(request);
  expect(st.emails).toHaveLength(0);
  expect(Object.keys(st.audience)).toHaveLength(0);
});

test("a failed confirmation send surfaces the retry message", async ({ page }) => {
  // The stub 500s any send to an address containing "fail-send".
  await subscribeAs(page, `fail-send-${Date.now()}@example.com`);
  const msg = page.locator("#nl-msg");
  await expect(msg).toContainText("Could not send the confirmation email");
  await expect(msg).toHaveClass(/is-error/);
});

test("subscribe rejects a hostile Origin outright", async ({ request }) => {
  const res = await request.post("/api/subscribe", {
    headers: { origin: "https://evil.example" },
    data: { email: "x@example.com", consent: true, website: "" },
  });
  expect(res.status()).toBe(403);
});
