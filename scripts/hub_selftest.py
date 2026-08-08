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
import re
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
    # original hubs shipped without sources. The moment the full sourced
    # records land, it must go, and an unsourced hub must be rejected outright.
    #
    # The expectation is DERIVED from the live hub count rather than hard-coded,
    # so landing them automatically demands the code change instead of
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
              "hubs; land the full set in the same patch")
    else:
        check("with the full hub set landed, an unsourced hub is REJECTED",
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
        "payment": "npa", "phone": "npa", "shopping": "npa",
        # "website" derives "none", not "npa": its prose carries a substantive
        # section on checking pharmacy registration (GPhC, PSNI, MHRA) with eight
        # pharmacy mentions. Medicines are a restricted advertising category, and
        # non-personalised ads change targeting rather than eligibility, so the
        # whole-hub assessment correctly escalates it (audit, 2026-07-31). This
        # is MORE restrictive than before, which the override rules permit.
        "website": "none",
        "marketplace": "default", "sms": "default", "travel": "default",
        # The four hubs that completed the set on 2026-08-01. `dating` derives
        # "npa" because romance-fraud terms are in the sensitive-finance list;
        # the other three carry no such term and stay on default Auto Ads.
        "dating": "npa", "employment": "default", "social": "default",
        "utility": "default",
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
    # The website hub carries a substantive pharmacy-registration section, so its
    # fixture must carry medicine prose too — feeding it DEBT made the fixture
    # derive "npa" while the live record derived "none", and the two layers are
    # meant to agree (audit, 2026-07-31).
    MEDICINE = "Fake online pharmacy sites selling prescription medicines with no consultation."
    ROMANCE = "Romance scam approaches on dating apps, and the money requests that follow."
    FIXTURE_PROSE = {
        "email": SEXTORTION, "tech": SEXTORTION,
        "crypto": DEBT, "finance": DEBT, "fraud": DEBT, "government": DEBT,
        "payment": DEBT, "phone": DEBT, "shopping": DEBT, "website": MEDICINE,
        "marketplace": BENIGN, "sms": BENIGN, "travel": BENIGN,
        "dating": ROMANCE, "employment": BENIGN, "social": BENIGN,
        "utility": BENIGN,
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
    live_expected = set(EXPECTED) & set(live)
    check("hub set is exactly the expected seventeen",
          live_expected == set(EXPECTED),
          f"got {sorted(live_expected)} — the legacy-three allowance was removed when all "
          f"seventeen landed")
    check("no unexpected hub key is present",
          not (set(live) - set(EXPECTED)), f"unexpected: {sorted(set(live) - set(EXPECTED))}")

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

    # ── Original guide figures ────────────────────────────────────────────
    # A figure is DATA rendered by code, never markup from a record. Guide prose
    # is html-escaped by _inline() so an article cannot inject attributes or
    # scripts; letting a record carry raw SVG would hand that straight back.
    # These pin that boundary, and pin the accessibility floor: a figure with no
    # alt text is worse than no figure, because assistive tech announces an image
    # and then has nothing to say about it (audit, 2026-07-31).
    good = {"title": "T", "alt": "A description of the figure.",
            "steps": [{"check": "First check", "then": "Why it matters"}]}
    out = B.render_guide_figure(good)
    check("a valid figure renders", bool(out))
    check("a figure is exposed to assistive tech as an image",
          'role="img"' in out and "<title" in out and "<desc" in out)
    for name, bad in (("no alt", {**good, "alt": ""}),
                      ("no title", {**good, "title": ""}),
                      ("no steps", {**good, "steps": []}),
                      ("a non-dict figure", "just a string")):
        check(f"a figure with {name} renders NOTHING rather than a broken one",
              B.render_guide_figure(bad) == "")
    hostile = {"title": "<script>alert(1)</script>", "alt": "<img onerror=x>",
               "caption": "</svg><script>x</script>",
               "steps": [{"check": "<iframe src=evil>", "then": "\"><script>y</script>"}]}
    hout = B.render_guide_figure(hostile)
    # Assert the PROPERTY, not a substring. "onerror=" legitimately survives as
    # inert text inside <desc> once the angle brackets are escaped; what must
    # never appear is a real element or a real attribute. Testing for the
    # substring failed on escaped text and would have been "fixed" by weakening
    # the renderer.
    for probe in ("<script", "<iframe", "<img"):
        check(f"figure content cannot inject a real {probe} element", probe not in hout)
    check("figure content cannot inject an event-handler attribute",
          not re.search(r"<[a-z]+[^>]*\son[a-z]+=", hout))
    check("hostile figure content is escaped rather than dropped",
          "&lt;img onerror=x&gt;" in hout)

    live_posts = json.loads((ROOT / "content" / "posts.json").read_text(encoding="utf-8"))

    # ── internal auto-links never claim an official body's name ──────────────
    # A keyword becomes a site-wide anchor trigger, so a keyword naming an
    # EXTERNAL register or service made that phrase link to a guide of ours
    # instead. Both offenders shipped: "FCA Warning List" → forex-trading-scam-uk
    # on share-fraud-uk, and "Cifas Protective Registration" → identity-theft-uk
    # on thirty pages, against the canon rule routing identity misuse to
    # cifas.org.uk (operator review, 2026-08-06).
    live_map = B.build_internal_link_map(live_posts)
    leaked = sorted(p for p in live_map if p in B._OFFICIAL_SERVICE_PHRASES)
    check("no official body/service name is an internal-link anchor",
          not leaked, ", ".join(f"{p} -> {live_map[p]}" for p in leaked))
    for phrase in ("fca warning list", "cifas protective registration"):
        check(f"the regressed phrase {phrase!r} is not auto-linked",
              phrase not in live_map)

    # The filter must key on the WHOLE phrase. Barring every keyword that merely
    # contains a body name would silently drop ~80 legitimate topic links.
    synth = [
        {"slug": "a-guide", "keywords": ["fca warning list", "cifas protective registration",
                                         "companies house scam letter"]},
        {"slug": "b-guide", "keywords": ["a distinctive topic phrase"]},
    ]
    smap = B.build_internal_link_map(synth)
    check("an official-service keyword yields no anchor",
          "fca warning list" not in smap and "cifas protective registration" not in smap)
    check("a topic phrase merely CONTAINING a body name still links",
          smap.get("companies house scam letter") == "/guides/a-guide/")
    check("an ordinary multi-word keyword still links",
          smap.get("a distinctive topic phrase") == "/guides/b-guide/")

    figs = [(pp["slug"], pp["figure"]) for pp in live_posts if pp.get("figure")]
    check("the corpus carries at least one original figure", bool(figs), str(len(figs)))
    for slug, f in figs:
        check(f"{slug}: figure carries alt text", bool((f.get("alt") or "").strip()))
        check(f"{slug}: figure renders", bool(B.render_guide_figure(f)))
        check(f"{slug}: alt text is not just the title repeated",
              (f.get("alt") or "").strip() != (f.get("title") or "").strip())

    # ── internal-link map: generic phrases must not be auto-linked ───────────
    # build_internal_link_map promotes any 2+-word keyword owned by exactly ONE
    # guide into a site-wide link phrase. For a GENERIC phrase that rule lets one
    # guide capture every other article using the words. Added 2026-08-08 after
    # the 2026-08-08 pipeline draft — an article about Snapchat — had
    # "verification code scam" in its FAQ auto-linked to the unrelated Google
    # Voice guide, purely because that guide lists the phrase in its keywords.
    posts_all = json.loads(Path("content/posts.json").read_text(encoding="utf-8"))
    live_posts = [p for p in posts_all if not p.get("consolidated_into")]
    lmap = B.build_internal_link_map(live_posts)
    check("the generic phrase 'verification code scam' is not auto-linked",
          "verification code scam" not in lmap,
          f"maps to {lmap.get('verification code scam')!r}")
    # The stop-list is only load-bearing if it is actually consulted; a rename or
    # refactor that drops the filter would otherwise pass silently.
    check("every stop-listed phrase is absent from the link map",
          not [p for p in B._INTERNAL_LINK_STOPWORDS if p in lmap],
          f"leaked: {[p for p in B._INTERNAL_LINK_STOPWORDS if p in lmap]}")
    # Guard the fix's blast radius: the map must still do its job.
    check("the link map is still populated after stop-listing",
          len(lmap) > 1000, f"only {len(lmap)} phrases")

    # ── generic-phrase ownership, reviewed 2026-08-08 ────────────────────────
    # A phrase naming a whole scam FAMILY must not be owned by one narrow member
    # of that family. Where the corpus HAS a general guide the phrase is
    # editorially assigned; where it does not, the phrase is stop-listed. The
    # blanket stop-list assertion above already covers the four stop-listed
    # phrases, so this pins the assignment and, just as importantly, the seven
    # phrases that were reviewed and found CORRECT — so a later over-zealous
    # stop-list cannot silently delete working links.
    check("'job scam uk' is owned by the general job guide, not advance-fee",
          lmap.get("job scam uk") == "/guides/job-offer-scam-uk/",
          f"maps to {lmap.get('job scam uk')!r}")
    for phrase, expected in [
        ("fraud recovery scam", "/guides/refund-recovery-scam-warning-signs/"),
        ("recovery scam uk", "/guides/refund-recovery-scam-warning-signs/"),
        ("recovery scam warning signs", "/guides/refund-recovery-scam-warning-signs/"),
        ("report recovery scam uk", "/guides/refund-recovery-scam-warning-signs/"),
        ("report job scam uk", "/guides/job-offer-scam-uk/"),
        ("romance investment scam uk", "/guides/pig-butchering-scam-uk/"),
        ("website scam checker", "/guides/is-this-website-a-scam/"),
    ]:
        check(f"{phrase!r} still auto-links to its correct owner",
              lmap.get(phrase) == expected, f"maps to {lmap.get(phrase)!r}")
    # Every editorially-assigned owner must be a live slug. build_internal_link_map
    # raises on a dead owner, so reaching here at all proves it — but assert the
    # map actually contains each assignment, which a typo'd key would not.
    check("every _CANONICAL_KEYWORD_OWNERS entry reached the link map",
          all(lmap.get(p) == f"/guides/{s}/" for p, s in B._CANONICAL_KEYWORD_OWNERS.items()),
          f"{[p for p, s in B._CANONICAL_KEYWORD_OWNERS.items() if lmap.get(p) != f'/guides/{s}/']}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All hub self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
