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
- Use directional language ("growing rapidly", "a meaningful share", "early data suggests") for figures unless they are well-established public facts. Never invent specific percentages, dollar figures, or entity-attributed statistics. Do not attribute a statistic to a named body (Report Fraud, the FCA, Which?, UK Finance, NCSC) unless you are certain of the exact figure — if unsure, describe the pattern without a number. This includes ILLUSTRATIVE or hypothetical numbers: do not invent a count or rate to make a point (e.g. "they email 100,000 people and even if 0.1% pay") — describe the mechanism qualitatively instead ("sent to very large numbers of people, so even a tiny response rate is profitable").
- Never give the reader an unconditional guarantee or absolute about their own situation or safety: do not write that something is impossible, that no footage/recording/evidence exists, that they are "100% safe", or that an outcome is guaranteed. Real threats vary, so an absolute can be both wrong and harmful — use hedged, accurate language ("almost always a bluff", "it is extremely unlikely that any footage exists", "in the vast majority of cases"). Accurately describing a scammer's OWN false promise is fine.
- NEVER invent or assert a specific dated event, deal, acquisition, merger, partnership, funding round, valuation, product launch, regulatory action, or piece of legislation involving a real named company, person, product, or regulator unless you are certain it is a true, well-established public fact. This explicitly includes who-acquired-whom, who-partnered-with-whom, launch/approval dates, what a law or feature actually covers, pricing/plan limits, and which tool or vendor a named company actually uses.
- Never present a named company as "legitimate", "genuine", or "trusted" unless it is a well-known real brand; do not invent example company names.
- If you are not certain of the exact relationship, date, figure, or attribution, describe it in general terms WITHOUT naming a specific deal/number — or omit it. Inventing a product or vendor name, or pairing a real company with the wrong partner, tool, or capability, is forbidden.
- Before finalising, re-read every sentence that names a real company, person, or product alongside a date, number, deal, price, or feature. If you are not confident it is a true public fact, rewrite it as a general statement or delete it.
- Do NOT state a phone number for any specific company (bank, courier, retailer, utility, etc.). The ONLY phone numbers permitted anywhere are: Report Fraud 0300 123 2040, Citizens Advice 0808 223 1133, the FCA consumer helpline 0800 111 6768, 159 (to reach your bank), and 7726 (forward spam texts). For any organisation, tell readers to use the number on their card, bill, or the organisation's official website — never state or invent a company's own number."""

# ─── ALLOWLISTS / BLOCKLISTS ─────────────────────────────────────────────────

# The ONLY phone numbers a guide may state (normalised to digits-only) and the
# only official reporting emails — both DERIVED from the verified canon in
# content/sources.json (single source of truth, shared with build.py's on-page
# reporting block). Everything else — bank fraud lines, courier numbers, utility
# numbers — is blocked, because hardcoding an organisation's number is the
# highest-consequence error on a scam-advice site. Loaded defensively: if the
# canon is missing/malformed the gate falls back to the hardcoded set below so
# it never breaks.
# Keep in sync with content/sources.json — this set is used ONLY when the canon
# fails to load, and any number in the canon but missing here would then be
# false-BLOCKed (e.g. the Revenge Porn Helpline was added to the canon after
# this fallback was first written and had drifted).
_FALLBACK_PHONE_DIGITS = {
    "03001232040", "08082231133", "08001116768", "03456000459", "7726", "159",
    "0800111999", "105", "999", "112", "101",
}
_FALLBACK_REPORT_EMAILS = {"report@phishing.gov.uk"}


def _load_canon() -> Dict:
    path = Path(__file__).resolve().parents[1] / "content" / "sources.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _canon_phone_digits(canon: Dict) -> set:
    digits = set()
    for r in canon.get("official_routes", []):
        for field in ("phone", "sms"):
            v = r.get(field)
            if v:
                d = re.sub(r"\D", "", str(v))
                if d:
                    digits.add(d)
    return digits or set(_FALLBACK_PHONE_DIGITS)


def _canon_report_emails(canon: Dict) -> set:
    emails = {e.strip().lower() for e in canon.get("report_emails", []) if e}
    for r in canon.get("official_routes", []):
        if r.get("email"):
            emails.add(str(r["email"]).strip().lower())
    return emails or set(_FALLBACK_REPORT_EMAILS)


def _judge_canon_block(canon: Dict) -> str:
    """Render the sources.json canon as a compact fact list for the LLM judge.

    Without this, the judge has no way to know check_phones() has ALREADY
    deterministically verified every phone number/route against this same
    canon — it re-derives "is this real?" from its own training-data recall
    on every call, which is what let it flip-flop across runs on whether 159
    is a genuine number (2026-07-13, see memory llm-judge-run-to-run-
    inconsistency). Giving it the canon stops it re-litigating settled facts."""
    lines = []
    for r in canon.get("official_routes", []):
        parts = [r.get("name", "")]
        if r.get("phone"):
            parts.append(f"phone {r['phone']}")
        if r.get("sms"):
            parts.append(f"SMS shortcode {r['sms']}")
        if r.get("email"):
            parts.append(f"email {r['email']}")
        if any(parts[1:]):
            lines.append("- " + " — ".join(p for p in parts if p))
    emails = [e for e in canon.get("report_emails", []) if e]
    if emails:
        lines.append("- Other verified official report emails: " + ", ".join(emails))
    return "\n".join(lines)


_CANON = _load_canon()
_JUDGE_CANON_BLOCK = _judge_canon_block(_CANON)
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
    """All reader-visible text from a post — title, section HEADINGS and bodies,
    faq, hero, description, and keywords. Headings/title/keywords are included so
    a high-stakes claim placed there (a hardcoded number, banned entity, false
    absolute) is checked too, not only the section bodies."""
    parts: List[str] = [str(post.get("title", ""))]
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
# was renamed TransUnion in 2018. Neither is a UK credit reference agency — the
# three CRAs are Experian, Equifax, TransUnion. Presenting ClearScore/CallCredit
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
                "detail": (f"presents '{name}' as a UK credit reference agency. The three CRAs are "
                           f"Experian, Equifax, and TransUnion — ClearScore is a free credit-checking "
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
def check_uk_advice_flags(post: Dict) -> List[Dict]:
    text = _post_text(post)
    issues: List[Dict] = []
    if _FRAUD_ALERT_RE.search(text):
        issues.append({"check": "fraud_alert", "severity": SEVERITY_FLAG,
                       "span": re.sub(r"\s+", " ", _FRAUD_ALERT_RE.search(text).group(0))[:140],
                       "detail": ("uses US-style 'fraud alert on your credit file'. The UK mechanism is a "
                                  "Cifas Protective Registration (cifas.org.uk); free CRA monitoring is separate.")})
    if _HMRC_CHANNEL_RE.search(text):
        issues.append({"check": "hmrc_channel", "severity": SEVERITY_FLAG,
                       "span": re.sub(r"\s+", " ", _HMRC_CHANNEL_RE.search(text).group(0))[:140],
                       "detail": ("blanket 'HMRC never texts/emails/links you' — HMRC runs genuine SMS/email "
                                  "campaigns and genuine texts can carry gov.uk links. Say HMRC won't ask you "
                                  "to confirm details or 'claim' a refund via a link.")})
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
    flag(_THREAT_DISMISS_RE, "threat_dismissal",
         "teaches that the absence of proof means a threat is fake/a bluff. Reassure that most are "
         "bulk bluffs WITHOUT guaranteeing safety; never imply a victim's real threat is fake.")
    flag(_SCAMSMART_RE, "retired_branding",
         "references the FCA's retired 'ScamSmart' branding. The current canon route is the FCA "
         "Firm Checker (register.fca.org.uk) — see content/sources.json.")
    return issues


def check_deterministic(post: Dict) -> List[Dict]:
    # Note: no deterministic domain/URL check — these guides intentionally
    # contain example scam/lookalike domains, so a domain allowlist is pure
    # noise here. Domain plausibility is left to the LLM judge.
    return (check_phones(post) + check_banned_entities(post)
            + check_absolutes(post) + check_sources(post)
            + check_legislation(post) + check_dated_events(post)
            + check_cra_misclassification(post) + check_nfd_routing(post)
            + check_uk_advice_flags(post) + check_recurring_accuracy(post))


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

Do NOT flag: general scam-pattern description, the standard UK reporting routes (Report Fraud \
0300 123 2040, Citizens Advice 0808 223 1133, forward texts to 7726, report@phishing.gov.uk), \
clearly directional language ("growing rapidly", "many victims"), or the site accurately \
describing a SCAMMER's own false promise (e.g. "the scammer claims your funds are 100% safe").

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
    system_prompt = JUDGE_SYSTEM
    if _JUDGE_CANON_BLOCK:
        system_prompt += (
            "\n\nThe following UK reporting routes, phone numbers, and email addresses have "
            "already been independently verified against this site's canonical source list. "
            "Treat them as accurate — do NOT flag them as fabricated, invented, or "
            "unverifiable. Only flag one of these if the draft attributes it to the wrong "
            "organisation or uses it in a clearly incorrect context:\n" + _JUDGE_CANON_BLOCK
        )
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=1500,
            temperature=0,
            system=system_prompt,
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
    return str(path)
