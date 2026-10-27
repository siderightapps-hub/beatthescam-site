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
import hashlib
import re
from urllib.parse import urlsplit
from html.parser import HTMLParser
from html import escape as html_escape
from datetime import date
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canon as canon_mod   # noqa: E402  — the shared canon loader/validator/renderers
import reporting_contracts as reporting  # destination-first authorization
import reporting_structured as structured  # explicit canon actions; no prose authorisation
import corpus as corpus_mod  # noqa: E402  — the shared public/source corpus partition
from reporting_syntax import INVALID_MARKDOWN_LINK_RE

# ─── SHARED ACCURACY CONTRACT ────────────────────────────────────────────────
# Single source of truth for the anti-fabrication rules, imported by BOTH
# generators (generate_content_claude.py and search_console_articles.py) so
# their prompts cannot drift apart again (audit GAP 4). The gate's allowlist
# (ALLOWED_PHONE_DIGITS) and this prompt rule are kept deliberately in sync.
ACCURACY_BLOCK = """ACCURACY — THIS OVERRIDES EVERY STYLE AND SEO RULE BELOW. A plausible-sounding but invented fact about a real company, person, or product is the single worst failure this publication can make: it is libel-adjacent and gets the site rejected from ad networks.
- Use directional language ("growing rapidly", "a meaningful share", "early data suggests") for figures unless they are well-established public facts. Never invent specific percentages, dollar figures, or entity-attributed statistics. Do not attribute a statistic to a named body (Report Fraud, the FCA, Which?, UK Finance, NCSC) unless you are certain of the exact figure — if unsure, describe the pattern without a number. This includes ILLUSTRATIVE or hypothetical numbers: do not invent a count or rate to make a point (e.g. "they email 100,000 people and even if 0.1% pay") — describe the mechanism qualitatively instead ("sent to very large numbers of people, so even a tiny response rate is profitable").
- Never give the reader an unconditional guarantee or absolute about their own situation or safety: do not write that something is impossible, that no footage/recording/evidence exists, that they are "100% safe", or that an outcome is guaranteed. Real threats vary, so an absolute can be both wrong and harmful — use hedged, accurate language ("almost always a bluff", "it is extremely unlikely that any footage exists", "in the vast majority of cases"). Accurately describing a scammer's OWN false promise is fine.
- NEVER invent or assert a specific dated event, deal, acquisition, merger, partnership, funding round, valuation, product launch, regulatory action, or piece of legislation involving a real named company, person, product, or regulator unless you are certain it is a true, well-established public fact. This explicitly includes who-acquired-whom, who-partnered-with-whom, launch/approval dates, what a law or feature actually covers, pricing/plan limits, and which tool or vendor a named company actually uses.
- Never present a named company as "legitimate", "genuine", or "trusted" unless it is a well-known real brand; do not invent example company names.
- If you are not certain of the exact relationship, date, figure, or attribution, describe it in general terms WITHOUT naming a specific deal/number — or omit it. Inventing a product or vendor name, or pairing a real company with the wrong partner, tool, or capability, is forbidden.
- Before finalising, re-read every sentence that names a real company, person, or product alongside a date, number, deal, price, or feature. If you are not confident it is a true public fact, rewrite it as a general statement or delete it.
- Do NOT state a phone number for any specific company (bank, courier, retailer, utility, etc.). The only phone numbers permitted anywhere are the official reporting and support routes in the verified canon, `content/sources.json` — the same list the gate enforces at publish time. Do not work from a memorised list: if a number is not in that canon, do not print it. For any organisation, tell readers to use the number on their card, bill, or the organisation's official website.
- UK credit reference agencies: Experian, Equifax and TransUnion are the three MAIN agencies; MoneyHelper also lists Crediva as offering a free statutory report. Never write "the three CRAs", "all three" or "the other two" as if exhaustive. ClearScore is a free app and CallCredit is the obsolete name for TransUnion.
- The National Fraud Database is a Cifas service. Do not tell readers to add their name to it through Citizens Advice, Action Fraud, or Report Fraud. Report the scam separately to the appropriate reporting service; where identity misuse is a concern, direct readers to Cifas Protective Registration at cifas.org.uk.
"""

# ─── ALLOWLISTS / BLOCKLISTS ─────────────────────────────────────────────────

# The ONLY phone numbers a guide may state (normalised to digits-only) and the
# only official reporting emails — both DERIVED from the verified canon in
# content/sources.json (single source of truth, shared with build.py's on-page
# reporting block). Everything else — bank fraud lines, courier numbers, utility
# numbers — is blocked, because hardcoding an organisation's number is the
# highest-consequence error on a scam-advice site.
#
# There is no hardcoded fallback. Two successive reviews found the hand-
# maintained copy drifted from the canon (14 numbers against 17; one reporting
# email against five), and a fallback that only activates when the single source
# of truth has failed is precisely the wrong moment to trust it. An absent or
# invalid canon now stops the gate.


def _load_canon(path=None) -> Dict:
    """Load and structurally validate the verified canon. FAILS CLOSED.

    Delegates to the ONE shared validator in scripts/canon.py, which build.py
    also calls, so the gate and the build cannot disagree about what a valid
    canon is. Previously this function only *parsed* the file: a parseable `{}`
    or a structurally incomplete object gave the gate empty route rendering and
    an empty allow-list instead of stopping publication (operator review,
    2026-07-29).

    The hand-maintained phone/email fallback sets are gone. They were a second,
    unreviewed copy of the canon — the exact thing content/sources.json exists
    to prevent — and they let a missing deployment input pass unnoticed.
    """
    try:
        return canon_mod.load_canon(path)
    except canon_mod.CanonError as exc:
        raise SystemExit(f"ERROR: {exc}")


_canon_phone_digits = canon_mod.phone_digits
_canon_report_emails = canon_mod.report_emails


# The ONE rendering of nation-scoped reporting routes, derived from the canon
# and shared with every other consumer (the generator prompt, the generator's
# fallback article, the site's standalone surfaces and the scam checker) via
# scripts/canon.py. Re-exported under the old name so existing callers and the
# self-test's mutation assertion keep working. The nation strings are now read
# from the route records rather than hand-typed here, so a canon re-scoping
# propagates instead of silently disagreeing (operator review, 2026-07-29).
render_canon_routes = canon_mod.render_prompt_routes


_CANON = _load_canon()
# Rendered by scripts/canon.py — the ONE renderer, shared with the quarterly
# re-verification pass. It was local to this file until 2026-07-31, which is why
# fact_reverify.py had no canon at all and re-litigated settled routes.
_JUDGE_CANON_BLOCK = canon_mod.render_verified_facts(_CANON)
CANON_ROUTE_BLOCK = render_canon_routes(_CANON)
# Append the rendered routes so the prompt and the canon cannot disagree.
ACCURACY_BLOCK = ACCURACY_BLOCK.rstrip() + "\n" + CANON_ROUTE_BLOCK + "\n"
ALLOWED_PHONE_DIGITS = _canon_phone_digits(_CANON)
ALLOWED_REPORT_EMAILS = _canon_report_emails(_CANON)

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
    reporting_mode: str = structured.LEGACY_DIAGNOSTIC
    # Route integrity is not WP4 evidence/claim clearance. Existing callers are
    # contained; they must adopt the reviewed-context interface before resuming.
    publication_ready: bool = False

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

def _figure_fields(post: Dict):
    """Every reader-visible string inside a `figure` object, as (label, text).

    Added 2026-08-01. The `figure` field shipped on 2026-08-01 rendering an
    inline decision diagram whose title, alt text, caption and per-step
    sentences are all on the page — and the alt text is what a screen-reader
    user hears INSTEAD of the diagram, so it is the only version of that content
    some readers get. Nothing in the gate read any of it: a figure could have
    named an invented phone number, a retired brand, or routed a Cifas matter
    via Report Fraud, and every suite would have stayed green.

    `_post_text` already carried the rule this broke — "Any new reader-visible
    field MUST be added here at the same time it is rendered". It was not. This
    generator exists so the next renderer has one obvious place to hook into
    rather than four field lists to remember."""
    fig = post.get("figure")
    if not isinstance(fig, dict):
        return
    yield "figure title", str(fig.get("title") or "")
    yield "figure alt text", str(fig.get("alt") or "")
    yield "figure caption", str(fig.get("caption") or "")
    for i, step in enumerate(fig.get("steps") or [], 1):
        if not isinstance(step, dict):
            continue
        yield f"figure step {i} check", str(step.get("check") or "")
        yield f"figure step {i} outcome", str(step.get("then") or "")


def _post_text(post: Dict) -> str:
    """All reader-visible text from a post — title, quick answer, section
    HEADINGS and bodies, faq, hero, description, and keywords. Headings/title/
    keywords are included so a high-stakes claim placed there (a hardcoded
    number, banned entity, false absolute) is checked too, not only the section
    bodies.

    `quick_answer` was added to the post schema on 2026-07-25 and is rendered in
    a highlighted box AND targeted by speakable structured data — i.e. it is the
    single most extractable passage on the page. It was omitted here until
    2026-07-27, so nothing in the gate inspected it: 57 live quick answers named
    Report Fraud with no Scotland route and passed clean. Any new
    reader-visible field MUST be added here at the same time it is rendered."""
    parts: List[str] = [str(post.get("title", ""))]
    parts.append(str(post.get("quick_answer", "")))
    # Category hubs use an HTML `intro` field instead of a guide `hero`.
    # Including it here lets the same deterministic accuracy contract cover
    # every reader-visible hub claim when build.py runs its preflight gate.
    parts.append(str(post.get("intro", "")))
    for item in post.get("sections", []):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            parts.append(str(item[0]))   # section heading
            parts.append(str(item[1]))   # section body
    for item in post.get("faq", []):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            parts.append(str(item[0]))
            parts.append(str(item[1]))
    parts.append(str(post.get("hero", "")))
    parts.append(str(post.get("description", "")))
    for _, figure_text in _figure_fields(post):
        parts.append(figure_text)
    kws = post.get("keywords") or []
    if isinstance(kws, (list, tuple)):
        parts.append(" ".join(str(k) for k in kws))
    return "\n".join(parts)


# Phone-like tokens: UK landline/mobile/freephone starting 0, the +44/0044
# international prefix, plus the short codes we explicitly allow/deny.
# Digit groups may be separated by spaces, hyphens, dots, or parens (e.g.
# "0345-300-0000", "0345.300.0000", "(0345) 300 0000", "+44 345 300 0000",
# "+443453000000") — a bare "0\d[\d\s]{5,12}\d" pattern misses all of these.
# The separator class includes the Unicode hyphen/dash family (‐-―,
# −): models routinely emit en/em dashes, and "0345–300–0000" must not
# slip past the allow-list. "/" is deliberately excluded — it would make
# numeric dates like "01/02/2026" match as phone-like and false-BLOCK.
# Still avoids matching money (£2,868) and years (a leading 0/+44/0044 is
# required, which prose dates and prices don't start with).
_PHONE_SEP = r"[\s.\-()‐-―−]"
_PHONE_RE = re.compile(
    r"(?<!\d)(?:"
    r"(?:\+44|0044)" + _PHONE_SEP + r"*0?" + _PHONE_SEP + r"*\d(?:" + _PHONE_SEP + r"*\d){6,12}"
    r"|0" + _PHONE_SEP + r"*\d(?:" + _PHONE_SEP + r"*\d){5,12}"
    r"|\b(?:7726|159|105|101|999|112)\b"
    r")"
)


def _norm_digits(s: str) -> str:
    digits = re.sub(r"\D", "", s)
    # Normalise the +44/0044 international prefix to the domestic leading 0
    # so "+44 345 300 0000" compares equal to the allowlisted "0345 300 0000".
    if digits.startswith("0044"):
        digits = "0" + digits[4:]
    elif digits.startswith("44") and len(digits) >= 11:
        digits = "0" + digits[2:]
    return digits


# SMS shortcodes are 5–6 digits and the phone regex above only knows a
# hard-coded handful (7726, 159, 105, 101, 999, 112). Any other shortcode was
# therefore INVISIBLE to the gate: "forward the text to 61234" passed clean, so
# a fabricated reporting shortcode could ship (found while adding HMRC's genuine
# 60599 to the canon, 2026-07-31).
#
# Matched only in a FORWARDING context — "forward/text/send … to <code>" — so an
# ordinary 5-digit number in prose is not dragged in. The allow-list is derived
# from the canon, not hard-coded, so adding a verified route is enough.
_SHORTCODE_CONTEXT_RE = re.compile(
    r"\b(?:forward(?:ing|s)?|text(?:ing|s)?|send(?:ing|s)?|report(?:ing|s)?)\b[^.]{0,60}?"
    r"\bto\s+`?(\d{5,6})`?\b", re.I)


def _canon_shortcodes() -> set:
    codes = set()
    for group in ("official_routes", "verified_org_contacts"):
        for r in _CANON.get(group, []):
            if r.get("sms"):
                codes.add(re.sub(r"\D", "", str(r["sms"])))
    return codes


def check_shortcodes(post: Dict) -> List[Dict]:
    """A 5–6 digit SMS shortcode offered as a reporting route must be in the canon."""
    text = _post_text(post)
    allowed = _canon_shortcodes()
    issues: List[Dict] = []
    seen = set()
    for m in _SHORTCODE_CONTEXT_RE.finditer(text):
        code = m.group(1)
        if code in allowed or code in seen:
            continue
        seen.add(code)
        issues.append({
            "check": "shortcode",
            "severity": SEVERITY_BLOCK,
            "span": code,
            "detail": (f"offers SMS shortcode '{code}' as a reporting route, but it is not in "
                       f"content/sources.json. Verify it against the organisation's own "
                       f"published page and add it to verified_org_contacts with source_url "
                       f"and checked_on, or tell readers to use the route on the official site."),
        })
    return issues


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
                "span": raw,
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
                "span": ent,
                "detail": f"references '{ent}', which is defunct/unsafe to present as legitimate.",
            })
    return issues


# Unconditional certainty that is dangerous on a safety-advice site. These are
# claims only the SITE makes to the reader — a scammer asserts the OPPOSITE (that
# footage/evidence DOES exist), so collision with described scammer-speech is ~nil.
# Hedged advice ("it is extremely unlikely that any footage exists", "there is
# almost certainly no footage") does NOT match these bare-absolute patterns by
# construction, because an adverb sits between the verb and the negation/noun.
# This is the exact class that leaked into the 2026-06-19 sextortion guide.
_ABSOLUTE_RES = [
    re.compile(r"\bno\s+(?:such\s+)?(?:footage|video|recording|images?|photos?|"
               r"pictures?)\s+(?:exists?|was\s+(?:ever\s+)?(?:taken|made|recorded|captured))\b", re.I),
    re.compile(r"\bthere\s+(?:is|are)\s+no\s+(?:footage|video|recording|images?|photos?|pictures?)\b", re.I),
    re.compile(r"\b(?:footage|video|recording|images?|photos?|pictures?)\s+(?:does|do)\s+not\s+exist\b", re.I),
    # Accept contractions ("you're", "you've", curly or straight apostrophe) —
    # "You're completely safe." must block exactly like "You are completely safe."
    re.compile(r"\byou(?:\s+are|['’]re)\s+(?:completely|totally|perfectly|fully|entirely|100%)\s+safe\b", re.I),
    re.compile(r"\byou(?:\s+have|['’]ve)\s+nothing\s+to\s+(?:worry\s+about|fear)\b", re.I),
    # RISK-ELIMINATION guarantees. The existing patterns all reassure the reader
    # directly ("you're completely safe"); this shape reassures them about an
    # ACTION — "buying direct eliminates resale risk entirely" — and slipped
    # through (LLM judge sample, 2026-07-31). Deliberately requires the word
    # "risk": "leaving the platform removes the platform's own protection
    # entirely" is a WARNING, not a safety guarantee, and must not match.
    re.compile(r"\b(?:eliminat\w+|remov\w+|get(?:s|ting)?\s+rid\s+of)\b[^.]{0,40}?\brisk\b"
               r"[^.]{0,30}?\b(?:entirely|completely|altogether|for\s+good)\b", re.I),
    re.compile(r"\brisk\b[^.]{0,30}?\b(?:eliminated|removed)\s+(?:entirely|completely|altogether)\b", re.I),
    re.compile(r"\b(?:zero|no)\s+risk\s+(?:at\s+all|whatsoever)\b", re.I),
    re.compile(r"\b(?:completely|totally|entirely|100%)\s+risk[- ]free\b", re.I),
]


def check_absolutes(post: Dict) -> List[Dict]:
    text = _post_text(post)
    issues: List[Dict] = []
    seen = set()
    for rx in _ABSOLUTE_RES:
        m = rx.search(text)
        if m:
            phrase = m.group(0).strip().lower()
            if phrase in seen:
                continue
            seen.add(phrase)
            issues.append({
                "check": "absolute",
                "severity": SEVERITY_BLOCK,
                "span": m.group(0).strip(),
                "detail": (f"makes an unconditional guarantee/absolute to the reader "
                           f"('{m.group(0).strip()}'). Real threats vary — use hedged, "
                           f"accurate language ('almost always a bluff', 'extremely "
                           f"unlikely that any footage exists')."),
            })
    return issues


# Email addresses on a UK government / police domain are almost always presented
# as an official reporting route. One that is NOT in the canon is likely
# hallucinated (a victim could send evidence into the void), but real gov
# reporting addresses exist beyond ours (e.g. phishing@hmrc.gov.uk), so this is
# a FLAG (review via the weekly digest), not a hard block — add confirmed ones
# to content/sources.json.
_REPORT_EMAIL_RE = re.compile(r"\b[\w.+-]+@(?:[\w-]+\.)*(?:gov\.uk|police\.uk)\b", re.I)


