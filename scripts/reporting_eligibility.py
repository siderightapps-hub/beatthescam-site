"""Separate reviewed contract eligibility from signed publication authority.

Contract eligibility uses the exact independently reviewed canon/model baseline,
closed schema and evidence freshness. It never reads a signing/trust store.
Publication additionally requires the existing contracts-role endorsement;
context/release approvals cannot create contract eligibility.
"""
from dataclasses import asdict
from datetime import date, timedelta
import hashlib
import reporting_structured as s
import reporting_trust as trust

VERSION = 'beatthescam-contract-evidence-v3'

# WP3D9E's six independent clearances, implemented and reconciled by WP3C9F.
# This is a reviewed source-data baseline, NOT a signing key, trust.json pin,
# runtime configuration or auto-generated fallback. Bind the complete canon
# (including provenance/holds/sharing) and model so self-edited metadata cannot
# approve itself. A later canon/model change needs a new reviewed baseline.
REVIEWED_CANON_SHA256 = '0319177c15f62e63de8b56a76d411b26855ba19ec87d3e95371a6b9b5d9a0a24'
# R6B2 operator-authorized six-only compatibility update; canon/IDs unchanged.
REVIEWED_MODEL_SHA256 = '3c7909967cce32904ed71db36139cbe0a54e064e0daa2e1b90021c9afb5e76fb'
REVIEWED_CONTRACT_IDS = frozenset({
    'citizens-advice:consumer-advice-english', 'victim-support:supportline',
    'o2-pay-monthly:customer-support', 'o2-payg:customer-support',
    'own-bank:number-on-bank-card', 'own-bank:existing-bank-app',
})


def claims(canon, route_id):
    catalog = s.catalog_from_canon(canon)
    action = catalog.resolve(route_id)
    checked = date.fromisoformat(action.checked_on)
    if not date.today() - timedelta(days=90) <= checked <= date.today():
        raise ValueError('contract evidence is stale/future')
    # Includes exact method, endpoints, conditions, limitations, visible
    # qualifiers and operator attribution; whole-canon binding covers aliases.
    return {'route_id': route_id, 'canon_sha256': s.digest(canon),
            'contract_sha256': s.digest(asdict(action)),
            'schema_version': action.schema_version, 'contract_model_sha256': s.contract_model_sha256(),
            'source_url': action.source_url, 'checked_on': action.checked_on,
            'evidence_state': 'verified-by-contract-reviewer'}


def packet_path(route_id):
    s.validate_route_id(route_id)
    return trust.store() / 'contracts' / (hashlib.sha256(route_id.encode()).hexdigest()+'.json')


def verify_contract_eligibility(canon, route_id):
    """Contract/evidence/schema predicate only; no enrollment or signatures."""
    catalog = s.catalog_from_canon(canon)
    catalog.select([route_id])  # Includes active status, not just resolution.
    if route_id not in REVIEWED_CONTRACT_IDS:
        raise ValueError('contract has no independent canon clearance')
    if s.digest(canon) != REVIEWED_CANON_SHA256:
        raise ValueError('canon/evidence differs from independently reviewed baseline')
    if s.contract_model_sha256() != REVIEWED_MODEL_SHA256:
        raise ValueError('contract model differs from independently reviewed baseline')
    return dict(claims(canon, route_id), evidence_state='independently-confirmed-canon')


def _companion_closure(catalog, eligible):
    while True:
        filtered = [r for r in eligible if set(catalog.actions[r].companions) <= set(eligible)]
        if filtered == eligible: return tuple(sorted(filtered))
        eligible = filtered


def contract_production_eligible_ids(canon):
    """Reviewed real contracts, independent of publication environment/authority."""
    catalog = s.catalog_from_canon(canon)
    eligible = []
    for rid in catalog.actions:
        try: verify_contract_eligibility(canon, rid)
        except (ValueError, TypeError, KeyError): continue
        eligible.append(rid)
    return _companion_closure(catalog, eligible)


