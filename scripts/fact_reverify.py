#!/usr/bin/env python3
"""
fact_reverify.py — quarterly re-verification of the LIVE corpus against the
current state of the world.

content_gate.py only runs ONCE, at generation time. It catches fabrication and
canon violations in a draft, but has no mechanism to notice that a guide's
facts have gone stale since publish — a compensation cap changes, a mailbox
gets retired, a deadline gets extended, a court date turns out to have been
mis-stated. The 2026-07-10 manual full-corpus audit (16 parallel web-search
agents reviewing all 181 guides) found exactly that class of error in guides
that had been live for months. This script automates that audit:

  Pass A (deterministic, no API cost) — re-runs content_gate.run_gate
  (use_llm=False) across EVERY guide regardless of publish date, surfacing
  canon/structural issues the weekly digest's 7-day window would otherwise
  never resurface (e.g. an unresolved non-canon reporting email flagged
  months ago and never revisited).

  Pass B (LLM + live web search) — one Claude call per guide, with the
  web_search server tool enabled, asking it to verify every checkable claim
  (dates, figures, named orgs' contact routes, legal citations, "X was
  retired/rebranded") against current primary UK sources. Only claims with
  clear primary-source evidence of drift are reported — an unverifiable claim
  is left alone, never guessed at (mirrors the sister publication's
  tuningdigital/.github/scripts/fact-reverify.mjs "research, don't publish"
  contract).

Both passes feed one Markdown report at
content/fact-reverify-reports/<YYYY>-Q<N>.md. This script NEVER edits
posts.json, content/manifests/, or dist/ — a human reviews the report and
applies any fixes by hand (see CLAUDE.md's "Operator review workflow").

    python3 scripts/fact_reverify.py                       # full corpus
    python3 scripts/fact_reverify.py --limit 3              # cheap smoke test
    ANTHROPIC_API_KEY=...  python3 scripts/fact_reverify.py --model claude-sonnet-5

Exit 0 ONLY on a run where every guide was actually checked (drift found or
not). Exit 1 if any guide could not be checked after retries, and 2 if the run
could not start at all (e.g. no API key). "0 drifted" from a run where every
call failed is the one outcome this script must never report as success —
that defect shipped and was caught by the 2026-07-25 audit. Use
--allow-errors only for deliberately partial local runs; CI must not set it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content_gate import run_gate, _post_text, SEVERITY_BLOCK, SEVERITY_FLAG


def load_env() -> None:
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def current_quarter(today: Optional[date] = None) -> str:
    d = today or date.today()
    q = (d.month - 1) // 3 + 1
    return f"{d.year}-Q{q}"


# ─── PASS B: LLM + WEB SEARCH ────────────────────────────────────────────────

REVERIFY_SYSTEM = """You are a fact-checking editor doing a QUARTERLY re-verification pass on a \
LIVE guide on a UK consumer-protection site (Beat The Scam). This guide was published in the past \
and may now contain STALE facts: a compensation cap that changed, a mailbox that was retired, a \
deadline that was extended, a rebrand, a wrong court/legislation date. Today's date is {today}.

You have web search. Use it to verify checkable claims against CURRENT primary UK sources \
(gov.uk, the regulator's own site, the named organisation's own site) — not secondary summaries \
or forum posts.

ALREADY-CANON facts you do NOT need to re-derive or flag (these are correct and already enforced \
elsewhere on the site) — only flag a DEVIATION from these, never re-report them as a "finding":
- Current reporting route name is "Report Fraud" (reportfraud.police.uk, 0300 123 2040); \
"Action Fraud" is its former name (rebranded Dec 2025).
- FCA's checker is the "FCA Firm Checker" (register.fca.org.uk); "ScamSmart" is retired branding.
- UK credit reference agencies: Experian, Equifax and TransUnion are the three MAIN agencies, and
  MoneyHelper also lists Crediva as offering a free statutory report. Treat "the three CRAs",
  "all three" or "the other two" written as EXHAUSTIVE as drift. ClearScore is a free app and
  CallCredit is the obsolete name for TransUnion — neither is a current agency.
