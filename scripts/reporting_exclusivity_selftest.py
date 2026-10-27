#!/usr/bin/env python3
"""Offline WP3C9B2 regressions: real signatures, writers and complete pages.

No model, network, production key, content writer or deployment is invoked.
The synthetic SSH key authenticates deliberately prohibited prose: failures
must come from the action boundary, never missing or forged approval.
"""
import argparse
import copy
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import tempfile
from unittest.mock import patch

import build
import canon
import generate_content_claude as writer
import reporting_publication as publication
import reporting_structured as s
import reporting_eligibility as eligibility
from reporting_actions import TEMPLATES
from reporting_action_render import components
from reporting_fixture_review import packet_for, sign_body, store
from reporting_output import ArticleText, ArticleHTML, Citation, Capability, Fragment
from reporting_prose import violation
from reporting_structured_selftest import fixture_canon, fixture_page, review_for, action
from reporting_taxonomy import identifier, resolve, TaxonomyUse, CATEGORY_LABELS

BOUNDARY = 'restricted action-authoring boundary'
SAFE = ('Reporting fraud can help investigators.', 'Police recommend reporting sextortion promptly.',
        'Banks can sometimes stop or recover payments.', 'Victims may need support after fraud.')
ATTACKS = ('Speak to your bank now.', 'Get in touch with your bank.',
    'Ask your bank to stop payment.', 'Tell your bank immediately.', 'Contact your bank immediately.',
    'Report to the police.', 'Call your bank.', 'Email the evidence.', 'Forward the message.',
    'Submit the evidence.', 'Visit the service for reporting.', 'Open the reporting form.',
    'Use the service to report fraud.', 'Report using the source above.', 'Follow our guide to report it.',
    'Raise the matter with your bank.', 'Reach out to your bank.', 'Ring your bank.',
    'The next step is to speak to your bank.', 'A phone scam can appear convincing; speak to your bank.',
    'Reporting fraud can help investigators. Speak to your bank now.',
    'A phishing email instructs you to contact the police.',
    'Speak to your bank through an unknown representation.')
SURFACES = ('section', 'bullet', 'title', 'description', 'hero', 'heading', 'quick_answer',
    'faq-question', 'faq-answer', 'keyword', 'citation', 'evidence', 'example', 'figure', 'hub-intro')


# Independently inspected complete non-action page text for this fixed fixture.
# A new paragraph or changed boilerplate cannot silently pass a verb detector.
# UI controls, first-party newsletter support and protective stopping/retention
# are not high-risk reporting/contact instructions. Any change requires review.
NON_ACTION_PAGE_TEXT = ('A suspicious message: safe next steps',
 'Skip to content',
 'Cookies & privacy',
 'Allow optional analytics and advertising cookies? They help us understand performance and support the '
 'site.',
 'Reject',
 'Accept',
 'Beat the Scam',
 'Scam checks, alerts, and consumer protection guides',
 'Home',
 'Guides',
 'Categories',
 'Research',
 'Recovery',
 'About',
 'Contact',
 'Check a message',
 'Menu',
 'Home',
 'Guides',
 'Email Scams',
 'A suspicious message: safe next steps',
 'Email Scams',
 'A suspicious message: safe next steps',
 'Pause and check the request before acting.',
 'By Alex Bacsa',
 '· Published 2026-10-09',
 '· 1 min read',
 'Quick answer:',
 'Reporting and support options',
 'Pause. Do not pay or share passwords, PINs or one-time codes.',
 'On this page',
 'Check safely',
 'Check safely',
 'Scammers use urgency to discourage independent checks. A familiar brand does not establish authenticity.',
 'Frequently asked questions',
 'Where can I report this?',
 'Think you’ve spotted a scam?',
 'Use the AI scam checker for an automated second opinion, and see reporting and support options on this '
 'page.',
 'Published 2026-10-09. Read about how Beat the Scam writes guides.',
 'Fast checks',
 'Pause before sending money or credentials',
 'A familiar brand does not establish authenticity',
 'Never share one-time passcodes',
 'Be sceptical of bank transfer pressure',
 'Related guides',
 'Browse all guides',
 'Reporting and support',
 'See reporting and support options on this page.',
 'Not sure?',
 'Paste the suspicious message into the free AI checker for an instant plain-English verdict.',
 'Check a message',
 'Get scam alerts before they reach you',
 'Plain-English warnings and new guides on the latest UK scams — the checks to run before you click, pay, or '
 'share. Free, and you can unsubscribe anytime.',
 'Email address',
 'Subscribe',
 'Leave this field empty',
 'I agree to receive emails from Beat the Scam and accept the Privacy Policy.',
 'Signing up needs JavaScript. With it switched off, contact',
 'us and we’ll send you a confirmation link. We won’t add your address until',
 'you confirm.',
 'Beat the Scam',
 'Scam alerts, plain-English checks, and practical guides to help people verify suspicious emails, texts, '
 'websites, calls, and offers.',
 'Educational content only. Not legal, regulatory, or financial advice.',
 'Explore',
 'All guides',
 'Research & data',
 'Scam recovery checklist',
 'Trust & legal',
 'About',
 'How we fact-check',
 'Corrections',
 'Privacy Policy',
 'Cookie Policy',
 'Cookie settings',
 'Terms',
 'Disclaimer',
 'Contact',
 '© 2026 Beat the Scam. Consumer protection guides for UK residents. Educational content only — not legal or '
 'financial advice.',
 'Check a message',
 'Start recovery')


