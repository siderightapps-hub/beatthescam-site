#!/usr/bin/env python3
"""Read-only WP3C8A census reproduction. NOT a trust/permission catalogue.

The legacy lexer/normaliser is used only to reproduce the frozen migration
worklist. Nothing imports this module from the gate, resolver or renderer.
Queue constants are unresolved review items, never allowed destinations.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

import canon
import content_gate as gate
import corpus
import reporting_contracts as legacy

EVIDENCE_QUEUE = (
    "phishing@companieshouse.gov.uk", "reportafraud@landregistry.gov.uk",
    "https://teamviewer.com/en/report-a-scam", "202", "4445", "1472",
    "https://cifas.org.uk/pr", "https://cifas.org.uk", "https://victimsupport.scot",
    "https://victimsupportni.com", "https://energyadvice.scot", "https://stopncii.org",
    "https://takeitdown.ncmec.org",
    "https://childline.org.uk/info-advice/bullying-abuse-safety/online-mobile-safety/report-remove",
    "https://voice.google.com", "https://gov.uk/report-problem-medicine-medical-device",
    "https://register.fca.org.uk",
)


def inventory_fields(post):
    # Same field granularity as WP3C8A, not combined FAQ/sentence contexts.
    for field in ("title", "description", "hero", "quick_answer", "intro"):
        if post.get(field): yield field, post[field]
    for field in ("sections", "faq"):
        for i, pair in enumerate(post.get(field, [])):
            for j, value in enumerate(pair): yield f"{field}/{i}/{j}", value
    for i, value in enumerate(post.get("keywords", [])): yield f"keywords/{i}", value
    for field in ("evidence", "message_examples"):
        for i, item in enumerate(post.get(field, [])):
            for key, value in item.items():
                if isinstance(value, str): yield f"{field}/{i}/{key}", value
    yield from gate._figure_fields(post)


def census(root):
    posts = json.loads((root / "content/posts.json").read_text())
    hubs = json.loads((root / "content/category-hubs.json").read_text())
    sources = canon.load_canon(root / "content/sources.json")
    contracts = legacy.contracts_from_canon(sources)
    lookup = defaultdict(set)
    for contract in contracts:
        for dest in contract.destinations: lookup[(dest.kind, dest.canonical_value)].add(contract.service)
    shorts = {d.canonical_value for c in contracts for d in c.destinations if d.kind == "shortcode"}
    shorts.update({"202", "4445", "1471", "1472"})  # Diagnostic items, not permissions.
    short_re = re.compile(r"(?<!\w)(?:" + "|".join(sorted(shorts)) + r")(?!\w)")
    rows, exclusions, citations, label_rows = [], [], [], []
    public = corpus.public_posts(posts)
    records = [("guide", p["slug"], p) for p in public] + [("hub", slug, p) for slug, p in hubs.items()]
    for kind, slug, post in records:
        for field, value in inventory_fields(post):
            text = gate._route_text(value)
            found = gate._route_destinations(text)
            for match in short_re.finditer(text):
                if not any(a <= match.start() < b for a, b, _, _ in found):
                    found.append((match.start(), match.end(), "phone", match.group()))
            for a, b, token_kind, token in sorted(found):
                if token.startswith("/"): continue
                normal = legacy.normalize(token_kind, token)
                row = {"kind": kind, "slug": slug, "field": field, "start": a, "end": b, "token": token,
                       "normalised": normal.canonical_value if normal else None,
                       "contract_ids": sorted(lookup.get((normal.kind, normal.canonical_value), [])) if normal else []}
                if token in ("2023", "2027", "https://"):
                    row["reason"] = "WP3C8A reviewed year/incomplete scheme exclusion"
                    exclusions.append(row)
                else: rows.append(row)
        for label, url in post.get("sources_checked", []):
            citations.append({"kind": kind, "slug": slug, "label": label, "url": url})
            for _, _, _, token in gate._route_destinations(gate._route_text(label)):
                if token != "2023": label_rows.append({"slug": slug, "token": token})
    matched = [r for r in rows if r['contract_ids']]
    queue_rows = [r for r in rows if r['normalised'] in EVIDENCE_QUEUE]
    main_services = sources['official_routes'] + sources['verified_org_contacts']
    summary = {"source_records": len(posts), "public_guides": len(public), "hubs": len(hubs),
        "surfaces": len(records), "surfaces_with_raw_values": len({(r['kind'], r['slug']) for r in rows}),
        "structured_surfaces": sum('reporting_routes' in p for _, _, p in records),
        "raw_occurrences": len(rows), "occurrences_by_kind": dict(Counter(r['kind'] for r in rows)),
        "canon_value_matches": len(matched), "contract_identities_touched": len({c for r in matched for c in r['contract_ids']}),
        "unmatched_occurrences": len(rows) - len(matched), "excluded_lexical_hits": len(exclusions),
        "citation_urls": len(citations), "unique_citation_urls": len({r['url'] for r in citations}),
        "citation_label_tokens": len(label_rows), "evidence_queue_values": len(EVIDENCE_QUEUE),
        "evidence_queue_values_seen": len({r['normalised'] for r in queue_rows}), "evidence_queue_occurrences": len(queue_rows),
        "services_missing_source_or_date": [r['key'] for r in main_services if not r.get('source_url') or not r.get('checked_on')],
        "hub_occurrences": dict(Counter(r['slug'] for r in rows if r['kind'] == 'hub'))}
    return {"summary": summary, "occurrences": rows, "exclusions": exclusions,
            "citations": citations, "citation_label_tokens": label_rows,
            "unresolved_evidence_queue": list(EVIDENCE_QUEUE)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, help='optional diagnostic JSON; never a source/canon input')
    args = parser.parse_args(); result = census(args.root)
    if args.output: args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(result['summary'], indent=2, ensure_ascii=False))


if __name__ == '__main__': main()
