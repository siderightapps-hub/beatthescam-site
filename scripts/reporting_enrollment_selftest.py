#!/usr/bin/env python3
"""WP3C9H public enrollment checks; disposable TEST signatures only.

No private-key input option, key discovery, agent, network, build or deployment.
Run in the pinned runtime with no inherited SSH agent. Expected pin/fingerprints
come from the independently retained owner-public receipt, never the mirror.
This is a focused audit harness, not an enrollment or policy-activation service.
"""
import argparse
import base64
from collections import Counter
from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch

import canon
import reporting_eligibility as eligibility
import reporting_pilot as pilot
import reporting_publication as publication
import reporting_reviewer as reviewer
import reporting_runtime as runtime
import reporting_structured as structured
import reporting_trust as trust

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = {'contracts': eligibility.VERSION, 'context': publication.NAMESPACE,
           'release': pilot.VERSION}


def public_fingerprint(value):
    if not isinstance(value, str) or not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/]+={0,2}', value):
        raise ValueError('public Ed25519 representation')
    encoded = value.split(' ')[1]
    blob = base64.b64decode(encoded, validate=True)
    if (len(blob) != 51 or blob[:19] != b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20'
            or base64.b64encode(blob).decode() != encoded):
        raise ValueError('public Ed25519 wire format')
    return 'SHA256:' + base64.b64encode(hashlib.sha256(blob).digest()).decode().rstrip('=')


def audit_rows(cfg, supplied):
    """This ceremony has three distinct keys/IDs; cross-role reuse is schema-legal."""
    keys, identities = set(), set()
    if set(cfg['roles']) != set(DOMAINS) or set(supplied) != set(DOMAINS):
        raise ValueError('exact enrollment roles')
    for role, entries in cfg['roles'].items():
        if len(entries) != 1 or set(entries[0]) != {'identity', 'public_key'}:
            raise ValueError('one exact public row per role')
        row = entries[0]
        if row['identity'] != supplied[role]['identity'] or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,128}', row['identity']):
            raise ValueError('owner reviewer identity mismatch')
        if public_fingerprint(row['public_key']) != supplied[role]['fingerprint']:
            raise ValueError('owner public fingerprint mismatch')
        if row['public_key'] in keys or row['identity'] in identities:
            raise ValueError('duplicate ceremony key or identity')
        keys.add(row['public_key']); identities.add(row['identity'])
    return True


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')
    path.chmod(0o600)


@contextmanager
def authority(path, environment, pin=''):
    with patch.dict(os.environ, {'BTS_REVIEW_STORE': str(path),
                    'BTS_REVIEW_ENVIRONMENT': environment,
                    'BTS_PRODUCTION_TRUST_SHA256': pin}):
        yield