def candidate(text=SAFE[0], surface='section'):
    p = fixture_page(); p['reporting_routes'] = []
    if surface == 'section': p['sections'][0][1] = text
    elif surface == 'bullet': p['sections'][0][1] = repr([text])
    elif surface == 'heading': p['sections'][0][0] = text
    elif surface == 'faq-question': p['faq'][0][0] = text
    elif surface == 'faq-answer': p['faq'][0][1] = text
    elif surface == 'keyword': p['keywords'] = [text]
    elif surface == 'citation': p['sources_checked'] = [[text, 'https://sources.example/evidence']]
    elif surface == 'evidence': p['evidence'] = [{'signal': text}]
    elif surface == 'example': p['message_examples'] = [{'message': text}]
    elif surface == 'figure': p['figure'] = {'type': 'decision-flow', 'title': text}
    elif surface == 'hub-intro':
        p = {k:v for k,v in p.items() if k in ('title','description','sections','faq','reporting_routes')}
        p['intro'] = text
    else: p[surface] = text
    return p


def approved(p, c, **kw):
    r = review_for(p, c, approved_fields=dict(s.approval_fields(p)),
                  allow_empty=not p.get('reporting_routes'), **kw)
    return r, packet_for(p, c, r)


def rejects(fn, reason=None):
    try: fn()
    except (ValueError, TypeError, KeyError) as exc:
        return reason is None or reason in str(exc)
    return False


