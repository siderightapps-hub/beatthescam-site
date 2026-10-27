#!/usr/bin/env python3
"""WP3C9D2 synthetic v2 cases, never production evidence or approvals.

C01–C09 are the nine design cases. M04/M05/M10 are the expressly approved
conditional restrictions, not three extra cleared cases. M07 remains absent.
Expected tuples below are independently stated, not generated from registries.
"""
import copy
from collections import Counter
from datetime import date
from dataclasses import asdict
import json
from pathlib import Path
import reporting_actions as v
import reporting_structured as s
from reporting_action_canon import destination_identity
from reporting_action_render import components, faq_projection, placement
from reporting_structured_selftest import action, fixture_canon, Links

# type, method, purpose, mode, field, kind, conditions, eligibility, qualifiers,
# limits, payload. All endpoints/owners below are disposable fixture data.
CASES = {
 'C01': ('forward','forward-email','phishing-report','intake','email','email',
    ['suspicious-email'], [], [], ['evidence-only','no-individual-outcome-feedback'], 'original-email'),
 'C02': ('call','call-consumer-advice-english','consumer-advice','support','phone','phone',
    [], ['consumer-seeking-advice'], ['free-uk-phone-call','weekday-0900-1700-excluding-bank-holidays'], ['support-only'], None),
 'C03': ('call','call-victim-support','victim-support','support','phone','phone',
    [], ['person-affected-by-crime'], ['free-uk-phone-call','support-24-hours-every-day','no-police-report-needed'], ['support-only'], None),
 'C04': ('forward','forward-brand-email','phishing-report','intake','email','email',
    ['suspicious-email','email-claims-service-brand'], [], [], ['evidence-only'], 'original-email'),
 'C05': ('forward','forward-brand-reference-email','phishing-report','intake','email','email',
    ['suspicious-email','email-refers-to-service-brand'], [], [], ['evidence-only'], 'original-email'),
 'C06': ('email','email-original-file','phishing-report','intake','email','email',
    ['suspicious-email','email-claims-service-brand'], [], [], ['evidence-only'], 'original-email-file-with-phishing-example-subject'),
 'C07': ('call','call-o2-personal-support','account-support','support','phone','voice-shortcode',
    [], ['o2-pay-monthly-origin'], ['free-from-required-o2-phone','o2-personal-support-hours'], ['support-only'], None),
 'C08': ('call','call-o2-personal-support','account-support','support','phone','voice-shortcode',
    [], ['o2-payg-origin'], ['free-from-required-o2-phone','o2-personal-support-hours'], ['support-only'], None),
 'C09': ('contact','number-on-bank-card','payment-recovery','support',None,None,
    ['suspected-authorised-bank-transfer-to-fraudster'], ['sender-own-account'], [], ['no-money-recovery-guarantee'], None),
 'M04': ('forward','forward-unanswered-email','phishing-report','intake','email','email',
    ['suspicious-email','not-responded-to-email'], [], [], ['evidence-only'], 'original-email'),
 'M05': ('report','report-caller-number-sms','suspicious-call-report','intake','sms','shortcode',
    ['suspicious-mobile-call'], ['recipient-mobile-line'], ['free-sms-to-provider'], ['no-refund-promise'], 'caller-number-from-recent-calls-sms'),
 'M10': ('contact','existing-bank-app','payment-recovery','support',None,None,
    ['suspected-authorised-bank-transfer-to-fraudster','banking-device-safe'], ['sender-own-account'], [], ['no-money-recovery-guarantee'], None),
}
TRACEABILITY = {'M01':['C07','C08'], 'M02':['C02','C03'], 'M04':['C04','C05','C06'],
    'M05':['C04','C05','C06','C09'], 'M10':['C09']}
# M05's payload/recipient containers are shared with the nine; its SMS method
# is the approved conditional exception. M10 restricts C09's existing sibling
# app method. Neither is claimed to be one of the nine representation cases.


