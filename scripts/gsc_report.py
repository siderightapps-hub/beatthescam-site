#!/usr/bin/env python3
"""
Beat The Scam — Search Console analytics report (READ-ONLY)
===========================================================
At-a-glance SEO picture for the analytics review + backlinks prioritisation.
Unlike search_console_articles.py (which only surfaces content gaps to
generate new articles), this pulls the full performance picture and never
writes anything:

  - Headline totals (clicks, impressions, CTR, avg position)
  - Top queries by impressions
  - Top pages by impressions
  - NEAR-MISS queries (position 5-20 with impressions) — the highest-leverage
    targets for the backlinks/outreach push: a small rank lift here multiplies
    clicks. These are the pages to point earned links + internal links at.
  - Zero-click queries (impressions but CTR 0) — title/meta-description fixes

Auth reuses token.json — run `python3 scripts/auth_google.py` first if the
token has expired (invalid_grant).

Usage:
    python3 scripts/gsc_report.py                 # last 90 days
    python3 scripts/gsc_report.py --days 28
    python3 scripts/gsc_report.py --json out.json # also dump raw rows
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

# Reuse the auth + site constant from the sibling script (no side effects on
# import — its runnable code is guarded by __main__).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from search_console_articles import get_search_console_service, SC_SITE  # noqa: E402


def query(service, days, dimensions):
    end = date.today()
    start = end - timedelta(days=days)
    body = {
        "startDate": str(start),
        "endDate":   str(end),
        "rowLimit":  1000,
    }
    if dimensions:
        body["dimensions"] = dimensions
    try:
        rows = service.searchanalytics().query(siteUrl=SC_SITE, body=body).execute().get("rows", [])
    except Exception as e:
        print(f"❌ Search Console API error ({dimensions or 'totals'}): {e}")
        return []
    # Sort client-side by impressions desc — the API's ordering isn't guaranteed.
    rows.sort(key=lambda r: r.get("impressions", 0), reverse=True)
    return rows


def trim(text, n):
    text = str(text)
    return text if len(text) <= n else text[: n - 1] + "…"


def shorten_url(u):
    return u.replace("https://beatthescam.com", "") or "/"


def main():
    ap = argparse.ArgumentParser(description="Search Console analytics report (read-only)")
    ap.add_argument("--days", type=int, default=90, help="Lookback window in days (default 90)")
    ap.add_argument("--min-impr", type=int, default=3, help="Min impressions to include a row (default 3)")
    ap.add_argument("--top", type=int, default=25, help="How many rows per section (default 25)")
    ap.add_argument("--json", help="Optional path to dump raw query+page rows as JSON")
    args = ap.parse_args()

    print(f"🔌 Connecting to Search Console ({SC_SITE})…")
    service = get_search_console_service()

    print(f"📅 Window: last {args.days} days\n")

    totals = query(service, args.days, [])
    queries = [r for r in query(service, args.days, ["query"]) if r.get("impressions", 0) >= args.min_impr]
    pages   = [r for r in query(service, args.days, ["page"])  if r.get("impressions", 0) >= args.min_impr]

    # ── Headline totals ──────────────────────────────────────────────────────
    print("═" * 72)
    print("HEADLINE TOTALS")
    print("═" * 72)
    if totals:
        t = totals[0]
        clicks, impr = t.get("clicks", 0), t.get("impressions", 0)
        ctr  = (clicks / impr * 100) if impr else 0
        print(f"  Clicks:      {clicks}")
        print(f"  Impressions: {impr}")
        print(f"  CTR:         {ctr:.2f}%")
        print(f"  Avg pos:     {t.get('position', 0):.1f}")
    else:
        print("  (no data returned — site may have near-zero traffic in this window)")
    print()

    # ── Top queries ──────────────────────────────────────────────────────────
    print("═" * 72)
    print(f"TOP {args.top} QUERIES BY IMPRESSIONS")
    print("═" * 72)
    print(f"  {'impr':>5} {'clk':>4} {'ctr':>6} {'pos':>5}  query")
    for r in queries[: args.top]:
        impr, clk = r["impressions"], r["clicks"]
        ctr = (clk / impr * 100) if impr else 0
        print(f"  {impr:5} {clk:4} {ctr:5.1f}% {r['position']:5.1f}  {trim(r['keys'][0], 48)}")
    print()

    # ── Near-miss queries — the outreach targets ─────────────────────────────
    near = [r for r in queries if 5.0 <= r["position"] <= 20.0]
    print("═" * 72)
    print(f"⭐ NEAR-MISS QUERIES (position 5-20) — {len(near)} found — BACKLINK TARGETS")
    print("   A small rank lift here multiplies clicks. Point earned + internal")
    print("   links (anchor = the query) at the page that ranks for each.")
    print("═" * 72)
    print(f"  {'impr':>5} {'clk':>4} {'pos':>5}  query")
    for r in near[: args.top]:
        print(f"  {r['impressions']:5} {r['clicks']:4} {r['position']:5.1f}  {trim(r['keys'][0], 50)}")
    print()

    # ── Zero-click queries — title/meta fixes ────────────────────────────────
    zero = [r for r in queries if r["clicks"] == 0 and r["impressions"] >= max(5, args.min_impr)]
    print("═" * 72)
    print(f"ZERO-CLICK QUERIES (impressions, no clicks) — {len(zero)} found — TITLE/META FIXES")
    print("═" * 72)
    print(f"  {'impr':>5} {'pos':>5}  query")
    for r in zero[: args.top]:
        print(f"  {r['impressions']:5} {r['position']:5.1f}  {trim(r['keys'][0], 52)}")
    print()

    # ── Top pages ────────────────────────────────────────────────────────────
    print("═" * 72)
    print(f"TOP {args.top} PAGES BY IMPRESSIONS")
    print("═" * 72)
    print(f"  {'impr':>5} {'clk':>4} {'pos':>5}  page")
    for r in pages[: args.top]:
        print(f"  {r['impressions']:5} {r['clicks']:4} {r['position']:5.1f}  {trim(shorten_url(r['keys'][0]), 50)}")
    print()

    if args.json:
        Path(args.json).write_text(
            json.dumps({"totals": totals, "queries": queries, "pages": pages}, indent=2),
            encoding="utf-8",
        )
        print(f"💾 Raw rows written to {args.json}")


if __name__ == "__main__":
    main()
