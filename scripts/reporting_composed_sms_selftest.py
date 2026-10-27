#!/usr/bin/env python3
"""R6A AF S01–S48. Offline TEST representation, never real SMS clearance.

Literal projection oracle is independently stated below. Every negative first
resolves/renders the accepted O2 control. No caller-number value is accepted.
"""
import copy
from dataclasses import asdict, replace, FrozenInstanceError
import json
from pathlib import Path
import tempfile
from types import MappingProxyType
from unittest.mock import patch

import canon
import reporting_actions as v
import reporting_structured as s
import reporting_eligibility as e
from reporting_action_canon import destination_identity
from reporting_action_render import components, placement, faq_projection, ActionComponent
from reporting_model_extension_selftest import case_fixture
from reporting_confirmed_contracts_selftest import record, definition

CASE = 'o2-call-then-caller-number'
RID = 'own-mobile-provider:case'
GENERIC = 'own-mobile-provider:general'
EXPECTED_HTML = ('<div class="restricted-action" data-action-id="own-mobile-provider:case">'
    '<p>Your mobile provider — suspicious mobile call reporting.</p>'
    '<p>For England, Wales, Scotland, Northern Ireland. For a suspicious call received on your mobile only. '
    'Use the mobile line on which you received the suspicious call. '
    'This format is for the O2 mobile line in the UK on which you received the call.</p>'
    '<ol><li>Copy the suspicious caller’s number from recent calls on that mobile.</li>'
    '<li>Compose a new SMS beginning with <span>Call</span>, followed by one space and that caller number. '
    'Include no other message text.</li><li>Send that SMS report to Your mobile provider: '
    '<span class="reporting-shortcode">7726</span> for your mobile provider.</li></ol>'
    '<p>The SMS report to your mobile provider is free.</p><p>This service does not promise a refund.</p></div>')
EXPECTED_PLAIN = ('Your mobile provider — suspicious mobile call reporting.\n\n'
    'For England, Wales, Scotland, Northern Ireland. For a suspicious call received on your mobile only. '
    'Use the mobile line on which you received the suspicious call. '
    'This format is for the O2 mobile line in the UK on which you received the call.\n\n\n'
    'Copy the suspicious caller’s number from recent calls on that mobile.\n\n'
    'Compose a new SMS beginning with Call, followed by one space and that caller number. Include no other message text.\n\n'
    'Send that SMS report to Your mobile provider: 7726 for your mobile provider.\n\n\n'
    'The SMS report to your mobile provider is free.\n\nThis service does not promise a refund.')
GENERIC_PLAIN = ('Your mobile provider — suspicious mobile call reporting.\n\n'
    'For England, Wales, Scotland, Northern Ireland. For a suspicious call received on your mobile only. '
    'Use the mobile line on which you received the suspicious call.\n\n\n'
    'Copy the suspicious caller’s number from recent calls on that mobile.\n\n'
    'Compose a new SMS containing that caller number to Your mobile provider: 7726 for your mobile provider.\n\n'
    'Send that SMS report.\n\n\nThe SMS report to your mobile provider is free.\n\n'
    'This service does not promise a refund.')


def fixture(composed=True, both=False):
    c, rid = case_fixture('M05')
    r = record(c, rid); r['sms'] = '7726'
    d = definition(c, rid)
    d['instruction']['channels'][0]['numbering_context'] = 'GB'
    if both: r['actions']['general'] = copy.deepcopy(d)
    if composed:
        d['schema_version'] = 'restricted-actions/v3'
        d['instruction']['sms_composition_case_id'] = CASE
        # Canonical owner anchor, with its existing support semantics unchanged.
        c['verified_org_contacts'].append(copy.deepcopy(record(canon.load_canon(), 'o2-payg:customer-support')))
    return c


def denied(fn, reason=None):
    try: fn()
    except (ValueError, TypeError, FrozenInstanceError) as exc:
        assert reason is None or reason in str(exc), str(exc)
        return str(exc)
    raise AssertionError('expected rejection was not observed')


def mutated(path, value=None, missing=False):
    c = fixture(); obj = definition(c, RID)
    for key in path[:-1]: obj = obj[key]
    if missing: del obj[path[-1]]
    else: obj[path[-1]] = value
    return c


