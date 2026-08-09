#!/usr/bin/env python3
"""
gate_quickanswer_selftest.py — regression tests for quick-answer gate coverage.

The `quick_answer` field was added to the post schema on 2026-07-25. It renders
in a highlighted box and is targeted by `speakable` structured data, making it
the most extractable passage on a guide — but `content_gate._post_text()` did
not extract it until 2026-07-27. Nothing in the gate inspected it for two days,
and 57 live quick answers named Report Fraud with no Scottish route while
passing clean.

These tests lock that shut: they prove the field is extracted, that a bad
reporting route in a quick answer is detected, and that the existing
deterministic guards reach the field.

Offline: no API key, no network.

    python3 scripts/gate_quickanswer_selftest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_gate import _post_text, body_shingles, check_deterministic, run_gate

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def _shared_canon_block_fixtures(check) -> None:
    """The verified-route block must reach BOTH model-backed consumers.

    The gate's judge had a canon block since 2026-07-16; fact_reverify.py never
    did, and on 2026-07-31 that produced four false "drift" findings at
    `confidence: high` — all of them the Advice Direct Scotland pair, where the
    checker found one genuine number on an official page and concluded the other
    was stale. One renderer now feeds both, and a canon edit that fails to reach
    either consumer fails here.
    """
    import json
    import canon as canon_mod
    import content_gate as cg
    import fact_reverify as fr

    canon = canon_mod.load_canon()
    block = canon_mod.render_verified_facts(canon)

    check("gate and re-verification share one rendered canon block",
          cg._JUDGE_CANON_BLOCK == block == fr._canon_block())

    prompt = fr.REVERIFY_SYSTEM.format(today="2026-01-01", canon_block=fr._canon_block())
    check("the re-verification prompt actually embeds the block", block in prompt)

    # Every canon phone/SMS reaches both consumers — the property that was false.
    for r in canon["official_routes"] + canon.get("verified_org_contacts", []):
        for field in ("phone", "sms"):
            if r.get(field):
                check(f"canon {field} {r[field]} reaches the re-verification prompt",
                      r[field] in prompt, r.get("key", ""))

    # The specific false-positive guard: both ADS numbers present, plus the note
    # saying one does not supersede the other.
    check("both Advice Direct Scotland numbers are in the block",
          "0808 800 9060" in block and "0808 164 6000" in block)
    check("the block says one genuine number does not supersede the other",
          "NOT evidence that the other" in block)

    # on_page must be read by PRESENCE: a route that omits it is not "not the
    # reader-facing route", it simply does not carry the distinction.
    edited = json.loads(json.dumps(canon))
    for r in edited["official_routes"]:
        r.pop("on_page", None)
    check("a canon with no on_page fields marks nothing as non-reader-facing",
          "NOT the route reader prose names" not in canon_mod.render_verified_facts(edited))

    # A canon edit must propagate, not be shadowed by a hand-typed copy.
    mutated = json.loads(json.dumps(canon))
    mutated["official_routes"][0]["phone"] = "0300 999 0001"
    check("a canon phone edit propagates into the rendered block",
          "0300 999 0001" in canon_mod.render_verified_facts(mutated))


def _report_mailbox_fixtures(check) -> None:
    """A mailbox the guide tells the reader to report TO must be in the canon.

    _REPORT_EMAIL_RE only ever matched gov.uk / police.uk, so a reporting
    address on any other domain was invisible to the gate. The Student Loans
    Company's retired `phishing@slc.co.uk` shipped and stayed live through
    every prior audit, and an invented address would have passed identically —
    the same silent-by-construction gap as the SMS shortcode hole (audit,
    2026-07-31).
    """
    import content_gate as cg

    def draft(text):
        return {"slug": "mb", "title": "T", "description": "d", "hero": "h",
                "sections": [["S", text]], "faq": []}

    for addr in ("totally-invented@notreal.example", "phishing@slc.co.uk"):
        check(f"a non-canon reporting mailbox {addr} is flagged",
              any(i["check"] == "report_mailbox"
                  for i in cg.check_report_mailboxes(draft(f"Forward it to {addr}."))))

    for addr in sorted({e for e in cg.ALLOWED_REPORT_EMAILS})[:4]:
        check(f"canon mailbox {addr} is accepted",
              not cg.check_report_mailboxes(draft(f"Report it to {addr}.")))

    # Guides quote scammers' OWN addresses as examples. Flagging those would be
    # wrong, and would train everyone to ignore the check.
    for benign in ("The message came from security-alert@fake-bank.example, which is not real.",
                   "A sender like no-reply@totally-fake.example is a red flag.",
                   "Look at the address: billing@not-a-real-domain.example."):
        check("a scammer address quoted as an EXAMPLE is not flagged",
              not cg.check_report_mailboxes(draft(benign)), benign[:44])

    # Severity: FLAG, not BLOCK. 33 live guides name an organisation's own
    # reporting mailbox; blocking them would stop publication corpus-wide, and a
    # check that halts everything gets switched off rather than actioned.
    issues = cg.check_report_mailboxes(draft("Forward it to made-up@nowhere.example."))
    check("non-canon reporting mailboxes FLAG rather than BLOCK",
          issues and all(i["severity"] != cg.SEVERITY_BLOCK for i in issues))


def _shortcode_fixtures(check) -> None:
    """A 5–6 digit SMS shortcode offered as a reporting route must be in the canon.

    The phone regex only ever matched a hard-coded handful (7726, 159, 105, 101,
    999, 112), so ANY other shortcode was invisible: "forward the text to 61234"
    passed the gate clean and a fabricated reporting route could ship. Found while
    adding HMRC's genuine 60599 to the canon (2026-07-31); the new check
    immediately surfaced a real live one, NatWest's 88355, which verified against
    the bank's own page.
    """
    import content_gate as cg
    import canon as canon_mod

    def draft(text):
        return {"slug": "sc", "title": "T", "description": "d", "hero": "h",
                "sections": [["S", text]], "faq": []}

    codes = {r.get("sms") for g in ("official_routes", "verified_org_contacts")
             for r in canon_mod.load_canon().get(g, []) if r.get("sms")}
    check("the canon carries the verified shortcodes", {"7726", "60599", "88355"} <= codes,
          str(sorted(codes)))
    for code in sorted(codes):
        check(f"canon shortcode {code} is accepted as a reporting route",
              not cg.check_shortcodes(draft(f"Forward the suspicious text to {code}.")))
    for code in ("61234", "88802", "70707"):
        check(f"FABRICATED shortcode {code} is BLOCKED",
              any(i["severity"] == "block" for i in
                  cg.check_shortcodes(draft(f"Forward the suspicious text to {code}."))))
    # Context-bound, so ordinary numbers in prose are not dragged in.
    for benign in ("The scheme covered 12500 people in total.",
                   "Losses reached 45000 across the period.",
                   "Reference 90210 appears on the letter."):
        check("a bare 5-digit number in prose is NOT flagged", not cg.check_shortcodes(draft(benign)),
              benign)


def _consolidation_evasion_fixtures(check) -> None:
    """A DRAFT may never declare itself consolidated.

    `consolidated_into` removes a record from the public corpus AND from the
    duplicate-content check, so without this the cheapest route past a
    similarity BLOCK would be to add one field. The check tests field PRESENCE,
    not truthiness — `post.get(...)` returned falsy for "", None, False, [] and
    {}, so five malformed values passed (operator review, 2026-07-30). There was
    no direct fixture for any of this.
    """
    import corpus as corpus_mod

    def draft(**extra):
        return {"slug": "selftest-draft", "title": "Draft", "description": "d", "hero": "h",
                "sections": [["Section", "body text " * 80]], "faq": [], **extra}

    def blocks(post):
        return any(i["check"] == "consolidation_evasion" and i["severity"] == "block"
                   for i in check_deterministic(post, is_draft=True))

    for value in ("evri-delivery-scam-guide", "", None, False, [], {}):
        check(f"a draft setting consolidated_into={value!r} is BLOCKED",
              blocks(draft(**{corpus_mod.CONSOLIDATED_INTO: value})))
    check("a draft WITHOUT the field is clean",
          not blocks(draft()))
    # A LIVE record may legitimately carry it — corpus audits pass is_draft=False.
    check("a live record carrying the field is NOT blocked",
          not any(i["check"] == "consolidation_evasion" for i in check_deterministic(
              draft(**{corpus_mod.CONSOLIDATED_INTO: "evri-delivery-scam-guide"}),
              is_draft=False)))


def _canon_negative_fixtures(check) -> None:
    """Run scripts/canon.py's malformed-canon fixtures against the validator AND
    against both of its real consumers.

    `hubs-v10-c.md` §1: the build validated structure while the gate only
    parsed, so a parseable `{}` gave the gate empty route rendering and an empty
    allow-list rather than stopping publication. The fix was one shared
    validator; this is the test that the sharing is real, not just asserted in a
    docstring. Every fixture is written to a temp file and pushed through
    `build.load_sources()` and `content_gate._load_canon()` — the actual code
    paths a publish and a build take.
    """
    import json as _json
    import tempfile
    import canon as canon_mod

    # The validator itself.
    check("the reference canon fixture is VALID", not canon_mod.validate_canon(canon_mod._valid_fixture()))
    check("the live content/sources.json is VALID",
          not canon_mod.validate_canon(_json.loads(canon_mod.CANON_PATH.read_text(encoding="utf-8"))))
    fixtures = canon_mod.negative_fixtures()
    for desc, bad in fixtures:
        check(desc, bool(canon_mod.validate_canon(bad)))

    # Both consumers, on the same fixtures. A fixture that the validator rejects
    # but a consumer accepts means that consumer is not calling the validator.
    import build as _build
    import content_gate as _cg

    def _rejects(writer, payload) -> bool:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "content").mkdir()
            (root / "content" / "sources.json").write_text(_json.dumps(payload), encoding="utf-8")
            try:
                writer(root)
                return False
            except SystemExit:
                return True

    # EVERY fixture through BOTH consumers. Only one was, so "17 fixtures against
    # both real consumers" was inaccurate (operator review, 2026-07-30).
    build_rejected = sum(_rejects(lambda r: _build.load_sources(r), bad) for _, bad in fixtures)
    gate_rejected = sum(_rejects(lambda r: _cg._load_canon(r / "content" / "sources.json"), bad)
                        for _, bad in fixtures)
    check(f"build.load_sources() rejects all {len(fixtures)} malformed canons",
          build_rejected == len(fixtures), f"{build_rejected}/{len(fixtures)}")
    check(f"content_gate._load_canon() rejects all {len(fixtures)} malformed canons",
          gate_rejected == len(fixtures), f"{gate_rejected}/{len(fixtures)}")
    check("build.load_sources() rejects an unparseable canon",
          _rejects_raw(lambda r: _build.load_sources(r), "{not json"))
    check("content_gate._load_canon() rejects an unparseable canon",
          _rejects_raw(lambda r: _cg._load_canon(r / "content" / "sources.json"), "{not json"))
    # An ABSENT canon is a missing deployment input, not a degraded mode.
    check("build.load_sources() rejects an ABSENT canon", _rejects_absent(lambda r: _build.load_sources(r)))
    check("content_gate._load_canon() rejects an ABSENT canon",
          _rejects_absent(lambda r: _cg._load_canon(r / "content" / "sources.json")))
    # And the sidebar has no second copy of the routes to fall back to.
    check("report_block() has no hard-coded fallback route set",
          "reportfraud.police.uk" not in
          Path(_build.__file__).read_text(encoding="utf-8").split("def report_block")[1].split("\ndef ")[0])

    # ── ONE CONSUMER SERVICE PER NATION IN PROSE ────────────────────────────
    # Two GOV.UK pages print different Advice Direct Scotland numbers, and both
    # are genuine: 0808 800 9060 is advice.scot, 0808 164 6000 is the separate
    # consumeradvice.scot service the same charity runs (operator review,
    # 2026-07-29; resolved against GOV.UK and gov.scot on 2026-07-30). The canon
    # records BOTH so neither reads as invented, but prose must name exactly one
    # per nation or the reader gets two Scottish helplines in one sentence.
    _live_canon = canon_mod.load_canon()
    _advice = canon_mod.consumer_advice_routes(_live_canon)
    check("prose names exactly one consumer service per nation", len(_advice) == 3,
          str([r["key"] for r in _advice]))
    check("prose consumer nations are the three expected",
          [r["nation"] for r in _advice] == list(canon_mod.CONSUMER_ADVICE_NATIONS),
          str([r["nation"] for r in _advice]))
    for _rendered in (canon_mod.consumer_advice_clause(_live_canon),
                      canon_mod.render_prompt_routes(_live_canon),
                      canon_mod.reporting_section_instruction(_live_canon)):
        check("the second Advice Direct Scotland number stays out of rendered prose",
              "0808 164 6000" not in _rendered)
    # ...but the gate must still accept it, so a guide citing GOV.UK's
    # consumer-protection-rights page is not blocked for an "invented" number.
    check("the consumeradvice.scot number is in the gate's allow-list",
          "08081646000" in canon_mod.phone_digits(_live_canon))

    # ── EVERY CONSUMER DERIVES FROM THE CANON ───────────────────────────────
    # `hubs-v10-c.md` §2: render_canon_routes() fixed ACCURACY_BLOCK and
    # JUDGE_SYSTEM, but the generator still hand-typed the same routes in its
    # system prompt, its section brief, its closing rules and three fallback
    # passages, and the JavaScript checker kept its own copy entirely. The test
    # below is the one that matters: MUTATE the canon and assert every consumer
    # moves with it. A hand-typed copy anywhere fails here.
    import generate_content_claude as _gen
    import sync_canon_js as _sync

    check("the generated functions canon module is in sync with content/sources.json",
          _sync.TARGET.exists()
          and _sync.render(canon_mod.load_canon()) == _sync.TARGET.read_text(encoding="utf-8"),
          "run: python3 scripts/sync_canon_js.py")

    mutated = _json.loads(canon_mod.CANON_PATH.read_text(encoding="utf-8"))
    for _r in mutated["official_routes"]:
        if _r["key"] == "police-scotland":
            _r["phone"] = "1010"
    check("the mutated canon fixture is still structurally valid",
          not canon_mod.validate_canon(mutated))
    for label, rendered in (
        ("prompt route block", canon_mod.render_prompt_routes(mutated)),
        ("generator section brief", canon_mod.reporting_section_instruction(mutated)),
        ("generator scope rule", canon_mod.route_scope_rule(mutated)),
        ("generator system-prompt preamble", canon_mod.nation_routes_inline(mutated)),
        ("fallback article routing sentence", canon_mod.police_report_sentence(mutated)),
        ("functions canon module", _sync.render(mutated)),
    ):
        check(f"a canon phone change propagates to the {label}", "1010" in rendered)

    # The live generator's own strings must be the rendered ones, not lookalikes.
    _live = canon_mod.load_canon()
    check("SYSTEM_PROMPT embeds the rendered nation preamble",
          canon_mod.nation_routes_inline(_live) in _gen.SYSTEM_PROMPT)
    check("SYSTEM_PROMPT embeds the rendered route block via ACCURACY_BLOCK",
          canon_mod.render_prompt_routes(_live) in _gen.SYSTEM_PROMPT)
    check("SYSTEM_PROMPT embeds the Cifas/National Fraud Database rule",
          "National Fraud Database is a Cifas service" in _gen.SYSTEM_PROMPT)
    _prompt = _gen.build_prompt(_gen.Topic("test scam uk", "TestCo", "sms"), ["a-slug"])
    check("build_prompt embeds the rendered reporting-section brief",
          canon_mod.reporting_section_instruction(_live) in _prompt)
    check("build_prompt embeds the rendered scope rule",
          canon_mod.route_scope_rule(_live) in _prompt)
    _fb = _gen.fallback_post(_gen.Topic("test scam uk", "TestCo", "sms"), "2026-07-30")
    _fb_text = " ".join(b for _, b in _fb["sections"]) + " " + " ".join(a for _, a in _fb["faq"])
    check("the fallback article routes through the canon renderer",
          canon_mod.police_report_sentence(_live) in _fb_text)
    check("the fallback article scopes consumer advice by nation",
          canon_mod.consumer_advice_sentence(_live) in _fb_text)
    # The unsupported universal window (hubs-v10-c.md §6).
    check("the fallback article makes no 24-hour payment-recall claim",
          "24 hours" not in _fb_text and "24-hour" not in _fb_text)
    check("the fallback article is clean through the deterministic gate",
          not [i for i in check_deterministic(_fb) if i["severity"] == "block"])


def _rejects_raw(writer, text: str) -> bool:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "content").mkdir()
        (root / "content" / "sources.json").write_text(text, encoding="utf-8")
        try:
            writer(root)
            return False
        except SystemExit:
            return True


def _rejects_absent(writer) -> bool:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "content").mkdir()
        try:
            writer(root)
            return False
        except SystemExit:
            return True


def post(**over) -> dict:
    base = {
        "slug": "test-guide", "title": "Test guide", "description": "A test guide description.",
        "hero": "A hero line.", "keywords": ["test"],
        "sections": [["A heading", "Some ordinary body text about a scam."]],
        "faq": [["A question?", "An answer."]],
    }
    base.update(over)
    return base


def issues_of(p: dict, check_name: str) -> list:
    return [i for i in check_deterministic(p) if i["check"] == check_name]


def run() -> int:
    # ── extraction ───────────────────────────────────────────────────────────
    marker = "zzuniquequickanswermarker"
    check("quick_answer is extracted by _post_text",
          marker in _post_text(post(quick_answer=f"Verdict {marker} here.")))
    check("absent quick_answer does not crash extraction",
          isinstance(_post_text(post()), str))

    # ── the Scotland-routing regression this test exists for ────────────────
    bad = post(quick_answer="Report it to Report Fraud at reportfraud.police.uk or on 0300 123 2040.")
    check("quick answer naming Report Fraud with no Scottish route is FLAGGED",
          len(issues_of(bad, "scotland_routing")) == 1, str(check_deterministic(bad)))

    good = post(quick_answer=("Report it to Report Fraud on 0300 123 2040 in England, Wales or "
                              "Northern Ireland, or Police Scotland on 101 in Scotland."))
    check("quick answer that routes Scotland is NOT flagged",
          not issues_of(good, "scotland_routing"))

    check("quick answer with no reporting service at all is NOT flagged",
          not issues_of(post(quick_answer="Do not tap the link; open the app yourself."), "scotland_routing"))

    check("bare 0300 123 2040 without the brand name is still caught",
          len(issues_of(post(quick_answer="Call 0300 123 2040 to report it."), "scotland_routing")) == 1)

    check("meta description is checked too",
          len(issues_of(post(description="Report it to Report Fraud on 0300 123 2040."), "scotland_routing")) == 1)

    # Scotland routing in a SECTION must not excuse its absence from the quick
    # answer — someone hearing the speakable summary never reaches the section.
    split = post(quick_answer="Report it to Report Fraud on 0300 123 2040.",
                 sections=[["Reporting", "In Scotland, contact Police Scotland on 101."]])
    check("Scotland route in a section does NOT excuse the quick answer",
          len(issues_of(split, "scotland_routing")) == 1)

    # ── existing guards must now reach the field ─────────────────────────────
    # ScamSmart is retired FCA branding — the gate reports it as `retired_branding`.
    banned = post(quick_answer="Check the firm on the FCA ScamSmart register before paying.")
    check("retired-branding guard reaches the quick answer",
          any(i["check"] == "retired_branding" for i in check_deterministic(banned)),
          str([i["check"] for i in check_deterministic(banned)]))

    phone = post(quick_answer="Ring the bank on 0800 555 1234 straight away.")
    check("non-canon phone in a quick answer is caught",
          any(i["check"] == "phone" for i in check_deterministic(phone)),
          str([i["check"] for i in check_deterministic(phone)]))

    s75 = post(quick_answer="Section 75 covers credit purchases from £100 to £30,000.")
    check("Section 75 inclusive form in a quick answer is caught",
          any(i["check"] == "section75_scope" for i in check_deterministic(s75)),
          str([i["check"] for i in check_deterministic(s75)]))

    # ── severity contract ────────────────────────────────────────────────────
    # Promoted to BLOCK on 2026-07-27: sending a whole nation to the wrong
    # reporting route is exactly what the gate exists to stop, and FLAG tier
    # meant run_gate() still returned passed=True on all 57 live cases.
    check("scotland_routing is BLOCK tier — a missing Scottish route stops a publish",
          not run_gate(bad, use_llm=False).passed)


    # ── canon guards added 2026-07-27 from the operator review corrections ───
    check("159 described as free is flagged",
          any(i["check"] == "159_cost" for i in check_deterministic(post(
              sections=[["Reporting", "Use the free 159 service to reach your bank."]]))))
    check("'159 is not necessarily free' is NOT flagged (negation)",
          not any(i["check"] == "159_cost" for i in check_deterministic(post(
              sections=[["Reporting", "Your provider sets the price of a 159 call, so it is not necessarily free."]]))))

    check("DBS without Disclosure Scotland/AccessNI is flagged",
          any(i["check"] == "dbs_jurisdiction" for i in check_deterministic(post(
              sections=[["Checks", "GOV.UK lists a basic DBS check fee."]]))))
    check("DBS alongside the other nations is NOT flagged",
          not any(i["check"] == "dbs_jurisdiction" for i in check_deterministic(post(
              sections=[["Checks", "DBS covers England and Wales; Scotland uses Disclosure Scotland and "
                                    "Northern Ireland uses AccessNI."]]))))

    check("fee exception without professional sport is flagged",
          any(i["check"] == "fee_exception_scope" for i in check_deterministic(post(
              sections=[["Fees", "Agencies in entertainment and modelling are an exception."]]))))
    check("fee exception naming professional sports people is NOT flagged",
          not any(i["check"] == "fee_exception_scope" for i in check_deterministic(post(
              sections=[["Fees", "Schedule 3 covers entertainment and modelling occupations and "
                                  "professional sports people."]]))))

    check("unsourced 'thousands' in a hero is flagged",
          any(i["check"] == "scale_claim" for i in check_deterministic(post(
              hero="These scams cost UK victims thousands every month."))))
    check("attributed 'thousands' is NOT flagged",
          not any(i["check"] == "scale_claim" for i in check_deterministic(post(
              hero="UK Finance reported thousands of cases in 2025."))))
    check("scale claim in a section body is NOT flagged (surfaces only)",
          not any(i["check"] == "scale_claim" for i in check_deterministic(post(
              sections=[["Losses", "Victims can lose thousands."]]))))

    # ── Scotland-routing matcher: the real regression cases ──────────────────
    # These exist because three earlier versions of the matcher each reported
    # clean on text a human then had to catch, and because a previous commit
    # message claimed these tests existed when they did not.
    def qa(text): return post(quick_answer=text)
    def blocks(text): return not run_gate(qa(text), use_llm=False).passed

    check("approved compact clause passes",
          not blocks("Hang up, and report it to Report Fraud or Police Scotland on 101."))
    check("full geography-qualified form passes",
          not blocks("Report it to Report Fraud in England, Wales or Northern Ireland, or "
                     "Police Scotland on 101 in Scotland."))
    check("missing Scottish route BLOCKS a publish",
          blocks("Report it to Report Fraud on 0300 123 2040."))
    check("bare 'Scotland' with no 101 blocks",
          blocks("Report it to Report Fraud, or Police Scotland in Scotland."))
    check("bare 101 without naming the force blocks",
          blocks("Report it to Report Fraud or call 101."))
    check("101 as a statistic is not a route",
          blocks("Police Scotland recorded 101 reports last month. Report it to Report Fraud."))
    check("negated route is not a route",
          blocks("Do not report this to Police Scotland on 101; report it to Report Fraud."))
    # CONTRACT CHANGED 2026-07-27: the operator's approved prose form is two
    # sentences, so a route in the IMMEDIATELY FOLLOWING sentence of the SAME
    # field is now served. A route further away, or in another field, is not —
    # covered by the "later section" test below.
    check("route in the immediately next sentence of the same field is served",
          not blocks("Report it to Report Fraud. In Scotland, contact Police Scotland on 101."))
    check("route three sentences later in the same field is NOT served",
          blocks("Report it to Report Fraud. Keep your evidence. Save the messages. "
                 "In Scotland, contact Police Scotland on 101."))

    # The two malformed strings that a bulk edit actually shipped past review.
    check("v1 failure: trailing dangling 'or.' blocks",
          blocks("...report the call to Report Fraud, or Police Scotland in Scotland or."))
    check("v1 failure: clause spliced into an unrelated list blocks",
          blocks("Official routes — your bank, the police, Report Fraud, or Police Scotland in "
                 "Scotland, the Financial Ombudsman — never charge a fee."))
    check("malformed text mid-field is caught, not just at the end",
          blocks("Do not pay or. Report it to Report Fraud or Police Scotland on 101."))
    # False positive found by running the guard over the live corpus: "on" is a
    # phrasal-verb particle here, not a dangling preposition.
    check("phrasal verb ending a sentence is NOT malformed",
          not any(i["check"] == "malformed_text" for i in check_deterministic(post(
              description="No genuine company needs you to bank a cheque and wire money on."))))
    # Two false positives found by running the tightened matcher over the
    # operator-approved replacement answers: a negation earlier in the sentence
    # usually governs a DIFFERENT clause, not the reporting route.
    check("negation on a different clause does NOT block (Don't pay ... report it)",
          not blocks("Don't pay, end the contact, and report it to Report Fraud or Police Scotland on 101."))
    check("negation on a different clause does NOT block (never grant ... report it)",
          not blocks("Close the tab, never grant remote access, and report it to reportphishing@apple.com "
                     "and any loss to Report Fraud or Police Scotland on 101."))
    check("the route itself being negated DOES still block",
          blocks("Do not report this to Police Scotland on 101; report it to Report Fraud."))

    check("dangling 'to' IS still malformed",
          any(i["check"] == "malformed_text" for i in check_deterministic(post(
              description="Report it to. Then contact your bank."))))

    # ── hub prose coverage + case sensitivity (operator review 2026-07-27) ────
    def hub(sections, faq=None, intro="<p>Intro.</p>"):
        return {"slug": "t", "title": "T" * 40, "description": "D" * 140,
                "intro": intro, "sections": sections, "faq": faq or [["Q?", "A."]]}
    def hub_blocks(h): return not run_gate(h, use_llm=False).passed
    SCOPE = ("Report Fraud covers England, Wales and Northern Ireland. If you live in Scotland "
             "or the crime happened there, contact Police Scotland on 101.")

    check("hub SECTION with an incomplete route blocks",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud on 0300 123 2040.</p>"]])))
    check("hub FAQ with an incomplete route blocks",
          hub_blocks(hub([["S", "<p>x</p>"]], [["How?", "Use Report Fraud on 0300 123 2040."]])))
    check("hub INTRO with an incomplete route blocks",
          hub_blocks(hub([["S", "<p>x</p>"]], intro="<p>Report it to Report Fraud.</p>")))
    check("hub section with a paired route passes",
          not hub_blocks(hub([["R", "<p>Report it to Report Fraud or Police Scotland on 101.</p>"]])))
    check("a route in a LATER section does not serve an earlier one",
          hub_blocks(hub([["A", "<p>Report it to Report Fraud.</p>"],
                          ["B", "<p>In Scotland, contact Police Scotland on 101.</p>"]])))
    check("the operator's canonical two-sentence block is accepted",
          not hub_blocks(hub([["R", f"<p>Report suspected fraud to Report Fraud. {SCOPE}</p>"]])))
    check("a scope sentence WITHOUT the route sentence still blocks",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud. Report Fraud covers England, Wales "
                                "and Northern Ireland.</p>"]])))

    # "Report Fraud" is a brand name that is also an ordinary verb phrase. Matching
    # it case-insensitively produced 111 false positives and broke the build.
    check("lowercase 'report fraud' as a verb phrase is NOT treated as the service",
          not hub_blocks(hub([["R", "<p>Contact your bank on the number on your card, block the "
                                    "card and report fraud.</p>"]])))
    check("the service name IS still caught",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud.</p>"]])))
    check("the reportfraud.police.uk URL is caught case-insensitively",
          hub_blocks(hub([["R", "<p>See REPORTFRAUD.POLICE.UK for details.</p>"]])))

    # EVERY named mention must be served. The first implementation short-circuited
    # on the first canonical scope+route pair and returned "served" for the whole
    # field, so a later unpaired mention was never inspected (operator review,
    # 2026-07-27). These four cases are the operator's prescribed regression set.
    check("a correct pair followed by an unpaired mention in the SAME field blocks",
          hub_blocks(hub([["R", f"<p>{SCOPE} Later, report the loss to Report Fraud.</p>"]]))),
    check("an unpaired mention in a SEPARATE section blocks",
          hub_blocks(hub([["R", f"<p>Report suspected fraud to Report Fraud. {SCOPE}</p>"],
                          ["More", "<p>You can also report the loss to Report Fraud.</p>"]])))
    check("an unpaired mention in a SEPARATE FAQ blocks",
          hub_blocks(hub([["R", f"<p>Report suspected fraud to Report Fraud. {SCOPE}</p>"]],
                         faq=[["Where do I report it?", "Report it to Report Fraud."]])))
    check("the approved adjacent two-sentence canonical pair still passes",
          not hub_blocks(hub([["R", "<p>Report Fraud covers England, Wales and Northern Ireland. "
                                    "If you live in Scotland or the crime happened there, contact "
                                    "Police Scotland on 101.</p>"]])))
    check("the approved same-sentence pair still passes",
          not hub_blocks(hub([["R", "<p>Report it to Report Fraud at reportfraud.police.uk or "
                                    "0300 123 2040 in England, Wales or Northern Ireland, or to "
                                    "Police Scotland on 101 in Scotland.</p>"]])))
    check("two correctly-paired mentions in one field pass",
          not hub_blocks(hub([["R", "<p>Report it to Report Fraud, or Police Scotland on 101 in "
                                    "Scotland. Then report the loss to Report Fraud at "
                                    "reportfraud.police.uk, or Police Scotland on 101 in "
                                    "Scotland.</p>"]])))
    # ONE rendering of the reporting routes, derived from the canon and shared by
    # every prompt. The routes were previously hand-typed in five places and
    # drifted (operator reviews, 2026-07-28/29).
    from content_gate import (ACCURACY_BLOCK, JUDGE_SYSTEM, CANON_ROUTE_BLOCK,
                              render_canon_routes, _CANON)
    check("the generator prompt carries the canon-rendered routes",
          CANON_ROUTE_BLOCK in ACCURACY_BLOCK)
    check("the judge prompt carries the canon-rendered routes",
          CANON_ROUTE_BLOCK in JUDGE_SYSTEM)
    for needed in ("England, Wales and Northern Ireland", "Police Scotland", "Scotland",
                   "Northern Ireland", "Never present Report Fraud as the UK-wide route",
                   "Never present Citizens Advice as a UK-wide helpline"):
        check(f"the rendered route block states {needed!r}", needed in CANON_ROUTE_BLOCK)
    check("the generator accuracy block states the Cifas/National Fraud Database rule",
          "National Fraud Database is a Cifas service" in ACCURACY_BLOCK and
          "Cifas Protective Registration" in ACCURACY_BLOCK)
    # No prompt may keep its own copy of a canon phone number.
    import re as _re
    for name, text in (("ACCURACY_BLOCK", ACCURACY_BLOCK), ("JUDGE_SYSTEM", JUDGE_SYSTEM)):
        residue = _re.findall(r"0808\s*223\s*1133|0808\s*800\s*9060|0300\s*123\s*6262",
                              text.replace(CANON_ROUTE_BLOCK, ""))
        check(f"{name} has no hand-typed consumer number outside the rendered block",
              not residue, str(residue))
    # A canon change must reach the rendering, not just the allowlist.
    import copy as _copy
    _mut = _copy.deepcopy(_CANON)
    for _r in _mut.get("official_routes", []):
        if _r.get("key") == "police-scotland":
            _r["phone"] = "999999"
    check("editing the canon changes the rendered route block",
          "999999" in render_canon_routes(_mut))

    # Citizens Advice covers ENGLAND AND WALES only. Naming it as a general UK
    # helpline strands Scottish and Northern Irish readers (operator review,
    # 2026-07-27). It is also a research publisher, so a CITATION must not flag.
    def qa_blocks(t):
        return bool([i for i in check_deterministic(post(quick_answer=t))
                     if i["check"] == "nation_consumer_routing"])
    check("an unscoped Citizens Advice helpline blocks",
          qa_blocks("Contact Citizens Advice on 0808 223 1133 for help with the trader."))
    check("the bare England-and-Wales number blocks",
          qa_blocks("Call 0808 223 1133 for help with the trader."))
    check("Citizens Advice in a list of advice bodies blocks",
          qa_blocks("Free debt advice is available from StepChange, National Debtline "
                    "and Citizens Advice, so never pay to get started."))
    check("the three-nation form passes",
          not qa_blocks("Citizens Advice in England and Wales on 0808 223 1133, Advice Direct "
                        "Scotland in Scotland on 0808 800 9060, or Consumerline in Northern "
                        "Ireland on 0300 123 6262."))
    check("a correct three-nation sentence does NOT excuse a later mention",
          qa_blocks("Ask your nation's consumer service about reviews. Then take the contract "
                    "to Citizens Advice."))
    check("CITING Citizens Advice research is not a route",
          not qa_blocks("Online shopping was the most commonly reported scam type in Citizens "
                        "Advice's 2025 Scams Awareness survey, at 26%."))
    check("pointing at the reader's own nation passes",
          not qa_blocks("Ask your nation's consumer service about the trader."))

    # ── CANON VALIDATION, SHARED BY THE GATE AND THE BUILD ──────────────────
    # The hand-maintained phone/email fallbacks are gone (operator review,
    # 2026-07-29): they were a second, unreviewed copy of the canon that drifted
    # twice, and they only ever activated at the exact moment the single source
    # of truth had failed. What is tested instead is that ONE validator rejects
    # every malformed shape, and that BOTH consumers actually call it.
    _canon_negative_fixtures(check)
    _consolidation_evasion_fixtures(check)
    _shortcode_fixtures(check)
    _report_mailbox_fixtures(check)
    _shared_canon_block_fixtures(check)

    # Citation prose is not a consumer route.
    check("'Data from Citizens Advice shows...' is a citation, not a route",
          not qa_blocks("Data from Citizens Advice shows online shopping complaints are common."))
    check("'Research from Citizens Advice found...' is a citation, not a route",
          not qa_blocks("Research from Citizens Advice found that scams cause harm."))
    check("'advice is available from ... Citizens Advice' IS a route",
          qa_blocks("Free debt advice is available from StepChange, National Debtline and "
                    "Citizens Advice."))

    # Experian, Equifax and TransUnion are the three MAIN agencies; MoneyHelper
    # also lists Crediva (operator review, 2026-07-27). "Three main" is correct;
    # an exhaustive "all three" / "the other two" is not.
    def cra_blocks(t):
        return bool([i for i in check_deterministic(post(quick_answer=t))
                     if i["check"] == "cra_exhaustive"])
    check("'all three UK credit reference agencies' blocks",
          cra_blocks("Check all three UK credit reference agencies — Experian, Equifax and TransUnion."))
    check("'the other two credit reference agencies' blocks",
          cra_blocks("Then check your file with the other two credit reference agencies."))
    check("naming all four agencies passes",
          not cra_blocks("Check the reports held by all four agencies MoneyHelper lists — Experian, "
                         "Equifax and TransUnion, the three main ones, plus the smaller Crediva."))
    check("'three main agencies' passes",
          not cra_blocks("Experian, Equifax and TransUnion are the three main agencies."))
    check("naming the three without an exhaustive claim passes",
          not cra_blocks("Check your credit file with Experian, Equifax and TransUnion."))
    check("a correct CRA sentence does NOT excuse a later exhaustive one",
          cra_blocks("Experian, Equifax and TransUnion are the three main agencies; Crediva is "
                     "also listed. Later, check all three UK credit reference agencies."))
    check("'Crediva is also listed' does not excuse 'the other two'",
          cra_blocks("Crediva is also listed by MoneyHelper. Check the other two credit "
                     "reference agencies as well."))
    check("'the only UK credit reference agencies are' blocks",
          cra_blocks("The only UK credit reference agencies are Experian, Equifax and TransUnion."))
    check("a correct clause does NOT excuse a contrasting one in the same sentence",
          cra_blocks("Experian, Equifax and TransUnion are the three main agencies, but check "
                     "all three UK credit reference agencies."))
    check("'Crediva is also listed, but ... the other two' blocks",
          cra_blocks("Crediva is also listed, but you only need to check the other two credit "
                     "reference agencies."))
    check("a three-dot MENU instruction does not block",
          not cra_blocks("Report the profile: tap the three-dot menu on the profile or in the chat "
                         "and choose to report it."))
    check("'all three' about something else does not block",
          not cra_blocks("All three of your bank cards should be replaced immediately."))

    # A Police Scotland + 101 match is only a ROUTE when a positive route verb
    # governs it and no negation governs that verb. Co-occurrence is not a route,
    # and the negation vocabulary must cover call/ring/dial (operator review,
    # 2026-07-27).
    check("a Police Scotland 101 STATISTIC is not a route",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud. Police Scotland recorded 101 "
                                "reports last month.</p>"]])))
    check("'Do not call Police Scotland on 101' is not a route",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud. Do not call Police Scotland "
                                "on 101.</p>"]])))
    check("'Never ring Police Scotland on 101' is not a route",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud. Never ring Police Scotland "
                                "on 101.</p>"]])))
    check("'Instead of contacting Police Scotland on 101' is not a route",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud. Instead of contacting Police "
                                "Scotland on 101, keep the evidence.</p>"]])))
    check("a negation in an EARLIER clause does not negate the route",
          not hub_blocks(hub([["R", "<p>Don't pay; report it to Report Fraud or Police Scotland "
                                    "on 101.</p>"]])))

    check("a narrative 'we reported ... Police Scotland recorded 101' is not a route",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud. We reported yesterday that Police "
                                "Scotland recorded 101 cases.</p>"]])))
    check("a LONG-DISTANCE negation still blocks the route",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud. Do not under any circumstances ever "
                                "call Police Scotland on 101.</p>"]])))
    check("post-verbal contrast ('contact X, not Police Scotland') is not a route",
          hub_blocks(hub([["R", "<p>Report it to Report Fraud. Contact your bank, not Police "
                                "Scotland on 101.</p>"]])))

    # ── figure text is gated like any other reader-visible field ─────────────
    # The `figure` field shipped on 2026-08-01 and NOTHING in the gate read it
    # for a day: an inline diagram could have named an invented number and every
    # suite stayed green. These fixtures assert the coverage by CONSEQUENCE —
    # each one is a claim class that must BLOCK or FLAG — rather than asserting
    # that some string reaches some extractor. A future field wired to the
    # renderer but not to `_figure_fields` fails here.
    def fig(**over) -> dict:
        f = {"title": "Three checks, in order",
             "alt": "Decision ladder. One: does it ask for payment through a link?",
             "caption": "Original diagram.",
             "steps": [{"check": "Does it ask for payment through a link?",
                        "then": "Genuine couriers do not collect fees that way."}]}
        f.update(over)
        return post(figure=f)

    check("a benign figure is clean",
          not check_deterministic(fig()))
    check("an invented phone number in figure ALT TEXT blocks",
          issues_of(fig(alt="Call the fraud line on 0300 999 1234 to report it."), "phone"))
    check("retired branding in a figure STEP is flagged",
          issues_of(fig(steps=[{"check": "Is the firm listed?",
                                "then": "Use the FCA ScamSmart register to check."}]),
                    "retired_branding"))
    check("routing the National Fraud Database via Report Fraud in a figure blocks",
          issues_of(fig(steps=[{"check": "Is your identity at risk?",
                                "then": "Report it to Report Fraud to add your name to the National "
                                        "Fraud Database. Report Fraud covers England, Wales and "
                                        "Northern Ireland. If you live in Scotland, report to Police "
                                        "Scotland on 101."}]),
                    "nfd_routing"))
    check("Report Fraud in a figure with no Scottish route is caught",
          issues_of(fig(alt="Report it to Report Fraud on 0300 123 2040."), "scotland_routing"))
    check("a US-style fraud alert in a figure is caught",
          issues_of(fig(steps=[{"check": "Has your identity been used?",
                                "then": "Place a fraud alert on your credit file with the three CRAs."}]),
                    "cra_exhaustive"))
    check("a dangling conjunction in figure alt text is caught",
          issues_of(fig(alt="Check the sender and."), "malformed_text"))

    # Alt text is the ONLY version of the diagram a screen-reader user gets, so
    # it is checked as prose, not treated as a metadata attribute.
    check("figure alt text reaches _post_text",
          "zzfiguremarker" in _post_text(fig(alt="Ladder. zzfiguremarker")))
    check("figure step outcomes reach _post_text",
          "zzstepmarker" in _post_text(fig(steps=[{"check": "C?", "then": "zzstepmarker"}])))

    # Malformed figures must not crash the gate — a record that fails to render
    # a figure still has to be publishable, or a bad optional field takes the
    # whole guide down.
    check("a non-dict figure does not crash the gate",
          not check_deterministic(post(figure="not a dict")))
    check("non-dict steps do not crash the gate",
          not check_deterministic(post(figure={"title": "T", "alt": "A.", "steps": ["x", None]})))
    check("an absent figure does not crash the gate",
          not check_deterministic(post()))

    # Similarity: a templated figure is the cookie-cutter risk at corpus scale,
    # so figure words must COUNT toward the duplication measure rather than
    # riding along untested.
    check("figure text contributes to the similarity shingles",
          len(body_shingles(fig())) > len(body_shingles(post())))

    # ── unrenderable markup (added 2026-08-08) ───────────────────────────────
    # The 2026-08-08 pipeline draft emitted eight **bold** bullets and the gate
    # passed it clean, because nothing in the gate looked at rendering at all.
    # build.py has no bold renderer, so the asterisks reached the page. BLOCK:
    # there is no context in which build.py renders these correctly.
    bold = post(sections=[["A heading", "- **Urgent language and threats.** More body text here."]])
    check("literal **bold** in a section body is BLOCKED",
          any(i["severity"] == "block" for i in issues_of(bold, "unrenderable_markup")))
    check("literal **bold** in an faq answer is BLOCKED",
          any(i["severity"] == "block"
              for i in issues_of(post(faq=[["Q?", "An **emphatic** answer."]]), "unrenderable_markup")))
    check("literal **bold** in quick_answer is BLOCKED",
          bool(issues_of(post(quick_answer="A **bold** verdict."), "unrenderable_markup")))
    check("an EXTERNAL markdown link is BLOCKED",
          bool(issues_of(post(sections=[["H", "See [the FCA](https://www.fca.org.uk/) for more."]]),
                         "unrenderable_markup")))
    # build.py DOES render internal root-relative links (6c881a5f7) — flagging
    # them would forbid the one markdown link form that actually works.
    check("an INTERNAL root-relative markdown link is allowed",
          not issues_of(post(sections=[["H", "See [our guide](/guides/some-slug/) for more."]]),
                        "unrenderable_markup"))
    check("ordinary prose is not flagged as unrenderable",
          not issues_of(post(), "unrenderable_markup"))
    # A lone pair of asterisks around nothing is not emphasis; keep the guard
    # from firing on maths or footnote markers.
    check("a bare '**' with no enclosed text is not flagged",
          not issues_of(post(sections=[["H", "Rated ** out of five in the review."]]),
                        "unrenderable_markup"))

    # ── credit-file annotation (added 2026-08-08) ────────────────────────────
    # _FRAUD_ALERT_RE requires the literal words "fraud alert"; the 2026-08-08
    # draft said "...Protective Registration ... to add a note to your credit
    # file" and matched nothing. Cifas PR flags the National Fraud Database, not
    # your credit file.
    check("'add a note to your credit file' is FLAGGED",
          bool(issues_of(post(sections=[["H", "Register with Cifas Protective Registration at "
                                              "cifas.org.uk to add a note to your credit file."]]),
                         "credit_file_annotation")))
    check("'place a marker on your credit report' is FLAGGED",
          bool(issues_of(post(sections=[["H", "They will place a marker on your credit report."]]),
                         "credit_file_annotation")))
    check("a correct Cifas description is NOT flagged",
          not issues_of(post(sections=[["H", "Cifas Protective Registration places a warning flag in "
                                             "the National Fraud Database for two years."]]),
                        "credit_file_annotation"))
    check("ordinary credit-file mentions are not flagged",
          not issues_of(post(sections=[["H", "Check your credit file with Experian, Equifax, "
                                             "TransUnion or Crediva."]]),
                        "credit_file_annotation"))

    # ── NCSC route scope (added 2026-08-08) ──────────────────────────────────
    # The NCSC runs three routes: EMAIL -> the SERS mailbox, WEBSITE -> the
    # separate scam-website form, TEXT -> 7726 (the mobile networks, already
    # guarded by _SHORTCODE_NCSC_RE). The 2026-08-08 draft sent a phishing LINK
    # to the SERS mailbox; the NCSC's own scam-website page never mentions it.
    def ncsc(body):
        return issues_of(post(sections=[["H", body]]), "ncsc_route_scope")

    check("the real 2026-08-08 sentence is FLAGGED",
          bool(ncsc("If the scam involved a phishing link (a fake login page), report it to the "
                    "National Cyber Security Centre (NCSC) Suspicious Email Reporting Service at "
                    "report@phishing.gov.uk.")),
          "the service's own name contains 'Email', which must not mask the misroute")
    check("a website routed to the SERS mailbox is FLAGGED",
          bool(ncsc("Report the fake website to report@phishing.gov.uk.")))
    check("a URL routed to the SERS mailbox is FLAGGED",
          bool(ncsc("Copy the URL and send it to report@phishing.gov.uk.")))
    # The mailbox is correct for emails and appears on 113 live guides — a guard
    # that fires on those would be worse than no guard at all.
    check("forwarding EMAILS to the mailbox is NOT flagged",
          not ncsc("Forward suspicious emails to report@phishing.gov.uk and then delete them."))
    check("a link INSIDE an email is NOT flagged",
          not ncsc("If you clicked a link in an email, forward that email to report@phishing.gov.uk."))
    check("naming the mailbox with no subject noun is NOT flagged",
          not ncsc("The NCSC runs report@phishing.gov.uk for phishing reports."))
    check("a website named in a PRIOR sentence is NOT flagged",
          not ncsc("Never enter details on a copycat website. Forward the suspicious email to "
                   "report@phishing.gov.uk."),
          "the clause window must stop at the sentence boundary")
    # The mailbox must come from the canon, not a literal in the gate.
    from content_gate import _sers_email, _CANON
    check("the SERS mailbox is read from the canon",
          _sers_email() == "report@phishing.gov.uk", f"got {_sers_email()!r}")
    check("the canon carries a distinct website-reporting route",
          any(r.get("key") == "ncsc-scam-website" for r in _CANON.get("official_routes", [])))

    # ── judge instructions for the two non-deterministic findings ────────────
    # Operator findings 1 and 4 cannot be reached by a regex: one is a claim
    # about a third party's product behaviour, the other is an OMISSION that a
    # pattern would have to detect by absence, firing on every guide that
    # legitimately says nothing about payments. Both are therefore judge-side.
    # The judge DID run on the 2026-08-08 draft (manifest records
    # claude-haiku-4-5-20251001) and recorded zero claims, so these instructions
    # are the fix for a check that executed and missed, not a new check.
    # Model behaviour can't be asserted offline; what CAN be asserted is that the
    # instructions survive refactoring, which is what silently lost coverage
    # before (quick_answer went unextracted for two days in 2026-07).
    from content_gate import JUDGE_SYSTEM
    for name, needle in [
        ("platform-verification claims are in the judge prompt", "badge / tick / checkmark proves identity"),
        ("the 'any variation is a scam' form is named", '"any variation is a scam"'),
        ("the APP omission case is in the judge prompt", "mandatory under Payment Systems Regulator rules"),
        ("the omission check is scoped to money the reader sent", "THEMSELVES AUTHORISED AND SENT"),
        # Scoping added after a live run flagged a CARD-DETAILS guide, where APP
        # reimbursement is the wrong protection entirely.
        ("card-detail and chargeback cases are excluded", "chargeback or Section"),
        # The omission section broadened the judge's whole remit on its first
        # version — it began raising "should also clarify" nitpicks on a clean
        # guide and failing it. This pins the containment wording.
        ("the omission check cannot spread to other missing content", 'could begin with the words "the guide should also"'),
        ("a no-high-severity verdict must be a pass", "A guide with no high-severity issue is a passing guide"),
        ("the recall-vs-reimbursement distinction is spelled out", "a recall is a courtesy"),
        ("the judge is told NOT to state cap/excess figures", "cannot verify"),
        ("both classes are pinned to medium severity", 'use "medium", never "high"'),
    ]:
        check(name, needle in JUDGE_SYSTEM, f"missing from JUDGE_SYSTEM: {needle!r}")
    # The canon block must still reach the judge — a model-backed check with no
    # canon re-litigates settled routes, which cost two prior debugging sessions.
    # Asserted on route BRANDS, not hostnames: a `"host.tld" in text` test is the
    # exact shape of py/incomplete-url-substring-sanitization, and CodeQL cannot
    # tell a prompt assertion from a URL allow-list check. Brands are also the
    # better assertion — they are what the judge actually reasons about.
    _brands = {r.get("brand") for r in _CANON.get("official_routes", []) if r.get("brand")}
    check("the judge prompt still carries the verified-route canon block",
          "VERIFIED ROUTES" in JUDGE_SYSTEM
          and {"Report Fraud", "Police Scotland"} <= _brands
          and all(b in JUDGE_SYSTEM for b in ("Report Fraud", "Police Scotland")))

    # NB: a mention placed BEFORE the scope+route block is served, not stranded —
    # that is the approved guide form (instruction, scope, route) and the reader
    # reaches the route by reading on. Only a mention with no route within the
    # two-sentence window strands anyone; "route three sentences later in the
    # same field is NOT served" above is the case that pins the window down.
    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All quick-answer gate self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
