// node --test netlify/functions/lib/
//
// Covers the compare-and-set counter writes behind every durable limit on the
// site: the checker's per-IP rate limit and 2000-call/day spend cap, and the
// newsletter's per-address and daily send caps.
//
// This suite exists because a @netlify/blobs bump (#107, 10.7.12 -> 10.7.13)
// reached review with NO functions-level CI at all: package-lock.json was not
// in the Gate self-test path filter, and the only functions test covered
// reporting links. The CAS contract below is exactly what a Blobs upgrade can
// break silently — getWithMetadata returning {data, etag}, setJSON honouring
// onlyIfMatch / onlyIfNew, and a losing write reporting modified:false.

const test = require("node:test");
const assert = require("node:assert");

const { atomicUpdate, ATOMIC_MAX_ATTEMPTS } = require("./atomic-store");

// A fake Blobs store with real CAS semantics: a write lands only if its
// precondition still holds, exactly as the Blobs API specifies. Records every
// setJSON option so the tests can assert which precondition was sent.
function fakeStore({ value = undefined, etag = "e0", failGet = false } = {}) {
  const calls = [];
  return {
    calls,
    get value() { return value; },
    async getWithMetadata(key, opts) {
      calls.push({ op: "get", key, opts });
      if (failGet) throw new Error("store unavailable");
      if (value === undefined) return null;
      // Deep-copy on read: a real store deserializes fresh JSON each time, so an
      // in-place mutator cannot accumulate across attempts the way it would if
      // the fake handed back one shared object.
      return { data: JSON.parse(JSON.stringify(value)), etag };
    },
    async setJSON(key, next, opts) {
      calls.push({ op: "set", key, next: JSON.parse(JSON.stringify(next)), opts });
      if (opts && opts.onlyIfNew && value !== undefined) return { modified: false };
      if (opts && opts.onlyIfMatch && opts.onlyIfMatch !== etag) return { modified: false };
      value = next;
      etag = "e" + (Number(etag.slice(1)) + 1);
      return { modified: true };
    },
  };
}

const inc = (c) => { c.count++; return c; };
const zero = () => ({ count: 0 });

test("creates the key with onlyIfNew when it is absent", async () => {
  const store = fakeStore();
  const out = await atomicUpdate(store, "k", zero, inc);
  assert.deepStrictEqual(out, { count: 1 });
  const set = store.calls.find((c) => c.op === "set");
  assert.deepStrictEqual(set.opts, { onlyIfNew: true },
    "a create must be guarded by onlyIfNew, or a racer's value is clobbered");
  assert.strictEqual(set.opts.onlyIfMatch, undefined);
});

test("updates an existing key with onlyIfMatch on its etag", async () => {
  const store = fakeStore({ value: { count: 7 }, etag: "e9" });
  const out = await atomicUpdate(store, "k", zero, inc);
  assert.deepStrictEqual(out, { count: 8 });
  const set = store.calls.find((c) => c.op === "set");
  assert.deepStrictEqual(set.opts, { onlyIfMatch: "e9" },
    "an update must be conditional on the etag that was read");
});

