#!/usr/bin/env python3
"""WP3C9F2 exact real baseline, independent predicates, hostile approvals.

Offline only. TEST keys/roots and TEST namespace signatures live in disposable
temporary directories. No real reviewer or production authority
is enrolled. All positive six-contract cases use the real compatibility pin.
No positive clearance predicate or model pin is mocked.
"""
import copy
from contextlib import ExitStack
from datetime import date, timedelta
import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch, Mock

import canon
import generate_content_claude as writer
import reporting_eligibility as e
import reporting_publication as p
import reporting_pilot as pilot
import reporting_structured as s
import reporting_trust as t
from reporting_confirmed_contracts_selftest import EXPECTED_IDS, HELD, definition, record, rejects
from reporting_structured_selftest import fixture_page
from reporting_model_extension_selftest import case_fixture
from reporting_model_binding_selftest import signed_page, write


def page_for(rid):
    page=fixture_page();page['slug']='separation-'+rid.replace(':','-')
    page['reporting_routes']=[rid]
    return page


def _accepted_compatibility_cases():
    rows=[];c=canon.load_canon();cat=s.catalog_from_canon(c)
    def check(group,name,fn):
        try:ok=bool(fn());detail='' if ok else 'assertion false'
        except Exception as exc:ok=False;detail=type(exc).__name__+': '+str(exc)
        rows.append(dict(group=group,name=name,ok=ok,detail=detail))

    # Pure contract checks must not even consult environment, authority, page
    # review or output verification. This catches accidental future coupling.
    with ExitStack() as stack:
        for obj,name in [(t,'environment'),(t,'store'),(t,'config'),(t,'verify'),(t,'sign'),
                         (p,'review'),(pilot,'verify_release')]:
            stack.enter_context(patch.object(obj,name,side_effect=AssertionError('later layer consulted')))
        check('unsigned','exact six with all later layers unavailable',lambda:set(e.contract_production_eligible_ids(c))==set(EXPECTED_IDS))
        for rid in EXPECTED_IDS:
            check('unsigned',rid,lambda rid=rid:e.is_contract_production_eligible(c,rid))
    for environment in ('production','test','invalid'):
        with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':environment,'BTS_REVIEW_STORE':'','BTS_PRODUCTION_TRUST_SHA256':''}):
            check('unsigned',environment+' cannot affect factual eligibility',lambda:set(e.contract_production_eligible_ids(c))==set(EXPECTED_IDS))
    with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production','BTS_REVIEW_STORE':'','BTS_PRODUCTION_TRUST_SHA256':''}):
        for rid in EXPECTED_IDS:
            check('page',rid+' without approval holds',lambda rid=rid:not p.is_page_publication_eligible(page_for(rid),c))
            check('page',rid+' invalid approval holds',lambda rid=rid:not p.is_page_publication_eligible(page_for(rid),c,{}))
        check('page','inventory distinguishes six clearances from zero endorsements',lambda:set(e.inventory(c)['contract_production_eligible'])==set(EXPECTED_IDS) and not e.inventory(c)['publication_endorsed_contracts'])
        client=Mock()
        check('containment','six contracts do not activate generator',lambda:rejects(lambda:writer.claude_post(writer.Topic('x','x','email'),'2026-10-14','offline-stub',client,[]),'generation remains held') and not client.messages.create.called)

    # Freshness and exact code/data binding are independent of signatures.
    class StaleDate(date):
        @classmethod
        def today(cls):return date(2026,10,14)+timedelta(days=91)
    with patch.object(e,'date',StaleDate):
        check('binding','expired evidence holds all six',lambda:e.contract_production_eligible_ids(c)==())
    with patch.object(s,'contract_model_sha256',return_value='0'*64):
        check('binding','changed model holds all six',lambda:e.contract_production_eligible_ids(c)==())
    mutations={
        'purpose inflation':lambda x:definition(x,EXPECTED_IDS[0]).update(purpose='police-report'),
        'O2 plan crossing':lambda x:definition(x,EXPECTED_IDS[2]).update(eligibility_ids=['o2-payg-origin']),
        'bank app safety omitted':lambda x:definition(x,EXPECTED_IDS[5]).update(condition_ids=['suspected-authorised-bank-transfer-to-fraudster']),
        'bank recipient substituted':lambda x:definition(x,EXPECTED_IDS[4])['instruction'].update(recipient_relation='service-operator'),
        'scope expanded':lambda x:definition(x,EXPECTED_IDS[1]).update(jurisdictions=list(s._NATIONS[:4])),
        'status withdrawn':lambda x:definition(x,EXPECTED_IDS[0]).update(status='withdrawn'),
        'provenance self-cleared':lambda x:x['contract_evidence'].update(implementation_allowlist=['ncsc-sers:report']),
        'evidence source swapped':lambda x:record(x,EXPECTED_IDS[0]).update(source_url='https://attacker.invalid/'),
        'whole canon notes changed':lambda x:record(x,EXPECTED_IDS[0]).update(note='Self-approved'),
    }
    for name,change in mutations.items():
        bad=copy.deepcopy(c);change(bad)
        check('binding',name,lambda bad=bad:all(not e.is_contract_production_eligible(bad,rid) for rid in EXPECTED_IDS))

    # Genuine test-only contexts are usable for tests, never production pages.
    test_page=page_for(EXPECTED_IDS[0]);test_packet=signed_page(test_page,c)
    check('test','valid test context accepted in test environment',lambda:bool(p.review(test_page,c,test_packet)))
    check('test','test context is not production-page eligibility',lambda:not p.is_page_publication_eligible(test_page,c,test_packet))
    with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production'}):
        check('test','test authority cannot cross to production',lambda:not p.is_page_publication_eligible(test_page,c,test_packet))

    # Exercise the same independent clearance and approval layers under TEST.
    # No production namespace is signed; no clearance predicate is mocked.
    with tempfile.TemporaryDirectory(prefix='bts-separation-fake-authority-') as raw:
        tmp=Path(raw).resolve();store=tmp/'store';store.mkdir(mode=0o700);keys={}
        for role in t.ROLES:
            key=tmp/('fake-'+role)
            subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
            keys[role]=key
        cfg={'version':'bts-trust/v1','environment':'test','site':t.SITE,
            'roles':{role:[{'identity':'fixture-'+role,'public_key':' '.join(key.with_suffix('.pub').read_text().split()[:2])}] for role,key in keys.items()},
            'pilot_page_ids':[],'baseline_sha256':'0'*64,'revocations_sha256':t.digest([])}
        write(store/'trust.json',cfg);write(store/'revoked.json',[])
        with patch.dict(os.environ,{'BTS_REVIEW_STORE':str(store),'BTS_REVIEW_ENVIRONMENT':'test',
                'BTS_PRODUCTION_TRUST_SHA256':'','CI':'','GITHUB_ACTIONS':'','NETLIFY':''}):
            def sign(body,role,namespace):
                data=tmp/'adversarial';data.write_bytes(t.canonical(body));sig=data.with_suffix('.sig')
                if sig.exists():sig.unlink()
                subprocess.run(['ssh-keygen','-Y','sign','-f',str(keys[role]),'-n',namespace+':test',str(data)],capture_output=True,check=True)
                return {'body':copy.deepcopy(body),'signature':sig.read_text()}
            def test_review(page,source,packet):
                e.require_contract_actions(source,page["reporting_routes"])
                e.require_actions(source,page["reporting_routes"])
                return p.review(page,source,packet)
            def raw_context(page,source):
                cfg['pilot_page_ids'] = ['guide:'+page['slug']]
                write(store/'trust.json',cfg)
                body=dict(t.header(p.NAMESPACE),scope=p.SCOPE,reviewer='fixture-context',
                    page_id='guide:'+page['slug'],page_sha256=s.digest(page),canon_sha256=s.digest(source),
                    dependencies=p.dependencies(),action_selection=p.action_selection(source,page['reporting_routes'],s._NATIONS[:4]),
                    numeric_facts=[],allow_empty=False)
                return sign(body,'context',p.NAMESPACE)
            for rid in EXPECTED_IDS:
                page=page_for(rid);context=raw_context(page,c)
                check('mandatory',rid+' authentic context cannot waive absent endorsement',lambda page=page,context=context:rejects(lambda:test_review(page,c,context)))
                endorsement=e.issue_reviewed(c,rid,reviewer='fixture-contracts',private_key=keys['contracts'])
                write(e.packet_path(rid),endorsement)
                check('mandatory',rid+' endorsement cannot waive absent context',lambda page=page:rejects(lambda:test_review(page,c,{})))
                check('mandatory',rid+' authentic approved TEST fixture passes both layers',lambda page=page,context=context:bool(test_review(page,c,context)))
                wrong=sign(context['body'],'contracts',p.NAMESPACE)
                check('mandatory',rid+' wrong role holds',lambda page=page,wrong=wrong:rejects(lambda:test_review(page,c,wrong)))
                with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production','BTS_PRODUCTION_TRUST_SHA256':''}):
                    check('mandatory',rid+' missing runtime trust pin holds',lambda page=page,context=context:rejects(lambda:test_review(page,c,context)))
            check('mandatory','six endorsements still only six contract clearances',lambda:set(e.contract_production_eligible_ids(c))==set(EXPECTED_IDS))

            # Authentic signatures on fully resolved but uncleared definitions:
            # verify endorsement crypto first, then require the factual layer to
            # reject. This distinguishes clearance rejection from bad signatures.
            held=[(case,*case_fixture(case)) for case in HELD]
            neighbour=copy.deepcopy(c);record(neighbour,EXPECTED_IDS[0])['actions']['unreviewed-copy']=copy.deepcopy(definition(c,EXPECTED_IDS[0]))
            held.append(('seventh',neighbour,'citizens-advice:unreviewed-copy'))
            for case,source,rid in held:
                page=page_for(rid);context=raw_context(page,source)
                endorsement=e.issue_reviewed(source,rid,reviewer='fixture-contracts',private_key=keys['contracts'])
                write(e.packet_path(rid),endorsement)
                check('held',case+' schema resolves',lambda source=source,rid=rid:bool(s.catalog_from_canon(source).select([rid])))
                check('held',case+' authentic endorsement really verifies',lambda source=source,rid=rid:bool(e.verify_contract(source,rid)))
                check('held',case+' authentic context signature really verifies',lambda context=context:t.verify(context['body'],context['signature'],'context',p.NAMESPACE) is None)
                check('held',case+' approval cannot grant contract clearance',lambda source=source,rid=rid:not e.is_contract_production_eligible(source,rid))
                check('held',case+' publication precondition rejects',lambda source=source,rid=rid:rejects(lambda:e.require_contract_actions(source,[rid]),'independent canon clearance'))
                check('held',case+' valid approval cannot make page eligible',lambda source=source,page=page,context=context:not p.is_page_publication_eligible(page,source,context))
                check('held',case+' guarded TEST review rejects',lambda source=source,page=page,context=context:rejects(lambda:test_review(page,source,context),'independent canon clearance'))
                check('held',case+' signed neighbour grants no endorsed IDs',lambda source=source:e.inventory(source)['publication_endorsed_contracts']==[])

    with patch.dict(os.environ,{'BTS_REVIEW_ENVIRONMENT':'production','BTS_REVIEW_STORE':'','BTS_PRODUCTION_TRUST_SHA256':''}):
        import corpus
        posts=json.loads((p.ROOT/'content/posts.json').read_text())
        public=corpus.public_posts(posts)
        hubs=json.loads((p.ROOT/'content/category-hubs.json').read_text())
        surfaces=[('guide:'+x['slug'],x) for x in public]+[('hub:'+k,x) for k,x in hubs.items()]
        check('public','204 public source surfaces',lambda:len(surfaces)==204)
        approved=json.loads((p.ROOT/'scripts/fixtures/wp3c9k_r4_reconciliation.json').read_text())['approved_phone']
        check('public','exact approved phone is the only migrated surface',lambda:
              [i for i,x in surfaces if 'reporting_routes' in x]==['hub:phone']
              and s.digest(hubs['phone'])==approved['source_sha256'])
        check('public','zero publication-eligible public surfaces',lambda:all(not p.is_page_publication_eligible(x,c,page_id=i) for i,x in surfaces))
        check('public','unconfigured deployment verifier holds',lambda:rejects(lambda:pilot.netlify_verify(p.ROOT)))
    return rows


def run_cases():
    c=canon.load_canon()
    rows=[dict(group='actual_model_pin',name='R6B2 real pin permits exactly six reviewed IDs',
        ok=e.REVIEWED_MODEL_SHA256==s.contract_model_sha256()
           and set(e.contract_production_eligible_ids(c))==set(EXPECTED_IDS)
           and set(e.REVIEWED_CONTRACT_IDS)==set(EXPECTED_IDS),detail='')]
    rows += _accepted_compatibility_cases()
    rows.append(dict(group='actual_model_pin',name='six-only actual eligibility preserved after hostile cases',
        ok=set(e.contract_production_eligible_ids(c))==set(EXPECTED_IDS),detail=''))
    return rows


if __name__=='__main__':
    rows=run_cases();out={'passed':sum(r['ok'] for r in rows),'total':len(rows),
        'groups':{g:{'passed':sum(r['ok'] for r in rows if r['group']==g),'total':sum(r['group']==g for r in rows)} for g in sorted({r['group'] for r in rows})},
        'failures':[r for r in rows if not r['ok']], 'authority':'disposable TEST fixtures; actual six-only compatibility pin; no positive pin mock'}
    print(json.dumps(out,indent=2));raise SystemExit(bool(out['failures']))
