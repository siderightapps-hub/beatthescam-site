#!/usr/bin/env python3
"""WP3C9F real-canon fidelity and unsigned fail-closed regressions.

No signing, trust enrollment, network, production content mutation or build.
The checked-in literal oracle was extracted from WP3D9E, not current renderers.
This suite checks fidelity and signed publication prerequisites; the F2 suite
separately checks unsigned contract eligibility.
"""
import argparse
import copy
from collections import Counter
from dataclasses import asdict
from html.parser import HTMLParser
import json
from pathlib import Path

import canon
import reporting_actions as v
import reporting_structured as s
import reporting_eligibility as e
import reporting_publication as publication
import reporting_contracts as legacy
from reporting_action_canon import destination_identity
from reporting_action_render import components, block, placement, faq_projection

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/'scripts/fixtures/wp3d9e_confirmed_contracts.json'
EXPECTED_IDS=(
    'citizens-advice:consumer-advice-english', 'victim-support:supportline',
    'o2-pay-monthly:customer-support', 'o2-payg:customer-support',
    'own-bank:number-on-bank-card', 'own-bank:existing-bank-app',
)
HELD=('C01','C04','C05','C06','M05','M04')

def record(c, rid):
    return next(r for group in s._GROUPS for r in c.get(group,[]) if r['key']==rid.split(':')[0])

def definition(c, rid):
    return record(c,rid)['actions'][rid.split(':',1)[1]]

def rejects(fn, reason=None):
    try:fn()
    except (ValueError,OSError) as exc:return reason is None or reason in str(exc)
    return False

class Tags(HTMLParser):
    def __init__(self):super().__init__();self.tags=[]
    def handle_starttag(self, tag, attrs):self.tags.append((tag,dict(attrs)))

