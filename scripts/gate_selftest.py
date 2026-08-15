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
    "quick_answer": (
        'Treat any call claiming to be from your bank as unverified until you hang up and dial the number printed on your own card. Genuine staff do not rush you into moving money to a new account.'
    ),
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
    "quick_answer": (
        'Recovery fraud targets people who have already lost money, by promising to get it back for an upfront fee. Treat any unsolicited offer to recover your losses as a scam and pay nothing in advance.'
    ),
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

_CLEAN_RECOVERY = (
    "Contact your bank straight away using the number on the back of your card. Report "
    "the scam to Report Fraud on 0300 123 2040 if you are in England, Wales or Northern "
    "Ireland, or to Police Scotland on 101 in Scotland. Forward the text to 7726. If you "
    "shared card details, ask your bank to block the card and watch for transactions."
)
_FLAGS_REPORT = (
    "Report it by emailing abuse@madeup-reports.gov.uk, or to Action Fraud "
    "on 0300 123 2040 in England, Wales and Northern Ireland, or to Police "
    "Scotland on 101 in Scotland."
)

# (3) Clean — directional language, no specific invented claims, only national
#     numbers, points readers to official sources. Must PASS (no over-blocking).
#     Says "Report Fraud", not "Action Fraud": the service was rebranded in Dec
#     2025 and the judge correctly treats the retired name as an identity error.
#     This fixture still said "Action Fraud", which is a second reason it had
#     been failing the no-over-blocking assertion on main — found 2026-08-08.
CLEAN = {
    "slug": "selftest-clean", "title": "Delivery Text Scam UK",
    "quick_answer": (
        "A missed-delivery text asking for a small redelivery fee is a common UK smishing pattern. Do not pay through the message. Check the order in the courier's own app, reaching it yourself rather than through the text."
    ),
    "hero": "x", "description": "y",
    "sections": [
        ["What is this scam?",
         "Scammers send fake 'missed delivery' texts containing a link to a lookalike "
         "website that harvests your card details. Reports of delivery-themed smishing have "
         "grown rapidly across the UK. The message creates urgency with a small 'redelivery "
         "fee' so you act before checking. Never pay or enter card details via a link in a text."],
        # The Scottish route is REQUIRED here, not decoration: naming Report Fraud
        # as if it covered the whole UK is block-tier (check_scotland_routing,
        # added by the 2026-07-30 accuracy release). This fixture predated that
        # rule and was silently failing the "no over-blocking" assertion on main
        # ever since — found 2026-08-08.
        ["What to do if you have already interacted", _CLEAN_RECOVERY],
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
    "quick_answer": (
        'Sextortion emails demand payment over a claimed webcam recording. Do not reply and do not pay. Keep the email as evidence and change the password on any account it names.'
    ),
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

# (5) FLAGS — review-tier (NOT block) classes that feed the claim manifest +
#     weekly digest: a legislation claim, a dated regulatory event, and a
#     non-canon official reporting email. These must be RECORDED (so a human can
#     verify them) but must NOT block publication.
FLAGS = {
    "slug": "selftest-flags", "title": "Consumer Rights Refund Scam UK",
    "quick_answer": (
        'A caller offering to process a refund you did not request is usually after your card details. Check any refund claim directly with the company, using contact details you have found for yourself.'
    ),
    "hero": "x", "description": "y",
    "sections": [
        ["What is this scam?",
         "Under the Consumer Rights Act 2015 you are legally entitled to a refund. "
         "The FCA banned this firm from trading in 2024 after an investigation."],
        # Scottish route present so the FLAG-tier classes under test are isolated
        # from the block-tier scotland_routing rule (see the CLEAN note above).
        ["How to report", _FLAGS_REPORT],
        ["Over-broad channel claims",
         "Banks never send links in text messages. Forward texts to 7726 because it works on "
         "all UK mobile networks. Forward RCS and iMessage chats to 7726 too. UK banks must "
         "reimburse most APP fraud victims within five days."],
    ],
    "faq": [],
}

# (6) JUDGE-ONLY classes from the 2026-08-08 operator review. Neither is
#     reachable by a regex: PLATFORM_VERIFY asserts how a third party's badge and
#     support handle work (product behaviour that changes without notice), and
#     APP_OMISSION is an OMISSION — a pattern detecting it by absence would fire
#     on every guide that legitimately says nothing about payments.
#
#     The judge already RAN on the draft these came from — the manifest records
#     claude-haiku-4-5-20251001 — and recorded zero claims, so this fixture is
#     the regression test for instructions added after a check executed and
#     missed. Deliberately carries no deterministic triggers: only the national
#     Report Fraud number and canon routes, so anything caught here is the judge.
#
#     Expected FLAG, not BLOCK. Both are editorial accuracy problems for a human
#     reviewer, and the judge's verdicts are known to vary run to run — blocking
#     the pipeline on a model's opinion about these would be the wrong trade.
# Bodies are bound to names rather than written inline. Implicitly concatenated
# string literals sitting directly inside a list literal are what
# py/implicit-string-concatenation-in-list reports ("maybe missing a comma?"),
# and a fixture list of [heading, body] pairs is precisely that shape.
_PV_VERIFY = (
    "The official support account is verified with a blue badge and has the exact username "
    "'support'. Any variation — with hyphens, underscores, or numbers — is a scam. If you "
    "receive a message claiming to be from support, compare the username character by "
    "character against that one and trust the badge if it matches."
)
_PV_REPORT = (
    "Report the scam to Report Fraud on 0300 123 2040 in England, Wales and Northern "
    "Ireland, or to Police Scotland on 101 in Scotland."
)

PLATFORM_VERIFY = {
    "slug": "selftest-platform-verify", "title": "Social Platform Support Scam UK",
    "quick_answer": (
        "Fake support accounts copy the real one's name and picture to intercept complaints. Approach support through the app's own help menu rather than replying to anyone who contacts you first."
    ),
    "hero": "x", "description": "y",
    "sections": [
        ["How to check whether support is genuine", _PV_VERIFY],
        ["Where to report it", _PV_REPORT],
    ],
    "faq": [["Can I trust the badge?",
             "Yes — a badge on the support account proves the account is authentic."]],
}

# (7) APP_OMISSION — finding 4 on its own, deliberately free of the absolute
#     language that makes PLATFORM_VERIFY block. Recovery advice that stops at
#     "may be able to recall" and never names the mandatory reimbursement right.
#     Everything else is correct: nation-scoped routes, no invented figures. So
#     the ONLY thing to object to is the omission, and it must be a FLAG — the
#     guide is publishable-with-review, not fabricated.
_APP_HOW = (
    "Criminals persuade you to move money to an account they control, usually by posing as "
    "someone you trust and creating time pressure. The transfer looks ordinary to your bank "
    "because you authorised it yourself, which is what makes this pattern so effective."
)
# The omission under test: stops at "recall", never names the reimbursement right.
_APP_RECOVERY = (
    "Contact your bank immediately using the number on the back of your card. They may be "
    "able to recall the payment if it has not yet been withdrawn from the receiving account. "
    "Report the scam to Report Fraud on 0300 123 2040 in England, Wales and Northern "
    "Ireland, or to Police Scotland on 101 in Scotland."
)
_APP_FAQ = (
    "Ask your bank as soon as you realise. The sooner you report it, the more likely the "
    "funds are still recoverable from the receiving account."
)

APP_OMISSION = {
    "slug": "selftest-app-omission", "title": "Bank Transfer Scam UK",
    "quick_answer": (
        'Someone posing as a trusted contact persuades you to transfer money to an account they control. Stop, verify the request through a channel you already trust, and contact your bank straight away if you have already sent it.'
    ),
    "hero": "x", "description": "y",
    "sections": [
        ["How the scam works", _APP_HOW],
        ["What to do if you have already sent money", _APP_RECOVERY],
    ],
    "faq": [["Will I get my money back?", _APP_FAQ]],
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
    ("legislation claim is RECORDED as a flag",         "FLAGS",
     lambda r: any(i["check"] == "legislation" for i in r.issues)),
    ("dated regulatory event is RECORDED as a flag",    "FLAGS",
     lambda r: any(i["check"] == "dated_event" for i in r.issues)),
    ("non-canon reporting email is RECORDED as a flag", "FLAGS",
     lambda r: any(i["check"] == "source" for i in r.issues)),
    ("bank-link absolute is RECORDED as a flag",         "FLAGS",
     lambda r: any(i["check"] == "bank_link_absolute" for i in r.issues)),
    ("7726 network scope is RECORDED as a flag",         "FLAGS",
     lambda r: any(i["check"] == "7726_scope" for i in r.issues)),
    ("7726 message-format scope is RECORDED as a flag",  "FLAGS",
     lambda r: any(i["check"] == "7726_format_scope" for i in r.issues)),
    # NB: app_reimbursement_scope is BLOCK-tier by design (an over-broad
    # reimbursement promise is dangerous, not merely imprecise). It is asserted
    # present, and excluded from the flag-tier regression guard below.
    ("APP reimbursement scope is RECORDED",              "FLAGS",
     lambda r: any(i["check"] == "app_reimbursement_scope" for i in r.issues)),
    # Regression guard: no DETERMINISTIC flag-tier class may ever emit a block —
    # a refactor promoting legislation/dated_event/source to block-tier would
    # otherwise still show a green self-test. The judge is excluded because it
    # may legitimately block this fixture's invented dated event.
    ("no deterministic flag class BLOCKS publication",  "FLAGS",
     lambda r: not any(i["severity"] == "block"
                       and i["check"] not in ("judge", "app_reimbursement_scope")
                       for i in r.issues)),
    # Judge-only classes (2026-08-08 operator review findings 1 and 4).
    ("the JUDGE objects to platform-verification claims",
     "PLATFORM_VERIFY", lambda r: any(i["check"] == "judge" for i in r.issues)),
    ("...and nothing DETERMINISTIC fires on it (proving it was the judge)",
     "PLATFORM_VERIFY", lambda r: not any(i["check"] != "judge" for i in r.issues)),
    ("the JUDGE objects to recovery advice omitting the APP right",
     "APP_OMISSION", lambda r: any(i["check"] == "judge" for i in r.issues)),
    ("...and nothing DETERMINISTIC fires on it (proving it was the judge)",
     "APP_OMISSION", lambda r: not any(i["check"] != "judge" for i in r.issues)),
    ("...as a FLAG, not a BLOCK — an omission is reviewable, not fabricated",
     "APP_OMISSION", lambda r: r.passed),
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
                       ("ABSOLUTE", ABSOLUTE), ("CLEAN", CLEAN), ("FLAGS", FLAGS),
                       ("PLATFORM_VERIFY", PLATFORM_VERIFY),
                       ("APP_OMISSION", APP_OMISSION)]:
        results[name] = run_gate(post, client=client, model=args.model, use_llm=True)

    for name in ("FABRICATED", "SUBTLE", "ABSOLUTE", "CLEAN", "FLAGS", "PLATFORM_VERIFY", "APP_OMISSION"):
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
