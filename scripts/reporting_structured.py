"""Restricted canonical actions and typed publication projections.

Only closed explicit canon contracts confer action capability. Public writers,
renderers and the publication gate authenticate whole-page review through
reporting_publication. Legacy per-field contexts remain diagnostic/test inputs,
never production signing authority. Arbitrary English still needs human review.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from calendar import monthrange
from hashlib import sha256
from html import escape, unescape
import json
import re
from types import MappingProxyType
import unicodedata
from urllib.parse import unquote
from reporting_syntax import (INVALID_MARKDOWN_LINK_RE, INTERNAL_PATH,
    INTERNAL_MARKDOWN_LINK_RE, normalize_phone, numeric_fragments, inline_html,
    schema_plain, normalize_bullet_body, parse_numbered_steps, howto_step_text)
from reporting_output import (ArticleText, ArticleHTML, CanonRoutes, Citation, Fragment,
    Capability, Provenance, TextUse, InternalLink, field_provenance)
from reporting_network import https_identity, raw_network_destinations

LEGACY_DIAGNOSTIC = "legacy_diagnostic"
STRUCTURED_REQUIRED = "structured_required"
MAX_ROUTES = 32
_PART = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
_PART_RE = re.compile(_PART, re.ASCII)
_ID_RE = re.compile(_PART + ":" + _PART, re.ASCII)
_HASH_RE = re.compile(r"[0-9a-f]{64}", re.ASCII)
_GROUPS = ("official_routes", "verified_org_contacts", "verified_number_sources")
_KINDS = frozenset({"url", "email", "phone", "shortcode", "voice-shortcode"})
_MODES = frozenset({"intake", "support", "protection", "verification", "navigation"})
_NATIONS = ("England", "Wales", "Scotland", "Northern Ireland", "Global")
_DEST_FIELDS = frozenset({"report_url", "info_url", "navigation_url", "email",
                          "phone", "phone_welsh", "sms"})
_SERVICE_FIELDS = _DEST_FIELDS | frozenset({"key", "name", "brand", "nation", "role",
    "note", "on_page", "report_label", "source_url", "checked_on", "purpose",
    "requires_named_owner", "actions"})
_ACTION_FIELDS = frozenset({"action_type", "purpose", "mode", "jurisdictions", "condition_ids",
    "instruction", "limitation_ids", "companions", "status", "source_url", "checked_on",
    "schema_version", "eligibility_ids", "qualifier_ids"})
_REQUIRED_ACTION = _ACTION_FIELDS - {"source_url", "checked_on"}
_CONDITION_KINDS = frozenset({"evidence", "age", "customer", "eligibility"})
_PAGE_FIELDS = frozenset({"slug", "title", "description", "hero", "quick_answer", "intro",
    "category", "keywords", "date", "updated", "dateModified", "sections", "faq", "figure",
    "sources_checked", "evidence", "message_examples", "content", "excerpt", "consolidated_into",
    "ads_mode", "reporting_routes"})


class ReportingError(ValueError):
    """Invalid contract, reference or structured page. Never a fallback signal."""


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def unique_object(pairs):
    """json.loads object_pairs_hook: reject shadowed authority before dict creation."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReportingError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _fail(where, message):
    raise ReportingError(f"{where}: {message}")


def _text(value, where, limit=600):
    if (not isinstance(value, str) or not value or value != value.strip()
            or len(value) > limit or any(unicodedata.category(c).startswith("C") for c in value)):
        _fail(where, "expected bounded, nonempty plain text without surrounding whitespace/control characters")
    return value


def validate_route_id(value):
    if (not isinstance(value, str) or not _ID_RE.fullmatch(value)
            or any(len(part) > 64 for part in value.split(":"))):
        _fail("route ID", "expected two lowercase ASCII slug components (1–64 chars) separated by one colon")
    return value


def _slug(value, where):
    if not isinstance(value, str) or len(value) > 64 or not _PART_RE.fullmatch(value):
        _fail(where, "expected a lowercase ASCII slug of 1–64 characters")
    return value


