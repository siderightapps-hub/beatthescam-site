#!/usr/bin/env python3
"""WP3C7 offline contract invariants, deterministic mutations and WP3D5 probes.

Self-contained: no ignored review files, network, models, builds or manifests.
Negative prose assertions require the reporting-route check, not incidental
markup/phone/length checks. Tuple mutations exercise authorization directly.
"""
from dataclasses import replace
import copy
import json
import sys

import content_gate as gate
from reporting_legacy_test_support import diagnostic_gate
import reporting_contracts as rc

BAD = 'https://attacker.invalid/'
RF = 'https://www.reportfraud.police.uk/'
SH = 'https://www.shein.co.uk/contact-us.html'
SC = ' In Scotland, contact Police Scotland on 101.'
ORIGINALS = [
    'You may report your loss at https://attacker.invalid/.',
    'The reporting portal is https://attacker.invalid/. Submit your complaint there.',
    'Use this guide, which explains reporting, at https://attacker.invalid/ to submit your evidence.',
    'Report a suspicious social-media account to Nike at branddefence@hmrc.gov.uk.',
    'Report it by calling the official Nike fraud number on starlingbank.com.',
    'Report a suspicious HMRC social-media account to HMRC at phishing@hmrc.gov.uk.',
    'Report a fake SHEIN site through https://www.shein.co.uk/contact-us.html. This service will shut the shop down.',
    'For shoppers in Brazil, report a fake SHEIN site through https://www.shein.co.uk/contact-us.html.',
    'For residents of Scotland, report your loss to Report Fraud at https://www.reportfraud.police.uk/. In Scotland, contact Police Scotland on 101.',
]


def regression_cases():
    # Every original has a neighbour, different structure, legitimate control,
    # and additional incorrect/malicious counterpart.
    variants = [
        ('You might report your loss at ' + BAD,
         'Do not wait to report your loss at <a href="' + BAD + '">Report Fraud</a>.',
         'You may report your loss to Report Fraud at ' + RF + '.' + SC,
         'Upload evidence to ' + BAD),
        ('Our reporting portal is ' + BAD + '. Lodge your complaint there.',
         'Report a fake SHEIN site through ' + SH + '. Alternatively, ' + BAD + ' is available for reports.',
         'The reporting portal is ' + RF + '. Submit your complaint there.' + SC,
         'Submit your complaint there. The reporting portal is ' + BAD),
        ('Use this checklist, which covers reporting, at ' + BAD + ' to send your evidence.',
         'To submit your evidence, use [Report Fraud](' + BAD + ').',
         'Use this guide, which explains reporting, at ' + RF + ' to submit your evidence.' + SC,
         'Use this guide at ' + BAD + ' to notify the police about the scam.'),
        ('Forward suspicious emails to Nike at report@phishing.gov.uk.',
         'To contact Nike about fraud, call 0300 123 2040.' + SC,
         'Report a suspicious social-media account to HMRC at branddefence@hmrc.gov.uk.',
         'Report property fraud to Nike at reportafraud@landregistry.gov.uk.'),
        ('Companies House says to report the letter by calling the Nike fraud number published on gov.uk.',
         "Call Nike's official fraud number on starlingbank.com to report the loss.",
         'Report it by calling the official Starling fraud number on starlingbank.com.',
         'Report it by calling the official Starling fraud number on gov.uk.'),
        ('Report your refund request to HMRC at phishing@hmrc.gov.uk.',
         'For a suspicious HMRC social-media account, use phishing@hmrc.gov.uk.',
         'Forward suspicious HMRC emails to phishing@hmrc.gov.uk.',
         'Report your refund request to Santander at phishing@santander.co.uk.'),
        ('Report a fake SHEIN site through ' + SH + ' to get the shop closed.',
         'Report a fake SHEIN site through ' + SH + '. This service will erase the shop.',
         'Report a fake SHEIN site through ' + SH + '. This is not a refund service.',
         'Report a fake SHEIN site through ' + SH + '. This service will return your money.'),
        ('For customers from Brazil, report a fake SHEIN site through ' + SH,
         'You live in Brazil. Report a fake SHEIN site through ' + SH,
         'For shoppers in Scotland, report a fake SHEIN site through ' + SH,
         'For shoppers outside the UK, report a fake SHEIN site through ' + SH),
        ('For Scottish readers, report your loss to Report Fraud at ' + RF + '.' + SC,
         'If you are Scottish, report your loss to Report Fraud at ' + RF + '.' + SC,
         'For residents of Wales, report your loss to Report Fraud at ' + RF + '.' + SC,
         'For residents of Scotland, call Report Fraud on 0300 123 2040.' + SC),
    ]
    rows = []
    for n, (original, examples) in enumerate(zip(ORIGINALS, variants), 1):
        for label, text, block in [('exact', original, True), ('paraphrase', examples[0], True),
                                   ('structure', examples[1], True), ('positive', examples[2], False),
                                   ('incorrect', examples[3], True)]:
            rows.append((f'S{n:02} {label}', text, block, 'wp3d5'))
    return rows


