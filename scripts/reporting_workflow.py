#!/usr/bin/env python3
"""Trusted-host adapter for the existing publication verifier. No promotion API.

Run with python -I from the trusted checkout. Candidate Git objects are data;
no candidate module, package configuration, hook, filter or executable is run.
Workflow provenance still requires protected review on GitHub (see policy).
"""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import reporting_pilot as pilot
import reporting_publication as publication
import reporting_runtime as runtime
import reporting_trust as trust

WORKFLOW = '.github/workflows/publication-verification.yml'
CHECK = 'Trusted publication verification'
# Prefixes also cover new files, deletions, alternate workflows and local Actions.
CONTROL_DIRS = ('scripts/', 'templates/', 'assets/', 'static/', 'netlify/', '.github/')
CONTROL_FILES = set(pilot.INPUT_FILES) | set(publication.DEPENDENCIES) | {
    '.gitattributes', '.gitmodules', '.npmrc', 'AGENTS.md', 'CLAUDE.md',
    'docs/publication-enforcement.md', 'pyproject.toml', 'setup.py', 'setup.cfg',
}


def control_path(path):
    return path in CONTROL_FILES or path.startswith(CONTROL_DIRS)


def critical_path(path):
    return control_path(path) or path.startswith(('deployment/', 'content/', 'dist/'))


def critical_inventory(files):
    """Complete publication data/control map, including every served file."""
    pilot.check_names(files)
    return pilot.hashes({p: data for p, data in files.items() if critical_path(p)})


def revision(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value) or value == '0' * 40:
        raise ValueError('revision must be an exact nonzero Git commit SHA')
    return value


def git(root, *args):
    # Ignore ambient config; disable local-config hooks, fsmonitor and transports.
    env = {'PATH': os.environ['PATH'], 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_NO_REPLACE_OBJECTS': '1',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_LAZY_FETCH': '1', 'GIT_ALLOW_PROTOCOL': ''}
    return subprocess.run(['git', '--no-replace-objects', '-C', str(root),
        '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
        '-c', 'protocol.allow=never', *args], env=env, capture_output=True,
        check=True, timeout=60).stdout


def git_snapshot(root, sha):
    """Read immutable blobs, ignoring checkout filters and export attributes."""
    sha = revision(sha)
    if git(root, 'rev-parse', '--verify', sha + '^{commit}').decode().strip() != sha:
        raise ValueError('candidate is not the requested commit')
    listing = git(root, 'ls-tree', '-r', '-z', '-l', '--full-tree', sha)
    if len(listing) > 2 * 1024 * 1024:
        raise ValueError('Git tree listing too large')
    records = []; total = 0
    for row in listing.split(b'\0'):
        if not row: continue
        meta, rawpath = row.split(b'\t', 1)
        mode, kind, oid, size = meta.split()
        path = pilot.path_name(rawpath.decode('ascii'))
        if mode not in (b'100644', b'100755') or kind != b'blob' or not re.fullmatch(b'[0-9a-f]{40}', oid):
            raise ValueError('nonregular Git entry: ' + path)
        total += int(size)
        if total > pilot.MAX_BYTES: raise ValueError('Git snapshot exceeds byte bound')
        records.append((path, oid.decode(), int(size)))
    pilot.check_names([r[0] for r in records])
    result = {}
    for path, oid, size in records:
        data = git(root, 'cat-file', 'blob', oid)
        if len(data) != size: raise ValueError('Git blob size changed')
        result[path] = data
    return result


def controls_match(candidate, trusted):
    old = {p: b for p, b in trusted.items() if control_path(p)}
    new = {p: b for p, b in candidate.items() if control_path(p)}
    if new != old:
        changed = sorted(p for p in set(old) | set(new) if old.get(p) != new.get(p))
        raise ValueError('control-plane change requires separate trusted installation: ' + ', '.join(changed))


def local_snapshot(root):
    """Diagnostic only: include tracked and nonignored untracked working bytes."""
    paths = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')
    result = {}
    for raw in paths:
        if not raw: continue
        name = pilot.path_name(raw.decode('ascii'))
        path = root / name
        if path.resolve() != path.absolute(): raise ValueError('symlink candidate path')
        if path.exists(): result[name] = trust.read_file(path, limit=pilot.MAX_BYTES)
    pilot.check_names(result)
    if sum(map(len, result.values())) > pilot.MAX_BYTES: raise ValueError('candidate exceeds byte bound')
    return result


