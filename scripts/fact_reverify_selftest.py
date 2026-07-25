#!/usr/bin/env python3
"""
fact_reverify_selftest.py — offline self-test for the quarterly fact-checker.

Covers the four failure modes that let the 2026-07-25 audit find a workflow
which could report DRIFT_COUNT=0 while every guide silently failed to be
checked:

  1. prose followed by fenced JSON      (the parser used to raise)
  2. malformed / non-JSON response      (must retry, then record an error)
  3. transient failure then success     (must retry and recover)
  4. every call failing                 (must NOT look like a clean run)

No API key and no network are needed — the Anthropic client is stubbed.

    python3 scripts/fact_reverify_selftest.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fact_reverify as fr

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


class _Block:
    type = "text"

    def __init__(self, text: str):
        self.text = text


class _Resp:
    def __init__(self, text: str):
        self.content = [_Block(text)]


class StubClient:
    """Replays a scripted sequence of responses/exceptions per create() call."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        item = self._script[min(self.calls - 1, len(self._script) - 1)]
        if isinstance(item, Exception):
            raise item
        return _Resp(item)


POST = {"slug": "test-guide", "title": "Test", "sections": [["H", "Body text."]], "faq": []}
FINDING_JSON = json.dumps({"findings": [
    {"claim_text": "the fee is £100", "issue": "fee changed", "correct_value": "£120",
     "source_url": "https://www.gov.uk/example", "confidence": "high"}]})


def run() -> int:
    # ── extract_findings_json ────────────────────────────────────────────────
    check("bare JSON parses", fr.extract_findings_json(FINDING_JSON)["findings"][0]["correct_value"] == "£120")

    prose_fenced = f"I checked the sources.\n\n```json\n{FINDING_JSON}\n```"
    try:
        got = fr.extract_findings_json(prose_fenced)
        check("prose + fenced JSON parses", got["findings"][0]["correct_value"] == "£120")
    except Exception as e:  # noqa: BLE001
        check("prose + fenced JSON parses", False, f"raised {type(e).__name__}: {e}")

    try:
        got = fr.extract_findings_json(f"Here you go:\n{FINDING_JSON}\nHope that helps.")
        check("JSON with trailing prose parses", got["findings"][0]["correct_value"] == "£120")
    except Exception as e:  # noqa: BLE001
        check("JSON with trailing prose parses", False, f"raised {type(e).__name__}: {e}")

    check("nested braces survive brace-matching",
          fr.extract_findings_json('prefix {"findings": [{"a": {"b": 1}}]} suffix')["findings"][0]["a"]["b"] == 1)

    for bad, label in [("not json at all", "prose-only"), ("", "empty"), ('{"findings": [', "truncated")]:
        try:
            fr.extract_findings_json(bad)
            check(f"malformed response rejected ({label})", False, "no exception raised")
        except Exception:  # noqa: BLE001
            check(f"malformed response rejected ({label})", True)

    # ── reverify_post_llm retry behaviour ────────────────────────────────────
    noop_sleep = lambda _s: None

    c = StubClient([RuntimeError("overloaded"), FINDING_JSON])
    out = fr.reverify_post_llm(POST, c, "m", "2026-07-25", attempts=3, sleep_fn=noop_sleep)
    check("transient failure then success recovers",
          c.calls == 2 and out and out[0].get("confidence") == "high", f"calls={c.calls} out={out}")

    c = StubClient([RuntimeError("boom")])
    out = fr.reverify_post_llm(POST, c, "m", "2026-07-25", attempts=3, sleep_fn=noop_sleep)
    check("persistent failure exhausts attempts then errors",
          c.calls == 3 and len(out) == 1 and out[0]["confidence"] == "error", f"calls={c.calls}")

    c = StubClient(["still not json"])
    out = fr.reverify_post_llm(POST, c, "m", "2026-07-25", attempts=2, sleep_fn=noop_sleep)
    check("unparseable response recorded as error",
          out[0]["confidence"] == "error" and c.calls == 2, f"out={out}")

    c = StubClient([prose_fenced])
    out = fr.reverify_post_llm(POST, c, "m", "2026-07-25", attempts=2, sleep_fn=noop_sleep)
    check("prose+fence response yields a finding, not an error",
          c.calls == 1 and out[0].get("confidence") == "high", f"out={out}")

    # ── no unsupported sampling params reach the API ─────────────────────────
    captured = {}

    class ParamSpy(StubClient):
        def create(self, **kwargs):
            captured.update(kwargs)
            return super().create(**kwargs)

    fr.reverify_post_llm(POST, ParamSpy([FINDING_JSON]), "m", "2026-07-25", sleep_fn=noop_sleep)
    check("no temperature sent (model rejects it)", "temperature" not in captured,
          f"sent: {sorted(captured)}")
    check("web_search tool still enabled",
          any(t.get("name") == "web_search" for t in captured.get("tools", [])))

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All fact_reverify self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