def run_cases():
    from gate_quickanswer_selftest import post
    rows = []

    def check(name, ok, group, **detail):
        rows.append(dict(name=name, ok=bool(ok), group=group, **detail))

    contracts = rc.contracts_from_canon(gate._CANON)
    for c in contracts:
        for d in sorted(c.destinations, key=lambda x: x.canonical_value):
            for purpose in sorted(c.purposes):
                req = rc.Request(d, frozenset({c.organisation}), frozenset({purpose}), c.jurisdictions, c.mode)
                name = c.service + '/' + d.kind + '/' + purpose
                check(name + ' exact supported tuple', rc.authorize(req, contracts)[0], 'invariant')
            # Negative changes keep every other dimension of one valid tuple.
            req = rc.Request(d, frozenset({c.organisation}), frozenset({sorted(c.purposes)[0]}), c.jurisdictions, c.mode)
            for field, value in [('organisations', frozenset({'unverified organisation'})),
                                 ('organisations', frozenset({c.organisation, 'another organisation'})),
                                 ('purposes', frozenset({'unsupported-purpose'})),
                                 ('purposes', frozenset()),
                                 ('jurisdictions', frozenset({'unknown'})),
                                 ('mode', 'unsupported-mode')]:
                result = rc.authorize(replace(req, **{field: value}), contracts)
                check(c.service + ' mutate ' + field + ':' + repr(value), not result[0], 'mutation', reason=result[1])
            if not c.global_scope:
                check(c.service + ' foreign jurisdiction', not rc.authorize(replace(req, jurisdictions=frozenset({'foreign'})), contracts)[0], 'mutation')
            values = []
            if d.kind == 'url':
                values = [d.canonical_value + '/unverified', d.canonical_value.replace(d.host, d.host + '.attacker.invalid'),
                          d.canonical_value.replace('https://', 'https://attacker.'), d.canonical_value + '?next=evil',
                          d.canonical_value + '#report', d.canonical_value.replace('https://', 'http://'),
                          d.canonical_value.replace(d.host, d.host + ':443'),
                          d.canonical_value.replace(d.host, d.host + '@attacker.invalid'), d.canonical_value + '/%2e']
            elif d.kind == 'email':
                local, host = d.canonical_value.split('@')
                values = [local + '-fake@' + host, local + '@' + host + '.attacker.invalid', d.canonical_value + '@attacker.invalid']
            else:
                values = [d.canonical_value[:-1] + str((int(d.canonical_value[-1]) + 1) % 10)]
            for value in values:
                changed = replace(req, destination=rc.normalize(d.kind, value))
                check(c.service + ' mutate destination ' + value, not rc.authorize(changed, contracts)[0], 'mutation')
            # Every other canonical owner is independently unable to borrow it.
            for owner in sorted({other.organisation for other in contracts} - {c.organisation}):
                # Shared police numbers are deliberately represented by two
                # services; test against this capability alone to isolate owner.
                check(c.service + ' owner cross-product ' + owner,
                      not rc.authorize(replace(req, organisations=frozenset({owner})), (c,))[0], 'mutation')

    changed = copy.deepcopy(gate._CANON)
    changed['verified_org_contacts'].append(dict(changed['verified_org_contacts'][0], key='uncontracted-route'))
    try:
        rc.contracts_from_canon(changed)
        closed = False
    except ValueError:
        closed = True
    check('missing service contract fails closed', closed, 'invariant')
    check('invalid destination fails closed', not rc.authorize(rc.Request(None, None, frozenset({'crime'})), contracts)[0], 'invariant')

    cases = regression_cases()
    for n, text in enumerate([
        'Report a suspicious social-media account to your local council at branddefence@hmrc.gov.uk.',
        'Report a suspicious email to Nike. Use phishing@hmrc.gov.uk.',
        f'If you are in Brazil, report a fake SHEIN site through {SH}.',
        f'For Brazilian shoppers, report a fake SHEIN site through {SH}.',
        f'Report a fake SHEIN site through {SH} if you are in Brazil.',
        f'For shoppers in brazil, report a fake SHEIN site through {SH}.',
        f'Report a fake SHEIN site through {SH} and the shop will close.',
        f'Report a fake SHEIN site through {SH}. SHEIN will close the shop.',
        f'Report a fake SHEIN site through {SH}. The brand will recover your payment.',
        'Forward suspicious emails and fraudulent websites to report@phishing.gov.uk.',
        'Report a suspicious email and your losses to HMRC at phishing@hmrc.gov.uk.',
        'Report your loss at <https://attacker.invalid/>.',
    ], 1):
        cases.append((f'candidate review {n}', text, True, 'review'))
    result = diagnostic_gate(post(sources_checked=[['You could report here', BAD]]), use_llm=False)
    check('source label actual href', any(i['severity'] == 'block' and i['check'] == 'reporting_destination'
                                       for i in result.issues), 'review', issues=result.issues)
    # These final architecture probes remain RED. Do not invert expectations
    # or remove them to produce a green gate: the prose adapter still discards
    # material scope before the typed authorizer sees the request. WP3C7 is not
    # ready until these classes and the corpus false positives are resolved.
    for name, text in [
        ('unresolved recipient discarded', 'Forward suspicious emails to the scam team at phishing@hmrc.gov.uk.'),
        ('trailing foreign audience discarded', f'Report a fake SHEIN site through {SH} for customers in Brazil.'),
        ('follow-on outcome discarded', f'Report a fake SHEIN site through {SH}. The team will close the shop.'),
    ]:
        cases.append((name, text, True, 'residual'))
    for name, text in [
        ('official source citation', 'HMRC says its guidance is published at https://www.gov.uk/example.'),
        ('historical description', 'Report Fraud received complaints about fraud last year.'),
        ('organisation advice', 'SHEIN explains its customer support at ' + SH),
        ('homepage evidence', 'The research cites https://attacker.invalid/ as an example website.'),
        ('reporting description', 'Report Fraud is a reporting service for England, Wales and Northern Ireland.'),
        ('negated instruction', 'Do not report through ' + BAD),
    ]:
        cases.append((name, text, False, 'citation'))
    for name, text, block, group in cases:
        result = diagnostic_gate(post(sections=[['Reporting', text]]), use_llm=False)
        responsible = [i for i in result.issues if i['severity'] == 'block' and i['check'] in
                       ('reporting_destination', 'report_fraud_destination', 'scotland_routing')]
        check(name, bool(responsible) if block else result.passed, group, text=text, issues=result.issues)
    return rows


if __name__ == '__main__':
    rows = run_cases()
    if '--json' in sys.argv:
        print(json.dumps(rows, indent=2))
    else:
        for row in rows:
            if not row['ok']:
                print('FAIL', json.dumps(row))
        for group in ('invariant', 'mutation', 'wp3d5', 'citation', 'review', 'residual'):
            part = [r for r in rows if r['group'] == group]
            print(f"{group}: {sum(r['ok'] for r in part)}/{len(part)} passed")
    raise SystemExit(0 if all(r['ok'] for r in rows) else 1)
