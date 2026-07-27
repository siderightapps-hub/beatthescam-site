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
from content_gate import _post_text, check_deterministic, run_gate

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


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