# Any email offered to the reader as somewhere to SEND a report.
#
# _REPORT_EMAIL_RE below matches only gov.uk / police.uk, so a reporting mailbox
# on any other domain was invisible: `phishing@slc.co.uk` (retired by the
# Student Loans Company) shipped and stayed live, and a wholly invented address
# would have passed the same way. Same failure mode as the SMS shortcode hole —
# a validator whose pattern is narrower than the class it polices, where the gap
# is silent because non-matching input is never considered (audit, 2026-07-31).
#
# Scoped to a REPORTING INSTRUCTION, not any email in prose: guides quote
# scammers' own addresses as examples, and those must not be flagged.
# Verb forms are ENUMERATED, not `send\w*` — that wildcard also matches the NOUN
# "sender", so "a sender like no-reply@fake.example is a red flag" read as a
# reporting instruction. Caught by this check's own benign fixtures.
_REPORT_INSTRUCTION_RE = re.compile(
    r"\b(?:forward|forwards|forwarding|report|reports|reporting|"
    r"email|emails|emailing|send|sends|sending|contact|contacts|contacting)\b"
    r"[^.]{0,50}?(?:\bto\s+)?`?([\w.+-]+@[\w-]+(?:\.[\w-]+)+)`?", re.I)


# A guide may quote an organisation's SENDING address so a reader can recognise
# genuine mail ("its legitimate emails come from donotreply@yodel.co.uk"). That
# is a claim about what real mail looks like, NOT a route to report to, and it
# does not belong in verified_org_contacts. The instruction regex matched them
# anyway because "emails" sits right beside the address — six of the first 32
# flags were this class (operator review, 2026-07-31).
_SENDER_CLAIM_RE = re.compile(
    r"\b(?:come|comes|came|sent|arrive|arrives)\s+from\b"
    r"|\breceive\s+(?:\w+\s+){0,3}(?:emails?|messages?|mail)\s+from\b"
    # An organisation NAMING its own sending addresses: "its identified senders
    # are X", "TV Licensing identifies X and Y".
    r"|\bsenders?\s+(?:are|is)\b|\bidentifie[sd]\b"
    # Asking WHETHER an address is genuine is the opposite of instructing someone
    # to use it. Allow a multi-word brand between the two words — "a genuine TV
    # Licensing address" was missed by a single-\w+ pattern.
    r"|\bis\s+a\s+genuine\b|\bgenuine\s+(?:\w+\s+){0,3}address\b"
    r"|\bis\s+[\w.+-]+@[\w.-]+\s+(?:a\s+)?(?:genuine|legitimate|legit|real)\b"
    r"|\bsupport\s+inbox\s+is\b", re.I)


def check_report_mailboxes(post: Dict) -> List[Dict]:
    """An email the guide tells the reader to report TO must be in the canon."""
    text = _post_text(post)
    allowed = {e.lower() for e in ALLOWED_REPORT_EMAILS}
    for group in ("official_routes", "verified_org_contacts"):
        for r in _CANON.get(group, []):
            if r.get("email"):
                allowed.add(str(r["email"]).lower())
    issues: List[Dict] = []
    seen = set()
    for m in _REPORT_INSTRUCTION_RE.finditer(text):
        addr = m.group(1).strip().rstrip(".,;:")
        low = addr.lower()
        if low in allowed or low in seen:
            continue
        # Look at the clause around the address, not just the matched span: a
        # sender claim is about where mail ORIGINATES, not where to send it.
        window = text[max(0, m.start() - 120):m.end() + 60]
        if _SENDER_CLAIM_RE.search(window):
            continue
        seen.add(low)
        issues.append({
            "check": "report_mailbox",
            "severity": SEVERITY_FLAG,
            "span": addr,
            "detail": (f"tells the reader to report to '{addr}', which is not in "
                       f"content/sources.json. Verify it against the organisation's own "
                       f"published page and add it to verified_org_contacts with source_url "
                       f"and checked_on, or point readers at the route on the official site. "
                       f"A retired or invented reporting mailbox sends a victim's evidence "
                       f"nowhere, or to an attacker."),
        })
    return issues


def check_sources(post: Dict) -> List[Dict]:
    text = _post_text(post)
    issues: List[Dict] = []
    seen = set()
    for m in _REPORT_EMAIL_RE.finditer(text):
        email = m.group(0).strip()
        low = email.lower()
        if low in seen:
            continue
        seen.add(low)
        if low not in ALLOWED_REPORT_EMAILS:
            issues.append({
                "check": "source",
                "severity": SEVERITY_FLAG,
                "span": email,
                "detail": (f"cites a non-canon official reporting email '{email}'. "
                           f"Verify it and add it to content/sources.json, or use a "
                           f"canon route (e.g. report@phishing.gov.uk)."),
            })
    return issues


# Legislation / legal-entitlement assertions. We can't verify the LAW
# deterministically, so these are FLAG-tier (recorded in the manifest + surfaced
# in the weekly digest for a human to confirm), never a block — many are correct
# (e.g. "the Fraud Act 2006"). The judge still independently blocks fabrications.
_LEGISLATION_RES = [
    # Case-sensitive on purpose ([A-Z] identifies the proper-noun Act name), but
    # "[Tt]he" so a sentence-initial "The Fraud Act 2006…" is also caught.
    re.compile(r"\b[Tt]he\s+(?:[A-Z][\w’']+\s+){1,5}Act\b(?:\s+\d{4})?", ),  # "the Fraud Act 2006"
    re.compile(r"\b(?:illegal|unlawful|a\s+criminal\s+offence)\s+under\b", re.I),
    re.compile(r"\b(?:you\s+are|you’re|you're)\s+legally\s+(?:entitled|required|obliged|protected)\b", re.I),
    re.compile(r"\blegally\s+(?:entitled|required|obliged)\s+to\b", re.I),
]


def check_legislation(post: Dict) -> List[Dict]:
    text = _post_text(post)
    issues: List[Dict] = []
    seen = set()
    for rx in _LEGISLATION_RES:
        for m in rx.finditer(text):
            span = m.group(0).strip()
            key = span.lower()
            if key in seen:
                continue
            seen.add(key)
            issues.append({
                "check": "legislation",
                "severity": SEVERITY_FLAG,
                "span": span,
                "detail": f"makes a legal/legislation claim ('{span}') — verify it is accurate.",
            })
    return issues


# A regulator/authority named alongside a specific year and an event verb — the
# "invented dated regulatory event" failure class the audit flagged. High-stakes
# but unverifiable deterministically → FLAG (manifest + digest), not a block.
_AUTHORITIES = (r"FCA|Ofcom|ICO|HMRC|NCSC|Action\s+Fraud|Report\s+Fraud|Companies\s+House|DVLA|"
                r"Ofgem|PSR|FOS|Financial\s+Ombudsman|Trading\s+Standards|Which\?|UK\s+Finance")
_EVENT_VERB = (r"banned|fined|launched|introduced|ruled|announced|acquired|merged|"
               r"ordered|warned|seized|charged|prosecuted|shut\s+down")
# Year: a plausible recent year (2000–2029), NOT one embedded in a phone number
# (e.g. the "2040" in Action Fraud's 0300 123 2040, or "…111 2024").
_YEAR = r"(?<!\d\s)(?<!\d)(20[0-2]\d)\b"
_DATED_RE = re.compile(
    rf"\b(?:{_AUTHORITIES})\b[^.]{{0,60}}?\b(?:{_EVENT_VERB})\b[^.]{{0,40}}?{_YEAR}"
    rf"|\b(?:{_EVENT_VERB})\b[^.]{{0,40}}?\b(?:{_AUTHORITIES})\b[^.]{{0,40}}?{_YEAR}",
    re.I)


def check_dated_events(post: Dict) -> List[Dict]:
    text = _post_text(post)
    issues: List[Dict] = []
    seen = set()
    for m in _DATED_RE.finditer(text):
        span = re.sub(r"\s+", " ", m.group(0).strip())[:160]
        key = span.lower()
        if key in seen:
            continue
        seen.add(key)
        issues.append({
            "check": "dated_event",
            "severity": SEVERITY_FLAG,
            "span": span,
            "detail": f"asserts a dated event involving an authority ('{span}') — verify it is true.",
        })
    return issues


# ─── UK CONSUMER-PROTECTION ACCURACY (added after the 2026-06 editorial audit) ─
# Catches the exact recurring factual errors that audit found in the corpus.

# ClearScore is a free credit-checking APP (it resells Equifax data); "CallCredit"
# was renamed TransUnion in 2018. Neither is a UK credit reference agency. The
# three MAIN CRAs are Experian, Equifax and TransUnion; MoneyHelper also lists
# Crediva as offering a free statutory report, so "the three CRAs" must not be
# written as if exhaustive (operator review, 2026-07-27). Presenting
# ClearScore/CallCredit
# AS an agency (enumerated alongside BOTH Experian and Equifax, or right next to
# "credit reference agenc[y]") is the misclassification to BLOCK. A correct,
# standalone mention of ClearScore as a free app sits apart from the trio, so
# requiring both other agencies (or the explicit CRA phrase) keeps this tight.
_CRA_APP_RE = re.compile(r"\b(?:clear\s?score|call\s?credit)\b", re.I)
# A guide *correcting* the error ("ClearScore is a free app, not a credit
# reference agency") is accurate and must not be quarantined — a false BLOCK
# silently burns the topic (quarantined drafts are never retried).
_CRA_NEGATED_RE = re.compile(
    r"\b(?:not?|isn['’]t|aren['’]t|rather\s+than|instead\s+of|unlike)\b[^.!?\n]{0,40}"
    r"credit\s+reference\s+agenc", re.I)
def check_cra_misclassification(post: Dict) -> List[Dict]:
    issues: List[Dict] = []
    seen = set()
    # Split on newlines as well as sentence punctuation: _post_text joins
    # title/headings/bodies with \n and headings carry no terminal punctuation,
    # so without the newline split a heading naming Experian+Equifax would
    # bleed into the next line and false-positive a correct ClearScore mention.
    for seg in re.split(r"(?<=[.!?])\s+|\n+", _post_text(post)):
        low = seg.lower()
        if not _CRA_APP_RE.search(low):
            continue
        if _CRA_NEGATED_RE.search(seg):
            continue
        if ("credit reference agenc" in low) or ("experian" in low and "equifax" in low):
            key = low[:60]
            if key in seen:
                continue
            seen.add(key)
            name = "ClearScore" if re.search(r"clear\s?score", low) else "CallCredit"
            issues.append({
                "check": "cra_misclassification",
                "severity": SEVERITY_BLOCK,
                "span": seg.strip()[:160],
                "detail": (f"presents '{name}' as a UK credit reference agency. The three main CRAs "
                           f"are Experian, Equifax and TransUnion, and MoneyHelper also lists Crediva "
                           f"as offering a free statutory report — ClearScore is a free credit-checking "
                           f"app and CallCredit was renamed TransUnion in 2018. Use TransUnion."),
            })
    return issues


# The National Fraud Database is a Cifas service; consumers join via a Cifas
# Protective Registration (cifas.org.uk), NOT "through Citizens Advice" or "via
# Action Fraud" / "via Report Fraud". Routing it through those bodies is the wrong-routing error. BLOCK.
# The gap pattern may cross ONE sentence boundary ("…the National Fraud
# Database. You do this through Citizens Advice.") — two short sentences is
# exactly how a model phrases the wrong routing, and "[^.]{0,60}" alone stops
# at the full stop and misses it.
_NFD_GAP = r"[^.]{0,60}(?:\.\s+[^.]{0,60})?"
_NFD_ROUTING_RE = re.compile(
    r"national\s+fraud\s+database" + _NFD_GAP + r"\b(?:citizens\s+advice|action\s+fraud|report\s+fraud)\b"
    r"|\b(?:through|via|with)\s+(?:citizens\s+advice|action\s+fraud|report\s+fraud)\b" + _NFD_GAP + r"national\s+fraud\s+database",
    re.I)
def check_nfd_routing(post: Dict) -> List[Dict]:
    text = _post_text(post)
    if _NFD_ROUTING_RE.search(text):
        m = _NFD_ROUTING_RE.search(text)
        return [{
            "check": "nfd_routing",
            "severity": SEVERITY_BLOCK,
            "span": re.sub(r"\s+", " ", m.group(0))[:160],
            "detail": ("routes the National Fraud Database through Citizens Advice / Report Fraud / Action Fraud. "
                       "It is a Cifas service — direct readers to a Cifas Protective Registration "
                       "(cifas.org.uk)."),
        }]
    return []


# US-style "fraud alert on your credit file" is not a UK mechanism (that is a
# Cifas Protective Registration). Imprecise rather than dangerous → FLAG (review).
_FRAUD_ALERT_RE = re.compile(
    r"fraud\s+alert[^.]{0,40}credit\s+(?:file|report|record|reference\s+agenc(?:y|ies))"
    r"|credit\s+(?:file|report|record|reference\s+agenc(?:y|ies))[^.]{0,40}fraud\s+alert", re.I)
# HMRC runs genuine SMS/email campaigns and genuine texts can carry gov.uk links,
# so blanket "HMRC never texts/emails/links you" is inaccurate → FLAG (review).
_HMRC_CHANNEL_RE = re.compile(
    r"HMRC[^.]{0,40}\bnever\b[^.]{0,40}\b(?:text|texts|sms|e-?mails?|links?)\b", re.I)
# The check's own guidance is to say HMRC won't ask you to CONFIRM details or
# 'CLAIM' a refund. Written that way the sentence still matches the pattern
# above ("...never asks you to 'confirm' bank details by text"), so the correct
# wording was flagged forever — noise that trains everyone to ignore the flag,
# which is how the retired SLC mailbox survived. A match carrying one of these
# qualifiers is the narrow form, not a blanket channel claim (audit, 2026-07-31).
def _hmrc_blanket(text: str):
    """True only for an UNQUALIFIED blanket channel claim."""
    m = _HMRC_CHANNEL_RE.search(text)
    return m and not _HMRC_QUALIFIED_RE.search(m.group(0))


_HMRC_QUALIFIED_RE = re.compile(
    r"\b(?:confirm|claim|verify|bank details|card details|security (?:details|information)|"
    r"password|passcode|PIN|one-?time code)\b", re.I)

# Other over-broad channel and reimbursement statements found in the 2026-07
# category-hub audit. Genuine banks and public bodies sometimes send links, so
# the safe rule is to verify independently and never disclose sensitive data.
# Ofcom's current page says suspicious SMS texts can be forwarded to 7726 free
# of charge; it does not claim universal network coverage, and directs RCS,
# iMessage and app messages to their built-in reporting tools. Mandatory APP
# reimbursement also has payment-rail, claimant, exception, cap, excess and
# stop-clock qualifications.
_BANK_LINK_ABSOLUTE_RE = re.compile(
    r"\bbanks?\b[^.]{0,70}\b(?:never|don['’]t|do\s+not|won['’]t|will\s+not)\b"
    r"[^.]{0,35}\b(?:send|include|contain|use)\b[^.]{0,20}\blinks?\b", re.I)
_7726_ALL_NETWORKS_RE = re.compile(
    r"\b7726\b[\s\S]{0,140}\b(?:all|every)\b[^.]{0,30}\b(?:UK\s+)?(?:mobile\s+)?networks?\b", re.I)
_7726_NON_SMS_RE = re.compile(
    r"\b(?:forward|send|report)\b[^.;]{0,100}"
    r"\b(?:RCS|iMessage|WhatsApp|app\s+messages?)\b[^.;]{0,100}\b7726\b", re.I)
_APP_REIMBURSEMENT_ABSOLUTE_RE = re.compile(
    r"\b(?:UK\s+)?banks?\b[^.]{0,35}\b(?:must|are\s+required\s+to)\b"
    r"[^.]{0,35}\breimburse\b[^.]{0,60}\b(?:five|5)\s+(?:business\s+)?days?\b", re.I)
_COURIER_PAYMENT_ABSOLUTE_RE = re.compile(
    r"\b(?:DPD|Royal\s+Mail|couriers?)\b[^.]{0,80}\b(?:never|do(?:es)?\s+not|won['’]t|will\s+not)\b"
    r"[^.]{0,45}\b(?:asks?|requested?|requests?|sends?|includes?|contains?)\b[^.]{0,35}\b(?:payment|pay|fee|card)\b", re.I)
_RETAILER_COMPANY_ABSOLUTE_RE = re.compile(
    r"\b(?:legitimate|genuine|real)\s+(?:UK\s+)?retailers?\b[^.]{0,80}"
    r"\b(?:registered\s+company\s+number|registered[^.]{0,20}Companies\s+House)\b", re.I)
_AMAZON_COLD_CALL_ABSOLUTE_RE = re.compile(
    r"\bAmazon\b[^.]{0,45}\b(?:does\s+not|doesn['’]t|never)\b[^.]{0,25}\bcold[- ]?call", re.I)
_PAYPAL_180_GENERIC_RE = re.compile(
    r"\bPayPal\b[^.]{0,90}\b(?:dispute|claim)\b[^.]{0,40}\bwithin\s+180\s+days\b", re.I)
_SECTION75_INCLUSIVE_RE = re.compile(
    r"\bSection\s+75\b[^.]{0,90}(?:£\s*100\s+(?:to|-)|card\s+payments?\s+(?:over|above)\s+£\s*100)", re.I)
