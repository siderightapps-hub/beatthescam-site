#!/usr/bin/env python3
"""
gate_selftest.py — LIVE validation of the content accuracy gate.

Runs the FULL gate (deterministic checks + the LLM judge) against three fixed
sample guides and asserts it behaves correctly. Use this to confirm the judge
is actually working BEFORE re-enabling the paused content crons.

    ANTHROPIC_API_KEY=...  python3 scripts/gate_selftest.py
    # (or put the key in .env — gitignored — and it loads automatically)
    python3 scripts/gate_selftest.py --model claude-haiku-4-5-20251001

Exit 0 = all checks passed (gate is working). Non-zero = a check failed —
do NOT re-enable the crons until it passes. Side-effect-free: never writes to
posts.json or the quarantine.
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_gate import run_gate


def load_env() -> None:
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# ── Fixtures ────────────────────────────────────────────────────────────────

# (1) Multi-vector fabrication — both the deterministic layer (org phone number,
#     defunct entity) AND the judge (invented stat, fake quote) should object.
FABRICATED = {
    "slug": "selftest-fabricated", "title": "Test Bank Scam UK",
    "hero": "x", "description": "y",
    "sections": [
        ["What is this scam?",
         "Fraudsters impersonate your bank. Action Fraud reported that £89 million was "
         "lost to this exact scam in 2025, a 63% rise year on year. As Detective Inspector "
         "Sarah Hughes said, 'these gangs are more organised than ever.' If you are hit, "
         "call Lloyds directly on 0345 300 0000. Victims are often steered to move funds "
         "into crypto via a 'safe' exchange such as FTX."],
    ],
    "faq": [["Is it common?", "Yes — 1 in 3 UK adults were targeted in 2025 according to UK Finance."]],
}

# (2) SUBTLE fabrication — NO deterministic triggers (only the national Action
#     Fraud number, no banned entity). It can ONLY be caught by the LLM judge:
#     an invented attributed statistic, a fake quote, and an invented dated
#     regulatory event. This is the decisive test that the judge is working.
SUBTLE = {
    "slug": "selftest-subtle", "title": "Investment Recovery Scam UK",
    "hero": "x", "description": "y",
    "sections": [
        ["What is this scam?",
         "Recovery fraud targets people who have already lost money to investment scams. "
         "Action Fraud figures show reports rose exactly 47% in 2025, with an average loss "
         "of £12,400 per victim. The pattern was first identified after the FCA's crackdown "
         "of March 2025. As City of London Police spokesperson James Whitfield put it, "
         "'recovery fraud is the cruellest scam we investigate.' Report anything suspicious "
         "to Action Fraud on 0300 123 2040 and forward scam texts to 7726."],
    ],
    "faq": [["How do I report it?", "Report to Action Fraud on 0300 123 2040; forward scam texts to 7726."]],
}

# (3) Clean — directional language, no specific invented claims, only national
#     numbers, points readers to official sources. Must PASS (no over-blocking).
CLEAN = {
    "slug": "selftest-clean", "title": "Delivery Text Scam UK",
    "hero": "x", "description": "y",
    "sections": [
        ["What is this scam?",
         "Scammers send fake 'missed delivery' texts containing a link to a lookalike "
         "website that harvests your card details. Reports of delivery-themed smishing have "
         "grown rapidly across the UK. The message creates urgency with a small 'redelivery "
         "fee' so you act before checking. Never pay or enter card details via a link in a text."],
        ["What to do if you have already interacted",
         "Contact your bank straight away using the number on the back of your card. Report "
         "the scam to Action Fraud on 0300 123 2040 and forward the text to 7726. If you "
         "shared card details, ask your bank to block the card and watch for transactions."],
    ],
    "faq": [["Is every delivery text a scam?",
             "No — but treat any link asking for payment or card details as suspicious. Check "
             "your order directly via the courier's official website rather than the link."]],
}

# (4) ABSOLUTE — the class that leaked into the 2026-06-19 sextortion guide:
#     an unconditional "no footage exists" guarantee plus an invented
#     illustrative figure. The deterministic absolute check MUST block the
#     guarantee (no API needed); the tightened judge should also object to the
#     made-up rate. The hedged sentence must NOT trip the absolute check.
ABSOLUTE = {
    "slug": "selftest-absolute", "title": "Sextortion Email Scam UK",
    "hero": "x", "description": "y",
    "sections": [
        ["What is this scam?",
         "Sextortion emails claim a hacker filmed you via your webcam. In reality no footage "
         "exists — the scammer is bluffing. They send the same email to 100,000 people, and "
         "even if only 0.1% pay, they profit. If your webcam is intact, you are completely safe."],
        ["What to do",
         "Do not pay. It is extremely unlikely that any footage exists. Report the email to "
         "Action Fraud on 0300 123 2040 and forward scam texts to 7726."],
    ],
    "faq": [["Do they have a video of me?",
             "Almost certainly not — these are mass-mailed bluffs."]],
}

EXPECT = [
    ("fabricated (multi-vector) is BLOCKED",            "FABRICATED", lambda r: not r.passed),
    ("subtle fabrication is BLOCKED",                   "SUBTLE",     lambda r: not r.passed),
    ("...and the LLM JUDGE is what caught the subtle one",
     "SUBTLE", lambda r: any(i["check"] == "judge" and i["severity"] == "block" for i in r.issues)),
    ("absolute guarantee is BLOCKED",                   "ABSOLUTE",   lambda r: not r.passed),
    ("...and the DETERMINISTIC absolute check caught it (no API needed)",
     "ABSOLUTE", lambda r: any(i["check"] == "absolute" and i["severity"] == "block" for i in r.issues)),
    ("clean guide PASSES (no over-blocking)",           "CLEAN",      lambda r: r.passed),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Live self-test of the content accuracy gate")
    ap.add_argument("--model", default="claude-haiku-4-5-20251001")
    args = ap.parse_args()

    load_env()
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set (env or .env). Cannot run the live judge.",
              file=sys.stderr)
        return 2

    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    print(f"Running gate self-test with model: {args.model}\n")
    results = {}
    for name, post in [("FABRICATED", FABRICATED), ("SUBTLE", SUBTLE),
                       ("ABSOLUTE", ABSOLUTE), ("CLEAN", CLEAN)]:
        results[name] = run_gate(post, client=client, model=args.model, use_llm=True)

    for name in ("FABRICATED", "SUBTLE", "ABSOLUTE", "CLEAN"):
        r = results[name]
        print(f"── {name}: {r.summary()}")
        for i in r.issues:
            print(f"     [{i['severity']:5}] {i['check']}: {i['detail'][:100]}")
        print()

    ok = True
    print("Checks:")
    for desc, sample, predicate in EXPECT:
        passed = predicate(results[sample])
        ok = ok and passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {desc}")

    print("\n" + ("✅ GATE SELF-TEST PASSED — the judge is working. Safe to proceed to the re-enable step."
                  if ok else
                  "❌ GATE SELF-TEST FAILED — do NOT re-enable the crons; investigate content_gate.py."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
