#!/usr/bin/env python3
"""Offline WP3C4B exact-route, purpose, ownership and provenance regressions."""
import copy
import json
from pathlib import Path

import canon
import content_gate as gate


# Evidence identity is deliberately pinned in tests, independently of runtime
# canon lookup: substituting an endpoint in the canon must fail this suite.
DESTINATIONS = [
    ('ups-fraud', 'info_url', 'https://www.ups.com/gb/en/support/shipping-support/legal-terms-conditions/fight-fraud',
     'Report suspicious UPS texts at {dest}.'),
    ('microsoft-support-scam', 'report_url', 'https://reportfraud.microsoft.com/',
     'Report a Microsoft support scam at {dest}.'),
    ('microsoft-support-scam', 'info_url', 'https://www.microsoft.com/en-us/concern/scam',
     'Report a Microsoft support scam at {dest}.'),
    ('hmrc-phone-scam', 'report_url', 'https://www.tax.service.gov.uk/submissions/new-form/report-a-suspicious-hmrc-phone-call',
     'Report a suspicious HMRC phone call at {dest}.'),
    ('ebay-phishing', 'email', 'spoof@ebay.co.uk',
     'Forward suspicious eBay emails as attachments to {dest}.'),
    ('depop-support', 'report_url', 'https://depophelp.zendesk.com/hc/en-gb/requests/new',
     'Report a suspicious Depop seller through {dest}.'),
    ('universal-credit-gb', 'info_url', 'https://www.gov.uk/universal-credit/contact-universal-credit',
     'In England, Scotland or Wales, report misuse of your Universal Credit account through {dest}.'),
    ('universal-credit-ni', 'info_url', 'https://www.nidirect.gov.uk/articles/contact-universal-credit-help-your-claim',
     'In Northern Ireland, report misuse of your Universal Credit account through {dest}.'),
    ('mhra-online-seller', 'report_url', 'https://report-or-check-suspicious-activity.mhra.gov.uk/report/suspect-seller',
     'Report suspected illegal online medicine sellers to MHRA at {dest}.'),
    ('mhra-yellow-card', 'report_url', 'https://yellowcard.mhra.gov.uk/',
     'Report a suspected counterfeit medicine to MHRA through {dest}.'),
    ('pandora-brand-protection', 'email', 'brandprotection@pandora.net',
     'Report suspected counterfeit Pandora sites to {dest} with details in English.'),
    ('amazon-reportascam', 'report_url', 'https://www.amazon.co.uk/reportascam',
     'Report suspicious Amazon messages at {dest}.'),
    ('hmrc-branddefence', 'email', 'branddefence@hmrc.gov.uk',
     'Report a fake social media account impersonating HMRC to {dest}.'),
]


