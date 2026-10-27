"""Exact source-commit identity for detached release approvals.

Only trusted entrypoints capture Git objects. A packet's claimed identity is
never used to select the candidate. No signing, network or Git writes here.
"""
from pathlib import Path
import re

import reporting_pilot as pilot
import reporting_trust as trust

VERSION = 'bts-source-revision/v1'


def identity(repository, sha):
    # Reuse the hardened immutable object reader; import lazily to avoid the
    # pilot/workflow import cycle.
    import reporting_workflow as workflow
    sha = workflow.revision(sha)
    files = workflow.git_snapshot(repository, sha)
    tree = workflow.git(repository, 'rev-parse', '--verify', sha + '^{tree}').decode().strip()
    if not re.fullmatch('[0-9a-f]{40}', tree):
        raise ValueError('invalid source tree identity')
    return files, {'version': VERSION, 'source_commit': sha, 'source_tree': tree,
                   'candidate_map_sha256': trust.digest(pilot.hashes(files))}


def worktree(repository, sha):
    """An explicit SHA plus exact working bytes, never an implicit HEAD."""
    import reporting_workflow as workflow
    repository = Path(repository).resolve()
    files, binding = identity(repository, sha)
    if workflow.local_snapshot(repository) != files:
        raise ValueError('working candidate differs from exact source revision')
    if pilot.tree(repository / 'dist') != {p[5:]: b for p,b in files.items() if p.startswith('dist/')}:
        raise ValueError('working served output differs from exact source revision')
    return binding


def validate(binding):
    if (not isinstance(binding, dict) or set(binding) != {
            'version', 'source_commit', 'source_tree', 'candidate_map_sha256'}
            or binding['version'] != VERSION):
        raise ValueError('explicit verified source revision required')
    for key, size in (('source_commit', 40), ('source_tree', 40), ('candidate_map_sha256', 64)):
        value = binding[key]
        if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{%d}' % size, value) or value == '0' * size:
            raise ValueError('invalid bound ' + key)
    return binding


def materialized(root, outputs, binding):
    """Recheck the entire captured candidate, including documentation and trust."""
    import reporting_workflow as workflow
    validate(binding)
    root = Path(root).resolve()
    files = (workflow.local_snapshot(root) if (root / '.git').exists()
             else pilot.tree(root, source=True))
    if trust.digest(pilot.hashes(files)) != binding['candidate_map_sha256']:
        raise ValueError('source revision candidate map mismatch')
    if {p[5:]: data for p, data in files.items() if p.startswith('dist/')} != outputs:
        raise ValueError('source revision artifact mismatch')
    return dict(binding)
