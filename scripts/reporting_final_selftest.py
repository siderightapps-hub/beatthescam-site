#!/usr/bin/env python3
"""WP3C5: exact reporting recipient, service and jurisdiction contract.

A reader instruction may PASS only for the verified organisation, purpose and
nation. Legitimate organisations cannot bless arbitrary destinations. An exact
endpoint cannot be borrowed across organisations or purposes. Attribution and
description alone are not instructions. Unknown/mismatched destinations BLOCK.

Exercise the full deterministic gate using a valid fixture, never a paid judge.
Original reproductions, neighbours and positive controls are retained separately
from the adversarial matrix. No ignored evidence file is needed to run this suite.
"""
import json

import content_gate as gate
from reporting_legacy_test_support import diagnostic_gate

BAD = 'https://attacker.invalid/'
RF = 'https://www.reportfraud.police.uk/'
SC = ' In Scotland, contact Police Scotland on 101.'
GB = 'https://www.gov.uk/universal-credit/contact-universal-credit'
NI = 'https://www.nidirect.gov.uk/articles/contact-universal-credit-help-your-claim'
YC = 'https://yellowcard.mhra.gov.uk/'
PD = 'brandprotection@pandora.net'
UPS = 'https://www.ups.com/gb/en/support/shipping-support/legal-terms-conditions/fight-fraud'
ROUTE_CHECKS = {'reporting_destination', 'report_fraud_destination', 'scotland_routing'}


