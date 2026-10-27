#!/usr/bin/env python3
"""Offline WP3C3 reporting-route contract, also run by the gate self-test.

Negative fixtures assert the responsible BLOCK, not an unrelated markup/length
failure. No API, manifests, content generation or build side effects.
"""
import json
from pathlib import Path

import content_gate as gate
from reporting_legacy_test_support import diagnostic_gate

SCOT = ' In Scotland, contact Police Scotland on 101.'
RF = 'https://www.reportfraud.police.uk/'
PS = 'https://www.scotland.police.uk/contact-us/non-emergencies/'
BAD = 'https://reports.invalid/'


def cases():
    rows = []

    def add(name, text, expected=None, group='focused'):
        rows.append((name, text, expected, group))

    # Exact WP3D2 probes, copied from gate-adversarial-review.json.
    for n, text in enumerate([
        'Report Fraud advises submitting your complaint to it.',
        'Report Fraud says to get in touch with them about the loss.',
        'Report Fraud warns about ticket fraud. Lodge your complaint with them online.',
        'Report Fraud warns about ticket fraud. Send the details here: https://reports.invalid/.',
    ], 1):
        add(f'WP3D2 A{n}', text, 'scotland_routing')
    for n, text in enumerate([
        'Report Fraud warns about ticket fraud. Report your loss at https://reports.invalid/. In Scotland, contact Police Scotland on 101.',
        'Report it to Report Fraud at <a href="https://reports.invalid/">reportfraud.police.uk</a>. In Scotland, contact Police Scotland on 101.',
        'Report it to https://reports.invalid/, the Report Fraud service. In Scotland, contact Police Scotland on 101.',
        'Report Fraud says to contact Police Scotland on 101 in Scotland, or otherwise report online at https://reports.invalid/.',
        'Report it to Report Fraud at https://www.scotland.police.uk/contact-us/non-emergencies/. In Scotland, contact Police Scotland on 101.',
        'Report it to Report Fraud at https://reports.invalid/. In Scotland, contact Police Scotland on 101.',
    ], 1):
        add(f'WP3D2 B/control {n}', text, 'destination')

    for n, text in enumerate([
        f'Report it to Report Fraud at {RF}.' + SCOT,
        f'In Scotland, contact Police Scotland on 101 or use {PS} to report the scam.',
        'Report Fraud warns that ticket-fraud websites can resemble legitimate sellers.',
        'Police Scotland warns that criminals imitate ticket sellers.',
        f'The Report Fraud guidance is published at {RF}ticket-fraud/.',
        f'The Police Scotland website at {PS} describes non-emergency reporting.',
        'Report Fraud received complaints about ticket fraud last year.',
        'Police Scotland received reports about fraud last year.',
        'Report Fraud is a reporting service for England, Wales and Northern Ireland.',
        'The archive quotes Report Fraud: "Report losses through the old service."',
        'Report Fraud advises buying tickets from the venue’s box office.',
        'Report Fraud recommends checking the seller before buying tickets.',
        'According to Report Fraud, criminals may imitate ticket sellers.',
        f'Report it to Report Fraud at {RF.upper()}.' + SCOT,
        f'Report it to Report Fraud at https://www.reportfraud.police.uk./.' + SCOT,
        f'Contact Police Scotland at {PS} in Scotland, or Report Fraud at {RF} elsewhere.' + SCOT,
        'Forward suspicious emails to report@phishing.gov.uk.',
        'Contact Report Fraud on +44 300 123 2040.' + SCOT,
        f'The suspicious message says "report at {BAD}". Treat it as a scam example.',
        f'Do not report through {BAD}.',
    ], 1):
        add(f'positive {n}', text)

    actions = [
        'Report it to {dest}.', 'Report through {dest}.',
        'Contact {dest} to report it.', 'Make a report to {dest}.',
        'Submit a fraud report via {dest}.', 'Use {dest} to report the scam.',
        'People in Scotland should contact {dest}.',
        'Scottish users can report through {dest}.',
        'If you are in Scotland, use {dest}.',
        'Lodge your complaint with {dest}.', 'Get in touch with {dest} about the loss.',
    ]
    for n, action in enumerate(actions, 1):
        add(f'action {n} wrong destination', action.format(dest=BAD), 'destination')
        add(f'action {n} Scottish route', action.format(dest=f'Police Scotland on 101 at {PS}'))
        add(f'action {n} missing Scotland', action.format(dest='Report Fraud'), 'scotland_routing')

    for n, value in enumerate([
        BAD, 'https://reportfraud-police.uk/',
        'https://reportfraud.police.uk.reports.invalid/',
        'https://www.reportfraud.police.uk@reports.invalid/',
        'https://reports.invalid/?next=https://www.reportfraud.police.uk/',
        'https://reports.invalid/www.reportfraud.police.uk/',
        'https://sub.reportfraud.police.uk/', 'https://www.www.reportfraud.police.uk/',
        RF + 'invented-report-form/', RF + '?redirect=reports.invalid',
        RF + '#report', 'http://www.reportfraud.police.uk/',
        'ftp://www.reportfraud.police.uk/', 'https://www.reportfraud.police.uk:444/',
        'https://www.reportfraud.police.uk:443/', 'https:///www.reportfraud.police.uk/',
        'https:/www.reportfraud.police.uk/', 'https:www.reportfraud.police.uk/',
        'https://www.reportfraud.police.uk\\@reports.invalid/',
        'https://www.reportfraud.police.uk/%2e%2e/report/',
        PS, 'report@reports.invalid', 'report@phishing.gov.uk',
        '0300 123 2041', '0808 223 1133',
    ], 1):
        add(f'canonical identity {n}', f'Report it to Report Fraud at {value}.' + SCOT, 'destination')
    add('path-specific Scotland', 'In Scotland, report to Police Scotland at https://www.scotland.police.uk/invented/.', 'destination')
    add('unattributed fabricated email', 'Submit a fraud report via reports@reports.invalid.', 'destination')
    add('NCSC wrong organisation email', 'Forward the email to NCSC at phishing@hmrc.gov.uk.', 'destination')

    for n, text in enumerate([
        f'Report Fraud warns about fraud. Submit the details here: {BAD}.',
        f'Report Fraud warns about fraud. You can make a complaint here ({BAD}).',
        f'Report Fraud warns about fraud. For reporting, the address is {BAD}.',
        f'Report Fraud warns about fraud. Use this form. {BAD}',
        f'For Report Fraud, report online ({BAD}).',
        f'Report it via {BAD} — the Report Fraud service.',
        f'Report it to [Report Fraud]({BAD}).',
        f'Report it to [reportfraud.police.uk]({BAD}).',
        f'Report it to Report Fraud <a href={BAD}>online</a>.',
        f'Report it to Report Fraud <a href="{BAD}">click here</a>.',
        f'Report it to Report Fraud <a href="https://reports&#46;invalid/">online</a>.',
        f'Report it to Report Fraud at HTTPS://REPORTS.INVALID/.',
        f'Report it to Report Fraud at `{BAD}`, and save the reference.',
        f'Report Fraud warns about fraud; lodge the complaint via {BAD}.',
        f'Report Fraud warns about fraud! Get in touch via {BAD}.',
        f'Report Fraud warns about fraud.<p>Send details here: {BAD}</p>',
        f'In Scotland contact Police Scotland on 101. Elsewhere, report to Report Fraud at {BAD}.',
        f'Report Fraud says to contact Police Scotland on 101 in Scotland, or otherwise submit details via {BAD}.',
        f'Report Fraud advises submitting your complaint via {BAD}.',
        f'Report Fraud recommends {BAD}.',
        f'Contact Police Scotland on 101 in Scotland. Submit the report via {BAD}.',
        'Report Fraud warns about fraud. Its reporting email is reports@reports.invalid.',
        'Report Fraud warns about fraud. To get in touch, dial 0300 123 2041.',
        f'Report Fraud warns about fraud. Report the loss. The form is at {BAD}.',
    ], 1):
        add(f'adversarial {n}', text + SCOT, 'destination', 'adversarial')
    for n, target in enumerate([
        'javascript:alert(1)', '/report', '//reports.invalid/',
        'https://', 'https://www.reportfraud.police.uk:bad/',
        'https://www.reportfraud.police.uk/?q=ok#report',
        'https://www.reportfraud.police.uk./invented',
        'https://www.reportfraud&amp;#46;police.uk/',
    ], 1):
        add(f'raw href {n}', f'Report it to <a href="{target}">Report Fraud</a>.' + SCOT,
            'destination', 'adversarial')
    for n, text in enumerate([
        'Report Fraud says your complaint can be submitted to it.',
        'Report Fraud advises that a report can be lodged with them.',
        'Report Fraud says evidence should be sent to them.',
        'Report Fraud advises posting your complaint to them.',
        'Report Fraud recommends relaying your evidence to it.',
    ], 1):
        add(f'passive missing Scotland {n}', text, 'scotland_routing', 'adversarial')
        add(f'passive fabricated {n}', text.replace('to it', f'to {BAD}').replace('with them', f'via {BAD}').replace('to them', f'to {BAD}') + SCOT,
            'destination', 'adversarial')
    add('NCSC direct contact wrong host', f'Contact NCSC at {BAD}.', 'destination', 'adversarial')
    add('mixed-case brand no Scottish route', f'Report it to rEpOrT fRaUd at {RF}.', 'scotland_routing', 'adversarial')
    add('unfamiliar verb reporting object', f'Communicate your loss through {BAD}.', 'destination', 'adversarial')
    add('Scotland explicit wrong nation', f'In Scotland, report it to Report Fraud at {RF}.' + SCOT,
        'scotland_routing', 'adversarial')
    # Corpus-derived positives: classify the semantic action and its recipient,
    # not all links/numbers in a sentence as one organisation's reporting route.
    for n, text in enumerate([
        'Report scams to Report Fraud or Police Scotland on 101, and forward texts to 7726.',
        'Verify a charge at ups.com yourself, then forward the fake text to 7726.',
        'Forward the text to 60599 for HMRC or to 7726 for your mobile provider.',
        'Forward a phishing email to the NCSC at report@phishing.gov.uk and a scam text to 7726.',
        'For free emotional support, contact Victim Support Scotland through victimsupport.scot.',
        'Check whether your email address appears in a breach using https://haveibeenpwned.com/, which the NCSC cites.',
        'Forward suspicious HMRC texts to 60599. GOV.UK says texts to this number are charged at your network rate.',
        'Report it to Report Fraud or Police Scotland on 101. Dial 999 if someone is on their way to your door.',
        'Use the NCSC route that matches what you received:\n- Forward a suspicious email to report@phishing.gov.uk.',
    ], 1):
        add(f'corpus semantic positive {n}', text, group='adversarial')
    for n, text in enumerate([
        'Report Fraud warns about scams. Report it to https://www.scotland.police.uk/contact-us/non-emergencies/.',
        'Report Fraud says: report it at https://www.reportfraud.police.uk.evil.invalid/.',
        'Report it to Report Fraud at report@phishing.gov.uk.',
        'Report Fraud advises using its form at https:/www.reportfraud.police.uk/.',
        f'Report it to Report Fraud via <a href="{BAD}">guidance</a>.',
        f'Contact Report Fraud at <a href="{BAD}">our guide</a>, which explains reporting.',
        f'Report Fraud advises using our reporting guide <a href="{BAD}">online</a>.',
    ], 1):
        add(f'additional association {n}', text + SCOT, 'destination', 'adversarial')
    return rows


