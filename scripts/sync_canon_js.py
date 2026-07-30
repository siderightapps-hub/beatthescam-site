#!/usr/bin/env python3
"""
sync_canon_js.py — bridge content/sources.json into the Netlify Functions.

`content/sources.json` is the single source of truth for every reporting route,
but the scam checker is JavaScript and cannot import the Python canon module.
Until now it carried its own hand-typed copy of the Report Fraud and Police
Scotland links and of the nation-scoping rules in its system prompt, so a canon
change reached the site, the gate and the generator but silently left the
checker behind (operator review, 2026-07-29, `hubs-v10-c.md` §2).

This script renders the canon into a committed, generated JavaScript module:

    python3 scripts/sync_canon_js.py           # rewrite the module
    python3 scripts/sync_canon_js.py --check   # exit 1 if it is stale

`--check` runs in the offline self-test, so a canon edit that is not propagated
fails a committed test rather than shipping a checker that disagrees with the
rest of the site.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canon as canon_mod

TARGET = canon_mod.ROOT / "netlify" / "functions" / "lib" / "canon-routes.js"

HEADER = """// GENERATED FILE — DO NOT EDIT BY HAND.
//
// Rendered from content/sources.json by scripts/sync_canon_js.py. The canon is
// the single source of truth for every reporting route on this site; this
// module is how the Netlify Functions read it. Edit content/sources.json and
// re-run the script. `scripts/sync_canon_js.py --check` runs in the offline
// self-test, so a stale copy fails CI.
"""


def render(canon: dict) -> str:
    rf = canon_mod.route(canon, "action-fraud")
    ps = canon_mod.route(canon, "police-scotland")
    ncsc = canon_mod.route(canon, "ncsc-sers")
    sms = canon_mod.route(canon, "report-spam-sms")

    report_fraud = {"url": rf["report_url"], "name": f"{canon_mod.brand(rf)} — {rf['nation']}"}
    police_scotland = {
        "url": ps["report_url"],
        "name": f"{canon_mod.brand(ps)} on {ps['phone']} — {ps['nation']}",
    }
    example_links = [
        report_fraud,
        police_scotland,
        {"url": "https://www.ncsc.gov.uk/collection/phishing-scams/report-scam-text-messages",
         "name": f"Forward to {sms['sms']} (SMS spam)"},
    ]

    # The prompt rules the checker's SYSTEM string embeds. Same facts as the
    # generator's `render_prompt_routes()`, phrased for a link-list response.
    rules = [
        (f"Police fraud reporting is NATION-SPECIFIC and both routes must be offered together. "
         f"\"{canon_mod.brand(rf)}\" ({rf['report_url']}, {rf['phone']}) covers {rf['nation']} ONLY. "
         f"A reader in {ps['nation']}, or reporting a crime that happened there, uses "
         f"{canon_mod.brand(ps)} on {ps['phone']} ({ps['report_url']}). Never present "
         f"{canon_mod.brand(rf)} as the UK-wide route, and never give it without the Scottish "
         f"alternative in the same list."),
        (f"{canon_mod.brand(rf)} replaced Action Fraud in December 2025 — never call it "
         f"\"Action Fraud\" except as a parenthetical former name, and always link "
         f"{rf['report_url']}, never actionfraud.police.uk."),
        ("Consumer advice is nation-specific too: "
         + canon_mod.consumer_advice_clause(canon, phones=False)
         + f". Never present {canon_mod.brand(canon_mod.route(canon, 'citizens-advice'))} as a "
           f"UK-wide helpline."),
    ]

    from urllib.parse import urlparse
    onpage = [r for r in canon["official_routes"] if r.get("on_page") and r.get("report_url")]
    onpage_urls = sorted(r["report_url"] for r in onpage)
    required_hosts = sorted({(urlparse(u).hostname or "").lower() for u in onpage_urls})

    def js(value) -> str:
        return json.dumps(value, ensure_ascii=False, indent=2)

    return (
        HEADER
        + "\n"
        + f"const REPORT_FRAUD_LINK = {js(report_fraud)};\n\n"
        + f"const POLICE_SCOTLAND_LINK = {js(police_scotland)};\n\n"
        + "// Hosts that canonicalise to each of the pair, so a model-emitted variant\n"
        + "// (actionfraud.police.uk, a bare host, a deep link) resolves to the approved label.\n"
        + f"const REPORT_FRAUD_HOSTS = {js(['actionfraud.police.uk', 'reportfraud.police.uk'])};\n\n"
        + f"const POLICE_SCOTLAND_HOSTS = {js(['scotland.police.uk'])};\n\n"
        + "// Every host serving an on_page canon route. check-scam.js unions these into\n"
        + "// its security allow-list, so a required reporting route can never be filtered\n"
        + "// out of a checker result — www.advice.scot was, silently, until 2026-07-30.\n"
        + f"const CANON_REQUIRED_HOSTS = {js(required_hosts)};\n\n"
        + "// Every on_page canon report_url, so a test can assert each one survives.\n"
        + f"const CANON_ONPAGE_URLS = {js(onpage_urls)};\n\n"
        + f"const NCSC_REPORT_EMAIL = {js(ncsc['email'])};\n\n"
        + f"const SMS_SHORTCODE = {js(sms['sms'])};\n\n"
        + f"const EXAMPLE_REPORTING_LINKS = {js(example_links)};\n\n"
        + f"const PROMPT_ROUTE_RULES = {js(rules)};\n\n"
        + "module.exports = {\n"
        + "  REPORT_FRAUD_LINK,\n  POLICE_SCOTLAND_LINK,\n  REPORT_FRAUD_HOSTS,\n"
        + "  POLICE_SCOTLAND_HOSTS,\n  NCSC_REPORT_EMAIL,\n  SMS_SHORTCODE,\n"
        + "  EXAMPLE_REPORTING_LINKS,\n  PROMPT_ROUTE_RULES,\n  CANON_REQUIRED_HOSTS,\n"
        + "  CANON_ONPAGE_URLS,\n};\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Render content/sources.json into the functions' canon module")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the committed module is stale instead of rewriting it")
    args = ap.parse_args()

    try:
        canon = canon_mod.load_canon()
    except canon_mod.CanonError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    want = render(canon)
    have = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""

    if args.check:
        if want == have:
            print(f"OK  {TARGET.relative_to(canon_mod.ROOT)} is in sync with content/sources.json")
            return 0
        print(f"STALE  {TARGET.relative_to(canon_mod.ROOT)} does not match content/sources.json.\n"
              f"       Run: python3 scripts/sync_canon_js.py", file=sys.stderr)
        return 1

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(want, encoding="utf-8")
    print(f"{'unchanged' if want == have else 'wrote'}  {TARGET.relative_to(canon_mod.ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
