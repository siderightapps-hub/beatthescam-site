#!/usr/bin/env python3
"""
similarity_report.py — find guide pairs that reuse each other's body copy.

The 2026-07-25 audit found five published pairs above 0.30 Jaccard similarity
on seven-word shingles (top pair 0.538, sharing an identical recovery
section). Google asks AdSense applicants for unique, differentiated content
and treats cookie-cutter pages as a scaled-content risk, so this is tracked as
a first-class content metric rather than a one-off audit finding.

`content_gate.check_similarity` blocks NEW drafts at publication time; this
script reports on the EXISTING corpus so remediation can be prioritised and
re-measured after each rewrite.

    python3 scripts/similarity_report.py                  # pairs >= 0.15
    python3 scripts/similarity_report.py --min 0.30       # only the worst
    python3 scripts/similarity_report.py --json out.json  # machine-readable
    python3 scripts/similarity_report.py --shared asos-copycat-scam-uk fake-ray-ban-website-scam-uk
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_gate import SIMILARITY_BLOCK_AT, SIMILARITY_FLAG_AT, body_shingles


def main() -> int:
    ap = argparse.ArgumentParser(description="Report near-duplicate guide bodies")
    ap.add_argument("--posts", default="content/posts.json")
    ap.add_argument("--min", type=float, default=SIMILARITY_FLAG_AT,
                     help=f"minimum Jaccard similarity to report (default {SIMILARITY_FLAG_AT})")
    ap.add_argument("--json", dest="json_out", default=None, help="also write results as JSON")
    ap.add_argument("--shared", nargs=2, metavar=("SLUG_A", "SLUG_B"),
                     help="print the shared word sequences for one pair instead of the corpus report")
    ap.add_argument("--include-redirected", action="store_true",
                     help="also compare consolidated records that 301 instead of rendering")
    args = ap.parse_args()

    posts = json.loads(Path(args.posts).read_text(encoding="utf-8"))
    if not args.include_redirected:
        # Consolidated records still live in posts.json but 301 instead of
        # rendering, so their (by definition near-identical) source text is not
        # a live duplicate-content problem. build.py is the authority on which
        # slugs those are.
        try:
            from build import ARTICLE_REDIRECTS
            skipped = [p["slug"] for p in posts if p["slug"] in ARTICLE_REDIRECTS]
            posts = [p for p in posts if p["slug"] not in ARTICLE_REDIRECTS]
            if skipped:
                print(f"Excluding {len(skipped)} redirected (non-rendered) record(s): "
                      f"{', '.join(skipped)}\n")
        except Exception as e:  # noqa: BLE001 — report is still useful without it
            print(f"warning: could not load ARTICLE_REDIRECTS ({e}); "
                  f"redirected records are included\n", file=sys.stderr)
    shingles = {p["slug"]: body_shingles(p) for p in posts}

    if args.shared:
        a, b = args.shared
        missing = [s for s in (a, b) if s not in shingles]
        if missing:
            print(f"unknown slug(s): {', '.join(missing)}", file=sys.stderr)
            return 2
        common = shingles[a] & shingles[b]
        print(f"{len(common)} shared 7-word sequences between {a} and {b}:\n")
        for seq in sorted(" ".join(s) for s in common):
            print("  " + seq)
        return 0

    pairs = []
    slugs = [p["slug"] for p in posts]
    for i, a in enumerate(slugs):
        for b in slugs[i + 1:]:
            sa, sb = shingles[a], shingles[b]
            union = len(sa | sb)
            if not union:
                continue
            jac = len(sa & sb) / union
            if jac >= args.min:
                pairs.append({"similarity": round(jac, 4), "shared": len(sa & sb), "a": a, "b": b})
    pairs.sort(key=lambda p: p["similarity"], reverse=True)

    if not pairs:
        print(f"No pairs at or above {args.min:.2f}. Corpus: {len(posts)} records.")
    else:
        width = max(len(p["a"]) for p in pairs)
        print(f"{len(pairs)} pair(s) at or above {args.min:.2f} "
              f"(block tier >= {SIMILARITY_BLOCK_AT:.2f}, flag tier >= {SIMILARITY_FLAG_AT:.2f}):\n")
        for p in pairs:
            tier = "BLOCK" if p["similarity"] >= SIMILARITY_BLOCK_AT else "flag "
            print(f"  {tier} {p['similarity']:.3f}  {p['shared']:>4} shared  "
                  f"{p['a']:<{width}}  {p['b']}")
        over_block = sum(1 for p in pairs if p["similarity"] >= SIMILARITY_BLOCK_AT)
        print(f"\n{over_block} at or above the block threshold; {len(pairs)} total to review.")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            {"corpus": len(posts), "min": args.min, "pairs": pairs}, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
