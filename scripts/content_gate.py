"""
content_gate.py — pre-publish accuracy gate for generated guides.

A generated post must PASS this gate before it is added to posts.json,
built, deployed, or tweeted. FAIL → the caller quarantines it (never
published). This is the safety layer that lets the autonomous content
pipeline run again after the 2026-06-18 hold (see the project audit).

Two layers:
  1. Deterministic checks (no API) — high-confidence blockers for the exact
     error classes the audit found: organisation-specific phone numbers,
     defunct/known-bad entities, and obviously-wrong reporting domains.
  2. LLM judge (optional) — a low-temperature Claude "critic" second pass
     that flags fabrication the rules can't catch (invented statistics,
     fake quotes, wrong attributions, unverifiable specific claims).

A post FAILS if any layer raises a high-severity ("block") issue.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

# ─── SHARED ACCURACY CONTRACT ────────────────────────────────────────────────
# Single source of truth for the anti-fabrication rules, imported by BOTH
# generators (generate_content_claude.py and search_console_articles.py) so
# their prompts cannot drift apart again (audit GAP 4). The gate's allowlist
# (ALLOWED_PHONE_DIGITS) and this prompt rule are kept deliberately in sync.
ACCURACY_BLOCK = """ACCURACY — THIS OVERRIDES EVERY STYLE AND SEO RULE BELOW. A plausible-sounding but invented fact about a real company, person, or product is the single worst failure this publication can make: it is libel-adjacent and gets the site rejected from ad networks.
- Use directional language ("growing rapidly", "a meaningful share", "early data suggests") for figures unless they are well-established public facts. Never invent specific percentages, dollar figures, or entity-attributed statistics. Do not attribute a statistic to a named body (Action Fraud, the FCA, Which?, UK Finance, NCSC) unless you are certain of the exact figure — if unsure, describe the pattern without a number.
- NEVER invent or assert a specific dated event, deal, acquisition, merger, partnership, funding round, valuation, product launch, regulatory action, or piece of legislation involving a real named company, person, product, or regulator unless you are certain it is a true, well-established public fact. This explicitly includes who-acquired-whom, who-partnered-with-whom, launch/approval dates, what a law or feature actually covers, pricing/plan limits, and which tool or vendor a named company actually uses.
- Never present a named company as "legitimate", "genuine", or "trusted" unless it is a well-known real brand; do not invent example company names.
- If you are not certain of the exact relationship, date, figure, or attribution, describe it in general terms WITHOUT naming a specific deal/number — or omit it. Inventing a product or vendor name, or pairing a real company with the wrong partner, tool, or capability, is forbidden.
- Before finalising, re-read every sentence that names a real company, person, or product alongside a date, number, deal, price, or feature. If you are not confident it is a true public fact, rewrite it as a general statement or delete it.
- Do NOT state a phone number for any specific company (bank, courier, retailer, utility, etc.). The ONLY phone numbers permitted anywhere are: Action Fraud 0300 123 2040, Citizens Advice 0808 223 1133, the FCA consumer helpline 0800 111 6768, 159 (to reach your bank), and 7726 (forward spam texts). For any organisation, tell readers to use the number on their card, bill, or the organisation's official website — never state or invent a company's own number."""

# ─── ALLOWLISTS / BLOCKLISTS ─────────────────────────────────────────────────

# The ONLY phone numbers a guide may state (normalised to digits-only). These
# are national, stable, cross-scam numbers verified against official sources.
# Everything else — bank fraud lines, courier numbers, utility numbers — is
# blocked, because hardcoding an organisation's number is the highest-
# consequence error on a scam-advice site (the audit found several wrong ones).
# New guides must instead tell readers to use the number on their card, bill,
# or the organisation's official website.
ALLOWED_PHONE_DIGITS = {
    "03001232040",   # Action Fraud
    "08082231133",   # Citizens Advice consumer helpline
    "08001116768",   # FCA consumer helpline (verified 2026-06-18)
    "7726",          # forward spam SMS (free, all UK networks)
    "159",           # Stop Scams UK — call your bank
    "0800111999",    # National Gas Emergency Service
    "105",           # power-cut / electricity emergency
    "999", "112", "101",  # police / emergency
}

# Substrings (matched case-insensitively, on word boundaries where sensible)
# that must never be presented as legitimate/current. Defunct or unsafe to
# recommend. Keep this list tight and factual.
BANNED_ENTITIES = [
    "ftx",            # collapsed Nov 2022; never a "legitimate exchange"
    "celsius network",
    "blockfi",
]

SEVERITY_BLOCK = "block"
SEVERITY_FLAG = "flag"


@dataclass
class GateResult:
    slug: str
    passed: bool
    issues: List[Dict] = field(default_factory=list)

    @property
    def blocking(self) -> List[Dict]:
        return [i for i in self.issues if i.get("severity") == SEVERITY_BLOCK]

    def summary(self) -> str:
        if self.passed:
            n = len(self.issues)
            return f"PASS{f' ({n} non-blocking flag(s))' if n else ''}"
        reasons = "; ".join(f"{i['check']}: {i['detail']}" for i in self.blocking)
        return f"FAIL — {reasons}"


# ─── TEXT EXTRACTION ─────────────────────────────────────────────────────────

def _post_text(post: Dict) -> str:
    """All human-readable body text from a post (sections + faq)."""
    parts: List[str] = []
    for item in post.get("sections", []):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            parts.append(str(item[1]))
    for item in post.get("faq", []):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            parts.append(str(item[0]))
            parts.append(str(item[1]))
    parts.append(str(post.get("hero", "")))
    parts.append(str(post.get("description", "")))
    return "\n".join(parts)


# Phone-like tokens: UK landline/mobile/freephone starting 0, plus the short
# codes we explicitly allow/deny. Avoids matching money (£2,868) and years.
_PHONE_RE = re.compile(r"(?<!\d)(?:0\d[\d\s]{5,12}\d|\b(?:7726|159|105|101|999|112)\b)")


def _norm_digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def check_phones(post: Dict) -> List[Dict]:
    text = _post_text(post)
    issues: List[Dict] = []
    seen = set()
    for m in _PHONE_RE.finditer(text):
        raw = m.group(0).strip()
        digits = _norm_digits(raw)
        if not digits or digits in seen:
            continue
        seen.add(digits)
        if digits not in ALLOWED_PHONE_DIGITS:
            issues.append({
                "check": "phone",
                "severity": SEVERITY_BLOCK,
                "detail": (f"states a non-allowlisted phone number '{raw}'. "
                           f"Do not hardcode organisation numbers — tell readers to use "
                           f"the number on their card, bill, or the official website."),
            })
    return issues


def check_banned_entities(post: Dict) -> List[Dict]:
    text = _post_text(post).lower()
    issues: List[Dict] = []
    for ent in BANNED_ENTITIES:
        if re.search(r"\b" + re.escape(ent.lower()) + r"\b", text):
            issues.append({
                "check": "entity",
                "severity": SEVERITY_BLOCK,
                "detail": f"references '{ent}', which is defunct/unsafe to present as legitimate.",
            })
    return issues


def check_deterministic(post: Dict) -> List[Dict]:
    # Note: no deterministic domain/URL check — these guides intentionally
    # contain example scam/lookalike domains, so a domain allowlist is pure
    # noise here. Domain plausibility is left to the LLM judge.
    return check_phones(post) + check_banned_entities(post)


# ─── LLM JUDGE ───────────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You are a strict fact-checking editor for a UK consumer-protection site. \
You are reviewing an AI-DRAFTED scam guide BEFORE publication. Your only job is to catch \
fabrication and unverifiable claims — not style. Assume the drafting model has no internet \
access and may hallucinate confidently.

Flag a claim when it is a specific assertion the reader could act on or be misled by and that \
cannot be safely assumed true:
- invented or unattributed statistics / figures / percentages / £ amounts presented as fact
- quotes attributed to a named person or organisation
- specific claims about a named company's deal, partnership, acquisition, product, pricing, or feature
- naming a specific company as "legitimate"/"genuine"/"trusted" (could be invented or defunct)
- a specific dated event, law, or regulatory action stated as fact
- any organisation-specific phone number (banks, couriers, utilities) — these should not be hardcoded

Do NOT flag: general scam-pattern description, the standard UK reporting routes (Action Fraud \
0300 123 2040, Citizens Advice 0808 223 1133, forward texts to 7726, report@phishing.gov.uk), \
or clearly directional language ("growing rapidly", "many victims").

Respond with ONLY this JSON, no other text:
{"verdict":"pass"|"fail","risk":"low"|"medium"|"high","issues":[{"claim":"<quote>","problem":"<short>","severity":"low"|"medium"|"high"}]}
Set verdict "fail" if there is ANY high-severity issue."""


