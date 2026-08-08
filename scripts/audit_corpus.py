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
from content_gate import run_gate, build_manifest, SEVERITY_BLOCK


def main() -> int:
    ap = argparse.ArgumentParser(description="One-time deterministic corpus accuracy audit")
    ap.add_argument("--posts", default="content/posts.json")
    ap.add_argument("--manifests", default="content/manifests",
                    help="manifest directory (read existing model provenance from here)")
    ap.add_argument("--hubs", default="content/category-hubs.json",
                    help="hand-authored category hubs to include in the deterministic audit")
    ap.add_argument("--no-write", action="store_true", help="report only; don't write manifests")
    args = ap.parse_args()

    posts = json.loads(Path(args.posts).read_text(encoding="utf-8"))
    hubs_path = Path(args.hubs)
    hubs = json.loads(hubs_path.read_text(encoding="utf-8")) if hubs_path.exists() else {}
    mdir = Path(args.manifests)
    by_type = Counter()
    blocks = []                    # (slug, claim)
    flags = defaultdict(list)      # type -> [(slug, text)]
    written = 0

    def existing_manifest(slug: str):
        """Load the manifest written at generation time. A deterministic
        re-audit must preserve two things from it that it cannot reproduce:
        the drafting-model provenance, and the LLM judge's claims (this run
        is use_llm=False, so rebuilding from scratch would silently erase the
        judge findings the weekly digest reviews)."""
        mp = mdir / f"{slug}.json"
        if mp.exists():
            try:
                return json.loads(mp.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return None
        return None

    for p in posts:
        # is_draft=False: these are LIVE records, not drafts. A record that has
        # been consolidated legitimately carries `consolidated_into`, which is a
        # BLOCK only when a DRAFT asserts it about itself (operator review,
        # 2026-07-30 — this caller reported a false consolidation_evasion BLOCK
        # on the archived Hermes record).
        result = run_gate(p, use_llm=False, is_draft=False)   # deterministic only
        prior = existing_manifest(p.get("slug", "")) or {}
        man = build_manifest(p, result, model=prior.get("model"), today=p.get("date"))
        man["claims"] += [c for c in prior.get("claims", []) if c.get("type") == "judge"]
        if not args.no_write:
            mdir.mkdir(parents=True, exist_ok=True)
            mp = mdir / f"{p.get('slug', 'unknown')}.json"
            mp.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written += 1
        for c in man["claims"]:
            by_type[c["type"]] += 1
            if c["severity"] == SEVERITY_BLOCK:
                blocks.append((p["slug"], c))
            else:
                flags[c["type"]].append((p["slug"], c["text"]))

    # Hubs are hand-authored rather than generated, so they do not get claim
    # manifests. They still run through the exact deterministic gate here and
    # at build time, preventing this editorial surface from bypassing accuracy
    # checks again.
    for slug, hub in hubs.items():
        surface = dict(hub or {})
        surface.setdefault("slug", f"category-{slug}")
        surface.setdefault("category", slug)
        surface.setdefault("keywords", [])
        result = run_gate(surface, use_llm=False, is_draft=False)
        for issue in result.issues:
            by_type[issue.get("check")] += 1
            text = issue.get("span") or issue.get("detail", "")[:160]
            if issue.get("severity") == SEVERITY_BLOCK:
                blocks.append((surface["slug"], {"type": issue.get("check"), "text": text}))
            else:
                flags[issue.get("check")].append((surface["slug"], text))

    print(f"Audited {len(posts)} guides + {len(hubs)} category hubs | manifests written: {written}")
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
