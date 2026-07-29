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

    # The BUILD must fail closed on a malformed reporting canon too. It used to
    # return [] and let report_block() ship a hard-coded sidebar that omitted
    # Police Scotland, Advice Direct Scotland and Consumerline (operator review,
    # 2026-07-28).
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "content").mkdir()
        check("an absent sources.json is tolerated by the build loader",
              B.load_sources(root) == [])
        (root / "content" / "sources.json").write_text("{not json", encoding="utf-8")
        try:
            B.load_sources(root)
            ok = False
        except SystemExit:
            ok = True
        check("a PRESENT but malformed sources.json stops the build", ok)
    fallback = B.report_block([])
    for needed in ("Police Scotland", "Advice Direct Scotland", "Consumerline",
                   "England and Wales", "formerly Action Fraud"):
        check(f"the absent-canon sidebar names {needed}", needed in fallback)

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

    check("validator rejects: empty FAQ answer",
          rejects(bad(lambda h: h["faq"].append(["Q?", "   "]))))
    # After the legacy exemption is removed this must fail; while it stands, an
    # unreviewed hub with no sources only warns. Pinned either way so the change
    # of behaviour is deliberate and visible.
    unreviewed = {"payment": {k: v for k, v in hub().items()
                              if k not in ("updated", "sources_checked")}}
    legacy_exempt = not rejects(unreviewed)
    check("a hub with neither 'updated' nor sources is currently EXEMPT (legacy branch present)",
          legacy_exempt,
          "the legacy branch appears to be gone — flip this expectation to rejects()")
    check("a wrapper object is rejected", rejects({"hubs": {"payment": hub()}}))
    check("a non-object root is rejected", rejects([]))
    check("a valid explicit ads_mode is accepted", not rejects(bad(lambda h: h.__setitem__("ads_mode", "npa"))))

    # The generator's own fallback article must satisfy the gate it feeds. Watching
    # the generator file in CI does not test the article it produces (operator
    # review, 2026-07-29): it previously emitted three scotland_routing BLOCKs.
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import generate_content_claude as _G
        from content_gate import run_gate as _rg
        _fields = getattr(_G.Topic, "_fields", None) or list(
            __import__("inspect").signature(_G.Topic).parameters)
        _topic = _G.Topic(**{f: ("test-org-scam-uk" if "slug" in f else "Test Org") for f in _fields})
        _iss = _rg(_G.fallback_post(_topic, "2026-01-01"), use_llm=False).issues
        _b = [i["check"] for i in _iss if i["severity"] == "block"]
        check("the generator's fallback article has zero deterministic BLOCKs", not _b, str(_b))
    except Exception as exc:            # never let an import quirk mask a real failure
        check("the generator fallback could be constructed and gated", False, f"{type(exc).__name__}: {exc}")

    # ── ad treatment ─────────────────────────────────────────────────────────
    EXPECTED = {
        "email": "none", "tech": "none",
        "crypto": "npa", "finance": "npa", "fraud": "npa", "government": "npa",
        "payment": "npa", "phone": "npa", "shopping": "npa", "website": "npa",
        "marketplace": "default", "sms": "default", "travel": "default",
    }
    # SELF-CONTAINED. This previously read docs/review/hubs-v6.json — an ignored,
    # by then absent file — and then `continue`d past any category missing from
    # the live three-record file, silently skipping TEN of the thirteen promised
    # cases while still reporting success (operator review, 2026-07-27).
    #
    # Fixtures below are the minimum prose that drives each mode, committed here
    # so the test behaves identically on a clean CI checkout.
    SEXTORTION = "Threats to share intimate images or sextortion demands, and deepfake material."
    DEBT = "Debt, insolvency, an IVA, bailiffs and recovering money you have lost."
    BENIGN = "How to check a parcel delivery text before tapping a link."
    FIXTURE_PROSE = {
        "email": SEXTORTION, "tech": SEXTORTION,
        "crypto": DEBT, "finance": DEBT, "fraud": DEBT, "government": DEBT,
        "payment": DEBT, "phone": DEBT, "shopping": DEBT, "website": DEBT,
        "marketplace": BENIGN, "sms": BENIGN, "travel": BENIGN,
    }
    missing = sorted(set(EXPECTED) - set(FIXTURE_PROSE))
    check("every expected category has a committed fixture", not missing, str(missing))
    for slug, want in EXPECTED.items():
        fixture = hub(sections=[["S", f"<p>{FIXTURE_PROSE[slug]}</p>"]])
        got = B.hub_ads_mode(slug, fixture)
        check(f"ad mode for {slug} is {want}", got == want, f"got {got}")

    # And every record that is actually LIVE must produce the same mode. This must
    # not depend on docs/review/, which is gitignored: reading a proposal from
    # there passed 66/66 in a working copy and 56/10 in a clean checkout, and the
    # 66 was cited as CI evidence (operator review, 2026-07-28).
    #
    # While the ten new hubs are unlanded, the live file holds three records. Once
    # the atomic release writes all thirteen, the completeness check below starts
    # enforcing the full map — no edit needed, and no way to quietly regress.
    for slug in sorted(set(EXPECTED) & set(live)):
        got = B.hub_ads_mode(slug, live[slug])
        check(f"live ad mode for {slug} is {EXPECTED[slug]}", got == EXPECTED[slug], f"got {got}")
    # Allow ONLY the exact legacy three-record set or the exact full thirteen.
    # A plain "pending" NOTE was fail-open: deleting one of thirteen records
    # printed a note and passed again (operator review, 2026-07-29).
    LEGACY_ONLY = {"sms", "payment", "government"}
    live_expected = set(EXPECTED) & set(live)
    check("hub set is exactly the legacy three or the full thirteen",
          live_expected in (LEGACY_ONLY, set(EXPECTED)),
          f"got {sorted(live_expected)} — an intermediate subset is not a valid release state")
    check("no unexpected hub key is present",
          not (set(live) - set(EXPECTED)), f"unexpected: {sorted(set(live) - set(EXPECTED))}")
    if live_expected == LEGACY_ONLY:
        print("NOTE  the ten new hubs are not landed yet; their modes are covered by the committed")
        print("      fixtures above. After the atomic release this branch should be deleted and the")
        print("      thirteen-key assertion made unconditional.")

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