def cases():
    rows = []

    def add(name, text, block=True, group='focused', **fields):
        rows.append(dict(name=name, text=text, block=block, group=group, fields=fields))

    # Verbatim WP3D4 §13 reproductions, including the linked S3 variant.
    originals = [
        ('S1a', f'You can also report your loss at {BAD}.'),
        ('S1b', f'Report Fraud warns about ticket fraud. You can also report your loss at {BAD}.'),
        ('S2', ['Where should I report a scam?', f'Through {BAD}.']),
        ('S3a', f'Report it to Report Fraud using the form published at {BAD}.' + SC),
        ('S3b', f'Use the Report Fraud form described on {BAD} to report the loss.' + SC),
        ('S3c', f'Report it to Report Fraud using the form published at <a href="{BAD}">reportfraud.police.uk</a>.' + SC),
        ('S3d', f'Companies House says to report a suspicious letter by phone, using the number published on {BAD}.'),
        ('S4', 'Forward suspicious emails to HMRC using report@phishing.gov.uk.'),
        ('S5a', f'In Northern Ireland, your Universal Credit account may be misused. Report it through {GB}.'),
        ('S5b', f'In England, your Universal Credit account may be misused. Report it through {NI}.'),
        ('S6a', f'Report your refund request about counterfeit Pandora jewellery to {PD}.'),
        ('S6b', f'Report a complaint about a counterfeit medicine via {YC} to get your money back.'),
    ]
    for name, text in originals:
        add(name + ' exact WP3D4', text)

    for name, bad, good in [
        ('S1 adverb', f'You should immediately report your loss at {BAD}.', f'You should immediately report your loss to Report Fraud at {RF}.' + SC),
        ('S2 FAQ', ['How can I report a suspicious HMRC email?', f'Using {BAD}.'], ['How can I report a suspicious HMRC email?', 'Forward it to phishing@hmrc.gov.uk.']),
        ('S3 form', f'Report the loss using the Report Fraud form cited at {BAD}.' + SC, f'Report the loss using the Report Fraud form cited at {RF}.' + SC),
        ('S3 phone source', f'Call the Companies House number published on {BAD} to report the letter.', 'Companies House says to report a suspicious letter by phone, using the number published on gov.uk.'),
        ('S4 recipient', f'Send a suspicious email to HMRC using {RF}.' + SC, 'Forward suspicious emails to HMRC using phishing@hmrc.gov.uk.'),
        ('S5 nation', f'Your Universal Credit account is in Northern Ireland. Report it through {GB}.', f'Your Universal Credit account is in Northern Ireland. Report it through {NI}.'),
        ('S6 mixed purpose', f'Report counterfeit Pandora jewellery to {PD} for compensation.', f'Report suspected counterfeit Pandora jewellery to {PD}.'),
        ('S6 medicine', f'Report a counterfeit medicine at {YC} to recover your payment.', f'Report a suspected counterfeit medicine at {YC}.'),
    ]:
        add(name + ' variant', bad)
        add(name + ' positive', good, False)
    add('Nike original FAQ', ['How do I report the shop to Nike itself?', 'Through the contact route on `nike.com`, opened by typing the address.'])
    add('UPS original FAQ', ['Where can I report a fake UPS text in the UK?', 'You can also report the phishing page to the NCSC and notify UPS through ups.com.'])
    add('UPS precise FAQ', ['Where can I report a fake UPS text in the UK?', f'Report suspicious UPS texts using the Email UPS option at {UPS}.'], False)
    add('attribution is not an instruction', f'Report Fraud warns about ticket fraud. Its research is published at {BAD}.', False)
    add('separate FAQs cannot lend recipients', '', False, faq=[['Where can I report fraud?', 'Use the police reporting service for your nation.'], ['What address appeared in the message?', BAD]])

    def adv(name, text, block=True, **fields):
        add(name, text, block, 'adversarial', **fields)

    for modifier in ('also', 'still', 'now', 'immediately', 'safely', 'simply', 'directly', 'also immediately'):
        adv('S1 modifier ' + modifier, f'You can {modifier} report your loss at {BAD}.')
        adv('S1 modifier positive ' + modifier, f'You can {modifier} report your loss to Report Fraud at {RF}.' + SC, False)
        adv('S1 Scotland attribution ' + modifier, f'Report Fraud warns about fraud. You can {modifier} report your loss to it.')
    for lead in ('Through', 'Via', 'Using', 'At', 'On', 'The form is at'):
        adv('S2 short answer ' + lead, ['Where should I report the loss?', f'{lead} {BAD}.'])
    for dest in (BAD, 'phishing@hmrc.gov.uk.fake.invalid', '0300 123 2041', f'[reportfraud.police.uk]({BAD})'):
        adv('S2 answer identity ' + dest, ['How do I report a scam?', f'Through {dest}.'])
    adv('S2 FAQ organisation', ['Where do I forward a suspicious email to HMRC?', 'Through report@phishing.gov.uk.'])
    adv('S2 FAQ nation', ['Where do I report misuse of my Universal Credit account in Northern Ireland?', f'Through {GB}.'])
    adv('S2 FAQ nation positive', ['Where do I report misuse of my Universal Credit account in Northern Ireland?', f'Through {NI}.'], False)
    adv('S2 FAQ purpose', ['Where do I report my refund request for counterfeit Pandora jewellery?', f'To {PD}.'])
    for dest in (BAD, BAD + '?official=gov.uk', 'https://gov.uk@attacker.invalid/', 'https://gov.uk.attacker.invalid/', 'https://gov.uk/unverified', 'https://evil.gov.uk/', 'https://gov.uk:443/', 'http://gov.uk/', 'https://gov.uk/%2f', 'https://gоv.uk/', 'https://gov.uk/#report'):
        adv('S3 bare provenance ' + dest, f'Companies House says to report a suspicious letter by phone using the number published on {dest}.')
    for dest in ('https://www.gov.uk/', 'https://GOV.UK./'):
        adv('S3 exact navigation ' + dest, f'Companies House says to report a suspicious letter by phone using the number published on {dest}.', False)
    adv('S3 navigation is not intake', 'Report the letter to Companies House at gov.uk.')
    adv('S3 number source wrong owner', 'Call the HMRC number published on starlingbank.com to report fraud.')
    adv('S3 source visible text cannot bless href', f'Companies House says to report by phone using the number published on [gov.uk]({BAD}).')
    adv('S3 literal form source', f'Report the loss through the form described at {BAD}.' + SC)
    adv('S3 citation beside attack', f'Report Fraud guidance is published at {RF}. You can also report your loss at {BAD}.' + SC)
    adv('S3 real citation', 'Forward the suspicious text to 7726, as explained in <a href="https://www.ofcom.org.uk/phones-and-broadband/scam-calls-and-messages/what-to-do-about-a-scam-call-text-or-message">Ofcom guidance</a>.', False)
    for means in ('using', 'by using', 'using the address', 'using this mailbox'):
        adv('S4 means ' + means, f'Forward suspicious emails to HMRC {means} report@phishing.gov.uk.')
        adv('S4 means positive ' + means, f'Forward suspicious emails to HMRC {means} phishing@hmrc.gov.uk.', False)
    adv('S4 preceding org', 'HMRC accepts suspicious email reports. Forward them to it using report@phishing.gov.uk.')
    adv('S4 trailing org', 'Forward suspicious emails using report@phishing.gov.uk to HMRC.')
    adv('S4 multiple correct orgs', 'Forward suspicious emails to HMRC using phishing@hmrc.gov.uk, or to NCSC using report@phishing.gov.uk.', False)
    adv('S4 multiple wrong orgs', 'Forward suspicious emails to HMRC using phishing@hmrc.gov.uk, or to NCSC using phishing@hmrc.gov.uk.')
    for boundary in ('. ', '.\n\n', '.<p>'):
        adv('S5 split nation ' + repr(boundary), f'In Northern Ireland, your Universal Credit account may be misused{boundary}Report it through {GB}.')
        adv('S5 split positive ' + repr(boundary), f'In Northern Ireland, your Universal Credit account may be misused{boundary}Report it through {NI}.', False)
    adv('S5 later nation', f'Report misuse of your Universal Credit account through {GB}. This is for claimants in Northern Ireland.')
    adv('S5 alternative override', f'In England, report misuse of your Universal Credit account through {GB}. In Northern Ireland, use {NI}.', False)
    adv('S5 purpose and nation preceding', f'Your Universal Credit account may be misused. You live in Northern Ireland. Report it through {GB}.')
    for purpose in ('get your money back', 'recover your payment', 'obtain compensation', 'claim a refund', 'request reimbursement'):
        adv('S6 medicine redress ' + purpose, f'Report the counterfeit medicine through {YC} to {purpose}.')
        adv('S6 brand redress ' + purpose, f'Report the counterfeit Pandora jewellery to {PD} to {purpose}.')
    adv('S6 inherited refund', f'Your refund request concerns counterfeit Pandora jewellery. Report it to {PD}.')
    adv('S6 following refund', f'Report counterfeit Pandora jewellery to {PD}. Use this route to get your money back.')
    adv('S6 purpose limitation positive', f'Report counterfeit Pandora jewellery to {PD}. This is not a refund service.', False)
    adv('S6 negation cannot clear refund', f'Report not just counterfeit Pandora jewellery but also your refund request to {PD}.')
    adv('S6 object negation is not purpose negation', f'Report counterfeit Pandora jewellery that is not genuine to {PD} for a refund.')
    adv('S6 prior refund with explicit subject', f'I want my money back for counterfeit Pandora jewellery. Report the counterfeit jewellery to {PD}.')
    adv('S1 parenthetical', f'You can, of course, report your loss at {BAD}.')
    adv('S1 initial modifier', f'Immediately report your loss at {BAD}.')
    adv('S2 answer address label', ['How do I report it to HMRC?', 'The address is report@phishing.gov.uk.'])
    adv('S3 citation with instruction', f'Forward a suspicious email to report@phishing.gov.uk, as explained in {BAD} to report your loss.')
    adv('S3 citation alone', 'Forward a suspicious email to report@phishing.gov.uk, as explained in https://example.org/research.', False)
    adv('S3 source becomes intake', 'Companies House says to report the letter by phone using the number published on gov.uk. Submit your report there.')
    adv('S4 separate means', 'Forward suspicious emails to HMRC. Use report@phishing.gov.uk.')
    adv('S4 means names a different actor', 'Forward suspicious emails to HMRC using the NCSC address report@phishing.gov.uk.')
    adv('S4 unknown recipient', 'Forward suspicious emails to Nike using report@phishing.gov.uk.')
    adv('S6 medicine without safety purpose', f'Report a medicine at {YC}.')
    adv('S3 unknown number owner', "Report it by calling Nike's official fraud number on starlingbank.com.")
    adv('S3 nearby publisher cannot lend identity', "Companies House says to call HMRC's official fraud number on gov.uk.")
    adv('S4 lowercase unknown owner', 'Forward suspicious emails to nike using report@phishing.gov.uk.')
    adv('S4 shortcode wrong organisation', 'Forward suspicious texts to NCSC using 60599.')
    adv('S4 shortcode owner positive', 'Forward suspicious texts to HMRC using 60599.', False)
    adv('S4 near-match shortcode', 'Report your loss using 7727.')
    adv('S6 independent bank refund positive', f'Ask your bank for a refund. Report counterfeit Pandora jewellery to {PD}.', False)
    adv('S6 independent financial and safety routes', f'For a refund, contact your bank. Report a counterfeit medicine to {YC}.', False)
    adv('S3 valid HTML number source', 'Companies House says to report a suspicious letter by phone using the number published on <a href="https://www.gov.uk/">gov.uk</a>.', False)
    adv('S3 shared government host needs owner', 'Report it by calling the official fraud number published on gov.uk.')
    # Destination placement and representation must not alter the boundary.
    for text in (
        f'{BAD} Report your loss here.',
        f'{BAD}\n\nReport your loss here.',
        f'Report your loss here. {BAD}',
        f'Report your loss here.\n\n{BAD}',
        f'Report your loss through {RF} or {BAD}.' + SC,
        f'Report Fraud warns about fraud. Lodge your complaint (using {BAD}).' + SC,
        f'Report the loss using [the official form]({BAD}).',
        f'Report the loss at <a href="{BAD}">{RF}</a>.' + SC,
    ):
        adv('placement ' + text, text)
    return rows


