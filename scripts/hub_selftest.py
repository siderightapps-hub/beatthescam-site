#!/usr/bin/env python3
"""
hub_selftest.py — regression tests for category-hub loading, validation and ads.

Category hubs are edited directly and the build is their publication boundary,
so `build()` deletes dist/ before rendering. A malformed hub that the validator
waves through therefore crashes AFTER the committed output tree is gone, and a
hub whose ad mode is computed wrongly ships personalised-capable ads over
sextortion, debt and identity-theft material.

These tests pin that behaviour so it does not depend on a one-session check
(operator review, 2026-07-27).

Offline: no API key, no network.

    python3 scripts/hub_selftest.py
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build as B

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def hub(**over) -> dict:
    base = {
        "title": "A hub title", "description": "D" * 140, "intro": "<p>Intro.</p>",
        "sections": [["A heading", "<p>Ordinary body text about a scam.</p>"]],
        "faq": [["A question?", "An answer."]],
        "sources_checked": [["A source", "https://www.gov.uk/consumer-advice"]],
        "updated": "2026-07-27",
    }
    base.update(over)
    return base


def rejects(hubs) -> bool:
    try:
        B.validate_category_hubs(hubs)
        return False
    except SystemExit:
        return True


def run() -> int:
    live = json.loads((ROOT / "content" / "category-hubs.json").read_text(encoding="utf-8"))

    # ── loading fails CLOSED ─────────────────────────────────────────────────
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "content").mkdir()
        check("a missing hub file is fine (hubs are optional)",
              B.load_category_hubs(root) == {})
        (root / "content" / "category-hubs.json").write_text("{not json", encoding="utf-8")
        try:
            B.load_category_hubs(root)
            ok = False
        except SystemExit:
            ok = True
        check("a PRESENT but malformed hub file stops the build", ok)

    # ── schema validation ────────────────────────────────────────────────────
    good = {"payment": hub()}
    check("a well-formed hub validates", not rejects(good))

    def bad(mut):
        h = copy.deepcopy(good)
        mut(h["payment"])
        return h

    for name, mut in (
        ("unknown category slug", None),
        ("record is not an object", lambda h: None),
        ("empty title", lambda h: h.__setitem__("title", "  ")),
        ("empty description", lambda h: h.__setitem__("description", "")),
        ("empty intro", lambda h: h.__setitem__("intro", "  ")),
        ("empty sections list", lambda h: h.__setitem__("sections", [])),
        ("section not a pair", lambda h: h["sections"].append(["only-one"])),
        ("section heading not a string", lambda h: h["sections"].append([1, "body"])),
        ("empty section heading", lambda h: h["sections"].append(["", "body"])),
        ("empty section body", lambda h: h["sections"].append(["H", "   "])),
        ("FAQ not a pair", lambda h: h["faq"].append(["q-only"])),
        ("FAQ answer not a string", lambda h: h["faq"].append(["Q?", None])),
        ("empty FAQ question", lambda h: h["faq"].append(["", "A."])),
        ("source not a pair", lambda h: h["sources_checked"].append(["label-only"])),
        ("source label not a string", lambda h: h["sources_checked"].append([1, "https://a.example"])),
        ("empty source label", lambda h: h["sources_checked"].append(["", "https://a.example"])),
        ("source URL not http(s)", lambda h: h["sources_checked"].append(["L", "ftp://a.example"])),
        ("source URL with no host", lambda h: h["sources_checked"].append(["L", "https://"])),
        ("reviewed hub with an empty source list", lambda h: h.__setitem__("sources_checked", [])),
        ("reviewed hub with no source key", lambda h: h.pop("sources_checked")),
        ("unknown record key", lambda h: h.__setitem__("source_checked", [])),
        ("updated not an ISO date", lambda h: h.__setitem__("updated", "27/07/2026")),
        ("updated not a real date", lambda h: h.__setitem__("updated", "2026-02-31")),
        ("invalid ads_mode", lambda h: h.__setitem__("ads_mode", "personalised")),
    ):
        if name == "unknown category slug":
            payload = {"notacategory": hub()}
        elif name == "record is not an object":
            payload = {"payment": "oops"}
        else:
            payload = bad(mut)
        check(f"validator rejects: {name}", rejects(payload))

    check("a wrapper object is rejected", rejects({"hubs": {"payment": hub()}}))
    check("a non-object root is rejected", rejects([]))
    check("a valid explicit ads_mode is accepted", not rejects(bad(lambda h: h.__setitem__("ads_mode", "npa"))))

    # ── ad treatment ─────────────────────────────────────────────────────────
    EXPECTED = {
        "email": "none", "tech": "none",
        "crypto": "npa", "finance": "npa", "fraud": "npa", "government": "npa",
        "payment": "npa", "phone": "npa", "shopping": "npa", "website": "npa",
        "marketplace": "default", "sms": "default", "travel": "default",
    }
    proposed = ROOT / "docs" / "review" / "hubs-v6.json"
    merged = dict(live)
    if proposed.exists():
        merged.update(json.loads(proposed.read_text(encoding="utf-8")))
    for slug, want in EXPECTED.items():
        if slug not in merged:
            continue
        got = B.hub_ads_mode(slug, merged[slug])
        check(f"ad mode for {slug} is {want}", got == want, f"got {got}")

    sensitive = hub(sections=[["S", "<p>Sextortion and intimate image threats, and debt problems.</p>"]])
    check("a sensitive hub with no explicit mode is not 'default'",
          B.hub_ads_mode("payment", sensitive) != "default")
    derived = B.hub_ads_mode("payment", sensitive)
    check("an EQUALLY restrictive override is honoured",
          B.hub_ads_mode("payment", {**sensitive, "ads_mode": derived}) == derived)
    check("a MORE restrictive override is honoured",
          B.hub_ads_mode("payment", {**sensitive, "ads_mode": "none"}) == "none")
    check("a LESS restrictive override cannot downgrade a derived 'none'",
          B.hub_ads_mode("payment", {**sensitive, "ads_mode": "default"}) == derived)
    benign = hub(sections=[["S", "<p>How to check a parcel delivery text before tapping a link.</p>"]])
    check("a benign hub derives 'default'", B.hub_ads_mode("sms", benign) == "default")
    check("a restrictive override on a benign hub is honoured",
          B.hub_ads_mode("sms", {**benign, "ads_mode": "none"}) == "none")
    try:
        B.hub_ads_mode("sms", {**benign, "ads_mode": "personalised"})
        ok = False
    except SystemExit:
        ok = True
    check("an invalid explicit ads_mode stops the build", ok)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All hub self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