def _date(value, where):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        _fail(where, "expected YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError:
        _fail(where, "invalid calendar date")


def validate_url(value, where="URL", *, citation=False):
    _text(value, where, 2048)
    try:
        https_identity(value, unicode_host=citation)
    except ValueError as exc:
        _fail(where, f"invalid URL: {exc}")
    # Canon remains exact ASCII; reviewed citations preserve Unicode source
    # bytes too. The comparison representation never replaces either value.
    return value


def _destination(kind, value, where):
    if not isinstance(kind, str) or kind not in _KINDS:
        _fail(where, "unknown destination kind")
    _text(value, where, 2048)
    if kind == "url":
        validate_url(value, where)
    elif kind == "email":
        if (not re.fullmatch(r"[A-Za-z0-9_+.-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+", value)
                or ".." in value or value.startswith(".") or ".@" in value):
            _fail(where, "invalid mailbox; query/header data is forbidden")
        validate_url("https://" + value.split("@")[1], where + ".domain")
    elif kind == "phone":
        if not re.fullmatch(r"\+?[0-9]+(?: [0-9]+)*", value):
            _fail(where, "canonical phones use digits, single spaces and an optional leading plus")
        if normalize_phone(value, kind=kind) is None:
            _fail(where, "phones require 7–15 digits; shortcodes have their own kind")
    elif not re.fullmatch(r"[0-9]+", value) or normalize_phone(value, kind=kind) is None:
        _fail(where, "shortcodes require 3–6 ASCII digits")
    return Destination(kind, value)


@dataclass(frozen=True)
class Destination:
    kind: str
    value: str


@dataclass(frozen=True)
class Action:
    route_id: str
    owner: str
    service: str
    purpose: str
    mode: str
    jurisdictions: tuple
    channels: tuple
    label: str
    method: str
    conditions: tuple
    limitations: tuple
    companions: tuple
    status: str
    source_url: str
    checked_on: str
    owner_id: str = ''
    service_id: str = ''
    action_type: str = ''
    template_id: str = ''
    condition_ids: tuple = ()
    limitation_ids: tuple = ()
    numbering_context: str = ''
    destination_field: str = ''
    attributions: tuple = ()
    schema_version: str = ''
    eligibility_ids: tuple = ()
    qualifier_ids: tuple = ()
    recipient_relation: str = ''
    payload_profile_id: str = ''
    dialling_network_id: str = ''
    resolution_kind: str = ''


@dataclass(frozen=True, kw_only=True)
class ComposedSmsAction(Action):
    sms_composition_case_id: str
    sms_composition: object


def validate_composed_sms(action):
    from reporting_actions import VERSION, sms_composition
    if action.schema_version == VERSION:
        if (type(action) is not ComposedSmsAction
                or action.sms_composition != sms_composition(action.sms_composition_case_id)):
            _fail('SMS composition', 'resolved case differs from the closed registry')
    elif type(action) is not Action:
        _fail('SMS composition', 'composition requires v3 schema')


def narrative_faq(post):
    """Explanatory pairs only; typed placements have their own projections."""
    return [item for item in post.get('faq', []) if isinstance(item, (list, tuple)) and len(item) == 2]


@dataclass(frozen=True)
class ReportingDestination:
    """Resolver-issued occurrence; never constructed from prose or citations.

    Trusted Python constructors are not a sandbox. At each consumption point
    the action and channel must be the objects held by this reviewed catalogue.
    Draft JSON cannot supply an instance or a capability override.
    """
    catalog: Catalog
    action: Action
    channel: Destination

    def __post_init__(self):
        self.catalog.validate_destination(self)

    @property
    def canon_sha256(self):
        return self.catalog.canon_sha256

    @property
    def capability(self):
        return Capability.REPORTING_ACTION

    @property
    def provenance(self):
        return Provenance.REPORTING_ROUTE

    @property
    def value(self):
        return self.channel.value


@dataclass(frozen=True)
class Catalog:
    canon_sha256: str
    actions: object

    def resolve(self, route_id):
        validate_route_id(route_id)
        action = self.actions.get(route_id)
        if action is None or action.status != "active":
            _fail(route_id, "unknown or withdrawn canonical action")
        validate_composed_sms(action)
        return action

    def select(self, route_ids):
        if not isinstance(route_ids, list) or len(route_ids) > MAX_ROUTES:
            _fail("reporting_routes", f"expected a list of at most {MAX_ROUTES} IDs")
        for value in route_ids:
            validate_route_id(value)
        if len(set(route_ids)) != len(route_ids):
            _fail("reporting_routes", "duplicate action ID")
        actions = tuple(self.resolve(value) for value in sorted(route_ids))
        caller_actions = [a for a in actions if a.template_id == 'report-caller-number-sms']
        if (any(type(a) is ComposedSmsAction for a in caller_actions)
                and any(type(a) is Action for a in caller_actions)):
            _fail('reporting_routes', 'generic and O2 composed caller-SMS actions conflict')
        for action in actions:
            missing = set(action.companions) - set(route_ids)
            if missing:
                _fail(action.route_id, f"required companion action(s) absent: {sorted(missing)}")
        return actions

    def destinations(self, route_ids):
        return tuple(ReportingDestination(self, action, channel)
                     for action in self.select(route_ids) for channel in action.channels)

    def validate_destination(self, node):
        if (type(node) is not ReportingDestination or node.catalog is not self
                or self.resolve(node.action.route_id) is not node.action
                or not any(channel is node.channel for channel in node.action.channels)):
            _fail('reporting destination', 'not issued by this resolved canon contract')


def catalog_from_canon(canon, *, expected_digest=None):
    """Only closed, explicitly evidenced action contracts confer capability."""
    from reporting_action_canon import catalog
    try:
        return catalog(canon, expected_digest)
    except (TypeError, KeyError, AttributeError) as exc:
        _fail('canon', 'malformed restricted action contract: ' + str(exc))


@dataclass(frozen=True)
class ReviewContext:
    """Resolved review data, never an article field or authentication token.

    Publication entry points accept a verified external signed packet only.
    Direct construction remains useful for lower-level diagnostic fixtures.
    """
    canon_sha256: str
    page_sha256: str
    allowed_route_ids: tuple
    reviewed_on: str
    citations: tuple = ()
    allow_empty: bool = False
    numeric_facts: tuple = ()
    page_id: str = ''
    prose_approvals: tuple = ()
    editorial_decision: object = None


PROSE_APPROVAL_VERSION = 'reporting-prose/v1'
PROSE_APPROVAL_SCOPE = 'contextual-prose-without-destination-authority'


@dataclass(frozen=True)
class ProseApproval:
    """External human semantic decision, NOT derived from an article or parser.

    The reviewer approves this field in the complete page context, including
    that it does not repurpose citations, facts or navigation as off-canon
    reporting channels. This permission only releases prose for display. It
    cannot exempt a raw destination or confer REPORTING_ACTION capability.
    """
    page_id: str
    field_id: str
    content_sha256: str
    page_sha256: str
    scope: str
    reviewer: str
    approved_at: str
    canon_sha256: str
    schema_version: str = PROSE_APPROVAL_VERSION


def prose_hash(text):
    """Exact UTF-8 bytes: no whitespace, Unicode or Markdown normalisation."""
    return sha256(text.encode('utf-8')).hexdigest()


def approval_fields(post):
    # Every free-form field is potentially instructional. Do not infer risk or
    # approval from vocabulary. Include citation labels, never their URL value.
    yield from prose_fields(post)
    for index, (label, _) in enumerate(post.get('sources_checked', [])):
        yield f'sources_checked/{index}/0', label


def validate_prose_approvals(post, review, *, page_id=None):
    expected_id = 'guide:' + post['slug'] if 'slug' in post else page_id or review.page_id
    if (not isinstance(expected_id, str) or len(expected_id) > 262
            or not re.fullmatch(r'(?:guide|hub):[a-z0-9]+(?:-[a-z0-9]+)*', expected_id)
            or review.page_id != expected_id
            or (page_id is not None and page_id != expected_id)
            or ('slug' not in post and not expected_id.startswith('hub:'))):
        _fail('prose approval', 'missing or wrong page identity')
    if review.editorial_decision is not None:
        from reporting_publication import EditorialDecision, SCOPE, dependencies
        d = review.editorial_decision
        if (type(d) is not EditorialDecision or d.page_id != expected_id
                or d.page_sha256 != digest(post) or d.canon_sha256 != review.canon_sha256
                or d.scope != SCOPE or d.dependency_digests != dependencies()):
            _fail('editorial decision', 'whole-page review binding mismatch')
        return  # Authentication is mandatory at publication entry points.
    if not isinstance(review.prose_approvals, tuple):
        _fail('prose approval', 'expected immutable external approvals')
    fields = dict(approval_fields(post))
    seen = set()
    for approval in review.prose_approvals:
        if (type(approval) is not ProseApproval or not isinstance(approval.field_id, str)
                or approval.field_id in seen
                or approval.field_id not in fields or approval.page_id != expected_id
                or approval.page_sha256 != review.page_sha256
                or approval.canon_sha256 != review.canon_sha256
                or approval.schema_version != PROSE_APPROVAL_VERSION
                or approval.scope != PROSE_APPROVAL_SCOPE
                or approval.content_sha256 != prose_hash(fields[approval.field_id])):
            _fail('prose approval', 'invalid, stale, duplicate or out-of-scope field approval')
        _text(approval.reviewer, 'prose approval reviewer', 256)
        try:
            timestamp = datetime.fromisoformat(approval.approved_at.replace('Z', '+00:00'))
            if (timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp)
                    or timestamp.date() > _date(review.reviewed_on, 'reviewed_on')):
                raise ValueError('approval timestamp must be UTC and not future-dated')
        except (AttributeError, TypeError, ValueError):
            _fail('prose approval', 'invalid approval timestamp')
        seen.add(approval.field_id)
    if set(fields) != seen:
        _fail('prose approval', 'unapproved reader-facing fields: ' + ', '.join(sorted(set(fields) - seen)))