def wp3c6b_cases():
    """New UK SHEIN service contract; original WP3C5 cases stay verbatim."""
    url = 'https://www.shein.co.uk/contact-us.html'
    hmrc = 'https://www.tax.service.gov.uk/submissions/new-form/report-a-suspicious-hmrc-phone-call'
    rows = []

    def add(name, text, block=True, **fields):
        rows.append(dict(name='WP3C6B ' + name, text=text, block=block,
                         group='wp3c6b', fields=fields))

    add('original NI', 'You can also report a suspicious HMRC-related call using the guidance at gov.uk, and forward any related text to 7726.')
    add('original UGG', 'Notify UGG through the contact options on `ugg.com`; do not use contact details supplied by the suspect seller.')
    add('original SHEIN', 'Notify SHEIN through the customer-service route reached from `shein.co.uk`, not through the suspect message.')
    add('approved NI', f'If the suspicious call mentioned HMRC, report the call to HMRC using {hmrc}. Forward any related suspicious text to 7726.', False)
    add('NI route wrong owner', f'Report a suspicious call to DWP using {hmrc}.')
    add('NI route wrong purpose', f'Report a suspicious HMRC email using {hmrc}.')
    add('NI route wrong path', f'Report a suspicious HMRC call using {hmrc}-fake.')

    approved = (f'For a scam involving a fake SHEIN site, notify SHEIN Customer Service through {url} '
                "and select Customer Service. SHEIN's UK guidance accepts scam reports whether or not "
                'money was lost. This does not replace contacting your bank or making a police report, '
                'and does not guarantee a refund.')
    add('approved SHEIN', approved, False)
    for topic in ('a fake SHEIN site', 'SHEIN impersonation', 'a SHEIN scam',
                  'phishing involving SHEIN', 'a message impersonating SHEIN'):
        add('supported purpose ' + topic, f'Report {topic} to SHEIN through {url}.', False)
    for scope in ('United Kingdom', 'UK', 'England', 'Wales', 'Scotland', 'Northern Ireland'):
        add('UK scope ' + scope, f'In {scope}, report a fake SHEIN site through {url}.', False)
    add('FAQ subject', ['Where can I report a fake SHEIN site?', f'Through {url}.'], False)
    add('preceding subject', f'I received a fake SHEIN email. Notify SHEIN through {url}.', False)
    add('preceding anaphora', f'The message impersonates SHEIN. Report it through {url}.', False)
    add('HTML gateway', f'Report a fake SHEIN site through <a href="{url}">Customer Service</a>.', False)
    add('bank refund separate', f'Ask your bank for a refund. Report a fake SHEIN site through {url}.', False)
    add('service denial', f'Report a SHEIN scam through {url}. This is not a refund service.', False)
    add('no global promise', f'Report a fake SHEIN site through {url}. This service is not global.', False)
    add('citation only', f'SHEIN explains its customer support at {url}.', False)
    add('FAQ purpose source citation', 'SHEIN scam guidance is published at https://www.shein.co.uk/faq/detail?id=77660.', False)
    add('pronoun us not US', f'Report a fake SHEIN site through {url}. This lets us notify the brand.', False)

    for topic in ('bank fraud', 'a romance scam', 'tax fraud', 'a fraudulent UGG seller',
                  'a SHEIN order delay', 'my SHEIN password reset', 'a SHEIN product return',
                  'my refund request for a fake SHEIN site', 'not just a fake SHEIN site but also my refund request'):
        add('unrelated purpose ' + topic, f'Report {topic} to SHEIN through {url}.')
    for purpose in ('get your money back', 'recover your payment', 'claim compensation',
                    'request reimbursement', 'authenticate your product', 'get a guaranteed takedown'):
        add('wrong added purpose ' + purpose, f'Report a fake SHEIN site through {url} to {purpose}.')
    add('object negation not refund denial', f'Report a fake SHEIN site that is not genuine through {url} for a refund.')
    add('inherited recovery', f'Your refund request concerns a fake SHEIN site. Report it through {url}.')
    add('following recovery', f'Report a fake SHEIN site through {url}. Use this route to get your money back.')
    add('following then recovery', f'Report a fake SHEIN site through {url}. Then use this route to recover your payment.')
    add('following modal recovery', f'Report a fake SHEIN site through {url}. You can use this route to get your money back.')
    add('following explicit product authentication', f'Report a fake SHEIN site through {url}. Ask SHEIN to authenticate your product.')
    add('denial cannot hide added reimbursement', f'Report a fake SHEIN site through {url}. This service does not guarantee a refund, but you can request reimbursement.')
    add('FAQ unrelated cannot borrow title', ['Where can I report bank fraud to SHEIN?', f'Through {url}.'], title='SHEIN scam guide')
    add('FAQ separate cannot lend purpose', '', faq=[['What happened?', 'A fake SHEIN site took money.'], ['Where can I report bank fraud?', f'Through {url}.']])

    for scope in ('United States', 'US', 'USA', 'Australia', 'Canada', 'France',
                  'Germany', 'India', 'Ireland', 'EU', 'Europe', 'all countries', 'any country'):
        add('unsupported scope ' + scope, f'For users in {scope}, report a fake SHEIN site through {url}.')
    add('inherited foreign scope', f'You live in Australia. Report a fake SHEIN site through {url}.')
    add('following global promise', f'Report a fake SHEIN site through {url}. This service is global.')
    add('following Japan scope', f'Report a fake SHEIN site through {url}. This service is for users in Japan.')
    add('unlisted reader country scope', f'For users in Brazil, report a fake SHEIN site through {url}.')
    add('unlisted direct country scope', f'In Brazil, report a fake SHEIN site through {url}.')
    add('outside UK scope', f'For users outside the UK, report a fake SHEIN site through {url}.')
    add('unlisted inherited residence', f'You live in Singapore. Report a fake SHEIN site through {url}.')
    add('reader UK scope positive', f'For users in the United Kingdom, report a fake SHEIN site through {url}.', False)
    add('reader UK nations positive', f'For users in Scotland and Northern Ireland, report a fake SHEIN site through {url}.', False)
    for dest in (BAD, 'https://www.shein.co.uk/', 'https://www.shein.co.uk/help/',
                 'https://us.shein.com/contact-us.html', 'https://help.shein.co.uk/contact-us.html',
                 'https://www.shein.co.uk.attacker.invalid/contact-us.html',
                 'https://www.shein.co.uk@attacker.invalid/contact-us.html',
                 'http://www.shein.co.uk/contact-us.html', url + '?official=true', url + '#report',
                 url.replace('.html', '%2ehtml'), url.replace('shein', 'sheіn'),
                 url.replace('.uk/', '.uk:443/'), 'https://www.shein.co.uk/faq/detail?id=77660'):
        add('unsupported destination ' + dest, f'Report a fake SHEIN site to SHEIN through {dest}.')
    add('owner mismatch', f'Report a fake SHEIN site to UGG through {url}.')
    add('actual href attack', f'Report a fake SHEIN site through <a href="{BAD}">{url}</a>.')
    add('source beside malicious intake', f'SHEIN explains scam notification at {url}. Report a fake SHEIN site through {BAD}.')
    add('later malicious alternative', f'Report a fake SHEIN site through {url} or {BAD}.')
    return rows