def case_fixture(case):
    c = fixture_canon(); record = c['verified_org_contacts'][-1]
    atype,method,purpose,mode,field,kind,conditions,eligible,qualifiers,limits,payload = copy.deepcopy(CASES[case])
    record['checked_on'] = date.today().isoformat()
    record['note'] = 'INTERNAL EVIDENCE NOTE: Call an unreviewed service; never render this note.'
    inst = {'kind':'fixed-destination','template_id':method,'recipient_relation':'service-operator',
            'channels':[{'field':field,'kind':kind}]}
    if payload: inst['payload_profile_id'] = payload
    if kind == 'voice-shortcode':
        record['phone'] = '202' if case=='C07' else '4445'
        inst['channels'][0].update(numbering_context='GB',dialling_network_id='o2-uk')
    if case in ('C09','M10'):
        record.update(key='own-bank',owner_id='own-bank',brand='Your own bank',name='Your own bank')
        for f in s._DEST_FIELDS: record.pop(f,None)
        inst = {'kind':'reader-held-channel','role':'own-bank','method_id':method,
                'recipient_relation':'sending-bank-of-affected-transfer'}
    elif case=='M05':
        record.update(key='own-mobile-provider',owner_id='own-mobile-provider',brand='Your mobile provider',name='Your mobile provider')
        inst['recipient_relation']='reader-mobile-provider'
    record['actions']={'case': {'schema_version':'restricted-actions/v2','action_type':atype,'purpose':purpose,'mode':mode,
        'jurisdictions':['England','Wales'] if case in ('C02','C03') else list(s._NATIONS[:4]),
        'condition_ids':conditions,'eligibility_ids':eligible,'qualifier_ids':qualifiers,'limitation_ids':limits,
        'instruction':inst,'companions':[],'status':'active'}}
    return c, record['key']+':case'


def template_fixture(template):
    for case, values in CASES.items():
        if values[1]==template: return case_fixture(case)
    c=fixture_canon(); rec=c['verified_org_contacts'][-1]
    atype,kind,purpose,mode,conditions,_,_=v.TEMPLATES[template]
    field={'url':'report_url','email':'email','phone':'phone','shortcode':'sms'}[kind]
    if template=='visit-verification': field='info_url';rec[field]=rec['report_url']
    if template=='open-verification': field='navigation_url';rec[field]=rec['report_url']
    rec['actions']={'case':action(field,kind,action_type=atype,purpose=purpose,mode=mode,
        condition_ids=list(conditions),eligibility_ids=['existing-customer'] if template in ('call-support','contact-support-web') else ['platform-account'] if template=='submit-platform' else [],
        instruction={'kind':'fixed-destination','template_id':template,'recipient_relation':'service-operator','channels':[{'field':field,'kind':kind}]},
        limitation_ids=['support-only'] if mode=='support' else ['no-refund-promise'])}
    return c,'fixture-service:case'


def definition(c): return c['verified_org_contacts'][-1]['actions']['case']


def rejects(fn, reason=None):
    try: fn()
    except ValueError as exc: return reason is None or reason in str(exc)
    return False


