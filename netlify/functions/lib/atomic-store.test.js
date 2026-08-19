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

test("a losing racer retries against the winner's value, so no increment is lost", async () => {
  // Two invocations both read count:9 against a cap of 10. Without CAS both
  // write count:10 and the second call slips past the limit.
  const store = fakeStore({ value: { count: 9 }, etag: "e1" });
  const first = await atomicUpdate(store, "k", zero, inc);   // wins, count -> 10
  assert.deepStrictEqual(first, { count: 10 });
  const second = await atomicUpdate(store, "k", zero, inc);  // must see 10, not 9
  assert.deepStrictEqual(second, { count: 11 },
    "the second writer must re-read after losing, not overwrite with a stale value");
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