@dataclass(frozen=True)
class NumericFact:
    """Separately reviewed complete field, never a destination-string whitelist.

    Values stay plain text; kind describes data, not permission to contact it.
    A reviewer must approve the whole non-instructional field in this page.
    """
    path: str
    text: str
    kind: str


def page_mode(post, requested=LEGACY_DIAGNOSTIC):
    if requested not in (LEGACY_DIAGNOSTIC, STRUCTURED_REQUIRED):
        _fail("reporting mode", "unknown validation mode")
    return STRUCTURED_REQUIRED if "reporting_routes" in post else requested


def prose_fields(post):
    """All unrestricted strings, including figures/examples and unknown nested keys.

    Citations have a separate exact reviewed representation. Dead legacy fields
    are never rendered. Dates/slugs are schema-checked metadata, not prose.
    """
    def walk(value, path):
        if isinstance(value, str):
            yield path, value
        elif isinstance(value, (list, tuple)):
            for n, child in enumerate(value):
                yield from walk(child, f"{path}/{n}")
        elif isinstance(value, dict):
            if value.get('kind') in ('action-faq', 'action-summary'):
                return  # Validated as a closed placement before prose traversal.
            for key, child in value.items():
                if path == "figure" and key == "type":
                    continue  # Closed renderer discriminator, not prose.
                yield from walk(child, f"{path}/{key}")
    skipped = {"reporting_routes", "sources_checked", "content", "excerpt", "slug",
               "date", "updated", "dateModified", "consolidated_into", "category", "ads_mode"}
    for key, value in post.items():
        if key not in skipped:
            yield from walk(value, key)