def reject_input(path, value=None, missing=False):
    return denied(lambda: s.catalog_from_canon(mutated(path, value, missing)))


def reject_row(**changes):
    cat = s.catalog_from_canon(fixture()); a = cat.resolve(RID)
    bad = replace(a, sms_composition=replace(a.sms_composition, **changes))
    counterfeit = s.Catalog(cat.canon_sha256, MappingProxyType({RID: bad}))
    assert s.digest(asdict(a)) != s.digest(asdict(bad))
    denied(lambda: ActionComponent(cat, bad).html(), 'not issued')
    return denied(lambda: ActionComponent(counterfeit, bad).html(), 'closed registry')


def model_mutation():
    old = s.contract_model_sha256()
    with tempfile.TemporaryDirectory(prefix='bts-sms-model-') as raw:
        root = Path(raw)
        for name in ('reporting_actions.py','reporting_action_canon.py','reporting_action_render.py','reporting_structured.py','reporting_syntax.py'):
            (root/name).write_bytes(Path(s.__file__).with_name(name).read_bytes())
        target=root/'reporting_actions.py'
        target.write_text(target.read_text().replace("'call-prefix', 'Call'", "'call-prefix', 'CALL'"))
        with patch.object(s, '__file__', str(root/'reporting_structured.py')):
            assert s.contract_model_sha256() != old


def replay(changed, target=RID):
    from reporting_model_binding_selftest import raw_sign
    from reporting_fixture_review import store
    import reporting_trust as trust
    c=fixture(); authority=store()
    packet=e.issue_reviewed(c,RID,reviewer='offline-fixture-reviewer',private_key=authority/'fixture-key')
    assert e.verify_contract(c,RID,packet)
    trust.verify(packet['body'],packet['signature'],'contracts',e.VERSION)
    denied(lambda:e.verify_contract(changed,target,packet),'binding')


