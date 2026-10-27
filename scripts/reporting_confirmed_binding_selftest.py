#!/usr/bin/env python3
"""WP3C9F real definitions, disposable test signatures and isolated artifacts.

All signing/enrollment is confined to reporting_fixture_review's temporary test
store. Never creates production authority, public content, dist or live calls.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch, Mock

import build
import canon
import generate_content_claude as writer
import reporting_structured as s
import reporting_eligibility as e
import reporting_publication as p
import reporting_pilot as pilot
import reporting_trust as trust
from reporting_fixture_review import store
from reporting_structured_selftest import fixture_page
from reporting_model_binding_selftest import write, raw_sign, signed_page
from reporting_confirmed_contracts_selftest import EXPECTED_IDS, definition, record, rejects


def run_cases():
    rows=[];c=canon.load_canon();cat=s.catalog_from_canon(c)
    def check(group,name,fn):
        try:ok=bool(fn());detail='' if ok else 'assertion false'
        except Exception as exc:ok=False;detail=type(exc).__name__+': '+str(exc)
        rows.append(dict(group=group,name=name,ok=ok,detail=detail))
    authority=store();signer='offline-fixture-reviewer'
    contracts={}
    for rid in EXPECTED_IDS:
        contracts[rid]=e.issue_reviewed(c,rid,reviewer=signer,private_key=authority/'fixture-key')
        write(e.packet_path(rid),contracts[rid])
        check('eligibility',rid+' genuine disposable evidence verifies',lambda rid=rid:bool(e.verify_contract(c,rid)))
    check('eligibility','exact six in disposable test store',lambda:set(e.eligible_ids(c))==set(EXPECTED_IDS))
    check('eligibility','test endorsements never claim production authority',lambda:e.inventory(c)['publication_endorsed_contracts']==[] and set(e.inventory(c)['test_endorsed_contracts'])==set(EXPECTED_IDS))
    check('generator','exact six future IDs from verified eligibility',lambda:set(s.generator_contract(cat,e.eligible_ids(c))['allowed_reporting_routes'])==set(EXPECTED_IDS))
    with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production'}):
        check('eligibility','test signatures grant zero production endorsements',lambda:e.eligible_ids(c)==())
        client=Mock()
        check('generator','production hold before any API call',lambda:rejects(lambda:writer.claude_post(writer.Topic('x','x','email'),'2026-10-14','offline-stub',client,[]),'generation remains held') and not client.messages.create.called)
    for rid in EXPECTED_IDS:
        page=fixture_page();page['slug']='confirmed-'+rid.replace(':','-');page['reporting_routes']=[rid]
        page['quick_answer']={'kind':'action-summary','route_ids':[rid]}
        page['faq']=[{'kind':'action-faq','question_id':'how-to-contact','route_ids':[rid]}]
        context=signed_page(page,c)
        check('approval',rid+' exact context accepted',lambda page=page,context=context:bool(p.review(page,c,context)))
        check('approval',rid+' context signature cannot authorize contract',lambda rid=rid,context=context:rejects(lambda:e.verify_contract(c,rid,context)))
        changed=copy.deepcopy(c)
        if rid.startswith('o2-'):
            definition(changed,rid)['eligibility_ids']=['o2-payg-origin' if rid.startswith('o2-pay-monthly:') else 'o2-pay-monthly-origin']
        elif rid.startswith('own-bank:'):
            d=definition(changed,rid)
            if rid.endswith('number-on-bank-card'):
                d['instruction']['method_id']='existing-bank-app';d['condition_ids'].append('banking-device-safe')
            else:
                d['instruction']['method_id']='number-on-bank-card';d['condition_ids'].remove('banking-device-safe')
        else:record(changed,rid)['name']+=' changed service'
        check('approval',rid+' semantic neighbour invalidates evidence',lambda changed=changed,rid=rid:rejects(lambda:e.verify_contract(changed,rid,contracts[rid]),'binding'))
        check('approval',rid+' semantic neighbour invalidates context',lambda changed=changed,page=page,context=context:rejects(lambda:p.review(page,changed,context),'binding'))
        check('output',rid+' semantic neighbour changes plan and output',lambda changed=changed,rid=rid:s.action_plan_sha256(s.catalog_from_canon(changed),[rid])!=s.action_plan_sha256(cat,[rid]) and s.render_plain(s.catalog_from_canon(changed),[rid])!=s.render_plain(cat,[rid]))

        # Complete controlled positive artifact, followed by distinct invalid
        # context, output, signed manifest and production-runtime controls.
        identity='guide:'+page['slug'];packet_path=authority/'packets'/(hashlib.sha256(identity.encode()).hexdigest()+'.json')
        cfg=trust.read_json(authority/'trust.json');saved=copy.deepcopy(cfg)
        files={'index.html':b'Frozen nonpilot page','assets/styles.css':b'/* fixture css */','assets/app.js':b'/* fixture js */'}
        base=pilot.hashes(files);cfg.update(pilot_page_ids=[identity],baseline_sha256=trust.digest(base))
        write(authority/'baseline.json',base);write(authority/'trust.json',cfg);write(packet_path,context)
        try:
            with tempfile.TemporaryDirectory(prefix='bts-confirmed-artifact-') as raw:
                root=Path(raw).resolve()
                for name,value in [('posts.json',[page]),('category-hubs.json',{}),('sources.json',c)]:write(root/'content'/name,value)
                for name in ('site.json','affiliates.json'):write(root/'content'/name,build.read_json(build.ROOT/'content'/name))
                files.update(pilot.render_selected(root,{identity:page},[page],{},c,files))
                from reporting_workflow_test_support import bind
                revision=bind(root,files)
                manifest=pilot.candidate(root,files,source_revision=revision)
                release=raw_sign(dict(trust.header(pilot.VERSION),reviewer=signer,manifest=manifest),pilot.VERSION)
                check('output',rid+' genuine exact artifact accepted in test only',lambda:pilot.verify_release(release,root,files,production=False,source_revision=revision)==manifest)
                check('output',rid+' action identity bound into manifest',lambda:manifest['pages'][0]['action_plan_sha256']==s.action_plan_sha256(cat,[rid]) and manifest['canon_sha256']==s.digest(c))
                packet_path.unlink()
                check('deployment',rid+' eligible contract without context approval holds',lambda:rejects(lambda:pilot.candidate(root,files)))
                write(packet_path,context)
                substituted=copy.deepcopy(files);substituted[pilot.output_path(identity)]+=b' changed'
                check('output',rid+' output substitution rejected',lambda:rejects(lambda:pilot.verify_release(release,root,substituted,production=False,source_revision=revision)))
                bad=copy.deepcopy(release['body']);bad['manifest']['pages'][0]['action_plan_sha256']='0'*64
                invalid=raw_sign(bad,pilot.VERSION)
                check('output',rid+' authentically signed wrong manifest rejected',lambda:rejects(lambda:pilot.verify_release(invalid,root,files,production=False,source_revision=revision),'manifest differs'))
                check('deployment',rid+' test runtime cannot deploy',lambda:rejects(lambda:pilot.verify_release(release,root,files,production=True,source_revision=revision),'test authority'))
                check('deployment',rid+' missing release approval holds',lambda:rejects(lambda:pilot.verify_release({},root,files,production=False,source_revision=revision),'missing release'))
        finally:write(authority/'trust.json',saved)

    # Same evidence source/owner/destination/template is not a seventh grant.
    changed=copy.deepcopy(c);service=record(changed,EXPECTED_IDS[0]);service['actions']['unreviewed-copy']=copy.deepcopy(service['actions']['consumer-advice-english'])
    seventh='citizens-advice:unreviewed-copy'
    check('held','same-owner same-source same-destination neighbour is representable',lambda:seventh in s.catalog_from_canon(changed).actions)
    check('held','neighbour cannot inherit a signature',lambda:rejects(lambda:e.verify_contract(changed,seventh,contracts[EXPECTED_IDS[0]]),'binding'))
    check('held','whole-canon change invalidates old approvals too',lambda:e.eligible_ids(changed)==())
    # Genuine context approval cannot introduce bank instructions from prose,
    # citations or author fields, even with raw destination scanner disabled.
    for rid in EXPECTED_IDS[4:]:
        for label,field,value in [
            ('phone','destination','01234 567890'),('url','destination','https://attacker.invalid/'),
            ('app-link','app_link','https://attacker.invalid/app'),('recipient','recipient_relation','receiving-bank'),
            ('trigger','condition_ids',[]),('payment','condition_ids',['money-sent']),
            ('article-instruction','instruction',{'method_id':'web-search'}),
            ('citation-as-destination','sources_checked',[['Use this source to contact your bank','https://sources.example/contact']]),
            ('web-search','sections',[['Contact safely','Search online for a telephone number and call the bank using that result.']])]:
            page=fixture_page();page['reporting_routes']=[rid];page[field]=value;pkt=signed_page(page,c)
            def boundary(page=page,pkt=pkt):
                with patch.object(s,'_raw_destinations',return_value=[]):return rejects(lambda:p.review(page,c,pkt))
            check('bank_adversarial',rid+' signed '+label+' cannot create capability',boundary)
    # Canon changes already require renewed evidence; no persisted keys or
    # signatures are used by the real repository after this process exits.
    return rows


if __name__=='__main__':
    rows=run_cases();out={'passed':sum(r['ok'] for r in rows),'total':len(rows),
        'groups':{g:{'passed':sum(r['ok'] for r in rows if r['group']==g),'total':sum(r['group']==g for r in rows)} for g in sorted({r['group'] for r in rows})},
        'failures':[r for r in rows if not r['ok']], 'authority':'disposable test only; no production signatures'}
    print(json.dumps(out,indent=2));raise SystemExit(bool(out['failures']))
