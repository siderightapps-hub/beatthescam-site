#!/usr/bin/env python3
"""WP3C8B3 offline effective-output and real persistence/quarantine tests.

Synthetic pages/canon and trusted contexts only; all writes are in temporary
directories. No generation, credentials, API calls or production build writes.
Counts are cases, not claims of independent security properties.
"""
import argparse
from collections import Counter
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import copy
from dataclasses import replace
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
from unittest.mock import patch

import build
from reporting_fixture_review import packet_for
import canon
import content_gate as gate
import generate_content_claude as writer
import search_console_articles as search
import rewrite_thin_guides as rewrite
import reporting_structured as sr
from reporting_output import ArticleText, ArticleHTML, CanonRoutes, Citation, Fragment
from reporting_structured_selftest import fixture_page, fixture_canon, review_for, Links


ORDINARY = [
    ('Version 1.2.3', 'version'), ('Version v1.2.300', 'version'),
    ('Address 192.0.2.10', 'ip'), ('Value 0.123456789', 'decimal'),
    ('Rate 12.5%', 'percentage'), ('Date 01.02.2026', 'date'),
    ('Cost £1,234.56', 'money'), ('Article ID A123456', None),
    ('In 2026', 'year'), ('Section 123', 'legislation'),
    ('Order AB123456', None), ('Only two choices.', None), ('Count 12', None)]