- The National Fraud Database is a Cifas service (Cifas Protective Registration) — not routed via \
Report Fraud or Citizens Advice. There is no UK "credit freeze"; the UK mechanism is Cifas \
Protective Registration.
- APP fraud reimbursement has been MANDATORY under PSR rules since 7 Oct 2024 (not the older \
voluntary CRM code).
- HMRC does run genuine SMS/email campaigns with gov.uk links — a blanket "HMRC never texts/\
emails you" is itself wrong, not something to confirm as correct.

Check every OTHER checkable, specific claim in the guide: dates and deadlines, statistics and \
compensation/reimbursement figures, a named organisation's reporting email/phone/URL, legal or \
regulatory citations, court case outcomes and dates, "X was retired/renamed/superseded" claims.
For each one, search for its current primary-source status.

Report a finding ONLY when you found clear primary-source evidence the guide's claim is now \
wrong, stale, or internally contradictory. If you cannot find a clear primary source either way, \
do NOT report it — an unverified claim is left alone, never guessed at. Do not report style, \
phrasing, or anything already covered by the ALREADY-CANON list above.

Respond with ONLY this JSON, no other text:
{{"findings":[{{"claim_text":"<exact short phrase quoted verbatim from the guide>","issue":"<what is wrong, one sentence>","correct_value":"<the current correct fact>","source_url":"<primary source URL>","confidence":"high"|"medium"}}]}}
Empty "findings" array if nothing in the guide is confirmed stale."""


def build_reverify_prompt(post: Dict) -> str:
    body = _post_text(post)
    return f"Title: {post.get('title', '')}\n\nRe-verify this LIVE guide:\n\n{body}\n\nReturn the JSON verdict."


_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)


def extract_findings_json(raw: str) -> Dict:
    """Pull the findings object out of a model response.

    The model is asked for bare JSON, but in practice it also returns
    prose-then-fenced-JSON and bare-JSON-with-trailing-commentary. Stripping a
    fence only when it wraps the WHOLE response (the original behaviour) turned
    every one of those into a json.loads failure, i.e. a silently unchecked
    guide. Order matters: try the whole string, then a fenced block, then the
    outermost brace-balanced object.
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty response")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = _FENCED_JSON_RE.search(raw)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = raw.find("{")
    if start != -1:
        depth, in_str, esc = 0, False, False
        for i, ch in enumerate(raw[start:], start):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(raw[start:i + 1])
    raise ValueError(f"no JSON object found in response: {raw[:200]!r}")


def reverify_post_llm(post: Dict, client, model: str, today: str,
                       attempts: int = 3, sleep_fn=time.sleep) -> List[Dict]:
    """Pass B: one web-search-enabled call per guide, retried on transient
    failure. Never raises — after the final attempt a failure is returned as a
    single confidence='error' dict and the caller moves on to the next guide,
    but the caller MUST treat a non-empty error list as a failed run (see
    main()): a quarterly report that says '0 drifted' because every call died
    is worse than no report at all.

    No sampling parameters are sent: the default model rejects `temperature`
    alongside the web-search tool, which failed every call in the 2026-07-25
    audit.
    """
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=2000,
                system=REVERIFY_SYSTEM.format(today=today),
                messages=[{"role": "user", "content": build_reverify_prompt(post)}],
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            )
            raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
            data = extract_findings_json(raw)
            findings = list(data.get("findings") or [])
            for f in findings:
                f.setdefault("confidence", "medium")
            return findings
        except Exception as e:  # noqa: BLE001 — must never abort the whole run
            last_err = e
            if attempt < attempts:
                sleep_fn(min(2 ** attempt, 30))
    return [{"claim_text": None,
             "issue": f"re-verification failed after {attempts} attempts: "
                      f"{type(last_err).__name__}: {last_err}",
             "correct_value": None, "source_url": None, "confidence": "error"}]


def find_affected_slugs(posts: List[Dict], claim_text: Optional[str], skip_slug: str) -> List[str]:
    """Grep the rest of the corpus for the same literal phrase a finding was
    anchored on, so one drifted fact surfaces every guide that repeats it —
    not just the one guide the LLM happened to check."""
    if not claim_text:
        return []
    needle = claim_text.strip().lower()
    if len(needle) < 6:
        return []
    hits = []
    for p in posts:
        if p.get("slug") == skip_slug:
            continue
        if needle in _post_text(p).lower():
            hits.append(p.get("slug"))
    return hits