def check_uk_advice_flags(post: Dict) -> List[Dict]:
    text = _post_text(post)
    issues: List[Dict] = []
    if _FRAUD_ALERT_RE.search(text):
        issues.append({"check": "fraud_alert", "severity": SEVERITY_FLAG,
                       "span": re.sub(r"\s+", " ", _FRAUD_ALERT_RE.search(text).group(0))[:140],
                       "detail": ("uses US-style 'fraud alert on your credit file'. The UK mechanism is a "
                                  "Cifas Protective Registration (cifas.org.uk); free CRA monitoring is separate.")})
    if _hmrc_blanket(text):
        issues.append({"check": "hmrc_channel", "severity": SEVERITY_FLAG,
                       "span": re.sub(r"\s+", " ", _HMRC_CHANNEL_RE.search(text).group(0))[:140],
                       "detail": ("blanket 'HMRC never texts/emails/links you' — HMRC runs genuine SMS/email "
                                  "campaigns and genuine texts can carry gov.uk links. Say HMRC won't ask you "
                                  "to confirm details or 'claim' a refund via a link.")})
    if _BANK_LINK_ABSOLUTE_RE.search(text):
        issues.append({"check": "bank_link_absolute", "severity": SEVERITY_FLAG,
                       "span": re.sub(r"\s+", " ", _BANK_LINK_ABSOLUTE_RE.search(text).group(0))[:140],
                       "detail": ("blanket claim that banks never send/include links. Genuine messages can include "
                                  "links; teach independent verification and never sharing passwords, PINs or codes.")})
    if _7726_ALL_NETWORKS_RE.search(text):
        issues.append({"check": "7726_scope", "severity": SEVERITY_FLAG,
                       "span": re.sub(r"\s+", " ", _7726_ALL_NETWORKS_RE.search(text).group(0))[:140],
                       "detail": ("claims 7726 works on all/every UK network. Current Ofcom guidance instead "
                                  "says a suspicious SMS text can be forwarded to 7726 free of charge; use that "
                                  "format-specific wording without asserting network coverage.")})
    if _7726_NON_SMS_RE.search(text):
        issues.append({"check": "7726_format_scope", "severity": SEVERITY_FLAG,
                       "span": re.sub(r"\s+", " ", _7726_NON_SMS_RE.search(text).group(0))[:140],
                       "detail": ("claims non-SMS formats can be forwarded to 7726. Current Ofcom guidance "
                                  "limits 7726 forwarding to SMS; RCS, iMessage and app messages should use "
                                  "their relevant built-in reporting tools.")})
    if _APP_REIMBURSEMENT_ABSOLUTE_RE.search(text):
        issues.append({"check": "app_reimbursement_scope", "severity": SEVERITY_BLOCK,
                       "span": re.sub(r"\s+", " ", _APP_REIMBURSEMENT_ABSOLUTE_RE.search(text).group(0))[:140],
                       "detail": ("oversimplifies mandatory APP reimbursement. State the eligible claimants and "
                                  "payment rails, exceptions, possible excess, cap, normal timetable and stop-clock.")})
    for rx, check, detail in (
        (_COURIER_PAYMENT_ABSOLUTE_RE, "courier_payment_absolute",
         "blanket claim that a courier never requests payment. Genuine import duties/taxes can be notified electronically; distinguish standard redelivery scams and require independent parcel verification."),
        (_RETAILER_COMPANY_ABSOLUTE_RE, "retailer_company_absolute",
         "treats Companies House registration as universal proof. Legitimate sole traders are not Companies House companies; apply that check only to a business claiming to be incorporated."),
        (_AMAZON_COLD_CALL_ABSOLUTE_RE, "amazon_cold_call_absolute",
         "claims Amazon never cold-calls. Use the sourced rules on OTPs/confidential information and tell readers to verify an unexpected call through their account."),
        (_PAYPAL_180_GENERIC_RE, "paypal_deadline",
         "gives a generic 180-day PayPal deadline. Item Not Received and Significantly Not as Described have different current deadlines; tell readers to open the Resolution Centre immediately and state both rules."),
        (_SECTION75_INCLUSIVE_RE, "section75_scope",
         "misstates Section 75 as inclusive of £100 or as generic card protection. Use a qualifying credit purchase with a cash price over £100 and no more than £30,000, subject to the required relationship."),
    ):
        m = rx.search(text)
        if m:
            issues.append({"check": check, "severity": SEVERITY_BLOCK,
                           "span": re.sub(r"\s+", " ", m.group(0))[:160], "detail": detail})
    return issues


# ── Recurring factual-accuracy guards (from the 2026-06 editorial audit) ──────
# Outdated reimbursement framework: the VOLUNTARY Contingent Reimbursement Model
# (CRM code) was superseded on 7 Oct 2024 by MANDATORY APP-fraud reimbursement
# under PSR rules. Presenting the CRM code as current recourse is wrong. FLAG.
_CRM_CODE_RE = re.compile(r"contingent\s+reimbursement\s+model|\bCRM\s+code\b", re.I)
# 7726 is the spam-reporting shortcode run by the MOBILE NETWORKS, not the NCSC
# (the NCSC runs report@phishing.gov.uk for emails). Misattribution. FLAG.
_SHORTCODE_NCSC_RE = re.compile(
    r"7726[^.]{0,60}\b(?:ncsc|national\s+cyber\s+security)\b"
    r"|\b(?:ncsc|national\s+cyber\s+security)\b[^.]{0,60}7726", re.I)
# "credit freeze" is a US mechanism with no UK equivalent (use a Cifas Protective
# Registration). Imprecise rather than dangerous → FLAG.
_CREDIT_FREEZE_RE = re.compile(r"credit\s+freeze|freez(?:e|ing)\s+your\s+credit", re.I)
# Cifas Protective Registration places a warning flag in the Cifas National Fraud
# Database. It does NOT annotate your credit file, and it is not credit
# insurance. Added 2026-08-08: the 2026-08-08 pipeline draft shipped "register
# with Cifas Protective Registration ... to add a note to your credit file" and
# passed the gate clean, because _FRAUD_ALERT_RE requires the literal words
# "fraud alert" and this phrasing never uses them. Same US-shaped error, one
# phrasing over. Deliberately does NOT require a Cifas mention in the span: the
# UK has no consumer mechanism that annotates a credit file, so the claim is
# wrong on its own. FLAG, matching its _FRAUD_ALERT_RE / _CREDIT_FREEZE_RE
# siblings.
_CREDIT_FILE_NOTE_RE = re.compile(
    r"\b(?:add|adds|adding|place|places|placing|put|puts|putting|register|registering)\b"
    r"[^.]{0,40}\b(?:note|marker|flag|alert|warning)\b"
    r"[^.]{0,40}\bcredit\s+(?:file|report|record)\b", re.I)
# Dangerous threat-dismissal heuristic: teaching a victim that the ABSENCE of
# proof means a threat is fake can make them ignore a real one. The LLM judge
# BLOCKs the worst "no footage exists" absolutes; this is a deterministic
# backstop for the directive forms. FLAG.
_THREAT_DISMISS_RE = re.compile(
    r"assume[^.]{0,30}\b(?:fake|bluff)\b[^.]{0,30}unless"
    r"|(?:genuine|real|legitimate)\s+threat\s+would[^.]{0,80}\b(?:proof|evidence|screenshot|verifiable)\b", re.I)
# The FCA retired the "ScamSmart" branding — the canon (sources.json, 2026-07-05)
# is the "FCA Firm Checker". Models with an older knowledge cutoff still write
# "check ScamSmart", so guard the retired name. FLAG (review), not block.
_SCAMSMART_RE = re.compile(r"\bscam\s?smart\b", re.I)


def check_recurring_accuracy(post: Dict) -> List[Dict]:
    """Forward guards for the recurring errors the editorial audit found, so new
    (incl. future-locale) drafts can't silently reproduce them. All FLAG-tier:
    recorded in the manifest + surfaced in the weekly digest and PR review."""
    text = _post_text(post)
    issues: List[Dict] = []

    def flag(rx, check, detail):
        m = rx.search(text)
        if m:
            issues.append({"check": check, "severity": SEVERITY_FLAG,
                           "span": re.sub(r"\s+", " ", m.group(0))[:140], "detail": detail})

    flag(_CRM_CODE_RE, "reimbursement_framework",
         "cites the voluntary Contingent Reimbursement Model / CRM code. Since 7 Oct 2024, "
         "APP-fraud reimbursement is MANDATORY under PSR rules for most banks — frame recovery "
         "around the mandatory scheme, not the superseded voluntary one.")
    flag(_SHORTCODE_NCSC_RE, "shortcode_attribution",
         "attributes 7726 to the NCSC. 7726 is the free spam-reporting shortcode run by the mobile "
         "networks; the NCSC runs report@phishing.gov.uk for suspicious EMAILS.")
    flag(_CREDIT_FREEZE_RE, "credit_freeze",
         "uses the US 'credit freeze' — there is no UK credit freeze. The UK mechanism is a Cifas "
         "Protective Registration (cifas.org.uk).")
    flag(_CREDIT_FILE_NOTE_RE, "credit_file_annotation",
         "describes adding a note/marker/flag to a credit file. No UK consumer mechanism does that: "
         "Cifas Protective Registration places a warning flag in the Cifas National Fraud Database "
         "(cifas.org.uk, £30 for two years), which is separate from your credit file and is not "
         "credit insurance. Say what Protective Registration actually does.")
    flag(_THREAT_DISMISS_RE, "threat_dismissal",
         "teaches that the absence of proof means a threat is fake/a bluff. Reassure that most are "
         "bulk bluffs WITHOUT guaranteeing safety; never imply a victim's real threat is fake.")
    flag(_SCAMSMART_RE, "retired_branding",
         "references the FCA's retired 'ScamSmart' branding. The current canon route is the FCA "
         "Firm Checker (register.fca.org.uk) — see content/sources.json.")
    return issues


SIMILARITY_SHINGLE_K = 7
SIMILARITY_FLAG_AT = 0.15
SIMILARITY_BLOCK_AT = 0.30


def _body_words(post: Dict) -> List[str]:
    """Rendered body words only (sections + faq + figure), normalised for
    comparison. Titles/descriptions/quick answers are excluded: they are already
    unique by construction, and including them would mask body-level
    duplication.

    Figure text is INCLUDED (2026-08-01) precisely because it is not unique by
    construction. A decision diagram is the easiest field on the page to
    template — same three checks, brand name swapped — and doing that across the
    corpus would reintroduce the cookie-cutter duplication this check was built
    to catch, in the most visually prominent element on the page. Counting it
    here means a templated figure raises the similarity it actually causes."""
    parts = []
    for h, b in post.get("sections") or []:
        parts.append(f"{h} {b}")
    for q, a in structured.narrative_faq(post):
        parts.append(f"{q} {a}")
    for _, figure_text in _figure_fields(post):
        parts.append(figure_text)
    text = re.sub(r"[^a-z0-9 ]", " ", " ".join(parts).lower())
    return re.sub(r"\s+", " ", text).split()


def body_shingles(post: Dict, k: int = SIMILARITY_SHINGLE_K) -> set:
    w = _body_words(post)
    return {tuple(w[i:i + k]) for i in range(len(w) - k + 1)}


def check_similarity(post: Dict, corpus: Optional[List[Dict]] = None, *,
                     include_consolidated: bool = False) -> List[Dict]:
    """Flag a draft that reuses another PUBLIC guide's body copy.

    The 2026-07-25 audit found five published pairs above 0.30 Jaccard
    similarity on seven-word shingles (top pair 0.538, with an identical
    recovery section) — the single clearest AdSense "scaled content"/
    "cookie-cutter" risk on the site. The generation-time gate had no notion
    of the rest of the corpus, so nothing could catch it before publication.

    Deliberately compares against ALL other PUBLIC guides, not just
    same-category ones: the worst offenders (shopping brands, bank texts) sit
    inside one category, but travel/marketplace overlaps cross categories.

    CONSOLIDATED records are excluded. A record carrying `consolidated_into` is
    retained archive data that never renders and 301s to its replacement, so it
    is not a page anyone can land on and cannot be a duplicate of one. Comparing
    it against the guide it was consolidated INTO reported the consolidation
    itself as a 54% duplicate-content BLOCK — while this function's own remedy
    text says "or consolidate the two guides" (operator review, 2026-07-30).
    This is a corpus-state rule, not a named exception for one pair: every
    non-rendered archive record is outside the AdSense duplicate-page question.

    `include_consolidated=True` restores the full comparison for diagnostics —
    `similarity_report.py --include-consolidated` uses it to show the archive
    overlaps deliberately.
    """
    if not corpus:
        return []
    mine = body_shingles(post)
    if len(mine) < 50:  # too short to judge meaningfully
        return []
    slug = post.get("slug")
    if not include_consolidated:
        # ONE partition decides BOTH sides of the comparison. Filtering only the
        # corpus left the archive copy still reporting a BLOCK against the guide
        # it had been consolidated into — the same finding, surviving in one
        # direction. A record is a page, or it is not.
        in_corpus = any(p.get("slug") == slug for p in corpus)
        corpus = corpus_mod.public_posts(corpus)
        is_public = any(p.get("slug") == slug for p in corpus)
        if in_corpus and not is_public:
            return []                       # a retained archive record: not a page
        if corpus_mod.CONSOLIDATED_INTO in post:
            return []                       # a draft claiming to be one (also BLOCKed)
    issues: List[Dict] = []
    for other in corpus:
        if other.get("slug") == slug:
            continue
        theirs = body_shingles(other)
        if not theirs:
            continue
        union = len(mine | theirs)
        if not union:
            continue
        jac = len(mine & theirs) / union
        if jac >= SIMILARITY_FLAG_AT:
            issues.append({
                "check": "similarity",
                "severity": SEVERITY_BLOCK if jac >= SIMILARITY_BLOCK_AT else SEVERITY_FLAG,
                "span": other.get("slug", "?"),
                "detail": (f"body copy is {jac:.0%} identical to '{other.get('slug')}' "
                           f"({len(mine & theirs)} shared {SIMILARITY_SHINGLE_K}-word sequences). "
                           f"Rewrite from this page's own decision problem, or consolidate the "
                           f"two guides — do not ship near-duplicate bodies."),
            })
    return sorted(issues, key=lambda i: i["detail"], reverse=True)


# "Report Fraud" is matched CASE-SENSITIVELY because it is a brand name that is
# also an ordinary verb phrase. With re.I this pattern matched "block the card
# and report fraud" — 111 of 134 corpus findings were that false positive, and it
# broke the build by failing all three live hubs (operator review, 2026-07-27).
# The URL and phone number stay case-insensitive; they are unambiguous.
_REPORT_FRAUD_NAMED_RE = re.compile(
    r"Report\s+Fraud|(?i:reportfraud\.police\.uk)|0300\s*123\s*2040"
    r"|(?i:report\s+fraud(?=\s+(?:at|on|says|warns|advises|recommends|explains)\b))")
# An ACTIONABLE Scottish route inside a POSITIVE reporting directive.
#
# Three earlier versions were each too loose, and each one reported clean on
# text a human then had to catch:
#   v1  any occurrence of "Scotland" or "101"      -> passed "...in Scotland or."
#   v2  "Police Scotland" within 40 chars of "101" -> passed "Police Scotland
#       recorded 101 reports last month" (a statistic, not a route) and
#       "Do not report this to Police Scotland on 101" (a negated route)
# So the match now requires all three of: a reporting verb, Report Fraud, and an
# actionable Police Scotland + 101 route, in ONE sentence, with no negation
# governing that sentence.
_REPORT_VERB_RE = re.compile(r"\breport(?:s|ed|ing)?\b|\btell\b|\bcontact\b", re.I)
_SCOTLAND_ACTIONABLE_RE = re.compile(
    r"Police\s+Scotland[^.;]{0,40}\b101\b|\b101\b[^.;]{0,40}Police\s+Scotland", re.I)
# Verbs that can actually GOVERN a reporting route. "call", "ring" and "dial"
# were missing, so "Do not call Police Scotland on 101" read as a valid route
# (operator review, 2026-07-27).
_ROUTE_VERB_RE = re.compile(
    r"\b(?:report(?:s|ed|ing)?|tell(?:s|ing)?|told|contact(?:s|ed|ing)?"
    r"|call(?:s|ed|ing)?|ring(?:s|ing)?|rang|dial(?:s|led|ling|ed|ing)?"
    r"|file(?:s|d|ing)?|submit(?:s|ted|ting)?|raise(?:s|d)?|raising)\b", re.I)
_NEGATED_DIRECTIVE_RE = re.compile(
    r"\b(?:do\s+not|don['’]t|does\s+not|doesn['’]t|never|instead\s+of"
    r"|rather\s+than|no\s+need\s+to)\b", re.I)


# A contrast marker between the verb and the route flips it into a non-route:
# "Contact your bank, not Police Scotland on 101."
_ROUTE_CONTRAST_RE = re.compile(r"\bnot\b|\brather\s+than\b|\binstead\s+of\b", re.I)
# Verbs that make 101 a STATISTIC rather than a number to dial.
_ROUTE_STATISTIC_RE = re.compile(
    r"\b(?:recorded|received|logged|took|taken|handled|reported|registered|saw|counted)\b", re.I)