def run_cases():
    rows=[];c=fixture();cat=s.catalog_from_canon(c);a=cat.resolve(RID);node=components(cat,[RID])[0]
    def check(n, name, fn):
        try:
            assert components(s.catalog_from_canon(fixture()),[RID])[0].html()==EXPECTED_HTML
            fn();ok=True;detail=''
        except Exception as exc:ok=False;detail=type(exc).__name__+': '+str(exc)
        rows.append({'id':f'S{n:02}', 'requirement':'R6A AF', 'name':name,'ok':ok,'detail':detail})
    def yes(value): assert value
    check(1,'exact O2 tuple and immutable row',lambda:yes(type(a) is s.ComposedSmsAction and a.action_type=='report'
        and a.sms_composition_case_id==CASE and a.sms_composition.provider_scope_id=='o2-uk-mobile-line'
        and a.sms_composition.components==('call-prefix','caller-number-from-recent-calls-sms')
        and a.sms_composition.separator==' ' and len(v.SMS_COMPOSITION_CASES)==1))
    check(2,'generic v2 literal unchanged',lambda:yes(s.render_plain(s.catalog_from_canon(fixture(False)),[RID])==GENERIC_PLAIN))
    check(3,'distinct per-action schemas and plan hashes',lambda:yes(s.action_plan_sha256(cat,[RID])!=s.action_plan_sha256(s.catalog_from_canon(fixture(False)),[RID])
        and s.action_plan(cat,[RID])['schema_version']=='restricted-actions/v3' and a.schema_version=='restricted-actions/v3'))
    check(4,'main literal HTML oracle',lambda:yes(node.html()==EXPECTED_HTML))
    check(5,'summary complete HTML',lambda:yes(placement({'kind':'action-summary','route_ids':[RID]},[RID],cat)[0].html()==EXPECTED_HTML))
    check(6,'FAQ complete HTML',lambda:yes(EXPECTED_HTML in faq_projection([{'kind':'action-faq','question_id':'where-to-report','route_ids':[RID]}],[RID],cat)[0]))
    check(7,'plain and FAQ schema literal oracle',lambda:yes(node.plain()==EXPECTED_PLAIN and faq_projection([{'kind':'action-faq','question_id':'where-to-report','route_ids':[RID]}],[RID],cat)[1][0][1]==EXPECTED_PLAIN))
    check(8,'no body value or submission link',lambda:yes(not any(x in node.html() for x in ('href="sms:','href="tel:','07123','&lt;caller')) and 'payload_value' not in asdict(a)))
    check(9,'missing fixed prefix semantic',lambda:reject_row(literal_semantic_id=''))
    check(10,'wrong prefix bytes and case',lambda:reject_row(literal='CALL'))
    check(11,'arbitrary/content prefix',lambda:reject_input(['instruction','message_prefix'],'Call'))
    check(12,'arbitrary suffix',lambda:reject_input(['instruction','suffix'],'extra'))
    check(13,'extra components',lambda:reject_input(['instruction','components'],['Call','caller','extra']))
    check(14,'reversed row components',lambda:reject_row(components=('caller-number-from-recent-calls-sms','call-prefix')))
    check(15,'removed separator',lambda:reject_row(separator=''))
    check(16,'same case ID changed literal code changes model',model_mutation)
    check(17,'original SMS payload',lambda:reject_input(['instruction','payload_profile_id'],'original-sms'))
    check(18,'suspicious-message prose payload',lambda:reject_input(['instruction','payload_profile_id'],'this is a suspicious message'))
    check(19,'original email payload',lambda:reject_input(['instruction','payload_profile_id'],'original-email'))
    check(20,'subscriber number value',lambda:reject_input(['instruction','subscriber_number'],'07123456789'))
    check(21,'account number value',lambda:reject_input(['instruction','account_number'],'12345678'))
    check(22,'numeric fact/reference cannot supply payload',lambda:reject_input(['instruction','numeric_fact'],{'kind':'reference','value':'12345678'}))
    check(23,'article caller value including malformed number',lambda:[reject_input(['instruction','caller_number'],x) for x in ('07123456789','invalid','7726','<caller-number>')])
    check(24,'arbitrary body/template/subject text',lambda:[reject_input(['instruction',k],'Call 07123456789') for k in ('sms_body','message_body','message_template','subject','payload_value')])
    check(25,'wrong provider row',lambda:reject_row(provider_owner_id='ee'))
    check(26,'missing provider scope row',lambda:reject_row(provider_scope_id=''))
    check(27,'wildcard provider scope',lambda:reject_row(provider_scope_id='*'))
    check(28,'author provider selector',lambda:[reject_input(['instruction',k],'o2') for k in ('provider','provider_scope_id','provider_owner_id')])
    check(29,'sibling/MVNO case inheritance',lambda:[reject_input(['instruction','sms_composition_case_id'],x) for x in ('virgin-call-then-caller-number','giffgaff-call-then-caller-number','ee-call-then-caller-number')])
    def support_reuse():
        bad=copy.deepcopy(c);definition(bad,'o2-payg:customer-support')['instruction']['sms_composition_case_id']=CASE
        denied(lambda:s.catalog_from_canon(bad))
    check(30,'O2 support contract cannot select composition',support_reuse)
    check(31,'false Ofcom/Hiya recipient',lambda:[reject_input(['instruction','recipient_relation'],x) for x in ('ofcom','hiya')])
    def anchor():
        for value in (None,'O₂','Virgin Media','O2 alias'):
            bad=copy.deepcopy(c)
            if value is None:bad['verified_org_contacts']=[r for r in bad['verified_org_contacts'] if r['key']!='o2-payg']
            else:record(bad,'o2-payg:customer-support')['brand']=value
            denied(lambda:s.catalog_from_canon(bad),'canonical O2')
        bad=copy.deepcopy(c);r=copy.deepcopy(record(bad,'o2-payg:customer-support'));r['key']='alias';r['brand']='Other';bad['verified_org_contacts'].append(r)
        denied(lambda:s.catalog_from_canon(bad),'conflicting labels')
    check(32,'missing/conflicting canonical owner and alias collision',anchor)
    def changed_code():
        bad=copy.deepcopy(c);record(bad,RID)['sms']='8888';assert s.catalog_from_canon(bad).resolve(RID).channels[0].value=='8888'
        assert not e.is_contract_production_eligible(bad,RID);replay(bad)
    check(33,'valid-shape changed code lacks evidence and cannot replay',changed_code)
    def bad_code(value):
        bad=copy.deepcopy(c);record(bad,RID)['sms']=value;denied(lambda:s.catalog_from_canon(bad))
    check(34,'ordinary phone/plus/separated shortcode',lambda:[bad_code(x) for x in ('07123456789','+7726','77.26','77 26')])
    check(35,'wrong field/kind/network',lambda:[reject_input(['instruction','channels'],[x]) for x in (
        {'field':'phone','kind':'phone','numbering_context':'GB'}, {'field':'email','kind':'email'},
        {'field':'sms','kind':'shortcode','numbering_context':'GB','dialling_network_id':'o2-uk'})])
    check(36,'Unicode canon digits',lambda:[bad_code(x) for x in ('７７２６','٧٧٢٦','77²6')])
    check(37,'citation cannot supply code',lambda:reject_input(['instruction','channels'],[{'field':'sources_checked/0','kind':'shortcode','numbering_context':'GB'}]))
    check(38,'prose code confers no capability',lambda:yes(bool(s.raw_destinations('Text Call 07123456789 to 7726'))))
    check(39,'valid code without selected eligible action',lambda:(yes(not e.is_contract_production_eligible(c,RID)),denied(lambda:placement({'kind':'action-summary','route_ids':[RID]},[],cat),'selected')))
    def collision():
        bad=copy.deepcopy(c); donor=copy.deepcopy(record(bad,RID));donor.update(key='unrelated',owner_id='unrelated',brand='Unrelated',name='Unrelated')
        from reporting_structured_selftest import action
        donor['actions']={'text':action('sms','shortcode')};bad['verified_org_contacts'].append(donor)
        denied(lambda:s.catalog_from_canon(bad),'collision')
        assert destination_identity(a.channels[0],'GB','')==('shortcode','GB','','7726')
    check(40,'scope cannot conceal numeric collision',collision)
    check(41,'v2 rejects new O2 selector',lambda:reject_input(['schema_version'],'restricted-actions/v2'))
    check(42,'v3 rejects generic missing selector',lambda:reject_input(['instruction','sms_composition_case_id'],missing=True))
    def downgrade():
        bad=mutated(['schema_version'],'restricted-actions/v2');del definition(bad,RID)['instruction']['sms_composition_case_id']
        assert type(s.catalog_from_canon(bad).resolve(RID)) is s.Action;replay(bad)
    check(43,'complete downgrade loses O2 evidence identity',downgrade)
    def version_only():
        bad=fixture(False);definition(bad,RID)['schema_version']='restricted-actions/v3';denied(lambda:s.catalog_from_canon(bad))
    check(44,'version-only upgrade rejects',version_only)
    check(45,'unknown missing null versions and cases',lambda:([reject_input(['schema_version'],x) for x in ('restricted-actions/v1','restricted-actions/v99',None,'')],reject_input(['schema_version'],missing=True),[reject_input(['instruction','sms_composition_case_id'],x) for x in ('',None,{},'unknown')]))
    check(46,'incompatible type/method/trigger',lambda:[reject_input(path,value) for path,value in ((['action_type'],'forward'),(['instruction','template_id'],'forward-text'),(['condition_ids'],['suspicious-text']),(['eligibility_ids'],['o2-payg-origin']))])
    def conflict():
        both=s.catalog_from_canon(fixture(both=True));both.select([RID]);both.select([GENERIC])
        denied(lambda:both.select([RID,GENERIC]),'conflict')
        denied(lambda:placement({'kind':'action-summary','route_ids':[RID,GENERIC]},[RID,GENERIC],both),'conflict')
        denied(lambda:faq_projection([{'kind':'action-faq','question_id':'where-to-report','route_ids':[RID,GENERIC]}],[RID,GENERIC],both),'conflict')
    check(47,'generic/O2 plan and placement conflict',conflict)
    def donor():
        bad=copy.deepcopy(c);record(bad,RID)['actions']['copy']=copy.deepcopy(definition(bad,RID))
        target='own-mobile-provider:copy';s.catalog_from_canon(bad).select([target]);replay(bad,target)
    check(48,'same tuple different route cannot replay donor',donor)
    return rows


if __name__=='__main__':
    rows=run_cases();print(json.dumps({'passed':sum(r['ok'] for r in rows),'total':len(rows),'cases':rows},indent=2));raise SystemExit(any(not r['ok'] for r in rows))
