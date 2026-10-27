"""G2 readback cases, called only with the preflight harness's real TEST release.

The positive record is authenticated using current TEST authority and all six
independently eligible actions. No network, production packet or deployment.
"""
import copy
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import reporting_provider as provider
import reporting_pilot as pilot
import reporting_trust as trust


def run(root, release, files, output, check):
    target={'site_id':'00000000-0000-0000-0000-000000000001',
            'team_id':'0'*24, 'project':'isolated-test-only', 'production_origin':'https://beatthescam.com'}
    revision=release['body']['manifest']['source_revision']['source_commit']; deploy='2'*24
    record=provider.prepare(root,files,release,environment='test',target=target,source_revision=revision)
    digest=trust.digest(record); observed=provider.expected_observation(record,deploy)
    captured={origin+'/'+name:files[name] for origin in ('deploy','production') for name in record['served_paths']}
    def verify(captured=captured, observed=observed, record=record, digest=digest, deploy=deploy):
        return provider.compare(record,digest,observed,captured,deploy_id=deploy)
    check('provider authentic TEST handoff and both-origin exact readback',lambda:verify()['static_readback']=='PASS')
    check('provider comparison never authorizes publication',lambda:verify()['production_acceptance']=='HOLD' and not verify()['deployment_eligible'])
    check('provider all six actions in authenticated manifest',lambda:len(record['pages'][0]['route_ids'])==6)
    name=record['pages'][0]['path']; text=files[name].decode()
    # Assert each mutation actually changes the authenticated HTML. This prevents
    # a wrong fixture substring from turning a negative into a vacuous test.
    mutations={
        'changed action link':lambda b:b.replace(b'tel:',b'tel:9',1),
        'changed bank semantics':lambda b:b.replace(b'Bank that sent your transfer',b'Bank that received your transfer',1),
        'changed qualifier':lambda b:b.replace(b'For England',b'For Brazil',1),
        'unexpected action':lambda b:b.replace(b'</body>',b'<a href="https://attacker.invalid">Report here</a></body>',1),
        'changed action method':lambda b:b.replace(b'tel:',b'https:',1),
        'stale page':lambda b:b'<html><body>Previous release</body></html>',
        'whitespace still requires exact bytes':lambda b:b+b'\n'}
    for label,mutate in mutations.items():
        changed=mutate(files[name])
        if changed==files[name]: raise AssertionError('readback mutation fixture absent: '+label)
        bad=dict(captured);bad['production/'+name]=changed
        check('provider '+label,lambda bad=bad:verify(captured=bad),'served byte mismatch')
    bad=dict(captured);bad.pop('deploy/'+name)
    check('provider missing page',lambda:verify(captured=bad),'missing or unexpected')
    bad=dict(captured);bad['production/unapproved.html']=b'<p>extra</p>'
    check('provider unexpected path',lambda:verify(captured=bad),'missing or unexpected')
    bad=dict(captured);bad['../outside']=b'x'
    check('provider traversal path',lambda:verify(captured=bad),'unsafe/noncanonical')
    bad=dict(captured);bad['production/'+name.upper()]=files[name]
    check('provider case collision',lambda:verify(captured=bad),'colliding')
    check('provider wrong retained handoff digest',lambda:verify(digest='0'*64),'handoff identity')
    tampered=copy.deepcopy(record);tampered['manifest_sha256']='0'*64
    check('provider tampered manifest',lambda:verify(record=tampered),'handoff identity')
    for field in ('manifest_sha256','canonical_archive_sha256','candidate_inputs_sha256','source_revision','deploy_id','site_id','team_id'):
        bad=copy.deepcopy(observed);bad[field]='wrong'
        check('provider wrong observed '+field,lambda bad=bad:verify(observed=bad),'observation identity')
    check('provider wrong expected deploy',lambda:verify(deploy='3'*24),'observation identity')
    for value in ('http://127.0.0.1/', 'http://169.254.169.254/', 'file:///etc/passwd',
                  'https://beatthescam.com@attacker.invalid/', 'https://attacker.invalid/'):
        bad=copy.deepcopy(observed);bad['responses']['production'][name]['url']=value
        check('provider arbitrary URL rejected '+value.split(':')[0],lambda bad=bad:verify(observed=bad),'observation identity')
    bad=copy.deepcopy(observed);bad['responses']['production'][name]['status']=302
    check('provider unexpected redirect',lambda:verify(observed=bad),'observation identity')
    bad=copy.deepcopy(record);bad['html_projection_sha256'][name]='0'*64
    check('provider projection mismatch',lambda:verify(record=bad,digest=trust.digest(bad)),'security projection mismatch')
    for project in ('../escape','a/b','example.com','x\ncommand'):
        bad=dict(target,project=project)
        check('provider unsafe project label',lambda bad=bad:provider.target_value(bad),'target identity')
    check('provider test cannot prepare production handoff',lambda:provider.prepare(root,files,release,
        environment='production',target=target,source_revision=revision),'matching handoff environment')
    # Exercise the real CLI, including exclusive output, metadata and capture I/O.
    def write(path,value):path.write_text(json.dumps(value))
    write(output/'provider-target.json',target);write(output/'provider-release.json',release)
    write(output/'provider-observation.json',observed)
    capture=output/'capture';capture.mkdir()
    for path,data in captured.items():
        dest=capture/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    cli=[sys.executable,str(root/'scripts/reporting_provider.py')]
    common=['--environment','test','--artifact',str(root/'dist'),'--packet',str(output/'provider-release.json'),
            '--target',str(output/'provider-target.json'),'--source-revision',revision]
    prepare=cli+['prepare',*common,'--output',str(output/'handoff.json')]
    result=subprocess.run(prepare,capture_output=True,text=True,timeout=120)
    check('provider prepare CLI',lambda:result.returncode==0)
    compare=cli+['compare',*common,'--handoff',str(output/'handoff.json'),'--expected-handoff-sha256',digest,
                 '--capture',str(capture),'--observation',str(output/'provider-observation.json'),'--expected-deploy-id',deploy]
    result=subprocess.run(compare,capture_output=True,text=True,timeout=120)
    check('provider compare CLI',lambda:result.returncode==0 and json.loads(result.stdout)['static_readback']=='PASS')
    result=subprocess.run(prepare,capture_output=True,text=True,timeout=120)
    check('provider CLI never overwrites handoff',lambda:result.returncode==1)
    copied=capture/'production'/name;copied.unlink();copied.symlink_to(root/'dist'/name)
    result=subprocess.run(compare,capture_output=True,text=True,timeout=120)
    check('provider capture symlink rejected',lambda:result.returncode==1)
    copied.unlink();copied.write_bytes(files[name])
    altered=copy.deepcopy(record);altered['manifest_sha256']='0'*64;write(output/'handoff.json',altered)
    result=subprocess.run(compare,capture_output=True,text=True,timeout=120)
    check('provider CLI reauthenticates handoff',lambda:result.returncode==1)
    write(output/'handoff.json',record)
    # Mutations after the expensive initial authentication/comparison must still
    # reject before emitting success. All paths belong to this disposable copy.
    real_compare=provider.compare
    for label,path,replacement in (
            ('artifact',root/'dist'/name,files[name]+b'late mutation'),
            ('capture',capture/'production'/name,files[name]+b'late mutation'),
            ('current authority',trust.store()/'trust.json',b'{}')):
        original=path.read_bytes()
        def mutate(*args,path=path,replacement=replacement,**kwargs):
            value=real_compare(*args,**kwargs);path.write_bytes(replacement);return value
        try:
            with patch.object(sys,'argv',compare[1:]),patch.object(provider,'compare',side_effect=mutate), \
                 contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                status=provider.main()
            check('provider late '+label+' mutation rejects',lambda status=status:status==1)
        finally:path.write_bytes(original)
