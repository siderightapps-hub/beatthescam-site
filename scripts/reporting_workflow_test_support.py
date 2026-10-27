"""Disposable TEST Git checkouts. Never writes Git state in the real repository."""
import os
from pathlib import Path
import subprocess

import reporting_pilot as pilot
import reporting_trust as trust
import reporting_revision as revision

_OBJECTS = {}
_TREES = {}


def commit_files(root, files, *, message='TEST candidate', parent=None):
    root = Path(root).resolve()
    source = Path(__file__).resolve().parents[1]
    isolated_worker = (trust.environment() == 'test' and root.parent.name.startswith('bts-g1-test-'))
    if (root == source or source in root.parents) and not isolated_worker:
        raise ValueError('TEST Git objects must be outside source repository')
    pilot.check_names(files)
    root.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME='TEST fixture', GIT_COMMITTER_NAME='TEST fixture',
               GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_EMAIL='fixture@example.invalid',
               GIT_AUTHOR_DATE='2026-10-20T00:00:00Z', GIT_COMMITTER_DATE='2026-10-20T00:00:00Z')
    def git(*args, data=None):
        return subprocess.run(['git', '-C', str(root), '-c', 'core.hooksPath=/dev/null',
                               *args], input=data, env=env, capture_output=True, check=True).stdout
    if not (root / '.git').exists():
        git('init', '--quiet', '--object-format=sha1')
    branches = {}
    for name, data in files.items():
        node = branches
        parts = name.split('/')
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        cache_key = (str(root), pilot.sha(data))
        if cache_key not in _OBJECTS:
            _OBJECTS[cache_key] = git('hash-object', '-w', '--stdin', data=data).decode().strip()
        node[parts[-1]] = _OBJECTS[cache_key]
    def tree(node):
        entries = []
        for name, value in sorted(node.items()):
            if isinstance(value, dict):
                entries.append(('040000 tree ' + tree(value) + '\t' + name).encode() + b'\0')
            else:
                entries.append(('100644 blob ' + value + '\t' + name).encode() + b'\0')
        encoded = b''.join(entries)
        cache_key = (str(root), encoded)
        if cache_key not in _TREES:
            _TREES[cache_key] = git('mktree', '-z', data=encoded).decode().strip()
        return _TREES[cache_key]
    tree_sha = tree(branches)
    sha = git('commit-tree', tree_sha, *(['-p', parent] if parent else []),
              data=(message + '\n').encode()).decode().strip()
    # Working files and index become a clean disposable checkout.
    import reporting_workflow as workflow
    old = workflow.local_snapshot(root)
    for name in set(old) - set(files):
        (root / name).unlink()
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    git('update-ref', 'HEAD', sha)
    git('read-tree', sha)
    return {'version': revision.VERSION, 'source_commit': sha, 'source_tree': tree_sha,
            'candidate_map_sha256': trust.digest(pilot.hashes(files))}


def bind(root, outputs):
    """Upgrade older content/artifact fixtures to explicit TEST revision inputs."""
    import reporting_workflow as workflow
    for name, data in outputs.items():
        path = Path(root) / 'dist' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    files = (workflow.local_snapshot(root) if (Path(root) / '.git').exists()
             else pilot.tree(root, source=True))
    return commit_files(root, files)