def _route_is_actionable(sent: str, route_m) -> bool:
    """True only if a positive route verb governs this Police Scotland + 101
    match and nothing negates or contrasts it.

    Rejects, in order (operator reviews, 2026-07-27):

      "Police Scotland recorded 101 reports last month."
          statistic — a counting verb sits inside the matched span.
      "We reported yesterday that Police Scotland recorded 101 cases."
          same, and the earlier `reported` is narrative, not a directive.
      "Do not under any circumstances ever call Police Scotland on 101."
          negated — the whole clause before the verb is scanned, not a fixed
          character window, so distance does not defeat it.
      "Contact your bank, not Police Scotland on 101."
          post-verbal contrast: the verb governs the bank, not the route.

    Accepts "Don't pay; report it to Report Fraud or Police Scotland on 101" —
    a clause boundary ends the earlier negation's reach.
    """
    # 1. A counting verb inside the match means 101 is a quantity, not a number.
    if _ROUTE_STATISTIC_RE.search(route_m.group(0)):
        return False
    lead = sent[:route_m.start()]
    # 2. Work within the clause the route sits in.
    # A colon INTRODUCES the routes rather than ending a clause — "file the loss
    # through the national fraud route: … and Police Scotland on 101" is governed
    # by "file", so treating ":" as a boundary lost the verb and false-flagged
    # four correct guides.
    boundary = max(lead.rfind(";"), lead.rfind(". "))
    clause = lead[boundary + 1:] if boundary >= 0 else lead
    verbs = list(_ROUTE_VERB_RE.finditer(clause))
    if not verbs:
        return False
    verb = verbs[-1]
    # 3. Nothing between the governing verb and the route may contrast it.
    if _ROUTE_CONTRAST_RE.search(clause[verb.end():]):
        return False
    # 4. Nothing earlier may negate that verb. A comma ends a negation's scope,
    #    so "Don't pay, end the contact, and report it to … Police Scotland on
    #    101" stays a valid route while "Do not under any circumstances ever call
    #    Police Scotland on 101" does not. The contrast rule above is what
    #    catches "contact your bank, not Police Scotland" — hence the asymmetry.
    before = clause[:verb.start()]
    if "," in before:
        before = before.rsplit(",", 1)[1]
    return not _NEGATED_DIRECTIVE_RE.search(before)


def _sentences(text: str) -> List[str]:
    # Hub and guide bodies are HTML. Without normalising tags to whitespace,
    # "…vulnerable consumers.</p><li>Report it to…" collapses to
    # "consumers.Report it to…", which the splitter cannot see as two sentences —
    # so a negation in one sentence leaked into the analysis of the next and
    # false-flagged a correct route (operator review, 2026-07-27). A space keeps
    # every character while restoring the boundary, and leaves dotted tokens like
    # reportfraud.police.uk intact inside their sentence.
    text = re.sub(r"<[^>]+>", " ", text or "")
    return [s for s in re.split(r"(?<=[.!?;])\s+", text) if s.strip()]


def _has_scottish_route(text: str) -> bool:
    """True only if some sentence positively directs the reader to Police
    Scotland on 101. Co-occurrence is not a route."""
    for sent in _sentences(text):
        if not _SCOTLAND_ACTIONABLE_RE.search(sent):
            continue
        # Only treat the ROUTE as negated when the negation governs it — i.e.
        # appears shortly before the route with a reporting verb in between
        # ("do NOT report this to Police Scotland on 101"). A negation earlier in
        # the sentence usually governs something else entirely: "DON'T pay, end
        # the contact, and report it to..." and "NEVER grant remote access, and
        # report it to..." are both correct directives, and a whole-sentence
        # negation test false-flagged them.
        route_m = _SCOTLAND_ACTIONABLE_RE.search(sent)
        if not _route_is_actionable(sent, route_m):
            continue
        # The route must be offered as an ALTERNATIVE to Report Fraud in the same
        # sentence. Without this, "Police Scotland recorded 101 reports last
        # month." satisfies the matcher — `reports` is a noun there, but the
        # verb pattern cannot tell. Requiring the pairing encodes what the
        # approved wording actually is: one instruction naming both routes.
        if not _REPORT_FRAUD_NAMED_RE.search(sent):
            continue
        if _REPORT_VERB_RE.search(sent):
            return True
    return False
# Text that is syntactically broken — usually the residue of a regex edit.
_MALFORMED_RES = (
    # "on" is deliberately EXCLUDED: it is a legitimate phrasal-verb particle at
    # sentence end ("bank a cheque and wire money on", "pass it on"), and
    # including it false-flagged mystery-shopper-scam-uk's correct description.
    (re.compile(r"\b(?:or|and|at|to)\s*[.!?]"), "a sentence ends in a dangling conjunction or preposition"),
    (re.compile(r"\b(or|and)\s+\1\b", re.I), "duplicated conjunction"),
    (re.compile(r",\s*,|\s,|\.\s*\."), "doubled or orphaned punctuation"),
    (re.compile(r"\b(Police Scotland)\b(?:[^.]{0,80}\b\1\b)"), "Police Scotland named twice in one sentence"),
)


def check_text_wellformed(post: Dict) -> List[Dict]:
    """Catch syntactically broken reader-visible text.

    Added 2026-07-27 after a bulk edit shipped two malformed quick answers that
    every property-based check passed: the clause was present, the word count
    was in range, no stale number remained — but one sentence ended "...or." and
    another spliced a reporting route into the middle of an unrelated list.
    Checking that the required token EXISTS is not the same as checking the
    sentence still reads."""
    issues: List[Dict] = []
    surfaces = [(f, str(post.get(f) or "")) for f in ("quick_answer", "description", "hero")]
    surfaces += list(_figure_fields(post))
    for field, text in surfaces:
        text = text.strip()
        if not text:
            continue
        for rx, why in _MALFORMED_RES:
            m = rx.search(text)
            if m:
                issues.append({"check": "malformed_text", "severity": SEVERITY_BLOCK,
                               "span": re.sub(r"\s+", " ", text[max(0, m.start() - 60):m.end() + 30]),
                               "detail": f"{field} is malformed — {why}. Reader-visible text must be "
                                         f"syntactically complete."})
                break
    return issues


# build.py renders only a narrow Markdown subset — backtick code spans, bare
# `/guides/slug/` auto-linking, and internal root-relative [text](/path/) links
# (6c881a5f7, 2026-07-18). Everything else survives into the page as literal
# characters: `**bold**` shows its asterisks and an EXTERNAL markdown link shows
# its brackets and URL. Both have shipped live before — 41 bold spots and 6
# broken bracket links found by hand in the 2026-07-10 sweep, which is why
# docs/project.md gotcha 34 makes the post-build greps a standing manual step.
#
# Added 2026-08-08: the 2026-08-08 pipeline draft emitted eight `**bold**`
# bullets and the gate passed it clean, because nothing in the gate looked at
# rendering at all. This moves gotcha 34's greps into the gate, where they run
# BEFORE publication rather than after. BLOCK, not FLAG: build.py cannot render
# either form, so there is no context in which it is correct.
_UNRENDERABLE_MARKUP_RES = (
    (re.compile(r"\*\*[^*\n]+\*\*"),
     "literal **bold** markdown — build.py has no bold renderer, so the asterisks reach "
     "the page. Use plain, emphasis-free prose."),
    (INVALID_MARKDOWN_LINK_RE,
     "a markdown link whose target is not a safe internal path — build.py renders only internal "
     "[text](/path/) links, so the brackets and URL reach the page. External references "
     "belong in sources_checked."),
)


def _reader_visible_fields(post: Dict):
    """(label, text) for every field whose characters reach the rendered page."""
    for f in ("title", "description", "hero", "quick_answer"):
        yield f, str(post.get(f) or "")
    yield "intro", str(post.get("intro") or "")
    for idx, item in enumerate(post.get("sections", []) or []):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            yield f"sections[{idx}] heading", str(item[0])
            yield f"sections[{idx}] body", str(item[1])
    for idx, item in enumerate(post.get("faq", []) or []):
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            yield f"faq[{idx}] question", str(item[0])
            yield f"faq[{idx}] answer", str(item[1])


def check_unrenderable_markup(post: Dict) -> List[Dict]:
    """BLOCK markup build.py cannot render, before it reaches a live page."""
    issues: List[Dict] = []
    for field, text in _reader_visible_fields(post):
        if not text:
            continue
        for rx, why in _UNRENDERABLE_MARKUP_RES:
            m = rx.search(text)
            if m:
                issues.append({"check": "unrenderable_markup", "severity": SEVERITY_BLOCK,
                               "span": re.sub(r"\s+", " ", m.group(0))[:140],
                               "detail": f"{field} contains {why}"})
                break
    return issues


# The NCSC runs THREE separate routes, and sending a reader to the wrong one
# sends their evidence somewhere that cannot act on it:
#   suspicious EMAIL   → the Suspicious Email Reporting Service mailbox
#   suspicious WEBSITE → the separate scam-website submission form
#   suspicious TEXT    → 7726, which is run by the mobile networks, not the NCSC
# The third is already guarded by _SHORTCODE_NCSC_RE. This guards the first two.
#
# Added 2026-08-08: the 2026-08-08 pipeline draft told readers to report a
# phishing LINK ("a fake login page") to the SERS mailbox. The NCSC's own
# scam-website page does not mention that mailbox anywhere. FLAG, matching
# shortcode_attribution — the same class of misrouting.
_WEBSITE_SUBJECT_RE = re.compile(
    r"\b(?:websites?|web\s?pages?|webpages?|links?|urls?|login\s+pages?)\b", re.I)
_EMAIL_SUBJECT_RE = re.compile(r"\be-?mails?\b", re.I)
# The service's own NAME contains "Email", which would otherwise read as the
# subject of the sentence and mask every single misroute. Strip it first.
_SERS_NAME_RE = re.compile(r"suspicious\s+e-?mail\s+reporting\s+service|\bSERS\b", re.I)


def _sers_email() -> str:
    """The SERS mailbox, from the canon — never hardcoded here."""
    for r in _CANON.get("official_routes", []):
        if r.get("key") == "ncsc-sers":
            return str(r.get("email") or "")
    return ""


def check_ncsc_route_scope(post: Dict) -> List[Dict]:
    """FLAG a website/link routed to the NCSC's EMAIL mailbox."""
    addr = _sers_email()
    if not addr:
        return []
    text = _post_text(post)
    issues: List[Dict] = []
    for m in re.finditer(re.escape(addr), text, re.I):
        # Bound the window at the previous sentence break. ". " (period then
        # space) is a safe boundary here precisely because URLs and the address
        # itself never contain one.
        before = text[max(0, m.start() - 220):m.start()]
        cut = before.rfind(". ")
        clause = (before[cut + 2:] if cut != -1 else before) + text[m.end():m.end() + 100].split(". ")[0]
        stripped = _SERS_NAME_RE.sub(" ", clause)
        if not _WEBSITE_SUBJECT_RE.search(stripped):
            continue                       # not about a website — correct usage
        if _EMAIL_SUBJECT_RE.search(stripped):
            continue                       # names an email too ("a link in an email")
        issues.append({
            "check": "ncsc_route_scope", "severity": SEVERITY_FLAG,
            "span": re.sub(r"\s+", " ", clause)[:140],
            "detail": (f"routes a suspicious WEBSITE or link to '{addr}', which is the NCSC's "
                       f"Suspicious Email Reporting Service — the mailbox for suspicious EMAILS. "
                       f"The NCSC's own scam-website page does not mention it. Send websites and "
                       f"links to the ncsc-scam-website route in content/sources.json instead; "
                       f"texts go to 7726, run by the mobile networks."),
        })
        break
    return issues


def _route_fields(post: Dict):
    """Every reader-visible field that can carry a reporting route, as
    (label, text) pairs. Category hubs put their routes in `intro`, section
    bodies and FAQ answers and have no `quick_answer`, so a check limited to
    `quick_answer`/`description` inspected none of a hub's prose — a hub whose
    section said only "Report it to Report Fraud on 0300 123 2040." passed
    `validate_category_hubs()` clean (operator review, 2026-07-27)."""
    yield "title", str(post.get("title") or "")
    yield "quick answer", str(post.get("quick_answer") or "")
    yield "meta description", str(post.get("description") or "")
    yield "hero", str(post.get("hero") or "")
    yield "intro", str(post.get("intro") or "")
    for head, body in (post.get("sections") or []):
        yield "section heading", str(head)
        yield f"section '{head}'", str(body)
    for q, a in structured.narrative_faq(post):
        # A question and its answer are one semantic field; never inherit
        # context from a different FAQ. Short answers can carry the recipient.
        yield f"FAQ '{q[:40]}'", str(q) + " " + str(a)
    for idx, pair in enumerate(post.get('sources_checked', []) or []):
        if (isinstance(pair, (list, tuple)) and len(pair) >= 2
                and _route_instruction(str(pair[0]))
                and (re.search(r'\b(?:you|your)\b', str(pair[0]), re.I)
                     or not re.search(r'[—:]|\b(?:how|what|where|when)\b', str(pair[0]), re.I))):
            # A normal source label is a citation; an imperative label still
            # offers the actual rendered href and must pass the same boundary.
            yield f'source[{idx}]', f'<a href="{html_escape(str(pair[1]), quote=True)}">{html_escape(str(pair[0]))}</a>'
    for idx, item in enumerate(post.get('evidence', []) or []):
        if isinstance(item, dict):
            for key in ('signal', 'finding', 'basis'):
                yield f'evidence[{idx}] {key}', str(item.get(key, ''))
    for idx, item in enumerate(post.get('message_examples', []) or []):
        if isinstance(item, dict):
            # The renderer explicitly labels message as a reconstructed scam
            # example. Its assessment and heading are editorial advice.
            for key in ('label', 'assessment'):
                yield f'message_examples[{idx}] {key}', str(item.get(key, ''))
    yield from _figure_fields(post)


# WP3C3: keep classification and destination authentication separate. A publisher
# attribution is not a field-wide waiver. All instruction destinations (including
# actual hrefs) are authenticated, even without a named organisation.
_ROUTE_ACTION_RE = re.compile(
    r"\b(?:report(?:ing|ed)?|send(?:ing)?|sent|submit(?:ting|ted)?|submission|"
    r"contact(?:ing)?|notify|notifying|call(?:ing)?|phone|telephone|dial|ring|"
    r"upload|relay|communicate|file|filing|lodge|lodging|lodged|forward(?:ing|ed)?|email(?:ing)?|"
    r"use|using|visit|go|make|making|get\s+in\s+touch)\b", re.I)
_ROUTE_OBJECT_RE = re.compile(
    r"\b(?:reports?|complaints?|loss|losses|evidence|details|fraud|scam|"
    r"helpline|hotline|reporting|form|submission)\b", re.I)
_ROUTE_REFERENCE_RE = re.compile(
    r"\b(?:it|them|us|here|there|its|their|our|this|that)\b", re.I)
_ROUTE_URL_RE = re.compile(
    r"⟦[^⟧]*⟧|[a-z][a-z0-9+.-]*:(?![;,.!?])[^\s<>\"'`)]+|"
    r"[^\s<>\"'`⟦⟧()]+@[^\s<>\"'`⟦⟧()]+|"
    r"(?<![\w@])(?:[\w-]+\.)+[a-z]{2,}(?::[0-9]+)?(?:[/?#][^\s<>\"'`)]*)?", re.I)
_ROUTE_DESCRIPTION_RE = re.compile(
    r"^\s*(?:(?:the\s+)?(?:archive|historical\s+record|suspicious\s+message)\s+"
    r"(?:quotes|says)\b|(?:the\s+)?(?:Report\s+Fraud|Police\s+Scotland)\s+"
    r"(?:(?:received|recorded|handled|published|was|were)\b|"
    r"is\s+(?:a|the)\s+(?:national\s+)?reporting\s+service\b)|"
    r"(?:the\s+)?(?:Report\s+Fraud|Police\s+Scotland)\s+"
    r"(?:guidance|website)\b.*\b(?:published|describes)\b)", re.I)
_RF_ATTRIBUTION_RE = re.compile(
    r"^\s*(?:Report\s+Fraud\s+(?:warns|recommends|advises|explains|says)\b"
    r"|According\s+to\s+Report\s+Fraud\b)", re.I)


