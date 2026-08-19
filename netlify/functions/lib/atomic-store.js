// Compare-and-set write helper for Netlify Blobs.
//
// The per-IP rate limits, the checker's daily spend cap and the newsletter's
// abuse caps are all read-modify-write counters. Without CAS, two concurrent
// invocations both read `count: 9`, both write `count: 10`, and one call slips
// past a limit of 10 — the failure the durable limiter exists to prevent.
//
// This lived twice, once in check-scam.js and once in subscribe.js, as
// byte-different copies of the same logic. Nothing tested either one, and the
// repo has already been bitten by hand-maintained duplicates drifting apart
// (the two canon fallbacks deleted on 2026-07-16). One copy, one test suite.
"use strict";

// Atomic read-modify-write on a Blobs key via compare-and-set (etag), so
// concurrent invocations can't clobber each other's increments and slip past a
// limit. `init()` supplies the value when the key is absent; `mutate(cur)`
// returns the next value. Retries under contention; on the final attempt falls
// back to an unconditional write so progress is still recorded rather than
// silently dropped. Returns the stored value, or null if the store is unusable.
async function atomicUpdate(store, key, init, mutate) {
  for (let attempt = 0; attempt < 5; attempt++) {
    let cur = null, etag = null;
    try {
      const meta = await store.getWithMetadata(key, { type: "json" });
      if (meta) { cur = meta.data; etag = meta.etag; }
    } catch { /* treat as absent and try to create */ }
    const next = mutate(cur || init());
    const opts = etag ? { onlyIfMatch: etag } : { onlyIfNew: true };
    try {
      const res = await store.setJSON(key, next, opts);
      if (!res || res.modified !== false) return next;   // wrote successfully
      // res.modified === false → a racer wrote first; loop and retry with fresh etag
    } catch (e) {
      if (attempt === 4) { try { await store.setJSON(key, next); return next; } catch { return null; } }
    }
  }
  return null;
}

module.exports = { atomicUpdate, ATOMIC_MAX_ATTEMPTS: 5 };