test("a competing write between our read and our set loses the CAS, and the retry builds on the winner", async () => {
  // The scenario the whole helper exists for: two invocations both read
  // count:9 against a cap of 10. Without CAS both write 10 and the second
  // caller slips past the limit.
  //
  // The race has to happen INSIDE one atomicUpdate call to prove anything.
  // Two sequential calls never collide, never see modified:false, and never
  // enter the retry path — so they cannot show that a retry reads the
  // competitor's value (operator review, 2026-08-19).
  const store = fakeStore({ value: { count: 9 }, etag: "e1" });
  let raced = false;
  const realGet = store.getWithMetadata.bind(store);
  store.getWithMetadata = async (key, opts) => {
    const meta = await realGet(key, opts);          // we read {count:9}, etag e1
    if (!raced) {
      raced = true;
      // A competing invocation commits AFTER our read and BEFORE our set,
      // taking 9 -> 10 and rotating the etag. Our etag is now stale.
      await store.setJSON(key, { count: 10 }, undefined);
    }
    return meta;
  };

  const out = await atomicUpdate(store, "k", zero, inc);

  assert.deepStrictEqual(out, { count: 11 },
    "the retry must increment the winner's 10, not re-write 10 from its own stale 9");

  const sets = store.calls.filter((c) => c.op === "set");
  assert.strictEqual(sets.length, 3, "racer's write, our losing write, our winning write");

  // Our first attempt: conditional on the etag we read, carrying the stale 9+1.
  assert.deepStrictEqual(sets[1].opts, { onlyIfMatch: "e1" });
  assert.strictEqual(sets[1].next.count, 10);
  assert.strictEqual(await store.setJSON("probe", {}, { onlyIfMatch: "e1" })
    .then((r) => r.modified), false, "e1 is genuinely stale, so that attempt did lose");

  // The retry: re-read gave the winner's value and its NEW etag.
  assert.deepStrictEqual(sets[2].opts, { onlyIfMatch: "e2" },
    "the retry must send the etag from the re-read, not the stale one");
  assert.strictEqual(sets[2].next.count, 11);

  assert.strictEqual(store.calls.filter((c) => c.op === "get").length, 2,
    "losing the CAS must force a fresh read rather than a blind rewrite");
});

test("retries while setJSON keeps reporting modified:false, then succeeds", async () => {
  let losses = 3, writes = 0;
  const store = fakeStore({ value: { count: 1 } });
  const realSet = store.setJSON.bind(store);
  store.setJSON = async (k, n, o) => { writes++; return losses-- > 0 ? { modified: false } : realSet(k, n, o); };
  const out = await atomicUpdate(store, "k", zero, inc);
  assert.deepStrictEqual(out, { count: 2 }, "the retry must re-read, so the count advances by one");
  assert.strictEqual(writes, 4, "three losses then one successful write");
});

test("gives up after the attempt cap rather than looping forever", async () => {
  const store = fakeStore({ value: { count: 1 } });
  store.setJSON = async () => ({ modified: false });          // permanent contention
  const out = await atomicUpdate(store, "k", zero, inc);
  assert.strictEqual(out, null, "unbounded retry would hang the function");
  assert.strictEqual(store.calls.filter((c) => c.op === "get").length, ATOMIC_MAX_ATTEMPTS);
});

test("a failing read is treated as absent, so the counter still records", async () => {
  const store = fakeStore({ failGet: true });
  const out = await atomicUpdate(store, "k", zero, inc);
  assert.deepStrictEqual(out, { count: 1 });
});

test("on the final attempt, writes unconditionally rather than dropping the count", async () => {
  let n = 0;
  const store = fakeStore({ value: { count: 4 } });
  store.setJSON = async (k, next, opts) => {
    n++;
    if (opts) throw new Error("conditional write rejected");  // every guarded write fails
    return { modified: true };                                // the unconditional fallback
  };
  const out = await atomicUpdate(store, "k", zero, inc);
  assert.deepStrictEqual(out, { count: 5 }, "progress must still be recorded");
  assert.strictEqual(n, ATOMIC_MAX_ATTEMPTS + 1, "one unconditional write after the guarded ones");
});

test("returns null when even the unconditional fallback throws", async () => {
  const store = fakeStore({ value: { count: 1 } });
  store.setJSON = async () => { throw new Error("store down"); };
  const out = await atomicUpdate(store, "k", zero, inc);
  assert.strictEqual(out, null, "callers rely on null to fall back to the in-memory limiter");
});

test("the mutator sees the stored value, not the init default", async () => {
  const store = fakeStore({ value: { count: 41, windowStart: 123 } });
  const out = await atomicUpdate(store, "k", () => ({ count: 0, windowStart: 999 }), inc);
  assert.deepStrictEqual(out, { count: 42, windowStart: 123 });
});
