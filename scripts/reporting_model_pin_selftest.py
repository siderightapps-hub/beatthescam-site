#!/usr/bin/env python3
"""R6B2 real six-only pin, held cases and byte-derived model mutations.

No positive pin/hash predicate is mocked. Negative byte mutations use isolated
copies of all five model inputs. No signatures, production store or key access.
"""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import canon
import reporting_actions as v
import reporting_eligibility as e
import reporting_structured as s
from reporting_confirmed_contracts_selftest import EXPECTED_IDS, ORACLE
from reporting_model_extension_selftest import case_fixture
from reporting_composed_sms_selftest import fixture, RID

OLD_PIN = '1606940009f584f2ca5d4ec8f11767ca0700f61ad8657263df929642ad01830a'
R6B_PIN = '3c7909967cce32904ed71db36139cbe0a54e064e0daa2e1b90021c9afb5e76fb'
FILES = ('reporting_actions.py', 'reporting_action_canon.py',
         'reporting_action_render.py', 'reporting_structured.py', 'reporting_syntax.py')


def run_cases():
    rows = []
    c = canon.load_canon()
    cat = s.catalog_from_canon(c)
    oracle = json.loads(ORACLE.read_text())
    def check(group, name, fn):
        try:
            fn()
            ok, detail = True, ''
        except Exception as exc:
            ok, detail = False, type(exc).__name__ + ': ' + str(exc)
        rows.append(dict(group=group, name=name, ok=ok, detail=detail))
    def actual():
        assert s.contract_model_sha256() == e.REVIEWED_MODEL_SHA256 == R6B_PIN
        assert set(e.contract_production_eligible_ids(c)) == set(EXPECTED_IDS)
        assert set(e.REVIEWED_CONTRACT_IDS) == set(EXPECTED_IDS)
    check('positive', 'real byte-derived pin permits exactly six', actual)
    for rid in EXPECTED_IDS:
        def compatible(rid=rid):
            a = cat.resolve(rid)
            assert type(a) is s.Action and a.schema_version == v.V2_VERSION
            assert s.digest(asdict(a)) == c['contract_evidence']['contracts'][rid]['resolved_action_sha256']
            assert s.render_plain(cat, [rid]) == oracle['contracts'][rid]['expected_text']
            claims = e.verify_contract_eligibility(c, rid)
            assert claims['contract_model_sha256'] == R6B_PIN
            assert s.action_plan(cat, [rid])['contract_model_sha256'] == R6B_PIN
        check('six', rid, compatible)
    for label, pin in [('old', OLD_PIN), ('wrong', 'f'*64), ('empty', ''), ('null', None)]:
        def reject(pin=pin):
            actual()
            with patch.object(e, 'REVIEWED_MODEL_SHA256', pin):
                assert e.contract_production_eligible_ids(c) == ()
                for rid in EXPECTED_IDS:
                    try: e.verify_contract_eligibility(c, rid)
                    except ValueError as exc: assert 'model differs' in str(exc)
                    else: raise AssertionError('pin accepted')
            actual()
        check('pin', label, reject)
    def absent():
        # A removed source constant is a broken trusted program: hard failure,
        # never a fallback or successful eligibility decision.
        actual()
        saved = e.REVIEWED_MODEL_SHA256
        try:
            del e.REVIEWED_MODEL_SHA256
            try: e.contract_production_eligible_ids(c)
            except NameError: pass
            else: raise AssertionError('absent pin accepted')
        finally: e.REVIEWED_MODEL_SHA256 = saved
        actual()
    check('pin', 'absent source constant hard-fails', absent)
    mutations = [
        ('composition registry', 'reporting_actions.py', "'call-prefix', 'Call'", "'call-prefix', 'CALL'"),
        ('provider registry', 'reporting_actions.py', "'o2-uk-mobile-line', 'o2'", "'other-mobile-line', 'o2'"),
        ('provider selector', 'reporting_action_canon.py', "row.provider_scope_id != 'o2-uk-mobile-line'", "row.provider_scope_id != 'other-mobile-line'"),
        ('schema version', 'reporting_actions.py', "VERSION = 'restricted-actions/v3'", "VERSION = 'restricted-actions/v4'"),
    ] + [(name, name, None, None) for name in FILES]
    for label, name, before, after in mutations:
        def reject_bytes(name=name, before=before, after=after):
            actual()
            with tempfile.TemporaryDirectory(prefix='bts-pin-mutation-') as raw:
                root = Path(raw)
                for f in FILES: (root/f).write_bytes(Path(s.__file__).with_name(f).read_bytes())
                target = root/name
                text = target.read_text()
                if before is None: text += '\n# TEST model-byte mutation\n'
                else:
                    assert before in text
                    text = text.replace(before, after, 1)
                target.write_text(text)
                with patch.object(s, '__file__', str(root/'reporting_structured.py')):
                    assert s.contract_model_sha256() != R6B_PIN
                    assert e.contract_production_eligible_ids(c) == ()
            actual()
        check('model_bytes', label, reject_bytes)
    held = [('new O2 composed SMS', fixture(), RID),
            ('generic Ofcom caller SMS', fixture(composed=False), RID)]
    held += [(label, *case_fixture(label)) for label in ('C01','C04','C05','C06','M04','C02')]
    for label, source, rid in held:
        def held_case(source=source, rid=rid):
            actual()
            assert s.catalog_from_canon(source).select([rid])
            assert not e.is_contract_production_eligible(source, rid)
            assert e.contract_production_eligible_ids(source) == ()
        check('held', label, held_case)
    def overlaps():
        a = s.catalog_from_canon(fixture()).resolve(RID)
        assert len(v.SMS_COMPOSITION_CASES) == 1
        assert a.sms_composition.provider_scope_id == 'o2-uk-mobile-line'  # M06 slice
        assert a.sms_composition.provider_owner_id == 'o2'  # M11 slice
        assert a.recipient_relation == 'reader-mobile-provider'
        assert not e.is_contract_production_eligible(fixture(), RID)
        assert set(cat.actions) == set(EXPECTED_IDS)  # zero new real records
    check('held', 'two Class-C family slices add no separate action or eligibility', overlaps)
    check('positive', 'negative cases did not change real eligibility', actual)
    return rows


if __name__ == '__main__':
    rows = run_cases()
    print(json.dumps(dict(passed=sum(x['ok'] for x in rows), total=len(rows),
        cases=rows), indent=2))
    raise SystemExit(any(not x['ok'] for x in rows))
