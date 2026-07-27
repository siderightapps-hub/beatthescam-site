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
    check("scotland_routing is FLAG tier, not BLOCK (it does not stop a publish)",
          run_gate(bad, use_llm=False).passed)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All quick-answer gate self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
