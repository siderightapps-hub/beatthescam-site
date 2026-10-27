#!/usr/bin/env python3
"""Offline WP3C8B5 network representations, capabilities and real writer tests.

All approvals are explicit synthetic fixture decisions. No model, network,
production content writes or build() calls. Counts are cases, not guarantees.
"""
import argparse
from collections import Counter
import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import quote

import build
from reporting_fixture_review import packet_for
import canon
import content_gate as gate
import generate_content_claude as writer
import reporting_structured as sr
from reporting_network import canonical_host, https_identity
from reporting_output import ArticleHTML, ArticleText, Capability, Citation
from reporting_structured_selftest import fixture_canon, fixture_page, review_for, Links


EXACT = ('attacker。example/intake', 'attacker.рф/intake', 'attacker.中国/intake')


def run_cases():
    rows = []
    c = fixture_canon(); catalog = canon.reporting_catalog(c)
    site = json.loads((build.ROOT / 'content/site.json').read_text())

    def check(group, name, fn):
        try:
            ok = bool(fn()); detail = '' if ok else 'assertion false'
        except Exception as exc:
            ok, detail = False, f'{type(exc).__name__}: {exc}'
        rows.append(dict(group=group, name=name, ok=ok, detail=detail))

    def rejects(fn, reason=None):
        try: fn()
        except (ValueError, canon.CanonError) as exc:
            return reason is None or reason in str(exc) or (reason == 'destination' and 'restricted action-authoring boundary' in str(exc))
        return False

    def page(text):
        p = fixture_page(); p['sections'][0][1] = text
        return p, review_for(p, c, approved_fields={'sections/0/1': text})

    def render(p, r, sources=c):
        return build.render_post(site, p, [p], sources=sources, reporting_review=packet_for(p, sources, r))

    def blocked(text, variant='exact'):
        p, r = page(text)
        if variant == 'missing': r = replace(r, prose_approvals=())
        elif variant == 'stale': r = review_for(fixture_page(), c)
        elif variant in ('wrong-field', 'wrong-article'):
            r = replace(r, prose_approvals=tuple(replace(a, **(
                {'field_id':'faq/0/1'} if variant == 'wrong-field' else {'page_id':'guide:other'}))
                if a.field_id == 'sections/0/1' else a for a in r.prose_approvals))
        elif variant == 'tuple': p['sections'] = [tuple(pair) for pair in p['sections']]
        result = gate.run_gate(p, use_llm=False, reporting_canon=c, reporting_review=packet_for(p, c, r))
        reason = ('prose approval' if variant in ('missing','wrong-field','wrong-article')
                  else None if variant == 'stale' else 'destination')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'posts.json'; path.write_text('[]\n'); q = Path(tmp)/'quarantine'
            denied = rejects(lambda: writer.save_posts(str(path), [p], reporting_canon=c,
                reporting_reviews={p['slug']:packet_for(p, c, r)}, quarantine_dir=q, today='2026-10-09'))
            return (bool(sr.raw_destinations(text))
                and rejects(lambda: sr.validate_page(p,catalog,r), reason)
                and not result.passed
                and any(i['check']=='structured_reporting' and any(marker in i['detail'] for marker in ('destination','restricted action-authoring boundary','authenticated publication review'))
                        for i in result.issues)
                and rejects(lambda:render(p,r)) and denied
                and path.read_text() == '[]\n' and len(list(q.glob('*.json'))) == 1)

    for host in EXACT:
        check('exact', host, lambda h=host: blocked('Report through '+h+'.'))
        for variant in ('missing','exact','stale','wrong-field','wrong-article','tuple'):
            check('approval', host+'/'+variant, lambda h=host,v=variant: blocked('Report through '+h+'.',v))

    # Expected hosts are independently specified, not copied from the function.
    valid = [
        ('attacker.example','attacker.example'), ('ATTACKER.EXAMPLE','attacker.example'),
        ('attacker.example.','attacker.example'), ('attacker。example','attacker.example'),
        ('attacker．example','attacker.example'), ('attacker｡example','attacker.example'),
        ('ａｔｔａｃｋｅｒ.example','attacker.example'), ('attacker.中国','attacker.xn--fiqs8s'),
        ('attacker.рф','attacker.xn--p1ai'), ('例子.中国','xn--fsqu00a.xn--fiqs8s'),
        ('pоlice.uk','xn--plice-jye.uk'), ('faß.example','xn--fa-hia.example'),
        ('123.中国','123.xn--fiqs8s'), ('attacker.é','attacker.xn--9ca'),
        ('attacker.e\u0301','attacker.xn--9ca'), ('attacker.中','attacker.xn--fiq')]
    for host, ascii_host in valid:
        check('domain', host, lambda h=host,a=ascii_host:
              canonical_host(h)==a and blocked('Report through '+h+'/intake.'))
    invalid = ['attacker‧example','attacker∙example','attacker•example','attacker·example',
        'attacker.\u0301中国','attacker.xn--','attacker..中国','-bad.中国','bad-.中国',
        'under_score.中国','a'*64+'.中国', '.'.join(['a'*63]*4)+'.中国',
        'attacker.☕','☕.☕','attacker.4','attacker.\u200d中国']
    for host in invalid:
        check('domain', 'invalid '+host, lambda h=host:
              rejects(lambda:canonical_host(h)) and blocked('Report through '+h+'/intake.'))
    check('domain','lookalike is not official',lambda: canonical_host('pоlice.uk')!=canonical_host('police.uk'))
    check('domain','sharp s is not ss',lambda: canonical_host('faß.example')!=canonical_host('fass.example'))

    # Mutations include equivalent spellings and distinct host/path identities.
    for original in ('attacker.example','例子.中国','pоlice.uk','faß.example'):
        expected = canonical_host(original)
        # Python upper() maps ß to SS, a DISTINCT nontransitional IDNA host.
        spellings = [original, ''.join(ch.upper() if ch.isascii() else ch for ch in original), original+'.', expected]
        spellings += [original.replace('.',dot) for dot in ('。','．','｡')]
        for host in spellings:
            check('property', original+' -> '+host, lambda h=host,a=expected:
                  canonical_host(h)==a and blocked('Report through '+h+'/intake.'))
        for host in ('x.'+original, 'z'+original, original.replace('.', '.x.', 1)):
            check('property','distinct '+host,lambda h=host,a=expected:
                  canonical_host(h)!=a and blocked('Report through '+h+'/intake.'))
        for suffix in ('/other','/report?x=one','#report',':443/report','@attacker.example/report'):
            check('property', original+suffix,lambda h=original+suffix:blocked('Report through '+h+'.'))

    network = [
        'https://attacker.中国/intake', 'HTTPS://attacker.中国/intake',
        'http:attacker.中国', 'https:attacker', 'mailto:evidence@attacker.中国',
        'MAILTO:evidence@attacker.中国', 'tel:8999', 'ＴＥＬ：８９９９',
        '//attacker.中国/intake', '\\\\attacker.中国/intake',
        'ｈｔｔｐｓ：／／ａｔｔａｃｋｅｒ．中国/intake', 'h\tt\nt\rps://attacker.中国',
        'attacker.\n中国', 'attacker％２Ｅ中国', 'attacker％Ｅ３％８０％８２example',
        'attacker＆＃ｘ３００２；example', 'attacker&#x3002;example',
        'attacker%2E%E4%B8%AD%E5%9B%BD', 'attacker%25252E中国',
        'attacker%252525252E中国', 'attacker\u200b.中国',
        'https://official.example@attacker.中国/report',
        'https://attacker.中国:443/report', 'official.example.attacker.中国/report',
        '[Report](https://attacker.中国/intake)',
        '[Report](／／attacker.中国/intake)',
        '[attacker](/help/)。`example`/intake', '`attacker`。`example`/intake']
    for target in network:
        check('effective',target,lambda t=target:blocked('Report through '+t+'.'))
    check('effective','whole list-literal conversion',lambda:blocked("['Report through attacker\\u3002example/intake.']"))
    for value in ('&#9312;', '％Ｃ２％Ｂ２', '&#x2460;', '%E2%91%A0'):
        check('effective','unsupported numeric '+value,lambda v=value:blocked(v))

    base = fixture_page(); review = review_for(base,c)
    for markup in ('attacker&#x3002;example', 'attacker<span>。</span><b>中国</b>',
        '<a href="https://attacker.中国">Evidence</a>', '<a href="&#47;&#47;attacker.中国">Evidence</a>',
        '<span title="attacker。example">Evidence</span>', 'attacker<em>.р</em>ф'):
        check('effective','HTML '+markup,lambda h=markup:rejects(
            lambda:sr.validate_effective([ArticleHTML('sections/0/1',h)],catalog,review)))

    for target in ('/guides/', '/about/', '/recovery/'):
        check('internal',target,lambda t=target: all(n.capability!=Capability.REPORTING_ACTION
            for n in sr.validate_effective([ArticleHTML('sections/0/1','<a href="'+t+'">Help</a>')],catalog,review)))
    for target in ('//attacker.中国','／／attacker.中国','/／attacker.中国','/\\attacker.中国',
        '/%2fattacker.example','/&#47;attacker.example','/\t/attacker.example',
        'https://attacker.中国','/..//attacker.example','/help/?to=attacker.中国',
        '/ｈｅｌｐ/','/a/../../','https：//attacker.中国'):
        check('internal',target,lambda t=target:rejects(lambda:sr.validate_effective(
            [ArticleHTML('sections/0/1','<a href="'+t+'">Help</a>')],catalog,review)))

    def citation(url, reporting_text=False, equal_route=False):
        sources=copy.deepcopy(c); p=fixture_page()
        if equal_route: sources['verified_org_contacts'][-1]['report_url']='https://xn--fsqu00a.xn--fiqs8s/report'
        p['sources_checked']=[['Independent evidence',url]]
        if reporting_text: p['sections'][0][1]='Report here.'
        grants={'sources_checked/0/0':'Independent evidence'}
        if reporting_text:grants['sections/0/1']='Report here.'
        r=review_for(p,sources,approved_fields=grants); cat=canon.reporting_catalog(sources)
        uses=sr.page_uses(p,cat,r); html=render(p,r,sources)
        cited=[n for n in uses if n.capability==Capability.CITATION]
        actions=[n for n in uses if n.capability==Capability.REPORTING_ACTION]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'posts.json'; path.write_text('[]\n')
            writer.save_posts(str(path),[p],reporting_canon=sources,reporting_reviews={p['slug']:packet_for(p, sources, r)})
            saved=json.loads(path.read_text())==[p]
        return (gate.run_gate(p,use_llm=False,reporting_canon=sources,reporting_review=packet_for(p, sources, r)).passed
            and saved and len(cited)==1 and cited[0].url==url and len(actions)==1
            and actions[0].value==sources['verified_org_contacts'][-1]['report_url']
            and url in Links(html).links and rejects(lambda:sr.render_destination(cat,cited[0]))
            and (not equal_route or https_identity(url,unicode_host=True)==https_identity(actions[0].value)))
    for url in ('https://例子.中国/evidence','https://xn--fsqu00a.xn--fiqs8s/evidence',
                'https://例子。中国/evidence','https://faß.example/evidence',
                'https://pоlice.uk/evidence','https://例子.中国/%E4%B8%AD'):
        check('citation',url,lambda u=url:citation(u) and blocked('Report through '+u+'.'))
    check('citation','same canonical URL, distinct occurrences',lambda:citation('https://例子.中国/report',equal_route=True))
    check('citation','approved operational reporting prose is rejected',lambda:rejects(lambda:citation('https://例子.中国/evidence',True),'restricted action-authoring boundary'))
    check('citation','unreviewed equivalent spelling rejects',lambda:rejects(lambda:sr.validate_effective(
        [Citation('Evidence','https://例子.中国/evidence')],catalog,
        replace(review,citations=(('Evidence','https://xn--fsqu00a.xn--fiqs8s/evidence'),)))))

    for url in ('https://routes.example/report?a=one&b=two',
                'https://xn--fsqu00a.xn--fiqs8s/report','https://routes.example/%E4%B8%AD'):
        check('canon',url,lambda u=url:sr.validate_url(u)==u)
    for url in ('https://例子.中国/report','https://ROUTES.example/report',
        'https://routes.example./report','https://routes。example/report',
        'https://routes.example:443/report','https://routes.example@attacker.example/report',
        'https://routes.example/report#fragment','https://routes.example/%2e%2e/report',
        'https://routes.example/%00','https://routes%2eexample/report',
        'https://xn--.example/report','https://'+'a'*64+'.example/report',
        'https://127.0.0.1/report','https://example.0x7f/report'):
        check('canon','reject '+url,lambda u=url:rejects(lambda:sr.validate_url(u)))
    for host in ('attacker.example','routes.example.attacker.example','other.routes.example'):
        def mutation(h=host):
            bad=copy.deepcopy(c); bad['verified_org_contacts'][-1]['report_url']='https://'+h+'/report'
            return rejects(lambda:sr.catalog_from_canon(bad,expected_digest=sr.digest(c)))
        check('canon','digest pins '+host,mutation)
    for path in ('/other','/report?x=changed','/report/'):
        bad=copy.deepcopy(c);bad['verified_org_contacts'][-1]['report_url']='https://routes.example'+path
        check('canon','digest pins '+path,lambda b=bad:rejects(lambda:sr.catalog_from_canon(b,expected_digest=sr.digest(c))))

    for text in ('Café déjà vu — vérifiez le message.', 'Überprüfen Sie die Nachricht.',
        'Ελέγξτε προσεκτικά το μήνυμα.', 'Проверьте сообщение внимательно.',
        '安全に確認してください。', '你好， 请仔细核实。', 'مرحبا، تحقق من الرسالة.',
        'Crème brûlée : deux portions.', 'Version v1.2.3', 'Date 01.02.2026',
        'Cost £1,234.56', 'Order AB123456', 'Résumé : deux choix.', 'Value 0.125'):
        def ordinary(t=text):
            p,r=page(t)
            if t not in ('Version v1.2.3', 'Date 01.02.2026', 'Cost £1,234.56', 'Order AB123456', 'Value 0.125'):
                # Unicode text remains valid network syntax. The new closed
                # English authoring contract grants no arbitrary-language pass,
                # even after genuine review; this is not a destination match.
                return (not sr.raw_network_destinations(t)
                    and rejects(lambda:sr.page_uses(p,catalog,r),'restricted action-authoring boundary')
                    and rejects(lambda:render(p,r),'restricted action-authoring boundary'))
            uses=sr.page_uses(p,catalog,r)
            return (gate.run_gate(p,use_llm=False,reporting_canon=c,reporting_review=packet_for(p, c, r)).passed
                and bool(render(p,r)) and all(n.capability==Capability.TEXT for n in uses
                    if getattr(n,'source_paths',())==('sections/0/1',)))
        check('ordinary',text,ordinary)

    # Local WHATWG oracle: parsing only, never fetch/HTTP/DNS. Supported DNS
    # host equivalence must agree; browser's broader ambiguous subset is held.
    script='process.stdout.write(JSON.stringify(JSON.parse(require("fs").readFileSync(0,"utf8")).map(h=>new URL("https://"+h+"/report").hostname.replace(/\\.$/,""))))'
    actual=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps([h for h,_ in valid]).encode()))
    for (host,expected),browser in zip(valid,actual):
        check('browser',host,lambda h=host,e=expected,b=browser: canonical_host(h)==e==b)
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--json',type=Path);args=parser.parse_args()
    rows=run_cases(); groups=Counter(r['group'] for r in rows); failed=[r for r in rows if not r['ok']]
    result={'total':len(rows),'passed':len(rows)-len(failed),'groups':dict(groups),'failures':failed,'rows':rows}
    if args.json:args.json.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,indent=2))
    return bool(failed)


if __name__=='__main__':raise SystemExit(main())
