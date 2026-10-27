#!/usr/bin/env python3
"""Isolated G1 rehearsal. TEST signatures only; no hosting or deploy credentials.

The parent copies declared candidate inputs into a disposable directory, then
starts a worker with a small environment allowlist. No real page is migrated.
"""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

import reporting_trust as t
import reporting_pilot as v
import reporting_publication as p
import reporting_runtime as runtime


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')


def encrypted_rehearsal(authority, cfg, body):
    """Own disposable agent and encrypted TEST backup; never use a real agent."""
    ambient={k:os.environ.get(k) for k in ('SSH_AUTH_SOCK','SSH_AGENT_PID')}
    if any(ambient.values()): raise ValueError('TEST worker must not inherit an existing agent')
    with tempfile.TemporaryDirectory(prefix='bts-g1-agent-test-') as raw:
        home=Path(raw).resolve(); key=home/'test-encrypted-key'
        phrase='DISPOSABLE TEST PASSPHRASE ONLY'
        def run(argv, **kw):
            return subprocess.run(argv,capture_output=True,check=True,timeout=15,**kw)
        run(['ssh-keygen','-q','-t','ed25519','-N',phrase,'-f',str(key)])
        public=key.with_suffix('.pub'); public.chmod(0o600)
        backup=home/'encrypted-backup'; restored=home/'restored-test-key'
        shutil.copyfile(key,backup);backup.chmod(0o600)
        locked=subprocess.run(['ssh-keygen','-y','-P','WRONG TEST PASSPHRASE','-f',str(backup)],
                              capture_output=True,stdin=subprocess.DEVNULL,timeout=15)
        if locked.returncode == 0: raise ValueError('TEST backup is not encrypted')
        shutil.copyfile(backup,restored);restored.chmod(0o600)
        run(['ssh-keygen','-p','-P',phrase,'-N','','-f',str(restored)])
        recovered=run(['ssh-keygen','-y','-f',str(restored)]).stdout.split()[:2]
        if recovered != public.read_bytes().split()[:2]: raise ValueError('backup fingerprint differs')
        ask=home/'askpass';ask.write_text('#!/bin/sh\nprintf "%s\\n" "DISPOSABLE TEST PASSPHRASE ONLY"\n');ask.chmod(0o700)
        sock=home/'agent.sock'
        agent=subprocess.Popen(['ssh-agent','-D','-a',str(sock)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        agent_env=dict(os.environ,SSH_AUTH_SOCK=str(sock),SSH_AGENT_PID=str(agent.pid),
            SSH_ASKPASS=str(ask),SSH_ASKPASS_REQUIRE='force',DISPLAY='test-only')
        try:
            for _ in range(40):
                if sock.exists(): break
                if agent.poll() is not None: raise ValueError('disposable ssh-agent could not start')
                time.sleep(0.05)
            run(['ssh-add','-t','60',str(key)],stdin=subprocess.DEVNULL,env=agent_env)
            test_cfg=copy.deepcopy(cfg)
            test_cfg['roles']['contracts'][0]['public_key']=' '.join(public.read_text().split()[:2])
            write(authority/'trust.json',test_cfg)
            with patch.dict(os.environ,agent_env,clear=True):
                packet=t.sign(body,public,'contracts',body['version'])
            if key.read_bytes() in t.canonical(packet): raise ValueError('private material in packet')
            run(['ssh-add','-D'],env=agent_env)
            unloaded=subprocess.run(['ssh-add','-l'],env=agent_env,capture_output=True,timeout=15)
            if unloaded.returncode != 1: raise ValueError('TEST agent was not emptied')
        finally:
            write(authority/'trust.json',cfg)
            agent.terminate();agent.wait(timeout=5)
        if sock.exists(): raise ValueError('temporary TEST socket was not removed')
    if home.exists(): raise ValueError('temporary TEST key directory was not removed')
    if {k:os.environ.get(k) for k in ambient} != ambient:
        raise ValueError('ambient agent environment changed')
    return {'encrypted_backup_restored':True,'own_agent_only':True,'agent_unloaded':True,
            'agent_terminated':agent.poll() is not None,'socket_and_key_directory_removed':True,
            'existing_agent_untouched':True}


def equivalent_worker():
    """Recompute the actual verification-only build identity, never full build()."""
    import reporting_provider as provider
    root=p.ROOT
    if not root.parent.name.startswith('bts-g2-equivalent-test-') or t.environment()!='test':
        raise ValueError('equivalent proof requires an isolated TEST copy')
    files=v.tree(root/'dist')
    release=t.read_json(t.store()/'release.json',protected=True)
    import reporting_revision
    revision=reporting_revision.worktree(root,os.environ.get('BTS_TEST_SOURCE_COMMIT'))
    result=v.verify_test_bundle(release,root,v.zip_bytes(files),source_revision=revision)
    manifest=v.candidate(root,files,source_revision=revision)
    return {'manifest':manifest,'manifest_sha256':t.digest(manifest),
            'canonical_archive_sha256':v.sha(v.zip_bytes(files)),
            'files':v.hashes(files),'security_projections':provider.projections(files),
            'runtime':runtime.require(),'deployment_eligible':result['deployment_eligible']}


def equivalent_proof(root, authority, release):
    write(authority/'release.json',release)
    results=[]
    with tempfile.TemporaryDirectory(prefix='bts-g2-equivalent-test-') as raw:
        parent=Path(raw).resolve()
        for label in ('first','second'):
            candidate=parent/label
            shutil.copytree(root,candidate,ignore=shutil.ignore_patterns('__pycache__'))
            env={k:os.environ[k] for k in ('PATH','TZ','LC_ALL','LANG','PYTHONUTF8') if k in os.environ}
            env.update(HOME=str(parent),PYTHONDONTWRITEBYTECODE='1',BTS_REVIEW_ENVIRONMENT='test',
                       BTS_REVIEW_STORE=str(authority),BTS_TEST_SOURCE_COMMIT=release['body']['manifest']['source_revision']['source_commit'])
            run=subprocess.run([sys.executable,str(candidate/'scripts/reporting_preflight_selftest.py'),
                                '--equivalent-worker'],cwd=candidate,env=env,
                               capture_output=True,text=True,check=True,timeout=120)
            results.append(json.loads(run.stdout))
    if results[0]!=results[1]: raise ValueError('equivalent build identity differs')
    result=results[0]
    return {'same_frozen_candidate_and_public_authority':True,'fresh_candidate_copies':2,
            'identical_manifest_sha256':result['manifest_sha256'],
            'identical_archive_sha256':result['canonical_archive_sha256'],
            'identical_file_count':len(result['files']),
            'identical_security_projection_count':len(result['security_projections']),
            'identical_runtime':True,'manifest':result['manifest'],
            'deployment_eligible':False,
            'proof_scope':'verification-only committed artifact plus authenticated selected-page rerender; normal full build remains blocked'}


def worker():
    import canon
    import reporting_eligibility as e
    import reporting_reviewer as ux
    from reporting_structured_selftest import fixture_page
    root = p.ROOT
    if '.git' in [x.name for x in root.iterdir()] or not root.parent.name.startswith('bts-g1-test-'):
        raise ValueError('worker requires the isolated disposable candidate')
    runtime.require()
    authority = root.parent/'test-authority'; authority.mkdir(mode=0o700)
    output = root.parent/'test-output'; output.mkdir(mode=0o700)
    os.environ['BTS_REVIEW_STORE'] = str(authority)
    os.environ['BTS_REVIEW_ENVIRONMENT'] = 'test'
    os.environ.pop('BTS_PRODUCTION_TRUST_SHA256', None)
    keys = {}
    for role in t.ROLES:
        key = root.parent/('test-'+role)
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)], check=True)
        keys[role] = key
    cfg = {'version':'bts-trust/v1','environment':'test','site':t.SITE,
        'roles':{role:[{'identity':'test-'+role,'public_key':' '.join(key.with_suffix('.pub').read_text().split()[:2])}]
                 for role,key in keys.items()}, 'pilot_page_ids':['guide:isolated-test-review'],
        'baseline_sha256':'0'*64, 'revocations_sha256':t.digest([])}
    files = v.tree(root/'dist'); base = v.hashes(files)
    cfg['baseline_sha256'] = t.digest(base)
    write(authority/'baseline.json', base); write(authority/'revoked.json', []); write(authority/'trust.json',cfg)
    sources = canon.load_canon(); rid = 'citizens-advice:consumer-advice-english'
    rows = []
    def check(name, fn, reason=None):
        try:
            result = fn()
            ok = bool(result) if reason is None else False
            detail = '' if ok else 'expected refusal not observed' if reason else 'assertion false'
        except Exception as exc:
            detail = str(exc)
            ok = reason is not None and reason in detail
        rows.append({'name':name,'ok':ok,'detail':detail})
    def args(role, **changes):
        value = argparse.Namespace(environment='test',role=role,candidate=root,reviewer='test-'+role,
            route_id=None,page=None,page_id=None,audience=None,allow_empty=False,artifact=None,
            expected_receipt_sha256=None,key_file=keys[role],output=output/(role+'.json'),test_only=True)
        for k,val in changes.items(): setattr(value,k,val)
        return value
    def sign(a):
        receipt = ux.prepare(a); a.expected_receipt_sha256=t.digest(receipt)
        ux.issue(a); return t.read_json(a.output)
    contract_args=args('contracts',route_id=rid)
    contract=sign(contract_args); write(e.packet_path(rid),contract)
    check('valid TEST contract signature',lambda:bool(e.verify_contract(sources,rid)))
    # TEST signatures; selection uses actual six-only contract eligibility.
    eligible=list(e.contract_production_eligible_ids(sources))
    assert len(eligible)==6 and set(eligible)==set(e.REVIEWED_CONTRACT_IDS)
    for route in eligible:
        if route == rid: continue
        extra=sign(args('contracts',route_id=route,output=output/(v.sha(route.encode())+'.json')))
        write(e.packet_path(route),extra)
        check('valid TEST endorsement '+route,lambda route=route:bool(e.verify_contract(sources,route)))
    page=fixture_page(); page.update(slug='isolated-test-review',reporting_routes=[rid],
        quick_answer={'kind':'action-summary','route_ids':eligible},
        faq=[{'kind':'action-faq','question_id':'how-to-contact','route_ids':eligible}])
    page['reporting_routes']=eligible
    posts=t.read_json(root/'content/posts.json');posts.append(page);write(root/'content/posts.json',posts)
    page_file=output/'page.json';write(page_file,page)
    identity='guide:'+page['slug']
    context_args=args('context',page=page_file,page_id=identity,audience=['England','Wales','Scotland','Northern Ireland'])
    context=sign(context_args)
    context_path=authority/'packets'/(v.sha(identity.encode())+'.json');write(context_path,context)
    check('valid TEST context signature',lambda:bool(p.review(page,sources,context,page_id=identity)))
    hubs=t.read_json(root/'content/category-hubs.json')
    files.update(v.render_selected(root,{identity:page},posts,hubs,sources,files))
    for name,data in files.items():
        path=root/'dist'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    from reporting_workflow_test_support import bind
    revision=bind(root,files)
    release_args=args('release',artifact=root/'dist',candidate_sha=revision['source_commit'])
    release=sign(release_args);data=v.zip_bytes(files)
    check('A positive exact TEST artifact',lambda:v.verify_test_bundle(release,root,data,source_revision=revision)['deployment_eligible'] is False)
    determinism=equivalent_proof(root,authority,release)
    check('equivalent verification build in two fresh candidates',lambda:determinism['fresh_candidate_copies']==2)
    from reporting_provider_selftest import run as provider_cases
    provider_cases(root, release, files, output, check)
    # Reconfirm the inherited diagnostic parser defects cannot buy structured
    # approval, even with authentic TEST signatures over the exact hostile text.
    import reporting_structured as structured
    legacy_cases=[
        ('unresolved recipient','Forward suspicious emails to the scam team at phishing@hmrc.gov.uk.'),
        ('trailing foreign audience','Report a fake SHEIN site through https://www.shein.co.uk/contact-us.html for customers in Brazil.'),
        ('follow-on outcome','Report a fake SHEIN site through https://www.shein.co.uk/contact-us.html. The team will close the shop.'),
        ('Apple expectation','Close the tab, never grant remote access, and report it to reportphishing@apple.com and any loss to Report Fraud or Police Scotland on 101.')]
    for label,prose in legacy_cases:
        hostile=copy.deepcopy(page);hostile['sections']=[['Background',prose]]
        body=copy.deepcopy(context['body']);body['page_sha256']=t.digest(hostile)
        packet=t.sign(body,keys['context'],'context',p.NAMESPACE)
        check('legacy isolation authentic TEST signature '+label,
              lambda packet=packet:t.verify(packet['body'],packet['signature'],'context',p.NAMESPACE) is None)
        check('legacy isolation structured review rejects '+label,
              lambda hostile=hostile,packet=packet:p.review(hostile,sources,packet,page_id=identity),'')
        with patch.object(structured,'_raw_destinations',return_value=[]):
            check('legacy isolation independent authoring boundary '+label,
                  lambda hostile=hostile,packet=packet:p.review(hostile,sources,packet,page_id=identity),
                  'restricted action-authoring boundary')
    check('deterministic archive',lambda:v.zip_bytes(dict(reversed(list(files.items()))))==data)
    check('H TEST packet cannot verify as production',lambda:v.verify_bundle(release,root,data),'test authority')
    check('B missing release approval',lambda:v.verify_bundle({},root,data,production=False,source_revision=revision),'missing release')
    context_path.unlink()
    check('B missing context approval',lambda:v.verify_test_bundle(release,root,data,source_revision=revision),'No such file')
    write(context_path,context)
    e.packet_path(rid).unlink()
    check('B missing contract approval',lambda:v.verify_test_bundle(release,root,data,source_revision=revision),'No such file')
    write(e.packet_path(rid),contract)
    changed=dict(files);changed[v.output_path(identity)]+=b' changed'
    check('C changed artifact',lambda:v.verify_test_bundle(release,root,v.zip_bytes(changed),source_revision=revision),'deterministic page render')
    def raw(body,role,namespace):
        # Test-only signature, even when deliberately malformed negative data.
        return t.sign(body,keys[role],role,namespace)
    bad=copy.deepcopy(release['body']);bad['manifest']['files'][v.output_path(identity)]='0'*64
    bad=raw(bad,'release',v.VERSION)
    check('F authentically signed wrong manifest',lambda:v.verify_test_bundle(bad,root,data,source_revision=revision),'manifest differs')
    # The real catalog contains exactly six actions. Add a seventh only to the
    # disposable copy: valid schema/signature must not grant factual clearance.
    held_sources=copy.deepcopy(sources)
    rec=next(r for group in e.s._GROUPS for r in held_sources.get(group,[]) if r['key']=='citizens-advice')
    rec['actions']['unreviewed-copy']=copy.deepcopy(rec['actions']['consumer-advice-english'])
    held='citizens-advice:unreviewed-copy'
    held_packet=e.issue_reviewed(held_sources,held,reviewer='test-contracts',private_key=keys['contracts'])
    check('D held contract has authentic TEST endorsement',lambda:bool(e.verify_contract(held_sources,held,held_packet)))
    bad=copy.deepcopy(release['body']);bad['manifest']['pages'][0]['route_ids']=[held]
    bad=raw(bad,'release',v.VERSION)
    canon_path=root/'content/sources.json';canon_bytes=canon_path.read_bytes()
    write(canon_path,held_sources)
    check('D held contract remains independently rejected',lambda:v.verify_test_bundle(bad,root,data,source_revision=revision),'independent canon clearance')
    check('held contract cannot use reviewer UX',lambda:ux.prepare(args('contracts',route_id=held)),'independent canon clearance')
    canon_path.write_bytes(canon_bytes)
    for name,change in [('source',lambda x:x.update(title=x['title']+' changed')),
                        ('action plan',lambda x:x.update(reporting_routes=[]))]:
        modified=copy.deepcopy(page);change(modified);write(page_file,modified)
        check('stale '+name+' refuses signing',lambda:ux.issue(context_args),'')
        write(page_file,page)
    original=(root/'dist'/v.output_path(identity)).read_bytes()
    (root/'dist'/v.output_path(identity)).write_bytes(original+b' mutation')
    check('stale manifest refuses signing',lambda:ux.issue(release_args),'working candidate differs')
    (root/'dist'/v.output_path(identity)).write_bytes(original)
    wrong=args('contracts',route_id=rid,reviewer='unknown')
    check('wrong reviewer',lambda:ux.prepare(wrong),'not enrolled')
    check('wrong role signature',lambda:t.verify(contract['body'],contract['signature'],'release',v.VERSION),'unauthorized')
    check('outside page scope',lambda:ux.prepare(args('context',page=page_file,page_id='guide:outside',audience=['England'])),'outside enrolled scope')
    check('no implicit release artifact',lambda:ux.prepare(args('release')),'explicit --artifact')
    check('no implicit candidate',lambda:ux.prepare(args('contracts',route_id=rid,candidate=Path('.'))),'absolute canonical')
    wrong=copy.copy(contract_args);wrong.expected_receipt_sha256='0'*64
    check('wrong receipt digest',lambda:ux.issue(wrong),'stale or wrong expected receipt')
    check('exclusive packet output refuses overwrite',lambda:ux.export(output/'contracts.json',contract),'File exists')
    linked=output/'packet-link';linked.symlink_to(output/'contracts.json')
    check('packet output refuses symlink',lambda:ux.export(linked,contract),'absolute canonical')
    check('packet output refuses repository',lambda:ux.export(root/'packet.json',contract),'outside repositories')
    wrong=copy.copy(contract_args);wrong.key_file=root/'repo-key';wrong.key_file.write_text('NOT A KEY');wrong.key_file.chmod(0o600)
    check('repo key rejected',lambda:t.key_path(wrong.key_file),'outside every repository')
    wrong.key_file.unlink()
    check('missing key',lambda:t.key_path(root.parent/'absent'),'No such file')
    keys['context'].chmod(0o644)
    check('unsafe key permissions',lambda:t.key_path(keys['context']),'owner-only')
    keys['context'].chmod(0o600)
    sibling=root.parent/'sibling';sibling.mkdir();(sibling/'.git').write_text('gitdir: example');(sibling/'key').write_text('not key')
    check('sibling worktree key',lambda:t.key_path(sibling/'key'),'outside every repository')
    with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production'}):
        check('H TEST root cannot claim production',t.config,'pinned')
        check('production refuses TEST key path',lambda:t.key_path(keys['contracts']),'fixture/test')
    edited=copy.deepcopy(release);edited['body']['environment']='production'
    check('H editing environment invalidates packet',lambda:v.verify_test_bundle(edited,root,data,source_revision=revision),'environment/site/role')
    original_cfg=copy.deepcopy(cfg)
    cfg['roles']['release'][0]['identity']='replacement';write(authority/'trust.json',cfg)
    check('G removed reviewer',lambda:v.verify_test_bundle(release,root,data,source_revision=revision),'unauthorized')
    cfg=copy.deepcopy(original_cfg);revoked=[release['body']['decision_id']]
    cfg['revocations_sha256']=t.digest(revoked);write(authority/'trust.json',cfg);write(authority/'revoked.json',revoked)
    check('G revoked approval',lambda:v.verify_test_bundle(release,root,data,source_revision=revision),'revoked')
    write(authority/'trust.json',original_cfg);write(authority/'revoked.json',[])
    with patch.object(runtime.platform,'python_version',return_value='0.0.0'):
        check('E wrong Python',lambda:v.verify_test_bundle(release,root,data,source_revision=revision),'runtime identity mismatch')
    with patch.object(runtime.unicodedata,'unidata_version','0.0.0'):
        check('E wrong Unicode',lambda:runtime.require(),'runtime identity mismatch')
    actual_tool_version=runtime.tool_version
    for wrong_tool in ('node','npm'):
        with patch.object(runtime,'tool_version',side_effect=lambda cmd,wrong_tool=wrong_tool:'0.0.0' if cmd[0]==wrong_tool else actual_tool_version(cmd)):
            check('E wrong '+wrong_tool,lambda:runtime.require(),'runtime identity mismatch')
    import idna
    with patch.object(idna,'__version__','0.0.0'):
        check('E wrong idna',lambda:runtime.require(),'runtime identity mismatch')
    with patch.dict(os.environ,{'TZ':'Europe/London'}):
        check('E wrong locale profile',lambda:runtime.require(),'runtime identity mismatch')
    for name in ('requirements-reporting.txt','requirements-reporting.lock','package-lock.json','.python-version','templates/base.html'):
        path=root/name;before=path.read_bytes();path.write_bytes(before+b'\n')
        check('changed lock/renderer '+name,lambda:ux.issue(release_args),'')
        path.write_bytes(before)
    cli=[sys.executable,str(root/'scripts/reporting_reviewer.py'),'prepare','--candidate',str(root),'--reviewer','test-contracts','--route-id',rid]
    for label,opts in [('missing role',['--environment','test']),('missing environment',['--role','contracts']),('invalid role',['--role','invalid','--environment','test'])]:
        result=subprocess.run(cli+opts,capture_output=True,text=True)
        check(label,lambda result=result:result.returncode==2)
    check('packet excludes private key bytes',lambda:all(keys[r].read_bytes() not in t.canonical(packet) for r in keys for packet in (contract,context,release)))
    agent_result={}
    def agent_test():
        agent_result.update(encrypted_rehearsal(authority,original_cfg,contract['body']))
        return all(agent_result.values())
    if os.environ.get('BTS_TEST_AGENT_UNAVAILABLE') == '1':
        # Permission-aware partial execution: preserve a failed case and exit 1.
        # This is never an alternate green/approval path and starts no agent.
        rows.append({'name':'encrypted TEST backup recovery and isolated agent signing',
                     'ok':False,'detail':'BLOCKED: final agent execution not authorized; no agent attempted'})
    else:
        check('encrypted TEST backup recovery and isolated agent signing',agent_test)
    # Unit-test the human gate without creating any production signature/root.
    # The fake config/key lookup never reaches an OpenSSH signing invocation.
    class Terminal(io.StringIO):
        def isatty(self): return True
    prod_cfg=copy.deepcopy(original_cfg);prod_cfg['environment']='production'
    prod_body=dict(contract['body'],environment='production')
    summary={'unit_test':'confirmation only; no production signature'}
    phrase='SIGN production contracts test-contracts '+t.digest(summary)
    with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production','CI':'','GITHUB_ACTIONS':'','NETLIFY':''}), \
         patch.object(t,'config',return_value=prod_cfg), patch.object(t,'key_path',return_value=keys['contracts']), \
         patch.object(sys,'stdin',Terminal()),patch.object(sys,'stderr',Terminal()), \
         patch.object(t.subprocess,'run',side_effect=AssertionError('must never sign production')) as ssh:
        with patch('builtins.input',return_value='no'):
            check('production confirmation rejects wrong phrase',lambda:t.sign(prod_body,keys['contracts'],'contracts',e.VERSION,review_summary=summary,recheck=lambda:None),'confirmation declined')
        with patch('builtins.input',return_value=phrase):
            def stale(): raise ValueError('candidate changed after confirmation')
            check('production rechecks after confirmation',lambda:t.sign(prod_body,keys['contracts'],'contracts',e.VERSION,review_summary=summary,recheck=stale),'changed after confirmation')
        with patch.dict(os.environ,{'CI':'true'}):
            check('production CI signing guard',lambda:t.sign(prod_body,keys['contracts'],'contracts',e.VERSION),'forbidden')
        check('confirmation guard tests create no production signature',lambda:not ssh.called)
    check('test result never deployment authority',lambda:not v.verify_test_bundle(release,root,data,source_revision=revision)['deployment_eligible'])
    return {'passed':sum(r['ok'] for r in rows),'total':len(rows),'failures':[r for r in rows if not r['ok']],
            'cases':rows,'artifact_sha256':v.sha(data),'output_files':v.hashes(files),'runtime':runtime.require(),
            'agent_rehearsal':agent_result,'determinism':determinism,
            'authority':'TEST only; temporary; no deploy command or credentials'}


