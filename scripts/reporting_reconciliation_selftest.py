#!/usr/bin/env python3
"""R4 bounded dependency, legacy HOLD and parser regressions. Offline.

The 18 legacy cases have no structured action selection. These tests preserve
that distinction; passing them is NOT proof of resolved action semantics.
No builds, signing, private-key access or production-store writes.
"""
import hashlib
import json
from pathlib import Path

import canon
import corpus
import content_gate as gate
import reporting_eligibility as eligibility
import reporting_pilot as pilot
import reporting_publication as publication
import reporting_structured as structured

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'scripts/fixtures/wp3c9k_r4_reconciliation.json'


def run_cases():
    oracle = json.loads(FIXTURE.read_text())
    sources = canon.load_canon(ROOT / 'content/sources.json')
    selected, posts, hubs = pilot.load_pages(ROOT, [oracle['approved_phone']['page_id']])
    pages = {'guide:' + p['slug']: p for p in corpus.public_posts(posts)}
    pages.update({'hub:' + k: v for k, v in hubs.items()})
    rows = []

    def check(group, name, condition):
        rows.append({'group': group, 'name': name, 'ok': bool(condition)})

    for path, expected in oracle['source_dependencies'].items():
        check('source', path, hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == expected)
    check('scope', '204 public pages remain unapproved without external authority', len(pages) == 204 and
          all(not publication.is_page_publication_eligible(p, sources, page_id=i)
              for i, p in pages.items()) and set(selected) == {'hub:phone'})
    approved = oracle['approved_phone']
    check('source', 'exact R11 phone source and action plan',
          structured.digest(hubs['phone']) == approved['source_sha256']
          and hubs['phone']['reporting_routes'] == approved['route_ids']
          and structured.action_plan_sha256(structured.catalog_from_canon(sources),
                                           approved['route_ids']) == approved['action_plan_sha256'])
    check('scope', 'exact six contract IDs', set(eligibility.contract_production_eligible_ids(sources)) == {
        'citizens-advice:consumer-advice-english', 'victim-support:supportline',
        'o2-pay-monthly:customer-support', 'o2-payg:customer-support',
        'own-bank:number-on-bank-card', 'own-bank:existing-bank-app'})
    for case in oracle['semantic_cases']:
        page = pages[case['page_id']]
        check('semantic_hold', case['id'],
              'reporting_routes' not in page and case['expected_action_authority'] is None
              and structured.digest(page) == case['source_sha256']
              and publication.legacy_unchanged(page, case['page_id'])
              and not publication.is_page_publication_eligible(page, sources, page_id=case['page_id']))
    for case in oracle['factual_cases']:
        page = pages['guide:' + case['slug']]
        # A reviewed proposition identity, not a general ban on words elsewhere.
        check('factual_source', case['id'], structured.digest(page['description']) ==
              case['source_description_sha256'])

    def issues(text):
        return gate.check_report_fraud_destinations({'sections': [['Reporting', text]]})

    cases = [
        ('GATE01 unknown recipient retained', 'Forward suspicious emails to the scam team at phishing@hmrc.gov.uk.', True),
        ('GATE01 legitimate owner', 'Forward suspicious HMRC emails to phishing@hmrc.gov.uk.', False),
        ('GATE02 trailing foreign audience', 'Report a fake SHEIN site through https://www.shein.co.uk/contact-us.html for customers in Brazil.', True),
        ('GATE02 UK neighbour', 'Report a fake SHEIN site through https://www.shein.co.uk/contact-us.html for customers in Scotland.', False),
        ('GATE03 follow-on outcome', 'Report a fake SHEIN site through https://www.shein.co.uk/contact-us.html. The team will close the shop.', True),
        ('GATE03 no refund promise', 'Report a fake SHEIN site through https://www.shein.co.uk/contact-us.html. This is not a refund service.', False),
        ('BUILD01 fresh text object does not inherit NCSC', 'Forward suspicious emails to the NCSC at report@phishing.gov.uk; forward suspicious texts to 7726.', False),
        ('BUILD01 explicit wrong owner still blocked', 'Forward suspicious texts to the NCSC at 7726.', True),
        ('BUILD02 dependent dial retains local bank object', 'Report to your bank first if money or account details are involved — dial 159 or use the number on your card.', False),
        ('BUILD02 absent bank object stays blocked', 'Report a suspicious phone call — dial 159.', True),
        ('BUILD03 caller payload stays blocked', "From a mobile, forward the caller's phone number to 7726.", True),
        ('BUILD03 text payload remains supported', 'Forward a suspicious SMS text to 7726.', False),
    ]
    for name, text, blocked in cases:
        check('gate', name, bool(issues(text)) == blocked)
    printer = next(p for p in posts if p['slug'] == 'printer-support-scam-uk')
    check('gate', 'GATE02 previous device advice is not a foreign audience',
          not gate.check_report_fraud_destinations(printer))
    phone = gate.check_report_fraud_destinations(hubs['phone'])
    check('gate', 'BUILD03 approved R11 phone removes caller-SMS instruction',
          not phone and '7726' not in json.dumps(hubs['phone']))
    return rows


if __name__ == '__main__':
    rows = run_cases()
    groups = {g: {'passed': sum(r['ok'] for r in rows if r['group'] == g),
                  'total': sum(r['group'] == g for r in rows)} for g in sorted({r['group'] for r in rows})}
    print(json.dumps({'groups': groups, 'results': rows}, indent=2))
    raise SystemExit(any(not r['ok'] for r in rows))