def run(args):
    if os.environ.get('SSH_AUTH_SOCK') or os.environ.get('SSH_AGENT_PID'):
        raise ValueError('refuse inherited agent; use an isolated environment')
    if not re.fullmatch('[a-f0-9]{64}', args.expected_trust_sha256):
        raise ValueError('explicit expected public trust digest required')
    measured = runtime.require(ROOT)
    receipt = trust.read_json(args.public_receipt)
    mirror = ROOT / 'deployment/review-store'
    material = pilot.tree(mirror)
    if set(material) != {'trust.json', 'baseline.json', 'revoked.json'}:
        raise ValueError('enrollment-only mirror has unexpected files')
    real = trust.read_json(mirror/'trust.json')
    if trust.digest(real) != args.expected_trust_sha256 or receipt['trust_sha256'] != args.expected_trust_sha256:
        raise ValueError('independent public pin mismatch')
    rows = []; artifacts = {}; sign_events = []

    def check(group, name, operation):
        try:
            result = operation()
            if result is False: raise AssertionError('false result')
            rows.append({'group': group, 'name': name, 'ok': True})
        except Exception as exc:
            rows.append({'group': group, 'name': name, 'ok': False,
                         'detail': type(exc).__name__ + ': ' + str(exc)})

    def rejects(operation, reason):
        try: operation()
        except (ValueError, OSError) as exc:
            if reason not in str(exc): raise AssertionError('wrong rejection: ' + str(exc))
            return True
        raise AssertionError('invalid operation accepted')

    with tempfile.TemporaryDirectory(prefix='bts-enrollment-test-') as tmp:
        temp = Path(tmp).resolve(); production = temp/'public-production'; production.mkdir(mode=0o700)
        for name, data in material.items():
            (production/name).write_bytes(data); (production/name).chmod(0o600)
        with authority(production, 'production', args.expected_trust_sha256):
            check('enrollment', 'real public root parsed with retained pin', lambda: trust.config() == real)
            check('public_keys', 'owner fingerprints and distinct role rows', lambda: audit_rows(real, receipt['public_reviewers']))
            check('enrollment', 'empty scope and unestablished baseline', lambda: real['pilot_page_ids'] == [] and pilot.baseline(real) == {})
            check('enrollment', 'empty revocations bound', lambda: trust.digest(trust.read_json(production/'revoked.json')) == real['revocations_sha256'])
            for role in DOMAINS:
                row = real['roles'][role][0]
                pub = temp/(role+'.pub'); pub.write_text(row['public_key']+'\n'); pub.chmod(0o600)
                def openssh_fingerprint(pub=pub, role=role):
                    result = subprocess.run(['/usr/bin/ssh-keygen', '-l', '-E', 'sha256', '-f', str(pub)], capture_output=True, text=True, check=True)
                    return result.stdout.split()[1] == receipt['public_reviewers'][role]['fingerprint']
                check('public_keys', role+' OpenSSH fingerprint matches owner', openssh_fingerprint)
                check('recognition', role+' principal recognized only in its explicit row', lambda role=role,row=row: [r for r in DOMAINS if any(x['identity']==row['identity'] for x in trust.config()['roles'][r])] == [role])
            sources = canon.load_canon()
            _, posts, hubs = pilot.load_pages(ROOT, [])
            public = [('guide:'+p['slug'], p) for p in posts if not p.get('consolidated_into')]+[('hub:'+k,v) for k,v in hubs.items()]
            check('publication_hold', 'R6B2 model pin preserves six actual eligible IDs', lambda: len(eligibility.REVIEWED_CONTRACT_IDS) == 6 and set(eligibility.contract_production_eligible_ids(sources)) == set(eligibility.REVIEWED_CONTRACT_IDS))
            held = set(structured.catalog_from_canon(sources).actions)-eligibility.REVIEWED_CONTRACT_IDS
            check('publication_hold', 'every other catalog contract remains held', lambda: all(not eligibility.is_contract_production_eligible(sources,r) for r in held))
            check('publication_hold', 'no production endorsements', lambda: eligibility.publication_endorsed_ids(sources) == ())
            check('publication_hold', '0 of 204 public pages eligible', lambda: len(public)==204 and not any(publication.is_page_publication_eligible(p,sources,page_id=i) for i,p in public))
            check('publication_hold', 'empty enrollment cannot release output', lambda: rejects(lambda:pilot.candidate(ROOT,pilot.tree(ROOT/'dist')), 'pilot must enroll one to seven'))
            with patch.dict(os.environ, {'COMMIT_REF': ''}):
                check('publication_hold', 'mirror without exact source revision holds verifier', lambda: rejects(lambda:pilot.netlify_verify(ROOT), 'exact nonzero Git commit SHA'))
            for role in DOMAINS:
                options = argparse.Namespace(environment='production',role=role,candidate=ROOT,
                    reviewer=real['roles'][role][0]['identity'],route_id=None,page=None,
                    page_id=None,artifact=None,audience=None,allow_empty=False,candidate_sha=None)
                if role=='contracts': options.route_id='citizens-advice:consumer-advice-english'
                elif role=='context':
                    options.page=ROOT/'content/posts.json';options.page_id=public[0][0];options.audience=['England','Wales']
                else: options.artifact=ROOT/'dist'
                with patch.object(trust,'sign',side_effect=AssertionError('signing forbidden')), patch.object(trust,'key_path',side_effect=AssertionError('key access forbidden')):
                    if role=='contracts':
                        prepared = reviewer.prepare(options); artifacts['unsigned_contract_receipt']=prepared
                        check('preflight', 'contracts prepare exposes exact identity without key access', lambda: prepared['reviewer']==options.reviewer and prepared['environment']=='production' and prepared['role']=='contracts' and prepared['public_key_fingerprint']==receipt['public_reviewers']['contracts']['fingerprint'] and prepared['candidate_inputs_sha256']==pilot.inputs(ROOT) and prepared['trust_sha256']==args.expected_trust_sha256)
                    else:
                        why='page outside enrolled scope' if role=='context' else 'exact nonzero Git commit SHA'
                        check('preflight', role+' prepare rejects unmet scope/revision prerequisites', lambda options=options,why=why: rejects(lambda:reviewer.prepare(options),why))
                    options.reviewer='unknown-reviewer'
                    check('unknown_reviewer',role+' unknown reviewer prepare rejects',lambda options=options: rejects(lambda:reviewer.prepare(options),'reviewer is not enrolled'))
            artifacts['dry_run']=reviewer.dry_run()
        with authority(production, 'test'):
            check('environment', 'production public root rejects TEST environment', lambda: rejects(trust.config, 'schema/environment/site'))
        with authority(production, 'production', ''):
            check('environment', 'production root without external pin rejects', lambda: rejects(trust.config, 'externally pinned'))
        with authority(production, 'production', '0'*64):
            check('enrollment', 'wrong independent pin rejects', lambda: rejects(trust.config,'externally pinned'))
        with authority(mirror, 'production', args.expected_trust_sha256):
            check('enrollment','repository cannot shadow external store',lambda:rejects(trust.config,'outside the repository'))

        # Malformed roots are isolated public copies; pins deliberately match the
        # mutated copies so schema tests reach schema validation, not the pin gate.
        sandbox = temp/'schema-test';sandbox.mkdir(mode=0o700)
        write_json(sandbox/'revoked.json',[]);write_json(sandbox/'baseline.json',{})
        for name, mutate in [
            ('duplicate role identity',lambda c:c['roles']['contracts'].append(copy.deepcopy(c['roles']['contracts'][0]))),
            ('wildcard principal',lambda c:c['roles']['context'][0].update(identity='*')),
            ('whitespace principal',lambda c:c['roles']['context'][0].update(identity='two names')),
            ('wildcard role',lambda c:c['roles'].update({'*':c['roles']['context']})),
            ('wildcard environment',lambda c:c.update(environment='*')),
            ('wrong site',lambda c:c.update(site='elsewhere.example')),
            ('unknown schema',lambda c:c.update(version='bts-trust/v2')),
            ('unknown status field',lambda c:c['roles']['context'][0].update(status='active')),
            ('key options',lambda c:c['roles']['context'][0].update(public_key='restrict '+c['roles']['context'][0]['public_key'])),
        ]:
            cfg=copy.deepcopy(real);mutate(cfg);write_json(sandbox/'trust.json',cfg)
            with authority(sandbox,'production',trust.digest(cfg)):
                check('schema',name+' rejected',lambda:rejects(trust.config,''))
        (sandbox/'trust.json').write_text('{"version":"bts-trust/v1","version":"bts-trust/v1"}')
        check('schema','duplicate JSON field rejects',lambda:rejects(lambda:trust.read_json(sandbox/'trust.json'),'duplicate JSON field'))
        for bad in ['ssh-ed25519 AAAA','ssh-ed25519 AAAAC3NzaC1yc2EAAAAA',real['roles']['context'][0]['public_key']+' comment','ssh-ed25519 !!!!']:
            check('public_keys','malformed/comment-bearing public material rejected',lambda bad=bad:rejects(lambda:public_fingerprint(bad),'public Ed25519'))
        bad=copy.deepcopy(real);bad['roles']['context'][0]['public_key']=bad['roles']['contracts'][0]['public_key']
        check('public_keys','role key substitution rejected against owner fingerprints',lambda:rejects(lambda:audit_rows(bad,receipt['public_reviewers']),'fingerprint mismatch'))

        # Fresh explicit TEST paths only. No agent is started or consulted.
        test_store=temp/'test-authority';test_store.mkdir(mode=0o700)
        keys=[]
        for n in range(2):
            key=temp/('disposable-test-key-'+str(n))
            subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True,capture_output=True)
            key.chmod(0o600);keys.append(key)
        pubs=[' '.join(k.with_suffix('.pub').read_text().split()[:2]) for k in keys]
        cfg={'version':'bts-trust/v1','environment':'test','site':trust.SITE,
             'roles':{role:[{'identity':'test-enrollment-reviewer','public_key':pubs[0]}] for role in DOMAINS},
             'pilot_page_ids':[],'baseline_sha256':trust.digest({}),'revocations_sha256':trust.digest([])}
        write_json(test_store/'trust.json',cfg);write_json(test_store/'revoked.json',[]);write_json(test_store/'baseline.json',{})
        def test_sign(body,role):
            if body['environment']!='test' or trust.environment()!='test' or keys[0].parent!=temp:
                raise AssertionError('only explicit disposable TEST signing is allowed')
            sign_events.append({'role':role,'environment':'test','namespace':DOMAINS[role]+':test'})
            return trust.sign(body,keys[0],role,DOMAINS[role])
        def verify(packet,role,namespace=None):
            return trust.verify(packet['body'],packet['signature'],role,namespace or DOMAINS[role])
        with authority(test_store,'test'):
            packets={role:test_sign(dict(trust.header(domain),reviewer='test-enrollment-reviewer',probe='WP3C9H TEST only'),role) for role,domain in DOMAINS.items()}
            for role,packet in packets.items():
                check('role',role+' authentic TEST positive',lambda role=role,packet=packet:verify(packet,role))
                for other in DOMAINS:
                    if other!=role:
                        check('role',role+' cannot replay as '+other+' with same key/principal',lambda packet=packet,other=other:rejects(lambda:verify(packet,other),'signature authentication'))
                mutated=copy.deepcopy(packet);mutated['body']['reviewer']='unknown-reviewer'
                check('unknown_reviewer',role+' unknown principal rejected',lambda mutated=mutated,role=role:rejects(lambda:verify(mutated,role),'unauthorized signer'))
                revoked=[packet['body']['decision_id']];changed=copy.deepcopy(cfg);changed['revocations_sha256']=trust.digest(revoked)
                write_json(test_store/'revoked.json',revoked);write_json(test_store/'trust.json',changed)
                check('revocation',role+' revoked decision rejected',lambda packet=packet,role=role:rejects(lambda:verify(packet,role),'approval revoked'))
                write_json(test_store/'trust.json',cfg);write_json(test_store/'revoked.json',[])
                check('revocation',role+' active control restored',lambda packet=packet,role=role:verify(packet,role))
                changed=copy.deepcopy(cfg);changed['roles'][role][0]['public_key']=pubs[1];write_json(test_store/'trust.json',changed)
                check('key_replacement',role+' replacement key rejects old signature',lambda packet=packet,role=role:rejects(lambda:verify(packet,role),'signature authentication'))
                changed['roles'][role][0]['identity']='test-replacement-reviewer';write_json(test_store/'trust.json',changed)
                check('revocation',role+' removed reviewer rejected',lambda packet=packet,role=role:rejects(lambda:verify(packet,role),'unauthorized signer'))
                write_json(test_store/'trust.json',cfg)
                mutated=copy.deepcopy(packet);mutated['body']['environment']='production'
                check('environment',role+' production metadata under TEST root rejected',lambda mutated=mutated,role=role:rejects(lambda:verify(mutated,role),'environment/site/role mismatch'))
                sig=temp/(role+'.sig');sig.write_text(packet['signature'])
                def namespace_reject(packet=packet,role=role,sig=sig):
                    result=subprocess.run(['/usr/bin/ssh-keygen','-Y','check-novalidate','-n',DOMAINS[role]+':production','-s',str(sig)],input=trust.canonical(packet['body']),capture_output=True)
                    return result.returncode!=0
                check('environment',role+' TEST signature rejects production namespace',namespace_reject)
            # Authentic TEST signature over a seventh contract still cannot buy clearance.
            seventh=copy.deepcopy(sources)
            record=next(r for g in structured._GROUPS for r in seventh.get(g,[]) if r['key']=='citizens-advice')
            record['actions']['unreviewed-copy']=copy.deepcopy(record['actions']['consumer-advice-english'])
            rid='citizens-advice:unreviewed-copy'
            endorsement=test_sign(dict(trust.header(eligibility.VERSION),reviewer='test-enrollment-reviewer',claims=eligibility.claims(seventh,rid)),'contracts')
            check('publication_hold','seventh contract TEST endorsement authentic',lambda:bool(eligibility.verify_contract(seventh,rid,endorsement)))
            check('publication_hold','authentic endorsement cannot clear seventh contract',lambda:rejects(lambda:eligibility.verify_contract_eligibility(seventh,rid),'independent canon clearance'))
            write_json(test_store/'revoked.json',['1'*32])
            check('revocation','unbound revocation file rejects intact signature',lambda:rejects(lambda:verify(packets['contracts'],'contracts'),'revocation state invalid'))
            write_json(test_store/'revoked.json',[])
            # Use real public principal labels with entirely disposable TEST
            # authority. Identical signed bytes pass the TEST key and fail the
            # real public key, isolating key substitution from metadata edits.
            named=copy.deepcopy(cfg)
            for role in DOMAINS:
                named['roles'][role][0]['identity']=real['roles'][role][0]['identity']
            write_json(test_store/'trust.json',named)
            for role in DOMAINS:
                packet=test_sign(dict(trust.header(DOMAINS[role]),reviewer=real['roles'][role][0]['identity'],probe='disposable TEST principal probe'),role)
                check('public_keys',role+' named TEST control authenticates',lambda packet=packet,role=role:verify(packet,role))
                sig=temp/('named-'+role+'.sig');sig.write_text(packet['signature'])
                signers=temp/('real-public-'+role)
                signers.write_text(real['roles'][role][0]['identity']+' '+real['roles'][role][0]['public_key']+'\n')
                def real_public_reject(packet=packet,role=role,sig=sig,signers=signers):
                    result=subprocess.run(['/usr/bin/ssh-keygen','-Y','verify','-f',str(signers),'-I',real['roles'][role][0]['identity'],'-n',DOMAINS[role]+':test','-s',str(sig)],input=trust.canonical(packet['body']),capture_output=True)
                    return result.returncode!=0
                check('public_keys',role+' real public key rejects identical TEST-key signature',real_public_reject)
                with authority(production,'production',args.expected_trust_sha256):
                    check('environment',role+' real reviewer label with TEST body/namespace rejects',lambda packet=packet,role=role:rejects(lambda:verify(packet,role),'environment/site/role mismatch'))
            write_json(test_store/'trust.json',cfg)
        with authority(test_store,'production'):
            check('environment','TEST root without production pin rejected',lambda:rejects(trust.config,'externally pinned'))
        with authority(test_store,'production',trust.digest(cfg)):
            check('environment','pin alone cannot promote TEST root',lambda:rejects(trust.config,'schema/environment/site'))
        simulated=copy.deepcopy(cfg);simulated['environment']='production';write_json(sandbox/'trust.json',simulated)
        for role,packet in packets.items():
            with authority(sandbox,'production',trust.digest(simulated)):
                check('environment',role+' TEST body rejects simulated production metadata',lambda packet=packet,role=role:rejects(lambda:verify(packet,role),'environment/site/role mismatch'))
                changed=copy.deepcopy(packet);changed['body']['environment']='production'
                check('environment',role+' edited TEST body cannot authenticate as production',lambda changed=changed,role=role:rejects(lambda:verify(changed,role),'signature authentication'))
            with authority(production,'production',args.expected_trust_sha256):
                check('environment',role+' TEST packet rejected by real root',lambda packet=packet,role=role:rejects(lambda:verify(packet,role),'environment/site/role mismatch'))
                changed=copy.deepcopy(packet);changed['body']['environment']='production';changed['body']['reviewer']=real['roles'][role][0]['identity']
                check('environment',role+' TEST key cannot impersonate real production reviewer',lambda changed=changed,role=role:rejects(lambda:verify(changed,role),'signature authentication'))
        if args.external_store:
            with authority(args.external_store,'production',args.expected_trust_sha256):
                check('recognition','persistent external public root recognized',lambda:trust.config()==real and pilot.baseline(real)=={})
                check('recognition','persistent external public bytes equal mirror',lambda:pilot.tree(args.external_store)==material)
    counts=Counter(r['group'] for r in rows);passed=Counter(r['group'] for r in rows if r['ok'])
    return {'version':'wp3c9h-enrollment-tests/v1','pass':sum(r['ok'] for r in rows),'total':len(rows),
            'groups':{g:{'pass':passed[g],'total':n} for g,n in sorted(counts.items())},
            'rows':rows,'runtime':measured,'trust_sha256':args.expected_trust_sha256,
            'test_signing_events':sign_events,'production_signatures_created':0,
            'disposable_directory_removed':not temp.exists(),'artifacts':artifacts}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-trust-sha256',required=True)
    parser.add_argument('--public-receipt',type=Path,required=True)
    parser.add_argument('--external-store',type=Path)
    args=parser.parse_args()
    result=run(args)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['pass']==result['total'] else 1)