def _raw_destinations(text, *, numeric_fact=False):
    """Reject representations only. No instruction, owner or service inference.

    Ambiguous three-plus-digit prose numbers are held for review, including
    amounts/years; typed date metadata is separate. A reviewed complete numeric
    field can suppress only the numeric hold, never the network detector.
    """
    # Check the original target too: decoding must not repair invalid Markdown
    # into a supported path when the actual renderer never decodes it.
    if INVALID_MARKDOWN_LINK_RE.search(text):
        return ["unsupported Markdown target"]
    value = text
    for _ in range(3):
        decoded = unquote(unescape(value))
        # Inspect before compatibility folding can erase unsupported numeric
        # characters revealed by an entity/escape (e.g. an encoded circled 1).
        if any(unicodedata.category(c) in ("Nl", "No") for c in decoded):
            return ["unsupported numeric character"]
        decoded = unicodedata.normalize("NFKC", decoded)
        if decoded == value:
            break
        value = decoded
    if any(unicodedata.category(c) in ("Cf", "Cc") and c not in "\n\r\t" for c in text + value):
        return ["control or hidden Unicode character"]
    if any(unicodedata.category(c) in ("Nl", "No") for c in text + value):
        return ["unsupported numeric character"]
    if re.search(r"%[0-9a-f]{2}|&#|</?[a-z][^>]*>", value, re.I):
        return ["encoded value or raw HTML"]
    # Decoding + NFKC reaches a bounded closure; residual encodings above reject
    # even when a width character revealed them in the last iteration. This
    # NEVER feeds canon admission, equality or rendering; phones retain NFC/Nd.
    if INVALID_MARKDOWN_LINK_RE.search(value):
        return ["unsupported Markdown target"]
    found = raw_network_destinations(value)
    if not numeric_fact:
        found.extend("numeric review required: " + number for number in numeric_fragments(value))
    return found


