"""canon.py — the ONE loader, validator and renderer for content/sources.json.

`content/sources.json` is the verified canon of official UK reporting and
consumer-advice routes. Before this module existed there were four separate
copies of that knowledge:

  * `build.py::load_sources()` validated syntax and a few structures;
  * `content_gate.py::_load_canon()` only parsed the file, so a parseable `{}`
    gave the publication gate empty route rendering and an empty allow-list;
  * `report_block()` carried a hard-coded six-route sidebar for an absent canon;
  * the gate carried hand-maintained phone/email fallback sets.

The last two are gone. A canon that is absent, unparseable or structurally
invalid now stops **both** the build and the publication gate, because a missing
deployment input must never be silently papered over with a second, unreviewed
copy of the routes (operator review, 2026-07-29, `hubs-v10-c.md` §1).

Validation checks route **identities**, not label substrings: an earlier version
accepted a single fabricated label containing all three nation phrases, and
accepted `report_url: "https://"` because it only tested `startswith`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CANON_PATH = ROOT / "content" / "sources.json"


class CanonError(Exception):
    """The canon is absent, unparseable or structurally invalid."""


# ─── WHAT THE CANON MUST CONTAIN ─────────────────────────────────────────────
# Each required route is pinned by identity: its exact key, the nation it
# serves, the role it plays and the official host that must serve it. A
# renamed, re-hosted or re-scoped route fails here rather than quietly
# changing what every prompt, sidebar and checker response tells a reader.
#
# role vocabulary:
#   police-report    — where a fraud is reported to the police
#   phishing-report  — where a phishing message is forwarded
#   consumer-advice  — the nation's consumer service
REQUIRED_ROUTES: Dict[str, Dict[str, str]] = {
    "action-fraud": {
        "nation": "England, Wales and Northern Ireland",
        "role": "police-report",
        "host": "www.reportfraud.police.uk",
    },
    "police-scotland": {
        "nation": "Scotland",
        "role": "police-report",
        "host": "www.scotland.police.uk",
    },
    "ncsc-sers": {
        "nation": "United Kingdom",
        "role": "phishing-report",
        "host": "www.ncsc.gov.uk",
    },
    "citizens-advice": {
        "nation": "England and Wales",
        "role": "consumer-advice",
        "host": "www.citizensadvice.org.uk",
    },
    "advice-direct-scotland": {
        "nation": "Scotland",
        "role": "consumer-advice",
        "host": "www.advice.scot",
    },
    "consumerline-ni": {
        "nation": "Northern Ireland",
        "role": "consumer-advice",
        "host": "www.nidirect.gov.uk",
    },
}

# Every nation a reader can live in must be reachable for both roles. Derived
# from REQUIRED_ROUTES rather than searched for in free text.
POLICE_REPORT_NATIONS = ("England, Wales and Northern Ireland", "Scotland")
CONSUMER_ADVICE_NATIONS = ("England and Wales", "Scotland", "Northern Ireland")

# Hosts an official_routes URL may point at. Base domains cover subdomains.
# verified_org_contacts is deliberately NOT covered: it holds commercial
# support lines published by the company itself and is never rendered as an
# official reporting route.
OFFICIAL_HOST_SUFFIXES = (
    "gov.uk",
    "gov.scot",
    "police.uk",
    "advice.scot",
    "consumeradvice.scot",
    "citizensadvice.org.uk",
    "fca.org.uk",
    "victimsupport.org.uk",
    "revengepornhelpline.org.uk",
)

_URL_FIELDS = ("report_url", "info_url", "source_url")


def _host_allowed(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_HOST_SUFFIXES)


def _check_url(value, where: str, problems: List[str], *, official: bool = True) -> Optional[str]:
    """Validate one URL field. Returns the lowercased host, or None."""
    if not isinstance(value, str) or not value.strip():
        problems.append(f"{where} must be a non-empty string")
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme != "https":
        problems.append(f"{where} must be https, got {value!r}")
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        # "https://" parses fine and passes a startswith test. It is not a URL.
        problems.append(f"{where} has no host: {value!r}")
        return None
    if official and not _host_allowed(host):
        problems.append(f"{where} host {host!r} is not an official UK domain")
    return host


def validate_canon(canon) -> List[str]:
    """Return a list of structural problems. Empty list == valid.

    Pure and side-effect free, so the same fixtures can be run against every
    consumer of the canon.
    """
    problems: List[str] = []

    if not isinstance(canon, dict):
        return [f"canon must be a JSON object, got {type(canon).__name__}"]

    routes = canon.get("official_routes")
    if not isinstance(routes, list) or not routes:
        problems.append("'official_routes' must be a non-empty list")
        routes = []

    emails = canon.get("report_emails")
    if not isinstance(emails, list) or not emails:
        problems.append("'report_emails' must be a non-empty list")
    else:
        for n, e in enumerate(emails):
            if not isinstance(e, str) or "@" not in e or "." not in e.split("@")[-1]:
                problems.append(f"report_emails[{n}] is not an email address: {e!r}")

    contacts = canon.get("verified_org_contacts", [])
    if not isinstance(contacts, list):
        problems.append("'verified_org_contacts' must be a list when present")
        contacts = []
    for n, c in enumerate(contacts):
        if not isinstance(c, dict):
            problems.append(f"verified_org_contacts[{n}] is {type(c).__name__}, expected an object")
            continue
        for field in ("key", "name", "source_url", "checked_on"):
            if not isinstance(c.get(field), str) or not c[field].strip():
                problems.append(f"verified_org_contacts[{n}] has no {field!r}")

    seen: Dict[str, dict] = {}
    for n, r in enumerate(routes):
        if not isinstance(r, dict):
            problems.append(f"official_routes[{n}] is {type(r).__name__}, expected an object")
            continue
        key = r.get("key")
        if not isinstance(key, str) or not key.strip():
            problems.append(f"official_routes[{n}] has no 'key'")
            continue
        if key in seen:
            problems.append(f"duplicate route key {key!r}")
            continue
        seen[key] = r

        if not isinstance(r.get("name"), str) or not r["name"].strip():
            problems.append(f"route {key!r} has no 'name'")

        for field in _URL_FIELDS:
            if field in r:
                _check_url(r[field], f"route {key!r} {field}", problems)

        if r.get("on_page"):
            for field in ("report_url", "report_label"):
                if not isinstance(r.get(field), str) or not r[field].strip():
                    problems.append(f"on-page route {key!r} has no {field!r}")

    # Required routes: exact identity, not a substring search over labels.
    for key, spec in REQUIRED_ROUTES.items():
        r = seen.get(key)
        if r is None:
            problems.append(f"required route {key!r} is missing from the canon")
            continue
        if not r.get("on_page"):
            problems.append(f"required route {key!r} must be on_page")
        if r.get("nation") != spec["nation"]:
            problems.append(
                f"required route {key!r} nation is {r.get('nation')!r}, expected {spec['nation']!r}"
            )
        if r.get("role") != spec["role"]:
            problems.append(
                f"required route {key!r} role is {r.get('role')!r}, expected {spec['role']!r}"
            )
        host = _check_url(r.get("report_url"), f"required route {key!r} report_url", problems)
        if host is not None and host != spec["host"]:
            problems.append(
                f"required route {key!r} report_url host is {host!r}, expected {spec['host']!r}"
            )
        if spec["role"] in ("police-report", "consumer-advice") and not str(r.get("phone") or "").strip():
            problems.append(f"required route {key!r} has no 'phone'")
        if not isinstance(r.get("report_label"), str) or not r["report_label"].strip():
            problems.append(f"required route {key!r} has no 'report_label'")
        # `brand` is what prose calls the organisation ("Citizens Advice"), as
        # distinct from `name` (the full service name) and `report_label` (the
        # sidebar link text). Every generated sentence uses it, so it is canon
        # data rather than a string function guessing at parentheses.
        if not isinstance(r.get("brand"), str) or not r["brand"].strip():
            problems.append(f"required route {key!r} has no 'brand'")

    # Nation coverage, derived from route identities.
    for role, nations in (("police-report", POLICE_REPORT_NATIONS),
                          ("consumer-advice", CONSUMER_ADVICE_NATIONS)):
        covered = {
            r.get("nation")
            for r in seen.values()
            if r.get("role") == role and r.get("on_page")
        }
        for nation in nations:
            if nation not in covered:
                problems.append(
                    f"no on-page {role} route serves {nation!r} — readers there would be stranded"
                )

    return problems


def load_canon(path: Optional[Path] = None) -> Dict:
    """Load and validate the canon. Raises CanonError on ANY failure.

    There is no fallback. An absent canon is a broken checkout or a missing
    deployment input, and both the build and the publication gate must stop.
    """
    path = Path(path) if path is not None else CANON_PATH
    if not path.exists():
        raise CanonError(
            f"{path} is missing. content/sources.json is the single source of truth for every "
            f"reporting route; without it the build and the accuracy gate cannot run."
        )
    try:
        canon = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CanonError(f"{path} could not be parsed: {exc}")
    problems = validate_canon(canon)
    if problems:
        detail = "\n".join(f"  - {p}" for p in problems)
        raise CanonError(f"{path} is structurally invalid ({len(problems)} problem(s)):\n{detail}")
    return canon


def route(canon: Dict, key: str) -> Dict:
    """Look one route up by key. Post-validation this cannot miss for a
    required key, so callers do not need to guard."""
    for r in canon.get("official_routes", []):
        if r.get("key") == key:
            return r
    return {}


def routes_by_role(canon: Dict, role: str, *, on_page_only: bool = False) -> List[Dict]:
    return [r for r in canon.get("official_routes", [])
            if r.get("role") == role and (r.get("on_page") or not on_page_only)]


def consumer_advice_routes(canon: Dict) -> List[Dict]:
    """The ONE consumer service to name per nation.

    on_page is what distinguishes the route a reader should be sent to from a
    same-nation alternative recorded only so the gate does not treat its number
    as invented — Advice Direct Scotland runs both advice.scot and the separate
    consumeradvice.scot helpline, and GOV.UK prints a different number for each.
    Prose must name one per nation; the canon has to know about both.
    """
    return routes_by_role(canon, "consumer-advice", on_page_only=True)


def short_name(r: Dict) -> str:
    """The organisation name without its trailing nation parenthetical —
    'Citizens Advice consumer helpline (England and Wales)' → 'Citizens
    Advice consumer helpline'."""
    return str(r.get("name") or "").split("(")[0].strip()


