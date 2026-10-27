"""External, verification-only trust roots. No production keys in CI or drafts.

Production is the default. Test mode requires BOTH an explicit process setting
and a test-labelled external root; every signed body and SSH namespace bind it.
The trusted operator/host owns this directory and the executed verifier code.
"""
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = 'beatthescam.com'
ROLES = ('context', 'contracts', 'release')
PAGE_ID = re.compile(r'(?:guide|hub):[a-z0-9]+(?:-[a-z0-9]+)*')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('duplicate JSON field')
        result[k] = v
    return result


def read_file(path, limit=16 * 1024 * 1024, *, protected=False):
    """No symlinks, devices, FIFOs or hard-linked authority/artifact files."""
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('symlink input rejected')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError('input must be a bounded regular file with one link')
        if protected and (before.st_uid != os.getuid() or before.st_mode & 0o022):
            raise ValueError('trust input owner/mode rejected')
        chunks = []; remaining = limit + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 1024 * 1024))
            if not chunk: break
            chunks.append(chunk); remaining -= len(chunk)
        after = os.fstat(fd)
        data = b''.join(chunks)
        if len(data) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('input changed while reading')
        return data
    finally:
        os.close(fd)


def read_json(path, *, protected=False):
    return json.loads(read_file(path, protected=protected), object_pairs_hook=unique)


def environment():
    value = os.environ.get('BTS_REVIEW_ENVIRONMENT', 'production')
    if value not in ('production', 'test'):
        raise ValueError('unknown review environment')
    return value


def store():
    value = os.environ.get('BTS_REVIEW_STORE', '')
    path = Path(value).absolute()
    if not value or not Path(value).is_absolute() or path.resolve() != path or path == ROOT or ROOT in path.parents:
        raise ValueError('BTS_REVIEW_STORE must be absolute and outside the repository')
    for item in (path, *path.parents):
        if item.is_symlink(): raise ValueError('symlink trust directory rejected')
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ValueError('trust directory owner/mode rejected')
    return path


def _page_scope(ids):
    if (not isinstance(ids, list) or len(ids) > 7
            or any(not isinstance(x, str) or not PAGE_ID.fullmatch(x) for x in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError('invalid exact pilot page scope')
    return ids


def require_page_scope(cfg, page_id, role):
    """Require current page authority from an already verified trust config.

    This predicate alone does not authenticate a root or an approval. Context
    consumers call verify(..., page_id=...) so signature and scope use the same
    fresh config. Contracts are not page-scoped; an empty scope authorizes none.
    """
    ids = _page_scope(cfg.get('pilot_page_ids'))
    if (role not in ('context', 'release') or not isinstance(page_id, str)
            or not PAGE_ID.fullmatch(page_id) or page_id not in ids):
        raise ValueError('page outside enrolled scope')


def config():
    value = read_json(store() / 'trust.json', protected=True)
    if environment() == 'production' and os.environ.get('BTS_PRODUCTION_TRUST_SHA256') != digest(value):
        raise ValueError('production trust root needs an externally pinned SHA-256')
    if (not isinstance(value, dict) or set(value) != {'version', 'environment', 'site', 'roles', 'pilot_page_ids', 'baseline_sha256', 'revocations_sha256'}
            or value['version'] != 'bts-trust/v1' or value['environment'] != environment() or value['site'] != SITE
            or not isinstance(value['roles'], dict) or set(value['roles']) != set(ROLES)):
        raise ValueError('trust root schema/environment/site mismatch')
    for entries in value['roles'].values():
        if not isinstance(entries, list) or not 1 <= len(entries) <= 16:
            raise ValueError('missing/bad signer enrollment')
        identities = set()
        for row in entries:
            if (not isinstance(row, dict) or set(row) != {'identity', 'public_key'}
                    or not isinstance(row['identity'], str) or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,128}', row['identity'])
                    or row['identity'] in identities or not isinstance(row['public_key'], str)
                    or not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/]+={0,2}', row['public_key'])):
                raise ValueError('invalid Ed25519 signer enrollment')
            identities.add(row['identity'])
    _page_scope(value['pilot_page_ids'])
    if (not isinstance(value['baseline_sha256'], str)
            or not re.fullmatch(r'[a-f0-9]{64}', value['baseline_sha256'])
            or not isinstance(value['revocations_sha256'], str)
            or not re.fullmatch(r'[a-f0-9]{64}', value['revocations_sha256'])):
        raise ValueError('invalid exact pilot/baseline policy')
    return value


def header(version):
    import secrets
    now = datetime.now(timezone.utc)
    return dict(version=version, environment=environment(), site=SITE,
        decision_id=secrets.token_hex(16), issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=7)).isoformat())


