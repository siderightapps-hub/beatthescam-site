#!/usr/bin/env python3
"""Offline contextual prose approval and capability regressions (WP3C8B4).

Review grants below are explicit test-author decisions, not a prose classifier.
No helper approves all candidate fields. A fresh dishonest human approval is
outside the model; tests do prove even that grant cannot exempt raw destinations.
"""
from collections import Counter
from dataclasses import replace, FrozenInstanceError
import copy
import json
from pathlib import Path
import tempfile
import argparse

import build
from reporting_fixture_review import packet_for
import canon
import content_gate as gate
import generate_content_claude as writer
import reporting_structured as sr
from reporting_action_render import ActionComponent
from reporting_output import Capability as C, Provenance as P, Citation, ArticleText, ArticleHTML
from reporting_structured_selftest import fixture_page, fixture_canon, review_for, Links


def run_cases():
    rows = []
    sources = fixture_canon(); catalog = canon.reporting_catalog(sources)
    site = json.loads((build.ROOT / 'content/site.json').read_text())

    def check(group, name, fn):
        try:
            ok = bool(fn()); detail = '' if ok else 'assertion false'
        except Exception as exc:
            ok, detail = False, f'{type(exc).__name__}: {exc}'
        rows.append(dict(group=group, name=name, ok=ok, detail=detail))

    def rejected(fn, contains=None):
        try: fn()
        except (sr.ReportingError, canon.CanonError) as exc:
            return contains is None or contains in str(exc)
        return False

    def render(p, r):
        return build.render_post(site, p, [p], sources=sources, reporting_review=packet_for(p, sources, r))

    def blocked_everywhere(p, r):
        result = gate.run_gate(p, use_llm=False, reporting_canon=sources, reporting_review=packet_for(p, sources, r))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'posts.json'; path.write_text('[]\n'); q = Path(tmp)/'quarantine'
            blocked = rejected(lambda: writer.save_posts(str(path), [p], reporting_canon=sources,
                reporting_reviews={p['slug']:packet_for(p, sources, r)}, quarantine_dir=q, today='2026-10-09'))
            return (not result.passed and rejected(lambda: render(p, r)) and blocked
                    and path.read_text() == '[]\n' and len(list(q.glob('*.json'))) == 1)

    # Exactly the two original failures, with independent approvals for the
    # benign facts/labels. The harmful instruction itself is NOT approved.
    for kind in ('numeric', 'citation'):
        p = fixture_page()
        if kind == 'numeric':
            p['sections'] = [['Reporting','Dial the value in the following paragraph.'],
                             ['Details','Count 07123456789']]
            approved = {'sections/0/0':'Reporting', 'sections/1/0':'Details',
                        'sections/1/1':'Count 07123456789'}
        else:
            p['sections'] = [['Reporting','For reporting, choose the blue item at the foot of this page.']]
            p['sources_checked'] = [['Independent evidence','https://attacker.example/intake']]
            approved = {'sections/0/0':'Reporting', 'sources_checked/0/0':'Independent evidence'}
        r = review_for(p, sources, approved_fields=approved)
        check('exact', kind, lambda p=p,r=r: blocked_everywhere(p,r))

    variants = [
        ('numeric-close', 'Ring the quantity shown earlier.', 'body', 'Count 07123456789'),
        ('numeric-rearranged', 'For alerting the team, type the earlier quantity into your messaging application.', 'faq', 'Count 8999'),
        ('numeric-same-field', 'Count 07123456789. Dial that value.', 'body', None),
        ('numeric-different-field', 'Use the quantity in the heading to alert the investigators.', 'faq', 'Count 07123456789'),
        ('citation-close', 'Choose the blue item below to pass evidence to investigators.', 'body', None),
        ('citation-rearranged', 'Select the blue item beneath the article to pass your evidence to the investigators.', 'faq', None),
        ('citation-same-field', 'Report through https://attacker.example/intake.', 'body', None),
        ('citation-different-field', 'Choose the evidence item to send your report.', 'title', None)]
    for name, text, field, fact in variants:
        p = fixture_page(); grants = {}
        if fact:
            p['sections'].append(['Facts',fact]); grants.update({'sections/1/0':'Facts','sections/1/1':fact})
        if name.startswith('citation'):
            p['sources_checked'] = [['Independent evidence','https://attacker.example/intake']]
            grants['sources_checked/0/0'] = 'Independent evidence'
        if field == 'body': p['sections'][0][1] = text
        elif field == 'faq': p['faq'][0][1] = text
        else: p['title'] = text
        r = review_for(p,sources,approved_fields=grants)
        check('regression_variants',name,lambda p=p,r=r: blocked_everywhere(p,r))

    base = fixture_page(); base_review = review_for(base,sources)
    for field, text in list(sr.approval_fields(base)):
        # Replace only the page digest to simulate a caller refreshing routing
        # review while accidentally retaining old semantic field approvals.
        changed = copy.deepcopy(base); parts=field.split('/'); target=changed
        for part in parts[:-1]: target=target[int(part)] if isinstance(target,list) else target[part]
        key=int(parts[-1]) if isinstance(target,list) else parts[-1]
        target[key]=text+' '
        ctx=replace(base_review,page_sha256=sr.digest(changed))
        check('approval', 'byte edit '+field, lambda p=changed,r=ctx: blocked_everywhere(p,r))
    first=base_review.prose_approvals[0]
    for key,value in [('schema_version','reporting-prose/v0'),('page_id','guide:other'),
        ('field_id','faq/99/1'),('content_sha256','0'*64),('page_sha256','0'*64),('canon_sha256','0'*64),
        ('scope','reporting-action'),('reviewer',''),('approved_at','2026-10-10T00:00:00Z'),
        ('approved_at','2026-10-09T00:00:00'),('approved_at','not-a-time')]:
        r=replace(base_review,prose_approvals=(replace(first,**{key:value}),)+base_review.prose_approvals[1:])
        check('approval',key+' '+str(value),lambda r=r: blocked_everywhere(base,r))
    for name,approvals in [('missing',()),('partial',base_review.prose_approvals[:-1]),
                           ('duplicate',base_review.prose_approvals+(first,)),('serialized',tuple([first.__dict__]))]:
        r=replace(base_review,prose_approvals=approvals)
        check('approval',name,lambda r=r: blocked_everywhere(base,r))
    # Context edit invalidates even unchanged field permissions.
    p=copy.deepcopy(base);p['sources_checked']=[['Evidence','https://routes.example/evidence']]
    r=replace(base_review,page_sha256=sr.digest(p),citations=tuple(map(tuple,p['sources_checked'])))
    check('approval','new citation invalidates context',lambda:blocked_everywhere(p,r))
    p=copy.deepcopy(base);p['prose_approvals']=[a.__dict__ for a in base_review.prose_approvals]
    check('approval','draft cannot self-approve',lambda:blocked_everywhere(p,review_for(p,sources)))

    # Explicitly grant bad prose here: raw policy must remain independent of
    # semantic approval, even if a human makes that erroneous decision.
    for text in ['Call 07123456789.', 'Call 01234 567890.', 'Text 8999.',
        'Email evidence@routes.example.', 'Report at https://routes.example/report?a=one&b=two.',
        'Call 07.12.34.56.78.9.', 'Call ٠٧١٢٣٤٥٦٧٨٩.', 'Call `07``123456789`.',
        '[Report](https://attacker.example/intake)', 'Count 07123456789. Dial it.']:
        p=fixture_page();p['sections'][0][1]=text
        r=review_for(p,sources,approved_fields={'sections/0/1':text})
        check('approval_not_destination',text,lambda p=p,r=r:blocked_everywhere(p,r))

    uses=sr.page_uses(base,catalog,base_review)
    check('capability','every reporting use is resolver-owned',lambda: all(
        isinstance(n,ActionComponent) and n.action is catalog.resolve(n.action.route_id)
        and n.validate() is None
        for n in uses if n.capability == C.REPORTING_ACTION))
    for kind in ('web','email','phone','text'):
        node=catalog.destinations(['fixture-service:'+kind])[0]
        check('capability','resolved '+kind,lambda node=node: node.capability==C.REPORTING_ACTION
              and node.provenance==P.REPORTING_ROUTE and bool(sr.render_destination(catalog,node)))
        check('capability','no channel substitution '+kind,lambda node=node: rejected(lambda:
            sr.ReportingDestination(catalog,node.action,sr.Destination(node.channel.kind,node.value))))
        check('capability','no citation substitution '+kind,lambda node=node: rejected(lambda:
            sr.render_destination(catalog,Citation('Evidence',node.value))))
    for node in (Citation('Evidence','https://routes.example/evidence'),
                 ArticleText('sections/0/1','Count 01234567890'),
                 ArticleHTML('sections/0/1','Read <a href="/recovery/">help</a>.')):
        r=replace(base_review,citations=(('Evidence','https://routes.example/evidence'),))
        check('capability',repr(node),lambda node=node,r=r:all(n.capability!=C.REPORTING_ACTION
            for n in sr.validate_effective([node],catalog,r)))

    numeric = [('phone','07123456789',None,False),('canon','01234567890',None,False),
        ('mutation','01234567891',None,False),('price','Cost £1,234.56','money',True),
        ('statistic','Count 01234567890','count',True),('date','Date 01.02.2026','date',True),
        ('legislation','Section 123','legislation',True),('version','Version 1.2.3','version',True),
        ('ip','Address 192.0.2.10','ip',True)]
    field_paths={'body':'sections/0/1','quick_answer':'quick_answer','faq':'faq/0/1',
        'title':'title','metadata':'description','citation_title':'sources_checked/0/0'}
    for field,path in field_paths.items():
        for name,text,kind,allowed in numeric:
            def case(field=field,path=path,text=text,kind=kind,allowed=allowed):
                p=fixture_page()
                if field=='body':p['sections'][0][1]=text
                elif field=='faq':p['faq'][0][1]=text
                elif field=='citation_title':p['sources_checked']=[[text,'https://routes.example/evidence']]
                else:p[path]=text
                facts=(sr.NumericFact(path,text,kind),) if kind else ()
                r=review_for(p,sources,approved_fields={path:text},numeric_facts=facts)
                if not allowed:return blocked_everywhere(p,r)
                output=render(p,r); nodes=sr.page_uses(p,catalog,r)
                text_uses=[n for n in nodes if getattr(n,'source_paths',())==(path,)]
                return bool(output) and bool(text_uses) and all(n.capability!=C.REPORTING_ACTION for n in text_uses)
            check('numeric_matrix',field+'/'+name,case)
    for name,text,kind,allowed in numeric:
        def citation_number(name=name,text=text):
            # Numeric syntax in a citation URL is still URL data. Label separately approved.
            url='https://routes.example/data/'+''.join(ch for ch in text if ch.isascii() and (ch.isalnum() or ch=='.'))
            p=fixture_page();p['sources_checked']=[['Numeric evidence',url]]
            r=review_for(p,sources,approved_fields={'sources_checked/0/0':'Numeric evidence'})
            nodes=sr.page_uses(p,catalog,r)
            return any(isinstance(n,Citation) and n.url==url and n.capability==C.CITATION for n in nodes) and url in Links(render(p,r)).links
        check('numeric_matrix','citation_url/'+name,citation_number)
        def route_number(text=text,allowed=allowed):
            c=fixture_canon();c['verified_org_contacts'][-1]['phone']=text
            if allowed: return rejected(lambda:canon.reporting_catalog(c))
            cat=canon.reporting_catalog(c);n=cat.destinations(['fixture-service:phone'])[0]
            return n.value==text and n.capability==C.REPORTING_ACTION
        check('numeric_matrix','reporting_block/'+name,route_number)

    same_url='https://routes.example/report?a=one&b=two'
    citations=[('near report wording','Official guidance','https://routes.example/evidence',True),
        ('separate field','Evidence','https://sources.example/data',True),
        ('equal canon','Official guidance',same_url,True),
        ('generic homepage','Evidence','https://sources.example/',True),
        ('report-like anchor','Reporting guidance','https://sources.example/data',True),
        ('multiple','Evidence','https://sources.example/data',True),
        ('route plus identical citation','Official guidance',same_url,True),
        ('no route plus citation','Official guidance',same_url,False)]
    for name,label,url,route in citations:
        def citation_case(name=name,label=label,url=url,route=route):
            p=fixture_page();p['sources_checked']=[[label,url]]
            if not route:p['reporting_routes']=[]
            grants={'sources_checked/0/0':label}
            if not route:
                p['quick_answer']='Pause and check the request independently. Keep the original message.'
                grants['quick_answer']='Pause and check the request independently. Keep the original message.'
            if name=='multiple':
                p['sources_checked'].append(['Second evidence',same_url]);grants['sources_checked/1/0']='Second evidence'
            if name=='near report wording':
                p['sections'][0][1]='Use the reporting and support routes for their stated purposes.'
                grants['sections/0/1']='Use the reporting and support routes for their stated purposes.'
            r=review_for(p,sources,approved_fields=grants,allow_empty=not route)
            if name in ('near report wording', 'report-like anchor'):
                return rejected(lambda: sr.page_uses(p,catalog,r), 'restricted action-authoring boundary') and rejected(lambda: render(p,r), 'restricted action-authoring boundary')
            nodes=sr.page_uses(p,catalog,r);html=render(p,r)
            cite=[n for n in nodes if n.capability==C.CITATION]
            actions=[n for n in nodes if n.capability==C.REPORTING_ACTION]
            return len(cite)==len(p['sources_checked']) and bool(actions)==route and (
                route or ('id="reporting-routes"' not in html and 'or report it to' not in html)) and all(type(n) is Citation for n in cite)
        check('citation_matrix',name,citation_case)

    for kind in ('numeric','citation'):
        p=fixture_page();grants={}
        if kind=='numeric':
            p['sections'][0][1]='Count 01234567890';grants['sections/0/1']='Count 01234567890'
            p['reporting_routes']=['fixture-service:phone']
        else:
            p['sources_checked']=[['Official guidance',same_url]];grants['sources_checked/0/0']='Official guidance'
        r=review_for(p,sources,approved_fields=grants)
        def integration(p=p,r=r,kind=kind):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'posts.json'
                writer.save_posts(str(path),[p],reporting_canon=sources,reporting_reviews={p['slug']:packet_for(p, sources, r)})
                loaded=json.loads(path.read_text())[0];nodes=sr.page_uses(loaded,catalog,r)
                html=render(loaded,r)
                return loaded==p and bool(html) and sum(n.capability in (C.REPORTING_ACTION,C.CALL_ACTION) for n in nodes)==1 and (
                    any(n.capability==C.CITATION for n in nodes) if kind=='citation' else
                    any(n.provenance==P.NUMERIC_FACT and n.capability==C.TEXT for n in nodes))
        check('integration',kind+' valid counterpart and same value',integration)
    p=fixture_page();p['reporting_routes']=['unresolved-service:web']
    check('integration','unknown route quarantines',lambda:blocked_everywhere(p,review_for(p,sources)))
    # Transformation outputs retain source identity and never acquire route capability.
    text='Read [the recovery guide](/recovery/) and keep `evidence`.'
    p=fixture_page();p['faq'][0][1]=text
    r=review_for(p,sources,approved_fields={'faq/0/1':text})
    nodes=sr.page_uses(p,catalog,r)
    for projection in ('text','html','schema'):
        check('transformation',projection,lambda projection=projection:any(
            getattr(n,'source_paths',())==('faq/0/1',) and getattr(n,'projection',None)==projection
            and n.provenance==P.FAQ and n.capability==C.TEXT for n in nodes))
    check('transformation','internal navigation retains source',lambda:any(n.capability==C.INTERNAL_NAVIGATION
        and n.source_paths==('faq/0/1',) for n in nodes))

    # Independent patch review: foreign records cannot inject prose through
    # related cards, hub grids or their ItemList schema after page approval.
    other=fixture_page();other.pop('reporting_routes');other['slug']='foreign-guide'
    other['title']='Dial 07123456789 to report.'
    other['description']='Submit evidence at https://attacker.example/intake.'
    check('review_regressions','related guide prose excluded',lambda:
        other['title'] not in build.render_post(site,base,[base,other],sources=sources,
                                                reporting_review=packet_for(base, sources, base_review)))
    hub={k:v for k,v in base.items() if k in ('title','description','sections','faq','reporting_routes')}
    hub['intro']='Check safely.';hub['sources_checked']=[['Evidence','https://routes.example/evidence']]
    hr=review_for(hub,sources,approved_fields={'sources_checked/0/0':'Evidence'})
    check('review_regressions','hub grid and schema prose excluded',lambda:all(value not in
        build.render_category_page(site,'email',[other],hub=hub,reporting_sources=sources,reporting_review=packet_for(hub, sources, hr))
        for value in (other['title'],other['description'])))
    def wrong_hub():
        try:build.validate_category_hubs({'marketplace':hub},reporting_sources=sources,
                                        reporting_reviews={'marketplace':packet_for(hub, sources, hr)})
        except SystemExit:return True
        return False
    check('review_regressions','wrong hub rejected at preflight',wrong_hub)
    check('review_regressions','wrong hub rejected at render',lambda:rejected(lambda:
        build.render_category_page(site,'marketplace',[],hub=hub,reporting_sources=sources,reporting_review=packet_for(hub, sources, hr))))
    for slug in ('123-safe-steps','a1-safe-steps','7'):
        p=fixture_page();p['slug']=slug;r=review_for(p,sources)
        check('review_regressions','valid slug '+slug,lambda p=p,r=r:bool(render(p,r)))
    return rows


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--json');args=parser.parse_args()
    rows=run_cases();counts=Counter(r['group'] for r in rows)
    for group,count in sorted(counts.items()):
        print(f'{group}: {sum(r["ok"] for r in rows if r["group"]==group)}/{count} PASS')
    for row in rows:
        if not row['ok']:print('FAIL:',row['group'],row['name'],row['detail'])
    print(f'Provenance: {sum(r["ok"] for r in rows)} PASS / {sum(not r["ok"] for r in rows)} FAIL')
    if args.json:Path(args.json).write_text(json.dumps(rows,indent=2)+'\n')
    raise SystemExit(int(any(not r['ok'] for r in rows)))