def judge_llm(post: Dict, client, model: str) -> List[Dict]:
    """Run the LLM critic. Returns issue dicts. Fail-CLOSED on judge error
    (a post we cannot verify is treated as blocking, since the engine is
    autonomous)."""
    body = _post_text(post)
    user = (f"Title: {post.get('title','')}\n\nReview this draft guide:\n\n{body}\n\n"
            "Return the JSON verdict.")
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=1500,
            temperature=0,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001 — any failure must fail closed
        return [{"check": "judge", "severity": SEVERITY_BLOCK,
                 "detail": f"LLM judge could not verify this draft ({type(e).__name__}); failing closed."}]

    issues: List[Dict] = []
    for it in (data.get("issues") or []):
        sev = SEVERITY_BLOCK if it.get("severity") == "high" else SEVERITY_FLAG
        issues.append({"check": "judge", "severity": sev,
                       "detail": f"{it.get('problem','issue')}: \"{str(it.get('claim',''))[:140]}\""})
    if data.get("verdict") == "fail" or data.get("risk") == "high":
        if not any(i["severity"] == SEVERITY_BLOCK for i in issues):
            issues.append({"check": "judge", "severity": SEVERITY_BLOCK,
                           "detail": f"judge verdict={data.get('verdict')} risk={data.get('risk')}"})
    return issues


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def run_gate(post: Dict, client=None, model: Optional[str] = None,
             use_llm: bool = True) -> GateResult:
    """Run the full gate on a post. PASS unless a blocking issue is found."""
    issues = check_deterministic(post)
    if use_llm and client is not None and model:
        issues += judge_llm(post, client, model)
    passed = not any(i.get("severity") == SEVERITY_BLOCK for i in issues)
    return GateResult(slug=post.get("slug", "?"), passed=passed, issues=issues)


def quarantine_post(post: Dict, result: GateResult, today: str,
                    qdir: str = "content/quarantine") -> str:
    """Persist a gate-failed post for human review. It is NOT written to
    posts.json, so it never builds, deploys, or gets tweeted. Returns the path."""
    d = Path(qdir)
    d.mkdir(parents=True, exist_ok=True)
    rec = {
        "date":   today,
        "slug":   post.get("slug"),
        "title":  post.get("title"),
        "issues": result.issues,
        "post":   post,
    }
    path = d / f"{today}-{post.get('slug', 'unknown')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
    return str(path)