def brand(r: Dict) -> str:
    """What prose calls the organisation — 'Citizens Advice', 'Police
    Scotland'. Canon data, validated, not a guess at where the parentheses
    start."""
    return str(r.get("brand") or short_name(r))


# ─── PROSE RENDERERS ─────────────────────────────────────────────────────────
# Every nation-scoped sentence the site or the generator emits is rendered
# here, from the validated canon. Hand-typing these is what let the sidebar,
# the generator prompt, the fallback article, the checker page, the disclaimer
# and the Terms drift apart from each other and from sources.json.

def police_report_clause(canon: Dict, *, url: bool = False, phone: bool = True) -> str:
    """The nation-scoped police route as a clause a caller supplies the verb
    for: 'Report Fraud on 0300 123 2040 for England, Wales and Northern
    Ireland, or Police Scotland on 101 for Scotland'.

    Both halves are always rendered together. Every surface that names one
    without the other strands a reader in the nation it omits — the defect this
    whole release exists to close.
    """
    rf, ps = route(canon, "action-fraud"), route(canon, "police-scotland")
    rf_bit = brand(rf)
    if url:
        rf_bit += f" at {rf['report_url']}"
    if phone and rf.get("phone"):
        rf_bit += (" or on " if url else " on ") + rf["phone"]
    return (f"{rf_bit} for {rf['nation']}, or "
            f"{brand(ps)} on {ps.get('phone', '101')} for {ps['nation']}")