def raw_destinations(text):
    """Scan source AND the actual supported inline/plain projections."""
    values = (text, normalize_bullet_body(text))
    for value in values:
        for effective in (value, Fragment(inline_html(value)).text, schema_plain(value)):
            found = _raw_destinations(effective)
            if found:
                return found
    return []


from reporting_prose import FACT_PATTERNS as _FACT_PATTERNS


def _numeric_fact(path, text, review):
    for fact in review.numeric_facts:
        if (not isinstance(fact, NumericFact) or fact.kind not in _FACT_PATTERNS
                or not re.fullmatch(_FACT_PATTERNS[fact.kind] + r'\.?', fact.text, re.ASCII)):
            _fail('numeric facts', 'invalid reviewed numeric declaration')
        if fact.path == path:
            # Whitespace collapse is the browser/figure transformation; no
            # markup, number mutation, instruction or substring exemption.
            return ' '.join(text.split()) == ' '.join(fact.text.split())
    return _ordinary_numeric_field(' '.join(text.split()))


def _ordinary_numeric_field(text):
    """Classify a whole labelled fact, never an arbitrary numeric substring.

    A label plus a complete narrow data grammar is non-instructional syntax.
    Bare values and any additional instruction remain held. IP literals and
    high-precision decimals are ambiguous enough to require NumericFact review.
    This grants no reporting authority and does not resolve human semantics.
    """
    for kind, pattern in _FACT_PATTERNS.items():
        if kind == 'ip' or not re.fullmatch(pattern + r'\.?', text, re.ASCII):
            continue
        digits = re.findall(r'[0-9]', text)
        if kind in ('version', 'decimal') and len(digits) > 6:
            return False
        if kind == 'date':
            from datetime import datetime
            value = text.split(' ', 1)[1].rstrip('.')
            for fmt in ('%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%Y/%m/%d'):
                try:
                    parsed = datetime.strptime(value, fmt)
                    return 1900 <= parsed.year <= 2100
                except ValueError:
                    pass
            return False
        return True
    return False


def validate_effective(nodes, catalog, review):
    """Last article boundary: typed values after conversion, before assembly.

    Canon nodes resolve IDs anew. Citation nodes match the separately reviewed
    tuple. Neither accepts caller-supplied exempt HTML. Article HTML attributes
    are parsed, and adjacent inline text nodes are scanned as one value.
    """
    uses = []
    for node in nodes:
        from reporting_taxonomy import TaxonomyUse
        if type(node) is TaxonomyUse:
            uses.append(node.validate())
            continue
        from reporting_action_render import ActionComponent, components
        if type(node) is ActionComponent:
            node.validate()
            if node.catalog is not catalog or node.action.route_id not in review.allowed_route_ids:
                _fail('effective action', 'foreign or unreviewed action component')
            uses.append(node)
            continue
        if isinstance(node, CanonRoutes):
            if set(node.route_ids) - set(review.allowed_route_ids):
                _fail('effective canon', 'unapproved route selection')
            uses.extend(components(catalog, list(node.route_ids)))
            continue
        if isinstance(node, ReportingDestination):
            _fail('effective canon', 'destination-only projections are forbidden; use a complete action component')
        if isinstance(node, Citation):
            if (node.label, node.url) not in review.citations:
                _fail('effective citation', 'unreviewed source')
            validate_url(node.url, 'citation URL', citation=True)
            from reporting_prose import require_explanatory
            require_explanatory(node.label, 'citation label')
            uses.append(node)
            continue
        paths = node.source_paths or (node.path,) if isinstance(node, (ArticleHTML, ArticleText)) else ()
        if isinstance(node, ArticleHTML):
            parsed = Fragment(node.html)
            for href in parsed.hrefs:
                if not re.fullmatch(INTERNAL_PATH, href, re.I | re.ASCII):
                    _fail(node.path, 'effective article href is not an internal path')
                from reporting_publication import internal_target
                if not internal_target(href):
                    _fail(node.path, 'internal navigation target is not in the trusted route map')
                uses.append(InternalLink(paths, href))
            values = [parsed.text] + parsed.attributes
        elif isinstance(node, ArticleText):
            values = [node.text]
        else:
            _fail('effective output', 'unknown provenance')
        for text in values:
            fact = _numeric_fact(node.path, text, review)
            found = _raw_destinations(text, numeric_fact=fact)
            if found:
                _fail(node.path, f'effective raw destination is prohibited: {found[0]!r}')
            from reporting_prose import require_explanatory
            try:
                require_explanatory(text, node.path)
            except ValueError as exc:
                _fail(node.path, str(exc))
            uses.append(TextUse(paths, text, Provenance.NUMERIC_FACT if fact else
                                field_provenance(paths[0]), node.projection))
    return tuple(uses)