class _RouteHTML(HTMLParser):
    """Keep link targets independently of labels; decode entities and bare hrefs."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self.parts.append(' ')
        raw = self.get_starttag_text() or ''
        if tag != 'a' and re.search(r'[:.@]', tag):
            # Guide HTML is escaped by build._inline: angle-bracket URLs are
            # visible text, not disposable markup. Retain their full token.
            self.parts.append(' ⟦' + raw[1:-1] + '⟧ ')
        if tag == 'a':
            for key, value in attrs:
                if key == 'href' and value:
                    self.parts.append(' ⟦' + value + '⟧ ')

    def handle_endtag(self, tag):
        self.parts.append(' ')

    def handle_data(self, data):
        self.parts.append(data)


def _route_text(text):
    parser = _RouteHTML()
    parser.feed(text or '')
    parser.close()
    # HTMLParser already decoded character references once, as a browser does.
    # Decoding again could authenticate a different host from the actual href.
    text = ''.join(parser.parts)
    return re.sub(r'\[([^\]\n]+)\]\(([^)\n]+)\)', r'\1 ⟦\2⟧', text)


def _route_destinations(text):
    """Return spans and values. Consume whole URLs before looking for mail/phones."""
    found = []
    for m in _ROUTE_URL_RE.finditer(text):
        value = m.group().rstrip('.,;:!')
        kind = 'url'
        if value.startswith('⟦'):
            kind, value = 'link', value[1:-1]
        if value.lower().startswith('mailto:'):
            kind, value = 'email', value[7:]
        elif value.lower().startswith('tel:'):
            kind, value = 'phone', value[4:]
        elif '@' in value and '://' not in value:
            kind = 'email'
        found.append((m.start(), m.end(), kind, value))
    for m in _PHONE_RE.finditer(text):
        if not any(a <= m.start() < b for a, b, _, _ in found):
            found.append((m.start(), m.end(), 'phone', m.group().strip()))
    # Reporting shortcodes need the same owner check as long phone numbers.
    # A means phrase ("using 60599") is not covered by the legacy to-only
    # shortcode guard. Extract directed numeric recipients, not arbitrary dates.
    for m in re.finditer(r'\b(?:to|via|through|using|dial|call)\s+`?(\d{3,6})(?!\d)', text, re.I):
        a, b = m.span(1)
        if not any(x <= a < y for x, y, _, _ in found):
            found.append((a, b, 'phone', m.group(1)))
    return sorted(found)


def _route_prose(text):
    # Hosts, URL paths and the organisation's name are not reporting verbs.
    for a, b, _, _ in reversed(_route_destinations(text)):
        text = text[:a] + ' ' * (b - a) + text[b:]
    return re.sub(r'\bReport\s+Fraud\b', lambda m: ' ' * len(m.group()), text, flags=re.I)


def _route_instruction(text):
    prose = _route_prose(text)
    # Negating delay still instructs reporting; negate actions, not sentences.
    prose = re.sub(r'\bdo\s+not\s+(?:wait|delay|hesitate)\s+to\s+', '', prose, flags=re.I)
    descriptive = bool(_ROUTE_DESCRIPTION_RE.search(text))
    # Destination-directed report objects also identify the semantic action
    # when the verb is an unfamiliar paraphrase ("relay your complaint ...").
    # This is deliberately grammatical, not a list of approved prose strings.
    directed_object = re.search(
        r'\b(?:your|a|the)\s+(?:fraud\s+)?(?:report|complaint|loss|evidence|details)\b'
        r'.*\b(?:to|with|via|through)\s+(?:it|them|us|here|there|⟦|https?:|[\w.+-]+@)', text, re.I)
    advisory = re.search(r'\b(?:advises|recommends|you\s+(?:should|can|must))\b', prose, re.I)
    imperative_object = re.match(r'^\s*[a-z]+\s+your\s+(?:report|complaint|loss|evidence|details)\b', prose, re.I)
    if (directed_object and (advisory or imperative_object)
            and not descriptive and not _NEGATED_DIRECTIVE_RE.search(prose)):
        return True
    for action in _ROUTE_ACTION_RE.finditer(prose):
        if action.group().lower() in ('phone', 'telephone') and re.match(r'\s+number\b', prose[action.end():], re.I):
            continue
        if action.group().lower() == 'email' and re.match(r'\s*(?:and|or|[,.;]|$)', prose[action.end():], re.I):
            continue
        lead = prose[:action.start()]
        clause = re.split(r'[;,]|\b(?:but|then)\b', lead, flags=re.I)[-1]
        if _NEGATED_DIRECTIVE_RE.search(clause):
            continue
        # A verb must occupy a directive/complement position. This separates
        # "file a report" from "already have the file", and "use this form"
        # from "check a breach using a lookup service".
        governs = (not lead.strip(' -•(\r\n\t') or bool(re.search(
            r"(?:[,;:]|\b(?:to|should|can|could|may|might|must|please|and|or|then|otherwise|"
            r"advises|recommends|says|you|I|we|by|be))\s*"
            r"(?:(?:also|still|now|directly|immediately|safely|simply|then|[a-z]+ly)\s+)*$", lead, re.I)))
        if not governs:
            continue
        if descriptive and not re.search(r'\b(?:you|should|can|must|please)\b|[;,]', lead, re.I):
            continue
        # Emotional support and lookup/verification are different actions from
        # submitting a report. They are not authenticated as reporting routes.
        if (action.group().lower() in ('contact', 'call')
                and re.search(r'\b(?:emotional\s+support|confidential\s+support)\b', lead, re.I)):
            continue
        return True
    # Noun phrases explicitly offering a destination, without a finite verb.
    return (not descriptive and not _NEGATED_DIRECTIVE_RE.search(prose)
            and bool(_route_destinations(text)) and bool(re.search(
                r"^\s*(?:(?:for\s+)?reporting\b|(?:its|their|our|the|this)\s+"
                r"(?:reporting\s+(?:email|address|form)|helpline|report\s+form))"
                r"|\b(?:recommends|advises)\s*$", prose.strip(' .'), re.I)))


def _report_fraud_advice_only(sent: str, following: List[str]) -> bool:
    """Only affirmative attribution/description can be exempt; ambiguity blocks.

    Reporting actions are recognised independently of speech verbs, including
    inflections and complaint/contact paraphrases. Follow-on references inherit
    the agency context; unrelated prevention advice does not.
    """
    if not (_RF_ATTRIBUTION_RE.match(sent) or _ROUTE_DESCRIPTION_RE.match(sent)):
        return False
    if (_route_instruction(sent)
            or re.search(r'\b(?:UK[- ]wide|Scotland|Scottish)\b|\b(?:its|their|our)\s+(?:online|form|service|website|helpline)\b', sent, re.I)):
        return False
    for other in following:
        if _route_instruction(other) and (
                _ROUTE_OBJECT_RE.search(_route_prose(other))
                or _ROUTE_REFERENCE_RE.search(_route_prose(other))
                or _route_destinations(other)):
            # Explicit contact with a different actor is not an anaphoric
            # instruction to report to the publisher of the preceding advice.
            if re.search(r'\b(?:contact|call)\s+(?:your\s+bank|support)\b', other, re.I) and not _route_destinations(other):
                continue
            return False
    return True


def _reporting_context(text):
    prose = _route_prose(text)
    return bool(re.search(r'\bcontact\b.*\b(?:about|regarding)\s+(?:the\s+)?(?:fraud|scam)\b', prose, re.I) or re.search(
        r"\b(?:report(?:ing|ed)?|forward(?:ing|ed)?|submit(?:ting|ted)?|lodge|lodging|lodged|"
        r"suspicious\b.*\baccount|complaint|notify|notifying|get\s+in\s+touch|Scotland|Scottish)\b|"
        r"^\s*(?:(?:you|we)\s+(?:can|should|must)\s+(?:also\s+)?)?send(?:ing)?\b"
        r"\s+(?:(?:a|the|your|any)\s+)?(?:suspicious|phishing|scam|report|evidence|details)\b|"
        r"\b(?:fraud|scam)\s+(?:phone\s+)?number\b|"
        r"\b(?:this|its|their|the)\s+(?:reporting\s+)?form\b|"
        r"\b(?:loss|evidence)\b.*\b(?:to|via|through|at|here)\b",
        prose, re.I) or re.search(r'\bReport\s+Fraud\b', text, re.I)
        or any(r.get('role') in ('police-report', 'phishing-report', 'website-report', 'consumer-advice')
               for _, _, r in _route_names(text, _CANON['official_routes'])))


def _route_names(text, routes):
    """Organisation identities from canon prose, never substrings inside URLs."""
    masked = text
    for a, b, _, _ in reversed(_route_destinations(text)):
        masked = masked[:a] + ' ' * (b - a) + masked[b:]
    matches = []
    for route in routes:
        name = (reporting.POLICIES[route['key']][0] if route['key'] in reporting.POLICIES else route.get('brand')) or re.split(
            r'\s+(?:phishing|scam[- ]|customer|general|suspicious)',
            route['name'], maxsplit=1, flags=re.I)[0]
        if route['key'] == 'fca-firm-checker':
            name = 'FCA'
        aliases = {name}
        if route['key'] in ('ncsc-sers', 'ncsc-scam-website'):
            aliases.add('National Cyber Security Centre')
        if route['key'] == 'fca-firm-checker':
            aliases.add('Financial Conduct Authority')
        for alias in aliases:
            for m in re.finditer(r'(?<!\w)' + re.escape(alias) + r'(?!\w)', masked, re.I):
                matches.append((m.start(), m.end(), route))
    # A full organisation name wins over a nested generic alias (Police).
    matches = [m for m in matches if not any(n[0] <= m[0] and m[1] < n[1] for n in matches)]
    return sorted(matches, key=lambda x: x[0])


def _destination_matches(kind, value, route):
    """Identity-only compatibility helper; never a service authorization."""
    d = reporting.normalize(kind, value)
    return d is not None and any(d == reporting.normalize(k, route[f])
        for f, k in (('report_url', 'url'), ('info_url', 'url'), ('email', 'email'),
                     ('phone', 'phone'), ('phone_welsh', 'phone'), ('sms', 'shortcode')) if route.get(f))


def _number_source_reference(clause, start, kind):
    """Classify number-lookup grammar; this does not establish source trust.

    Match only the immediately governing noun phrase. The caller authenticates
    the exact source URL and owner separately; actual phone values always use
    the reporting canon. Link labels never replace their actual targets.
    """
    if kind not in ('url', 'link'):
        return False
    if not re.search(r'\b(?:call(?:ing)?|phone|telephone|dial|ring|(?:official\s+)?fraud\s+number)\b',
                     _route_prose(clause[:start]), re.I):
        return False
    prefix = clause[:start].rstrip(' `')
    adjacent = _route_destinations(prefix)
    if adjacent:
        a, b, previous_kind, _ = adjacent[-1]
        if previous_kind in ('url', 'link') and not prefix[b:].strip():
            # HTML puts the href before its label; Markdown puts it after.
            # Both values still authenticate separately against the same
            # number-source contract, so neither can hide a hostile partner.
            prefix = prefix[:a].rstrip(' `')
    return bool(re.search(
        r'\bnumber\s+(?:published\s+(?:in\s+(?:its\s+own\s+)?'
        r'(?:scam-reporting\s+)?guidance\s+)?)?on\s*$',
        prefix, re.I))


def _explicit_recipient(clause, names):
    """Bind 'to OWNER using MEANS' before inspecting names in the means.

    Return None if no named recipient is stated; an unknown named
    recipient yields an unmatchable record rather than global canon fallback.
    """
    masked = clause
    for a, b, _, _ in reversed(_route_destinations(clause)):
        masked = masked[:a] + ' ' * (b - a) + masked[b:]
    direct = re.search(r'\b(?:contact|notify|call|ring|phone)\s+(?:the\s+)?'
                       r'([A-Za-z][A-Za-z ]*?)(?=\s+(?:about|regarding|using|via|through|at|on)\b|[,;]|$)', masked, re.I)
    if direct and re.search(r'(?:^|[,;:]|\b(?:to|can|may|should|must|then|and|or))\s*$', masked[:direct.start()], re.I):
        phrase = direct.group(1).strip()
        if phrase.casefold() not in ('it', 'them', 'us', 'its official fraud number') and not re.search(r'\b(?:number|phone|to|by)\b', phrase, re.I):
            identified = [r for a, b, r in names if direct.start(1) <= a < direct.end(1)]
            return identified or [{'key': 'unverified-recipient', 'name': phrase}]
    for m in re.finditer(r'\b(?:to|with)\s+(?:the\s+)?([^,;:.!?]+?)(?=\s+(?:using|via|through|at|on)\b|[.,;:!?]|$)', masked, re.I):
        if not re.match(r'\s+(?:using|via|through|at|on)\b', masked[m.end(1):], re.I):
            continue
        identified = [r for a, b, r in names if m.start(1) <= a < m.end(1)]
        if identified:
            first = min(a for a, b, r in names if m.start(1) <= a < m.end(1))
            return [r for a, b, r in names if a == first]
        phrase = m.group(1).strip()
        if (phrase and not re.search(r'\b(?:number|parcel|standard|report|forward)\b', phrase, re.I) and not re.match(
                r'(?:this|that|them|it|us|me|you|here|there|get|report|police|the\s+address)$', phrase, re.I)):
            return [{'key': 'unverified-recipient', 'name': phrase}]
    return None


def _request_scope(clause, previous, following, label):
    """Prose adapter only: produce typed scope, never an authorization decision.

    Local explicit objects outrank adjacent context. References may inherit at
    most two sentences in the same field/FAQ; article titles cannot invent a
    missing reporting purpose. Additional service claims are separate purposes.
    """
    prose = _route_prose(clause)
    prose = re.sub(r'\bemail\s+(?=(?:it|them|those)\b)', 'send ', prose, flags=re.I)
    reference = bool(re.search(
        r'\b(?:report|forward|send|email)\s+(?:it|them|those|this|that|fakes|the\s+(?:fake|scam))'
        r'(?=\s+(?:free\s+)?(?:to|at|with|via|through|using|as\s+an?\s+attachment)\b|[.,;:]|$)', prose, re.I))
    scope_free = re.sub(r'^\s*(?:In|For)\b.*?,\s*(?=use\b)', '', prose, flags=re.I)
    short = not re.sub(r'\b(?:through|via|at|using|to|on|use|this|that|the|its|form|route|service|address|is|contact|options)\b', '', scope_free, flags=re.I).strip(' .:`()')
    bare_contact = bool(re.fullmatch(r'\s*(?:notify|contact)\s+[A-Z][A-Za-z ]*?\s+(?:through|via|using|at)\s*[ .`]*', prose, re.I))
    context = prose
    if re.search(r'\bReport\s+Fraud\b', clause, re.I):
        context += ' crime'
    local_purpose = reporting.purposes(context)
    inherit = (reference and local_purpose <= {'crime', 'unknown'}) or short or bare_contact
    if re.search(r'\bReport\s+Fraud\b', clause, re.I):
        inherit = False
    if inherit and not re.search(r'\b(?:for(?!\s+free\b)|about|regarding)\b', prose, re.I):
        for prior in reversed(previous[-2:]):
            candidate = _route_prose(prior)
            if reporting.purposes(candidate) not in (frozenset({'unknown'}), frozenset({'crime'})):
                context += ' ' + candidate
                break
        else:
            context += ' ' + label
    # Same-FAQ questions and section labels can resolve an explicit "report
    # suspected illegal sellers", but never an explicitly different object.
    if re.search(r'\breport\s+(?:suspected\s+)?illegal\s+sellers\s+to\b', prose, re.I):
        context += ' ' + label + ' ' + ' '.join(_route_prose(s) for s in previous[-2:])
    if (re.match(r'^\s*(?:to|with)\b', prose, re.I) and previous
            and reporting.purposes(context) == frozenset({'unknown'})):
        context += ' ' + _route_prose(previous[-1])
        if reporting.purposes(context) == frozenset({'unknown'}):
            context += ' ' + label
    if reporting.purposes(prose) == frozenset({'message'}) and previous and reporting.purposes(_route_prose(previous[-1])) == frozenset({'text'}):
        context += ' ' + _route_prose(previous[-1])
    purpose = reporting.purposes(context)
    if purpose == frozenset({'message'}):
        context_subject = reporting.purposes(label)
        if context_subject in (frozenset({'email'}), frozenset({'text'})):
            purpose = context_subject
    # Retain additional service/outcome assertions as separate, unsupported
    # purposes. This is a positive grammar, not a blacklist of outcome verbs.
    claims = []
    ends = [b for _, b, _, _ in _route_destinations(clause)]
    tail = prose[max(ends, default=len(prose)):]
    outcome = re.search(r'\b(?:and|so)\b.*\b(?:will|can|shall)\b.*', tail, re.I)
    if outcome:
        claims.append(outcome.group())
    trailing = re.search(r'\bto\s+(?:get|recover|claim|obtain|authenticate|verify|ensure|have)\b.*', tail, re.I)
    if trailing:
        claims.append(trailing.group())
    for sentence in following[:2]:
        if _route_destinations(sentence):
            break  # a new route owns its own following claims
        plain = _route_prose(sentence).strip()
        if re.match(r'^(?:(?:then|you\s+(?:can|should|must|may))\s+)*(?:(?:this|that)\s+(?:route|service)|this\s+(?:lets|is\s+for)|it|use\s+(?:this|that)|the\s+(?:route|service)|ask\s+SHEIN|SHEIN\s+(?:will|can|shall))\b', plain, re.I):
            claims.append(plain)
        elif re.match(r'^(?:the\s+(?:brand|shop|company|team)|[A-Z][A-Za-z]+)\s+(?:will|can|shall)\b', plain, re.I):
            current_names = _route_names(clause, _CANON['official_routes'] + _CANON.get('verified_org_contacts', []))
            if plain.lower().startswith('the ') or any(re.match(re.escape(r.get('brand', '')) + r'\s+', plain, re.I) for _, _, r in current_names if r.get('brand')):
                claims.append(plain)
    for claim in claims:
        if not reporting.attached_claims_supported(claim):
            if re.search(r'\b(?:reports?\b.*\b(?:to|contact)|takes\s+reports|route\s+for\s+reporting|network\s+can\s+investigate)\b', claim, re.I):
                extra = reporting.purposes(claim)
                if re.search(r'\bnetwork\s+can\s+investigate\b', claim, re.I):
                    extra = frozenset({'text'})
                if extra == frozenset({'message'}) and purpose in (frozenset({'text'}), frozenset({'email'})):
                    extra = purpose
                purpose |= extra
            else:
                purpose |= {'unsupported-service-claim'}
    # A local nation condition is independent of an adjacent correct route.
    # Organisation names (Police Scotland) are not audience conditions.
    def condition(text, *, trailing_audience=False):
        t = _route_prose(text)
        t = re.sub(r'\b(?:Police\s+Scotland|Advice\s+Direct\s+Scotland|Victim\s+Support\s+Scotland)\b', '', t, flags=re.I)
        t = re.sub(r'\b(?:not|never)\s+(?:a\s+)?(?:global|worldwide|international)\b', '', t, flags=re.I)
        pieces = re.findall(r'\b(?:Northern\s+Ireland|United\s+Kingdom|Great\s+Britain|UK|GB|NI|England|Wales|Scotland|Scottish|Scots|English|Welsh|global|worldwide|international)\b', t, re.I)
        # Locations attached to the audience/condition, independent of the
        # audience noun, plus residence declarations and same-FAQ questions.
        for m in re.finditer(r'(?:(?:^|\bif)\s*(?:in|(?:for|if)\b[^,.;!?]*?\b(?:in|from|outside|of))|\b(?:live|reside|based)\s+in)\s+(?:the\s+)?([^,.;!?]+)', t, re.I):
            place = re.split(r'\b(?:report|notify|contact|can|should|must|may)\b', m.group(1), flags=re.I)[0]
            pieces.append(('outside ' if 'outside' in m.group().lower() else 'in ') + place)
        for m in re.finditer(r'\bif\b[^,.;!?]*?\b(?:in|from|outside)\s+(?:the\s+)?([^,.;!?]+)', t, re.I):
            place = re.split(r'\b(?:report|notify|contact|can|should|must|may)\b', m.group(1), flags=re.I)[0]
            pieces.append('in ' + place)
        result = reporting.jurisdiction(' '.join(pieces))
        lead = re.match(r'^\s*for\s+([^,.;!?]+)', t, re.I)
        if lead and not result and not re.search(r'\b(?:scam|fraud|phishing|email|text|SMS|report|reporting|complaint|advice|support|refund|claim|account|medicine|loss|counterfeit|free)\b', lead.group(1), re.I):
            # Unknown explicit audience/condition is not an absent scope.
            result = frozenset({'unknown'})
        # A trailing audience is still a scope restriction; do not drop it
        # merely because the destination precedes it. Apply this to the local
        # action and its attached claims, not arbitrary earlier prevention
        # advice such as changing account passwords from a different device.
        if trailing_audience:
            for m in re.finditer(r'\bfor\s+[^,.;!?]*?\b(?:in|from|outside)\s+(?:the\s+)?([^,.;!?]+)', t, re.I):
                place = re.split(r'\b(?:report|notify|contact|can|should|must|may)\b', m.group(1), flags=re.I)[0]
                result |= reporting.jurisdiction(('outside ' if 'outside' in m.group().lower() else 'in ') + place)
        return result
    nation = condition(prose, trailing_audience=True)
    if not nation:
        for prior in reversed(previous[-2:]):
            # Inherit conditions, not jurisdiction belonging to a completed
            # independent instruction with its own destination.
            if (_route_instruction(prior) or _route_destinations(prior)) and not prior.rstrip().endswith('?'):
                continue
            nation = condition(prior)
            if prior.rstrip().endswith('?') and nation == reporting.UK:
                nation = frozenset()  # a UK-wide FAQ asks for the national alternatives
            if nation:
                break
    for claim in claims:
        if re.search(r'\b(?:for|in|global|worldwide|international)\b', claim, re.I):
            nation |= condition(claim, trailing_audience=True)
    return frozenset(purpose), frozenset(nation)


def _request_owners(owners):
    if not owners:
        return None
    return frozenset((reporting.POLICIES[r['key']][0] if r['key'] in reporting.POLICIES
                      else r.get('brand', 'unknown')).casefold() for r in owners)


def _number_owner(clause, source):
    """The owner of a number is not the publisher of the preceding advice."""
    prose = _route_prose(clause)
    m = re.search(r"\b(?:call|calling|dial|ring|use|using|or)\s+(?:the\s+)?(?:official\s+)?"
                  r"([A-Za-z][A-Za-z ]*?)(?:[’']s)?\s+(?:official\s+)?(?:fraud\s+)?number\b", prose, re.I)
    if m:
        owner = re.sub(r'^(?:by\s+calling|using)\s+', '', m.group(1).strip(), flags=re.I)
        if owner.casefold() not in ('its', 'their', 'the', 'official', 'fraud', 'using the'):
            return frozenset({owner.casefold()})
    names = _route_names(clause, _CANON.get('verified_number_sources', []))
    if names:
        return frozenset(r['brand'].casefold() for _, _, r in names)
    if source.get('requires_named_owner'):
        return frozenset({'unknown'})
    return None


def check_report_fraud_destinations(post: Dict) -> List[Dict]:
    """Authenticate all reporting instructions, retaining the old public API.

    Analyse clauses in either direction and carry bounded same-field context
    across adjacent sentences. Each new named agency owns its local clause;
    unlabelled routes must still match a verified destination. No instruction
    is trusted simply because an official organisation appears somewhere nearby.
    """
    routes = _CANON['official_routes'] + _CANON.get('verified_org_contacts', [])
    contracts = reporting.contracts_from_canon(_CANON)
    # Ownership metadata for the canon's two legacy, independently verified mailboxes.
    routes += [{'key': c.service, 'brand': c.organisation, 'name': c.organisation}
               for c in contracts if c.service.startswith('legacy-')]
    issues = []
    for label, raw in _route_fields(post):
        sents = _sentences(re.sub(r'\n\s*[-•]\s*', '; ', _route_text(raw)))
        for i, sent in enumerate(sents):
            # Retain all branches of national alternatives; never discard the
            # remainder after a Police Scotland mention.
            sent = re.sub(r'\((?:or\s+)?(?=(?:in\s+Scotland|Police\s+Scotland)\b)', '; ', sent, flags=re.I)
            clauses = re.split(
                r';\s*|(?:—\s*|,\s*(?:(?:and|or|then)\s+)?|\s+(?:and|or)\s+)'
                r'(?=(?:otherwise\s+)?(?:(?:in\s+Scotland|if\s+by\s+(?:email|text))\b|Citizens\s+Advice|Advice\s+Direct\s+Scotland|Consumerline|contact|notify|report|submit|send|use|call|dial|forward|email|'
                r'(?:consider\s+reporting)|(?:any\s+)?loss|(?:a\s+)?(?:(?:scam|suspicious)\s+)?(?:SMS\s+)?texts?|'
                r'(?:a\s+)?(?:(?:suspicious|scam|phishing)\s+)?emails?|Police\s+Scotland|to\s+\w+|log\s+the\s+case)\b)',
                sent, flags=re.I)
            for clause_index, clause in enumerate(clauses):
                destinations = _route_destinations(clause)
                if not destinations:
                    continue
                instruction = _route_instruction(clause)
                if clause_index and _reporting_context(clauses[0]) and re.match(r'^\s*(?:Citizens\s+Advice|Advice\s+Direct\s+Scotland|Consumerline)\b', clause, re.I):
                    instruction = True
                previous = sents[max(0, i - 2):i]
                if clause_index:
                    previous = previous + [clauses[clause_index - 1]]
                    # Preserve the purpose/condition of a leading dependent
                    # clause when splitting coordinated reporting alternatives.
                    prefix = clauses[0]
                    if re.match(r'^\s*(?:For|If|To)\b', prefix, re.I):
                        instruction = _route_instruction(prefix + ', ' + clause)
                if instruction and not _reporting_context(clause):
                    instruction = ((clause_index > 0 and _reporting_context(clauses[0])) or
                                   (any(_reporting_context(s) for s in previous) and bool(
                                       (re.search(r'\b(?:its|their|our|here|there|this\s+form)\b', _route_prose(clause), re.I) or
                                        re.fullmatch(r'\s*use\s*(?:(?:this|that|the|its)\s+(?:form|route|service))?[ .`]*', _route_prose(clause), re.I)))))
                if not instruction:
                    # A separate destination sentence completes the previous
                    # instruction, but a new source citation cannot inherit it.
                    prose = _route_prose(clause).strip(' .,:;()[]`')
                    instruction = (any(_route_instruction(s) and _reporting_context(s) for s in previous)
                                   and (not prose or (destinations[0][0] == len(clause) - len(clause.lstrip())
                                                      and re.fullmatch(r'in\s+Scotland[, .]*', prose, re.I)) or bool(re.match(
                                       r'^(?:(?:through|via|at|using|to|on)\b|(?:the|its|their|our|this)\s+(?:form|address|reporting|website|email|helpline)\b)', prose, re.I))))
                if not instruction and (not _route_prose(clause).strip(' .,:;()[]`') or
                        re.search(r'\b(?:reporting|portal|form|address|helpline)\b', _route_prose(clause), re.I)):
                    # An isolated link can precede the instruction referring to
                    # it. This is the same binding as a following link, in reverse.
                    following = sents[i + 1:i + 3]
                    if (following and _route_instruction(following[0]) and _reporting_context(following[0])
                            and not _route_destinations(following[0])
                            and re.search(r'\b(?:here|there|this\s+(?:form|portal)|that\s+(?:form|portal)|their\s+site)\b', following[0], re.I)):
                        instruction = True
                        previous = previous + [following[0]] if not _route_names(clause, routes) else previous
                # Offered alternatives remain instructions even in declarative form.
                if not instruction and re.search(r'\b(?:alternatively|available\s+for\s+reports|reporting\s+(?:portal|form|address))\b', _route_prose(clause), re.I):
                    instruction = True
                if not instruction:
                    continue
                names = _route_names(clause, routes)
                for a, b, kind, value in destinations:
                    # The object being reported is not the recipient. Require
                    # explicit object grammar, not a reassuring label on a link.
                    if (kind == 'url' and re.search(r'\b(?:fake|suspicious|scam)\s*$', clause[:a], re.I)
                            and re.match(r'\s+(?:websites?|sites?|domains?)\s+to\b', clause[b:], re.I)):
                        continue
                    # An explanatory citation after a completed, authenticated
                    # recipient is distinct from using a form/number found there.
                    if (re.search(r',\s*as\s+(?:explained|described)\s+(?:in|on)\s*$', clause[:a], re.I)
                            and not re.search(r'\bto\s+(?:report|submit|send|forward|lodge|contact|call)\b', clause[b:], re.I)
                            and any(x[1] <= a and any(_destination_matches(x[2], x[3], r)
                                    for r in routes) for x in destinations)):
                        continue
                    # Reading/checking an explanatory guide is not submitting
                    # evidence to it. Require descriptive grammar, not merely
                    # a reassuring link label ("official reporting guide").
                    if (re.search(r'\b(?:guide|checklist|dataset)\b', clause, re.I)
                            and re.search(r'\b(?:explains|covers|sets\s+out|walks\s+through)\b', clause, re.I)
                            and not re.search(r'\b(?:report|submit|send|forward|lodge|contact|call|upload|notify)\b', _route_prose(clause), re.I)):
                        continue
                    if (re.search(r'\buse\s+(?:our|the|this)\b[^.]*\b(?:guide|checklist)\s*$', clause[:a].rstrip(), re.I)
                            and not _reporting_context(clause[:a])
                            and not re.search(r'\bto\s+(?:report|submit|send|lodge)\b', clause[b:], re.I)):
                        continue
                    if (re.match(r"(?:[’']s)?\s+(?:lists|says|guidance|consumer-rights)\b", clause[b:], re.I)
                            and not (_route_instruction(clause[:a]) and _reporting_context(clause[:a]))):
                        continue
                    before = [n for n in names if n[1] <= a]
                    after = [n for n in names if n[0] >= b]
                    # A means phrase retains the recipient of the action it modifies.
                    actions = [m for m in _ROUTE_ACTION_RE.finditer(_route_prose(clause[:a]))
                               if m.group().lower() != 'using']
                    if actions:
                        action_start = actions[-1].start()
                        before = [n for n in before if n[0] >= action_start or
                                  re.search(r'\b(?:says|advises|recommends|asks|their|its)\b', clause[n[1]:action_start], re.I)]
                    owners = []
                    if before:
                        last = max(n[0] for n in before)
                        owners = [n[2] for n in before if n[0] == last]
                    elif after and not re.search(r'\b(?:and|or|then|if)\b', clause[b:after[0][0]], re.I):
                        first = min(n[0] for n in after)
                        owners = [n[2] for n in after if n[0] == first]
                    elif previous and (re.search(r'\b(?:(?:to|with|via|through)\s+(?:it|them|us)|(?:its|their|our)\s+(?:online|form|service|website|email|helpline)|here|there(?!\s+is))\b', _route_prose(clause), re.I)
                                       or (clause_index == 0 and re.match(r'^\s*(?:through|via|at|using|to|on|use)\b', clause, re.I))
                                       or (previous[-1].rstrip().endswith('?') and re.match(r'^\s*the\s+address\b', clause, re.I))
                                       or (re.match(r'^\s*(?:report|submit|lodge)\b', clause, re.I)
                                           and re.search(r'\b(?:report|submit|lodge)\s+(?:it|the\s+(?:loss|complaint))\b', _route_prose(clause), re.I))):
                        inherited = _route_names(previous[-1], routes)
                        if inherited:
                            last = max(n[0] for n in inherited)
                            owners = [n[2] for n in inherited if n[0] == last]
                    # Global mailbox membership must not bypass an evidenced
                    # owner/service contract on the same mailbox.
                    if after and re.match(r'\s+for\s+', clause[b:after[0][0]], re.I):
                        first = min(n[0] for n in after)
                        owners = [n[2] for n in after if n[0] == first]
                    earlier = [end for start, end, _, _ in destinations if end <= a]
                    owner_start = max(earlier, default=0)
                    explicit = _explicit_recipient(clause[owner_start:a], [(x-owner_start,y-owner_start,r) for x,y,r in names if x >= owner_start])
                    # Carry a recipient only into a dependent means/reference,
                    # never into a fresh coordinated object such as an SMS.
                    dependent = bool(re.match(
                        r'^\s*(?:(?:using|via|through|at|on|dial|call|ring|use)\b|'
                        r'(?:report|forward|send|email)\s+(?:it|them|this|that)\b)',
                        _route_prose(clause), re.I))
                    if (explicit is None and not owners and dependent and clause_index and not _route_destinations(clauses[clause_index - 1])
                            and _route_instruction(clauses[clause_index - 1]) and _reporting_context(clauses[clause_index - 1])):
                        prior = clauses[clause_index - 1]
                        explicit = _explicit_recipient(prior, _route_names(prior, routes))
                    if explicit is None and not owners and previous and re.search(r'\b(?:to\s+(?:them|it)|their\s+(?:site|form)|use)\b', _route_prose(clause), re.I):
                        for prior in reversed(previous[-2:]):
                            m = re.search(r'\b(?:to|contact|notify)\s+([A-Za-z][A-Za-z ]*?)\s*[.!?]?$', _route_prose(prior))
                            if m and m.group(1).strip().casefold() not in ('it', 'them', 'us'):
                                named = _route_names(prior, routes)
                                owners = [r for _, _, r in named] or [{'key': 'unverified-recipient', 'name': m.group(1)}]
                                break
                    if explicit is not None:
                        owners = explicit
                    scope = clause
                    if (clause_index == 1 and not _route_destinations(clauses[0])
                            and not _route_instruction(clauses[0])):
                        scope = clauses[0] + ', ' + clause
                    if recipient_prefix := re.search(r'\bto\s+Police\s+Scotland\b', scope, re.I):
                        if a >= recipient_prefix.end():
                            scope = scope[recipient_prefix.start():]
                    # An object-free dialing alternative belongs to its local
                    # preceding instruction. Do not use a distant field/title.
                    if (dependent and clause_index and
                            reporting.purposes(_route_prose(scope)) == frozenset({'unknown'}) and
                            not _route_destinations(clauses[clause_index - 1])):
                        scope = clauses[clause_index - 1] + ', ' + scope
                    purpose, nation = _request_scope(scope, previous, sents[i + 1:i + 3], label)
                    recipient = _request_owners(owners)
                    mode = 'intake'
                    destination = reporting.normalize(kind, value)
                    if _number_source_reference(clause, a, kind):
                        mode = 'number-lookup'
                        purpose = frozenset({'number-lookup'})
                        source = next((r for r in _CANON.get('verified_number_sources', [])
                                       if reporting.normalize('url', r['navigation_url']) == destination), {})
                        recipient = _number_owner(clause, source)
                        if any(_route_instruction(s) and re.search(r'\b(?:report|submit|send|forward|lodge)\b.*\b(?:there|here|this\s+route)\b', s, re.I)
                               for s in sents[i + 1:i + 3]):
                            purpose |= {'crime'}
                    request = reporting.Request(destination, recipient, purpose, nation, mode)
                    allowed, reason, services = reporting.authorize(request, contracts)
                    rf = recipient == frozenset({'report fraud'})
                    if reason == 'jurisdiction-mismatch' and rf and 'scotland' in nation:
                        issues.append({'check': 'scotland_routing', 'severity': SEVERITY_BLOCK,
                                       'span': clause, 'detail': f'the {label} directs Scottish readers to Report Fraud.'})
                    if not allowed:
                        issues.append({'check': 'report_fraud_destination' if rf else 'reporting_destination',
                                       'severity': SEVERITY_BLOCK, 'span': value,
                                       'detail': f"the {label} offers an unsupported reporting {kind}: {reason}; "
                                                 f"owner={sorted(recipient) if recipient is not None else 'unnamed'}, "
                                                 f"purpose={sorted(purpose)}, jurisdiction={sorted(nation)}, mode={mode}."})

    return issues


def _field_routes_scotland(text: str) -> bool:
    """True if every reporting mention of Report Fraud in this field is served by an
    actionable Police Scotland + 101 route, in that sentence or the one
    immediately after it.

    The adjacent-sentence allowance exists because the operator's own prescribed
    GUIDE BODY wording is deliberately two sentences —

        "Report Fraud covers England, Wales and Northern Ireland. If you live in
         Scotland or the crime happened there, contact Police Scotland on 101."

    — so a strict same-sentence rule would flag the approved copy. The window is
    two sentences, because the approved GUIDE form puts the instruction first and
    the route last:

        "Report it to Report Fraud. Report Fraud covers England, Wales and
         Northern Ireland. If you live in Scotland ... Police Scotland on 101."

    The window never crosses a field, so a route buried in a later section or FAQ
    still fails.

    EVERY reporting mention must be served. Recognised non-routing advice
    attributions are assessed individually, not exempted field-wide.
    An earlier version short-circuited on the
    first canonical scope+route pair and returned True for the whole field, so a
    later unpaired mention in the same field was never inspected —

        "Report Fraud covers England, Wales and Northern Ireland. In Scotland,
         contact Police Scotland on 101. Later, report the loss to Report Fraud."

    — passed despite the third sentence stranding a Scottish reader (operator
    review, 2026-07-27). The per-mention loop below already accepts the approved
    two-sentence form via its own window, so that shortcut was redundant as well
    as unsound; it is deliberately not reinstated.
    """
    sents = _sentences(_route_text(text))

    for i, sent in enumerate(sents):
        if not _REPORT_FRAUD_NAMED_RE.search(sent):
            continue
        if _report_fraud_advice_only(sent, sents[i + 1:i + 3]):
            continue
        window = [sent] + (sents[i + 1:i + 3])
        served = False
        for w in window:
            m = _SCOTLAND_ACTIONABLE_RE.search(w)
            if not m or not _route_is_actionable(w, m):
                continue
            served = True
            break
        if not served:
            return False
    return True


# Only a ROUTE counts. Citizens Advice is also a research publisher, and citing
# "Citizens Advice's 2025 Scams Awareness survey" is not a consumer-advice
# instruction — flagging that was a false positive on the marketplace hub.
_CA_NAMED_RE = re.compile(
    r"0808\s*223\s*1133"
    # `from` must be ROUTE-SHAPED. Bare `from` turned "Data from Citizens Advice
    # shows…" into a routing instruction (operator review, 2026-07-27).
    r"|(?:contact|call|ring|phone|ask|speak\s+to|report\s+to|refer\s+to|take\s+it\s+to"
    r"|take\s+the\s+\w+\s+to|(?:advice|help|support|guidance)\s+(?:is\s+)?(?:available\s+)?from"
    r"|available\s+from|go\s+through|apply\s+via)"
    r"\b[^.]{0,60}?\bCitizens\s+Advice(?![\u2019']s)"
    r"|Citizens\s+Advice(?:\s+consumer)?\s+(?:helpline|consumer\s+service|adviser)", re.I)
# The other two nations' consumer services, either named or by number.
_CA_SCOPED_RE = re.compile(
    r"England\s+and\s+Wales|Advice\s+Direct\s+Scotland|0808\s*800\s*9060"
    r"|Consumerline|0300\s*123\s*6262|your\s+nation|each\s+nation", re.I)


# "Three main agencies" is correct; "the three CRAs" written as EXHAUSTIVE is
# not — MoneyHelper also lists Crediva as offering a free statutory report
# (operator review, 2026-07-27). Deliberately narrow: it fires only on an
# explicitly exhaustive construction near a credit-agency context.
# Field-level gate: the text must be ABOUT credit reference agencies. Without it
# "tap the three-dot menu ... choose Report" matched, because "the three" sat
# within 60 characters of "report" — five false positives on UI instructions.
_CRA_CONTEXT_RE = re.compile(
    r"credit\s+reference|credit[- ]reference|credit\s+files?|credit\s+reports?"
    r"|\bCRAs?\b|Experian|Equifax|TransUnion|Crediva", re.I)
_CRA_EXHAUSTIVE_RE = re.compile(
    r"\b(?:all\s+three|the\s+three|only\s+three|the\s+other\s+two|both\s+other"
    r"|the\s+only(?:\s+\w+){0,3}?)\b"
    r"[^.,;\u2014]{0,60}\b(?:credit\s+reference|credit[- ]reference|CRAs?|agenc\w+|credit\s+files?"
    r"|credit\s+reports?|Experian|Equifax|TransUnion)\b"
    r"|\b(?:credit\s+reference|credit[- ]reference)\s+agenc\w*[^.,;\u2014]{0,40}"
    r"\b(?:all\s+three|the\s+three|only\s+three|the\s+other\s+two)\b", re.I)
_CRA_MAIN_QUALIFIED_RE = re.compile(r"\bthree\s+main\b|\bmain\s+(?:three|agencies)\b|Crediva", re.I)


# Clause boundaries for local qualification. A contrastive conjunction matters
# most: "X are the three main agencies, BUT check all three" must not be excused
# by the correct first half.
_CLAUSE_SPLIT_RE = re.compile(r"[;,\u2014]|\s+(?:but|however|though|although|whereas)\s+", re.I)


def _clause_around(sent: str, m) -> str:
    """The clause of `sent` containing match `m`."""
    starts = [0] + [b.end() for b in _CLAUSE_SPLIT_RE.finditer(sent)]
    ends = [b.start() for b in _CLAUSE_SPLIT_RE.finditer(sent)] + [len(sent)]
    for a, b in zip(starts, ends):
        if a <= m.start() < b:
            return sent[a:b]
    return sent


def check_cra_exhaustive(post: Dict, *, fields=None) -> List[Dict]:
    """Flag credit-agency advice written as if three agencies were all of them.

    Experian, Equifax and TransUnion are the three MAIN agencies. A recovery
    guide telling a reader to check "all three" or "the other two" leaves out an
    agency that also holds a free statutory report.
    """
    issues: List[Dict] = []
    for label, text in (_route_fields(post) if fields is None else fields):
        if not text.strip() or not _CRA_CONTEXT_RE.search(text):
            continue
        # PER SENTENCE. A field-wide qualification check let a correct "three
        # main agencies ... Crediva" sentence excuse a separate later "check all
        # three UK credit reference agencies" in the same field, and only the
        # FIRST match was ever examined (operator review, 2026-07-27).
        for sent in _sentences(text):
            for m in _CRA_EXHAUSTIVE_RE.finditer(sent):
                # Qualification must be LOCAL to the matched claim. Suppressing the
                # whole sentence let "…are the three main agencies, but check all
                # three UK credit reference agencies" pass, and only the first
                # match was examined (operator review, 2026-07-27).
                if _CRA_MAIN_QUALIFIED_RE.search(_clause_around(sent, m)):
                    continue
                issues.append({
                    "check": "cra_exhaustive",
                    "severity": SEVERITY_BLOCK,
                    "span": re.sub(r"\s+", " ", _clause_around(sent, m))[:160],
                    "detail": ("presents the credit reference agencies as an exhaustive set of "
                               "three. Experian, Equifax and TransUnion are the three MAIN agencies; "
                               "MoneyHelper also lists Crediva as offering a free statutory report. "
                               "Say \"the three main agencies\" or name all four."),
                })
    return issues


def check_nation_consumer_routing(post: Dict) -> List[Dict]:
    """Citizens Advice is the consumer service for ENGLAND AND WALES only.

    Scotland uses Advice Direct Scotland (0808 800 9060) and Northern Ireland
    uses Consumerline (0300 123 6262) — both added to the verified canon on
    2026-07-27. Naming Citizens Advice as a general UK helpline strands Scottish
    and Northern Irish readers exactly as an unqualified Report Fraud route
    does, and 23 live guides did so (operator review, 2026-07-27).

    Checked per field, like the Scotland reporting route: a scope note buried in
    a later section does not help a reader who only sees the quick answer.
    """
    issues: List[Dict] = []
    for label, text in _route_fields(post):
        if not text.strip():
            continue
        # PER MENTION, scoped locally. A field-wide `_CA_SCOPED_RE.search(text)`
        # let one correct three-nation sentence excuse a separate later "take the
        # contract to Citizens Advice" in the same field (operator review,
        # 2026-07-27) — the same suppression bug the Report Fraud matcher had.
        sents = _sentences(text)
        for n, sent in enumerate(sents):
            if not _CA_NAMED_RE.search(sent):
                continue
            window = " ".join([sent] + sents[n + 1:n + 3])
            if _CA_SCOPED_RE.search(window):
                continue
            issues.append({
                "check": "nation_consumer_routing",
                "severity": SEVERITY_BLOCK,
                "span": re.sub(r"\s+", " ", sent)[:160],
                "detail": (f"the {label} names Citizens Advice without scoping it. Citizens Advice "
                           f"covers England and Wales; add Advice Direct Scotland on 0808 800 9060 "
                           f"and Consumerline on 0300 123 6262, or point to the service for the "
                           f"reader's nation."),
            })
    return issues


def check_scotland_routing(post: Dict) -> List[Dict]:
    """Flag a reporting route that names Report Fraud without the Scottish route.

    Report Fraud covers England, Wales and Northern Ireland; Scotland reports
    through Police Scotland on 101. The corpus gets this right in section bodies
    (165 of 176 that name Report Fraud also route Scotland) but the
    `quick_answer` field — which feeds speakable markup and is the most
    extractable passage on the page — dropped the qualifier on 57 guides,
    because `_post_text` did not include that field until 2026-07-27.

    Checked per-field rather than over the concatenated post text: a Scotland
    route buried in a later section does not help a reader who only ever sees
    the quick answer read aloud.
    """
    issues: List[Dict] = []
    for label, text in _route_fields(post):
        if not text.strip():
            continue
        if _REPORT_FRAUD_NAMED_RE.search(text) and not _field_routes_scotland(text):
            issues.append({
                "check": "scotland_routing",
                "severity": SEVERITY_BLOCK,
                "span": text[:160],
                "detail": (f"the {label} names Report Fraud without the Scottish route. Report Fraud "
                           f"covers England, Wales and Northern Ireland; add Police Scotland on 101 "
                           f"for Scotland, or drop the specific service and point to the guide body."),
            })
    return issues


# ── Canon guards derived from the 2026-07-26/27 operator reviews ─────────────
# Each of these encodes a rule the operator had to correct by hand, so the class
# cannot silently reappear. All FLAG tier: they mark passages for editorial
# judgement rather than blocking a publish, because each has legitimate uses
# (a negation, an attributed statement, a claim that carries its own caveat).
# Suppression logic below mirrors the false-positive patterns found when these
# were first run over the corpus — without it the noise makes them useless.

_159_FREE_RE = re.compile(r"\b159\b[^.]{0,50}\bfree\b|\bfree\b[^.]{0,25}\b159\b", re.I)
_DBS_RE = re.compile(r"\bDBS\b")
_DBS_OTHER_NATIONS_RE = re.compile(r"Disclosure Scotland|AccessNI", re.I)
_FEE_EXCEPTION_RE = re.compile(r"entertainment (?:and|or) modelling", re.I)
_SPORTS_EXCEPTION_RE = re.compile(r"\bsports?\s+(?:person|people)\b|professional sport\b", re.I)
_SCALE_CLAIM_RE = re.compile(
    r"\b(?:thousands|millions|hundreds of thousands)\b", re.I)
_SCALE_ATTRIB_RE = re.compile(
    r"UK Finance|ONS|Office for National Statistics|Cifas|FCA|Ofcom|Citizens Advice|"
    r"City of London Police|according to|survey", re.I)
_NEGATION_NEAR_RE = re.compile(
    r"\b(?:not|never|no|none|isn't|is not|does not|doesn't|cannot|can't)\b", re.I)


def check_canon_guards(post: Dict) -> List[Dict]:
    """FLAG passages matching error classes the operator has corrected before.

    Checked per reader-visible field, because `quick_answer` and `description`
    are surfaced independently (speakable markup and search snippets) — a
    caveat present only in a later section does not reach that reader.
    """
    issues: List[Dict] = []
    whole = _post_text(post)

    def add(check, field, span, detail):
        issues.append({"check": check, "severity": SEVERITY_FLAG,
                       "span": re.sub(r"\s+", " ", str(span))[:160], "detail": detail})

    surfaces = [("quick answer", str(post.get("quick_answer") or "")),
                ("meta description", str(post.get("description") or "")),
                ("hero", str(post.get("hero") or ""))]
    bodies = [("section body", b) for _, b in (post.get("sections") or [])]
    bodies += [("FAQ answer", a) for _, a in structured.narrative_faq(post)]

    # 159 is not free — the caller's provider sets the price (Ofcom/Stop Scams UK).
    for label, text in surfaces + bodies:
        m = _159_FREE_RE.search(text)
        # Suppress the correct usage: "159 ... is not necessarily free", "not free".
        while m and _NEGATION_NEAR_RE.search(text[max(0, m.start() - 40):m.end()]):
            m = _159_FREE_RE.search(text, m.end())
        if m:
            add("159_cost", label, m.group(0),
                "describes 159 as free. The caller's provider sets the price and it may not be "
                "included in an allowance — state that instead.")
            break

    # DBS is England and Wales only.
    if _DBS_RE.search(whole) and not _DBS_OTHER_NATIONS_RE.search(whole):
        m = _DBS_RE.search(whole)
        add("dbs_jurisdiction", "post", m.group(0),
            "names DBS without Disclosure Scotland or AccessNI. DBS covers work in England and "
            "Wales; Scotland uses Disclosure Scotland (Level 1 direct, Level 2/PVG "
            "organisation-started) and Northern Ireland uses AccessNI.")

    # Work-finding fee exception must include professional sport, and GB/NI differ.
    if _FEE_EXCEPTION_RE.search(whole) and not _SPORTS_EXCEPTION_RE.search(whole):
        add("fee_exception_scope", "post", _FEE_EXCEPTION_RE.search(whole).group(0),
            "states the work-finding fee exception without professional sports people. Schedule 3 "
            "covers specified performers and creative occupations, photographic or fashion models "
            "AND professional sports people; Great Britain and Northern Ireland have separate "
            "regulations.")

    # Unsourced scale claims ("costs you thousands") — flagged in hero/description
    # only, where they function as the page's headline promise.
    for label, text in surfaces:
        m = _SCALE_CLAIM_RE.search(text)
        if m and not _SCALE_ATTRIB_RE.search(text):
            add("scale_claim", label, m.group(0),
                f"unsourced scale claim in the {label}. Either attribute it to a published figure "
                f"(the site's own /research/uk-scam-statistics/ dataset names its publishers) or "
                f"describe the harm without quantifying it.")
            break

    return issues


def check_consolidation_evasion(post: Dict) -> List[Dict]:
    """A DRAFT may never declare itself consolidated.

    `consolidated_into` removes a record from the public corpus and from the
    similarity check. That is an editorial retirement decision, made by the
    operator on an existing guide — never something a generated draft can
    assert about itself. Without this, the cheapest way past a duplicate-content
    BLOCK would be to add one field (operator review, 2026-07-30).

    The gate only ever sees drafts and re-audited live records; a live record
    that legitimately carries the field is exempted by the corpus partition
    before it reaches here, so this fires only on a draft asserting it.
    """
    # PRESENCE, not truthiness. `post.get(...)` returned falsy for "", None,
    # False, [] and {} — so a draft could carry the field, pass the gate, and
    # then be rejected (or not) much later by the build (operator review,
    # 2026-07-30). The field must simply not be there.
    if corpus_mod.CONSOLIDATED_INTO not in post:
        return []
    return [{
        "check": "consolidation_evasion",
        "severity": SEVERITY_BLOCK,
        "span": repr(post.get(corpus_mod.CONSOLIDATED_INTO)),
        "detail": (f"the draft sets {corpus_mod.CONSOLIDATED_INTO!r}, which would remove it from "
                   f"the public corpus and from the duplicate-content check. Consolidation is an "
                   f"operator decision applied to an existing guide, not a property a new draft "
                   f"may claim. Remove the field."),
    }]


def check_quick_answer_present(post: Dict, *, is_hub: bool = False) -> List[Dict]:
    """BLOCK a guide with no usable `quick_answer`.

    The field feeds TWO rendered surfaces — the highlighted answer box and the
    `speakable` structured data — so an absent one silently costs the guide both,
    with nothing in the output to show it is missing.

    Every quick-answer check already in this gate reads the field as
    `post.get("quick_answer", "")` or `... or ""`, which makes an ABSENT field
    indistinguishable from an empty one: each check finds no text, finds nothing
    wrong with no text, and passes. The gate therefore validated the content of
    the field but never its existence, and a draft omitting it passed clean — as
    the 2026-08-14 Search Console draft did (operator review, 2026-08-14). It
    would have been the only one of 185 public guides without an answer box.

    Presence AND non-blankness, because both fail identically at render time; a
    non-string is caught for the same reason. Deliberately NOT a length check —
    the 35–60-word house rule is a drafting instruction in
    `generate_content_claude.py`, and enforcing it here would block the
    generator's own short fallback article, which is the safety net used when
    drafting fails.

    Two exemptions:

    - HUBS never have the field. `validate_category_hubs()` restricts hub keys to
      a set that does not include it, and hubs open with `intro` instead, so this
      would be a guaranteed false BLOCK that fails the build on every run. Hub
      callers pass `is_hub=True`.
    - CONSOLIDATED records render no page at all, so they have no answer box to
      be missing.

    The consolidated test is `consolidation_map`'s, called on this one record so
    the rule is not restated here: a non-empty string target. That is a different
    test from `check_consolidation_evasion`'s deliberately, and the difference is
    load-bearing — that check asks "did a draft assert this field at all", so
    mere presence is right there, whereas this one asks "is this record
    published", and a record whose target is `""` IS published (`corpus.py`
    rejects it separately as malformed). Using presence here would exempt a
    live guide from the answer-box requirement via an empty string.
    """
    if is_hub:
        return []
    probe = dict(post)
    probe.setdefault("slug", "")           # consolidation_map indexes by slug
    if corpus_mod.consolidation_map([probe]):
        return []
    qa = post.get("quick_answer")
    if isinstance(qa, dict) and qa.get('kind') == 'action-summary' and 'reporting_routes' in post:
        return []  # The closed placement was already checked by validate_page.
    if isinstance(qa, str) and qa.strip():
        return []
    if "quick_answer" not in post:
        why = "has no 'quick_answer' field"
    elif not isinstance(qa, str):
        why = f"'quick_answer' is {type(qa).__name__}, not a string"
    else:
        why = "'quick_answer' is blank"
    return [{
        "check": "quick_answer_missing",
        "severity": SEVERITY_BLOCK,
        "span": repr(qa)[:140],
        "detail": (f"the guide {why}. It renders the highlighted answer box and the speakable "
                   f"structured data, so without it the page ships with neither. Add a "
                   f"verdict-first answer of 35 to 60 words that stands alone without the rest "
                   f"of the article."),
    }]


def check_deterministic(post: Dict, *, is_draft: bool = True,
                        is_hub: bool = False,
                        reporting_mode: str = structured.LEGACY_DIAGNOSTIC,
                        reporting_canon=None, reporting_review=None, reporting_page_id=None) -> List[Dict]:
    # Field presence always selects strict mode, even when a caller requests
    # compatibility. A draft cannot downgrade itself through an empty/null plan.
    try:
        mode = structured.page_mode(post, reporting_mode)
        if mode == structured.STRUCTURED_REQUIRED:
            sources = _CANON if reporting_canon is None else reporting_canon
            catalog = canon_mod.reporting_catalog(sources,
                expected_digest=reporting_review.canon_sha256 if isinstance(
                    reporting_review, structured.ReviewContext) else None)
            structured.validate_page(post, catalog, reporting_review, page_id=reporting_page_id)
    except (structured.ReportingError, canon_mod.CanonError) as exc:
        return [{"check": "structured_reporting", "severity": SEVERITY_BLOCK,
                 "span": "reporting_routes", "detail": str(exc)}]
    if mode == structured.STRUCTURED_REQUIRED:
        # Retain ordinary factual/editorial checks, but never ask legacy prose
        # parsers to authorise or reconstruct an already structured route.
        return (check_banned_entities(post) + check_absolutes(post)
                + check_legislation(post) + check_dated_events(post)
                + check_cra_misclassification(post) + check_nfd_routing(post)
                + check_uk_advice_flags(post) + check_recurring_accuracy(post)
                + check_cra_exhaustive(post, fields=structured.prose_fields(post)) + check_canon_guards(post)
                + check_text_wellformed(post) + check_unrenderable_markup(post)
                + check_quick_answer_present(post, is_hub=is_hub)
                + (check_consolidation_evasion(post) if is_draft else []))
    # Reporting instructions authenticate their destinations against the canon.
    # General citations and example scam URLs are not a global URL allowlist.
    return (check_phones(post) + check_shortcodes(post) + check_report_mailboxes(post)
            + check_banned_entities(post)
            + check_absolutes(post) + check_sources(post)
            + check_legislation(post) + check_dated_events(post)
            + check_cra_misclassification(post) + check_nfd_routing(post)
            + check_uk_advice_flags(post) + check_recurring_accuracy(post)
            + check_scotland_routing(post) + check_nation_consumer_routing(post)
            + check_cra_exhaustive(post)
            + check_canon_guards(post)
            + check_text_wellformed(post)
            + check_unrenderable_markup(post)
            + check_ncsc_route_scope(post)
            + check_report_fraud_destinations(post)
            + check_quick_answer_present(post, is_hub=is_hub)
            # Corpus-state assertions a DRAFT may not make about itself. Corpus
            # audits pass is_draft=False, because a live consolidated record
            # legitimately carries the field.
            + (check_consolidation_evasion(post) if is_draft else []))


# ─── LLM JUDGE ───────────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You are a strict fact-checking editor for a UK consumer-protection site. \
You are reviewing an AI-DRAFTED scam guide BEFORE publication. Your only job is to catch \
fabrication and unverifiable claims — not style. Assume the drafting model has no internet \
access and may hallucinate confidently.

Flag a claim when it is a specific assertion the reader could act on or be misled by and that \
cannot be safely assumed true:
- invented or unattributed statistics / figures / percentages / £ amounts presented as fact
- numbers used illustratively or hypothetically (e.g. "they send this to 100,000 people and even \
if only 0.1% pay") — a made-up count or rate is still fabrication when framed as an example
- absolute guarantees or certainty stated to the READER about their own situation: that no \
footage / recording / evidence exists, that they are completely safe, that an outcome is impossible \
or guaranteed. Hedged language ("almost certainly", "extremely unlikely", "in the vast majority of \
cases") is fine; an unconditional absolute is not
- quotes attributed to a named person or organisation
- specific claims about a named company's deal, partnership, acquisition, product, pricing, or feature
- naming a specific company as "legitimate"/"genuine"/"trusted" (could be invented or defunct)
- a specific dated event, law, or regulatory action stated as fact
- any organisation-specific phone number (banks, couriers, utilities) — these should not be hardcoded
- how a named platform's VERIFICATION works: that its support account uses one exact username, \
that a badge / tick / checkmark proves identity or authenticity, that a badge colour means something \
specific, or that "any variation is a scam". Platforms rename and re-tier these without notice and \
no two work alike, so a reader who trusts the description trusts the wrong account. The safe advice \
is to reach support from inside the app or the platform's official help centre. Severity "medium"

Do NOT flag: general scam-pattern description, the verified UK reporting routes listed under \
VERIFIED ROUTES above (including forwarding texts to 7726 and report@phishing.gov.uk), \
clearly directional language ("growing rapidly", "many victims"), or the site accurately \
describing a SCAMMER's own false promise (e.g. "the scammer claims your funds are 100% safe").
DO still flag an unscoped route: Report Fraud presented as the UK-wide service without the \
Police Scotland alternative, or Citizens Advice presented as a UK-wide helpline, is an error \
even though both bodies are in the canon.

OMISSION — ONE case, and one only. This is the single exception to the rule that you do not report \
missing content. Nothing else in the guide is ever a finding for being absent, incomplete, \
unclarified, or ordered differently than you would order it: not a reporting route you would have \
scoped differently, not a caveat you would have added, not an explanation you think a reader would \
benefit from. If your finding could begin with the words "the guide should also", "should clarify", \
or "omits", and it is not the payment case below, it is NOT a finding — discard it.
The one case: if the guide tells a reader what to do after they THEMSELVES AUTHORISED AND SENT a payment — a bank \
transfer or faster payment they made — and never mentions that reimbursement for authorised push \
payment (APP) fraud has been mandatory under Payment Systems Regulator rules since 7 October 2024, \
flag it with severity "medium" and set "class":"app_omission". "Your bank may be able to recall the \
payment" standing alone IS the failure case: a recall is a courtesy that depends on the money still \
being there, whereas reimbursement is a right.
This applies ONLY to payments the reader authorised and sent. Do NOT raise it for a guide about \
stolen or shared CARD DETAILS, an unauthorised transaction, a card payment, a chargeback or Section \
75 claim, cash, gift cards, or cryptocurrency bought and sent on the reader's own initiative — those \
are different protections and APP reimbursement is not the right answer. Do NOT flag a guide that \
never discusses the reader sending money. Do NOT require the cap, excess, deadline or exception \
figures — the drafting model cannot verify those and should not state them.

Severity discipline for the two classes above (platform verification, APP omission): use "medium", \
never "high", and set the "class" field so they can be told apart. They are editorial accuracy \
problems for a human reviewer, not fabrications, and neither may set verdict "fail" on its own.

Respond with ONLY this JSON, no other text:
{"verdict":"pass"|"fail","risk":"low"|"medium"|"high","issues":[{"claim":"<quote>","problem":"<short>","severity":"low"|"medium"|"high","class":"platform_verification"|"app_omission"|null}]}
Set verdict "fail" ONLY when at least one issue has severity "high". If every issue you found is \
"low" or "medium", the verdict is "pass" — those are recorded for a human reviewer and must not stop \
publication. A guide with no high-severity issue is a passing guide."""
# Same rendering as ACCURACY_BLOCK, so judge and generator cannot disagree.
JUDGE_SYSTEM = JUDGE_SYSTEM.replace(
    "VERIFIED ROUTES above",
    "VERIFIED ROUTES above").rstrip() + "\n\nVERIFIED ROUTES (nation-scoped, from the verified canon):\n" + CANON_ROUTE_BLOCK + "\n"