def police_report_sentence(canon: Dict, *, url: bool = True, phone: bool = True,
                           verb: str = "Report it to") -> str:
    return f"{verb} {police_report_clause(canon, url=url, phone=phone)}."


def consumer_advice_clause(canon: Dict, *, phones: bool = True) -> str:
    """The three nation consumer services, never presented as UK-wide."""
    parts = []
    for r in consumer_advice_routes(canon):
        bit = brand(r)
        if phones and r.get("phone"):
            bit += f" on {r['phone']}"
        parts.append(f"{bit} in {r['nation']}")
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + f", or {parts[-1]}"
    return parts[0] if parts else ""


def consumer_advice_sentence(canon: Dict, *, phones: bool = True) -> str:
    clause = consumer_advice_clause(canon, phones=phones)
    return f"{clause}." if clause else ""


def nation_routes_inline(canon: Dict) -> str:
    """A compact parenthetical listing every route family and its scope, for
    prompt preambles and short site prose."""
    rf, ps = route(canon, "action-fraud"), route(canon, "police-scotland")
    ncsc = route(canon, "ncsc-sers")
    return (f"{brand(rf)} for {rf['nation']}; {brand(ps)} on {ps.get('phone', '101')} "
            f"for {ps['nation']}; {brand(ncsc)}; and the consumer service for the "
            f"reader's nation")


