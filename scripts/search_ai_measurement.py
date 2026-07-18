#!/usr/bin/env python3
"""Create a retained Google Search Console + Bing AI visibility snapshot.

Google data is pulled through the existing read-only Search Console OAuth
client. Bing AI Performance currently has no documented AI-report API, so its
dashboard CSV exports are supplied explicitly. Raw exports, a normalized JSON
snapshot, an internal Markdown scorecard and an optional public research JSON
file are written deterministically.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from search_console_articles import SC_SITE, get_search_console_service  # noqa: E402


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def int_value(value: Any) -> int:
    return int(str(value or "0").replace(",", ""))


def bing_date(value: str) -> str:
    return datetime.strptime(value, "%m/%d/%Y %I:%M:%S %p").date().isoformat()


def query_gsc(service: Any, start: date, end: date, dimensions: Iterable[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    start_row = 0
    while True:
        body: Dict[str, Any] = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dataState": "final",
            "rowLimit": 25000,
            "startRow": start_row,
        }
        dimension_list = list(dimensions)
        if dimension_list:
            body["dimensions"] = dimension_list
        batch = service.searchanalytics().query(siteUrl=SC_SITE, body=body).execute().get("rows", [])
        rows.extend(batch)
        if len(batch) < 25000:
            break
        start_row += len(batch)
        if start_row >= 50000:
            break
    rows.sort(key=lambda row: row.get("impressions", 0), reverse=True)
    return rows


def gsc_window(service: Any, start: date, end: date) -> Dict[str, Any]:
    totals = query_gsc(service, start, end, [])
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "totals": totals[0] if totals else {},
        "queries": query_gsc(service, start, end, ["query"]),
        "pages": query_gsc(service, start, end, ["page"]),
        "page_queries": query_gsc(service, start, end, ["page", "query"]),
        "daily": query_gsc(service, start, end, ["date"]),
    }


def normalize_bing(overview: Path, pages: Path, queries: Path) -> Dict[str, Any]:
    overview_rows = read_csv(overview)
    page_rows = read_csv(pages)
    query_rows = read_csv(queries)
    daily = [
        {
            "date": bing_date(row["Date"]),
            "citations": int_value(row["Citations"]),
            "cited_pages": int_value(row["Cited Pages"]),
        }
        for row in overview_rows
    ]
    normalized_pages = [
        {"page": row["Page"], "citations": int_value(row["Citations"])}
        for row in page_rows
    ]
    normalized_queries = [
        {
            "grounding_query": row["Grounding Query"],
            "intent": row.get("Intent", ""),
            "topic": row.get("Topic", ""),
            "citations": int_value(row["Citations"]),
            "citation_share": row.get("Citation Share", ""),
        }
        for row in query_rows
    ]
    return {
        "start_date": daily[0]["date"] if daily else None,
        "end_date": daily[-1]["date"] if daily else None,
        "days_returned": len(daily),
        "total_citations": sum(row["citations"] for row in daily),
        "average_cited_pages": round(
            sum(row["cited_pages"] for row in daily) / len(daily), 1
        ) if daily else 0,
        "cited_page_count": len(normalized_pages),
        "grounding_query_sample_count": len(normalized_queries),
        "daily": daily,
        "pages": normalized_pages,
        "grounding_queries": normalized_queries,
    }


def metric_delta(current: Dict[str, Any], previous: Dict[str, Any], field: str) -> Optional[float]:
    old = float(previous.get(field) or 0)
    if not old:
        return None
    return round((float(current.get(field) or 0) - old) / old * 100, 1)


def page_metrics(window: Dict[str, Any], urls: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    url_list = list(dict.fromkeys(urls))
    metrics = {
        url: {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}
        for url in url_list
    }
    for row in window["pages"]:
        if row.get("keys") and row["keys"][0] in metrics:
            metrics[row["keys"][0]] = {
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "ctr": row.get("ctr", 0),
            "position": row.get("position", 0),
            }
    return metrics


def combined_metrics(metrics: Dict[str, Dict[str, Any]], urls: Iterable[str]) -> Dict[str, Any]:
    rows = [metrics.get(url, {}) for url in urls]
    impressions = sum(float(row.get("impressions") or 0) for row in rows)
    clicks = sum(float(row.get("clicks") or 0) for row in rows)
    weighted_position = sum(
        float(row.get("position") or 0) * float(row.get("impressions") or 0)
        for row in rows
    )
    return {
        "clicks": clicks,
        "impressions": impressions,
        "ctr": clicks / impressions if impressions else 0,
        "position": weighted_position / impressions if impressions else 0,
    }


def fmt_delta(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:+.1f}%"


def scorecard_markdown(snapshot: Dict[str, Any]) -> str:
    current = snapshot["gsc"]["current_28_days"]
    previous = snapshot["gsc"]["previous_28_days"]
    ct = current["totals"]
    pt = previous["totals"]
    bing = snapshot["bing_ai"]["30_days"]
    current_focus = snapshot["measurement"]["focus_page_metrics_current"]
    previous_focus = snapshot["measurement"]["focus_page_metrics_previous"]
    lines = [
        f"# Search and AI visibility scorecard — {snapshot['snapshot_date']}",
        "",
        "## Headline baseline",
        "",
        "| Signal | Current period | Previous period | Change |",
        "|---|---:|---:|---:|",
        f"| Google clicks | {ct.get('clicks', 0):g} | {pt.get('clicks', 0):g} | {fmt_delta(metric_delta(ct, pt, 'clicks'))} |",
        f"| Google impressions | {ct.get('impressions', 0):g} | {pt.get('impressions', 0):g} | {fmt_delta(metric_delta(ct, pt, 'impressions'))} |",
        f"| Google CTR | {ct.get('ctr', 0) * 100:.2f}% | {pt.get('ctr', 0) * 100:.2f}% | {((ct.get('ctr', 0) - pt.get('ctr', 0)) * 100):+.2f} pp |",
        f"| Google average position | {ct.get('position', 0):.1f} | {pt.get('position', 0):.1f} | {ct.get('position', 0) - pt.get('position', 0):+.1f} |",
        f"| Bing AI citations | {bing['total_citations']:,} | — | baseline |",
        f"| Bing AI average cited pages/day | {bing['average_cited_pages']:.1f} | — | baseline |",
        "",
        f"Google current window: {current['start_date']} to {current['end_date']}; previous equal window: {previous['start_date']} to {previous['end_date']}. Bing export window: {bing['start_date']} to {bing['end_date']}.",
        "",
        "## Focus-page baseline",
        "",
        "| Page | Impr. current | Impr. previous | Change | Clicks current | CTR current | CTR previous | Position current | Position previous |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for url in snapshot["measurement"]["focus_urls"]:
        row = current_focus.get(url, {})
        old = previous_focus.get(url, {})
        lines.append(
            f"| {url.replace('https://beatthescam.com', '') or '/'} | "
            f"{row.get('impressions', 0):g} | {old.get('impressions', 0):g} | "
            f"{fmt_delta(metric_delta(row, old, 'impressions'))} | {row.get('clicks', 0):g} | "
            f"{row.get('ctr', 0) * 100:.2f}% | {old.get('ctr', 0) * 100:.2f}% | "
            f"{row.get('position', 0):.1f} | {old.get('position', 0):.1f} |"
        )
    consolidations = snapshot["measurement"]["intervention"].get("consolidations", [])
    if consolidations:
        lines.extend([
            "",
            "## Consolidation clusters",
            "",
            "Source and target are combined so a redirect migration is not mistaken for a loss or gain.",
            "",
            "| Cluster | Impr. current | Impr. previous | Clicks current | Clicks previous | CTR current | CTR previous |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ])
        for consolidation in consolidations:
            urls = [consolidation["from"], consolidation["to"]]
            cluster_current = combined_metrics(current_focus, urls)
            cluster_previous = combined_metrics(previous_focus, urls)
            label = " + ".join(url.replace("https://beatthescam.com", "") for url in urls)
            lines.append(
                f"| {label} | {cluster_current['impressions']:g} | {cluster_previous['impressions']:g} | "
                f"{cluster_current['clicks']:g} | {cluster_previous['clicks']:g} | "
                f"{cluster_current['ctr'] * 100:.2f}% | {cluster_previous['ctr'] * 100:.2f}% |"
            )
    lines.extend([
        "",
        "## Measurement rules",
        "",
        "- Treat the 18 July release as an intervention, not proof of causation.",
        "- Compare equal 28-day windows and use the 7-day view only as an early directional check.",
        "- Track redirects as a combined source-and-target cluster until the legacy URL disappears from reports.",
        "- Bing grounding queries are a sample and AI-generated intent/topic labels may change.",
        "- AI citations measure source appearances, not ranking, answer placement, visits or endorsement.",
        "- Search impressions and AI citations are visibility signals, not estimates of scam prevalence.",
        "",
    ])
    return "\n".join(lines)


def public_payload(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    bing = snapshot["bing_ai"]["30_days"]
    current = snapshot["gsc"]["current_28_days"]
    previous = snapshot["gsc"]["previous_28_days"]
    current_focus = snapshot["measurement"]["focus_page_metrics_current"]
    previous_focus = snapshot["measurement"]["focus_page_metrics_previous"]
    consolidations = []
    for consolidation in snapshot["measurement"]["intervention"].get("consolidations", []):
        urls = [consolidation["from"], consolidation["to"]]
        consolidations.append({
            **consolidation,
            "combined_current": combined_metrics(current_focus, urls),
            "combined_previous": combined_metrics(previous_focus, urls),
        })
    month_label = datetime.strptime(snapshot["snapshot_date"][:7], "%Y-%m").strftime("%B %Y")
    return {
        "schema_version": 1,
        "slug": f"uk-scam-search-ai-trends-{snapshot['snapshot_date'][:7]}",
        "title": f"UK Scam Guidance Visibility Report — {month_label}",
        "published": snapshot["snapshot_date"],
        "summary": "An original monthly snapshot of how UK scam guidance is discovered in Google Search and cited across Microsoft Copilot, Bing AI answers and selected partners.",
        "scope_note": "This dataset measures visibility for beatthescam.com. It does not estimate how many scams occurred, how much money was lost, or population-level search demand.",
        "bing_ai": {
            "source": "Bing Webmaster Tools AI Performance CSV exports",
            "start_date": bing["start_date"],
            "end_date": bing["end_date"],
            "days_returned": bing["days_returned"],
            "total_citations": bing["total_citations"],
            "average_cited_pages": bing["average_cited_pages"],
            "cited_page_count": bing["cited_page_count"],
            "grounding_query_sample_count": bing["grounding_query_sample_count"],
            "daily": bing["daily"],
            "top_pages": bing["pages"][:25],
            "top_grounding_queries": bing["grounding_queries"][:25],
        },
        "google_search": {
            "source": "Google Search Console Search Analytics API, final web-search data",
            "start_date": current["start_date"],
            "end_date": current["end_date"],
            "clicks": current["totals"].get("clicks", 0),
            "impressions": current["totals"].get("impressions", 0),
            "ctr": current["totals"].get("ctr", 0),
            "average_position": current["totals"].get("position", 0),
            "previous_period": {
                "start_date": previous["start_date"],
                "end_date": previous["end_date"],
                "clicks": previous["totals"].get("clicks", 0),
                "impressions": previous["totals"].get("impressions", 0),
                "ctr": previous["totals"].get("ctr", 0),
                "average_position": previous["totals"].get("position", 0),
            },
            "focus_pages": current_focus,
            "focus_pages_previous": previous_focus,
            "consolidations": consolidations,
        },
        "method": [
            "Bing figures are retained from the dashboard's 30-day overview, cited-pages and grounding-query CSV exports.",
            "Google figures use final Search Console web-search data for the latest complete 28-day window, ending two days before the snapshot date.",
            "The published tables retain the top 25 Bing cited pages and sampled grounding queries; raw exports are archived internally.",
            "No user-submitted messages, personal data or checker input are collected or included.",
            "Counts can be revised by the source platforms; each monthly release is an immutable dated snapshot.",
        ],
        "limitations": [
            "Bing says grounding queries represent a sample of overall citation activity.",
            "Bing citation counts do not show placement, importance, answer ranking, traffic or endorsement.",
            "Search Console omits anonymized queries and can show different totals under different aggregation dimensions.",
            "Changes after an editorial release can correlate with, but do not by themselves prove, an effect from that release.",
            "This is a visibility dataset for one publication, not a national fraud-incidence dataset.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Retain a Search Console and Bing AI measurement snapshot")
    parser.add_argument("--snapshot-date", default=date.today().isoformat())
    parser.add_argument("--bing-overview-30", type=Path, required=True)
    parser.add_argument("--bing-pages-30", type=Path, required=True)
    parser.add_argument("--bing-queries-30", type=Path, required=True)
    parser.add_argument("--bing-overview-90", type=Path, required=True)
    parser.add_argument("--bing-pages-90", type=Path, required=True)
    parser.add_argument("--bing-queries-90", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / "analytics" / "search-ai")
    parser.add_argument("--public-output", type=Path)
    args = parser.parse_args()

    snapshot_date = parse_date(args.snapshot_date)
    output_dir = args.output_root / args.snapshot_date
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    supplied = {
        "bing-ai-overview-30d.csv": args.bing_overview_30,
        "bing-ai-pages-30d.csv": args.bing_pages_30,
        "bing-ai-queries-30d.csv": args.bing_queries_30,
        "bing-ai-overview-3m.csv": args.bing_overview_90,
        "bing-ai-pages-3m.csv": args.bing_pages_90,
        "bing-ai-queries-3m.csv": args.bing_queries_90,
    }
    for name, source in supplied.items():
        write_csv(raw_dir / name, read_csv(source))

    latest_final = snapshot_date - timedelta(days=2)
    current_start = latest_final - timedelta(days=27)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=27)
    service = get_search_console_service()
    current = gsc_window(service, current_start, latest_final)
    previous = gsc_window(service, previous_start, previous_end)

    interventions = json.loads((args.output_root / "interventions.json").read_text(encoding="utf-8"))
    intervention = interventions["interventions"][-1]
    focus_urls = list(intervention["focus_urls"])
    for consolidation in intervention.get("consolidations", []):
        focus_urls.extend([consolidation["from"], consolidation["to"]])

    snapshot = {
        "schema_version": 1,
        "snapshot_date": args.snapshot_date,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "bing_ai": {
            "30_days": normalize_bing(args.bing_overview_30, args.bing_pages_30, args.bing_queries_30),
            "3_months": normalize_bing(args.bing_overview_90, args.bing_pages_90, args.bing_queries_90),
        },
        "gsc": {"current_28_days": current, "previous_28_days": previous},
        "measurement": {
            "intervention": intervention,
            "focus_urls": focus_urls,
            "focus_page_metrics_current": page_metrics(current, focus_urls),
            "focus_page_metrics_previous": page_metrics(previous, focus_urls),
        },
    }
    (output_dir / "snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    (output_dir / "scorecard.md").write_text(scorecard_markdown(snapshot), encoding="utf-8")
    if args.public_output:
        args.public_output.parent.mkdir(parents=True, exist_ok=True)
        args.public_output.write_text(json.dumps(public_payload(snapshot), indent=2) + "\n", encoding="utf-8")

    print(f"Wrote snapshot: {output_dir / 'snapshot.json'}")
    print(f"Wrote scorecard: {output_dir / 'scorecard.md'}")
    if args.public_output:
        print(f"Wrote public research source: {args.public_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