def run_cases():
    # Local import avoids a cycle when called from gate_quickanswer_selftest.
    from gate_quickanswer_selftest import post
    results = []
    for name, text, expected, group in cases():
        result = diagnostic_gate(post(sections=[['Reporting', text]]), use_llm=False)
        blocks = [i for i in result.issues if i['severity'] == 'block']
        if expected == 'destination':
            ok = any(i['check'] in ('report_fraud_destination', 'reporting_destination') for i in blocks)
        elif expected:
            ok = any(i['check'] == expected for i in blocks)
        else:
            ok = not blocks
        results.append(dict(name=name, text=text, expected=expected, group=group,
                            ok=ok, issues=result.issues))
    for field in ('title', 'description', 'hero', 'quick_answer', 'intro', 'section heading', 'FAQ question'):
        text = f'Report the scam through {BAD}.'
        p = post(**{field: text})
        if field == 'section heading':
            p['sections'] = [[text, 'Ordinary advice.']]
        elif field == 'FAQ question':
            p['faq'] = [[text, 'Ordinary advice.']]
        issues = gate.check_deterministic(p)
        results.append(dict(name='surface ' + field, group='adversarial',
                            ok=any(i['check'] == 'reporting_destination' and i['severity'] == 'block' for i in issues),
                            issues=issues))
    posts = json.loads((Path(__file__).resolve().parents[1] / 'content/posts.json').read_text())
    for p in posts:
        if p['slug'] in ('viagogo-scam-uk', 'tinder-scam-uk', 'deepfake-video-scam-uk',
                         'facebook-dating-scam-uk', 'sextortion-email-scam-uk'):
            result = diagnostic_gate(p, use_llm=False, is_draft=False)
            results.append(dict(name=p['slug'], group='target', ok=result.passed, issues=result.issues))
    return results


if __name__ == '__main__':
    import sys
    rows = run_cases()
    if '--json' in sys.argv:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for r in rows:
            print(('PASS' if r['ok'] else 'FAIL') + ' ' + r['name'])
            if not r['ok']:
                print(json.dumps(r, ensure_ascii=False))
        print(f"{sum(r['ok'] for r in rows)}/{len(rows)} passed")
    raise SystemExit(0 if all(r['ok'] for r in rows) else 1)
