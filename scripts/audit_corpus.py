#!/usr/bin/env python3
"""
audit_corpus.py — one-time (re-runnable) accuracy audit of the whole corpus.

Runs the DETERMINISTIC accuracy gate over every guide in content/posts.json,
writes a per-guide claim manifest to content/manifests/<slug>.json, and prints a
summary of the high-stakes claims it detected for a human spot-check. No API key
/ LLM judge needed (deterministic only). Re-runnable; the only side effect is
writing manifests (skip with --no-write).

    python3 scripts/audit_corpus.py
    python3 scripts/audit_corpus.py --no-write          # report only

Exit code: non-zero if any BLOCK-tier claim is found in a LIVE guide (there
should be none — the gate quarantines those before publish).
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_gate import run_gate, build_manifest, write_manifest, SEVERITY_BLOCK


def main() -> int:
    ap = argparse.ArgumentParser(description="One-time deterministic corpus accuracy audit")
    ap.add_argument("--posts", default="content/posts.json")
    ap.add_argument("--manifests", default="content/manifests",
                    help="manifest directory (read existing model provenance from here)")
    ap.add_argument("--no-write", action="store_true", help="report only; don't write manifests")
    args = ap.parse_args()

    posts = json.loads(Path(args.posts).read_text(encoding="utf-8"))
    mdir = Path(args.manifests)
    by_type = Counter()
    blocks = []                    # (slug, claim)
    flags = defaultdict(list)      # type -> [(slug, text)]
    written = 0

    def existing_model(slug: str):
        """Preserve the drafting model recorded by the generation path — a
        deterministic re-audit must not wipe provenance to null."""
        mp = mdir / f"{slug}.json"
        if mp.exists():
            try:
                return json.loads(mp.read_text(encoding="utf-8")).get("model")
            except (ValueError, OSError):
                return None
        return None

    for p in posts:
        result = run_gate(p, use_llm=False)   # deterministic only
        model = existing_model(p.get("slug", ""))
        man = build_manifest(p, result, model=model, today=p.get("date"))
        if not args.no_write:
            write_manifest(p, result, model=model, today=p.get("date"))
            written += 1
        for c in man["claims"]:
            by_type[c["type"]] += 1
            if c["severity"] == SEVERITY_BLOCK:
                blocks.append((p["slug"], c))
            else:
                flags[c["type"]].append((p["slug"], c["text"]))

    print(f"Audited {len(posts)} guides | manifests written: {written}")
    print(f"Detected claim types: {dict(by_type)}\n")

    if blocks:
        print(f"BLOCK-tier claims in LIVE guides ({len(blocks)}) — these should not exist, FIX:")
        for slug, c in blocks:
            print(f"   [{c['type']}] {slug}: {c['text']}")
    else:
        print("OK — 0 BLOCK-tier claims in live guides (deterministic).")

    print("\nFLAG-tier claims to verify (by type):")
    for t, items in sorted(flags.items()):
        print(f"  {t} ({len(items)}):")
        for slug, text in items:
            print(f"     {slug}: {text}")

    return 1 if blocks else 0


if __name__ == "__main__":
    raise SystemExit(main())