# Judge classes that may never block publication — see the cap in judge_llm().
_JUDGE_FLAG_ONLY_CLASSES = frozenset({"platform_verification", "app_omission"})


def judge_llm(post: Dict, client, model: str) -> List[Dict]:
    """Run the LLM critic. Returns issue dicts. Fail-CLOSED on judge error
    (a post we cannot verify is treated as blocking, since the engine is
    autonomous)."""
    body = _post_text(post)
    # Tell the judge TODAY'S DATE. Without it, it reads any date after its own
    # training cutoff as "future-dated" and calls a correct, already-verified
    # claim fabricated — four such findings in the 2026-07-31 sample, including
    # a legitimate "as checked on" line (operator review follow-up).
    user = (f"Today's date is {date.today().isoformat()}. Dates before today are in the PAST "
            f"and may be genuine even if they are after your training cutoff — judge them on "
            f"plausibility and attribution, not on whether you personally recall them.\n\n"
            f"Title: {post.get('title','')}\n\nReview this draft guide:\n\n{body}\n\n"
            "Return the JSON verdict.")
    system_prompt = JUDGE_SYSTEM
    if _JUDGE_CANON_BLOCK:
        # The renderer carries its own preamble — don't restate it here, or the
        # two wordings drift apart the way hand-typed canon copies always have.
        system_prompt += "\n\n" + _JUDGE_CANON_BLOCK
    # `temperature` is DEPRECATED on current models (Opus 5, Sonnet 5, Opus 4.8
    # all reject it with a 400) and accepted only by the pinned Haiku 4.5. Since
    # judge_llm fails CLOSED, a hard-coded temperature meant that pointing the
    # gate at any current model would BLOCK every draft with an unexplained
    # "could not verify" — the publication pipeline would look like it was
    # catching fabrications when it was really just erroring (found while
    # running the judge on a sample, 2026-07-31).
    #
    # Try with it, then retry without on that specific rejection, so the same
    # code works across model generations without a hard-coded model list.
    # 1500 was enough for Haiku's terse verdicts (~220 output tokens) but any
    # more thorough model runs past it, and a TRUNCATED verdict surfaces as a
    # JSONDecodeError — which fails closed and reads like a caught fabrication.
    # Half the guides in the 2026-07-31 sample failed this way before the limit
    # was raised.
    def _create(**extra):
        return client.messages.create(
            model=model,
            max_tokens=8000,
            system=system_prompt,
            messages=[{"role": "user", "content": user}],
            **extra,
        )

    try:
        try:
            resp = _create(temperature=0)
        except Exception as exc:                     # noqa: BLE001 — inspected below
            if "temperature" not in str(exc).lower():
                raise
            resp = _create()
        if getattr(resp, "stop_reason", None) == "max_tokens":
            # Say WHY, instead of letting it look like malformed JSON.
            raise ValueError(
                "the judge's verdict was truncated at max_tokens — raise the limit rather "
                "than treating this as a finding")
        raw = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001 — any failure must fail closed
        return [{"check": "judge", "severity": SEVERITY_BLOCK,
                 "detail": f"LLM judge could not verify this draft ({type(e).__name__}); failing closed."}]

    issues: List[Dict] = []
    for it in (data.get("issues") or []):
        sev = SEVERITY_BLOCK if it.get("severity") == "high" else SEVERITY_FLAG
        # Severity cap, enforced HERE rather than trusted to the prompt. Both of
        # these classes were added 2026-08-08 with an explicit "use medium, never
        # high" instruction, and on the very first run the judge returned "high"
        # for both anyway — it reasoned they were serious, which is a defensible
        # editorial view but not its call to make. A model's opinion about
        # completeness or a third party's UI must not halt the publication
        # pipeline; both are for a human reviewer. Judge verdicts also vary run
        # to run (2026-07-16), so a prompt-only cap is not a cap at all.
        if it.get("class") in _JUDGE_FLAG_ONLY_CLASSES:
            sev = SEVERITY_FLAG
        issues.append({"check": "judge", "severity": sev,
                       "detail": f"{it.get('problem','issue')}: \"{str(it.get('claim',''))[:140]}\""})
    # ...and the same cap has to survive the verdict-level fallback below, or it
    # is no cap at all: a judge that rates an app_omission "high" also returns
    # verdict "fail", which would re-add a block for the very issue just capped.
    raw_issues = data.get("issues") or []
    only_capped = bool(raw_issues) and all(
        i.get("class") in _JUDGE_FLAG_ONLY_CLASSES for i in raw_issues)
    if only_capped:
        return issues
    if data.get("verdict") == "fail" or data.get("risk") == "high":
        if not any(i["severity"] == SEVERITY_BLOCK for i in issues):
            issues.append({"check": "judge", "severity": SEVERITY_BLOCK,
                           "detail": f"judge verdict={data.get('verdict')} risk={data.get('risk')}"})
    return issues


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