def main():
    if sys.argv[1:] == ['--equivalent-worker']:
        print(json.dumps(equivalent_worker()));return 0
    if sys.argv[1:] == ['--isolated-worker']:
        result=worker();print(json.dumps(result,indent=2));return int(bool(result['failures']))
    if sys.argv[1:] not in ([],['--agent-unavailable']): raise ValueError('unsupported arguments')
    with tempfile.TemporaryDirectory(prefix='bts-g1-test-') as raw:
        temp=Path(raw).resolve();root=temp/'candidate';root.mkdir();(temp/'home').mkdir()
        for name in v.INPUT_DIRS+('dist',):
            if (p.ROOT/name).exists():
                shutil.copytree(p.ROOT/name,root/name,ignore=shutil.ignore_patterns('__pycache__'))
        for name in v.INPUT_FILES:
            shutil.copyfile(p.ROOT/name,root/name)
        env={k:os.environ[k] for k in ('PATH','TZ','LC_ALL','LANG','PYTHONUTF8') if k in os.environ}
        env.update(HOME=str(temp/'home'),BTS_REVIEW_ENVIRONMENT='test',PYTHONDONTWRITEBYTECODE='1')
        if sys.argv[1:]==['--agent-unavailable']:env['BTS_TEST_AGENT_UNAVAILABLE']='1'
        result=subprocess.run([sys.executable,str(root/'scripts/reporting_preflight_selftest.py'),'--isolated-worker'],
            cwd=root,env=env,timeout=600,capture_output=True,text=True)
        sys.stdout.write(result.stdout);sys.stderr.write(result.stderr);return result.returncode


if __name__ == '__main__': raise SystemExit(main())
