"use strict";

const test = require("node:test");
const assert = require("node:assert");

test("refuses checker requests when the durable spend store is unavailable", async () => {
  const originalFetch = global.fetch;
  const originalKey = process.env.ANTHROPIC_API_KEY;
  process.env.ANTHROPIC_API_KEY = "test-key";
  global.fetch = async () => {
    throw new Error("the upstream model must not be called without a durable budget");
  };

  delete require.cache[require.resolve("../check-scam")];
  const { handler } = require("../check-scam");
  try {
    const result = await handler({
      httpMethod: "POST",
      headers: { "x-nf-client-connection-ip": "203.0.113.7" },
      body: JSON.stringify({ message: "Please verify this suspicious message.", type: "email" }),
    });
    assert.strictEqual(result.statusCode, 503);
    assert.match(result.body, /very busy/i);
  } finally {
    global.fetch = originalFetch;
    if (originalKey === undefined) delete process.env.ANTHROPIC_API_KEY;
    else process.env.ANTHROPIC_API_KEY = originalKey;
    delete require.cache[require.resolve("../check-scam")];
  }
});
