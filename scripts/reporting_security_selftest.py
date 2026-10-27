#!/usr/bin/env python3
"""Offline WP3D8 regressions and deterministic representation properties.

Synthetic canon/review fixtures only. No build, network, corpus writes or live
approval. Each rejection uses a freshly bound review so digest drift cannot
hide a lexical defect. Node's URL parser checks actual emitted HTML hrefs.
"""
import argparse
from collections import Counter
import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import unicodedata

import build
from reporting_fixture_review import packet_for
import canon
import content_gate as gate
import reporting_contracts as legacy
import reporting_structured as sr
from reporting_structured_selftest import fixture_canon, fixture_page, review_for, Links
from reporting_syntax import normalize_phone, PHONE_SEPARATORS


def run_cases():
    rows = []
    c = fixture_canon()
    cat = canon.reporting_catalog(c)
    site = json.loads((build.ROOT / 'content/site.json').read_text())

    def check(name, group, fn):
        try:
            ok = bool(fn())
            detail = '' if ok else 'assertion false'
        except Exception as exc:
            ok, detail = False, f'{type(exc).__name__}: {exc}'
        rows.append(dict(name=name, group=group, ok=ok, detail=detail))

    def rejects(fn):
        try:
            fn()
        except (sr.ReportingError, canon.CanonError):
            return True
        return False

    def page_with(text, surface='section'):
        p = fixture_page()
        if surface == 'section': p['sections'][0][1] = text
        elif surface == 'bullet': p['sections'][0][1] = '- ' + text
        elif surface == 'heading': p['sections'][0][0] = text
        elif surface == 'quick_answer': p['quick_answer'] += ' ' + text
        elif surface.startswith('faq-'): p['faq'][0][int(surface == 'faq-answer')] = text
        elif surface.startswith('evidence-'): p['evidence'] = [{surface.split('-')[1]: text}]
        elif surface.startswith('example-'): p['message_examples'] = [{surface.split('-')[1]: text}]
        elif surface.startswith('hub-'):
            p = {k: v for k, v in p.items() if k in ('title', 'description', 'sections', 'faq', 'reporting_routes')}
            p['intro'] = 'Check independently.'
            if surface == 'hub-intro': p['intro'] = text
            elif surface == 'hub-section': p['sections'][0][1] = text
            else: p['faq'][0][1] = text
            p['sources_checked'] = [['Evidence', 'https://routes.example/evidence']]
        else: p[surface] = text
        return p

    def render(p, review, surface):
        if surface.startswith('hub-'):
            return build.render_category_page(site, 'email', [], hub=p,
                                             reporting_sources=c, reporting_review=packet_for(p, c, review))
        return build.render_post(site, p, [p], sources=c, reporting_review=packet_for(p, c, review))

    def boundary_blocks(text, surface='section'):
        p = page_with(text, surface)
        review = review_for(p, c, approved_fields=dict(sr.approval_fields(p)))
        result = gate.run_gate(p, use_llm=False, is_hub=surface.startswith('hub-'),
                               reporting_canon=c, reporting_review=packet_for(p, c, review))
        return (bool(sr.raw_destinations(text)) and not result.passed
                and any(i['check'] == 'structured_reporting' and i['severity'] == 'block'
                        for i in result.issues)
                and rejects(lambda: render(p, review, surface)))

    attack = 'Report through [this secure portal](//0xcb00710a/report/).'
    focused = [attack, 'Report through [this secure portal](///0xcb00710a/report/).',
               'Report through [this portal](//attacker/).',
               'Call 07.12.34.56.78.9 to report it.',
               'Call ٠٧١٢٣٤٥٦٧٨٩ to report it.', 'Forward the text to ۷۷۲۶.',
               'Forward to &#xff17;&#xff17;&#xff12;&#xff16;.']
    for text in focused:
        check(text, 'wp3d8', lambda text=text: boundary_blocks(text))
    for surface in ('quick_answer', 'faq-question', 'faq-answer', 'hub-intro', 'hub-section'):
        check('exact attack in ' + surface, 'wp3d8', lambda surface=surface: boundary_blocks(attack, surface))
    for value in ('07123 456789', '07123-456789', '07123 456788'):
        check('ASCII equivalent/mutation ' + value, 'wp3d8', lambda value=value: boundary_blocks('Call ' + value))
    check('valid internal Markdown emits only its site path', 'wp3d8', lambda:
          Links(build._inline('[Read](/guides/example/)')).links == ['/guides/example/'])
    check('decimal/version/IP are numeric holds, not phone destinations', 'wp3d8', lambda:
          all(rejects(lambda v=v: sr._destination('phone',v,'control'))
              and sr.raw_destinations(v)
              and all(t.startswith('numeric review required: ') for t in sr.raw_destinations(v))
              for v in ('0.123456789','1.2.300','192.0.2.10')))
    check('typed canonical phone renders the exact tel target', 'wp3d8', lambda:
          Links(sr.render_block(cat,['fixture-service:phone'])).links == ['tel:01234567890'])
    citation_page = fixture_page()
    citation_page['sources_checked'] = [['Official evidence','https://routes.example/evidence']]
    citation_review = review_for(citation_page,c,approved_fields={'sources_checked/0/0':'Official evidence'})
    check('reviewed citation stays separate from action selection', 'wp3d8', lambda:
          [a.route_id for a in sr.validate_page(citation_page,cat,citation_review)]
          == ['fixture-service:web']
          and 'https://routes.example/evidence' in Links(render(citation_page,citation_review,'section')).links)

    # Safe syntax: actual anchors, gate acceptance and full render acceptance.
    paths = ['/guides/example/', '/categories/fraud/', '/recovery/', '/A_B/x-y', '/abc']
    paths += [f'/guides/example-{n}/part_{n}/' for n in range(40)]
    hrefs = []
    for path in paths:
        def positive(path=path):
            text = f'Before [Read the guide]({path}) afterwards.'
            p = page_with(text); review = review_for(p, c, approved_fields={'sections/0/1':text})
            emitted = Links(build._inline(text)).links
            hrefs.extend(emitted)
            return (emitted == [path] and build._schema_plain(text) == 'Before Read the guide afterwards.'
                    and not gate.check_unrenderable_markup(p)
                    and not sr.raw_destinations(text)
                    and ((gate.run_gate(p, use_llm=False, reporting_canon=c, reporting_review=packet_for(p, c, review)).passed
                          and path in Links(render(p, review, 'section')).links) if __import__('reporting_publication').internal_target(path)
                         else rejects(lambda: render(p, review, 'section'))))
        check(path, 'markdown', positive)

    bad_targets = ['//evil.example/x', '//0xcb00710a/report/', '//attacker/', '///attacker/',
        '////attacker/', '//user@attacker/', 'https://evil.example/', 'HTTP://evil.example/',
        'HTTPS://evil.example/', 'mailto:evidence@evil.example', 'tel:07123456789',
        'sms:7726', 'data:text/html,hello', 'javascript:alert(1)', 'ftp://evil.example/',
        'file:///etc/passwd', 'custom:target', '/\\attacker/', '\\attacker\\',
        '/guides/a:b/', '/guides/a\\b/', '/guides//example/', '/guides/./example/',
        '/guides/../example/', '/guides/%2e%2e/example/', '/%2fattacker/', '/%2Fattacker/',
        '%2f%2fattacker/', '&#47;&#47;attacker/', '/&#47;attacker/',
        '／／attacker/', '/ａｔｔａｃｋｅｒ/', '/guides/K/', '/guides/İ/',
        ' /guides/example/', '/guides/example/ ', '\t/guides/example/',
        '/\tattacker/', '/\nattacker/', '/\rattacker/', '/guides/example/?next=x',
        '/guides/example/#x', '/', '', '../relative/', 'relative/path',
        '/guides/\x00x/', '/guides/\u200bx/', '/guides/\u202ex/']
    for target in bad_targets:
        for label in ('Official reporting portal', 'Report Fraud', 'https://official.example'):
            text = f'Before [{label}]({target}) afterwards.'
            def negative(text=text):
                emitted = Links(build._inline(text)).links
                hrefs.extend(emitted)
                return (not emitted and build._schema_plain(text) == text
                        and bool(gate.check_unrenderable_markup(page_with(text)))
                        and boundary_blocks(text))
            check(repr((label, target)), 'markdown', negative)
    for text, expected in [
        ('[Safe](/guides/example/)[Official](//attacker/)', ['/guides/example/']),
        ('[Official](//attacker/)[Safe](/categories/fraud/)', ['/categories/fraud/']),
        ('[outer [Official](//attacker/)](/guides/example/)', []),
        ('[outer [Safe](/guides/example/)](//attacker/)', ['/guides/example/']),
        ('`[Official](//attacker/)`', []),
        ('([Official](//attacker/)) and **urgent**', []),
    ]:
        def nested(text=text, expected=expected):
            emitted = Links(build._inline(text)).links
            hrefs.extend(emitted)
            return emitted == expected and boundary_blocks(text)
        check(text, 'markdown', nested)

    def browser_origin():
        p = subprocess.run(['node', '-e',
            'const fs=require("node:fs"); const h=JSON.parse(fs.readFileSync(0,"utf8"));'
            'process.exit(h.every(x=>{const u=new URL(x,"https://beatthescam.com/guides/test/");'
            'return u.origin==="https://beatthescam.com" && !u.username && !u.password;})?0:1);'],
            input=json.dumps(hrefs), text=True, capture_output=True, check=False)
        return bool(hrefs) and p.returncode == 0
    check('all actual emitted hrefs resolve to site origin (WHATWG URL)', 'markdown', browser_origin)

    for surface in ('title', 'description', 'hero', 'heading', 'section', 'bullet', 'quick_answer',
                    'faq-question', 'faq-answer', 'evidence-signal', 'evidence-finding', 'evidence-basis',
                    'example-label', 'example-message', 'example-assessment', 'hub-intro', 'hub-section', 'hub-faq'):
        for text in (attack, 'Call 07.12.34.56.78.9 to report it.', 'Forward the text to ۷۷۲۶.'):
            check(surface + ': ' + text, 'surface', lambda text=text, surface=surface: boundary_blocks(text, surface))

    # Every decimal digit family in this Python Unicode database; script mixing
    # and supported separators change representation only, never permission.
    zeros = [chr(n) for n in range(0x110000)
             if unicodedata.category(chr(n)) == 'Nd' and unicodedata.decimal(chr(n)) == 0]
    for zero in zeros:
        for separator in ('', '.', ' ', '-', '\u00a0', '\u202f', '\u2009', '\u2011', '\u2013', '\u2212'):
            for plain, kind in (('07123456789', 'phone'), ('7726', 'shortcode')):
                digits = ''.join(chr(ord(zero) + int(d)) for d in plain)
                value = separator.join(digits[n:n+2] for n in range(0, len(digits), 2))
                def property_case(value=value, plain=plain, kind=kind):
                    normalized = normalize_phone(value, kind=kind)
                    return (normalized == plain and normalize_phone(normalized, kind=kind) == normalized
                            and boundary_blocks('Contact ' + value + ' for help.'))
                check(f'U+{ord(zero):04X}/{separator!r}/{kind}', 'phone', property_case)
    for value, expected in [('0٧1٢3٤5٦7٨9', '07123456789'), ('(07123) 456789', '07123456789'),
                            ('+٤٤ (٧١٢٣) ٤٥٦٧٨٩', '+447123456789'),
                            ('+44 (0) 7123 456789', '+4407123456789'),
                            ('0044 7123 456789', '00447123456789')]:
        check('exact normalization ' + value, 'phone', lambda value=value, expected=expected:
              normalize_phone(value, kind='phone') == expected and boundary_blocks('Call ' + value))
    for separator in PHONE_SEPARATORS:
        check('explicit separator ' + repr(separator), 'phone', lambda separator=separator:
              normalize_phone(separator.join('07123456789'), kind='phone') == '07123456789')
    for value in ('07O23456789', '⓪⑦①②③④⑤⑥⑦⑧⑨', '⁰⁷¹²³⁴⁵⁶⁷⁸⁹', 'ⅦⅦⅡⅥ', '＋447123456789',
                  '07123/456789', '07123,456789', '07123•456789', '07123\t456789',
                  '07123\n456789', '07123\u200b456789', '07123\u202e456789', '07+123456789',
                  '++447123456789', 'tel:07123456789', '07123456789x12', '', None):
        check('unsupported representation ' + repr(value), 'phone', lambda value=value:
              normalize_phone(value, kind='phone') is None)
    for value, kind, expected in [('7726','phone',None), ('07123456789','shortcode',None),
        ('+7726','shortcode',None), ('12','shortcode',None), ('123','shortcode','123'),
        ('123456','shortcode','123456'), ('1234567','phone','1234567'),
        ('123456789012345','phone','123456789012345'), ('1234567890123456','phone',None)]:
        check('kind/length ' + repr((value,kind)), 'phone', lambda value=value,kind=kind,expected=expected:
              normalize_phone(value, kind=kind) == expected)
    for value in ('&#x660;&#x667;&#x661;&#x662;&#x663;&#x664;&#x665;&#x666;&#x667;&#x668;&#x669;',
                  '%D9%A7%D9%A7%D9%A2%D9%A6', '&#xff17;&#xff17;&#xff12;&#xff16;',
                  '07%2e12%2e34%2e56%2e78%2e9', '&#x202e;7726', '77&#x200b;26',
                  '⁷⁷²⁶', '⑦⑦②⑥'):
        check('encoded/unsupported numeric hold ' + value, 'phone', lambda value=value: boundary_blocks('Contact ' + value))

    # No classifier manufactures phone identities for these ordinary numbers.
    # Canon rejects their serialization; raw prose gets the separately labelled
    # conservative numeric hold (not a claim that the value is a phone).
    for value in ('0.123456789', '£0.123456789', '12.50', '£1,234.56', '$123.00',
                  '2026-10-09', '01.02.2026', '2026/10/09', '1.2.300', '192.0.2.10', '2026'):
        check('ordinary numeric prose ' + value, 'numeric_hold', lambda value=value:
              rejects(lambda: sr._destination('phone', value, 'control'))
              and bool(sr.raw_destinations(value))
              and all(t.startswith('numeric review required: ') for t in sr.raw_destinations(value)))
    for text in ('There are two steps.', 'Take 2 steps.', 'Contact your bank through its official app.'):
        check('ordinary prose ' + text, 'numeric_hold', lambda text=text: not sr.raw_destinations(text))

    # Canon remains exact ASCII data. Unicode/display normalization must not
    # relax serialized contracts, owner bindings or reviewed selections.
    for value in ('07.12.34.56.78.9', '٠٧١٢٣٤٥٦٧٨٩', '07123\u00a0456789', '(07123) 456789'):
        check('canon serialization not widened ' + value, 'authority', lambda value=value:
              rejects(lambda: sr._destination('phone', value, 'canon')))
    changed = copy.deepcopy(c); changed['verified_org_contacts'][-1]['phone'] = '+44 7123 456789'
    changed['verified_org_contacts'][-1]['actions']['phone']['instruction']['channels'][0]['numbering_context'] = 'international'
    check('canonical plus preserved in actual tel href', 'authority', lambda:
          Links(sr.render_block(canon.reporting_catalog(changed), ['fixture-service:phone'])).links == ['tel:+447123456789'])
    for field, value in [('phone','01234 567891'), ('sms','8998'), ('brand','Another Owner')]:
        changed_c = copy.deepcopy(c); changed_c['verified_org_contacts'][-1][field] = value
        check('review rejects changed ' + field, 'authority', lambda changed_c=changed_c:
              rejects(lambda: canon.reporting_catalog(changed_c, expected_digest=sr.digest(c))))
    for field, value in [('purpose','refund-request'), ('jurisdictions',['Global'])]:
        changed_c = copy.deepcopy(c); changed_c['verified_org_contacts'][-1]['actions']['phone'][field] = value
        check('review rejects changed ' + field, 'authority', lambda changed_c=changed_c:
              rejects(lambda: canon.reporting_catalog(changed_c, expected_digest=sr.digest(c))))
    for selected in ('fixture-service:email', 'fixture-service:phone', 'fixture-service:text'):
        p = fixture_page(); p['reporting_routes'] = [selected]
        check('existing route not approved for this scope ' + selected, 'authority', lambda p=p:
              rejects(lambda: sr.validate_page(p, cat, review_for(p,c,allowed=['fixture-service:web']))))
    p = fixture_page(); p['sources_checked'] = [['Official evidence', 'https://routes.example/evidence']]
    review = review_for(p,c,approved_fields={'sources_checked/0/0':'Official evidence'})
    check('exact separately reviewed citation remains valid', 'authority', lambda:
          bool(sr.validate_page(p,cat,review)) and p['sources_checked'][0][1] in Links(render(p,review,'section')).links)
    substituted = copy.deepcopy(p); substituted['sources_checked'][0][1] = 'https://evil.example/evidence'
    check('citation substitution is rejected even with rebound page hash', 'authority', lambda:
          rejects(lambda: sr.validate_page(substituted,cat,replace(review,page_sha256=sr.digest(substituted)))))
    check('citation does not license raw extra in prose', 'authority', lambda:
          boundary_blocks('Report at https://routes.example/evidence.'))

    # Explicit snapshots of deliberately different legacy semantics.
    for value, expected in [('0300 123 2040','03001232040'), ('+44 300 123 2040','03001232040'),
        ('0044 300 123 2040',None), ('+44 (0) 300 123 2040',None), ('03.00.12.32.04.0',None),
        ('0٣٠٠ ١٢٣ ٢٠٤٠',None), ('7726','7726')]:
        check('legacy normalization preserved ' + value, 'legacy', lambda value=value,expected=expected:
              (legacy.normalize('phone',value).canonical_value if legacy.normalize('phone',value) else None) == expected)
    check('mixed Unicode legacy phone remains blocked', 'legacy', lambda:
          bool(gate.check_phones({'sections': [['Reporting','Call 0٣٠٠ ١٢٣ ٢٠٤٠.']]})))
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    rows = run_cases()
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n')
    for group in sorted(Counter(r['group'] for r in rows)):
        part = [r for r in rows if r['group'] == group]
        print(f"{group}: {sum(r['ok'] for r in part)}/{len(part)} PASS")
    for row in rows:
        if not row['ok']: print('FAIL ' + json.dumps(row, ensure_ascii=False))
    print(f"Structured security: {sum(r['ok'] for r in rows)} PASS / {sum(not r['ok'] for r in rows)} FAIL")
    raise SystemExit(0 if all(r['ok'] for r in rows) else 1)