def effective_prose(post):
    """Shared conversion closure used by gate, writers and direct rendering.

    Include a conservative schema projection for every field. This also closes
    unmatched-backtick metadata/HowTo removal and legacy literal decoding.
    Actual renderer fragments are checked again at the final render boundary.
    """
    if 'category' in post:
        from reporting_taxonomy import resolve
        yield resolve(post['category'])
    for path, text in approval_fields(post):
        # Only section bodies and hub introductions use the legacy list
        # converter. Never let a lossy source parser hide literal metadata/FAQ.
        if path == 'intro' or re.fullmatch(r'sections/[0-9]+/1', path):
            from reporting_prose import body_text
            value = body_text(text, path)
        else:
            value = text
        yield ArticleText(path, value)
        yield ArticleHTML(path, inline_html(value))
        yield ArticleText(path, schema_plain(value), projection='schema')
    if 'keywords' in post:
        yield ArticleText('keywords/joined', ', '.join(post['keywords']), projection='schema',
                          source_paths=tuple(f'keywords/{n}' for n in range(len(post['keywords']))))
    for index, (_, body) in enumerate(post.get('sections', [])):
        for step, value in enumerate(parse_numbered_steps(normalize_bullet_body(body))[:8]):
            yield ArticleText(f'sections/{index}/1/howto/{step}', howto_step_text(value),
                              projection='schema', source_paths=(f'sections/{index}/1',))


