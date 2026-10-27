"""Offline test-only SSH identity. Never imported by production modules.

This synthetic key is temporary, signs only test inputs, and is enrolled only in
this process's temporary review store. Tests still cross the real verifier.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import hashlib
import os
import secrets
import subprocess
import tempfile
import reporting_publication as publication
import reporting_structured as s

_temporary = None
_cache = {}


def store():
    global _temporary
    if _temporary is None:
        _temporary = tempfile.TemporaryDirectory(prefix='bts-synthetic-review-')
        root = Path(_temporary.name).resolve()
        key = root / 'fixture-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
        (root / 'allowed_signers').write_text('offline-fixture-reviewer ' + key.with_suffix('.pub').read_text())
        public = ' '.join(key.with_suffix('.pub').read_text().split()[:2])
        (root / 'trust.json').write_text(json.dumps({'version': 'bts-trust/v1', 'environment': 'test',
            'site': 'beatthescam.com', 'roles': {role: [{'identity': 'offline-fixture-reviewer', 'public_key': public}]
            for role in ('context', 'contracts', 'release')}, 'pilot_page_ids': [], 'baseline_sha256': '0'*64,
            'revocations_sha256': hashlib.sha256(b'[]').hexdigest()}))
        (root / 'revoked.json').write_text('[]\n')
        (root / 'packets').mkdir()
    os.environ['BTS_REVIEW_STORE'] = str(Path(_temporary.name).resolve())
    os.environ['BTS_REVIEW_ENVIRONMENT'] = 'test'
    return Path(_temporary.name).resolve()


def sign_body(body):
    root = store()
    with tempfile.TemporaryDirectory(prefix='bts-synthetic-sign-') as tmp:
        data = Path(tmp) / 'decision'; data.write_bytes(publication._json(body))
        subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(root / 'fixture-key'),
                        '-n', publication.NAMESPACE + ':test', str(data)], capture_output=True, check=True)
        return {'body': body, 'signature': data.with_suffix('.sig').read_text()}


def packet_for(post, canon, review):
    """Preserve exact independently supplied fixture field-approval decisions.

    We do not derive approval from a passing scanner. Invalid old bindings stay
    invalid. Correctly bound but prohibited wording can be signed deliberately;
    the real verifier must reject it at the restricted boundary.
    """
    if not isinstance(review, s.ReviewContext):
        return review
    try:
        s.validate_prose_approvals(post, review, page_id=review.page_id)
    except (ValueError, TypeError, KeyError):
        return {}  # Explicitly unauthenticated negative control.
    # Malformed plans are intentionally signable only by this adversarial test helper.
    # There is no resolved plan to hash; the genuine verifier must reject them.
    try:
        selection = publication.action_selection(canon, list(review.allowed_route_ids), s._NATIONS[:4])
    except ValueError:
        from reporting_actions import VERSION
        selection = {'route_ids': list(review.allowed_route_ids), 'audience': list(s._NATIONS[:4]),
                     'schema_version': VERSION, 'action_plan_sha256': '0'*64}
    now = datetime.now(timezone.utc)
    body = dict(version=publication.NAMESPACE, scope=publication.SCOPE,
        environment='test', site='beatthescam.com',
        reviewer='offline-fixture-reviewer', decision_id=secrets.token_hex(16),
        issued_at=now.isoformat(), expires_at=(now + timedelta(days=1)).isoformat(),
        page_id=review.page_id, page_sha256=review.page_sha256, canon_sha256=review.canon_sha256,
        dependencies=publication.dependencies(),
        action_selection=selection,
        numeric_facts=[vars(f) for f in review.numeric_facts], allow_empty=review.allow_empty)
    cache_key = s.digest({k:v for k,v in body.items() if k not in ('issued_at','expires_at','decision_id')})
    root = store()
    # Each grammar case explicitly enrolls its exact synthetic surface. The
    # cached signature is not a cached current-authorization decision.
    cfg = json.loads((root / 'trust.json').read_text())
    cfg['pilot_page_ids'] = [review.page_id]
    (root / 'trust.json').write_text(json.dumps(cfg))
    if cache_key not in _cache:
        _cache[cache_key] = sign_body(body)
    return _cache[cache_key]