def is_contract_production_eligible(canon, route_id):
    try: return route_id in contract_production_eligible_ids(canon)
    except (ValueError, TypeError, KeyError): return False


def require_contract_actions(canon, route_ids):
    catalog = s.catalog_from_canon(canon)
    actions = catalog.select(route_ids)
    for action in actions: verify_contract_eligibility(canon, action.route_id)
    return catalog


def verify_contract(canon, route_id, packet=None):
    """Verify the signed publication endorsement, NOT contract eligibility.

    Historical API retained for signed-packet tooling and synthetic tests.
    Production callers must use require_actions(), which requires both layers.
    """
    expected = claims(canon, route_id)
    if packet is None: packet = trust.read_json(packet_path(route_id), protected=True)
    if not isinstance(packet, dict) or set(packet) != {'body', 'signature'}:
        raise ValueError('missing signed contract evidence')
    b = packet['body']
    if (not isinstance(b, dict) or set(b) != {'version', 'environment', 'site', 'reviewer', 'decision_id',
            'issued_at', 'expires_at', 'claims'} or b['version'] != VERSION or b['claims'] != expected):
        raise ValueError('contract evidence binding/schema mismatch')
    trust.verify(b, packet['signature'], 'contracts', VERSION)
    return expected


def require_actions(canon, route_ids):
    """Publication precondition: eligible real contract AND signed endorsement.

    Test-mode artifacts may exercise synthetic grammar. They are never accepted
    by the production release verifier or page-publication predicate.
    """
    catalog = s.catalog_from_canon(canon)
    actions = catalog.select(route_ids)
    if trust.environment() == 'production': require_contract_actions(canon, route_ids)
    for action in actions: verify_contract(canon, action.route_id)
    return catalog


def publication_endorsed_ids(canon):
    """Signed publication prerequisite; alone never a publishable-page result."""
    catalog = s.catalog_from_canon(canon)
    eligible = []
    for rid, action in catalog.actions.items():
        if action.status != 'active': continue
        try:
            if trust.environment() == 'production': verify_contract_eligibility(canon, rid)
            verify_contract(canon, rid)
        except (ValueError, OSError, TypeError, KeyError): continue
        eligible.append(rid)
    return _companion_closure(catalog, eligible)


def eligible_ids(canon):
    """Compatibility alias for publication_endorsed_ids; not contract eligibility."""
    return publication_endorsed_ids(canon)


def inventory(canon):
    import reporting_actions as vocabulary
    catalog = s.catalog_from_canon(canon)
    eligible = set(contract_production_eligible_ids(canon))
    endorsed = list(publication_endorsed_ids(canon))
    return {'environment': trust.environment(),
        'contract_production_eligible': sorted(eligible),
        'publication_endorsed_contracts': endorsed if trust.environment() == 'production' else [],
        'test_endorsed_contracts': endorsed if trust.environment() == 'test' else [],
        'implemented_action_types': sorted({v[0] for v in vocabulary.TEMPLATES.values()} | {'contact'}),
        'contracts': [dict(s.action_descriptor(a), **{
            'classification': 'A. CONTRACT ELIGIBLE; PUBLICATION SEPARATE' if rid in eligible
                              else 'B. NO INDEPENDENT CONTRACT CLEARANCE',
            'owner': a.owner, 'service': a.service, 'purpose': a.purpose, 'method': a.template_id,
            'jurisdictions': list(a.jurisdictions), 'conditions': list(a.condition_ids),
            'limitations': list(a.limitation_ids)}) for rid,a in sorted(catalog.actions.items())]}


def issue_reviewed(canon, route_id, *, reviewer, private_key):
    body = dict(trust.header(VERSION), reviewer=reviewer, claims=claims(canon, route_id))
    return trust.sign(body, private_key, 'contracts', VERSION)