def run_cases():
    results = []
    routes = {r['key']: r for group in ('official_routes', 'verified_org_contacts')
              for r in gate._CANON[group]}

    def check(name, ok, **detail):
        results.append(dict(name=name, ok=bool(ok), **detail))

    def probe(name, text, blocked=False, **fields):
        p = dict(sections=[['Reporting', text]], **fields)
        issues = gate.check_report_fraud_destinations(p)
        check(name, bool(issues) == blocked, text=text, issues=issues)

    for key, field, dest, instruction in DESTINATIONS:
        r = routes[key]
        name = f'{key}/{field}'
        check(name + ' exact evidence value', r[field] == dest)
        probe(name + ' valid purpose', instruction.format(dest=dest))
        bad = dest.replace('@', '-fake@') if field == 'email' else dest.rstrip('/') + '/unverified'
        probe(name + ' fabricated near-match', instruction.format(dest=bad), True)
        probe(name + ' wrong organisation', f'Report the scam to NCSC at {dest}.', True)
        brand = r.get('brand', 'Amazon')
        probe(name + ' wrong purpose', f'Report investment fraud to {brand} at {dest}.', True)
        probe(name + ' heading cannot override explicit purpose',
              f'Use {dest} to report investment fraud.', True, title=instruction.format(dest=''))
        probe(name + ' demonstrative is not anaphora',
              f'Report this investment fraud at {dest}.', True, title=instruction.format(dest=''))
        if field != 'email':
            probe(name + ' query forbidden', instruction.format(dest=dest + '?redirect=evil.invalid'), True)
            probe(name + ' child host forbidden', instruction.format(dest=dest.replace('https://', 'https://unverified.')), True)
        # Verify propagation through the ONE shared judge/re-verification block.
        block = canon.render_verified_facts(gate._CANON)
        line = next(line for line in block.splitlines() if dest in line)
        check(name + ' scope/provenance propagated', all(str(r.get(f, '')) in line
              for f in ('nation', 'note', 'source_url', 'checked_on')))
        changed = copy.deepcopy(gate._CANON)
        item = next(x for group in ('official_routes', 'verified_org_contacts') for x in changed[group] if x['key'] == key)
        item[field] = 'replacement@fixture.invalid' if field == 'email' else 'https://fixture.invalid/exact'
        check(name + ' canon mutation propagates', item[field] in canon.render_verified_facts(changed))

    probe('HMRC old phishing ownership retained', 'Forward suspicious HMRC emails to phishing@hmrc.gov.uk.')
    probe('HMRC social route is not phone intake', 'Report a suspicious HMRC phone call to branddefence@hmrc.gov.uk.', True)
    probe('HMRC phone route is not social intake',
          'Report a fake social media account impersonating HMRC at ' + routes['hmrc-phone-scam']['report_url'], True)
    probe('HMRC owned global email cannot bypass purpose', 'Report investment fraud to branddefence@hmrc.gov.uk.', True)
    probe('GB route wrong nation', 'In Northern Ireland, report misuse of your Universal Credit account through ' + routes['universal-credit-gb']['info_url'], True)
    probe('NI route wrong nation', 'In England, report misuse of your Universal Credit account through ' + routes['universal-credit-ni']['info_url'], True)
    probe('UC victim route not allegation form', 'Report another claimant for benefit fraud through ' + routes['universal-credit-gb']['info_url'], True)
    probe('Yellow Card is not seller intake', 'Report a suspected illegal online medicine seller to MHRA at https://yellowcard.mhra.gov.uk/.', True)
    probe('Yellow Card is not refund intake', 'Report a refund claim for medicine to MHRA at https://yellowcard.mhra.gov.uk/.', True)
    probe('Yellow Card unsupported device scope', 'Report a defective medical device to MHRA at https://yellowcard.mhra.gov.uk/.', True)
    probe('medicine context cannot clear unrelated fraud', 'A counterfeit medicine is dangerous. Report investment fraud to MHRA at https://yellowcard.mhra.gov.uk/.', True)
    probe('Nike unsupported route remains forbidden', 'Report the counterfeit seller through the contact route on nike.com.', True)
    check('Nike destination not admitted', not any(gate._destination_matches('url', 'https://nike.com', r) for r in routes.values()))

    # Exact three source fields retained; these tests must not depend on the
    # mutable corpus changing the field into something easier to parse.
    positives = [
        "Maybe. Report it in the Starling app immediately, or call Starling's official fraud number on starlingbank.com, to secure your account. Eligible UK transfers since 7 October 2024 may fall under APP reimbursement rules, subject to limits and exclusions. Being told the payment was \"authorised\" does not by itself end a claim.",
        "Report it through the Starling app's in-app chat or by calling its official fraud number on starlingbank.com, then if you lost money or shared details, report it to Report Fraud in England, Wales, or Northern Ireland, or to Police Scotland on 101 in Scotland.",
        "Go to GOV.UK or the Companies House register independently and check the company's filing status. Do not scan the letter's QR code or use its link or bank details.\n\nCompanies House's current guidance says to report a suspicious letter by phone, using the number published in its own scam-reporting guidance on gov.uk. The address `phishing@companieshouse.gov.uk` is its route for suspicious emails, not the published reporting route for posted letters.\n\nIf money was lost, contact the bank immediately and report the crime to Report Fraud at `reportfraud.police.uk` or 0300 123 2040 in England, Wales or Northern Ireland; in Scotland, call Police Scotland on 101.",
        'Report it by calling the official fraud number on starlingbank.com.',
        'Report it by calling the official fraud number published on starlingbank.com.',
        'Companies House says to report a suspicious letter by phone, using the number published in its own scam-reporting guidance on gov.uk.',
        'Companies House says to report a suspicious letter by phone, using the number published on gov.uk.',
    ]
    for n, text in enumerate(positives, 1):
        probe(f'phone provenance positive {n}', text)
    negatives = [
        'Report it to Starling through starlingbank.com.',
        'Report it through the Starling app or submit the report at starlingbank.com.',
        'Companies House says to report a suspicious letter at gov.uk.',
        'Report it by calling 0300 123 2041, the official fraud number on starlingbank.com.',
        'Companies House says to report by phone on 0300 123 2041, using the number published in its own scam-reporting guidance on gov.uk.',
        'Report it through https://attacker.invalid/ then call the official fraud number on starlingbank.com.',
        'Report it by calling the official fraud number on starlingbank.com, then submit the report at https://attacker.invalid/.',
        'Report it by calling the official fraud number on <a href="https://attacker.invalid/">starlingbank.com</a>.',
        'Report it by calling the official fraud number published on <a href="https://attacker.invalid/">starlingbank.com</a>.',
        'Companies House says to report by phone, using the number published in its own scam-reporting guidance on <a href="https://attacker.invalid/">gov.uk</a>.',
    ]
    for n, text in enumerate(negatives, 1):
        probe(f'phone provenance negative {n}', text, True)

    root = Path(__file__).resolve().parents[1]
    posts = json.loads((root / 'content/posts.json').read_text())
    for slug in ('ups-delivery-scam-text-messages-uk', 'hmrc-phone-call-scam-uk',
                 'universal-credit-scam-uk', 'tv-licence-scam-letter-uk', 'fake-nike-website-uk',
                 'fake-online-pharmacy-uk-scam', 'fake-pandora-website-uk-scam', 'ebay-listing-fee-scam-uk'):
        p = next(p for p in posts if p['slug'] == slug)
        result = gate.run_gate(p, use_llm=False, is_draft=False)
        check('corrected guide ' + slug, result.passed, issues=result.issues)
        check('quick answer length ' + slug, 35 <= len(p['quick_answer'].split()) <= 60)
    hub = json.loads((root / 'content/category-hubs.json').read_text())['website']
    issues = gate.check_report_fraud_destinations(hub)
    check('exact corrected Yellow Card hub', not issues, issues=issues)
    return results


if __name__ == '__main__':
    import sys
    rows = run_cases()
    if '--json' in sys.argv:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for row in rows:
            if not row['ok']:
                print('FAIL', json.dumps(row, ensure_ascii=False))
        print(f"{sum(r['ok'] for r in rows)}/{len(rows)} passed")
    raise SystemExit(0 if all(r['ok'] for r in rows) else 1)
