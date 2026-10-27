#!/usr/bin/env python3
"""R6A AF S49–S64: authenticated TEST consumers and containment.

Disposable TEST keys and Git/artifact fixtures only. The real R6B2 compatibility
pin preserves exactly the six reviewed contracts; new SMS cases remain held.
"""
import copy
from contextlib import contextmanager
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from types import MappingProxyType
from unittest.mock import patch, Mock

import build
import canon
import content_gate as gate
import generate_content_claude as writer
import reporting_actions as v
import reporting_structured as s
import reporting_eligibility as e
import reporting_publication as p
import reporting_pilot as pilot
import reporting_trust as trust
from reporting_action_render import components
from reporting_fixture_review import store
from reporting_structured_selftest import fixture_page
from reporting_model_binding_selftest import signed_page, raw_sign, write
from reporting_confirmed_contracts_selftest import record, definition, EXPECTED_IDS, ORACLE
from reporting_composed_sms_selftest import fixture, RID, CASE, EXPECTED_HTML, EXPECTED_PLAIN, denied


def protected_snapshot():
    root=Path(__file__).resolve().parents[1]
    return {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
        for group in ('content','dist','deployment','.github/workflows')
        for path in sorted((root/group).rglob('*')) if path.is_file()}


def page_fixture():
    page=fixture_page();page.update(slug='composed-sms-fixture',reporting_routes=[RID],
        quick_answer={'kind':'action-summary','route_ids':[RID]},
        faq=[{'kind':'action-faq','question_id':'where-to-report','route_ids':[RID]}])
    return page


@contextmanager
def artifact():
    authority=store();saved=trust.read_json(authority/'trust.json');c=fixture();page=page_fixture()
    identity='guide:'+page['slug'];packet=signed_page(page,c)
    contract=e.issue_reviewed(c,RID,reviewer='offline-fixture-reviewer',private_key=authority/'fixture-key')
    write(e.packet_path(RID),contract)
    write(authority/'packets'/(hashlib.sha256(identity.encode()).hexdigest()+'.json'),packet)
    files={'index.html':b'Frozen nonpilot page','assets/styles.css':b'/* fixture css */','assets/app.js':b'/* fixture js */'}
    base=pilot.hashes(files);cfg=trust.read_json(authority/'trust.json')
    cfg.update(pilot_page_ids=[identity],baseline_sha256=trust.digest(base))
    write(authority/'baseline.json',base);write(authority/'trust.json',cfg)
    try:
        with tempfile.TemporaryDirectory(prefix='bts-sms-artifact-') as raw:
            root=Path(raw).resolve()
            for name,value in [('posts.json',[page]),('category-hubs.json',{}),('sources.json',c)]:write(root/'content'/name,value)
            for name in ('site.json','affiliates.json'):write(root/'content'/name,build.read_json(build.ROOT/'content'/name))
            files.update(pilot.render_selected(root,{identity:page},[page],{},c,files))
            from reporting_workflow_test_support import bind
            revision=bind(root,files)
            manifest=pilot.candidate(root,files,source_revision=revision)
            release=raw_sign(dict(trust.header(pilot.VERSION),reviewer='offline-fixture-reviewer',manifest=manifest),pilot.VERSION)
            assert e.verify_contract(c,RID,contract)
            assert p.review(page,c,packet)
            assert pilot.verify_release(release,root,files,production=False,source_revision=revision)==manifest
            yield c,page,contract,packet,root,files,revision,release,manifest
    finally:
        write(authority/'trust.json',saved)
        e.packet_path(RID).unlink(missing_ok=True)