# ─── REPORT ───────────────────────────────────────────────────────────────────

def _cell(s: Optional[str], width: int = 100) -> str:
    """Markdown-table-safe cell: escape pipes, collapse whitespace, truncate."""
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    s = s.replace("|", "\\|")
    return (s[: width - 1] + "…") if len(s) > width else s


def write_report(quarter: str, out_dir: str, posts: List[Dict],
                  det_findings: List[Tuple[str, Dict]],
                  llm_findings: List[Tuple[str, Dict]],
                  cross_refs: Dict[Tuple[str, str], List[str]],
                  errors: List[Tuple[str, str]], today: str, model: str) -> str:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{quarter}.md"

    lines: List[str] = []
    lines.append(f"# Fact re-verification report — {quarter}")
    lines.append("")
    lines.append(f"Generated {today} · model `{model}` · {len(posts)} guides examined.")
    lines.append("")
    lines.append("**No facts were edited.** This report only records what the deterministic gate "
                  "and a web-search-enabled Claude pass found — apply any corrections by hand, then "
                  "merge this PR (or close it to discard). See the reviewer checklist at the bottom.")
    lines.append("")

    block_det = [f for f in det_findings if f[1].get("severity") == SEVERITY_BLOCK]
    flag_det = [f for f in det_findings if f[1].get("severity") == SEVERITY_FLAG]

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Deterministic re-scan: {len(block_det)} BLOCK-tier, {len(flag_det)} FLAG-tier "
                  f"(across the whole corpus, not just guides published this week)")
    lines.append(f"- Web-verified drift (Pass B): {len(llm_findings)} finding(s)")
    if errors:
        lines.append(f"- Guides that could not be checked this run: {len(errors)}")
    lines.append("")

    if block_det:
        lines.append("## A1. Deterministic BLOCK-tier flags — should not exist, investigate first")
        lines.append("")
        lines.append("| Slug | Check | Claim |")
        lines.append("|---|---|---|")
        for slug, i in block_det:
            lines.append(f"| {slug} | {i.get('check')} | {_cell(i.get('detail'))} |")
        lines.append("")

    if flag_det:
        lines.append("## A2. Deterministic FLAG-tier issues (corpus-wide, any age)")
        lines.append("")
        lines.append("| Slug | Check | Claim |")
        lines.append("|---|---|---|")
        for slug, i in flag_det:
            lines.append(f"| {slug} | {i.get('check')} | {_cell(i.get('detail'))} |")
        lines.append("")

    real_llm = [(s, f) for s, f in llm_findings if f.get("confidence") != "error"]
    if real_llm:
        lines.append("## B. Web-verified drift")
        lines.append("")
        lines.append("| Slug | Claim in guide | Issue | Correct value | Source | Confidence |")
        lines.append("|---|---|---|---|---|---|")
        for slug, f in real_llm:
            lines.append(f"| {slug} | {_cell(f.get('claim_text'))} | {_cell(f.get('issue'))} | "
                          f"{_cell(f.get('correct_value'))} | {_cell(f.get('source_url'), 60)} | "
                          f"{f.get('confidence', '')} |")
        lines.append("")

        any_cross = False
        for (slug, claim_text), affected in cross_refs.items():
            if affected:
                if not any_cross:
                    lines.append("### Other guides repeating the same drifted claim")
                    lines.append("")
                    any_cross = True
                lines.append(f"- **{slug}**'s finding on \"{_cell(claim_text, 60)}\" also appears in: "
                              f"{', '.join(affected)}")
        if any_cross:
            lines.append("")
    else:
        lines.append("## B. Web-verified drift")
        lines.append("")
        lines.append("No confirmed drift found this pass.")
        lines.append("")

    if errors:
        lines.append("## Guides not checked this run")
        lines.append("")
        for slug, msg in errors:
            lines.append(f"- {slug}: {msg}")
        lines.append("")

    lines.append("## Reviewer checklist")
    lines.append("")
    lines.append("- [ ] For each Section B finding, confirm the correct value against its cited source")
    lines.append("- [ ] Edit the guide's `sections`/`faq` in `content/posts.json` by hand — never the "
                  "legacy `content` field (it is never rendered)")
    lines.append("- [ ] Never use `[text](/guides/slug/)` bracket-links or `**bold**` in article prose "
                  "— `build.py` has no Markdown renderer for either (see CLAUDE.md invariant 6)")
    lines.append("- [ ] For any Section A1/A2 item, add the verified route to `content/sources.json` "
                  "or fix the prose per the check's `detail`")
    lines.append("- [ ] Run `python3 scripts/build.py` and grep `dist/` for `](`, `**`, and `…` before committing")
    lines.append("- [ ] If a reporting route or phone number changed, update `content/sources.json` "
                  "(canon) so `content_gate.py` and `build.py`'s on-page reporting block stay in sync")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Quarterly re-verification of the live corpus")
    ap.add_argument("--posts", default="content/posts.json")
    ap.add_argument("--out-dir", default="content/fact-reverify-reports")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--limit", type=int, default=None,
                     help="only process the first N guides (cheap smoke test)")
    ap.add_argument("--quarter", default=None, help="override quarter label, e.g. 2026-Q3")
    ap.add_argument("--attempts", type=int, default=3,
                     help="attempts per guide before recording it as unchecked (default 3)")
    ap.add_argument("--allow-errors", action="store_true",
                     help="exit 0 even if some guides could not be checked. Local partial "
                          "runs only — CI must never set this, or a fully failed run reports clean.")
    args = ap.parse_args()

    load_env()
    posts_path = Path(args.posts)
    posts = json.loads(posts_path.read_text(encoding="utf-8"))
    if args.limit:
        posts = posts[: args.limit]

    today_str = date.today().isoformat()
    quarter = args.quarter or current_quarter()

    # Pass A — deterministic re-scan, every guide, regardless of publish date.
    det_findings: List[Tuple[str, Dict]] = []
    for p in posts:
        # is_draft=False: these are LIVE records, not drafts. A record that has
        # been consolidated legitimately carries `consolidated_into`, which is a
        # BLOCK only when a DRAFT asserts it about itself (operator review,
        # 2026-07-30 — this caller reported a false consolidation_evasion BLOCK
        # on the archived Hermes record).
        result = run_gate(p, use_llm=False, is_draft=False)
        for i in result.issues:
            det_findings.append((p.get("slug", "?"), i))

    # Pass B — LLM + web search, per guide.
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set (env or .env). Cannot run Pass B.", file=sys.stderr)
        return 2
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    llm_findings: List[Tuple[str, Dict]] = []
    errors: List[Tuple[str, str]] = []
    for idx, p in enumerate(posts, 1):
        slug = p.get("slug", "?")
        print(f"[{idx}/{len(posts)}] re-verifying {slug}...", file=sys.stderr)
        for f in reverify_post_llm(p, client, args.model, today_str, attempts=args.attempts):
            if f.get("confidence") == "error":
                errors.append((slug, f.get("issue", "unknown error")))
            else:
                llm_findings.append((slug, f))

    # Cross-reference: which OTHER guides repeat a drifted claim?
    cross_refs: Dict[Tuple[str, str], List[str]] = {}
    for slug, f in llm_findings:
        claim_text = f.get("claim_text")
        affected = find_affected_slugs(posts, claim_text, slug)
        if affected:
            cross_refs[(slug, claim_text)] = affected

    report_path = write_report(quarter, args.out_dir, posts, det_findings, llm_findings,
                                cross_refs, errors, today_str, args.model)

    real_drift = len([f for f in llm_findings if f[1].get("confidence") != "error"])
    checked = len(posts) - len({slug for slug, _ in errors})
    print(f"\nREPORT_PATH={report_path}")
    print(f"DRIFT_COUNT={real_drift}")
    print(f"EXAMINED={len(posts)}")
    print(f"CHECKED={checked}")
    print(f"ERROR_COUNT={len(errors)}")
    print(f"QUARTER={quarter}")

    # Fail closed. DRIFT_COUNT only counts guides the model actually reported
    # on, so an all-failed run would otherwise print DRIFT_COUNT=0 and let the
    # workflow open a "0 drifted" PR that means the opposite of what it says.
    if errors and not args.allow_errors:
        print(f"\nERROR: {len(errors)} of {len(posts)} guides could not be re-verified "
              f"after retries — refusing to report this run as clean. "
              f"See the Errors section of {report_path}.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
