// Playwright config for the Beat the Scam E2E suite. The webServer is the
// hermetic harness in harness/server.mjs — it serves the committed dist/ plus
// the real Netlify Function handlers with stubbed upstreams, so the suite
// needs a built dist/ but no network, secrets, or Netlify CLI.
import { defineConfig } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.E2E_PORT || 8877);
const BASE = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./specs",
  // One shared harness process holds the functions' in-memory rate-limit maps;
  // serial workers keep that state deterministic (per-test e2e_ip cookies keep
  // tests isolated from each other's limiters regardless).
  workers: 1,
  timeout: 30_000,
  reporter: [["list"]],
  use: {
    baseURL: BASE,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: {
    command: "node harness/server.mjs",
    cwd: __dirname,
    url: `${BASE}/__e2e__/health`,
    reuseExistingServer: !process.env.CI,
    stdout: "pipe",
    stderr: "pipe",
  },
});
