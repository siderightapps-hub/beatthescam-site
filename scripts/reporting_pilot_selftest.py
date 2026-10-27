#!/usr/bin/env python3
"""Offline WP3C9B3 hostile signed-input and exact-artifact regressions.

All keys, roots and signatures are disposable TEST-only fixtures. No production secret, network, model, build(), dist write or deploy.
"""
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

import canon
import reporting_trust as t
import reporting_eligibility as e
import reporting_publication as p
import reporting_pilot as v
import reporting_structured as s
from reporting_structured_selftest import fixture_canon, fixture_page


def rejects(fn, reason=None):
    try: fn()
    except (ValueError,OSError,KeyError,TypeError,canon.CanonError) as exc:
        return reason is None or reason in str(exc)
    return False


def run():
    # Grammar fixtures stay in TEST. The G1 harness and separation suite
    # exercise the real, unpatched six-contract baseline independently.
    return _run()


def _run():
    rows=[]
    def review_test(page, source, packet, **kw):
        e.require_actions(source, page.get("reporting_routes"))
        return p.review(page, source, packet, **kw)
    def verify_test(packet, root, data):
        return v.verify_bundle(packet, root, data, production=False,source_revision=revision)
    def check(group,name,fn):
        try: ok=bool(fn()); detail='' if ok else 'assertion false'
        except Exception as exc: ok=False; detail=type(exc).__name__+': '+str(exc)
        rows.append({'group':group,'name':name,'ok':ok,'detail':detail})
    def write(path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='bts-pilot-test-') as raw:
        tmp=Path(raw).resolve(); root=tmp/'candidate'; root.mkdir(); store=tmp/'authority';store.mkdir(mode=0o700)
        keys={}
        for role in t.ROLES:
            key=tmp/('fake-'+role)
            subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
            keys[role]=key
        ids=['guide:pilot-'+word for word in ('one','two','three','four','five','six')]+['hub:email']
        cfg={'version':'bts-trust/v1','environment':'test','site':t.SITE,
            'roles':{r:[{'identity':'fixture-'+r,'public_key':' '.join(k.with_suffix('.pub').read_text().split()[:2])}] for r,k in keys.items()},
            'pilot_page_ids':ids,'baseline_sha256':'0'*64,'revocations_sha256':t.digest([])}
        def policy():
            write(store/'trust.json',cfg)
        write(store/'revoked.json',[])
        with patch.dict(os.environ,{'BTS_REVIEW_STORE':str(store),'BTS_REVIEW_ENVIRONMENT':'test','BTS_PRODUCTION_TRUST_SHA256':'',
                                  'CI':'','GITHUB_ACTIONS':'','NETLIFY':''}):
            policy()
            c=fixture_canon(); cat=s.catalog_from_canon(c); rid='fixture-service:web'
            # Independent signing path can deliberately sign otherwise-invalid
            # bodies; rejection must come from the actual verifier, not issuer.
            def sign(body,role,namespace,environment='test'):
                if environment != 'test': raise ValueError('fixtures only sign TEST namespaces')
                path=tmp/'raw-decision';path.write_bytes(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())
                sig=path.with_suffix('.sig')
                if sig.exists():sig.unlink()
                subprocess.run(['ssh-keygen','-Y','sign','-f',str(keys[role]),'-n',namespace+':'+environment,str(path)],capture_output=True,check=True)
                return {'body':copy.deepcopy(body),'signature':sig.read_text()}
            check('eligibility','implemented template alone unavailable',lambda: e.eligible_ids(c)==())
            check('eligibility','fixture without evidence rejected',lambda: rejects(lambda:e.verify_contract(c,rid)))
            contract=e.issue_reviewed(c,rid,reviewer='fixture-contracts',private_key=keys['contracts'])
            write(e.packet_path(rid),contract)
            check('eligibility','complete reviewed contract eligible',lambda: e.eligible_ids(c)==(rid,))
            mutations={
                'missing owner':lambda r:r.pop('owner_id'),
                'missing purpose':lambda r:r['actions']['web'].pop('purpose'),
                'missing method':lambda r:r['actions']['web']['instruction'].pop('template_id'),
                'missing destination':lambda r:r.pop('report_url'),
                'missing jurisdiction':lambda r:r['actions']['web'].pop('jurisdictions'),
                'missing limitations':lambda r:r['actions']['web'].pop('limitation_ids'),
                'missing conditions':lambda r:r['actions']['web'].pop('condition_ids'),
                'unresolved evidence':lambda r:r.pop('source_url'),
                'undated evidence':lambda r:r.pop('checked_on'),
                'unsupported eligibility':lambda r:r['actions']['web']['condition_ids'].append('minor'),
                'withdrawn action':lambda r:r['actions']['web'].update(status='withdrawn'),
                'editor trusted flag':lambda r:r['actions']['web'].update(trusted=True)}
            for name,mutate in mutations.items():
                bad=copy.deepcopy(c);mutate(bad['verified_org_contacts'][-1])
                check('eligibility',name,lambda bad=bad:rejects(lambda:e.require_actions(bad,[rid])))
            bad=copy.deepcopy(c);other=copy.deepcopy(bad['verified_org_contacts'][-1]);other.update(key='other',owner_id='other',brand='Other');bad['verified_org_contacts'].append(other)
            check('eligibility','unsupported shared endpoint',lambda:rejects(lambda:e.require_actions(bad,[rid])))
            body=copy.deepcopy(contract['body']);body['claims']['evidence_state']='unresolved'
            check('eligibility','authentic unresolved evidence rejected',lambda:rejects(lambda:e.verify_contract(c,rid,sign(body,'contracts',e.VERSION))))
            check('eligibility','context role cannot approve contract',lambda:rejects(lambda:e.verify_contract(c,rid,sign(contract['body'],'context',e.VERSION)),'signature'))
            # Complete destination-free action retains its exact closed role.
            from reporting_structured_selftest import action
            bank=copy.deepcopy(c); record=bank['verified_org_contacts'][-1]
            record.update(key='own-bank',owner_id='own-bank',brand='Your own bank',name='Your own bank')
            for field in s._DEST_FIELDS: record.pop(field, None)
            record['actions']={'paid':action(action_type='contact',purpose='payment-recovery',mode='support',
                condition_ids=['suspected-authorised-bank-transfer-to-fraudster','banking-device-safe'], eligibility_ids=['sender-own-account'],
                instruction={'kind':'reader-held-channel','role':'own-bank','method_id':'existing-bank-app','recipient_relation':'sending-bank-of-affected-transfer'},
                limitation_ids=['no-money-recovery-guarantee'])}
            bank_id='own-bank:paid'
            bank_packet=e.issue_reviewed(bank,bank_id,reviewer='fixture-contracts',private_key=keys['contracts'])
            check('eligibility','destination-free exact reviewed contract',lambda:bool(e.verify_contract(bank,bank_id,bank_packet)))
            bank_bad=copy.deepcopy(bank)
            record=next(r for g in s._GROUPS for r in bank_bad.get(g,[]) if r['key']=='own-bank')
            record['actions'][bank_id.split(':')[1]]['instruction']['method_id']='caller-supplied'
            check('eligibility','destination-free method changed',lambda:rejects(lambda:e.verify_contract(bank_bad,bank_id,bank_packet)))
            # Exact seven-surface fixture: six guides and one real hub render.
            posts=[]
            for identity in ids[:-1]:
                page=fixture_page();page['slug']=identity.split(':')[1];posts.append(page)
            hub={k:v for k,v in fixture_page().items() if k in ('title','description','sections','faq','reporting_routes')};hub['intro']='Check safely.'
            hubs={'email':hub}
            for filename,value in [('posts.json',posts),('category-hubs.json',hubs),('sources.json',c)]:write(root/'content'/filename,value)
            for filename in ('site.json','affiliates.json'):
                write(root/'content'/filename,json.loads((p.ROOT/'content'/filename).read_text()))
            files={'index.html':b'Frozen non-pilot home','assets/styles.css':b'/* frozen css */','assets/app.js':b'/* frozen js */'}
            base=v.hashes(files);write(store/'baseline.json',base);cfg['baseline_sha256']=t.digest(base);policy()
            selected={**{'guide:'+page['slug']:page for page in posts},'hub:email':hub}
            packets={}
            for identity,page in selected.items():
                packet=p.issue_reviewed(page,c,page_id=identity,private_key=keys['context'],reviewer='fixture-context',audience=list(s._NATIONS[:4]))
                packets[identity]=packet;write(store/'packets'/(v.sha(identity.encode())+'.json'),packet)
            files.update(v.render_selected(root,selected,posts,hubs,c,files))
            import shutil
            shutil.copytree(store,root/'deployment/review-store')
            from reporting_workflow_test_support import bind
            revision=bind(root,files)
            manifest=v.candidate(root,files,source_revision=revision)
            release=sign(dict(t.header(v.VERSION),reviewer='fixture-release',manifest=manifest),'release',v.VERSION)
            data=v.zip_bytes(files)
            check('output','exact approved seven-surface artifact',lambda: verify_test(release,root,data)['deployment_eligible'] is False)
            # A historical authentic release cannot survive current scope shrink.
            original_ids = list(cfg['pilot_page_ids'])
            for label, scope in [('empty', []), ('removed page', original_ids[1:])]:
                cfg['pilot_page_ids'] = scope; policy()
                check('current-scope',label+' release record remains authentic',
                    lambda:t.verify(release['body'],release['signature'],'release',v.VERSION) is None)
                check('current-scope',label+' release consumption rejects',
                    lambda:rejects(lambda:verify_test(release,root,data)))
            cfg['pilot_page_ids'] = original_ids; policy()
            check('current-scope','unchanged release works after exact scope restoration',
                lambda:verify_test(release,root,data)['deployment_eligible'] is False)
            check('output','container determinism',lambda:v.zip_bytes(dict(reversed(list(files.items()))))==data)
            check('output','full guide and hub outputs represented',lambda:len(manifest['pages'])==7 and set(files)>=set(v.output_path(i) for i in ids))
            for name,contents in files.items():
                target=root/'dist'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(contents)
            write(store/'release.json',release)
            check('deployment-hook','Netlify refuses TEST approval material',lambda:rejects(lambda:v.netlify_verify(root),'production'))
            with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production','BTS_PRODUCTION_TRUST_SHA256':''}):
                check('deployment-hook','missing external pin holds deployment',lambda:rejects(lambda:v.netlify_verify(root),'pinned'))
            with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'test'}):
                check('deployment-hook','test mode holds Netlify',lambda:rejects(lambda:v.netlify_verify(root),'production'))
            check('deployment-hook','missing detached release holds verification',
                  lambda:rejects(lambda:verify_test({},root,data),'missing release signature'))
            # Cache exact good render bytes only for mutation checks; actual full
            # renderer above is independent of the manifest's own claimed hashes.
            renders={v.output_path(i):files[v.output_path(i)] for i in ids}
            with patch.object(v,'render_selected',return_value=renders):
                page_path=v.output_path(ids[0])
                cases={
                    'one byte mutation':lambda x:x.update({page_path:x[page_path]+b' '}),
                    'action destination mutation':lambda x:x.update({page_path:x[page_path].replace(b'routes.example',b'attacker.example')}),
                    'action wording mutation':lambda x:x.update({page_path:x[page_path].replace(b'Report the suspicious',b'Submit the suspicious')}),
                    'extra action block':lambda x:x.update({page_path:x[page_path]+b'<p>Call the attacker.</p>'}),
                    'missing page':lambda x:x.pop(page_path),
                    'replaced page':lambda x:x.update({page_path:b'replacement'}),
                    'unexpected eighth page':lambda x:x.update({'guides/eighth/index.html':b'extra action'}),
                    'stale asset':lambda x:x.update({'assets/previous.js':b'stale'}),
                    'missing asset':lambda x:x.pop('assets/app.js'),
                    'changed nonpilot page':lambda x:x.update({'index.html':b'changed'}),
                    'metadata is not excluded':lambda x:x.update({page_path:x[page_path].replace(b'<head>',b'<head><!-- changed metadata -->')})}
                for name,change in cases.items():
                    changed=copy.deepcopy(files);change(changed)
                    check('output',name,lambda changed=changed:rejects(lambda:verify_test(release,root,v.zip_bytes(changed))))
                bad=copy.deepcopy(release);bad['body']['manifest']['files'][page_path]='0'*64
                check('output','manifest tampering',lambda:rejects(lambda:verify_test(bad,root,data),'signature'))
                bad=copy.deepcopy(release['body']);bad['manifest']['files'][page_path]='0'*64
                check('output','genuinely signed wrong manifest',lambda:rejects(lambda:verify_test(sign(bad,'release',v.VERSION),root,data),'manifest differs'))
                bad=copy.deepcopy(release['body']);bad['expires_at']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
                check('output','stale release',lambda:rejects(lambda:verify_test(sign(bad,'release',v.VERSION),root,data),'stale'))
                # Source/action/canon changes after review cannot re-use packets.
                original=(root/'content/posts.json').read_bytes()
                for name,change in [('prose',lambda x:x[0]['sections'][0].__setitem__(1,'Speak to your bank now.')),
                                    ('action plan',lambda x:x[0].__setitem__('reporting_routes',[])),
                                    ('title whitespace',lambda x:x[0].__setitem__('title',x[0]['title']+' ')),
                                    ('eighth source',lambda x:x.append(dict(x[0],slug='eighth')))]:
                    changed=copy.deepcopy(posts);change(changed);write(root/'content/posts.json',changed)
                    check('toctou',name,lambda:rejects(lambda:verify_test(release,root,data)))
                    (root/'content/posts.json').write_bytes(original)
                for name,change in [('destination',lambda x:x.update(report_url='https://routes.example/other')),
                                    ('owner',lambda x:x.update(brand='Changed owner')),
                                    ('purpose',lambda x:x['actions']['web'].update(purpose='police-report')),
                                    ('jurisdiction',lambda x:x['actions']['web'].update(jurisdictions=['England'])),
                                    ('eligibility',lambda x:x['actions']['web'].update(condition_ids=[])),
                                    ('qualifier',lambda x:x['actions']['web'].update(limitation_ids=['not-emergency']))]:
                    changed=copy.deepcopy(c);change(changed['verified_org_contacts'][-1]);write(root/'content/sources.json',changed)
                    check('canon-invalidation',name,lambda:rejects(lambda:verify_test(release,root,data)))
                    write(root/'content/sources.json',c)
            identity=ids[0];page=selected[identity];good=packets[identity]
            sigcases={
                'wrong page':lambda b:b.update(page_id='guide:elsewhere'),
                'wrong content':lambda b:b.update(page_sha256='0'*64),
                'wrong action plan':lambda b:b['action_selection'].update(route_ids=[]),
                'wrong schema':lambda b:b.update(version='old'),
                'wrong site':lambda b:b.update(site='other.example'),
                'unauthorized reviewer':lambda b:b.update(reviewer='generator'),
                'wrong environment':lambda b:b.update(environment='production'),
                'stale':lambda b:b.update(expires_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())}
            for name,change in sigcases.items():
                body=copy.deepcopy(good['body']);change(body);bad=sign(body,'context',p.NAMESPACE)
                check('signing',name,lambda bad=bad:rejects(lambda:review_test(page,c,bad,page_id=identity)))
            for name,bad in [('missing',{}),('bad',dict(good,signature='bad')),('signature missing',{'body':good['body']})]:
                check('signing',name,lambda bad=bad:rejects(lambda:review_test(page,c,bad,page_id=identity)))
            check('signing','valid page packet',lambda:bool(review_test(page,c,good,page_id=identity)))
            revoked=[good['body']['decision_id']]
            write(store/'revoked.json',revoked);cfg['revocations_sha256']=t.digest(revoked);policy()
            check('signing','revoked decision rejected',lambda:rejects(lambda:review_test(page,c,good,page_id=identity),'revoked'))
            write(store/'revoked.json',[])
            check('signing','rollback of public revocations rejected',lambda:rejects(lambda:review_test(page,c,good,page_id=identity),'revoked'))
            cfg['revocations_sha256']=t.digest([]);policy()
            testbody=copy.deepcopy(good['body']);testbody['environment']='test'
            testpacket=sign(testbody,'context',p.NAMESPACE,'test')
            with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production','CI':'true'}):
                check('signing','test signature never production',lambda:rejects(lambda:p.review(page,c,testpacket,page_id=identity),'pinned'))
                check('signing','automated TEST trust cannot invoke production signer',lambda:rejects(lambda:t.sign(good['body'],keys['context'],'context',p.NAMESPACE),'pinned'))
            # Host/environment controls cannot be supplied by article data.
            for field,value in [('hero','Speak to your bank now.'),('category','call-your-bank'),('title','Report using the source above.')]:
                badpage=copy.deepcopy(page);badpage[field]=value;body=copy.deepcopy(good['body']);body['page_sha256']=s.digest(badpage)
                check('boundary',field,lambda badpage=badpage,body=body:rejects(lambda:review_test(badpage,c,sign(body,'context',p.NAMESPACE),page_id=identity)))
            (store/'contracts'/e.packet_path(rid).name).unlink()
            check('eligibility','authentic page cannot waive missing contract review',lambda:rejects(lambda:review_test(page,c,good,page_id=identity)))
            write(e.packet_path(rid),contract)
            # Test root + namespace cannot be offered to the protected command.
            cfg['environment']='test';policy()
            with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'test'}):
                check('signing','test root cannot deploy',lambda:rejects(lambda:v.verify_bundle(release,root,data),'test authority'))
                check('eligibility','test inventory never production endorsed',lambda:e.inventory(c)['publication_endorsed_contracts']==[])
            with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production','BTS_PRODUCTION_TRUST_SHA256':t.digest(cfg)}):
                check('signing','test root rejected in production mode',lambda:rejects(t.config,'environment'))
            with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production','BTS_PRODUCTION_TRUST_SHA256':'0'*64}):
                check('signing','repository-selected trust root not accepted',lambda:rejects(t.config,'pinned'))
            # Paths are tested before extraction (the verifier never extracts).
            for name in ('../outside','/absolute','a/../b','a//b','a\\b','a/%2e%2e/b','a/./b','C:/x'):
                check('paths',name,lambda name=name:rejects(lambda:v.zip_bytes({name:b'x'})))
            check('paths','case-fold collision',lambda:rejects(lambda:v.zip_bytes({'A':b'a','a':b'b'})))
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,'w') as z:
                info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=0o120777<<16;z.writestr(info,b'../../outside')
            check('paths','archive symlink',lambda:rejects(lambda:v.zip_files(buf.getvalue())))
            artifacts=tmp/'artifacts';artifacts.mkdir();(artifacts/'link').symlink_to(root/'content/posts.json')
            check('paths','filesystem symlink',lambda:rejects(lambda:v.tree(artifacts)))
            (artifacts/'link').unlink();os.link(root/'content/posts.json',artifacts/'hardlink')
            check('paths','filesystem hardlink',lambda:rejects(lambda:v.tree(artifacts)))
            (artifacts/'hardlink').unlink()
            check('containment','production canon remains unsigned for publication',lambda:not e.eligible_ids(canon.load_canon()))
            from reporting_inventory import EVIDENCE_QUEUE
            check('containment','seventeen queue items gain no selection',lambda:len(EVIDENCE_QUEUE)==17 and e.eligible_ids(canon.load_canon())==())
    return rows


if __name__=='__main__':
    results=run();summary={'passed':sum(r['ok'] for r in results),'total':len(results),
        'groups':{g:{'passed':sum(r['ok'] for r in results if r['group']==g),'total':sum(r['group']==g for r in results)} for g in sorted({r['group'] for r in results})},
        'failures':[r for r in results if not r['ok']]}
    print(json.dumps(summary,indent=2));raise SystemExit(bool(summary['failures']))