def wp3c6b_content_cases():
    """Assert published-input semantics, without depending on ignored packets."""
    from pathlib import Path
    import copy
    posts = {p['slug']: p for p in json.loads(
        (Path(__file__).resolve().parents[1] / 'content/posts.json').read_text())}
    ni = posts['national-insurance-scam-call-uk']
    ugg = posts['fake-ugg-website-uk']
    shein = posts['shein-fake-website-scam-uk']
    results = []

    def check(name, ok, detail=''):
        results.append(dict(name='WP3C6B content ' + name, group='wp3c6b-content',
                            ok=bool(ok), issues=[] if ok else [detail]))

    for p in (ni, ugg, shein):
        result = diagnostic_gate(p, use_llm=False, is_draft=False)
        check(p['slug'] + ' full record passes', result.passed, result.issues)
    ni_body = ni['sections'][5][1]
    check('NI exact scoped route', 'If the suspicious call mentioned HMRC, report the call to HMRC using ' +
          'https://www.tax.service.gov.uk/submissions/new-form/report-a-suspicious-hmrc-phone-call.' in ni_body)
    check('NI obsolete instruction absent', 'using the guidance at gov.uk' not in ni_body)
    check('UGG section withdraws route', 'We have not verified a UGG contact route for reporting a suspected fake shop.' in ugg['sections'][4][1])
    check('UGG FAQ withdraws route', 'We have not verified a UGG contact route for reporting a suspected fake shop.' in ugg['faq'][4][1])
    public_ugg = json.dumps({k: v for k, v in ugg.items() if k != 'content'})
    check('UGG no equivalent positive instruction', not __import__('re').search(
        r'(?:notify\s+UGG|report\b[^.!?]{0,60}\bto\s+UGG)', public_ugg, __import__('re').I))
    check('SHEIN precise service gateway', 'notify SHEIN Customer Service through https://www.shein.co.uk/contact-us.html' in shein['sections'][4][1])
    check('SHEIN old navigation instruction absent', 'customer-service route reached from' not in shein['sections'][4][1])
    canon = gate._CANON
    route = [r for r in canon.get('verified_org_contacts', []) if r['key'] == 'shein-uk-scam-notification']
    check('one exact SHEIN canon record', len(route) == 1 and route[0]['report_url'] == 'https://www.shein.co.uk/contact-us.html')
    check('no UGG route admitted', not any(r.get('brand') == 'UGG' for r in canon.get('verified_org_contacts', [])))
    # Full original article reproductions, not only shortened sentence probes.
    originals = [
        (ni, 'sections', 5, 'If the suspicious call mentioned HMRC, report the call to HMRC using https://www.tax.service.gov.uk/submissions/new-form/report-a-suspicious-hmrc-phone-call. Forward any related suspicious text to 7726.',
         'You can also report a suspicious HMRC-related call using the guidance at gov.uk, and forward any related text to 7726.'),
        (ugg, 'sections', 4, 'We have not verified a UGG contact route for reporting a suspected fake shop. Use the reporting and consumer-advice routes above, and keep the website address, messages and payment records as evidence.',
         'Notify UGG through the contact options on `ugg.com`; do not use contact details supplied by the suspect seller.'),
        (shein, 'sections', 4, 'For a scam involving a fake SHEIN site, notify SHEIN Customer Service through https://www.shein.co.uk/contact-us.html and select Customer Service. SHEIN\'s UK guidance accepts scam reports whether or not money was lost. This does not replace contacting your bank or making a police report, and does not guarantee a refund.',
         'Notify SHEIN through the customer-service route reached from `shein.co.uk`, not through the suspect message.')]
    for p, field, index, new, old in originals:
        original = copy.deepcopy(p)
        assert original[field][index][1].count(new) == 1
        original[field][index][1] = original[field][index][1].replace(new, old)
        if p is ugg:
            original['faq'][4][1] = original['faq'][4][1].replace(
                'We have not verified a UGG contact route for reporting a suspected fake shop.', 'You can also notify UGG.')
        result = diagnostic_gate(original, use_llm=False, is_draft=False)
        check(p['slug'] + ' original still blocks', any(i['check'] == 'reporting_destination' and i['severity'] == 'block' for i in result.issues), result.issues)
    return results


def run_cases():
    from gate_quickanswer_selftest import post
    results = []
    for row in cases() + wp3c6b_cases():
        fields = dict(row['fields'])
        if isinstance(row['text'], list):
            fields['faq'] = [row['text']]
            fields['sections'] = [['Advice', 'Keep safe.']]
        else:
            fields['sections'] = [['Advice', row['text']]]
        result = diagnostic_gate(post(**fields), use_llm=False)
        responsible = [i for i in result.issues if i['severity'] == gate.SEVERITY_BLOCK and i['check'] in ROUTE_CHECKS]
        ok = bool(responsible) if row['block'] else result.passed
        results.append(dict(row, ok=ok, issues=result.issues))
    return results + wp3c6b_content_cases()


if __name__ == '__main__':
    import sys
    rows = run_cases()
    if '--json' in sys.argv:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for row in rows:
            if not row['ok']:
                print('FAIL', json.dumps(row, ensure_ascii=False))
        for group in ('focused', 'adversarial', 'wp3c6b', 'wp3c6b-content'):
            subset = [r for r in rows if r['group'] == group]
            print(f"{group}: {sum(r['ok'] for r in subset)}/{len(subset)} passed")
    raise SystemExit(0 if all(r['ok'] for r in rows) else 1)