def semantic_mutation(field, value):
    with artifact() as (c,page,contract,packet,root,files,revision,release,manifest):
        cat=s.catalog_from_canon(c);a=cat.resolve(RID)
        if field=='case':bad=replace(a,sms_composition_case_id=value)
        elif field=='schema':bad=replace(a,schema_version=value)
        else:bad=replace(a,sms_composition=replace(a.sms_composition,**{field:value}))
        assert s.digest(asdict(a))!=s.digest(asdict(bad))
        # Authenticate controls before challenging the semantic consumption layer.
        for pkt,role,domain in [(contract,'contracts',e.VERSION),(packet,'context',p.NAMESPACE),(release,'release',pilot.VERSION)]:
            trust.verify(pkt['body'],pkt['signature'],role,domain)
        forged=s.Catalog(cat.canon_sha256,MappingProxyType({**cat.actions,RID:bad}))
        with patch.object(s,'catalog_from_canon',return_value=forged):
            denied(lambda:s.action_plan(forged,[RID]))
            denied(lambda:e.verify_contract(c,RID,contract))
            denied(lambda:p.review(page,c,packet))
            denied(lambda:pilot.verify_release(release,root,files,production=False,source_revision=revision))


def destination_mutation():
    with artifact() as (c,page,contract,packet,root,files,revision,release,manifest):
        bad=copy.deepcopy(c);record(bad,RID)['sms']='8888';new=s.catalog_from_canon(bad)
        assert s.action_plan_sha256(new,[RID])!=manifest['pages'][0]['action_plan_sha256']
        assert components(new,[RID])[0].html()!=EXPECTED_HTML
        denied(lambda:e.verify_contract(bad,RID,contract),'binding')
        denied(lambda:p.review(page,bad,packet))
        write(root/'content/sources.json',bad)
        denied(lambda:pilot.verify_release(release,root,files,production=False,source_revision=revision))


