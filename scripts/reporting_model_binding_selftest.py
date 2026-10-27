#!/usr/bin/env python3
"""WP3C9D2 genuine disposable signatures, writer and exact-output checks.

All stores, keys and artifacts are temporary test data. No production root,
real approval, network, model API, build() output, or content write is used.
"""
import copy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch, Mock
import build
import canon
import content_gate as gate
import generate_content_claude as writer
import reporting_actions as vocabulary
import reporting_structured as s
import reporting_eligibility as e
import reporting_publication as p
import reporting_pilot as pilot
import reporting_trust as trust
from reporting_action_render import components
from reporting_fixture_review import store, packet_for
from reporting_structured_selftest import fixture_page, review_for
from reporting_model_extension_selftest import CASES, case_fixture, definition, rejects


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def raw_sign(body,namespace):
    root=store()
    with tempfile.TemporaryDirectory(prefix='bts-v2-raw-sign-') as raw:
        path=Path(raw)/'input';path.write_bytes(p._json(body))
        subprocess.run(['ssh-keygen','-Y','sign','-f',str(root/'fixture-key'),'-n',namespace+':test',str(path)],capture_output=True,check=True)
        return {'body':copy.deepcopy(body),'signature':path.with_suffix('.sig').read_text()}


def signed_page(page,c):
    review=review_for(page,c,approved_fields=dict(s.approval_fields(page)))
    return packet_for(page,c,review)


