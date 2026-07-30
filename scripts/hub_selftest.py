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
from html import unescape as html_unescape
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

    # The BUILD must fail closed on ANY unusable reporting canon. It used to
    # return [] and let report_block() ship a hard-coded sidebar that omitted
    # Police Scotland, Advice Direct Scotland and Consumerline (operator review,
    # 2026-07-28). An ABSENT canon used to be tolerated for the same reason, and
    # that too now stops the build: a missing deployment input must not be
    # papered over with a second, unreviewed copy of the routes (2026-07-29).
    # Structural fixtures live in scripts/canon.py and run in the gate self-test.
    for label, contents in (("an absent", None), ("a malformed", "{not json"),
                            ("an empty-object", "{}")):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "content").mkdir()
            if contents is not None:
                (root / "content" / "sources.json").write_text(contents, encoding="utf-8")
            try:
                B.load_sources(root)
                ok = False
            except SystemExit:
                ok = True
            check(f"{label} sources.json stops the build", ok)

    # The sidebar renders every nation from the LIVE canon, with no fallback set.
    sidebar = B.report_block(B.load_sources(ROOT))
    for needed in ("Police Scotland", "Advice Direct Scotland", "Consumerline",
                   "England and Wales", "formerly Action Fraud"):
        check(f"the canon-rendered sidebar names {needed}", needed in sidebar)

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
    # The legacy `unsourced_legacy` exemption exists ONLY because the three
    # original hubs shipped without sources. The moment all thirteen sourced
    # records land, it must go, and an unsourced hub must be rejected outright.
    #
    # The expectation is DERIVED from the live hub count rather than hard-coded,
    # so landing the thirteen automatically demands the code change instead of
    # relying on someone remembering to flip a boolean. A note that says "flip
    # this later" is not enforcement (operator review, 2026-07-29).
    unreviewed = {"payment": {k: v for k, v in hub().items()
                              if k not in ("updated", "sources_checked")}}
    legacy_exempt = not rejects(unreviewed)
    exemption_still_allowed = len(live) == 3
    if exemption_still_allowed:
        check("a hub with neither 'updated' nor sources is EXEMPT while the legacy three stand",
              legacy_exempt,
              "the legacy branch appears to be gone — good, but the live file still has three "
              "hubs; land all thirteen in the same patch")
    else:
        check("with all thirteen hubs landed, an unsourced hub is REJECTED",
              not legacy_exempt,
              "the `unsourced_legacy` exemption branch is still in validate_category_hubs(). "
              "Delete it — the atomic release requires a non-empty sources_checked for every hub.")
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

    # ── STANDALONE SURFACES CARRY THE FULL NATION SCOPE ──────────────────────
    # The checker page said "report it to Report Fraud ... (Police Scotland:
    # 101)" — a bare parenthetical, not a self-contained instruction — and the
    # Terms verification sentence and the Disclaimer action sentence named
    # Report Fraud with no geography at all (operator review, 2026-07-29,
    # `hubs-v10-c.md` §4). All of them now render from police_route_html().
    _site_json = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    _canon = B.load_sources(ROOT)
    _component = B.police_route_html(_canon)
    _surfaces = {"check": B.render_check_page(_site_json, _canon)}
    for _name, _body in zip(
        ("about", "privacy", "cookies", "terms", "contact", "disclaimer",
         "methodology", "corrections", "recovery"),
        B.build_legal_bodies(_site_json, _canon),
    ):
        _surfaces[_name] = _body

    # The property that matters is the one the gate already enforces on guides:
    # no named Report Fraud mention without the Scottish route in the same
    # window. Running the gate's own checks over the RENDERED surfaces tests
    # that directly, instead of a brittle "every mention is literally the
    # component" rule that a correctly-scoped source list would fail.
    sys.path.insert(0, str(ROOT / "scripts"))
    from content_gate import check_deterministic as _cd

    def _text(body: str) -> str:
        body = _re_pre.sub(" ", body)                     # drop <script>/<style>
        return html_unescape(_re_tag.sub(" ", body))

    import re as _re
    _re_pre = _re.compile(r"<(script|style)\b.*?</\1>", _re.S | _re.I)
    _re_tag = _re.compile(r"<[^>]+>")

    _ROUTING_CHECKS = {"scotland_routing", "nation_consumer_routing"}
    for _name in sorted(_surfaces):
        _plain = _text(_surfaces[_name])
        if "Report Fraud" not in _plain and "Citizens Advice" not in _plain:
            continue
        _issues = [i for i in _cd({"slug": f"page-{_name}", "title": _name,
                                   "description": "", "hero": "",
                                   "sections": [["Page", _plain]], "faq": []})
                   if i["check"] in _ROUTING_CHECKS and i["severity"] == "block"]
        check(f"{_name}: rendered page passes the gate's nation-routing checks",
              not _issues, "; ".join(i["detail"][:120] for i in _issues))

    # And the surfaces the review named specifically must use the component.
    for _name in ("check", "terms", "disclaimer", "methodology"):
        check(f"{_name}: renders the shared canon route component",
              _component in _surfaces[_name]
              or B.police_route_html(_canon, phone=False, url=False) in _surfaces[_name])
    check("no surface relegates Scotland to a bare parenthetical",
          not any("(Police Scotland: " in b for b in _surfaces.values()))
    # No route URL, number or geography may be typed into build.py again. Every
    # one is now read from the canon — including the list-shaped surfaces
    # (methodology and recovery source rows, humans.txt) that a prose component
    # does not fit (operator review, 2026-07-30, hubs-v11-c.md §6).
    _build_src = Path(B.__file__).read_text(encoding="utf-8")
    # Every value the canon owns. The earlier six covered only the police hosts
    # and nation numbers, which is why "zero hand-typed route URLs" was an
    # overstatement (operator review, 2026-07-30). These are the full set.
    for _needle in ("reportfraud.police.uk", "scotland.police.uk", "0300 123 2040",
                    "0808 223 1133", "0808 800 9060", "0300 123 6262",
                    "report@phishing.gov.uk", "gov.uk/consumer-advice", ">7726<"):
        check(f"build.py hand-types no {_needle!r}", _needle not in _build_src)
    # `https://www.ncsc.gov.uk/` is the canon's info_url and must be derived; the
    # DEEP link `.../section/respond-recover/phishing` is a guidance page cited
    # as a source row, not a reporting route, so it is legitimately written out.
    check("build.py hand-types no bare NCSC route URL",
          '"https://www.ncsc.gov.uk/"' not in _build_src)
    check("no unsubstituted route placeholder ships",
          not any("<!--POLICE_ROUTE" in b for b in _surfaces.values()))

    # ── <title> must equal the reviewed H1 and schema name ───────────────────
    # render_category_page() called seo_title() with the ' | Beat the Scam'
    # suffix enabled, so all ten proposed hub titles were truncated away from
    # the approved H1 and schema `name` — three into visibly broken endings
    # ("Travel Scams UK: Fake Holidays, Flights &"). Every full hub title fits
    # the 60-char budget, so the suffix bought nothing (operator review,
    # 2026-07-29, `hubs-v10-c.md` §5).
    import re as _re

    _site = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    _post = {"slug": "a-guide", "title": "A guide", "description": "D", "hero": "H",
             "date": "2026-01-01", "category": "payment", "keywords": [], "sections": [],
             "faq": []}

    def _rendered_titles(hub_record, category="payment"):
        page = B.render_category_page(_site, category, [_post], hub=hub_record)
        title = _re.search(r"<title>(.*?)</title>", page, _re.S).group(1)
        h1 = _re.search(r"<h1>(.*?)</h1>", page, _re.S).group(1)
        name = _re.search(r'"name":\s*"([^"]*)"', page).group(1)
        return html_unescape(title), html_unescape(h1), html_unescape(name)

    LONG_HUB_TITLE = "Travel Scams UK: Fake Holidays, Flights & Bookings"
    t, h1, name = _rendered_titles(hub(title=LONG_HUB_TITLE), "travel")
    check("a hub <title> is the full reviewed title", t == LONG_HUB_TITLE, f"got {t!r}")
    check("a hub <title> equals its H1", t == h1, f"{t!r} vs {h1!r}")
    check("a hub <title> equals its schema name", t == name, f"{t!r} vs {name!r}")
    check("a hub <title> is not truncated mid-phrase", not t.rstrip().endswith(("&", ":", ",")))
    # A plain category page (no hub) keeps the brand suffix — its label is short.
    t_plain, _, _ = _rendered_titles(None, "payment")
    check("a plain category page still carries the brand suffix",
          t_plain.endswith(f' | {_site["site_name"]}'), f"got {t_plain!r}")

    # Every LIVE hub title must survive rendering intact.
    for slug, record in sorted(live.items()):
        want = record.get("title") or ""
        t, h1, name = _rendered_titles(record, slug)
        check(f"live hub {slug}: <title>, H1 and schema name all carry the reviewed title",
              t == want == h1 == name, f"title={t!r} h1={h1!r} schema={name!r} want={want!r}")
        check(f"live hub {slug}: title is within the 60-char budget", len(t) <= 60, f"{len(t)} chars")

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