def run_cases():
    rows = []
    c = fixture_canon(); catalog = canon.reporting_catalog(c)
    site = json.loads((build.ROOT / 'content/site.json').read_text())

    def check(name, group, fn):
        try:
            ok = bool(fn()); detail = '' if ok else 'assertion false'
        except Exception as exc:
            ok, detail = False, f'{type(exc).__name__}: {exc}'
        rows.append(dict(name=name, group=group, ok=ok, detail=detail))

    def rejects(fn, contains=None):
        try: fn()
        except (sr.ReportingError, canon.CanonError) as exc:
            return contains is None or contains in str(exc) or (contains == 'destination' and 'restricted action-authoring boundary' in str(exc))
        return False

    def page(text, field='section'):
        p = fixture_page()
        if field.startswith('hub-'):
            p = {k:v for k,v in p.items() if k in ('title','description','sections','faq','reporting_routes')}
            p['intro'] = 'Check safely.'
        if field in ('section','hub-section'): p['sections'][0][1] = text
        elif field == 'bullet': p['sections'][0][1] = '- ' + text
        elif field == 'heading': p['sections'][0][0] = text
        elif field == 'hub-intro': p['intro'] = text
        elif field in ('faq-question','faq-answer','hub-faq'):
            p['faq'][0][0 if field=='faq-question' else 1] = text
        elif field.startswith('figure-'):
            key=field.split('-')[1]
            p['figure'] = {'type':'decision-flow', 'title':'Check safely', 'alt':'Decision flow'}
            if key in ('check','then'): p['figure']['steps'] = [{key:text}]
            else: p['figure'][key] = text
        elif field.startswith('evidence-'): p['evidence'] = [{field.split('-')[1]:text}]
        elif field.startswith('example-'): p['message_examples'] = [{field.split('-')[1]:text}]
        elif field == 'keywords': p['keywords'] = [text]
        else: p[field] = text
        return p

    def render(p, review, hub=False):
        return (build.render_category_page(site,'email',[],hub=p,reporting_sources=c,reporting_review=packet_for(p, c, review))
                if hub else build.render_post(site,p,[p],sources=c,reporting_review=packet_for(p, c, review)))

    def blocked(text, field='section'):
        p=page(text,field); review=review_for(p,c,approved_fields=dict(sr.approval_fields(p)))
        result=gate.run_gate(p,use_llm=False,is_hub=field.startswith('hub'), reporting_page_id='hub:email' if field.startswith('hub') else None,
                             reporting_canon=c,reporting_review=packet_for(p, c, review))
        return (not result.passed and any(i['check']=='structured_reporting'
                    and any(reason in i['detail'] for reason in ('destination', 'restricted action-authoring boundary')) for i in result.issues)
                and rejects(lambda:render(p,review,field.startswith('hub')), 'destination'))

    payloads = [
        'Call 07\t12\t34\t56\t78\t9 to report it.',
        'Call 07\n12\n34\n56\n78\n9 to report it.',
        'Call 07\r\n12\r\n34\r\n56\r\n78\r\n9 to report it.',
        *['Call '+mark.join('07123456789')+' to report it.' for mark in ('\u034f','\u0332','\u0301','\u20e3')],
        'Text '+'\u0332'.join('8899')+' to report it.',
        'Call `07``12``34``56``78``9` to report it.',
        'Text `88``99` to report it.',
        'Email `evidence`@`attacker`.`example` to report it.',
        'Report through `https`://`attacker`.`example`/intake.',
        'Call [07](/a/)[12](/b/)[34](/c/)[56](/d/)[78](/e/)[9](/f/) to report it.']
    for text in payloads:
        for field in ('section','quick_answer','faq-question','faq-answer','hub-intro','hub-section','hub-faq'):
            check(repr(text)+'/'+field,'reproductions',lambda t=text,f=field:blocked(t,f))

    separators = ['.','·','•','‧','⁃',' ', '\u00a0','\u202f','\u2009','\u2002',
                  '\u200b','\u034f','\u0332','\u20e3','\u2028','\u2029','\t','\n','\r\n',
                  '/',',',':',';','_','*','**','`','&#32;','&#x034f;']
    for digits in ('07123456789','٠٧١٢٣٤٥٦٧٨٩','０７１２３４５６７８９','8899','۸۸۹۹'):
        for sep in separators:
            for chunks in ([digits[i:i+2] for i in range(0,len(digits),2)], list(digits)):
                text='Contact '+sep.join(chunks)+' for help.'
                check(repr(text),'fragments',lambda t=text:blocked(t))

    reassembly = [*payloads[8:],
        'Call 07`123456789 to report it.',
        'Call [07](/a/)`12`[34](/b/)`56``78``9`.',
        'Email [evidence](/a/)@[attacker](/b/).`example`.',
        'Report through [https](/a/)://`attacker`.`example`/intake.',
        "['Call " + ''.join('\\x'+format(ord(v),'02x') for v in '07123456789') + " to report it.']",
        "['Email " + ''.join('\\x'+format(ord(v),'02x') for v in 'evidence@attacker.example') + " to report it.']",
        "['Call ' '07' '12' '34' '56' '78' '9' ' to report it.']"]
    for text in reassembly:
        for field in ('section','bullet','hub-intro','faq-answer'):
            if field == 'bullet' and '\\x' in text:
                # A bullet prefix prevents the legacy whole-body list parser;
                # these escapes remain visible literals, not decoded attacks.
                continue
            check(repr(text)+'/'+field,'reassembly',lambda t=text,f=field:blocked(t,f))

    derived_fields = ('title','description','hero','quick_answer','heading','keywords','faq-question',
        'faq-answer','hub-faq','evidence-signal','evidence-finding','evidence-basis','example-label',
        'example-message','example-assessment','figure-title','figure-alt','figure-caption','figure-check','figure-then')
    for field in derived_fields:
        for text in (payloads[8],payloads[10],payloads[11]):
            check(field+'/'+text,'derived',lambda f=field,t=text:blocked(t,f))
    check('keyword schema concatenation','derived',lambda:blocked('Call 07123456789','keywords'))
    check('metadata fallback conversion','derived',lambda:blocked('Call 07`123456789.'))
    check('HowTo backtick removal','derived',lambda:blocked('Step 1: Pause. Step 2: Call 07`123456789. Step 3: Keep evidence.'))
    # Independent review: inspect the actual 500-character schema conversion,
    # including a suffix that the source scanner correctly treats as an ID.
    for digits in ('07123456789', '٠٧١٢٣٤٥٦٧٨٩', '8899'):
        prefix = 'Keep the original message. ' + 'A' * (467-len(digits)) + ' Call '
        text = 'Step 1: '+prefix+digits+'x. Step 2: Pause. Step 3: Keep evidence.'
        check('HowTo truncation '+digits,'derived',lambda t=text:blocked(t))
    for value in ('_07123456789_', '_07_12_34_56_78_9_', '_٨٨٩٩_'):
        check('wrapped '+value,'fragments',lambda v=value:blocked('Call '+v+' to report it.'))

    def real_howto():
        p=page('Step 1: Pause. Step 2: Check independently. Step 3: Keep evidence.')
        output=render(p,review_for(p,c,approved_fields={'sections/0/1':
            'Step 1: Pause. Step 2: Check independently. Step 3: Keep evidence.'}))
        import re
        schemas=[json.loads(v) for v in re.findall(r'<script type="application/ld\+json">(.*?)</script>',output,re.S)]
        return not any(v.get('@type')=='HowTo' for v in schemas)
    check('restricted pages do not mine narrative into HowTo','e2e',real_howto)

    p=fixture_page(); review=review_for(p,c)
    def effective(node): return bool(sr.validate_effective([node],catalog,review))
    for node in (ArticleText('unit','Safe plain text'),ArticleHTML('unit','Read <code>settings</code>.'),
                 ArticleHTML('unit','<a href="/recovery/">Read the guide</a>'),
                 CanonRoutes(('fixture-service:web',))):
        check(repr(node),'unit',lambda n=node:effective(n))
    for value in ('https://attacker.example','evidence@attacker.example','07123456789',
                  '07.12.34.56.78.9','٠٧١٢٣٤٥٦٧٨٩','88\t99'):
        check(value,'unit',lambda v=value:rejects(lambda:effective(ArticleText('unit',v)),'destination'))
    for value in ('<code>07</code><code>123456789</code>',
                  '<code>evidence</code>@<code>attacker</code>.<code>example</code>',
                  '<code>https</code>://<code>attacker</code>.<code>example</code>'):
        check(value,'unit',lambda v=value:rejects(lambda:effective(ArticleHTML('unit',v)),'destination'))
    for href in ('http://attacker.example','https://attacker.example','mailto:a@attacker.example',
                 'tel:07123456789','//attacker.example','&#47;&#47;attacker.example',
                 'javascript:alert(1)','/\\attacker','/a/../b/','/a/?url=x'):
        check(href,'hrefs',lambda h=href:rejects(lambda:effective(ArticleHTML('unit',f'<a href="{h}">Read</a>')),'href'))
    for href in ('/recovery/','/categories/email/','/about/'):
        check(href,'hrefs',lambda h=href:effective(ArticleHTML('unit',f'<a href="{h}">Read</a>')))

    # Actual guide/hub renderer output, not just a validator result.
    for hub in (False,True):
        for label,text,extra in [('route only','Check independently.',{}),
            ('citation','Check independently.',{'sources_checked':[['Independent evidence','https://routes.example/evidence']]}),
            ('internal','Read [the guide](/recovery/).',{})]:
            def positive(hub=hub,text=text,extra=extra):
                p=page(text,'hub-section' if hub else 'section');p.update(extra)
                r=review_for(p,c,approved_fields={'sections/0/1':text,
                    'sources_checked/0/0':'Independent evidence'})
                result=gate.run_gate(p,use_llm=False,is_hub=hub,reporting_page_id='hub:email' if hub else None,reporting_canon=c,reporting_review=packet_for(p, c, r))
                html=render(p,r,hub);links=Links(html).links
                return result.passed and 'https://routes.example/report?a=one&b=two' in links and (
                    not extra or 'https://routes.example/evidence' in links) and (
                    '[' not in text or '/recovery/' in links)
            check(label+'/'+str(hub),'e2e',positive)
        for text in ('Report at https://attacker.example','Email evidence@attacker.example',payloads[0],payloads[8]):
            check(text+'/'+str(hub),'e2e',lambda t=text,h=hub:blocked(t,'hub-section' if h else 'section'))

    cp=fixture_page();cp['sources_checked']=[['Independent evidence','https://routes.example/evidence']]
    cr=review_for(cp,c)
    check('reviewed citation typed node','citation',lambda:sr.validate_effective(
        [Citation(*cp['sources_checked'][0])],catalog,cr) == (Citation(*cp['sources_checked'][0]),))
    check('unreviewed citation typed node','citation',lambda:rejects(lambda:sr.validate_effective(
        [Citation('Read','https://attacker.example')],catalog,cr)))
    for text in ('Report through the sources below.','Send evidence using Independent evidence.',
                 'Use the bibliography to contact the service.','Report at https://routes.example/evidence.',
                 'Report through the final link below.',
                 'Send evidence using the last link at the bottom of this page.',
                 'Report through the [li](/a/)`nk` below.'):
        def cross(text=text):
            p=copy.deepcopy(cp);p['sections'][0][1]=text
            return rejects(lambda:render(p,review_for(p,c)))
        check(text,'citation',cross)
    bad=copy.deepcopy(cp);bad['sources_checked'][0][0]='Report here'
    check('instructional citation label','citation',lambda:rejects(lambda:render(bad,review_for(bad,c))))

    for text,kind in ORDINARY:
        def ordinary(text=text,kind=kind):
            p=page(text);r=review_for(p,c,approved_fields={'sections/0/1':text})
            # Original, unchanged 13-example corpus. Two ambiguous fields need
            # separate review; never count expected holds as accepted prose.
            if kind in ('ip','decimal'):
                return rejects(lambda:render(p,r), 'destination')
            return bool(render(p,r))
        check(text,'numeric_default_policy',ordinary)
        def numeric(text=text,kind=kind):
            p=page(text);facts=() if kind is None else (sr.NumericFact('sections/0/1',text,kind),)
            r=review_for(p,c,numeric_facts=facts,approved_fields={'sections/0/1':text})
            result=gate.run_gate(p,use_llm=False,reporting_canon=c,reporting_review=packet_for(p, c, r))
            return result.passed and text in Fragment(render(p,r)).text
        check(text,'numeric_controls',numeric)
    # Additional representative values: syntax classes, not thirteen bespoke strings.
    for text,kind in [('Release 12.44.1','version'),('IP address 203.0.113.9','ip'),('Average 123.45','decimal'),
        ('Percentage 0.5%','percentage'),('Dated 2026-10-09','date'),('Price €999.00','money'),
        ('Balance £100,000.99','money'),('Year 1998','year'),('Regulation 321','legislation'),
        ('Reference ABC123456','identifier'),('Total 1500','count')]:
        def additional(text=text,kind=kind):
            p=page(text);r=review_for(p,c,numeric_facts=(sr.NumericFact('sections/0/1',text,kind),),
                                   approved_fields={'sections/0/1':text})
            return bool(render(p,r))
        check(text,'numeric_controls',additional)
    for text,kind in [('Call 2026','year'),('Version 1.2.3 to report','version'),
                       ('Text 88.99','decimal'),('Cost £1,234.56; dial it','money')]:
        p=page(text);r=review_for(p,c,numeric_facts=(sr.NumericFact('sections/0/1',text,kind),))
        check(text,'numeric_isolation',lambda p=p,r=r:rejects(lambda:render(p,r)))
    p=page('Value 0.123456789');r=review_for(p,c,numeric_facts=(sr.NumericFact('sections/0/1','Value 0.123456789','decimal'),))
    p['faq'][0][1]='Value 0.123456789';r=replace(r,page_sha256=sr.digest(p))
    check('fact cannot license another field','numeric_isolation',lambda:rejects(lambda:render(p,r)))
    # Whole-field numeric syntax cannot exempt surrounding instructions.
    for text in ('Call Version 1.2.3','Version 1.2.3 to report it.',
                 'Text Rate 12.5%','Cost £1,234.56; use that number.',
                 'Date 77.88.2026','In 2026 call us','Call Section 123',
                 'Version 07.123456789','Rate 12.5%\nCall 8899'):
        check(text,'numeric_isolation',lambda t=text:blocked(t))

    for field,path in [('title','title'),('description','description'),('quick_answer','quick_answer'),
                       ('figure-title','figure/title'),('evidence-finding','evidence/0/finding')]:
        def derived_fact(field=field,path=path):
            text='Value 0.123456789';p=page(text,field)
            if field=='figure-title':p['figure']['steps']=[{'check':'Pause','then':'Check safely'}]
            r=review_for(p,c,numeric_facts=(sr.NumericFact(path,text,'decimal'),),approved_fields={
                path:text, 'figure/type':'decision-flow', 'figure/alt':'Decision flow',
                'figure/steps/0/check':'Pause', 'figure/steps/0/then':'Check safely'})
            return text in Fragment(render(p,r)).text
        check('reviewed number '+field,'derived',derived_fact)
    for field in ('evidence-finding','example-message'):
        p=page('Check independently.',field)
        path='evidence/0/finding' if field=='evidence-finding' else 'message_examples/0/message'
        check('generated date '+field,'derived',lambda p=p,path=path:bool(render(p,review_for(p,c,
            approved_fields={path:'Check independently.'}))))

    # Real serializer + actual quarantine artifact. No mock of the gate or writer.
    for text,routes,approved in [('Check safely.',['fixture-service:web'],True),
        ('Check safely.',['unknown:route'],False),('Call 01234 567890',['fixture-service:web'],False),
        (payloads[8],['fixture-service:web'],False)]:
        def persistence(text=text,routes=routes,approved=approved):
            p=page(text);p['reporting_routes']=routes;r=review_for(p,c,
                approved_fields={'sections/0/1':'Check safely.'})
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/'posts.json';path.write_text('[]\n');before=path.read_bytes();q=Path(d)/'quarantine'
                try: writer.save_posts(str(path),[p],reporting_canon=c,reporting_reviews={p['slug']:packet_for(p, c, r)},quarantine_dir=str(q),today='2026-10-09')
                except sr.ReportingError:
                    files=list(q.glob('*.json'))
                    return not approved and path.read_bytes()==before and len(files)==1 and json.loads(files[0].read_text())['post']==p
                loaded=json.loads(path.read_text())[0]
                return approved and loaded==p and bool(render(loaded,r)) and not q.exists()
        check(text+repr(routes),'writer',persistence)
    for value in (None, [], ['unknown:route'], {'url':'https://attacker.example'}):
        p=fixture_page();p['reporting_routes']=value
        check('normalizer preserves '+repr(value),'writer',lambda p=p:
            writer.normalise(p,writer.Topic('test','test','email'),'2026-10-09')==p
            and search.normalise_search_console_post(p,'test','email','2026-10-09')==p)
    def repeat_approval():
        p=fixture_page();r=review_for(p,c)
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'posts.json';target.write_text('[]\n')
            writer.save_posts(str(target),[p],reporting_canon=c,reporting_reviews={p['slug']:packet_for(p, c, r)})
            before=target.read_bytes();changed=copy.deepcopy(p);changed['sections'][0][1]=payloads[10]
            return (rejects(lambda:writer.save_posts(str(target),[changed],reporting_canon=c,reporting_reviews={p['slug']:packet_for(changed, c, r)}))
                and rejects(lambda:render(changed,r)) and target.read_bytes()==before)
    check('approval binding repeated on write/render','writer',repeat_approval)
    def no_provider():
        p=fixture_page()
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'posts.json';target.write_text('[]\n')
            return rejects(lambda:writer.save_posts(str(target),[p],reporting_canon=c)) and target.read_text()=='[]\n'
    check('normal writer has no approval provider','writer',no_provider)
    def no_downgrade():
        p=fixture_page()
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'posts.json';target.write_text(json.dumps([p]));before=target.read_bytes()
            q=copy.deepcopy(p);del q['reporting_routes']
            return rejects(lambda:writer.save_posts(str(target),[q])) and target.read_bytes()==before
    check('existing structured record cannot downgrade','writer',no_downgrade)
    def producer_quarantine(producer, no_gate=False, downgrade=False):
        """Run actual CLI control flow with producer/network clients replaced.

        The fake SDK has no messages API: accidentally invoking a model fails.
        run_gate, quarantine_post and the serializer are real functions.
        """
        p=fixture_page();p['reporting_routes']=['unknown:route']
        original=fixture_page()
        if downgrade:
            p=copy.deepcopy(original);del p['reporting_routes']
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            target=Path(d)/'posts.json';qdir=Path(d)/'quarantine'
            initial=[original] if producer is rewrite else []
            target.write_text(json.dumps(initial,indent=2)+'\n');before=target.read_bytes()
            stack.enter_context(patch.dict('os.environ',{'ANTHROPIC_API_KEY':'offline-fixture'},clear=True))
            stack.enter_context(patch.dict(sys.modules,{'anthropic':SimpleNamespace(Anthropic=lambda **kw:object())}))
            stack.enter_context(patch.object(producer,'quarantine_post',lambda post,result,today:
                gate.quarantine_post(post,result,today,qdir=str(qdir))))
            if producer is writer:
                argv=['fixture','unused.csv','--posts',str(target),'--mode','template','--gate-no-llm']
                stack.enter_context(patch.object(writer,'read_topics',return_value=[writer.Topic('fixture','fixture','email')]))
                stack.enter_context(patch.object(writer,'fallback_post',return_value=p))
            elif producer is rewrite:
                argv=['fixture','--posts',str(target),'--gate-no-llm']
                stack.enter_context(patch.object(rewrite,'claude_post',return_value=p))
            else:
                argv=['fixture'];gap={'query':'fixture','impressions':10,'position':1,'coverage':0}
                stack.enter_context(patch.object(search,'POSTS_FILE',target))
                stack.enter_context(patch.object(search,'get_search_console_service',return_value=object()))
                stack.enter_context(patch.object(search,'get_trending_queries',return_value=[gap]))
                stack.enter_context(patch.object(search,'find_content_gaps',return_value=[gap]))
                stack.enter_context(patch.object(search,'generate_article',return_value=p))
                # The deterministic gate remains real; the LLM stub must never run.
                stack.enter_context(patch.object(gate,'judge_llm',side_effect=AssertionError('offline test attempted judge')))
            if no_gate:argv.append('--no-gate')
            stack.enter_context(patch.object(sys,'argv',argv))
            # Invalid structured input must never reach a model, even when the
            # normal writer would request its judge after deterministic checks.
            stack.enter_context(patch.object(gate,'_CANON',c))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):producer.main()
            files=list(qdir.glob('*.json'))
            return target.read_bytes()==before and len(files)==1 and json.loads(files[0].read_text())['post']==p
    for producer in (writer,rewrite,search):
        check(producer.__name__+' actual quarantine','writer',lambda p=producer:producer_quarantine(p))
    for producer in (writer,rewrite):
        check(producer.__name__+' no-gate cannot bypass structured validation','writer',lambda p=producer:producer_quarantine(p,True))
    check('rewrite cannot drop structured mode','writer',lambda:producer_quarantine(rewrite,True,True))
    def search_without_eligible_contract():
        # A complete renderer fixture is not production evidence. The real
        # eligibility path must hold before even this disposable SDK is called.
        calls=[]
        fake=SimpleNamespace(messages=SimpleNamespace(create=lambda **kw:calls.append(kw)))
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            stack.enter_context(patch.dict('os.environ',{'BTS_REVIEW_ENVIRONMENT':'production',
                'BTS_REVIEW_STORE':str(Path(d).resolve()),'BTS_PRODUCTION_TRUST_SHA256':''}))
            stack.enter_context(patch.dict(sys.modules,{'anthropic':SimpleNamespace(Anthropic=lambda **kw:fake)}))
            stack.enter_context(patch.object(writer,'CANON',c))
            with redirect_stdout(io.StringIO()):
                result=search.generate_article({'query':'fixture','category':'email','impressions':10,'position':1},'offline-fixture')
            return result is None and not calls
    check('Search Console without production eligibility never calls SDK','writer',search_without_eligible_contract)
    def search_response_quarantine():
        # Exercise generate_article itself with an offline SDK response. The
        # missing slug and malformed section must survive to actual quarantine.
        p={'reporting_routes':['unknown:route'],'sections':[{'malformed':'shape'}]}
        fake=SimpleNamespace(messages=SimpleNamespace(create=lambda **kw:
            SimpleNamespace(content=[SimpleNamespace(type='text',text=json.dumps(p))])))
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules,{'anthropic':SimpleNamespace(Anthropic=lambda **kw:fake)}))
            stack.enter_context(patch.object(writer,'CANON',c))
            # This test owns response propagation, not trust enrollment. Supply
            # only its eligibility seam; parser, normalizer, gate and quarantine
            # stay real. The separate test above checks actual fail-closed
            # eligibility, and reporting_pilot_selftest checks real signatures.
            stack.enter_context(patch('reporting_trust.environment',return_value='production'))
            stack.enter_context(patch('reporting_eligibility.publication_endorsed_ids',return_value=('fixture-service:web',)))
            with redirect_stdout(io.StringIO()):
                result=search.generate_article({'query':'fixture','category':'email','impressions':10,'position':1},'offline-fixture')
            if result!=p:return False
            rejected=gate.run_gate(result,use_llm=False,reporting_canon=c)
            gate.quarantine_post(result,rejected,'2026-10-09',qdir=d)
            files=list(Path(d).glob('*.json'))
            return not rejected.passed and len(files)==1 and json.loads(files[0].read_text())['post']==p
    check('Search Console raw response reaches quarantine','writer',search_response_quarantine)
    # Deliberately RED: cross-field semantics are not established by the
    # per-field fact grammar or citation word checks. Preserve these blockers
    # for independent review; do not invert their expectations to green.
    def residual(name):
        p=fixture_page()
        if name=='numeric':
            p['sections']=[['Reporting','Dial the value in the following paragraph.'],
                           ['Details','Count 07123456789']]
        else:
            p['sections']=[['Reporting','For reporting, choose the blue item at the foot of this page.']]
            p['sources_checked']=[['Independent evidence','https://attacker.example/intake']]
        r=review_for(p,c)
        result=gate.run_gate(p,use_llm=False,reporting_canon=c,reporting_review=packet_for(p, c, r))
        return not result.passed and rejects(lambda:render(p,r))
    check('numeric fact used as reporting destination across fields','residual_boundary',lambda:residual('numeric'))
    check('indirect citation instruction outside word checks','residual_boundary',lambda:residual('citation'))
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--json',action='store_true');args=parser.parse_args()
    rows=run_cases()
    if args.json: print(json.dumps(rows,ensure_ascii=False,indent=2))
    else:
        for group in sorted({r['group'] for r in rows}):
            subset=[r for r in rows if r['group']==group]
            print(f"{group}: {sum(r['ok'] for r in subset)}/{len(subset)} PASS")
        for r in rows:
            if not r['ok']:print('FAIL:',r['group'],r['name'],r['detail'])
        print(f"Effective output: {sum(r['ok'] for r in rows)} PASS / {sum(not r['ok'] for r in rows)} FAIL")
    return int(any(not r['ok'] for r in rows))


if __name__=='__main__':raise SystemExit(main())