def run_cases():
    rows=[]
    def check(group,name,fn):
        try: ok=bool(fn()); detail='' if ok else 'assertion false'
        except Exception as exc: ok=False;detail=type(exc).__name__+': '+str(exc)
        rows.append(dict(group=group,name=name,ok=ok,detail=detail))
    authority=store(); signer='offline-fixture-reviewer'
    for case in CASES:
        c,rid=case_fixture(case);cat=s.catalog_from_canon(c); a=cat.resolve(rid)
        check('eligibility',case+' model support alone not eligible',lambda c=c:e.eligible_ids(c)==())
        contract=e.issue_reviewed(c,rid,reviewer=signer,private_key=authority/'fixture-key')
        check('approval',case+' signed contract round trip',lambda c=c,rid=rid,contract=contract:bool(e.verify_contract(c,rid,contract)))
        check('approval',case+' all immutable fields bound',lambda c=c,rid=rid,a=a: e.claims(c,rid)['contract_sha256']==s.digest(asdict(a))
              and e.claims(c,rid)['contract_model_sha256']==s.contract_model_sha256())
        page=fixture_page();page['slug']='model-'+case.lower();page['reporting_routes']=[rid]
        page['quick_answer']={'kind':'action-summary','route_ids':[rid]}
        page['faq']=[{'kind':'action-faq','question_id':'where-to-report','route_ids':[rid]}]
        packet=signed_page(page,c)
        check('approval',case+' context version and plan',lambda page=page,c=c,packet=packet,cat=cat,rid=rid:
            p.review(page,c,packet).page_sha256==s.digest(page)
            and packet['body']['action_selection']['action_plan_sha256']==s.action_plan_sha256(cat,[rid]))
        def projection(page=page,c=c,packet=packet,cat=cat,rid=rid):
            html=build.render_post(build.read_json(build.ROOT/'content/site.json'),page,[page],sources=c,reporting_review=packet)
            node=components(cat,[rid])[0]
            blocks=re.findall(r'<div class="restricted-action" data-action-id="[^"]+">.*?</div>',html,re.S)
            assert blocks==[node.html()]*3
            objects=[json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>',html,re.S)]
            faq=next(x for x in objects if x.get('@type')=='FAQPage')
            return faq['mainEntity'][0]['acceptedAnswer']['text']==node.plain() and gate.run_gate(page,use_llm=False,reporting_canon=c,reporting_review=packet).passed
        check('renderer',case+' exact full page/gate/FAQ schema projections',projection)
        def writer_case(page=page,c=c,packet=packet):
            with tempfile.TemporaryDirectory(prefix='bts-v2-writer-') as raw:
                target=Path(raw)/'posts.json'; target.write_text('[]\n')
                writer.save_posts(str(target),[page],reporting_canon=c,reporting_reviews={page['slug']:packet})
                return json.loads(target.read_text())==[page]
        check('writer',case+' actual offline writer accepts',writer_case)
        # Factual territory changes are bound by evidence, not inferred by grammar.
        changed=copy.deepcopy(c);definition(changed)['jurisdictions']=['Scotland']
        check('approval',case+' jurisdiction replay',lambda changed=changed,rid=rid,contract=contract:rejects(lambda:e.verify_contract(changed,rid,contract),'binding'))
        bad=copy.deepcopy(packet['body']);bad['action_selection']['audience']=['Northern Ireland']
        hostile=raw_sign(bad,p.NAMESPACE)
        check('approval',case+' authentic incompatible audience',lambda page=page,c=c,hostile=hostile:rejects(lambda:p.review(page,c,hostile),'scope exceeds'))
        for path in ('schema_version','eligibility_ids','qualifier_ids','recipient_relation','payload_profile_id','dialling_network_id','resolution_kind'):
            descriptor=s.action_descriptor(a)
            check('generator',case+' descriptor '+path,lambda path=path,descriptor=descriptor:path in descriptor)
        interface=s.generator_contract(cat,[rid]);prompt=writer.restricted_prompt(writer.Topic('x','x','email'),'2026-10-12',interface)
        check('generator',case+' read-only descriptors exclude notes/endpoints/subject',lambda prompt=prompt:
            'routes.example' not in prompt and 'INTERNAL EVIDENCE' not in prompt and 'phishing email example' not in prompt and 'read-only' in prompt)
        for version in ('beatthescam-contract-evidence-v1','beatthescam-contract-evidence-v99'):
            body=copy.deepcopy(contract['body']);body['version']=version;old=raw_sign(body,version)
            check('schema',case+' authentic '+version,lambda c=c,rid=rid,old=old:rejects(lambda:e.verify_contract(c,rid,old),'schema'))
        body=copy.deepcopy(packet['body']);body['version']='beatthescam-publication-v2';old=raw_sign(body,body['version'])
        check('schema',case+' authentic old context',lambda page=page,c=c,old=old:rejects(lambda:p.review(page,c,old),'schema'))
        body=copy.deepcopy(contract['body']);body['claims']['schema_version']='restricted-actions/v1';bad=raw_sign(body,e.VERSION)
        check('schema',case+' new signature old schema claim',lambda c=c,rid=rid,bad=bad:rejects(lambda:e.verify_contract(c,rid,bad),'binding'))
    # Structurally valid semantic neighbours: evidence and context cannot replay.
    variants=[('C01','remove-no-feedback'),('C04','reference-predicate'),('C07','other-plan'),
              ('C09','safe-app'),('M04','add-brand'),('C06','note-only'),('C06','brand')]
    for case,variant in variants:
        c,rid=case_fixture(case);cat=s.catalog_from_canon(c)
        packet=e.issue_reviewed(c,rid,reviewer=signer,private_key=authority/'fixture-key')
        page=fixture_page();page['reporting_routes']=[rid];context=signed_page(page,c)
        changed=copy.deepcopy(c);d=definition(changed)
        if variant=='remove-no-feedback':d['limitation_ids']=['evidence-only']
        elif variant=='reference-predicate':
            d['condition_ids']=['suspicious-email','email-refers-to-service-brand'];d['instruction']['template_id']='forward-brand-reference-email'
        elif variant=='other-plan':d['eligibility_ids']=['o2-payg-origin']
        elif variant=='safe-app':d['instruction']['method_id']='existing-bank-app';d['condition_ids'].append('banking-device-safe')
        elif variant=='add-brand':d['condition_ids'].append('email-claims-service-brand')
        elif variant=='note-only':changed['verified_org_contacts'][-1]['note']='INTERNAL revised evidence observation'
        else:changed['verified_org_contacts'][-1]['brand']='A different fixture brand'
        new=s.catalog_from_canon(changed)
        check('approval',variant+' valid neighbour cannot borrow evidence',lambda changed=changed,rid=rid,packet=packet:
            rejects(lambda:e.verify_contract(changed,rid,packet),'binding'))
        check('approval',variant+' context replay',lambda changed=changed,page=page,context=context:
            rejects(lambda:p.review(page,changed,context),'binding'))
        check('output',variant+' plan and render identity',lambda variant=variant,cat=cat,new=new,rid=rid:
            ((s.action_plan_sha256(cat,[rid])!=s.action_plan_sha256(new,[rid]))==(variant!='note-only'))
            and ((s.render_plain(cat,[rid])!=s.render_plain(new,[rid]))==(variant!='note-only')))
    # Every new path rejects forged values at source boundaries even if signed.
    c,rid=case_fixture('C09')
    for field,value in [('schema_version','restricted-actions/v2'),('eligibility_ids',['sender-own-account']),
        ('qualifier_ids',['free-uk-phone-call']),('instruction',{'recipient_relation':'sending-bank-of-affected-transfer'}),
        ('recipient_relation','sending-bank-of-affected-transfer'),('payload_profile_id','original-email'),
        ('dialling_network_id','o2-uk'),('destination','01234 567890'),('recorded_evidence_note','Contact your bank now.')]:
        page=fixture_page();page['reporting_routes']=[rid];page[field]=value;pkt=signed_page(page,c)
        def quarantine(page=page,pkt=pkt):
            normalized=writer.normalise(page,writer.Topic('x','x','email'),'2026-10-12',strict=True)
            if normalized!=page:return False
            with tempfile.TemporaryDirectory(prefix='bts-v2-quarantine-') as raw:
                target=Path(raw)/'posts.json';target.write_text('[]\n');q=Path(raw)/'quarantine'
                with patch.object(s,'_raw_destinations',return_value=[]):
                    failed=rejects(lambda:writer.save_posts(str(target),[page],reporting_canon=c,reporting_reviews={page['slug']:pkt},quarantine_dir=q))
                return failed and target.read_text()=='[]\n' and len(list(q.glob('*.json')))==1
        check('writer','signed override quarantines '+field,quarantine)
        check('adversarial','signed source field cannot create capability '+field,lambda page=page,pkt=pkt:rejects(lambda:p.review(page,c,pkt)))
    for field in ('sections','description','category','keywords','citation','quick_answer','faq'):
        page=fixture_page();page['reporting_routes']=[rid];text='Contact the bank that sent the transfer using the number from the source above.'
        if field=='sections':page[field][0][1]=text
        elif field=='faq':page[field][0][1]=text
        elif field=='citation':page['sources_checked']=[[text,'https://sources.example/evidence']]
        elif field=='keywords':page[field]=[text]
        else:page[field]=text
        pkt=signed_page(page,c)
        def boundary(page=page,pkt=pkt):
            with patch.object(s,'_raw_destinations',return_value=[]):return rejects(lambda:p.review(page,c,pkt))
        check('adversarial','authentic non-action '+field+' with raw scanner disabled',boundary)
    for label,mutate in [
        ('unknown eligibility',lambda d:d.update(eligibility_ids=['arbitrary'])),
        ('wrong trigger',lambda d:d.update(condition_ids=['suspicious-text'])),
        ('payload injection',lambda d:d['instruction'].update(payload_profile_id={'body':'CALL 123'})),
        ('wrong recipient',lambda d:d['instruction'].update(recipient_relation='sending-bank-of-affected-transfer'))]:
        bad,rid=case_fixture('M05');mutate(definition(bad));page=fixture_page();page['reporting_routes']=[rid]
        pkt=signed_page(page,bad)
        def bad_contract_writer(bad=bad,page=page,pkt=pkt):
            with tempfile.TemporaryDirectory(prefix='bts-v2-invalid-contract-') as raw:
                target=Path(raw)/'posts.json';target.write_text('[]\n');q=Path(raw)/'quarantine'
                failed=rejects(lambda:writer.save_posts(str(target),[page],reporting_canon=bad,reporting_reviews={page['slug']:pkt},quarantine_dir=q))
                return failed and target.read_text()=='[]\n' and len(list(q.glob('*.json')))==1
        check('writer','invalid complete contract quarantines '+label,bad_contract_writer)
    c,rid=case_fixture('C09');page=fixture_page();page['reporting_routes']=[rid]
    def preflight_reject():
        changed=copy.deepcopy(page);changed['instruction']={'recipient_relation':'arbitrary'}
        original=build.read_json
        with patch.object(build,'read_json',side_effect=lambda path:[changed] if Path(path).name=='posts.json' else original(path)), patch.object(build.shutil,'rmtree') as remove:
            try:build.build()
            except (ValueError,SystemExit):return not remove.called
        return False
    check('writer','new field override preflight before destructive output',preflight_reject)
    # Model dependency bytes, including code-owned literal subjects/hours, are
    # recomputed. No cache or same-ID semantic replay across any of the five files.
    c,rid=case_fixture('C06');contract=e.issue_reviewed(c,rid,reviewer=signer,private_key=authority/'fixture-key')
    page=fixture_page();page['reporting_routes']=[rid];context=signed_page(page,c);original=s.contract_model_sha256()
    paths=('reporting_actions.py','reporting_action_canon.py','reporting_action_render.py','reporting_structured.py','reporting_syntax.py')
    with tempfile.TemporaryDirectory(prefix='bts-v2-model-') as raw:
        root=Path(raw)
        for name in paths:(root/name).write_bytes(Path(s.__file__).with_name(name).read_bytes())
        for name in paths:
            path=root/name;before=path.read_bytes();path.write_bytes(before+b'\n# changed model semantics\n')
            with patch.object(s,'__file__',str(root/'reporting_structured.py')):
                check('approval','model bytes invalidate evidence '+name,lambda:s.contract_model_sha256()!=original and rejects(lambda:e.verify_contract(c,rid,contract),'binding'))
                check('approval','model bytes invalidate context '+name,lambda:rejects(lambda:p.review(page,c,context),'plan/model binding'))
            path.write_bytes(before)
    check('eligibility','real canon still zero production endorsements',lambda:not e.eligible_ids(canon.load_canon()) and not e.inventory(canon.load_canon())['publication_endorsed_contracts'])
    with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production'}):
        check('eligibility','test root cannot authorize production',lambda:rejects(lambda:e.verify_contract(c,rid,contract)))
        client=Mock()
        check('generator','zero real eligibility prevents API call',lambda:rejects(lambda:writer.claude_post(writer.Topic('x','x','email'),'2026-10-12','offline-stub',client,[]),'generation remains held') and not client.messages.create.called)
    # Complete exact-artifact flow for every new case with a test-only enrollment.
    for case in CASES:
        def artifact(case=case):
            c,rid=case_fixture(case);page=fixture_page();page['slug']='artifact-'+case.lower();page['reporting_routes']=[rid]
            identity='guide:'+page['slug'];packet=signed_page(page,c)
            write(e.packet_path(rid),e.issue_reviewed(c,rid,reviewer=signer,private_key=authority/'fixture-key'))
            write(authority/'packets'/(hashlib.sha256(identity.encode()).hexdigest()+'.json'),packet)
            cfg=trust.read_json(authority/'trust.json');saved=copy.deepcopy(cfg)
            files={'index.html':b'Frozen nonpilot page','assets/styles.css':b'/* fixture css */','assets/app.js':b'/* fixture js */'}
            base=pilot.hashes(files);cfg.update(pilot_page_ids=[identity],baseline_sha256=trust.digest(base))
            write(authority/'baseline.json',base);write(authority/'trust.json',cfg)
            try:
                with tempfile.TemporaryDirectory(prefix='bts-v2-artifact-') as raw:
                    root=Path(raw).resolve()
                    for file,value in [('posts.json',[page]),('category-hubs.json',{}),('sources.json',c)]:write(root/'content'/file,value)
                    for file in ('site.json','affiliates.json'):write(root/'content'/file,build.read_json(build.ROOT/'content'/file))
                    files.update(pilot.render_selected(root,{identity:page},[page],{},c,files))
                    from reporting_workflow_test_support import bind
                    revision=bind(root,files)
                    manifest=pilot.candidate(root,files,source_revision=revision)
                    assert manifest['version']=='pilot-output/v4' and manifest['schema_version']=='restricted-actions/v3'
                    assert manifest['contract_model_sha256']==s.contract_model_sha256()
                    assert manifest['pages'][0]['action_plan_sha256']==s.action_plan_sha256(s.catalog_from_canon(c),[rid])
                    release=raw_sign(dict(trust.header(pilot.VERSION),reviewer=signer,manifest=manifest),pilot.VERSION)
                    assert pilot.verify_release(release,root,files,production=False,source_revision=revision)==manifest
                    assert rejects(lambda:pilot.verify_release(release,root,files,production=True,source_revision=revision),'test authority')
                    changed=copy.deepcopy(files);changed[pilot.output_path(identity)]+=b' changed'
                    assert rejects(lambda:pilot.verify_release(release,root,changed,production=False,source_revision=revision))
                    for field,value in [('contract_model_sha256','0'*64),('schema_version','restricted-actions/v1'),('version','pilot-output/v1')]:
                        bad=copy.deepcopy(release['body']);bad['manifest'][field]=value
                        assert rejects(lambda:pilot.verify_release(raw_sign(bad,pilot.VERSION),root,files,production=False,source_revision=revision),'manifest differs')
                    bad=copy.deepcopy(release['body']);bad['version']='beatthescam-pilot-release-v1'
                    assert rejects(lambda:pilot.verify_release(raw_sign(bad,bad['version']),root,files,production=False,source_revision=revision),'schema')
                    return True
            finally:
                write(authority/'trust.json',saved)
                e.packet_path(rid).unlink()
        check('output',case+' complete manifest/render/release and authentic replay rejection',artifact)
    # Plan order agrees with rendering, independently of author selection order.
    bank,bid=case_fixture('C09');email,eid=case_fixture('C04')
    bank['verified_org_contacts'].append(email['verified_org_contacts'][-1]);cat=s.catalog_from_canon(bank)
    check('output','one shared protection-first plan order',lambda:[a['route_id'] for a in s.action_plan(cat,[eid,bid])['ordered_actions']]==[bid,eid]
        and [n.action.route_id for n in components(cat,[eid,bid])]==[bid,eid]
        and s.action_plan_sha256(cat,[eid,bid])==s.action_plan_sha256(cat,[bid,eid]))
    return rows


if __name__=='__main__':
    rows=run_cases();print(json.dumps({'total':len(rows),'passed':sum(r['ok'] for r in rows),
        'groups':{g:{'passed':sum(r['ok'] for r in rows if r['group']==g),'total':sum(r['group']==g for r in rows)} for g in sorted({r['group'] for r in rows})},
        'failures':[r for r in rows if not r['ok']]},indent=2));raise SystemExit(any(not r['ok'] for r in rows))