def validate_page(post, catalog, review, *, mode=STRUCTURED_REQUIRED, page_id=None):
    """Return exact canon actions; legacy diagnostics never return permission."""
    if not isinstance(post, dict):
        _fail("page", "expected an object")
    if page_mode(post, mode) != STRUCTURED_REQUIRED:
        _fail("page", "legacy diagnostic mode does not authorise rendering")
    unknown = set(post) - _PAGE_FIELDS
    if unknown:
        _fail("page", f"unknown fields (no route overrides): {sorted(unknown)}")
    for field in ("title", "description", "hero", "intro", "category"):
        if field in post and not isinstance(post[field], str):
            _fail(field, "reader-visible text must be a string, never coerced")
    if "keywords" in post and (not isinstance(post["keywords"], list)
            or any(not isinstance(value, str) for value in post["keywords"])):
        _fail("keywords", "expected a list of strings")
    # These renderers stringify values in legacy mode. Do not let numeric or
    # nested objects evade string scanning and become raw destinations later.
    def text_object(value, keys, where):
        if (not isinstance(value, dict) or set(value) - keys
                or any(not isinstance(v, str) for v in value.values())):
            _fail(where, "expected known string fields only")
    for field, keys in (("evidence", {"signal", "finding", "basis"}),
                        ("message_examples", {"label", "message", "assessment"})):
        if field in post:
            if not isinstance(post[field], list):
                _fail(field, "expected a list")
            for index, value in enumerate(post[field]):
                text_object(value, keys, f"{field}/{index}")
    if "figure" in post:
        figure = post["figure"]
        if not isinstance(figure, dict) or set(figure) - {"type", "title", "alt", "caption", "steps"}:
            _fail("figure", "expected known figure fields")
        text_object({k: v for k, v in figure.items() if k != "steps"},
                    {"type", "title", "alt", "caption"}, "figure")
        if "steps" in figure:
            if not isinstance(figure["steps"], list):
                _fail("figure/steps", "expected a list")
            for index, value in enumerate(figure["steps"]):
                text_object(value, {"check", "then"}, f"figure/steps/{index}")
    if "ads_mode" in post and post["ads_mode"] not in ("none", "npa", "default"):
        _fail("ads_mode", "unknown advertising mode")
    if "category" in post:
        from reporting_taxonomy import resolve
        try:
            resolve(post['category'])
        except ValueError as exc:
            _fail('category', str(exc))
    for field, limit in (('title', 60), ('description', 160)):
        if len(schema_plain(post.get(field, ''))) > limit:
            _fail(field, 'structured metadata must fit without truncation')
    if 'figure' in post and post['figure'].get('type', 'decision-flow') != 'decision-flow':
        _fail('figure/type', 'unknown figure discriminator')
    actions = catalog.select(post.get("reporting_routes"))
    from reporting_action_render import placement
    qa = post.get('quick_answer', '')
    try:
        if isinstance(qa, dict):
            placement(qa, post['reporting_routes'], catalog)
        elif not isinstance(qa, str):
            _fail('quick_answer', 'expected explanatory text or a closed action summary')
        for item in post.get('faq', []):
            if isinstance(item, dict):
                placement(item, post['reporting_routes'], catalog, faq=True)
    except (ValueError, TypeError, KeyError) as exc:
        _fail('action placement', str(exc))
    if not isinstance(review, ReviewContext):
        _fail("review", "structured pages require a caller-supplied reviewed context")
    if (catalog.canon_sha256 != review.canon_sha256 or digest(post) != review.page_sha256
            or not _HASH_RE.fullmatch(review.canon_sha256 or "")
            or not _HASH_RE.fullmatch(review.page_sha256 or "")):
        _fail("review", "canon/page differs from the reviewed candidate")
    if not isinstance(review.allowed_route_ids, tuple):
        _fail("review", "allowed_route_ids must be an immutable tuple")
    allowed = catalog.select(list(review.allowed_route_ids))
    if set(post["reporting_routes"]) - {a.route_id for a in allowed}:
        _fail("reporting_routes", "known action is outside the reviewed purpose/scope selection")
    if type(review.allow_empty) is not bool or (not actions and not review.allow_empty):
        _fail("reporting_routes", "empty plan needs explicit reviewed approval")
    today = _date(review.reviewed_on, "reviewed_on")
    for action in actions:
        checked = _date(action.checked_on, action.route_id)
        month = checked.month + 3
        year = checked.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        expires = date(year, month, min(checked.day, monthrange(year, month)[1]))
        if not checked <= today <= expires:
            _fail(action.route_id, "evidence is future-dated or overdue at the pinned review date")
    for key in ("date", "updated", "dateModified"):
        if key in post:
            _date(post[key], key)
    if "slug" in post:
        slug = post["slug"]
        if not isinstance(slug, str) or len(slug) > 256 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            _fail("slug", "invalid page slug")
    for key in ("sections", "faq"):
        if key in post and (not isinstance(post[key], list) or any(
                (not (key == 'faq' and isinstance(pair, dict))) and (
                not isinstance(pair, (list, tuple)) or len(pair) != 2
                or any(not isinstance(s, str) for s in pair)) for pair in post[key])):
            _fail(key, "expected string pairs")
    citations = post.get("sources_checked", [])
    if not isinstance(citations, list) or any(not isinstance(p, (list, tuple)) or len(p) != 2
                                            or any(not isinstance(v, str) for v in p) for p in citations):
        _fail("sources_checked", "expected source label/URL pairs")
    if not isinstance(review.citations, tuple) or tuple(tuple(p) for p in citations) != review.citations:
        _fail("sources_checked", "not the exact separately reviewed citation list")
    for label, url in citations:
        _text(label, "citation label")
        validate_url(url, "citation URL", citation=True)
    # Citation labels are prose too. No page-wide vocabulary/proximity/equality
    # search can prove their semantic use; external contextual approvals do.
    fields = dict(approval_fields(post))
    if not isinstance(review.numeric_facts, tuple):
        _fail('numeric facts', 'expected immutable reviewed declarations')
    seen = set()
    for fact in review.numeric_facts:
        if (not isinstance(fact, NumericFact) or fact.path in seen
                or fields.get(fact.path) != fact.text or fact.kind not in _FACT_PATTERNS
                or not re.fullmatch(_FACT_PATTERNS[fact.kind] + r'\.?', fact.text, re.ASCII)):
            _fail('numeric facts', 'expected an exact, typed, non-instructional reviewed field')
        seen.add(fact.path)
    validate_prose_approvals(post, review, page_id=page_id)
    # Approval authenticates context. It never waives the action boundary.
    validate_effective(effective_prose(post), catalog, review)
    return actions


def page_uses(post, catalog, review):
    """Validated capability ledger before rendering; never rediscover authority.

    Identical citation/reporting bytes deliberately remain separate occurrences.
    """
    validate_page(post, catalog, review)
    return validate_effective((*effective_prose(post),
        *(Citation(label, url) for label, url in post.get('sources_checked', [])),
        CanonRoutes(tuple(post['reporting_routes']))), catalog, review)