def run_cases():
    rows=[]
    def check(group,name,fn):
        try: ok=bool(fn()); detail='' if ok else 'assertion false'
        except Exception as exc: ok=False; detail=type(exc).__name__+': '+str(exc)
        rows.append(dict(group=group,name=name,ok=ok,detail=detail))
    def mutation(case,path,value,missing=False):
        c,_=case_fixture(case); d=definition(c)
        for key in path[:-1]: d=d[key]
        if missing: del d[path[-1]]
        else: d[path[-1]]=value
        return rejects(lambda:s.catalog_from_canon(c))
    for case in CASES:
        c,rid=case_fixture(case); cat=s.catalog_from_canon(c); a=cat.resolve(rid)
        check('validator',case+' exact tuple',lambda a=a: a.schema_version=='restricted-actions/v2')
        # Every new primitive participates in one of these complete cases.
        for key in ('schema_version','eligibility_ids','qualifier_ids','instruction','condition_ids','limitation_ids'):
            check('validator',case+' missing '+key,lambda case=case,key=key:mutation(case,[key],None,True))
        for key,value in [('action_type','send'),('purpose','emergency-response'),('mode','protection'),
                          ('jurisdictions',['UK']),('condition_ids',['generic-trigger']),('steps',['Call elsewhere']),
                          ('evidence_note','Call elsewhere'),('qualifier','Contact anyone')]:
            check('validator',case+' wrong '+key,lambda case=case,key=key,value=value:mutation(case,[key],value))
        for key in ('recipient_relation',):
            check('validator',case+' missing '+key,lambda case=case,key=key:mutation(case,['instruction',key],None,True))
        check('validator',case+' free payload body',lambda case=case:mutation(case,['instruction','body'],'CALL 123'))
        check('validator',case+' free destination',lambda case=case:mutation(case,['instruction','destination'],'https://evil.example'))
        check('schema',case+' v1 with v2 fields',lambda case=case:mutation(case,['schema_version'],'restricted-actions/v1'))
        check('schema',case+' future version',lambda case=case:mutation(case,['schema_version'],'restricted-actions/v99'))
        node=components(cat,[rid])[0]; html=node.html(); plain=node.plain()
        check('renderer',case+' no evidence note',lambda html=html: 'INTERNAL EVIDENCE' not in html and 'unreviewed service' not in html)
        check('renderer',case+' full summary and FAQ',lambda cat=cat,rid=rid,node=node:
            placement({'kind':'action-summary','route_ids':[rid]},[rid],cat)[0].html()==node.html()
            and faq_projection([{'kind':'action-faq','question_id':'where-to-report','route_ids':[rid]}],[rid],cat)[1][0][1]==node.plain())
        check('renderer',case+' all applicability and material qualifiers',lambda a=a,plain=plain:
            all(v.CONDITIONS[x].format(brand=a.owner) in plain for x in a.condition_ids)
            and all(v.ELIGIBILITY[x] in plain for x in a.eligibility_ids)
            and all(v.QUALIFIERS[x][0] in plain for x in a.qualifier_ids)
            and all(v.LIMITATIONS[x] in plain for x in a.limitation_ids))
        d=definition(c)
        for key in ('condition_ids','eligibility_ids','qualifier_ids'):
            if d[key]:
                # C01 no-feedback is an evidence requirement, tested by signatures in binding suite.
                check('validator',case+' remove required '+key,lambda case=case,key=key:mutation(case,[key],[]))
        if a.payload_profile_id:
            check('validator',case+' missing payload',lambda case=case:mutation(case,['instruction','payload_profile_id'],None,True))
        else:
            check('validator',case+' forbidden payload',lambda case=case:mutation(case,['instruction','payload_profile_id'],'original-email'))
    for case in ('C09','M10'):
        c,rid=case_fixture(case);cat=s.catalog_from_canon(c);plain=s.render_plain(cat,[rid])
        check('bank',case+' exact relevant-bank channel',lambda case=case,plain=plain:
            'bank that sent that transfer immediately' in plain and 'from your own account' in plain
            and ('printed on that bank&#x27;s card' in s.render_block(cat,[rid]) if case=='C09' else 'until it is safe' in plain))
        check('bank',case+' no invented endpoint',lambda cat=cat,rid=rid:not cat.destinations([rid]) and not Links(s.render_block(cat,[rid])).links)
        for path,value in [(['condition_ids'],['money-sent']),(['condition_ids'],['account-at-risk']),
            (['condition_ids'],['card-payment']),(['eligibility_ids'],['existing-customer']),
            (['instruction','recipient_relation'],'service-operator'),(['instruction','role'],'any-bank'),
            (['instruction','method_id'],'number-on-bank-statement'),(['instruction','method_id'],'search-for-bank'),
            (['instruction','channels'],[{'field':'phone','kind':'phone'}]),(['action_type'],'call'),
            (['limitation_ids'],['no-recovery-promise'])]:
            check('bank',case+str(path)+str(value),lambda case=case,path=path,value=value:mutation(case,path,value))
        bad=copy.deepcopy(c); bad['verified_org_contacts'][-1]['phone']='01234 567890'
        check('bank',case+' canon fixed endpoint override',lambda bad=bad:rejects(lambda:s.catalog_from_canon(bad)))
    check('bank','app cannot omit safe-device predicate',lambda:mutation('M10',['condition_ids'],['suspected-authorised-bank-transfer-to-fraudster']))
    check('bank','card cannot absorb app predicate',lambda:mutation('C09',['condition_ids'],['suspected-authorised-bank-transfer-to-fraudster','banking-device-safe']))
    for path,value in [(['action_type'],'forward'),(['instruction','template_id'],'forward-text'),
            (['condition_ids'],['suspicious-text']),(['instruction','payload_profile_id'],'original-email'),
            (['instruction','recipient_relation'],'service-operator'),(['eligibility_ids'],['existing-customer']),
            (['instruction','channels',0,'kind'],'voice-shortcode'),(['instruction','prefix'],'CALL'),
            (['instruction','payload_profile_id'],'transfer-reference')]:
        check('ofcom',str(path)+str(value),lambda path=path,value=value:mutation('M05',path,value))
    c,rid=case_fixture('M05');plain=s.render_plain(s.catalog_from_canon(c),[rid])
    check('ofcom','composed caller object, own provider, no message forwarding',lambda:
        'number from recent calls' in plain and 'new SMS containing that caller number' in plain
        and 'your mobile provider' in plain and 'Forward' not in plain and 'original' not in plain
        and 'CALL' not in plain and 'Ofcom' not in plain)
    # All five new registries: every member admitted in a compatible fixture.
    seen={name:set() for name in ('ELIGIBILITY','QUALIFIERS','RECIPIENT_RELATIONS','PAYLOAD_PROFILES','DIALLING_NETWORKS')}
    for case in CASES:
        c,rid=case_fixture(case);a=s.catalog_from_canon(c).resolve(rid)
        for name,values in [('ELIGIBILITY',a.eligibility_ids),('QUALIFIERS',a.qualifier_ids),
            ('RECIPIENT_RELATIONS',[a.recipient_relation]),('PAYLOAD_PROFILES',[a.payload_profile_id] if a.payload_profile_id else []),
            ('DIALLING_NETWORKS',[a.dialling_network_id] if a.dialling_network_id else [])]: seen[name].update(values)
    for method,extra in [('call-support',[]),('submit-platform',[]),('submit-platform',['adult']),('submit-platform',['minor'])]:
        c,rid=template_fixture(method);definition(c)['eligibility_ids']+=extra
        a=s.catalog_from_canon(c).resolve(rid);seen['ELIGIBILITY'].update(a.eligibility_ids)
    for name in seen:
        for value in getattr(v,name):
            check('registry',name+' known '+value,lambda name=name,value=value:value in seen[name])
    registry_cases=[('ELIGIBILITY','C02',['eligibility_ids'],'consumer-seeking-advice',True),
        ('QUALIFIERS','C02',['qualifier_ids'],'free-uk-phone-call',True),
        ('RECIPIENT_RELATIONS','C04',['instruction','recipient_relation'],'service-operator',False),
        ('PAYLOAD_PROFILES','C04',['instruction','payload_profile_id'],'original-email',False),
        ('DIALLING_NETWORKS','C07',['instruction','channels',0,'dialling_network_id'],'o2-uk',False)]
    for name,case,path,known,is_list in registry_cases:
        bad_values=['unknown',known.upper(),' '+known,known+' ','',None,False,17,{},[],
                    next(iter(v.PAYLOAD_PROFILES)) if name!='PAYLOAD_PROFILES' else next(iter(v.ELIGIBILITY))]
        for value in bad_values:
            check('registry',name+' rejects '+repr(value),lambda case=case,path=path,value=value,is_list=is_list:
                mutation(case,path,[value] if is_list else value))
        if is_list:
            for value in (known,{},None,False,[known,known],[known]*9):
                check('registry',name+' malformed list '+repr(value),lambda case=case,path=path,value=value:mutation(case,path,value))
    for case in ('C07','C08'):
        for key,value in [('phone','+202'),('phone','２０２'),('phone','20'),('phone','1234567'),('phone','2 02')]:
            c,_=case_fixture(case);c['verified_org_contacts'][-1][key]=value
            check('voice',case+' canonical '+value,lambda c=c:rejects(lambda:s.catalog_from_canon(c)))
        for path,value in [(['instruction','channels',0,'field'],'sms'),(['instruction','channels',0,'field'],'phone_welsh'),
            (['instruction','channels',0,'kind'],'phone'),(['instruction','channels',0,'numbering_context'],'international'),
            (['eligibility_ids'],['o2-pay-monthly-origin','o2-payg-origin']),(['qualifier_ids'],['support-24-hours-every-day'])]:
            check('voice',case+str(path)+str(value),lambda case=case,path=path,value=value:mutation(case,path,value))
        c,rid=case_fixture(case);html=s.render_block(s.catalog_from_canon(c),[rid])
        check('voice',case+' no tel link and scoped hours',lambda case=case,html=html:
            'tel:' not in html and '08:00–21:00' in html and ('Platinum' in html)==(case=='C07'))
    check('voice','numeric namespace separation',lambda:destination_identity(s.Destination('voice-shortcode','202'),'GB','o2-uk')!=destination_identity(s.Destination('shortcode','202'),'GB'))
    for case in ('C01','C02','C09'):
        check('validator',case+' network forbidden elsewhere',lambda case=case:mutation(case,['instruction','dialling_network_id'],'o2-uk'))
    c,rid=case_fixture('C06');plain=s.render_plain(s.catalog_from_canon(c),[rid]);html=s.render_block(s.catalog_from_canon(c),[rid])
    check('renderer','original file procedure exact ordered steps',lambda:'<ol><li>Save the original email as a message file.' in html
        and 'not an attachment contained inside it' in plain and 'Create a new email' in plain
        and 'phishing email example' in plain and 'Attach that saved message file and send the new email.' in plain)
    # Relative-role names and identities cannot be article/canon aliases.
    for case in ('C09','M05'):
        for key,value in [('key','attacker'),('owner_id','attacker'),('brand','Attacker Bank'),('name','Attacker Service')]:
            c,_=case_fixture(case);c['verified_org_contacts'][-1][key]=value
            check('adversarial',case+' locked role '+key,lambda c=c:rejects(lambda:s.catalog_from_canon(c),'role envelope'))
    c,_=case_fixture('C09');c['verified_org_contacts'][-1]['phone']=None
    check('bank','even empty destination override forbidden',lambda:rejects(lambda:s.catalog_from_canon(c),'fixed destination'))
    for case in ('C02','C04','C07','M05'):
        c,rid=case_fixture(case);cat=s.catalog_from_canon(c);rec=c['verified_org_contacts'][-1]
        # A declared second fixed owner cannot silently reuse an endpoint, even
        # in the new voice namespace or against a provider-relative recipient.
        other=copy.deepcopy(rec);other.update(key='second-fixture',owner_id='second-owner',brand='Other Owner',name='Other Service')
        if case=='M05':
            other['actions']['case']=action('sms','shortcode')
        c['verified_org_contacts'].append(other)
        check('collision',case+' duplicate endpoint needs explicit relationship',lambda c=c:rejects(lambda:s.catalog_from_canon(c),'collision'))
    c,rid=case_fixture('C07');cat=s.catalog_from_canon(c);a=cat.resolve(rid)
    for scenario in ('voice-to-sms-alias','relative-operator'):
        base_case='C07' if scenario=='voice-to-sms-alias' else 'M05'
        c,rid=case_fixture(base_case);rec=c['verified_org_contacts'][-1]
        other=copy.deepcopy(rec);other.update(key='second-fixture',owner_id='second-owner',brand='Other Owner',name='Other Service')
        other['sms']=rec['phone'] if scenario=='voice-to-sms-alias' else rec['sms']
        other['actions']={'case':action('sms','shortcode')}
        left=s.catalog_from_canon({'verified_org_contacts':[rec]}).resolve(rid)
        right=s.catalog_from_canon({'verified_org_contacts':[other]}).resolve('second-fixture:case')
        c['verified_org_contacts'].append(other)
        c['destination_relationships']=[{'id':'fixture-relationship',
            'type':'alias' if scenario=='voice-to-sms-alias' else 'shared-service',
            'operator_owner_id':left.owner_id,'attribution_id':'operated-by','status':'active',
            'source_url':'https://routes.example/evidence','checked_on':date.today().isoformat(),
            'members':[{'route_id':a.route_id,'owner_id':a.owner_id,'purpose':a.purpose,
                'jurisdictions':list(a.jurisdictions),'destination_field':a.destination_field,
                'destination_identity':list(destination_identity(a.channels[0],a.numbering_context,a.dialling_network_id))} for a in (left,right)]}]
        check('collision',scenario,lambda c=c,scenario=scenario:rejects(lambda:s.catalog_from_canon(c),
            'cross-kind' if scenario=='voice-to-sms-alias' else 'relative recipient cannot'))
    # Every field-level numeric override remains forbidden on nonvoice methods.
    for case in ('C01','C02','M05'):
        check('validator',case+' nested network forbidden',lambda case=case:mutation(case,['instruction','channels',0,'dialling_network_id'],'o2-uk'))
    # Existing moved eligibility is not an event, nor a license to add new ages.
    c,rid=template_fixture('submit-platform');definition(c)['eligibility_ids']=['platform-account','adult','minor']
    check('validator','conflicting ages',lambda:rejects(lambda:s.catalog_from_canon(c)))
    for value in ('existing-customer','adult','minor','platform-account'):
        check('validator','old eligibility in condition category '+value,lambda value=value:mutation('C02',['condition_ids'],[value]))
    # Unordered ID lists normalize for Action/plan identity; display order is fixed.
    c,rid=case_fixture('C06');other=copy.deepcopy(c);definition(other)['condition_ids'].reverse()
    check('schema','normalized unordered ID sets',lambda:s.action_plan_sha256(s.catalog_from_canon(c),[rid])==s.action_plan_sha256(s.catalog_from_canon(other),[rid]))
    c,rid=template_fixture('call-support');definition(c)['limitation_ids']=['no-recovery-promise']
    check('validator','unextended support retains historical scope option',lambda:'Recovery of money or removal of content is not guaranteed.' in s.render_plain(s.catalog_from_canon(c),[rid]))
    check('validator','duplicate JSON keys',lambda:rejects(lambda:json.loads('{"schema_version":"restricted-actions/v2","schema_version":"restricted-actions/v1"}',object_pairs_hook=s.unique_object)))
    check('validator','no extra types or deferred emergency purpose',lambda:{x[0] for x in v.TEMPLATES.values()}=={'report','contact','call','email','forward','submit','visit','open'} and 'emergency-response' not in v.PURPOSES and len(v.PAYLOAD_PROFILES)==3)
    return rows


if __name__=='__main__':
    rows=run_cases();print(json.dumps({'total':len(rows),'passed':sum(r['ok'] for r in rows),
        'groups':{g:{'passed':sum(r['ok'] for r in rows if r['group']==g),'total':sum(r['group']==g for r in rows)} for g in sorted({r['group'] for r in rows})},
        'failures':[r for r in rows if not r['ok']]},indent=2));raise SystemExit(any(not r['ok'] for r in rows))