def run_cases():
    rows=[];c=canon.load_canon();oracle=json.loads(ORACLE.read_text());cat=s.catalog_from_canon(c)
    metadata=c['contract_evidence']
    def check(group,name,fn):
        try:ok=bool(fn());detail='' if ok else 'assertion false'
        except Exception as exc:ok=False;detail=type(exc).__name__+': '+str(exc)
        rows.append(dict(group=group,name=name,ok=ok,detail=detail))
    def mutate(rid,path,value,delete=False):
        changed=copy.deepcopy(c);obj=definition(changed,rid)
        for key in path[:-1]:obj=obj[key]
        if delete:del obj[path[-1]]
        else:obj[path[-1]]=value
        return changed

    check('canon','exact six explicit IDs',lambda:set(cat.actions)==set(EXPECTED_IDS))
    check('compatibility','R6B2 actual model pin retains exactly six contracts',lambda:set(e.contract_production_eligible_ids(c))==set(EXPECTED_IDS) and set(e.REVIEWED_CONTRACT_IDS)==set(EXPECTED_IDS))
    check('provenance','exact implementation allowlist',lambda:oracle['allowlist']==list(EXPECTED_IDS)==metadata['implementation_allowlist'])
    check('provenance','two full/four narrower A3/B3',lambda:Counter(r['grade'] for r in metadata['contracts'].values())=={'A':3,'B':3}
          and sum(r['disposition'].startswith('A.') for r in metadata['contracts'].values())==2)
    check('provenance','independent review hashes preserved',lambda:oracle['review_documents']==metadata['review_documents'])
    check('eligibility','unsigned real production endorsement set remains empty',lambda:e.eligible_ids(c)==())
    check('eligibility','no unexpected eligible contract',lambda:not set(e.eligible_ids(c))-set(EXPECTED_IDS))
    check('provenance','audit metadata has no authority fields',lambda:metadata['version']=='bts-independent-contract-records/v1'
          and not {'signature','body','reviewer','public_key'} & set(metadata))
    for rid in EXPECTED_IDS:
        ref=oracle['contracts'][rid];a=cat.resolve(rid);d=definition(c,rid);entry=metadata['contracts'][rid]
        expected=copy.deepcopy(ref['reviewed_definition'])
        next(iter(expected['actions'].values()))['status']='active'
        expected_action=s.catalog_from_canon({'official_routes':[expected]}).resolve(rid)
        check('canon',rid+' exact independent resolved semantics',lambda a=a,expected_action=expected_action:asdict(a)==asdict(expected_action))
        check('provenance',rid+' grade/source/scope/binding',lambda entry=entry,ref=ref,a=a:
            (entry['grade'],entry['disposition'],entry['source_ids'],entry['scope'])==(ref['grade'],ref['disposition'],ref['source_ids'],ref['scope'])
            and entry['resolved_action_sha256']==s.digest(asdict(a)))
        check('provenance',rid+' complete primary field references',lambda entry=entry:
            all(set(f.get('source_ids',[]))<=set(metadata['sources']) for f in entry['supported_fields'].values())
            and all(metadata['sources'][sid]['retrieval_date']=='2026-10-14' and metadata['sources'][sid]['owner'] and metadata['sources'][sid]['title'] for sid in entry['source_ids']))
        node=components(cat,[rid])[0];html=node.html();plain=node.plain()
        check('renderer',rid+' literal independent text',lambda plain=plain,ref=ref:plain==ref['expected_text'])
        check('renderer',rid+' all material qualifiers and limits',lambda a=a,plain=plain:
            all(v.QUALIFIERS[q][0] in plain for q in a.qualifier_ids) and all(v.LIMITATIONS[l] in plain for l in a.limitation_ids)
            and all(v.ELIGIBILITY[x] in plain for x in a.eligibility_ids))
        check('renderer',rid+' summary/FAQ preserve complete action',lambda rid=rid,plain=plain:
            placement({'kind':'action-summary','route_ids':[rid]},[rid],cat)[0].plain()==plain
            and faq_projection([{'kind':'action-faq','question_id':'how-to-contact','route_ids':[rid]}],[rid],cat)[1][0][1]==plain)
        check('renderer',rid+' labelled accessible support block',lambda rid=rid:'aria-labelledby="reporting-routes-heading"' in block(cat,[rid]))
        check('renderer',rid+' no internal evidence notes',lambda html=html:'reviewer_notes' not in html and 'WP3D9E' not in html and 'Audit provenance' not in html)
        check('eligibility',rid+' unsigned packet rejected specifically',lambda rid=rid:rejects(lambda:e.verify_contract(c,rid,packet={}), 'missing signed contract evidence'))
        check('approval_binding',rid+' every action field hashed',lambda a=a,rid=rid:e.claims(c,rid)['contract_sha256']==s.digest(asdict(a)))
        check('approval_binding',rid+' whole canon/provenance hashed',lambda rid=rid:e.claims(c,rid)['canon_sha256']==s.digest(c))
        for version in ('restricted-actions/v1','restricted-actions/v99'):
            check('schema',rid+' rejects '+version,lambda rid=rid,version=version:rejects(lambda:s.catalog_from_canon(mutate(rid,['schema_version'],version)),'schema'))
        for field in ('schema_version','condition_ids','eligibility_ids','qualifier_ids','instruction','limitation_ids'):
            check('schema',rid+' missing '+field,lambda rid=rid,field=field:rejects(lambda:s.catalog_from_canon(mutate(rid,[field],None,True))))
        changed=copy.deepcopy(c);changed['contract_evidence']['contracts'][rid]['reviewer_notes']+=' altered'
        check('approval_binding',rid+' evidence mutation changes canon identity',lambda changed=changed,rid=rid:e.claims(changed,rid)['canon_sha256']!=e.claims(c,rid)['canon_sha256'])
        check('renderer',rid+' evidence mutation is non-rendered',lambda changed=changed,rid=rid:s.render_plain(s.catalog_from_canon(changed),[rid])==s.render_plain(cat,[rid]))

    # Precise support scope cannot be promoted into formal fraud reporting.
    for rid in EXPECTED_IDS[:4]:
        for key,value in [('action_type','report'),('purpose','police-report'),('mode','intake')]:
            check('purpose',rid+' refuses '+key,lambda rid=rid,key=key,value=value:rejects(lambda:s.catalog_from_canon(mutate(rid,[key],value))))
    for rid in EXPECTED_IDS[2:4]:
        other='o2-payg-origin' if rid.startswith('o2-pay-monthly:') else 'o2-pay-monthly-origin'
        changed=mutate(rid,['eligibility_ids'],[other])
        # This is a structurally representable factual neighbour; it MUST have a different evidence identity.
        check('o2',rid+' opposite plan cannot reuse contract identity',lambda changed=changed,rid=rid:e.claims(changed,rid)['contract_sha256']!=e.claims(c,rid)['contract_sha256'])
        check('o2',rid+' generic eligibility fails',lambda rid=rid:rejects(lambda:s.catalog_from_canon(mutate(rid,['eligibility_ids'],['existing-customer']))))
        check('o2',rid+' both plans fail',lambda rid=rid:rejects(lambda:s.catalog_from_canon(mutate(rid,['eligibility_ids'],['o2-payg-origin','o2-pay-monthly-origin']))))
    check('o2','two voice codes remain different identities',lambda:destination_identity(cat.resolve(EXPECTED_IDS[2]).channels[0],'GB','o2-uk')!=destination_identity(cat.resolve(EXPECTED_IDS[3]).channels[0],'GB','o2-uk'))
    check('o2','Platinum only monthly',lambda:'Platinum' in s.render_plain(cat,[EXPECTED_IDS[2]]) and 'Platinum' not in s.render_plain(cat,[EXPECTED_IDS[3]]))

    for rid in EXPECTED_IDS[4:]:
        check('bank',rid+' no fixed endpoints or links',lambda rid=rid:not cat.resolve(rid).channels and '<a ' not in components(cat,[rid])[0].html())
        for field,value in [('phone','01234 567890'),('report_url','https://attacker.invalid/'),('info_url','https://attacker.invalid/app'),('email','x@attacker.invalid')]:
            changed=copy.deepcopy(c);record(changed,rid)[field]=value
            check('bank',rid+' reject fixed '+field,lambda changed=changed:rejects(lambda:s.catalog_from_canon(changed),'fixed destination'))
        for key,value in [('destination','01234 567890'),('url','https://attacker.invalid/'),('app_link','https://attacker.invalid/app'),('fallback','web-search'),('recipient_relation','receiving-bank'),('recipient_relation','service-operator'),('role','arbitrary-bank')]:
            check('bank',rid+' reject '+key+'='+value,lambda rid=rid,key=key,value=value:rejects(lambda:s.catalog_from_canon(mutate(rid,['instruction',key],value))))
        for conditions in ([],['money-sent'],['account-at-risk']):
            check('bank',rid+' reject trigger '+repr(conditions),lambda rid=rid,conditions=conditions:rejects(lambda:s.catalog_from_canon(mutate(rid,['condition_ids'],conditions))))
        for actor in ([],['existing-customer'],['recipient-mobile-line']):
            check('bank',rid+' reject audience '+repr(actor),lambda rid=rid,actor=actor:rejects(lambda:s.catalog_from_canon(mutate(rid,['eligibility_ids'],actor))))
        for key,value in [('key','another-bank'),('owner_id','receiving-bank'),('name','Receiving bank'),('brand','Another bank')]:
            changed=copy.deepcopy(c);record(changed,rid)[key]=value
            check('bank',rid+' reject owner '+key,lambda changed=changed:rejects(lambda:s.catalog_from_canon(changed),'role envelope'))
    card,app=EXPECTED_IDS[4:]
    check('bank','separate methods/plans',lambda:cat.resolve(card).template_id!=cat.resolve(app).template_id and s.action_plan_sha256(cat,[card])!=s.action_plan_sha256(cat,[app]))
    check('bank','no implicit fallback or companions',lambda:not cat.resolve(card).companions and not cat.resolve(app).companions and 'app' not in s.render_plain(cat,[card]).lower() and 'card' not in s.render_plain(cat,[app]).lower())

    # Legacy identities, similar evidence and extra metadata confer no capability.
    check('held','six exact holds and reasons preserved',lambda:set(metadata['held_cases'])==set(HELD) and metadata['held_cases']==oracle['held_cases'])
    for cid,held in oracle['held_cases'].items():
        service=held['source_bundle'].split(':')[0]
        check('held',cid+' absent from production catalog',lambda service=service:not any(r.startswith(service+':') for r in cat.actions))
        check('held',cid+' exact missing reason retained',lambda cid=cid:bool(metadata['held_cases'][cid]['unresolved_fields']))
        rid=service+':review-case'
        check('held',cid+' selection fails',lambda rid=rid:rejects(lambda:cat.select([rid])))
        check('held',cid+' renderer fails',lambda rid=rid:rejects(lambda:components(cat,[rid])))
        check('held',cid+' generator descriptor fails',lambda rid=rid:rejects(lambda:s.generator_contract(cat,[rid])))
    for service in ('action-fraud','police-scotland','slc-phishing','amazon','yodel','own-mobile-provider','o2'):
        check('held','unrelated '+service+' not selectable',lambda service=service:rejects(lambda:cat.select([service+':report'])))
    changed=copy.deepcopy(c);changed['contract_evidence']['production_eligible']=list(EXPECTED_IDS)+['ncsc-sers:report']
    check('held','forged metadata eligibility grants nothing',lambda:e.eligible_ids(changed)==())
    changed=copy.deepcopy(c);changed['contract_evidence']['contracts']['ncsc-sers:report']=copy.deepcopy(metadata['contracts'][EXPECTED_IDS[0]])
    check('held','copied evidence metadata creates no action',lambda:set(s.catalog_from_canon(changed).actions)==set(EXPECTED_IDS) and e.eligible_ids(changed)==())

    # Collision/escaping controls exercise real new records with valid controls above.
    changed=copy.deepcopy(c);dup=copy.deepcopy(record(c,EXPECTED_IDS[0]));dup.update(key='different-owner',owner_id='different-owner',brand='Different owner');changed['verified_org_contacts'].append(dup)
    check('collision','normalized phone different owner rejects',lambda:rejects(lambda:s.catalog_from_canon(changed),'collision'))
    changed=copy.deepcopy(c);changed['verified_org_contacts'].append(copy.deepcopy(record(c,EXPECTED_IDS[0])))
    check('collision','duplicate service/action identity rejects',lambda:rejects(lambda:s.catalog_from_canon(changed),'duplicate service'))
    changed=copy.deepcopy(c);record(changed,EXPECTED_IDS[1])['name']='Support <img src=x> & help'
    check('renderer','service label escaped',lambda:'<img ' not in s.render_block(s.catalog_from_canon(changed),[EXPECTED_IDS[1]]) and '&lt;img' in s.render_block(s.catalog_from_canon(changed),[EXPECTED_IDS[1]]))
    for rid in EXPECTED_IDS:
        parser=Tags();parser.feed(components(cat,[rid])[0].html())
        check('renderer',rid+' no scripts/forms/event handlers',lambda parser=parser:not any(tag in ('script','form','input','iframe') or any(k.startswith('on') for k in attrs) for tag,attrs in parser.tags))
    check('generator','actual eligible interface empty',lambda:s.generator_contract(cat,e.eligible_ids(c))['allowed_reporting_routes']==[])
    # Future descriptor shape is checked explicitly as schema data, not production eligibility.
    descriptor=s.generator_contract(cat,list(EXPECTED_IDS))
    check('generator','six descriptor IDs, no endpoint/authority override',lambda:set(descriptor['allowed_reporting_routes'])==set(EXPECTED_IDS) and not any(x in json.dumps(descriptor) for x in ('0808 223 1133','0808 168 9111','signature','reviewer_notes')))
    posts=json.loads((ROOT/'content/posts.json').read_text());hubs=json.loads((ROOT/'content/category-hubs.json').read_text())
    hub_values=list(hubs.values()) if isinstance(hubs,dict) else hubs
    if isinstance(hubs,dict) and 'hubs' in hubs:hub_values=list(hubs['hubs'].values()) if isinstance(hubs['hubs'],dict) else hubs['hubs']
    # R11 intentionally migrated only the exact owner-approved phone source.
    approved=json.loads((ROOT/'scripts/fixtures/wp3c9k_r4_reconciliation.json').read_text())['approved_phone']
    check('content','exact R11 phone is the only migrated public record',lambda:
          all('reporting_routes' not in r for r in posts)
          and [k for k,r in hubs.items() if 'reporting_routes' in r]==['phone']
          and s.digest(hubs['phone'])==approved['source_sha256']
          and hubs['phone']['reporting_routes']==approved['route_ids'])
    # These three services cannot be represented by the older prose relation.
    # Their explicit denial must not silently expand its destination allowlist.
    legacy_contracts=legacy.contracts_from_canon(c)
    before=copy.deepcopy(c)
    before['verified_org_contacts']=[r for r in before['verified_org_contacts'] if r['key'] not in ('o2-pay-monthly','o2-payg','own-bank')]
    check('legacy','new services confer no legacy capability',lambda:legacy.contracts_from_canon(before)==legacy_contracts)
    for rid in EXPECTED_IDS[2:]:
        check('legacy',rid+' has no unqualified legacy service',lambda rid=rid:all(x.service!=rid.split(':')[0] for x in legacy_contracts))
    for number in ('202','4445'):
        request=legacy.Request(legacy.normalize('phone',number),frozenset({'o2'}),frozenset({'account-support'}))
        check('legacy',number+' cannot bypass plan/network restrictions',lambda request=request:not legacy.authorize(request,legacy_contracts)[0])
    unknown=copy.deepcopy(c);unknown['verified_org_contacts'].append({'key':'unreviewed-service'})
    check('legacy','unknown service still fails closed',lambda:rejects(lambda:legacy.contracts_from_canon(unknown),'Missing reporting service contract'))
    return rows

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--json',type=Path);args=parser.parse_args()
    rows=run_cases();passed=sum(r['ok'] for r in rows)
    out={'suite':'confirmed-contracts','passed':passed,'total':len(rows),'groups':{g:{'passed':sum(r['ok'] for r in rows if r['group']==g),'total':sum(r['group']==g for r in rows)} for g in sorted({r['group'] for r in rows})},'rows':rows,'signatures_created':0,'interpretation':'Six represented real contracts; production publication endorsements remain absent without signed evidence. Contract eligibility is tested separately.'}
    if args.json:args.json.write_text(json.dumps(out,indent=2)+'\n')
    for r in rows:
        if not r['ok']:print('FAIL',r['group'],r['name'],r['detail'])
    print(f'{passed}/{len(rows)} passed')
    return int(passed!=len(rows))

if __name__=='__main__':raise SystemExit(main())
