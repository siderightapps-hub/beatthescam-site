#!/usr/bin/env python3
"""Exact-commit subprocess CLI regressions using disposable TEST authority."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reporting_workflow as w
import reporting_pilot as v
import reporting_trust as t
from reporting_workflow_test_support import commit_files
from reporting_workflow_selftest import run as original_checks


def run():
    rows = []
    def check(group, name, fn, reason=None):
        try:
            value = fn()
            ok = bool(value) if reason is None else False
            detail = '' if ok else 'expected result not observed'
        except Exception as exc:
            detail = str(exc)
            ok = reason is not None and reason in detail
        rows.append(dict(group=group, name=name, ok=ok, detail=detail))

    wf = json.loads((w.ROOT / w.WORKFLOW).read_text())
    job = wf['jobs']['publication']
    commands = 'python -I -B scripts/reporting_workflow_selftest.py\npython -I -B scripts/reporting_workflow_cli_selftest.py'
    steps = job['steps']
    matches = [s for s in steps if s.get('run') == commands]
    check('ci', 'mandatory suites in stable required job', lambda:
          len(matches) == 1 and job['name'] == w.CHECK and 'if' not in matches[0]
          and 'continue-on-error' not in matches[0] and steps.index(matches[0]) < len(steps)-1)
    gate = (w.ROOT / '.github/workflows/gate-selftest.yml').read_text()
    check('ci', 'offline gate invokes CLI before legacy gates', lambda:
          commands.splitlines()[1] in gate and gate.index('reporting_workflow_cli_selftest.py')
          < gate.index('gate_quickanswer_selftest.py'))
    check('ci', 'exact approval SHA has no fallback', lambda:
          job['env']['APPROVAL_SHA'] == '${{ vars.BTS_PUBLICATION_APPROVAL_SHA }}')
    check('ci', 'production check never selects TEST', lambda:
          '--test-only' not in steps[-1]['run'] and job['env']['BTS_REVIEW_ENVIRONMENT'] == 'production')
    check('ci', 'event SHA validation precedes checkout', lambda:
          steps[0].get('working-directory') == '.' and 'for sha in "$CANDIDATE_SHA" "$TRUSTED_SHA"' in steps[0].get('run',''))
    approval_checkout = next(s for s in steps if s.get('with', {}).get('path') == 'approval')
    check('ci', 'approval data checkout fixed and credentialless', lambda:
          approval_checkout['with'] == dict(steps[1]['with'], ref='${{ env.APPROVAL_SHA }}', path='approval'))
    check('ci', 'missing approval ref blocked before checkout', lambda:
          any('[[ "$APPROVAL_SHA" =~ ^[0-9a-f]{40}$' in s.get('run', '')
              for s in steps[:steps.index(approval_checkout)]))

    current = w.local_snapshot(w.ROOT) if (w.ROOT / '.git').exists() else v.tree(w.ROOT, source=True)
    served = {p: data for p, data in current.items() if p.startswith('dist/')}
    critical = w.critical_inventory(current)
    check('inventory', 'every served file critical', lambda: bool(served) and set(served) <= set(critical))
    check('inventory', 'served inventory cryptographic identity', lambda:
          {p: critical[p] for p in served} == v.hashes(served))
    check('inventory', 'future outputs critical data, not immutable controls', lambda:
          w.critical_path('dist/future/file.json') and not w.control_path('dist/future/file.json'))
    outputs = {p[5:]: data for p, data in served.items()}
    base = v.hashes(outputs)
    check('inventory', 'current complete served set accepted', lambda:v.protected_output(outputs,base,set()) == base)
    check('inventory', 'current served set plus one file rejected',
          lambda:v.protected_output(dict(outputs,unexpected=b'X'),base,set()),'missing or unexpected')
    check('inventory', 'current served set minus one file rejected',
          lambda:v.protected_output({p:b for p,b in outputs.items() if p!='index.html'},base,set()),'missing or unexpected')
    check('inventory', 'one-byte current served mutation rejected',
          lambda:v.protected_output(dict(outputs,**{'index.html':outputs['index.html']+b'X'}),base,set()),'non-pilot output differs')
    for names in (['../outside'], ['/absolute'], ['dist/./x'], ['dist/a/../x'],
                  ['dist/x', 'dist/x'], ['dist/x', 'dist/X'], ['dist\\x'],
                  ['dist/caf\u00e9'], ['dist/cafe\u0301'], ['dist//x'], ['.git/config'], ['dist/.GIT/config']):
        check('inventory', 'reject path '+repr(names), lambda names=names:v.check_names(names),
              'colliding' if len(names)>1 else 'unsafe/noncanonical')

    def fixture(temp, root, trusted, files, binding, release, keys, cfg):
        # Exercise the actual CLI with a small complete TEST publication.
        # Real 454-file membership is exercised separately above. Keeping
        # unrelated guides' images/manifests out avoids thousands of repeated
        # Git subprocess reads per negative; no verifier control is mocked.
        required_content = {'content/posts.json', 'content/category-hubs.json',
                            'content/sources.json', 'content/site.json', 'content/affiliates.json'}
        trusted = {p:b for p,b in trusted.items() if w.control_path(p) or p in required_content}
        pilot_path = release['body']['manifest']['pages'][0]['path']
        output_paths = {'index.html','assets/app.js','assets/styles.css',pilot_path}
        original_files = {p:b for p,b in files.items() if w.control_path(p)
                          or p in required_content or p.startswith('deployment/review-store/')
                          or p.startswith('dist/') and p[5:] in output_paths}
        baseline = {p[5:]:v.sha(b) for p,b in original_files.items()
                    if p.startswith('dist/') and p[5:] != pilot_path}
        cfg = dict(cfg, baseline_sha256=t.digest(baseline))
        original_files['deployment/review-store/trust.json'] = t.canonical(cfg)
        original_files['deployment/review-store/baseline.json'] = t.canonical(baseline)
        root = temp/'cli-candidate'
        binding = commit_files(root, original_files)
        trusted_root = temp/'trusted'
        trusted_binding = commit_files(trusted_root, trusted)
        approval_root = temp/'approval'
        entry = trusted_root/'scripts/reporting_workflow.py'
        environment = dict(os.environ, BTS_REVIEW_ENVIRONMENT='test')
        environment.pop('BTS_PRODUCTION_TRUST_SHA256', None)
        def raw_sign(body):
            path = temp/'raw-TEST-release'
            path.write_bytes(t.canonical(body))
            signature = path.with_suffix('.sig')
            if signature.exists(): signature.unlink()
            subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys['release']),
                            '-n', v.VERSION+':test', str(path)], check=True, capture_output=True)
            return dict(body=copy.deepcopy(body), signature=signature.read_text())
        with v.public_review_store(root):
            body = copy.deepcopy(release['body'])
            body['manifest'] = v.candidate(root,v.tree(root/'dist'),source_revision=binding)
            release = raw_sign(body)
        def invoke(name, *, data=None, packet=release, code=1, reason='', diagnostic=False,
                   candidate_sha=None, resign_revision=False, env=None, test=True, mutation=None):
            selected = original_files if data is None else data
            identity = commit_files(root, selected)
            if resign_revision:
                body = copy.deepcopy(packet['body'])
                body['manifest']['source_revision'] = identity
                packet = raw_sign(body)
            args = [sys.executable, '-I', '-B', str(entry), '--candidate', str(root)]
            if diagnostic:
                args += ['--diagnostic-working-tree']
            else:
                args += ['--candidate-sha', candidate_sha or identity['source_commit'],
                         '--trusted-sha', trusted_binding['source_commit']]
            if packet is not None:
                transport = commit_files(approval_root, {'release.json':t.canonical(packet)})
                args += ['--approval-repository', str(approval_root),
                         '--approval-sha', transport['source_commit']]
            if test: args += ['--test-only']
            if mutation: mutation()
            result = subprocess.run(args, env=env or environment, cwd=trusted_root,
                                    capture_output=True, text=True, timeout=120)
            outcome = json.loads(result.stdout)
            expected = {0:'PASS',1:'BLOCKED',2:'ERROR'}[code]
            good = (result.returncode == code and outcome['outcome'] == expected
                    and outcome['deployment_eligible'] is False and reason in outcome.get('reason',''))
            if code == 0:
                good = good and outcome['source_revision'] == identity and outcome['test_only'] is True
                good = good and outcome['candidate_sha'] == identity['source_commit']
                good = good and outcome['candidate_map_sha256'] == identity['candidate_map_sha256']
            rows.append(dict(group='cli', name=name, ok=good, exit=result.returncode,
                             outcome=outcome['outcome'], reason=outcome.get('reason','')))
        def changed(path, data):
            result = dict(original_files)
            result[path] = data
            return result
        try:
            invoke('PASS authentic exact commit and detached TEST release', code=0)
            invoke('successful data diagnostic never certifies a commit', diagnostic=True,
                   reason='diagnostic verification cannot satisfy')
            invoke('ERROR unavailable exact Git object', candidate_sha='f'*40, code=2,
                   reason='CalledProcessError')
            invoke('BLOCKED malformed revision', candidate_sha='main', reason='exact nonzero')
            invoke('missing release', packet=None, reason='detached release approval required')
            # An empty commit has the same tree and output, but a different SHA.
            second = commit_files(root, original_files, message='TEST different revision, same bytes')
            invoke('same output and same tree different revision rejects', candidate_sha=second['source_commit'],
                   reason='approval source revision mismatch')
            invoke('D9J documentation-only revision rejects unchanged approval',
                   data=changed('docs/unbound-review-note.md', b'TEST alternate repository candidate\n'),
                   reason='approval source revision mismatch')
            invoke('same revision uncommitted source mutation rejects',
                   mutation=lambda:(root/'content/posts.json').write_bytes(b'[]\n'),
                   reason='working candidate differs')
            invoke('same revision uncommitted output mutation rejects',
                   mutation=lambda:(root/'dist/index.html').write_bytes(b'X'),
                   reason='working candidate differs')
            for field in ('source_commit', 'source_tree', 'candidate_map_sha256'):
                body = copy.deepcopy(release['body'])
                body['manifest']['source_revision'][field] = '1'*len(body['manifest']['source_revision'][field])
                invoke('authentic wrong '+field, packet=raw_sign(body), reason='approval source revision mismatch')
            edited = copy.deepcopy(release)
            edited['body']['manifest']['source_revision']['source_commit'] = '1'*40
            invoke('editing revision invalidates signature', packet=edited, reason='signature authentication failed')
            historical = copy.deepcopy(release['body'])
            historical['version'] = 'beatthescam-pilot-release-v2'
            invoke('historical schema fails closed', packet=raw_sign(historical), reason='wrong release schema')
            missing = copy.deepcopy(release['body'])
            del missing['manifest']['source_revision']
            invoke('missing revision never inferred', packet=raw_sign(missing), reason='approval source revision mismatch')
            for field, value, error in (
                    ('reviewer','test-context','unauthorized signer'),
                    ('reviewer','unknown-reviewer','unauthorized signer'),
                    ('site','wrong.example','environment/site/role mismatch'),
                    ('environment','production','environment/site/role mismatch'),
                    ('expires_at','2020-01-01T00:00:00+00:00','approval is stale')):
                body = copy.deepcopy(release['body']); body[field] = value
                invoke('authentic release wrong '+field+' '+value, packet=raw_sign(body), reason=error)
            for label, value in (('missing',''), ('wrong','0'*64), ('malformed','invalid')):
                env = dict(environment, BTS_REVIEW_ENVIRONMENT='production', BTS_PRODUCTION_TRUST_SHA256=value)
                invoke(label+' external production pin', env=env, test=False, reason='externally pinned')
            invoke('empty current scope despite authentic approval',
                   data=changed('deployment/review-store/trust.json',t.canonical(dict(cfg,pilot_page_ids=[]))),
                   reason='empty pilot scope')
            revoked=[release['body']['decision_id']]
            data=changed('deployment/review-store/trust.json',t.canonical(dict(cfg,revocations_sha256=t.digest(revoked))))
            data['deployment/review-store/revoked.json']=t.canonical(revoked)
            invoke('revoked release',data=data,reason='revoked')
            selected_page=release['body']['manifest']['pages'][0]
            required_approvals={
                'contracts/':v.sha(selected_page['route_ids'][0].encode()),
                'packets/':v.sha(selected_page['page_id'].encode()),
            }
            for prefix, digest in required_approvals.items():
                name='deployment/review-store/'+prefix+digest+'.json'
                assert name in original_files
                data={p:b for p,b in original_files.items() if p!=name}
                invoke('missing '+prefix+'approval',data=data,resign_revision=True,reason='No such file')
            for label, data, reason in (
                ('extra served file',changed('dist/extra.txt',b'X'),'missing or unexpected protected output'),
                ('missing served file',{p:b for p,b in original_files.items() if p!='dist/index.html'},'missing or unexpected protected output'),
                ('one-byte served mutation',changed('dist/index.html',original_files['dist/index.html']+b'X'),'non-pilot output differs')):
                invoke(label,data=data,resign_revision=True,reason=reason)
            body=copy.deepcopy(release['body']);body['manifest']['inputs_sha256']='0'*64
            invoke('authentic wrong manifest',packet=raw_sign(body),reason='manifest differs')
            body=copy.deepcopy(release['body']);body['manifest']['files']['index.html']='0'*64
            invoke('stale artifact manifest',packet=raw_sign(body),reason='manifest differs')
            badenv=dict(environment,TZ='Europe/London')
            invoke('actual wrong runtime profile',env=badenv,reason='runtime identity mismatch')
            sources=json.loads(original_files['content/sources.json'])
            import reporting_eligibility as eligibility
            record=next(r for group in eligibility.s._GROUPS for r in sources.get(group,[]) if r['key']=='citizens-advice')
            record['actions']['unreviewed-copy']=copy.deepcopy(record['actions']['consumer-advice-english'])
            body=copy.deepcopy(release['body'])
            body['manifest']['pages'][0]['route_ids']=['citizens-advice:unreviewed-copy']
            invoke('held contract despite authentic release',data=changed('content/sources.json',t.canonical(sources)),
                   packet=raw_sign(body),resign_revision=True,reason='no independent canon clearance')
            for path in ('scripts/reporting_workflow.py','scripts/reporting_workflow_cli_selftest.py',w.WORKFLOW):
                invoke('candidate cannot replace '+path,data=changed(path,b'raise SystemExit(0)\n'),
                       reason='control-plane change')
            link=temp/'symlink-artifact'; link.mkdir()
            (link/'alias').symlink_to(root/'dist/index.html')
            check('inventory','symlink served file rejected',lambda:v.tree(link),'symlink')
            check('revision','missing explicit revision rejected',lambda:v.verify_release(release,root,v.tree(root/'dist'),production=False),
                  'explicit verified source revision')
        finally:
            commit_files(root, original_files)

    with redirect_stdout(io.StringIO()) as output:
        original_code = original_checks(fixture)
    check('original', 'original 82 checks remain passing', lambda:original_code == 0)
    summary = {g:{'pass':sum(r['ok'] for r in rows if r['group']==g),
                  'total':sum(r['group']==g for r in rows)}
               for g in sorted({r['group'] for r in rows})}
    print(json.dumps({'counts':summary,'results':rows},indent=2))
    return int(not all(r['ok'] for r in rows))


if __name__ == '__main__':
    raise SystemExit(run())
