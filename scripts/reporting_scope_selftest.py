#!/usr/bin/env python3
"""Offline current-scope regressions with disposable TEST-only SSHSIG authority.

Record authentication is deliberately tested separately from current page
authorization. Never reads production keys, signs production, or writes dist.
"""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import Mock, patch

import canon
import reporting_eligibility as eligibility
import reporting_pilot as pilot
import reporting_publication as publication
import reporting_structured as structured
import reporting_trust as trust
from reporting_structured_selftest import fixture_page


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def rejects(operation, reason=None):
    try:
        operation()
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        return reason is None or reason in str(exc)
    return False


def run():
    rows = []

    def check(group, name, operation):
        try:
            result = operation()
            ok = result is not False
            detail = '' if ok else 'assertion false'
        except Exception as exc:
            ok = False
            detail = type(exc).__name__ + ': ' + str(exc)
        rows.append({'group': group, 'name': name, 'ok': ok, 'detail': detail})

    with tempfile.TemporaryDirectory(prefix='bts-scope-test-') as raw:
        tmp = Path(raw).resolve()
        store = tmp / 'authority'; store.mkdir(mode=0o700)
        keys = [tmp / 'disposable-test-key', tmp / 'replacement-test-key']
        for key in keys:
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                           check=True, capture_output=True)
        public = [' '.join(k.with_suffix('.pub').read_text().split()[:2]) for k in keys]
        cfg = {'version': 'bts-trust/v1', 'environment': 'test', 'site': 'beatthescam.com',
               'roles': {r: [{'identity': 'scope-test-reviewer', 'public_key': public[0]}]
                         for r in trust.ROLES}, 'pilot_page_ids': [],
               'baseline_sha256': digest({}), 'revocations_sha256': digest([])}

        def write(path, value):
            path.write_bytes(canonical(value)); path.chmod(0o600)

        def policy(ids, revoked=()):
            cfg['pilot_page_ids'] = ids
            cfg['revocations_sha256'] = digest(list(revoked))
            write(store / 'trust.json', cfg)
            write(store / 'revoked.json', list(revoked))

        events = []

        def sign(body, namespace=publication.NAMESPACE, key=0):
            # Independent raw signer can create invalid TEST records; a failed
            # issuer is never mistaken for a successful consumer rejection.
            assert keys[key].parent == tmp and body['environment'] == 'test'
            data = tmp / ('decision-' + str(len(events)))
            data.write_bytes(canonical(body))
            subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys[key]),
                            '-n', namespace + ':test', str(data)], check=True, capture_output=True)
            events.append(namespace + ':test')
            return {'body': copy.deepcopy(body), 'signature': data.with_suffix('.sig').read_text()}

        def record(packet, role='context', namespace=publication.NAMESPACE):
            return trust.verify(packet['body'], packet['signature'], role, namespace)

        sources = canon.load_canon()
        pages = {}
        packets = {}
        for slug in ('independent-scope-test', 'scope-page-b', 'scope-page-c'):
            page = fixture_page(); page['slug'] = slug; page['reporting_routes'] = []
            identity = 'guide:' + slug; pages[identity] = page
            body = dict(trust.header(publication.NAMESPACE), environment='test', scope=publication.SCOPE,
                        reviewer='scope-test-reviewer', page_id=identity,
                        page_sha256=digest(page), canon_sha256=digest(sources),
                        dependencies=publication.dependencies(),
                        action_selection=publication.action_selection(sources, [], ['England']),
                        numeric_facts=[], allow_empty=True)
            packets[identity] = sign(body)
        a, b, c = pages

        def consume(identity=a, packet=None):
            return publication.review(pages[identity], sources,
                                      packets[identity] if packet is None else packet,
                                      page_id=identity)

        env = {'BTS_REVIEW_STORE': str(store), 'BTS_REVIEW_ENVIRONMENT': 'test',
               'BTS_PRODUCTION_TRUST_SHA256': '', 'CI': '', 'GITHUB_ACTIONS': '',
               'NETLIFY': '', 'SSH_AUTH_SOCK': '', 'SSH_AGENT_PID': ''}
        with patch.dict(os.environ, env):
            write(store / 'baseline.json', {})
            # Exact WP3D9H case: authentic positive, same packet, scope-only
            # removal, then empty scope. No page/dependency/signature mutation.
            policy([a])
            check('wp3d9h', 'authentic enrolled positive', lambda: bool(consume()))
            policy(['guide:other'])
            check('historical', 'removed page record remains authentic',
                  lambda: record(packets[a]) is None)
            check('wp3d9h', 'removed page verify_packet rejects', lambda: rejects(
                lambda: publication.verify_packet(packets[a], pages[a], sources, page_id=a), 'scope'))
            policy([])
            check('historical', 'empty scope record remains authentic',
                  lambda: record(packets[a]) is None)
            check('wp3d9h', 'empty scope review rejects', lambda: rejects(consume, 'scope'))

            for scope, expected in [([], (False, False, False)),
                                    ([a], (True, False, False)),
                                    ([a, b], (True, True, False)),
                                    ([b], (False, True, False)),
                                    ([], (False, False, False))]:
                policy(scope)
                for identity, allowed in zip(pages, expected):
                    check('scope_matrix', repr(scope) + ' / ' + identity,
                          lambda identity=identity, allowed=allowed:
                          bool(consume(identity)) if allowed else rejects(lambda: consume(identity), 'scope'))
                    for role in ('context', 'release'):
                        check('scope_matrix', role + ' shared predicate / ' + repr(scope) + ' / ' + identity,
                              lambda identity=identity, role=role, allowed=allowed:
                              (trust.require_page_scope(trust.config(), identity, role) is None)
                              if allowed else rejects(lambda: trust.require_page_scope(trust.config(), identity, role), 'scope'))

            # Root/scope changes do not erase historical signatures. Context
            # records have no root-digest field: reenrollment may reuse a still
            # fresh record only if ALL current checks and exact bindings pass.
            policy([])
            check('expansion', 'pre-enrollment authentic record cannot consume', lambda: rejects(consume, 'scope'))
            policy([a])
            check('expansion', 'fresh unchanged record allowed after explicit enrollment', lambda: bool(consume()))
            stale = copy.deepcopy(packets[a]['body'])
            now = datetime.now(timezone.utc)
            stale.update(issued_at=(now-timedelta(days=2)).isoformat(),
                         expires_at=(now-timedelta(days=1)).isoformat())
            stale = sign(stale)
            check('expansion', 'enrollment cannot revive expired record', lambda: rejects(lambda: consume(packet=stale), 'stale'))
            changed = copy.deepcopy(packets[a]['body']); changed['dependencies']['scripts/reporting_trust.py'] = '0'*64
            changed = sign(changed)
            check('expansion', 'enrollment cannot revive old code binding', lambda: rejects(lambda: consume(packet=changed), 'binding mismatch'))

            malformed = [None, {}, '*', [a, a], [''], ['*'], ['guide:*'],
                         ['guide:../other'], ['guide:UPPER'], ['guide:caf\u00e9'],
                         ['guide:cafe\u0301'], [1], [{}], ['guide:p'+str(i) for i in range(8)]]
            for value in malformed:
                policy(value)
                check('malformed', repr(value), lambda: rejects(consume))
            policy([a]); bad = copy.deepcopy(cfg); bad.pop('pilot_page_ids'); write(store/'trust.json', bad)
            check('malformed', 'missing scope', lambda: rejects(consume))
            policy([a])

            check('replay', 'correct page/current scope positive', lambda: bool(consume()))
            policy([a, b])
            check('replay', 'copy to another enrolled page rejected', lambda: rejects(lambda: consume(b, packets[a]), 'binding mismatch'))
            for field, value in [('page_id', b), ('environment', 'production'), ('site', 'elsewhere.example')]:
                altered = copy.deepcopy(packets[a]); altered['body'][field] = value
                check('replay', field + ' tampering', lambda altered=altered: rejects(lambda: consume(packet=altered)))
            for namespace in ('beatthescam-contract-evidence-v2', 'beatthescam-pilot-release-v2'):
                wrong = sign(packets[a]['body'], namespace)
                check('replay', namespace + ' same-key domain', lambda wrong=wrong: rejects(lambda: consume(packet=wrong), 'signature'))
            for role in ('contracts', 'release'):
                check('reviewer_role_environment', 'same-key context to ' + role,
                      lambda role=role: rejects(lambda: trust.verify(packets[a]['body'], packets[a]['signature'], role,
                          'beatthescam-contract-evidence-v2' if role=='contracts' else 'beatthescam-pilot-release-v2'), 'signature'))
            check('reviewer_role_environment', 'contracts are not page scoped',
                  lambda: rejects(lambda: trust.require_page_scope(trust.config(), a, 'contracts'), 'scope'))
            original = copy.deepcopy(cfg['roles']['context'])
            for label, entries in [('unknown/removed principal', [{'identity':'another-reviewer','public_key':public[0]}]),
                                   ('replaced key', [{'identity':'scope-test-reviewer','public_key':public[1]}])]:
                cfg['roles']['context'] = entries; policy([a])
                check('reviewer_role_environment', label, lambda: rejects(consume))
            cfg['roles']['context'] = original; policy([a])
            bad_body = copy.deepcopy(packets[a]['body']); bad_body['reviewer'] = 'unknown-reviewer'
            unknown = sign(bad_body)
            check('reviewer_role_environment', 'authentically signed unknown principal', lambda: rejects(lambda: consume(packet=unknown), 'unauthorized'))
            with patch.dict(os.environ, {'BTS_REVIEW_ENVIRONMENT':'production', 'BTS_PRODUCTION_TRUST_SHA256':digest(cfg)}):
                check('reviewer_role_environment', 'TEST trust cannot become production', lambda: rejects(consume))

            for scope, revoked, allowed in [([a], [], True), ([a], [packets[a]['body']['decision_id']], False),
                                           ([], [], False), ([], [packets[a]['body']['decision_id']], False)]:
                policy(scope, revoked)
                check('revocation', repr(scope) + ' revoked=' + str(bool(revoked)),
                      lambda allowed=allowed: bool(consume()) if allowed else rejects(consume))
            policy([a])
            # A scope change while OpenSSH is running cannot return cached/stale
            # authorization. The next call also sees the new empty policy.
            original_run = trust.subprocess.run
            def change_during_verify(*args, **kwargs):
                result = original_run(*args, **kwargs)
                if args[0][0:3] == ['ssh-keygen', '-Y', 'verify']:
                    policy([])
                return result
            with patch.object(trust.subprocess, 'run', side_effect=change_during_verify):
                check('refresh', 'mid-verification scope shrink rejects', lambda: rejects(consume, 'trust changed'))
            check('refresh', 'next consumption sees empty scope', lambda: rejects(consume, 'scope'))
            policy([a])
            original_validate = structured.validate_page
            def change_during_validation(*args, **kwargs):
                result = original_validate(*args, **kwargs)
                policy([])
                return result
            with patch.object(structured, 'validate_page', side_effect=change_during_validation):
                check('refresh', 'scope shrink during page validation rejects', lambda: rejects(consume, 'trust changed'))

            # Real gate/writer/render callers must not consume stale context.
            import build
            import content_gate as gate
            import generate_content_claude as writer
            site = trust.read_json(publication.ROOT/'content/site.json')
            target = tmp/'posts.json'; target.write_text('[]\n')
            policy([a])
            check('consumers', 'in-scope gate positive', lambda:
                gate.run_gate(pages[a], use_llm=False, reporting_canon=sources, reporting_review=packets[a]).passed)
            check('consumers', 'in-scope guide render positive', lambda:
                bool(build.render_post(site, pages[a], [pages[a]], sources=sources, reporting_review=packets[a])))
            hub = {k:v for k,v in pages[a].items() if k in ('title','description','sections','faq','reporting_routes')}
            hub_body = copy.deepcopy(packets[a]['body'])
            hub_body.update(page_id='hub:email', page_sha256=digest(hub))
            hub_packet = sign(hub_body)
            policy([a, 'hub:email'])
            check('consumers', 'in-scope hub render positive', lambda:
                bool(build.render_category_page(site,'email',[],hub=hub,reporting_sources=sources,reporting_review=hub_packet)))
            for label, scope in [('removed', [b]), ('empty', [])]:
                policy(scope)
                check('consumers', label+' gate rejects with structured_reporting', lambda:
                    any(i['check']=='structured_reporting' and 'scope' in i['detail']
                        for i in gate.run_gate(pages[a], use_llm=False, reporting_canon=sources,
                                              reporting_review=packets[a]).issues))
                def writer_rejects():
                    result = rejects(lambda: writer.save_posts(str(target), [pages[a]], reporting_canon=sources,
                        reporting_reviews={pages[a]['slug']:packets[a]}, quarantine_dir=tmp/'quarantine'), 'scope')
                    return result and target.read_text() == '[]\n'
                check('consumers', label+' writer rejects before write', writer_rejects)
                check('consumers', label+' guide renderer rejects', lambda: rejects(lambda:
                    build.render_post(site, pages[a], [pages[a]], sources=sources, reporting_review=packets[a]), 'scope'))
                check('consumers', label+' hub renderer rejects', lambda: rejects(lambda:
                    build.render_category_page(site,'email',[],hub=hub,reporting_sources=sources,reporting_review=hub_packet), 'scope'))
            # Exercise the production-only outer predicate with an isolated
            # adapter. Authentication still runs the real TEST verifier against
            # TEST metadata, domain and keys; no production signature is made.
            rid = 'citizens-advice:consumer-advice-english'
            contract = eligibility.issue_reviewed(sources,rid,reviewer='scope-test-reviewer',private_key=keys[0])
            eligibility.packet_path(rid).parent.mkdir(exist_ok=True)
            write(eligibility.packet_path(rid), contract)
            eligible_page = copy.deepcopy(pages[a]); eligible_page['reporting_routes'] = [rid]
            eligible_body = copy.deepcopy(packets[a]['body'])
            eligible_body.update(page_sha256=digest(eligible_page), allow_empty=False,
                action_selection=publication.action_selection(sources,[rid],['England','Wales']))
            eligible_packet = sign(eligible_body)
            adapter = Mock(wraps=trust); adapter.environment.return_value = 'production'
            policy([a])
            check('eligibility', 'TEST page never gains production eligibility', lambda:
                not publication.is_page_publication_eligible(eligible_page,sources,eligible_packet,page_id=a))
            with patch.object(publication,'trust',adapter):
                check('eligibility', 'adapter in-scope production predicate positive', lambda:
                    publication.is_page_publication_eligible(eligible_page,sources,eligible_packet,page_id=a))
                for scope in ([b], []):
                    policy(scope)
                    check('eligibility', repr(scope)+' production predicate denies current scope', lambda:
                        not publication.is_page_publication_eligible(eligible_page,sources,eligible_packet,page_id=a))
            for scope in ([b], []):
                policy(scope)
                check('eligibility', repr(scope)+' shared production consumer rejects', lambda:
                    rejects(lambda: publication.verify_packet(packets[a], pages[a], sources, page_id=a), 'scope'))
            policy([a])
            check('refresh', 'valid control restored after all policy transitions', lambda: bool(consume()))
    return rows, events, not tmp.exists()


if __name__ == '__main__':
    rows, events, cleaned = run()
    groups = {g: {'pass':sum(r['ok'] for r in rows if r['group']==g),
                  'total':sum(r['group']==g for r in rows)} for g in sorted({r['group'] for r in rows})}
    result = {'pass':sum(r['ok'] for r in rows), 'total':len(rows), 'groups':groups, 'rows':rows,
              'test_signing_namespaces':events, 'production_signatures_created':0,
              'disposable_directory_removed':cleaned}
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['pass']==result['total'] and cleaned else 1)