def run_gate(post: Dict, client=None, model: Optional[str] = None,
             use_llm: bool = True, corpus: Optional[List[Dict]] = None,
             is_draft: bool = True, is_hub: bool = False,
             reporting_mode: str = structured.LEGACY_DIAGNOSTIC,
             reporting_canon=None, reporting_review=None, reporting_page_id=None) -> GateResult:
    """Run the full gate on a post. PASS unless a blocking issue is found.

    Pass `corpus` (the existing posts.json list) to also check the draft for
    body-copy duplication against already-published guides. Consolidated
    archive records are excluded from that comparison — see check_similarity().

    `is_draft=False` for corpus audits of already-published records: a live
    record may legitimately carry `consolidated_into`, a draft may not.

    `is_hub=True` for category hubs, which are a different surface with a
    different schema — see check_quick_answer_present()."""
    # Publication mode is external to the draft. Diagnostic parsers remain
    # available through check_deterministic; they cannot grant publication.
    from reporting_publication import required, review as authenticated_review
    if required(post, reporting_page_id):
        reporting_mode = structured.STRUCTURED_REQUIRED
        try:
            reporting_review = authenticated_review(post,
                _CANON if reporting_canon is None else reporting_canon,
                reporting_review, page_id=reporting_page_id)
        except (ValueError, OSError, TypeError, KeyError) as exc:
            return GateResult(slug=post.get('slug', '?'), passed=False,
                issues=[{"check": "structured_reporting", "severity": SEVERITY_BLOCK,
                         "span": "publication review", "detail": str(exc)}],
                reporting_mode=structured.STRUCTURED_REQUIRED)
    issues = check_deterministic(post, is_draft=is_draft, is_hub=is_hub,
        reporting_mode=reporting_mode, reporting_canon=reporting_canon,
        reporting_review=reporting_review, reporting_page_id=reporting_page_id)
    issues += check_similarity(post, corpus)
    if use_llm and client is not None and model and not any(
            i.get('check') == 'structured_reporting' and i.get('severity') == SEVERITY_BLOCK
            for i in issues):
        issues += judge_llm(post, client, model)
    passed = not any(i.get("severity") == SEVERITY_BLOCK for i in issues)
    mode = (structured.STRUCTURED_REQUIRED if "reporting_routes" in post
            else reporting_mode)
    return GateResult(slug=post.get("slug", "?"), passed=passed, issues=issues,
                      reporting_mode=mode)


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
    safe_name = hashlib.sha256(json.dumps(post, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    path = d / f"quarantine-{safe_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return str(path)


# ─── CLAIM MANIFEST ───────────────────────────────────────────────────────────

def build_manifest(post: Dict, result: GateResult, model: Optional[str] = None,
                   today: Optional[str] = None) -> Dict:
    """An AUDIT record of the high-stakes claims the gate detected in a post —
    NOT a bibliography. These are detector outputs (phones, absolutes, banned
    entities, non-canon reporting emails, legislation, dated events) plus any LLM
    judge findings, each tagged block/flag. One is written per PUBLISHED guide so
    the weekly digest can surface flag-tier claims for a human to verify. The
    drafting model has no internet, so we never ask it to cite — the manifest is
    derived entirely from deterministic + judge detection."""
    claims = []
    for i in result.issues:
        claims.append({
            "type":     i.get("check"),
            "severity": i.get("severity"),
            "text":     i.get("span") or (i.get("detail", "")[:160]),
            "detail":   i.get("detail", ""),
        })
    return {
        "slug":        post.get("slug"),
        "title":       post.get("title"),
        "date":        today or post.get("date"),
        "model":       model,
        "gate_passed": result.passed,
        "claims":      claims,
    }


def write_manifest(post: Dict, result: GateResult, model: Optional[str] = None,
                   today: Optional[str] = None, mdir: str = "content/manifests") -> str:
    """Write the per-guide claim manifest to content/manifests/<slug>.json.
    Best-effort: callers should not fail a publish if this raises."""
    d = Path(mdir)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{post.get('slug', 'unknown')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(build_manifest(post, result, model, today), f, indent=2, ensure_ascii=False)
        f.write("\n")
    return str(path)