def run_cases():
    rows=[];before=protected_snapshot()
    def check(n,name,fn):
        try:
            assert components(s.catalog_from_canon(fixture()),[RID])[0].html()==EXPECTED_HTML
            fn();ok=True;detail=''
        except Exception as exc:ok=False;detail=type(exc).__name__+': '+str(exc)
        rows.append({'id':f'S{n:02}','requirement':'R6A AF','name':name,'ok':ok,'detail':detail})
    check(49,'provider mutation invalidates contract/context/manifest',lambda:semantic_mutation('provider_scope_id','*'))
    check(50,'case-ID mutation invalidates contract/context/manifest',lambda:semantic_mutation('case','unknown'))
    check(51,'payload mutation invalidates contract/context/manifest',lambda:semantic_mutation('payload_profile_id','original-email'))
    check(52,'prefix semantic and bytes invalidate all consumers',lambda:[semantic_mutation(k,x) for k,x in [('literal_semantic_id','other-prefix'),('literal','CALL')]])
    check(53,'order mutation invalidates all consumers',lambda:semantic_mutation('components',('caller-number-from-recent-calls-sms','call-prefix')))
    check(54,'destination mutation invalidates all consumers',destination_mutation)
    def versions():
        semantic_mutation('schema','restricted-actions/v2')
        with artifact() as (c,page,contract,packet,root,files,revision,release,manifest):
            for pkt,domain,consume in [(contract,'beatthescam-contract-evidence-v2',lambda x:e.verify_contract(c,RID,x)),
                    (packet,'beatthescam-publication-v3',lambda x:p.review(page,c,x)),
                    (release,'beatthescam-pilot-release-v3',lambda x:pilot.verify_release(x,root,files,production=False,source_revision=revision))]:
                body=copy.deepcopy(pkt['body']);body['version']=domain
                denied(lambda:consume(raw_sign(body,domain)),'schema')
            with patch.object(s,'contract_model_sha256',return_value='0'*64):
                denied(lambda:e.verify_contract(c,RID,contract),'binding')
                denied(lambda:p.review(page,c,packet),'plan/model binding')
                denied(lambda:pilot.verify_release(release,root,files,production=False,source_revision=revision))
    check(55,'schema/model and authentic old domains reject',versions)
    def projections():
        with artifact() as (c,page,contract,packet,root,files,revision,release,manifest):
            identity='guide:'+page['slug'];path=pilot.output_path(identity);html=files[path].decode()
            blocks=re.findall(r'<div class="restricted-action" data-action-id="[^"]+">.*?</div>',html,re.S)
            assert blocks==[EXPECTED_HTML]*3
            objects=[json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>',html,re.S)]
            faq=next(x for x in objects if x.get('@type')=='FAQPage')
            assert faq['mainEntity'][0]['acceptedAnswer']['text']==EXPECTED_PLAIN
            assert manifest['version']=='pilot-output/v4' and manifest['schema_version']=='restricted-actions/v3'
            for old,new in [('O2 mobile line','any mobile line'),('<span>Call</span>','<span>Text</span>'),('beginning with Call','beginning with Text')]:
                bad=dict(files);bad[path]=html.replace(old,new).encode();assert bad[path]!=files[path]
                denied(lambda:pilot.verify_release(release,root,bad,production=False,source_revision=revision))
            body=copy.deepcopy(release['body']);body['manifest']['pages'][0]['action_plan_sha256']='0'*64
            denied(lambda:pilot.verify_release(raw_sign(body,pilot.VERSION),root,files,production=False,source_revision=revision),'manifest differs')
            bad_revision=dict(revision,source_commit='a'*40)
            denied(lambda:pilot.verify_release(release,root,files,production=False,source_revision=bad_revision),'source revision')
    check(56,'literal projections and authenticated artifact/manifest/revision substitution',projections)
    def generator():
        c=fixture();interface=s.generator_contract(s.catalog_from_canon(c),[RID]);descriptor=interface['actions'][0]
        assert descriptor['sms_composition_case_id']==CASE and descriptor['provider_scope_id']=='o2-uk-mobile-line'
        assert interface['allowed_reporting_routes']==[RID]
        assert not {'literal','components','separator','sms_body','destination'} & set(descriptor)
        prompt=writer.restricted_prompt(writer.Topic('x','x','email'),'2026-10-22',interface)
        assert '7726' not in prompt and '<span>Call' not in prompt
        denied(lambda:s.generator_contract(s.catalog_from_canon(c),['own-mobile-provider:invented']))
        with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production'}):
            client=Mock()
            denied(lambda:writer.claude_post(writer.Topic('x','x','email'),'2026-10-22','offline-stub',client,[]),'generation remains held')
            assert not client.messages.create.called and not e.contract_production_eligible_ids(c)
    check(57,'generator whole eligible IDs only and no production selection',generator)
    def extra_fields():
        c=fixture()
        for key,value in [('provider','invented'),('sms_composition_case_id',CASE),('message_prefix','Call'),('shortcode','7726'),('payload_profile_id','original-email'),('components',['caller','Call'])]:
            page=page_fixture();page[key]=value;packet=signed_page(page,c)
            assert writer.normalise(page,writer.Topic('x','x','email'),'2026-10-22',strict=True)==page
            denied(lambda:p.review(page,c,packet))
    check(58,'unknown generator fields survive normalization and reject',extra_fields)
    def actual_writer():
        c=fixture();good=page_fixture();packet=signed_page(good,c)
        with tempfile.TemporaryDirectory(prefix='bts-sms-writer-') as raw:
            target=Path(raw)/'posts.json';target.write_text('[]\n')
            writer.save_posts(str(target),[good],reporting_canon=c,reporting_reviews={good['slug']:packet})
            frozen=target.read_bytes();bad=copy.deepcopy(good);bad['instruction']={'provider':'*','sms_body':'Call 07123456789'}
            hostile=signed_page(bad,c)
            denied(lambda:writer.save_posts(str(target),[bad],reporting_canon=c,reporting_reviews={bad['slug']:hostile}))
            assert target.read_bytes()==frozen
    check(59,'real writer positive and unchanged target on rejection',actual_writer)
    def hostile_prose():
        c=fixture();good=page_fixture();assert p.review(good,c,signed_page(good,c))
        bad=copy.deepcopy(good);bad['sections'][0][1]='Text Call 07123456789 to 7726.';packet=signed_page(bad,c)
        trust.verify(packet['body'],packet['signature'],'context',p.NAMESPACE)
        with patch.object(s,'_raw_destinations',return_value=[]),patch.object(s,'raw_destinations',return_value=[]):
            denied(lambda:p.review(bad,c,packet))
    check(60,'authentic hostile prose rejected with raw scanner disabled',hostile_prose)
    def test_production():
        with artifact() as (c,page,contract,packet,root,files,revision,release,manifest):
            denied(lambda:pilot.verify_release(release,root,files,production=True,source_revision=revision),'test authority')
            with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production'}):
                denied(lambda:e.verify_contract(c,RID,contract))
                assert not p.is_page_publication_eligible(page,c,packet)
    check(61,'TEST authority rejected in production',test_production)
    def scope():
        with artifact() as (c,page,contract,packet,root,files,revision,release,manifest):
            authority=store();cfg=trust.read_json(authority/'trust.json')
            for ids in ([],['guide:other']):
                write(authority/'trust.json',dict(cfg,pilot_page_ids=ids))
                denied(lambda:p.review(page,c,packet),'scope')
                denied(lambda:pilot.verify_release(release,root,files,production=False,source_revision=revision))
            write(authority/'trust.json',cfg);assert p.review(page,c,packet)
    check(62,'current empty and shrunk scope consumed in same process',scope)
    def compatibility():
        c=canon.load_canon();cat=s.catalog_from_canon(c);oracle=json.loads(ORACLE.read_text())
        assert set(e.REVIEWED_CONTRACT_IDS)==set(EXPECTED_IDS) and set(e.contract_production_eligible_ids(c))==set(EXPECTED_IDS)
        for rid in EXPECTED_IDS:
            a=cat.resolve(rid);assert type(a) is s.Action and a.schema_version=='restricted-actions/v2'
            assert s.digest(asdict(a))==c['contract_evidence']['contracts'][rid]['resolved_action_sha256']
            assert s.render_plain(cat,[rid])==oracle['contracts'][rid]['expected_text']
        assert e.contract_production_eligible_ids(fixture())==()
        with patch.object(e,'REVIEWED_MODEL_SHA256','1606940009f584f2ca5d4ec8f11767ca0700f61ad8657263df929642ad01830a'):
            assert e.contract_production_eligible_ids(c)==()
        assert set(e.contract_production_eligible_ids(c))==set(EXPECTED_IDS)
    check(63,'six unchanged and actually eligible; old pin and new SMS stay held',compatibility)
    def containment():
        root=Path(__file__).resolve().parents[1];cfg=json.loads((root/'deployment/review-store/trust.json').read_text())
        assert cfg['pilot_page_ids']==['hub:phone'] and json.loads((root/'deployment/review-store/baseline.json').read_text())=={}
        assert trust.digest(cfg)=='c5edefda52f8c9c9f7f345b217404767dca44b2aad5e8df51ecde9092ff495db'
        hubs=json.loads((root/'content/category-hubs.json').read_text())
        approved=json.loads((root/'scripts/fixtures/wp3c9k_r4_reconciliation.json').read_text())['approved_phone']
        assert s.digest(hubs['phone'])==approved['source_sha256']
        assert not gate.check_report_fraud_destinations(hubs['phone'])
        caller={'sections':[['Reporting', "From a mobile, forward the caller's phone number to 7726."]]}
        assert any(x['span']=='7726' and x['severity']=='block' for x in gate.check_report_fraud_destinations(caller))
        import corpus
        pages=[('guide:'+x['slug'],x) for x in corpus.public_posts(json.loads((root/'content/posts.json').read_text()))]+[('hub:'+k,x) for k,x in hubs.items()]
        assert len(pages)==204 and [i for i,x in pages if 'reporting_routes' in x]==['hub:phone']
        with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production','BTS_REVIEW_STORE':''}):
            assert all(not p.is_page_publication_eligible(x,canon.load_canon(),page_id=i) for i,x in pages)
        assert protected_snapshot()==before
    check(64,'R11 phone migration, caller hold, current scope and unchanged protected bytes',containment)
    return rows


if __name__=='__main__':
    rows=run_cases();print(json.dumps({'passed':sum(r['ok'] for r in rows),'total':len(rows),'cases':rows},indent=2));raise SystemExit(any(not r['ok'] for r in rows))