def reporting_section_instruction(canon: Dict) -> str:
    """The generator's 'how to report it' section brief. Previously hand-typed
    beside the prompt that already carried `render_prompt_routes()`, so the two
    could disagree about the same six routes."""
    rf, ps = route(canon, "action-fraud"), route(canon, "police-scotland")
    ncsc, sms = route(canon, "ncsc-sers"), route(canon, "report-spam-sms")
    return (
        "How to report it in the UK — specific routes with org names, taken from the verified "
        "canon in content/sources.json and SCOPED BY NATION: "
        f"{brand(rf)} ({rf['phone']}) for {rf['nation']} and {brand(ps)} on "
        f"{ps.get('phone', '101')} for {ps['nation']}; "
        f"{brand(ncsc)} Suspicious Email Reporting Service ({ncsc.get('email', '')}); "
        f"forward SMS to {sms.get('sms', '7726')}; and the consumer service for the reader's "
        f"nation — {consumer_advice_clause(canon)}. "
        f"Never present {brand(route(canon, 'citizens-advice'))} as a UK-wide helpline. "
        "(120-150 words)"
    )


def route_scope_rule(canon: Dict) -> str:
    """The generator's closing 'keep the scope' rule."""
    rf, ps = route(canon, "action-fraud"), route(canon, "police-scotland")
    return (
        "Keep the official reporting routes above accurate and unchanged, INCLUDING their nation "
        f"scope: {brand(rf)} covers {rf['nation']}, {brand(ps)} on {ps.get('phone', '101')} "
        f"covers {ps['nation']}, and the consumer service differs by nation"
    )


def render_prompt_routes(canon: Dict) -> str:
    """The nation-scoped routing rules block shared by every model prompt —
    the generator system prompt, the accuracy block, the LLM judge and the
    scam checker. Previously hand-typed in five places."""
    rf, ps = route(canon, "action-fraud"), route(canon, "police-scotland")
    lines = ["- REPORTING ROUTES ARE NATION-SPECIFIC and must always be given together:"]
    lines.append(f"  • Report Fraud ({rf.get('report_url', '')}"
                 f"{', ' + rf['phone'] if rf.get('phone') else ''}) covers {rf['nation']} ONLY.")
    lines.append(f"  • Police Scotland on {ps.get('phone', '101')} "
                 f"({ps.get('report_url', '')}) is the route for {ps['nation']}.")
    lines.append("  Never present Report Fraud as the UK-wide route, and never give it without the "
                 "Scottish alternative in the same instruction.")
    lines.append("- Consumer advice is nation-specific too:")
    for r in consumer_advice_routes(canon):
        lines.append(f"  • {short_name(r)}{' on ' + r['phone'] if r.get('phone') else ''} — {r['nation']}.")
    lines.append("  Never present Citizens Advice as a UK-wide helpline.")
    return "\n".join(lines)


def phone_digits(canon: Dict) -> set:
    """Every phone number the gate will accept in prose, digits only.

    verified_org_contacts is a deliberately separate list: a company's own
    support line is NOT a national reporting route and never surfaces in the
    sidebar, but a guide may name one when the company's own site publishes it.
    """
    import re
    digits = set()
    for r in canon.get("official_routes", []):
        for field in ("phone", "sms", "phone_welsh"):
            if r.get(field):
                d = re.sub(r"\D", "", str(r[field]))
                if d:
                    digits.add(d)
    for r in canon.get("verified_org_contacts", []):
        if r.get("phone"):
            d = re.sub(r"\D", "", str(r["phone"]))
            if d:
                digits.add(d)
    return digits


def report_emails(canon: Dict) -> set:
    emails = {e.strip().lower() for e in canon.get("report_emails", []) if e}
    for r in canon.get("official_routes", []):
        if r.get("email"):
            emails.add(str(r["email"]).strip().lower())
    return emails


# ─── NEGATIVE FIXTURES ───────────────────────────────────────────────────────
# Run against every consumer of the canon, so "the gate and the build share one
# validator" is a tested property rather than a claim in a docstring.

