#!/usr/bin/env python3
"""WP3C9B boundary tests. Synthetic canon, external fixture key, no live calls."""
import copy
import json
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import tempfile
from datetime import datetime, timezone, timedelta
import canon
import build
import content_gate as gate
import generate_content_claude as writer
import reporting_structured as s
import reporting_publication as publication
import reporting_eligibility as eligibility
from reporting_structured_selftest import fixture_canon, fixture_page, review_for, action, Links
from reporting_fixture_review import packet_for, sign_body, store
from reporting_action_canon import destination_identity
from reporting_action_render import components, ActionComponent
from reporting_output import ArticleText, ArticleHTML, Capability, Citation
from reporting_network import https_identity


def run_cases():
    rows = []
    c = fixture_canon(); p = fixture_page(); cat = s.catalog_from_canon(c)
    site = build.read_json(build.ROOT / 'content/site.json')

    def check(group, name, fn):
        try:
            ok = bool(fn()); detail = '' if ok else 'assertion false'
        except Exception as exc:
            ok = False; detail = type(exc).__name__ + ': ' + str(exc)
        rows.append(dict(group=group, name=name, ok=ok, detail=detail))

    def rejects(fn, reason=None):
        try:
            fn()
        except (ValueError, canon.CanonError, SystemExit) as exc:
            return reason is None or reason in str(exc)
        return False

    def approved(page, sources=c):
        r = review_for(page, sources, approved_fields=dict(s.approval_fields(page)))
        return r, packet_for(page, sources, r)

    positive = ['Scammers use urgency to discourage independent checks.',
        'A familiar logo is not proof of authenticity.', 'Reporting fraud helps investigators.',
        'Reporting the incident may help investigators.', 'Police recommend reporting sextortion promptly.',
        'Do not send more money.', 'A phishing email can create pressure.',
        'The police report records a rise in attempts.', 'A phone scam can appear convincing.']
    negative = ['Phoning your bank immediately is essential.', 'Using the source above is the recommended way to notify the authorities.', 'Report this to Organisation X.', 'Call Organisation X.', 'Email Organisation X.',
        'Forward the message.', 'Submit the evidence.', 'Visit the approved service.',
        'Open the official app.', 'Contact your bank immediately.', 'Dial the following figure.',
        'Upload the evidence.', 'Report using the source above.', 'Use the source above to report.',
        'Contact your bank if money has left your account.', 'Follow the internal guide and report there.',
        'Do not hesitate to call Organisation X.', 'Do not email them; instead forward the evidence.',
        'Reporting fraud helps investigators; call Organisation X.',
        'Police recommend reporting sextortion promptly. Forward the message.',
        'Phone scam investigators.', 'Email scams to the team.', 'Report through 0xcb00710a.',
        'Report through [::1].', 'Report through an undisclosed destination.']
    for text in positive:
        def test(text=text):
            page=fixture_page(); page['sections'][0][1]=text; r,pkt=approved(page)
            with patch.object(s, '_raw_destinations', return_value=[]):
                return bool(s.validate_page(page, cat, r)) and publication.review(page,c,pkt).page_sha256 == s.digest(page)
        check('prose', 'explanation '+text, test)
    for text in negative:
        for surface in ('sections', 'faq', 'quick_answer', 'description', 'citation'):
            def test(text=text, surface=surface):
                page=fixture_page()
                if surface=='sections':page['sections'][0][1]=text
                elif surface=='faq':page['faq'][0][1]=text
                elif surface=='citation':page['sources_checked']=[[text,'https://sources.example/evidence']]
                else:page[surface]=text
                r,pkt=approved(page)
                with patch.object(s, '_raw_destinations', return_value=[]):
                    return (rejects(lambda:s.validate_page(page,cat,r),'restricted action-authoring boundary')
                        and rejects(lambda:publication.review(page,c,pkt),'restricted action-authoring boundary'))
            check('prose', surface+' '+text, test)
    for markup in ('<p>Ca<em>ll</em> Organisation X.</p>', '<p>Re<code>port</code> using the source above.</p>'):
        check('prose','effective '+markup,lambda markup=markup:rejects(lambda:s.validate_effective(
            [ArticleHTML('sections/0/1',markup)],cat,review_for(p,c)),'restricted action-authoring boundary'))

    # Explicit expectations, independent of registry iteration.
    contracts = [
        ('report','report-phishing-web','phishing-report','intake','report_url','url',['suspicious-email']),
        ('contact','contact-support-web','account-support','support','report_url','url',['existing-customer']),
        ('call','call-support','account-support','support','phone','phone',['existing-customer']),
        ('email','email-evidence','phishing-report','intake','email','email',['suspicious-email']),
        ('forward','forward-email','phishing-report','intake','email','email',['suspicious-email']),
        ('forward','forward-text','phishing-report','intake','sms','shortcode',['suspicious-text']),
        ('submit','submit-platform','platform-report','intake','report_url','url',['platform-account','adult']),
        ('visit','visit-verification','site-verification','verification','info_url','url',[]),
        ('open','open-verification','site-verification','navigation','navigation_url','url',[])]
    for atype,template,purpose,mode,field,kind,conditions in contracts:
        cc=copy.deepcopy(c);rec=cc['verified_org_contacts'][-1];rec['info_url']=rec['navigation_url']=rec['report_url']
        definition=action(field,kind,action_type=atype,purpose=purpose,mode=mode,condition_ids=[x for x in conditions if x not in ('existing-customer','platform-account','adult')],
            eligibility_ids=[x for x in conditions if x in ('existing-customer','platform-account','adult')],
            instruction=dict(kind='fixed-destination',template_id=template,channels=[{'field':field,'kind':kind}],
                recipient_relation='service-operator', **({'payload_profile_id':'original-email'} if template=='forward-email' else {})),
            limitation_ids=['support-only'] if mode=='support' else ['no-refund-promise'])
        rec['actions']={'case':definition};catalog=s.catalog_from_canon(cc)
        def render_test(catalog=catalog,rec=rec,field=field,conditions=conditions,atype=atype):
            block=s.render_block(catalog,['fixture-service:case']);plain=s.render_plain(catalog,['fixture-service:case'])
            node=components(catalog,['fixture-service:case'])[0]
            return (node.action.action_type==atype and rec[field].replace('&','&amp;') in block
                and 'Fixture Owner' in block and 'Fixture Service' in block and 'Scotland' in block
                and node.capability != Capability.TEXT and 'aria-labelledby' in block
                and ('not promise a refund' in plain or 'does not take a police crime report' in plain))
        check('renderer',template,render_test)
        for key,value in [('action_type','custom'),('purpose','refund-entitlement'),('mode','custom'),
                          ('jurisdictions',['Mars']),('condition_ids',['unknown']),('instruction',{'kind':'custom','text':'Call X'}),
                          ('owner','imposter'),('route_id','evil:route')]:
            mutated=copy.deepcopy(cc);mutated['verified_org_contacts'][-1]['actions']['case'][key]=value
            check('actions',template+'/'+key,lambda x=mutated:rejects(lambda:s.catalog_from_canon(x)))
        changed=copy.deepcopy(cc);changed['verified_org_contacts'][-1]['actions']['case']['instruction']['template_id']='unknown-method'
        check('actions',template+'/method',lambda x=changed:rejects(lambda:s.catalog_from_canon(x)))

    bank=copy.deepcopy(c); rec=bank['verified_org_contacts'][-1]
    rec.update(key='own-bank', owner_id='own-bank', brand='Your own bank', name='Your own bank')
    for field in s._DEST_FIELDS: rec.pop(field, None)
    rec['actions']={'paid':action(action_type='contact',purpose='payment-recovery',mode='support',
        condition_ids=['suspected-authorised-bank-transfer-to-fraudster','banking-device-safe'], eligibility_ids=['sender-own-account'],
        instruction={'kind':'reader-held-channel','role':'own-bank','method_id':'existing-bank-app','recipient_relation':'sending-bank-of-affected-transfer'},
        limitation_ids=['no-money-recovery-guarantee'])}
    bc=s.catalog_from_canon(bank); bid=['own-bank:paid']
    check('renderer','endpoint-free bank contact',lambda:not bc.destinations(bid) and not Links(s.render_block(bc,bid)).links
        and 'authorised bank transfer' in s.render_plain(bc,bid) and 'Contact the bank that sent that transfer immediately' in s.render_plain(bc,bid)
        and components(bc,bid)[0].capability==Capability.CONTACT_ACTION)
    for key,value in [('role','any-organisation'),('method_id','arbitrary-app'),('url','https://evil.example')]:
        x=copy.deepcopy(bank);x['verified_org_contacts'][-1]['actions']['paid']['instruction'][key]=value
        check('actions','reader-held '+key,lambda x=x:rejects(lambda:s.catalog_from_canon(x)))

    for field,value in [('action_type','call'),('route_ids',['missing:route']),('condition_ids',['money-sent']),
                        ('owner','imposter'),('purpose','refund'),('jurisdictions',['Global']),('method','arbitrary')]:
        page=fixture_page();page[field]=value;r,_=approved(page)
        check('actions','article cannot override '+field,lambda page=page,r=r:rejects(lambda:s.validate_page(page,cat,r)))

    def two(url1,url2,owner='second-owner',service='second-service',scope=None,shared=False):
        cc=copy.deepcopy(c);rec=cc['verified_org_contacts'][-1];rec['actions']={'web':rec['actions']['web']};rec['report_url']=url1
        other=copy.deepcopy(rec);other.update(key=service,owner_id=owner,brand='Other Owner' if owner!='fixture-owner' else rec['brand'],report_url=url2)
        if scope:other['actions']['web']['jurisdictions']=scope
        if service=='fixture-service':rec['actions']['other']=copy.deepcopy(other['actions']['web'])
        else:cc['verified_org_contacts'].append(other)
        if shared:
            cc['destination_relationships']=[{'id':'explicit-sharing','type':'delegated-intake','operator_owner_id':'fixture-owner', 'attribution_id':'operated-by',
                'members':[{'route_id':r['key']+':web','owner_id':r['owner_id'],'purpose':'phishing-report','destination_field':'report_url',
                'destination_identity':list(destination_identity(s.Destination('url',r['report_url']))),
                'jurisdictions':list(s.catalog_from_canon({'verified_org_contacts':[r]}).resolve(r['key']+':web').jurisdictions)} for r in (rec,other)],
                'source_url':'https://routes.example/sharing-evidence','checked_on':'2026-10-01','status':'active'}]
        return cc
    for urls in [('https://collect.example','https://collect.example/'),('https://collect.example/report','https://collect.example/report')]:
        for owner in ('fixture-owner','second-owner'):
            cc=two(*urls,owner=owner)
            check('collision',str(urls)+owner,lambda cc=cc:rejects(lambda:s.catalog_from_canon(cc),'normalized destination collision'))
    check('collision','same evidenced owner/service compatible actions',lambda:len(s.catalog_from_canon(two('https://collect.example','https://collect.example/',owner='fixture-owner',service='fixture-service')).actions)==2)
    check('collision','distinct paths remain distinct',lambda:len(s.catalog_from_canon(two('https://collect.example/a','https://collect.example/b')).actions)==2)
    check('collision','empty fragment rejected',lambda:rejects(lambda:s.catalog_from_canon(two('https://collect.example/report','https://collect.example/report#'))))
    check('collision','query delimiter retained',lambda:https_identity('https://collect.example')!=https_identity('https://collect.example/?'))
    check('collision','same service incompatible nation needs relationship',lambda:rejects(lambda:s.catalog_from_canon(two('https://collect.example','https://collect.example/',owner='fixture-owner',service='fixture-service',scope=['Scotland']))))
    no_implicit=two('https://collect.example','https://collect.example/',scope=['Scotland'])
    no_implicit['verified_org_contacts'][-2]['actions']['web']['jurisdictions']=['England','Wales','Northern Ireland']
    check('collision','disjoint geography does not imply sharing',lambda:rejects(lambda:s.catalog_from_canon(no_implicit),'normalized destination collision'))
    for first,second in [('01234 567890','01234567890'),('01234 567890','٠١٢٣٤٥٦٧٨٩٠')]:
        cc=copy.deepcopy(c);rec=cc['verified_org_contacts'][-1];rec['actions']={'phone':rec['actions']['phone']};rec['phone']=first
        other=copy.deepcopy(rec);other.update(key='other-phone',owner_id='other-owner',brand='Other Owner',phone=second);cc['verified_org_contacts'].append(other)
        check('collision','phone loader collision or noncanonical hold '+second,lambda cc=cc:rejects(lambda:s.catalog_from_canon(cc)))
    cc=copy.deepcopy(c);rec=cc['verified_org_contacts'][-1];rec['actions']={'email':rec['actions']['email']}
    other=copy.deepcopy(rec);other.update(key='other-email',owner_id='other-owner',brand='Other Owner');cc['verified_org_contacts'].append(other)
    check('collision','email loader conflicting ownership',lambda:rejects(lambda:s.catalog_from_canon(cc),'normalized destination collision'))
    for a,b in [('https://例子.中国/a','https://xn--fsqu00a.xn--fiqs8s/a'),('https://COLLECT.example/a','https://collect.example./a')]:
        check('collision','URL comparison identity '+a,lambda a=a,b=b:destination_identity(s.Destination('url',a))==destination_identity(s.Destination('url',b)))
        check('collision','narrow canon spelling remains enforced '+a,lambda a=a:rejects(lambda:s._destination('url',a,'canon')))
    check('collision','lookalikes are distinct',lambda:destination_identity(s.Destination('url','https://pоlice.uk'))!=destination_identity(s.Destination('url','https://police.uk')))
    for value in ('01234 567890','01234-567890','٠١٢٣٤٥٦٧٨٩٠','０１２３４５６７８９０'):
        check('collision','phone identity '+value,lambda value=value:destination_identity(s.Destination('phone',value),'GB')==('phone','GB','','01234567890'))
    check('collision','numbering context separate',lambda:destination_identity(s.Destination('phone','01234567890'),'GB')!=destination_identity(s.Destination('phone','01234567890'),'international'))
    check('collision','email exact local normalized host',lambda:destination_identity(s.Destination('email','Evidence@EXAMPLE.ORG.'))==destination_identity(s.Destination('email','Evidence@example.org')) and destination_identity(s.Destination('email','Evidence@example.org'))!=destination_identity(s.Destination('email','evidence@example.org')))
    shared=two('https://collect.example','https://collect.example/',shared=True)
    check('collision','explicit evidenced sharing',lambda:len(s.catalog_from_canon(shared).actions)==2)
    check('collision','delegated operator is visible',lambda:'This route is operated by Fixture Owner.' in s.render_plain(s.catalog_from_canon(shared),['second-service:web']))
    contradictory=copy.deepcopy(shared)
    another=copy.deepcopy(contradictory['destination_relationships'][0]);another.update(id='opposite-operator',operator_owner_id='second-owner')
    contradictory['destination_relationships'].append(another)
    check('collision','review regression: contradictory operators',lambda:rejects(lambda:s.catalog_from_canon(contradictory),'overlapping relationship'))
    aliases=two('https://alpha.example/a','https://beta.example/b',shared=True)
    aliases['destination_relationships'][0]['type']='alias'
    third=copy.deepcopy(aliases['verified_org_contacts'][-1]);third.update(key='third-service',owner_id='third-owner',brand='Third Owner',report_url='https://gamma.example/c')
    aliases['verified_org_contacts'].append(third)
    second=copy.deepcopy(aliases['destination_relationships'][0]);second['id']='second-alias';second['operator_owner_id']='second-owner'
    second['members']=[copy.deepcopy(second['members'][1]),{'route_id':'third-service:web','owner_id':'third-owner','purpose':'phishing-report','jurisdictions':list(s._NATIONS[:4]),'destination_field':'report_url','destination_identity':['url','gamma.example','/c',False,'']}]
    aliases['destination_relationships'].append(second)
    check('collision','review regression: overlapping alias chain',lambda:rejects(lambda:s.catalog_from_canon(aliases),'alias chains/cycles'))
    cycle=copy.deepcopy(aliases);last=copy.deepcopy(second);last['id']='closing-cycle';last['members']=[copy.deepcopy(second['members'][1]),copy.deepcopy(cycle['destination_relationships'][0]['members'][0])];last['operator_owner_id']='third-owner';cycle['destination_relationships'].append(last)
    check('collision','review regression: alias cycle',lambda:rejects(lambda:s.catalog_from_canon(cycle),'alias chains/cycles'))
    complete_alias=two('https://alpha.example/a','https://beta.example/b',shared=True)
    complete_alias['destination_relationships'][0]['type']='alias'
    check('collision','one complete alias group supported',lambda:len(s.catalog_from_canon(complete_alias).actions)==2)
    for key,value in [('status','pending'),('source_url',''),('checked_on','2025-01-01'),('operator_owner_id','stranger'),('type','implicit'),('members',[])]:
        cc=copy.deepcopy(shared);cc['destination_relationships'][0][key]=value
        check('collision','invalid relationship '+key,lambda cc=cc:rejects(lambda:s.catalog_from_canon(cc)))

    r,pkt=approved(p)
    check('approval','authenticated exact candidate',lambda:publication.review(p,c,pkt).page_sha256==s.digest(p))
    check('approval','raw context is not publication authority',lambda:rejects(lambda:publication.review(p,c,r)))
    for field in ('title','description','quick_answer'):
        page=copy.deepcopy(p);page[field]+=' Changed.'
        check('approval','replay '+field,lambda page=page:rejects(lambda:publication.review(page,c,pkt),'binding mismatch'))
    for field,value in [('scope','action-authority'),('page_id','guide:other'),('canon_sha256','0'*64),('dependencies',{}),
                        ('reviewer','attacker'),('expires_at',(datetime.now(timezone.utc)-timedelta(days=1)).isoformat())]:
        altered=copy.deepcopy(pkt);altered['body'][field]=value
        check('approval','signed packet tampering '+field,lambda altered=altered:rejects(lambda:publication.review(p,c,altered)))
    def revoked():
        path=store()/'revoked.json';path.write_text(json.dumps([pkt['body']['decision_id']]))
        try:return rejects(lambda:publication.review(p,c,pkt),'revoked')
        finally:path.write_text('[]\n')
    check('approval','revocation',revoked)
    # Real issuer and verifier, only a synthetic key. No production packet.
    check('approval','explicit fixture issuer round trip',lambda:publication.review(p,c,publication.issue_reviewed(p,c,
        page_id='guide:'+p['slug'],private_key=store()/'fixture-key',reviewer='offline-fixture-reviewer',audience=s._NATIONS[:4])).page_sha256==s.digest(p))

    def writer_case(kind):
        page=fixture_page()
        if kind=='missing-marker':del page['reporting_routes']
        elif kind=='unknown-route':page['reporting_routes']=['unknown:route']
        elif kind=='unsafe-prose':page['sections'][0][1]='Call Organisation X.'
        elif kind=='override':page['condition_ids']=['money-sent']
        rr=review_for(page,c,allowed=p['reporting_routes'],approved_fields=dict(s.approval_fields(page)))
        packet=packet_for(page,c,rr)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'posts.json';target.write_text('[]\n');q=Path(tmp)/'quarantine'
            fn=lambda:writer.save_posts(str(target),[page],reporting_canon=c,reporting_reviews={page['slug']:packet},quarantine_dir=q)
            if kind=='valid':fn();return json.loads(target.read_text())==[page]
            return rejects(fn) and target.read_text()=='[]\n' and len(list(q.glob('*.json')))==1
    for kind in ('valid','missing-marker','unknown-route','unsafe-prose','override'):
        check('writer',kind,lambda kind=kind:writer_case(kind))
    existing=json.loads((build.ROOT/'content/posts.json').read_text())[0]
    check('writer','frozen legacy unchanged',lambda:not publication.required(existing))
    changed=copy.deepcopy(existing);changed['hero']+=' Changed.'
    check('writer','modified legacy cannot opt out',lambda:publication.required(changed))
    check('writer','actual renderer rejects marker omission',lambda:rejects(lambda:build.render_post(site,changed,[changed],sources=c)))
    def preflight():
        original=build.read_json
        with patch.object(build,'read_json',side_effect=lambda path:[changed] if Path(path).name=='posts.json' else original(path)), patch.object(build.shutil,'rmtree') as remove:
            result=rejects(build.build)
            return result and not remove.called
    check('writer','build rejection before destructive output replacement',preflight)

    contract=s.generator_contract(cat,tuple(cat.actions))
    check('generator','closed identifiers and no destination values',lambda:'routes.example' not in json.dumps(contract) and all('condition_ids' in x and 'action_type' in x for x in contract['actions']))
    check('generator','unknown IDs fail',lambda:rejects(lambda:s.generator_contract(cat,['unknown:action'])))
    check('generator','strict normalization retains forbidden approval',lambda:writer.normalise({'approved':True},writer.Topic('x','x','email'),'2026-10-10',strict=True)=={'approved':True})
    check('generator','unsigned production canon exposes no eligible actions',lambda:not s.generator_contract(s.catalog_from_canon(canon.load_canon()),eligibility.eligible_ids(canon.load_canon()))['allowed_reporting_routes'])
    check('generator','interface excludes old prose-action prompt',lambda:'reporting_routes' in writer.restricted_prompt(writer.Topic('x','x','email'),'2026-10-10',contract) and 'routes.example' not in writer.restricted_prompt(writer.Topic('x','x','email'),'2026-10-10',contract))

    def slots():
        page=fixture_page();page['quick_answer']={'kind':'action-summary','route_ids':page['reporting_routes']}
        page['faq']=[{'kind':'action-faq','question_id':'where-to-report','route_ids':page['reporting_routes']}]
        rr,packet=approved(page)
        html=build.render_post(site,page,[page],sources=c,reporting_review=packet)
        result=gate.run_gate(page,use_llm=False,reporting_canon=c,reporting_review=packet)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'posts.json'
            writer.save_posts(str(target),[page],reporting_canon=c,reporting_reviews={page['slug']:packet})
            saved=json.loads(target.read_text())==[page]
        return result.passed and saved and html.count('data-action-id="fixture-service:web"')==3 and 'HowTo' not in html and 'For a suspicious email only.' in html
    check('renderer','complete FAQ and quick-answer projections',slots)
    def hub_slots():
        page={k:v for k,v in fixture_page().items() if k in ('title','description','sections','reporting_routes')}
        page['faq']=[{'kind':'action-faq','question_id':'where-to-report','route_ids':page['reporting_routes']}]
        page['sources_checked']=[['Evidence','https://routes.example/evidence']]
        rr,packet=approved(page)
        result=gate.run_gate(page,use_llm=False,is_hub=True,reporting_page_id='hub:email',reporting_canon=c,reporting_review=packet)
        html=build.render_category_page(site,'email',[],hub=page,reporting_sources=c,reporting_review=packet)
        return result.passed and html.count('data-action-id="fixture-service:web"')==2
    check('renderer','review regression: action FAQ in hub and gate',hub_slots)
    for extra in ('prefix','suffix','destination','condition_ids'):
        page=fixture_page();page['quick_answer']={'kind':'action-summary','route_ids':page['reporting_routes'],extra:'Call X'}
        rr,_=approved(page)
        check('actions','placement rejects '+extra,lambda page=page,rr=rr:rejects(lambda:s.validate_page(page,cat,rr)))
    check('renderer','unknown provenance rejected',lambda:rejects(lambda:s.validate_effective([{'capability':'reporting_action'}],cat,r)))
    check('renderer','foreign catalog component rejected',lambda:rejects(lambda:s.validate_effective(components(s.catalog_from_canon(c),p['reporting_routes']),cat,r)))
    check('renderer','destination-only projection rejected',lambda:rejects(lambda:s.validate_effective(cat.destinations(p['reporting_routes']),cat,r),'destination-only'))
    check('renderer','citation cannot be an action',lambda:rejects(lambda:s.render_destination(cat,Citation('Evidence','https://routes.example/report'))))
    return rows


if __name__ == '__main__':
    rows=run_cases();groups=Counter(r['group'] for r in rows)
    print(json.dumps({'total':len(rows),'passed':sum(r['ok'] for r in rows),'groups':groups,
        'failures':[r for r in rows if not r['ok']]},indent=2))
    raise SystemExit(any(not r['ok'] for r in rows))