def run_cases(output=None):
    rows = []; c = canon.load_canon(); cat = s.catalog_from_canon(c)
    site = build.read_json(build.ROOT / 'content/site.json')
    def check(group, name, fn):
        try: ok=bool(fn()); detail='' if ok else 'assertion false'
        except Exception as exc: ok=False; detail=f'{type(exc).__name__}: {exc}'
        rows.append(dict(group=group,name=name,ok=ok,detail=detail))
    def render(p, packet, cc=c):
        if 'slug' not in p:
            return build.render_category_page(site,'email',[],hub=p,reporting_sources=cc,reporting_review=packet)
        return build.render_post(site,p,[p],sources=cc,reporting_review=packet)
    def verify(p, packet, cc=c):
        return publication.review(p,cc,packet,page_id='hub:email' if 'slug' not in p else None)

    for text in SAFE:
        for surface in SURFACES:
            def positive(text=text,surface=surface):
                p=candidate(text,surface);r,pkt=approved(p,c)
                # Literal-list source is normalized by the renderer. All other
                # representations must be complete admitted productions too.
                return bool(verify(p,pkt)) and 'data-action-id=' not in render(p,pkt)
            check('signed',surface+' / '+text,positive)
    for text in ATTACKS:
        for surface in SURFACES:
            # Long metadata is an independent schema rejection, not the proof
            # being tested here. Keep the same operational class in the title.
            value=text if surface!='title' or len(text)<=60 else 'Speak to your bank now.'
            def negative(value=value,surface=surface):
                p=candidate(value,surface);r,pkt=approved(p,c)
                assert pkt.get('signature')
                with patch.object(s,'_raw_destinations',return_value=[]):
                    return rejects(lambda:verify(p,pkt),BOUNDARY) and rejects(lambda:render(p,pkt),BOUNDARY)
            check('signed',surface+' / '+text,negative)
    for text in ATTACKS[:5]:
        def destination_free(text=text):
            p=candidate(text);r,pkt=approved(p,c)
            return not s.raw_destinations(text) and rejects(lambda:verify(p,pkt),BOUNDARY)
        check('destination_free',text,destination_free)
    # Independent review found that a global literal-list conversion discarded
    # comments even in metadata and FAQ fields whose renderer shows the source.
    for payload in ("['Pause.' # Speak to your bank now.\n]",
                    "['Pause.' # Call your bank.\n]", "['Speak to your bank now.']"):
        for surface in SURFACES:
            if surface == 'bullet':
                continue
            def comment_case(payload=payload,surface=surface):
                p=candidate(payload,surface);_,packet=approved(p,c)
                reason = ('citation label: expected bounded' if surface=='citation' and '\n' in payload else BOUNDARY)
                with patch.object(s,'_raw_destinations',return_value=[]):
                    return rejects(lambda:verify(p,packet),reason) and rejects(lambda:render(p,packet),reason)
            check('review_regression',surface+' / '+repr(payload),comment_case)
    for surface in ('hero','title','description','faq-answer','citation'):
        def literal_label(surface=surface):
            p=candidate("['Pause.']",surface);_,packet=approved(p,c)
            return rejects(lambda:verify(p,packet),BOUNDARY)
        check('review_regression','non-body list has no implicit interpretation / '+surface,literal_label)
    for text in (*SAFE,*ATTACKS[:15]):
        p=candidate(text)
        check('unsigned',text,lambda p=p,text=text: rejects(lambda:verify(p,{}))
              and ((violation(text) is None)==(text in SAFE)))

    # Observe the real successful SSH verification before the rejecting boundary.
    def order():
        p=candidate(ATTACKS[0]);_,pkt=approved(p,c);events=[]
        run=publication.subprocess.run;validate=s.validate_effective
        def observed_run(args,*a,**kw):
            result=run(args,*a,**kw)
            if '-Y' in args and 'verify' in args and result.returncode==0:events.append('authenticated')
            return result
        def observed_boundary(nodes,catalog,review):
            assert review.editorial_decision is not None
            events.append('boundary');return validate(nodes,catalog,review)
        with patch.object(publication.subprocess,'run',side_effect=observed_run),patch.object(s,'validate_effective',side_effect=observed_boundary):
            blocked=rejects(lambda:verify(p,pkt),BOUNDARY)
        return blocked and events==['authenticated','boundary']
    check('approval','authentication then boundary',order)
    p=candidate();_,pkt=approved(p,c)
    def expired():
        body=copy.deepcopy(pkt['body']);now=datetime.now(timezone.utc)
        body.update(issued_at=(now-timedelta(days=3)).isoformat(),expires_at=(now-timedelta(days=2)).isoformat())
        return rejects(lambda:verify(p,sign_body(body)),'expired')
    check('approval','genuinely signed expired decision',expired)
    wrong=copy.deepcopy(p);wrong['hero']=SAFE[0]
    check('approval','wrong field replay',lambda:rejects(lambda:verify(wrong,pkt),'binding mismatch'))
    other=copy.deepcopy(p);other['slug']='other-article'
    check('approval','wrong article replay',lambda:rejects(lambda:verify(other,pkt),'binding mismatch'))
    check('approval','issuer cannot approve operational prose',lambda:rejects(lambda:publication.issue_reviewed(
        candidate(ATTACKS[0]),c,page_id='guide:structured-fixture',private_key=store()/'fixture-key',
        reviewer='offline-fixture-reviewer',audience=s._NATIONS[:4],allow_empty=True),BOUNDARY))

    for slug in ('report-fraud-now','call-your-bank','contact-police','submit-evidence','open-report-fraud','contact-your-bank-now'):
        check('category_slug','syntax remains independent / '+slug,lambda slug=slug:identifier(slug)==slug)
        def unregistered(slug=slug):
            p=candidate();p['category']=slug;_,pkt=approved(p,c)
            return rejects(lambda:verify(p,pkt),'not enrolled') and rejects(lambda:render(p,pkt),'not enrolled')
        check('category_slug','no automatic label / '+slug,unregistered)
    for slug in ('', 'Email','contact police','../email','email/now','email:action','email%20','émail','email\n'):
        check('category_slug','invalid identifier '+repr(slug),lambda slug=slug:rejects(lambda:identifier(slug),'syntax'))
    for slug,label in CATEGORY_LABELS.items():
        def enrolled(slug=slug,label=label):
            p=candidate();p['category']=slug;_,pkt=approved(p,c);node=resolve(slug)
            return node.capability==Capability.TAXONOMY and node.project()==label and node.project('path')=='/categories/'+slug+'/' and 'data-action-id=' not in render(p,pkt)
        check('category_label',slug,enrolled)
    for label in ('Report fraud now','Call your bank','Contact the police','https://attacker.example','<a href="//attacker">Help</a>'):
        check('category_label','unregistered visible label '+label,lambda label=label:rejects(lambda:resolve(label)))
        check('category_label','no free label parameter '+label,lambda label=label:rejects(lambda:TaxonomyUse('email',label)))
    p=candidate();r,pkt=approved(p,c)
    cc=fixture_canon();ac=s.catalog_from_canon(cc);a=components(ac,['fixture-service:web'])[0]
    check('cross_capability','action object as taxonomy',lambda:rejects(lambda:resolve(a)))
    check('cross_capability','taxonomy as action ID',lambda:rejects(lambda:ac.select([resolve('email')])))
    check('cross_capability','taxonomy ID as action ID',lambda:rejects(lambda:ac.select(['email'])))
    check('cross_capability','approved prose hash as action',lambda:rejects(lambda:ac.select([s.prose_hash(SAFE[0])])) )
    check('cross_capability','citation approval is not page approval',lambda:rejects(lambda:verify(p,Citation('Evidence','https://sources.example'))))
    check('cross_capability','category title as template input',lambda:rejects(lambda:components(ac,['Email Scams'])))
    check('cross_capability','forged capability dictionary',lambda:rejects(lambda:s.validate_effective([{'capability':'action','text':ATTACKS[0]}],cat,r)))
    check('cross_capability','citation cannot render operational label',lambda:rejects(lambda:s.render_citation(Citation(ATTACKS[0],'https://sources.example')),BOUNDARY))
    def numeric_replay():
        page=candidate(ATTACKS[0]);_,packet=approved(page,c)
        body=copy.deepcopy(packet['body'])
        body['numeric_facts']=[{'path':'sections/0/1','text':ATTACKS[0],'kind':'count'}]
        return rejects(lambda:verify(page,sign_body(body)),'typed, non-instructional reviewed field')
    check('cross_capability','genuinely signed numeric declaration cannot wrap action',numeric_replay)
    for markup in ('<p>Sp<em>eak</em> to your bank now.</p>','<p>Get in <code>touch</code> with your bank.</p>',
                   '<a href="/recovery/">Follow our guide to report it.</a>'):
        check('derived',markup,lambda markup=markup:rejects(lambda:s.validate_effective([ArticleHTML('sections/0/1',markup)],cat,r),BOUNDARY))
    for text in (ATTACKS[0], 'Report fraud now', 'Call your bank'):
        for path in ('title','description','keywords/joined','faq/0/1','sources_checked/0/0'):
            check('derived',path+' / '+text,lambda text=text,path=path:rejects(lambda:s.validate_effective([ArticleText(path,text,projection='schema')],cat,r),BOUNDARY))

    def writer_case(p,cc,accept,reason=None):
        _,packet=approved(p,cc)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'posts.json';target.write_text('[]\n');q=Path(tmp)/'quarantine'
            call=lambda:writer.save_posts(str(target),[p],reporting_canon=cc,reporting_reviews={p['slug']:packet},quarantine_dir=q)
            if accept:
                call();return json.loads(target.read_text())==[p] and not list(q.glob('*.json'))
            return rejects(call,reason) and target.read_text()=='[]\n' and len(list(q.glob('*.json')))==1
    for text in (*SAFE,*ATTACKS[:15]):
        check('writer',text,lambda text=text:writer_case(candidate(text),c,text in SAFE))
    bad=candidate();bad['category']='contact-your-bank-now'
    check('writer','category repro quarantines',lambda:writer_case(bad,c,False))
    check('writer','typed action accepted',lambda:writer_case(fixture_page(),cc,True))
    for surface in ('hero','title','description','faq-answer'):
        check('writer','review regression / '+surface,lambda surface=surface:writer_case(
            candidate("['Pause.' # Speak to your bank now.\n]",surface),c,False,BOUNDARY))
    for key,value in (('approved',True),('signature','model signature'),('prose_approvals',[]),('capability','action'),('template_id','call-support')):
        page=candidate();page[key]=value
        check('generator',key,lambda page=page:writer_case(writer.normalise(page,writer.Topic('x','x','email'),'2026-10-10',strict=True),c,False))
    for route in ('email','contact-your-bank-now','Email Scams','unknown:action'):
        page=candidate();page['reporting_routes']=[route]
        check('generator','unresolved ID '+route,lambda page=page:writer_case(page,cc,False))
    contract=s.generator_contract(ac,tuple(ac.actions))
    check('generator','no signing or raw destinations in contract',lambda:'signature' not in contract and 'routes.example' not in json.dumps(contract))
    check('generator','unsigned production canon exposes no eligible actions',lambda:not eligibility.eligible_ids(canon.load_canon()))

    # Complete HTML for every action TYPE and every registered fixed template.
    # Enumeration compares exact typed blocks and
    # every FAQ schema answer; residual complete page text is inspected separately.
    enumerations=[]
    for template,(atype,kind,purpose,mode,conditions,optional,_) in TEMPLATES.items():
        from reporting_model_extension_selftest import template_fixture
        source,rid=template_fixture(template)
        def full_page(source=source,template=template,atype=atype,rid=rid):
            catalog=s.catalog_from_canon(source);plan=[rid];node=components(catalog,plan)[0]
            page=fixture_page();page['reporting_routes']=plan
            page['quick_answer']={'kind':'action-summary','route_ids':plan}
            page['faq']=[{'kind':'action-faq','question_id':'where-to-report','route_ids':plan}]
            _,packet=approved(page,source);html=render(page,packet,source)
            blocks=re.findall(r'<div class="restricted-action" data-action-id="[^"]+">.*?</div>',html,re.S)
            assert blocks==[node.html()]*3
            scripts=re.findall(r'<script type="application/ld\+json">(.*?)</script>',html,re.S)
            objects=[json.loads(x) for x in scripts]
            faqs=[x for x in objects if x.get('@type')=='FAQPage']
            assert len(faqs)==1 and faqs[0]['mainEntity'][0]['acceptedAnswer']['text']==node.plain()
            residue=html.replace(node.html(),'')
            residue=re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>','',residue,flags=re.S)
            # Independent final-output check, not the production prose matcher.
            # Names of navigation/fields are inert labels, not commands.
            lines=[' '.join(x.split()) for x in Fragment(residue).text.splitlines() if x.strip()]
            operational=[x for x in lines if re.match(r'^(?:Report|Contact|Call|Email|Forward|Submit|Visit|Open|Attach|Speak|Tell|Ask|Get in touch|Follow)\b',x,re.I)
                         and x not in ('Contact','Email address','Email','Contact us','Email Scams')]
            assert not operational, operational
            assert tuple(lines) == NON_ACTION_PAGE_TEXT, 'unclassified complete-page text'
            enumerations.append({'template':template,'action_type':atype,'route_id':node.action.route_id,
                'typed_html_occurrences':3,'typed_schema_occurrences':1,'instruction':node.plain(),
                'residual_text':lines,'untyped_operational':operational})
            if output:(output/(template+'.html')).write_text(html)
            return True
        check('final_output',template,full_page)
    check('final_output','all eight types enumerated',lambda:set(x['action_type'] for x in enumerations)=={'report','contact','call','email','forward','submit','visit','open'})
    if output:(output/'operational-inventory.json').write_text(json.dumps(enumerations,indent=2)+'\n')
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.output:args.output.mkdir(parents=True,exist_ok=True)
    rows=run_cases(args.output);groups=Counter(r['group'] for r in rows)
    result={'total':len(rows),'passed':sum(r['ok'] for r in rows),
        'groups':{g:{'passed':sum(r['ok'] for r in rows if r['group']==g),'total':n} for g,n in groups.items()},
        'failures':[r for r in rows if not r['ok']]}
    if args.output:(args.output/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));raise SystemExit(bool(result['failures']))