def render_citation(node):
    if type(node) is not Citation:
        _fail('citation', 'expected a citation occurrence')
    validate_url(node.url, 'citation URL', citation=True)
    from reporting_prose import require_explanatory
    require_explanatory(node.label, 'citation label')
    return (f'<a href="{escape(node.url, quote=True)}" rel="noopener noreferrer" target="_blank">'
            f'{escape(node.label)}</a>')


def render_destination(catalog, node):
    catalog.validate_destination(node)
    channel, action = node.channel, node.action
    value = escape(channel.value, quote=True)
    owner = escape(action.owner)
    if channel.kind == 'url':
        return f'<a href="{value}" rel="noopener noreferrer">{owner} — {escape(action.label)}</a>'
    if channel.kind == 'email':
        return f'<a href="mailto:{value}">{owner}: {value}</a>'
    if channel.kind == 'phone':
        number = normalize_phone(channel.value, kind='phone')
        return f'<a href="tel:{number}">{owner}: {value}</a>'
    if channel.kind in ('shortcode', 'voice-shortcode'):
        return f'{owner}: <span class="reporting-shortcode">{value}</span>'
    _fail('destination renderer', 'unknown destination kind')


def ordered_actions(catalog, route_ids):
    """One protection-first order for all projections and approval identities."""
    return tuple(sorted(catalog.select(route_ids),
        key=lambda a: (0 if a.purpose == 'payment-recovery' else 1, a.route_id)))


def contract_model_sha256():
    from pathlib import Path
    from reporting_actions import VERSION
    paths = ('reporting_actions.py', 'reporting_action_canon.py', 'reporting_action_render.py',
             'reporting_structured.py', 'reporting_syntax.py')
    return digest({'schema_version': VERSION, 'files': {
        p: sha256(Path(__file__).with_name(p).read_bytes()).hexdigest() for p in paths}})


def action_plan(catalog, route_ids):
    from dataclasses import asdict
    from reporting_actions import VERSION
    return {'schema_version': VERSION, 'contract_model_sha256': contract_model_sha256(),
            'ordered_actions': [asdict(a) for a in ordered_actions(catalog, route_ids)]}


def action_plan_sha256(catalog, route_ids):
    return digest(action_plan(catalog, route_ids))


def action_descriptor(a):
    """Read-only selection metadata, without endpoints, notes or template prose."""
    result = {'route_id': a.route_id, 'schema_version': a.schema_version,
        'action_type': a.action_type, 'purpose': a.purpose,
        'condition_ids': list(a.condition_ids), 'eligibility_ids': list(a.eligibility_ids),
        'jurisdictions': list(a.jurisdictions), 'recipient_relation': a.recipient_relation,
        'payload_profile_id': a.payload_profile_id, 'resolution_kind': a.resolution_kind,
        'method_id': a.template_id, 'qualifier_ids': list(a.qualifier_ids),
        'limitation_ids': list(a.limitation_ids), 'dialling_network_id': a.dialling_network_id}
    validate_composed_sms(a)
    if type(a) is ComposedSmsAction:
        result.update(sms_composition_case_id=a.sms_composition_case_id,
            provider_scope_id=a.sms_composition.provider_scope_id,
            provider_owner_id=a.sms_composition.provider_owner_id)
    return result


def generator_contract(catalog, allowed_route_ids):
    """Offline interface only. Complete eligible IDs are the only writable choice."""
    from reporting_actions import VERSION
    actions = ordered_actions(catalog, list(allowed_route_ids))
    return {'schema_version': VERSION, 'contract_model_sha256': contract_model_sha256(),
        'allowed_reporting_routes': [a.route_id for a in actions],
        'actions': [action_descriptor(a) for a in actions],
        'instruction': 'Select only these exact complete reporting_routes IDs. All descriptors are read-only and cannot be overridden. Narrative must be explanatory: reporting, contact, forwarding, submission and external-navigation instructions belong only in actions. Never supply destinations, recipients, payloads, template prose, policy fields, evidence notes or approvals. Unknown IDs or extra fields quarantine the draft.'}


def render_block(catalog, route_ids):
    from reporting_action_render import block
    return block(catalog, route_ids)


def render_plain(catalog, route_ids):
    from reporting_action_render import components
    return '\n'.join(node.plain() for node in components(catalog, route_ids))
