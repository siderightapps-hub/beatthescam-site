#!/usr/bin/env python3
"""Offline workflow adapter tests. Only ephemeral TEST keys/signatures are made."""
import copy
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from contextlib import redirect_stdout
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reporting_workflow as w
import reporting_pilot as v
import reporting_publication as p
import reporting_trust as t
import reporting_eligibility as e
import canon
from reporting_structured_selftest import fixture_page


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def run(on_fixture=None):
    rows = []
    def check(group, name, fn, error=None):
        try:
            value = fn()
            ok = error is None and bool(value)
            detail = '' if ok else 'expected assertion/refusal not observed'
        except Exception as exc:
            detail = str(exc)
            ok = error is not None and error in detail
        rows.append(dict(group=group, name=name, ok=ok, detail=detail))
    wf = json.loads((w.ROOT / w.WORKFLOW).read_text())  # JSON is a YAML subset.
    job = wf['jobs']['publication']; steps = job['steps'][1:]
    flat = json.dumps(wf)
    static = {
        'workflow identity': wf['name'] == 'Publication verification',
        'stable sole job identity': list(wf['jobs']) == ['publication'] and job['name'] == w.CHECK,
        'workflow permissions': wf['permissions'] == {'contents': 'read'},
        'job permissions': job['permissions'] == {'contents': 'read'},
        'no write or id-token': 'write' not in json.dumps([wf['permissions'], job['permissions']]) and 'id-token' not in flat,
        'minimal automatic events': set(wf['on']) == {'push', 'pull_request'},
        'main targets': all(x['branches'] == ['main'] for x in wf['on'].values()),
        'no event path filters': not any('paths' in k for x in wf['on'].values() for k in x),
        'no job skipping': not any(k in job for k in ('if', 'continue-on-error', 'strategy')),
        'no step skipping': not any(k in s for s in steps for k in ('if', 'continue-on-error')),
        'no secrets': 'secrets.' not in flat,
        'no environments': 'environment' not in job,
        'no deployment or signing command': not any(term in ' '.join(s.get('run','') for s in steps).lower() for term in ('deploy','sign','curl','gh ', 'netlify')),
        'no artifact transfer': not any('artifact@' in s.get('uses','') for s in steps),
        'immutable Actions': all(re.fullmatch(r'actions/[a-z-]+@[a-f0-9]{40}',s['uses']) for s in steps if 'uses' in s),
        'three exact data/control checkouts only': len([s for s in steps if 'actions/checkout@' in s.get('uses','')]) == 3,
        'checkout constraints': all(s['with'].get('persist-credentials') is False and s['with'].get('submodules') is False and s['with'].get('lfs') is False for s in steps[:2]),
        'trusted ref': steps[0]['with']['ref'] == '${{ env.TRUSTED_SHA }}' and steps[0]['with']['path'] == 'trusted',
        'candidate ref': steps[1]['with']['ref'] == '${{ env.CANDIDATE_SHA }}' and steps[1]['with']['path'] == 'candidate',
        'event head binding': job['env']['CANDIDATE_SHA'] == '${{ github.event.pull_request.head.sha || github.sha }}',
        'event base binding': job['env']['TRUSTED_SHA'] == '${{ github.event.pull_request.base.sha || github.event.before }}',
        'public pin required without fallback': job['env']['BTS_PRODUCTION_TRUST_SHA256'] == '${{ vars.BTS_PRODUCTION_TRUST_SHA256 }}',
        'production only': job['env']['BTS_REVIEW_ENVIRONMENT'] == 'production',
        'trusted working directory': job['defaults']['run'] == {'shell':'bash','working-directory':'trusted'},
        'trusted Python selector': steps[2]['with'] == {'python-version-file':'trusted/.python-version'},
        'trusted Node selector without cache': steps[3]['with'] == {'node-version-file':'trusted/.nvmrc','package-manager-cache':False},
        'hash-locked Python': steps[4]['run'] == 'python -I -m pip install --require-hashes --only-binary=:all: -r requirements-reporting.lock',
        'locked Node no lifecycle': steps[5]['run'] == 'npm ci --ignore-scripts --no-audit --no-fund',
        'fixed isolated entrypoint': steps[-1]['run'] == 'python -I scripts/reporting_workflow.py --candidate ../candidate --candidate-sha "$CANDIDATE_SHA" --trusted-sha "$TRUSTED_SHA" --approval-repository ../approval --approval-sha "$APPROVAL_SHA"',
        'no inline run interpolation': all('${{' not in s.get('run','') for s in steps),
        'bounded run': job['timeout-minutes'] == 20,
        'no chain triggers': not any(x in wf['on'] for x in ('workflow_run','workflow_call','workflow_dispatch','repository_dispatch','pull_request_target')),
    }
    for name, ok in static.items(): check('static', name, lambda ok=ok:ok)
    for name in ('daily-publish.yml','daily-search-console.yml','tweet-on-publish.yml'):
        text = (w.ROOT / '.github/workflows' / name).read_text()
        check('static', 'containment ' + name, lambda text=text:
              '  workflow_dispatch:' in text and not re.search(r'^  (push|pull_request|schedule|workflow_run):',text,re.M)
              and text.index('Reject automatic invocation') < text.index('- name: Checkout'))
    trusted = w.local_snapshot(w.ROOT) if (w.ROOT/'.git').exists() else v.tree(w.ROOT,source=True)
    # A clean archive has no Git database. This TEST-only reference lets binding
    # probes read existing immutable objects without creating fixture commits.
    git_source = Path(os.environ.get('BTS_WORKFLOW_TEST_GIT_SOURCE', str(w.ROOT)))
    head = w.git(git_source,'rev-parse','HEAD').decode().strip()
    committed = w.git_snapshot(git_source,head)
    check('binding', 'exact HEAD blob independent of dirty checkout',lambda:
          committed['scripts/build.py'] == w.git(git_source,'show',head+':scripts/build.py'))
    for sha in ('main', '0'*40, 'a'*39, 'a'*40+';echo injected', None):
        check('binding', 'invalid revision '+str(sha), lambda sha=sha:w.revision(sha), 'exact nonzero')
    for path in ('scripts/reporting_workflow.py',w.WORKFLOW,'.github/new-action/action.yml','scripts/sitecustomize.py','.npmrc'):
        changed=dict(trusted);changed[path]=b'raise SystemExit(0)'
        check('binding','candidate cannot replace '+path,lambda changed=changed:w.controls_match(changed,trusted),'control-plane change')
    deleted=dict(trusted);del deleted[w.WORKFLOW]
    check('binding','deleted workflow blocked',lambda:w.controls_match(deleted,trusted),'control-plane change')
    for mode in (b'120000', b'160000'):
        listing = mode+b' blob '+b'a'*40+b' 1\tunsafe\0'
        with patch.object(w,'git',side_effect=[(head+'\n').encode(),listing]):
            check('binding','nonregular entry '+mode.decode(),lambda:w.git_snapshot(w.ROOT,head),'nonregular')
    for path in (b'../outside',b'/outside',b'bad path'):
        listing=b'100644 blob '+b'a'*40+b' 1\t'+path+b'\0'
        with patch.object(w,'git',side_effect=[(head+'\n').encode(),listing]):
            check('binding','unsafe path '+path.decode(),lambda:w.git_snapshot(w.ROOT,head),'unsafe/noncanonical')
    with tempfile.TemporaryDirectory(prefix='bts-workflow-test-') as raw:
        temp=Path(raw).resolve();root=temp/'candidate';root.mkdir()
        for name,data in trusted.items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        authority=temp/'test-authority';authority.mkdir(mode=0o700)
        keys={}
        for role in t.ROLES:
            key=temp/('TEST-'+role)
            subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
            keys[role]=key
        with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'test','BTS_REVIEW_STORE':str(authority)}):
            cfg={'version':'bts-trust/v1','environment':'test','site':t.SITE,
                 'roles':{role:[{'identity':'test-'+role,'public_key':' '.join(key.with_suffix('.pub').read_text().split()[:2])}] for role,key in keys.items()},
                 'pilot_page_ids':['guide:workflow-test'], 'baseline_sha256':t.digest(v.hashes(v.tree(root/'dist'))), 'revocations_sha256':t.digest([])}
            write(authority/'trust.json',cfg);write(authority/'baseline.json',v.hashes(v.tree(root/'dist')));write(authority/'revoked.json',[])
            # TEST signatures; selection uses the actual six-only compatibility pin.
            sources=canon.load_canon();ids=list(e.contract_production_eligible_ids(sources))
            assert len(ids)==6 and set(ids)==set(e.REVIEWED_CONTRACT_IDS)
            for rid in ids: write(e.packet_path(rid),e.issue_reviewed(sources,rid,reviewer='test-contracts',private_key=keys['contracts']))
            page=fixture_page();page.update(slug='workflow-test',reporting_routes=ids,
                quick_answer={'kind':'action-summary','route_ids':ids},
                faq=[{'kind':'action-faq','question_id':'how-to-contact','route_ids':ids}])
            posts=t.read_json(root/'content/posts.json');posts.append(page);write(root/'content/posts.json',posts)
            # This synthetic corpus has no hubs. Real hub bytes are never edited;
            # a separate negative below proves the inherited gate still rejects them.
            write(root/'content/category-hubs.json',{})
            ident='guide:workflow-test'
            context=p.issue_reviewed(page,sources,page_id=ident,private_key=keys['context'],reviewer='test-context',audience=['England','Wales','Scotland','Northern Ireland'])
            write(authority/'packets'/(v.sha(ident.encode())+'.json'),context)
            outputs=v.tree(root/'dist');outputs.update(v.render_selected(root,{ident:page},posts,{},sources,outputs))
            for name,data in outputs.items():
                path=root/'dist'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            fixture=dict(trusted)
            fixture['content/posts.json']=(root/'content/posts.json').read_bytes()
            fixture['content/category-hubs.json']=b'{}\n'
            fixture.update({'dist/'+n:b for n,b in outputs.items()})
            fixture.update({'deployment/review-store/'+n:b for n,b in v.tree(authority).items()})
            from reporting_workflow_test_support import commit_files
            revision=commit_files(root, fixture)
            body=dict(t.header(v.VERSION),reviewer='test-release',manifest=v.candidate(root,outputs,source_revision=revision))
            release=t.sign(body,keys['release'],'release',v.VERSION)
            if on_fixture is not None:
                on_fixture(temp, root, trusted, fixture, revision, release, keys, cfg)
            # TEST transport convenience only: remove packet before passing
            # candidate data to the verifier, exactly as detached CLI transport.
            fixture['deployment/review-store/release.json']=t.canonical(release)
            def verify(f=fixture):
                data=dict(f);raw=data.pop('deployment/review-store/release.json',None)
                packet=json.loads(raw) if raw is not None else None
                return w.verify_data(data,trusted,production=False,source_revision=revision,release_packet=packet)
            check('positive','authentic TEST contracts/context/release and exact output',lambda:verify()['deployment_eligible'] is False)
            def changed(name,value):
                result=dict(fixture);result[name]=t.canonical(value)+b'\n';return result
            check('negative','missing baseline',lambda:verify({k:b for k,b in fixture.items() if k!='deployment/review-store/baseline.json'}),'No such file')
            cfgempty=dict(cfg,baseline_sha256=t.digest({}))
            f=changed('deployment/review-store/trust.json',cfgempty);f['deployment/review-store/baseline.json']=b'{}'
            check('negative','unestablished baseline',lambda:verify(f),'UNESTABLISHED')
            check('negative','empty scope',lambda:verify(changed('deployment/review-store/trust.json',dict(cfg,pilot_page_ids=[]))),'empty pilot scope')
            check('negative','out of scope',lambda:verify(changed('deployment/review-store/trust.json',dict(cfg,pilot_page_ids=['guide:another']))),'unexpected/missing structured')
            check('negative','wrong root site',lambda:verify(changed('deployment/review-store/trust.json',dict(cfg,site='example.com'))),'schema/environment/site')
            check('negative','wrong root environment',lambda:verify(changed('deployment/review-store/trust.json',dict(cfg,environment='production'))),'schema/environment/site')
            f=dict(fixture);f['dist/'+v.output_path(ident)]+=b'X'
            check('negative','output mutation',lambda f=f:verify(f),'deterministic page render')
            f=dict(fixture);f['dist/extra.txt']=b'extra'
            check('negative','extra output',lambda f=f:verify(f),'missing or unexpected protected output')
            f=dict(fixture);del f['dist/index.html']
            check('negative','missing output',lambda f=f:verify(f),'missing or unexpected protected output')
            for name in ('release.json','packets/'+v.sha(ident.encode())+'.json','contracts/'+v.sha(ids[0].encode())+'.json'):
                f=dict(fixture);del f['deployment/review-store/'+name]
                check('negative','missing approval '+name,lambda f=f:verify(f),'detached release approval' if name=='release.json' else 'No such file')
            for field,value in (('site','example.com'),('environment','production'),('reviewer','test-context')):
                packet=copy.deepcopy(release);packet['body'][field]=value
                check('negative','release '+field,lambda packet=packet:verify(changed('deployment/review-store/release.json',packet)), 'mismatch' if field!='reviewer' else 'unauthorized signer')
            revoked=[body['decision_id']]
            f=changed('deployment/review-store/trust.json',dict(cfg,revocations_sha256=t.digest(revoked)))
            f['deployment/review-store/revoked.json']=t.canonical(revoked)
            check('negative','revoked release',lambda f=f:verify(f),'revoked')
            check('negative','revocation digest mismatch',lambda:verify(changed('deployment/review-store/revoked.json',revoked)),'revoked')
            held_sources=copy.deepcopy(sources)
            rec=next(r for group in e.s._GROUPS for r in held_sources.get(group,[]) if r['key']=='citizens-advice')
            rec['actions']['unreviewed-copy']=copy.deepcopy(rec['actions']['consumer-advice-english'])
            bad=copy.deepcopy(release);bad['body']['manifest']['pages'][0]['route_ids']=['citizens-advice:unreviewed-copy']
            f=changed('deployment/review-store/release.json',bad);f['content/sources.json']=t.canonical(held_sources)
            check('negative','held canonical contract before signature acceptance',lambda f=f:verify(f),'no independent canon clearance')
            bad=copy.deepcopy(body);bad['manifest']['inputs_sha256']='0'*64
            packet=t.sign(bad,keys['release'],'release',v.VERSION)
            check('negative','authentic TEST wrong manifest',lambda:verify(changed('deployment/review-store/release.json',packet)),'manifest differs')
            f=dict(fixture);f['content/category-hubs.json']=trusted['content/category-hubs.json']
            check('negative','inherited ordinary hub gate still enforced',lambda f=f:verify(f),'hub gate blocked')
            with patch.object(w.runtime,'require',side_effect=ValueError('measured runtime mismatch')):
                check('negative','wrong measured runtime',lambda:verify(),'runtime mismatch')
            with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production'}):
                for label,pin in (('missing',''),('malformed','bad'),('wrong','0'*64)):
                    with patch.dict(os.environ,{'BTS_PRODUCTION_TRUST_SHA256':pin}):
                        check('negative',label+' production pin',lambda:w.verify_data(fixture,trusted),'externally pinned')
                with patch.dict(os.environ,{'BTS_PRODUCTION_TRUST_SHA256':t.digest(cfg)}):
                    check('negative','TEST root with matching pin cannot authorize production',lambda:w.verify_data(fixture,trusted),'schema/environment/site')
                production={k:b for k,b in trusted.items()}
                pin=t.digest(json.loads(production['deployment/review-store/trust.json']))
                with patch.dict(os.environ,{'BTS_PRODUCTION_TRUST_SHA256':pin}):
                    check('negative','real frozen production candidate HOLD',lambda:w.verify_data(production,trusted),'UNESTABLISHED')
                    cfgbad=json.loads(production['deployment/review-store/trust.json']);cfgbad['site']='example.com'
                    production['deployment/review-store/trust.json']=t.canonical(cfgbad)
                    check('negative','production mirror mismatch',lambda:w.verify_data(production,trusted),'externally pinned')
    for exception,code in ((ValueError('hold'),1),(RuntimeError('fault'),2)):
        with patch.object(w,'local_snapshot',return_value={}),patch.object(w,'verify_data',side_effect=exception),redirect_stdout(io.StringIO()):
            check('binding','nonzero outcome '+str(code),lambda code=code:w.main(['--candidate',str(w.ROOT),'--diagnostic-working-tree'])==code)
    counts={g:{'pass':sum(r['ok'] for r in rows if r['group']==g),'total':sum(r['group']==g for r in rows)} for g in sorted({r['group'] for r in rows})}
    print(json.dumps({'counts':counts,'results':rows},indent=2))
    return int(not all(r['ok'] for r in rows))


if __name__ == '__main__': raise SystemExit(run())