def verify(body, signature, role, namespace, *, page_id=None):
    """Authenticate a current reviewer record; returns no publication capability.

    Page consumers must supply the exact bound page_id to enforce current scope.
    That form returns the verified config for a final consumer change check.
    Without page_id this returns None and is record authentication only, never
    page authorization. Historical signatures remain evidence after scope removal.
    """
    cfg = config()
    if role not in ROLES or body.get('environment') != cfg['environment'] or body.get('site') != cfg['site']:
        raise ValueError('approval environment/site/role mismatch')
    reviewer = body.get('reviewer'); decision = body.get('decision_id')
    if (not isinstance(reviewer, str) or not any(x['identity'] == reviewer for x in cfg['roles'][role])
            or not isinstance(decision, str) or not re.fullmatch(r'[a-f0-9]{32}', decision)):
        raise ValueError('unauthorized signer/provenance')
    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(body['issued_at']); end = datetime.fromisoformat(body['expires_at'])
    if (start.tzinfo is None or end.tzinfo is None or start.utcoffset() != timedelta(0) or end.utcoffset() != timedelta(0)
            or not start <= now <= end or not timedelta(0) < end-start <= timedelta(days=7)):
        raise ValueError('approval is stale, future-dated, expired or overlong')
    revoked = read_json(store() / 'revoked.json', protected=True)
    if (digest(revoked) != cfg['revocations_sha256'] or not isinstance(revoked, list)
            or any(not isinstance(x, str) or not re.fullmatch(r'[a-f0-9]{32}', x) for x in revoked)
            or decision in revoked):
        raise ValueError('approval revoked or revocation state invalid')
    if not isinstance(signature, str) or len(signature) > 16384:
        raise ValueError('invalid signature')
    with tempfile.TemporaryDirectory(prefix='bts-verify-') as tmp:
        path = Path(tmp); sig = path / 'signature'; sig.write_text(signature)
        roots = path / 'signers'
        roots.write_text(''.join(x['identity']+' '+x['public_key']+'\n' for x in cfg['roles'][role]))
        result = subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(roots), '-I', reviewer,
            '-n', namespace + ':' + cfg['environment'], '-s', str(sig)], input=canonical(body), capture_output=True, timeout=10)
    if result.returncode: raise ValueError('signature authentication failed')
    if page_id is not None:
        require_page_scope(cfg, page_id, role)
        if config() != cfg:
            raise ValueError('trust changed during page approval verification')
        return cfg


def key_path(private_key):
    """Reject keys in any Git checkout (including sibling linked worktrees)."""
    key = Path(private_key)
    if not key.is_absolute() or key.resolve() != key:
        raise ValueError('key path must be absolute, canonical and nonsymlink')
    if ROOT == key or ROOT in key.parents or any((p/'.git').exists() for p in key.parents):
        raise ValueError('private key must be outside every repository/worktree')
    if environment() == 'production':
        if store() in key.parents or any(re.search(r'(?:test|fixture|synthetic|fake)', p, re.I) for p in key.parts):
            raise ValueError('production refuses fixture/test keys and verification-store keys')
    info = key.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError('private key must be an owner-only regular file with one link')
    return key


def sign(body, private_key, role, namespace, *, review_summary=None, recheck=None):
    """Explicit human operation; no key creation and no CI production signing."""
    if os.environ.get('BTS_REVIEW_ENVIRONMENT') not in ('production', 'test'):
        raise ValueError('signing requires an explicit environment')
    cfg = config()
    if role not in ROLES or body.get('environment') != environment() or body.get('site') != SITE:
        raise ValueError('signing environment/site/role mismatch')
    if not any(r['identity'] == body.get('reviewer') for r in cfg['roles'][role]):
        raise ValueError('unauthorized signer for selected role')
    if environment() == 'production' and (os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS') or os.environ.get('NETLIFY')):
        raise ValueError('production signing is forbidden in automated build environments')
    key = key_path(private_key)
    if environment() == 'production':
        if review_summary is None or recheck is None or not sys.stdin.isatty() or not sys.stderr.isatty():
            raise ValueError('production requires the interactive expected-receipt reviewer command')
        print(json.dumps(review_summary, indent=2, ensure_ascii=True), file=sys.stderr)
        phrase = 'SIGN production '+role+' '+body['reviewer']+' '+digest(review_summary)
        print('Type exactly: '+phrase, file=sys.stderr)
        if input() != phrase: raise ValueError('production confirmation declined')
    if recheck is not None: recheck()
    # OpenSSH closes inherited descriptors on macOS. Retain the external path,
    # compare its bounded bytes before/after, and authenticate the result against
    # the enrolled public key. No private key is copied into a temporary file.
    key_hash = hashlib.sha256(read_file(key, protected=True)).digest()
    with tempfile.TemporaryDirectory(prefix='bts-sign-') as tmp:
        p = Path(tmp) / 'decision'; p.write_bytes(canonical(body))
        result = subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', namespace+':'+environment(), str(p)],
                       capture_output=True, timeout=10)
        if result.returncode: raise ValueError('signing failed: check the selected key and local ssh-agent; no key data logged')
        packet = {'body': body, 'signature': p.with_suffix('.sig').read_text()}
    if key_path(key) != key or hashlib.sha256(read_file(key, protected=True)).digest() != key_hash:
        raise ValueError('key changed during signing')
    if config() != cfg: raise ValueError('trust changed during signing')
    if recheck is not None: recheck()
    verify(body, packet['signature'], role, namespace)
    return packet
