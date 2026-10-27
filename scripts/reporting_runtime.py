"""Measured approval runtime; declarations are inputs, never environment overrides.

Selected-page verification uses captured CSS/JS and does not run Pillow or asset
minifiers. Their optional full-site-build profile is separate from this profile.
No installer, network, source mutation or deployment happens here.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
FILES = ('.python-version', '.nvmrc', 'package.json', 'package-lock.json',
         'requirements-reporting.txt', 'requirements-reporting.lock', 'scripts/reporting-runtime.json')


def sha(path):
    import reporting_trust as trust
    return hashlib.sha256(trust.read_file(path)).hexdigest()


def tool_version(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=True)
    return result.stdout.strip().removeprefix('v')


def identity(root=ROOT):
    """Actual process/tool versions, not caller-supplied expected values."""
    try:
        import idna
    except ImportError as exc:
        raise ValueError('runtime dependency missing: install the declared reporting lock in the isolated runtime') from exc
    return {'implementation': platform.python_implementation(),
            'python': platform.python_version(), 'unicode': unicodedata.unidata_version,
            'idna': idna.__version__, 'idna_distribution': importlib.metadata.version('idna'),
            'node': tool_version(['node', '--version']), 'npm': tool_version(['npm', '--version']),
            'utf8_mode': sys.flags.utf8_mode,
            'locale': {k: os.environ.get(k) for k in ('TZ', 'LC_ALL', 'LANG')},
            'timezone_offset': time.timezone,
            'files': {p: sha(Path(root)/p) for p in FILES}}


def require(root=ROOT):
    import reporting_trust as trust
    root = Path(root)
    policy = trust.read_json(root/'scripts/reporting-runtime.json')
    if (not isinstance(policy, dict) or set(policy) != {'version','runtime','locks'}
            or policy['version'] != 'bts-review-runtime/v1'
            or set(policy['locks']) != {'requirements-reporting.txt','requirements-reporting.lock','package-lock.json'}):
        raise ValueError('runtime policy schema mismatch')
    actual = identity(root)
    expected = policy['runtime']
    if {k: v for k, v in actual.items() if k != 'files'} != expected:
        raise ValueError('runtime identity mismatch: use the pinned Python/Unicode/idna/Node/npm and UTC/C/UTF-8 profile')
    for name, wanted in policy['locks'].items():
        if sha(root/name) != wanted:
            raise ValueError('runtime dependency lock identity mismatch: '+name)
    if (root/'.python-version').read_text().strip() != expected['python'] or (root/'.nvmrc').read_text().strip() != expected['node']:
        raise ValueError('runtime selector identity mismatch')
    package = trust.read_json(root/'package.json')
    if package.get('engines') != {'node':expected['node'], 'npm':expected['npm']}:
        raise ValueError('Node/npm declaration mismatch')
    return actual


if __name__ == '__main__':
    try:
        print(json.dumps(require(), indent=2))
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print('BLOCKED: '+str(exc), file=sys.stderr)
        raise SystemExit(1)