def _valid_fixture() -> Dict:
    """A minimal canon that MUST validate. Mutated by the negative fixtures."""
    return {
        "report_emails": ["report@phishing.gov.uk"],
        "official_routes": [
            {"key": "action-fraud", "name": "Report Fraud (formerly Action Fraud)", "brand": "Report Fraud",
             "report_url": "https://www.reportfraud.police.uk", "phone": "0300 123 2040",
             "report_label": "Report Fraud — England, Wales and Northern Ireland",
             "nation": "England, Wales and Northern Ireland", "role": "police-report",
             "on_page": True},
            {"key": "police-scotland", "name": "Police Scotland non-emergency reporting (Scotland)", "brand": "Police Scotland",
             "report_url": "https://www.scotland.police.uk/contact-us/non-emergencies/",
             "phone": "101", "report_label": "Police Scotland on 101 — Scotland",
             "nation": "Scotland", "role": "police-report", "on_page": True},
            {"key": "ncsc-sers", "name": "National Cyber Security Centre", "brand": "NCSC",
             "report_url": "https://www.ncsc.gov.uk/collection/phishing-scams",
             "email": "report@phishing.gov.uk", "report_label": "NCSC — report phishing",
             "nation": "United Kingdom", "role": "phishing-report", "on_page": True},
            {"key": "citizens-advice", "name": "Citizens Advice consumer helpline (England and Wales)", "brand": "Citizens Advice",
             "report_url": "https://www.citizensadvice.org.uk/consumer/scams/reporting-a-scam/",
             "phone": "0808 223 1133", "report_label": "Citizens Advice (England and Wales)",
             "nation": "England and Wales", "role": "consumer-advice", "on_page": True},
            {"key": "advice-direct-scotland", "name": "Advice Direct Scotland consumer helpline (Scotland)", "brand": "Advice Direct Scotland",
             "report_url": "https://www.advice.scot/", "phone": "0808 800 9060",
             "report_label": "Advice Direct Scotland (Scotland)",
             "nation": "Scotland", "role": "consumer-advice", "on_page": True},
            {"key": "consumerline-ni", "name": "Consumerline consumer helpline (Northern Ireland)", "brand": "Consumerline",
             "report_url": "https://www.nidirect.gov.uk/contacts/consumerline", "phone": "0300 123 6262",
             "report_label": "Consumerline (Northern Ireland)",
             "nation": "Northern Ireland", "role": "consumer-advice", "on_page": True},
        ],
    }


def _drop(canon: Dict, key: str) -> Dict:
    canon["official_routes"] = [r for r in canon["official_routes"] if r.get("key") != key]
    return canon


def _edit(canon: Dict, key: str, **fields) -> Dict:
    for r in canon["official_routes"]:
        if r.get("key") == key:
            r.update(fields)
    return canon


def negative_fixtures() -> List[tuple]:
    """(description, canon) pairs that MUST be rejected by validate_canon()."""
    import copy

    def m(fn):
        return fn(copy.deepcopy(_valid_fixture()))

    return [
        ("non-object root is rejected", []),
        ("empty canon is rejected", {}),
        ("empty official_routes is rejected", m(lambda c: {**c, "official_routes": []})),
        ("empty report_emails is rejected", m(lambda c: {**c, "report_emails": []})),
        ("a missing required route is rejected", m(lambda c: _drop(c, "police-scotland"))),
        ("a missing consumer-advice nation is rejected", m(lambda c: _drop(c, "consumerline-ni"))),
        ("a duplicate route key is rejected",
         m(lambda c: {**c, "official_routes": c["official_routes"] + [dict(c["official_routes"][0])]})),
        ("a wrong route role is rejected", m(lambda c: _edit(c, "citizens-advice", role="police-report"))),
        ("a wrong route nation is rejected",
         m(lambda c: _edit(c, "citizens-advice", nation="United Kingdom"))),
        ("a non-https report_url is rejected",
         m(lambda c: _edit(c, "action-fraud", report_url="http://www.reportfraud.police.uk"))),
        ("a hostless https report_url is rejected",
         m(lambda c: _edit(c, "action-fraud", report_url="https://"))),
        ("an unofficial host is rejected",
         m(lambda c: _edit(c, "action-fraud", report_url="https://reportfraud.example.com"))),
        ("the RIGHT host on the WRONG required route is rejected",
         m(lambda c: _edit(c, "advice-direct-scotland", report_url="https://www.citizensadvice.org.uk/"))),
        ("a required route demoted from on_page is rejected",
         m(lambda c: _edit(c, "police-scotland", on_page=False))),
        ("a required route with no phone is rejected",
         m(lambda c: _edit(c, "advice-direct-scotland", phone=""))),
        ("an on-page route with no report_label is rejected",
         m(lambda c: _edit(c, "consumerline-ni", report_label=""))),
        ("one fabricated label naming every nation does NOT satisfy coverage",
         m(lambda c: _edit(_drop(c, "advice-direct-scotland"), "citizens-advice",
                           report_label="Citizens Advice — England, Wales, Scotland and Northern Ireland"))),
    ]
