"""Trusted mode policy and authenticated whole-page editorial decisions.

The frozen snapshot is compatibility data, not approval of new prose. Production
entry points consult it before normalization and load signed decisions from an
operator-controlled external directory. Draft JSON and raw ReviewContext objects
cannot configure keys, legacy mode, expiry or revocation.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta, date
from dataclasses import dataclass
import json
import os
import subprocess
import tempfile
import hashlib
import reporting_trust as trust

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path(__file__).with_name('reporting_legacy_snapshot.json')
NAMESPACE = 'beatthescam-publication-v4'
SCOPE = 'whole-page-context-and-evidence-only'
DEPENDENCIES = ('scripts/reporting_publication.py', 'scripts/reporting_legacy_snapshot.json',
    'scripts/reporting_structured.py', 'scripts/reporting_actions.py', 'scripts/reporting_action_canon.py',
    'scripts/reporting_action_render.py', 'scripts/reporting_prose.py', 'scripts/reporting_taxonomy.py', 'scripts/reporting_output.py',
    'scripts/reporting_network.py', 'scripts/reporting_syntax.py', 'scripts/canon.py',
    'scripts/build.py', 'scripts/content_gate.py', 'scripts/generate_content_claude.py',
    'scripts/search_console_articles.py', 'scripts/rewrite_thin_guides.py', 'scripts/merge_new_posts.py',
    'scripts/corpus.py', 'templates/base.html', 'assets/app.js', 'assets/styles.css',
    'content/site.json', 'netlify.toml', 'requirements-reporting.txt',
    'scripts/reporting_trust.py', 'scripts/reporting_eligibility.py', 'scripts/reporting_pilot.py',
    'scripts/reporting_reviewer.py', 'scripts/reporting_provider.py', 'scripts/reporting_runtime.py', 'scripts/reporting-runtime.json',
    '.python-version', '.nvmrc', 'package.json', 'package-lock.json', 'requirements-reporting.lock',
    'scripts/reporting_revision.py', 'scripts/reporting_workflow.py')


def page_identity(post, page_id=None):
    return page_id or ('guide:' + post.get('slug', ''))


def legacy_unchanged(post, page_id=None):
    import reporting_structured as s
    manifest = json.loads(SNAPSHOT.read_text(), object_pairs_hook=s.unique_object)
    return ('reporting_routes' not in post and s.digest(post) in
            manifest['pages'].get(page_identity(post, page_id), []))


def required(post, page_id=None):
    return not legacy_unchanged(post, page_id)


def internal_target(href):
    """Frozen canonical route map; redirects are not action delegations."""
    import reporting_structured as s
    manifest = json.loads(SNAPSHOT.read_text(), object_pairs_hook=s.unique_object)
    return href.rstrip('/') + '/' in manifest['internal_paths']


def dependencies():
    import idna
    import sys
    import unicodedata
    result = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in DEPENDENCIES}
    result['runtime'] = hashlib.sha256(_json([list(sys.version_info[:3]), idna.__version__, unicodedata.unidata_version])).hexdigest()
    return result


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def _store():
    return trust.store()


@dataclass(frozen=True)
class EditorialDecision:
    page_id: str
    page_sha256: str
    canon_sha256: str
    dependency_digests: dict
    reviewer: str
    scope: str
    decision_id: str


def action_selection(canon, route_ids, audience):
    import reporting_structured as s
    from reporting_actions import VERSION
    return {'route_ids': route_ids, 'audience': list(audience), 'schema_version': VERSION,
            'action_plan_sha256': s.action_plan_sha256(s.catalog_from_canon(canon), route_ids)}


def _context(post, canon, body):
    import reporting_structured as s
    selection = body['action_selection']
    if (not isinstance(selection, dict) or set(selection) != {'route_ids', 'audience', 'schema_version', 'action_plan_sha256'}
            or not isinstance(selection['audience'], list) or not selection['audience']
            or any(not isinstance(n, str) or n not in s._NATIONS for n in selection['audience'])
            or len(set(selection['audience'])) != len(selection['audience'])):
        raise ValueError('invalid separately reviewed action selection/audience')
    if selection['route_ids'] != post.get('reporting_routes'):
        raise ValueError('editorial action-selection decision must bind the exact article plan')
    catalog = s.catalog_from_canon(canon)
    from reporting_actions import VERSION
    if (selection['schema_version'] != VERSION
            or selection['action_plan_sha256'] != s.action_plan_sha256(catalog, selection['route_ids'])):
        raise ValueError('editorial action-plan/model binding mismatch')
    actions = s.ordered_actions(catalog, selection['route_ids'])
    audience = set(selection['audience'])
    if 'Global' in audience and len(audience) != 1:
        raise ValueError('invalid Global audience')
    for a in actions:
        if not set(a.jurisdictions) <= audience and a.jurisdictions != ('Global',):
            raise ValueError('action scope exceeds the reviewed audience')
    if any(a.purpose == 'police-report' for a in actions):
        covered = set().union(*(set(a.jurisdictions) for a in actions if a.purpose == 'police-report'))
        if audience - covered:
            raise ValueError('police reporting plan omits a reviewed audience jurisdiction')
    facts = tuple(s.NumericFact(**f) for f in body['numeric_facts'])
    decision = EditorialDecision(body['page_id'], body['page_sha256'], body['canon_sha256'],
        body['dependencies'], body['reviewer'], body['scope'], body['decision_id'])
    return s.ReviewContext(body['canon_sha256'], body['page_sha256'], tuple(selection['route_ids']),
        date.today().isoformat(), tuple(tuple(p) for p in post.get('sources_checked', [])),
        body['allow_empty'], facts, body['page_id'], (), decision)


def verify_packet(packet, post, canon, *, page_id=None):
    """Authenticate and authorize consumption in the current external page scope."""
    import reporting_structured as s
    if not isinstance(packet, dict) or set(packet) != {'body', 'signature'}:
        raise ValueError('expected an external signed editorial packet')
    b = packet['body']
    keys = {'version', 'scope', 'reviewer', 'decision_id', 'issued_at', 'expires_at', 'page_id',
            'page_sha256', 'canon_sha256', 'dependencies', 'action_selection', 'numeric_facts', 'allow_empty',
            'environment', 'site'}
    if not isinstance(b, dict) or set(b) != keys or b['version'] != NAMESPACE or b['scope'] != SCOPE:
        raise ValueError('unknown editorial packet schema or scope')
    if (b['page_id'] != page_identity(post, page_id) or b['page_sha256'] != s.digest(post)
            or b['canon_sha256'] != s.digest(canon) or b['dependencies'] != dependencies()):
        raise ValueError('editorial packet candidate/canon/policy/template binding mismatch')
    cfg = trust.verify(b, packet['signature'], 'context', NAMESPACE,
                       page_id=page_identity(post, page_id))
    if trust.environment() == 'production':
        from reporting_eligibility import require_actions
        require_actions(canon, post.get('reporting_routes'))
    context = _context(post, canon, b)
    s.validate_page(post, s.catalog_from_canon(canon), context, page_id=page_id)
    if trust.config() != cfg:
        raise ValueError('trust changed during page approval consumption')
    return context


def review(post, canon, supplied=None, *, page_id=None):
    """Publication callers accept signed packets only; never raw contexts."""
    import reporting_structured as s
    try:
        if supplied is None:
            name = hashlib.sha256(page_identity(post, page_id).encode()).hexdigest() + '.json'
            supplied = trust.read_json(_store() / 'packets' / name, protected=True)
        return verify_packet(supplied, post, canon, page_id=page_id)
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        raise s.ReportingError('authenticated publication review: ' + str(exc)) from exc


def is_page_publication_eligible(post, canon, supplied=None, *, page_id=None):
    """Current structured production-page approval; not artifact/deploy permission.

    Frozen legacy rendering and test contexts are not production page approvals.
    Output, release and platform verification remain separate later predicates.
    """
    try:
        if trust.environment() != 'production' or 'reporting_routes' not in post:
            return False
        from reporting_eligibility import require_contract_actions
        require_contract_actions(canon, post['reporting_routes'])
        review(post, canon, supplied, page_id=page_id)
        return True
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError):
        return False


def issue_reviewed(post, canon, *, page_id, private_key, reviewer, audience,
                   allow_empty=False, numeric_facts=()):
    """Explicit operator issuance only, called by the review CLI after review.

    Never called by generation, gate, writer or renderer. No keys are generated
    or installed here. Possession of an enrolled external signing key is needed.
    """
    import secrets
    import reporting_structured as s
    key = Path(private_key).resolve()
    if ROOT in key.parents:
        raise ValueError('editor signing key must be outside the repository')
    b = dict(trust.header(NAMESPACE), scope=SCOPE, reviewer=reviewer, page_id=page_id,
        page_sha256=s.digest(post), canon_sha256=s.digest(canon), dependencies=dependencies(),
        action_selection=action_selection(canon, post.get('reporting_routes'), audience),
        numeric_facts=list(numeric_facts), allow_empty=allow_empty)
    # The deterministic boundary is unwaivable even by the signing editor.
    context = _context(post, canon, b)
    s.validate_page(post, s.catalog_from_canon(canon), context, page_id=page_id)
    if trust.environment() == 'production':
        from reporting_eligibility import require_actions
        require_actions(canon, post.get('reporting_routes'))
    packet = trust.sign(b, key, 'context', NAMESPACE)
    verify_packet(packet, post, canon, page_id=page_id)
    return packet