def verify_data(files, trusted, *, production=True, source_revision=None, release_packet=None):
    """Use one existing verifier with captured data and trusted implementation."""
    controls_match(files, trusted)
    runtime.require()
    if production and trust.environment() != 'production':
        raise ValueError('publication workflow requires production trust')
    if not production and trust.environment() != 'test':
        raise ValueError('synthetic verification requires TEST authority')
    pilot.check_names(files)
    if sum(map(len, files.values())) > pilot.MAX_BYTES: raise ValueError('snapshot too large')
    with tempfile.TemporaryDirectory(prefix='bts-publication-data-') as raw:
        root = Path(raw).resolve()
        for name, data in files.items():
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        with pilot.public_review_store(root) as store:
            cfg = trust.config()  # Canonical digest / external production pin FIRST.
            if not pilot.baseline(cfg): raise ValueError('release baseline is UNESTABLISHED')
            if not cfg['pilot_page_ids']: raise ValueError('empty pilot scope authorizes no page')
            import build
            import canon
            sources = canon.load_canon(root / 'content/sources.json')
            hubs = trust.read_json(root / 'content/category-hubs.json')
            # The ordinary hub gate remains mandatory, including legacy failures.
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    build.validate_category_hubs(hubs, reporting_sources=sources)
            except SystemExit as exc:
                raise ValueError('hub gate blocked: ' + str(exc)) from exc
            if release_packet is None:
                raise ValueError('detached release approval required')
            packet = release_packet
            archive = pilot.zip_bytes(pilot.tree(root / 'dist'))
            result = (pilot.verify_bundle(packet, root, archive, source_revision=source_revision) if production else
                      pilot.verify_test_bundle(packet, root, archive, source_revision=source_revision))
            # A verification success is not a deployment instruction/capability.
            return dict(result, deployment_eligible=False,
                        candidate_map_sha256=trust.digest(pilot.hashes(files)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--candidate-sha')
    parser.add_argument('--trusted-sha')
    parser.add_argument('--approval-repository', type=Path)
    parser.add_argument('--approval-sha')
    parser.add_argument('--test-only', action='store_true')
    parser.add_argument('--diagnostic-working-tree', action='store_true')
    args = parser.parse_args(argv)
    result = {'check': CHECK, 'deployment_eligible': False,
              'candidate_sha': args.candidate_sha, 'trusted_sha': args.trusted_sha,
              'diagnostic_only': args.diagnostic_working_tree}
    try:
        if args.test_only and trust.environment() != 'test':
            raise ValueError('--test-only requires explicit TEST authority')
        if not args.test_only and trust.environment() != 'production':
            raise ValueError('publication workflow requires production trust')
        source_revision = None
        if args.diagnostic_working_tree:
            if args.candidate_sha or args.trusted_sha:
                raise ValueError('dirty diagnostic must not claim commit identity')
            files = local_snapshot(args.candidate.resolve())
            trusted = local_snapshot(ROOT)
        else:
            trusted = git_snapshot(ROOT, args.trusted_sha)
            # Also reject modification of the trusted checkout after setup.
            controls_match(local_snapshot(ROOT), trusted)
            import reporting_revision
            files, source_revision = reporting_revision.identity(args.candidate.resolve(), args.candidate_sha)
            if local_snapshot(args.candidate.resolve()) != files:
                raise ValueError('working candidate differs from exact source revision')
            if pilot.tree(args.candidate.resolve() / 'dist') != {
                    p[5:]: b for p,b in files.items() if p.startswith('dist/')}:
                raise ValueError('working served output differs from exact source revision')
        packet = None
        if args.approval_repository is not None or args.approval_sha is not None:
            if args.approval_repository is None or args.approval_sha is None:
                raise ValueError('explicit approval repository and SHA required')
            approvals = git_snapshot(args.approval_repository.resolve(), args.approval_sha)
            # Detached transport is data at an exact immutable commit. It must
            # contain only the release packet; nothing from it executes.
            if set(approvals) != {'release.json'}:
                raise ValueError('detached approval commit must contain only release.json')
            packet = json.loads(approvals['release.json'], object_pairs_hook=trust.unique)
        if args.diagnostic_working_tree and packet is not None:
            # Corroborate the packet's claim only for diagnostics. There is no
            # independently selected event SHA; the unconditional diagnostic
            # refusal below still forbids a required-check PASS.
            import reporting_revision
            source_revision = reporting_revision.worktree(args.candidate.resolve(),
                packet['body']['manifest']['source_revision']['source_commit'])
        result['test_only'] = args.test_only
        result['approval_sha'] = args.approval_sha
        result['candidate_map_sha256'] = trust.digest(pilot.hashes(files))
        result.update(verify_data(files, trusted, production=not args.test_only,
                                 source_revision=source_revision, release_packet=packet))
        if args.diagnostic_working_tree:
            raise ValueError('diagnostic verification cannot satisfy a required commit check')
        result['outcome'] = 'PASS'; code = 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result.update(outcome='BLOCKED', reason=str(exc)); code = 1
    except Exception as exc:
        result.update(outcome='ERROR', reason=type(exc).__name__ + ': ' + str(exc)); code = 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return code


if __name__ == '__main__': raise SystemExit(main())
