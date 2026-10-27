#!/usr/bin/env python3
"""Prepare an exact review receipt, then explicitly sign its expected digest.

No enrollment, implicit artifact selection, network, model or deployment. Run
trusted reviewed code in the isolated reviewer account. A receipt is not approval.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import canon
import reporting_eligibility as eligibility
import reporting_pilot as pilot
import reporting_publication as publication
import reporting_runtime as runtime
import reporting_structured as structured
import reporting_trust as trust


def exact_path(value, label):
    path = Path(value)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError(label+' must be an explicit absolute canonical path')
    return path


def prepare(args):
    if args.environment not in ('test', 'production') or args.role not in trust.ROLES:
        raise ValueError('explicit environment and role required')
    if trust.environment() != args.environment:
        raise ValueError('process and selected environment differ')
    root = exact_path(args.candidate, 'candidate')
    if root != publication.ROOT:
        raise ValueError('run the reviewed command from the exact candidate checkout')
    measured = runtime.require(root)
    before = pilot.inputs(root)
    cfg = trust.config()
    row = next((r for r in cfg['roles'][args.role] if r['identity'] == args.reviewer), None)
    if row is None: raise ValueError('reviewer is not enrolled for selected role')
    sources = canon.load_canon(root/'content/sources.json')
    payload = {}
    detail = {}
    if args.role == 'contracts':
        if not args.route_id or args.page or args.page_id or args.artifact or args.audience or args.allow_empty:
            raise ValueError('contracts requires only an explicit --route-id')
        eligibility.verify_contract_eligibility(sources, args.route_id)
        payload = {'claims': eligibility.claims(sources, args.route_id)}
        detail = {'contract_ids':[args.route_id], 'actions':structured.render_plain(structured.catalog_from_canon(sources), [args.route_id])}
        namespace = eligibility.VERSION
        scope = 'exact-contract-evidence-endorsement; does not grant canon clearance'
    elif args.role == 'context':
        if not args.page or not args.page_id or not args.audience or args.route_id or args.artifact:
            raise ValueError('context requires explicit --page, --page-id and --audience')
        trust.require_page_scope(cfg, args.page_id, 'context')
        page_path = exact_path(args.page, 'page')
        page = trust.read_json(page_path)
        if args.page_id.startswith('guide:') and args.page_id != 'guide:'+page.get('slug', ''):
            raise ValueError('page identity and slug differ')
        eligibility.require_contract_actions(sources, page.get('reporting_routes'))
        # Both TEST and production UX require real contract clearance plus
        # endorsements. Grammar-fixture helpers remain separate TEST-only code.
        eligibility.require_actions(sources, page.get('reporting_routes'))
        payload = dict(scope=publication.SCOPE, page_id=args.page_id,
            page_sha256=trust.digest(page), canon_sha256=trust.digest(sources),
            dependencies=publication.dependencies(),
            action_selection=publication.action_selection(sources, page.get('reporting_routes'), args.audience),
            numeric_facts=[], allow_empty=args.allow_empty)
        check_body = dict(payload, reviewer=args.reviewer, decision_id='0'*32)
        context = publication._context(page, sources, check_body)
        structured.validate_page(page, structured.catalog_from_canon(sources), context, page_id=args.page_id)
        detail = {'page_path':str(page_path), 'page':page,
                  'contract_ids':page['reporting_routes'], 'audience':args.audience,
                  'actions':structured.render_plain(structured.catalog_from_canon(sources), page['reporting_routes'])}
        namespace = publication.NAMESPACE
        scope = publication.SCOPE
    else:
        if not args.artifact or args.page or args.page_id or args.route_id or args.audience or args.allow_empty:
            raise ValueError('release requires only an explicit --artifact')
        artifact = exact_path(args.artifact, 'artifact')
        files = pilot.tree(artifact)
        import reporting_revision
        revision = reporting_revision.worktree(root, getattr(args, 'candidate_sha', None))
        payload = {'manifest':pilot.candidate(root, files, source_revision=revision)}
        detail = {'artifact_path':str(artifact), 'manifest_sha256':trust.digest(payload['manifest']),
                  'archive_sha256':pilot.sha(pilot.zip_bytes(files)),
                  'contract_ids':sorted({r for p in payload['manifest']['pages'] for r in p['route_ids']})}
        detail['actions']=structured.render_plain(structured.catalog_from_canon(sources),detail['contract_ids'])
        namespace = pilot.VERSION
        scope = 'exact-complete-output; no platform deployment authority'
    receipt = {'version':'bts-review-receipt/v1', 'environment':args.environment,
        'role':args.role, 'reviewer':args.reviewer, 'site':trust.SITE,
        'public_key_fingerprint':'SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(row['public_key'].split()[1])).digest()).decode().rstrip('='),
        'candidate_path':str(root), 'candidate_inputs_sha256':before, 'namespace':namespace,
        'scope':scope, 'maximum_validity_days':7, 'runtime':measured,
        'canon_sha256':trust.digest(sources), 'contract_model_sha256':structured.contract_model_sha256(),
        'eligible_contract_ids':list(eligibility.contract_production_eligible_ids(sources)),
        'manifest_sha256':detail.get('manifest_sha256'),
        'manifest_scope':('complete authenticated output' if args.role=='release'
                          else 'not issued by this role; separate release approval required'),
        'dependencies':publication.dependencies(), 'trust_sha256':trust.digest(cfg),
        'baseline_sha256':cfg['baseline_sha256'], 'revocations_sha256':cfg['revocations_sha256'],
        'enrolled_page_ids':cfg['pilot_page_ids'], 'payload':payload, 'detail':detail}
    if pilot.inputs(root) != before or trust.config() != cfg:
        raise ValueError('candidate/trust changed while preparing receipt')
    return receipt


def issue(args):
    if not args.expected_receipt_sha256 or not args.key_file or not args.output:
        raise ValueError('sign requires --expected-receipt-sha256, --key-file and --output')
    if args.environment == 'test' and not args.test_only:
        raise ValueError('automated TEST signing requires --test-only')
    if args.environment == 'production' and args.test_only:
        raise ValueError('--test-only cannot sign production')
    receipt = prepare(args)
    if trust.digest(receipt) != args.expected_receipt_sha256:
        raise ValueError('stale or wrong expected receipt; prepare and review the candidate again')
    def recheck():
        if trust.digest(prepare(args)) != args.expected_receipt_sha256:
            raise ValueError('stale or wrong expected receipt; prepare and review the candidate again')
    recheck()
    body = dict(trust.header(receipt['namespace']), reviewer=args.reviewer, **receipt['payload'])
    packet = trust.sign(body, exact_path(args.key_file, 'key'), args.role, receipt['namespace'],
                        review_summary=receipt, recheck=recheck)
    recheck()
    export(args.output, packet)
    return {'written':str(args.output), 'packet_sha256':trust.digest(packet),
            'receipt_sha256':trust.digest(receipt), 'environment':args.environment, 'role':args.role}


def export(value, packet):
    """Public packet only; exclusive creation in an owner-controlled directory."""
    path = exact_path(value, 'output')
    if publication.ROOT in path.parents or any((p/'.git').exists() for p in path.parents):
        raise ValueError('packet export must be outside repositories')
    data = json.dumps(packet, indent=2, ensure_ascii=True).encode()+b'\n'
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parent = os.fstat(directory)
        if parent.st_uid != os.getuid() or parent.st_mode & 0o022:
            raise ValueError('packet output directory must be owner-controlled')
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    finally:
        os.close(directory)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def dry_run():
    root = publication.ROOT
    result = {'candidate_path':str(root), 'candidate_inputs_sha256':pilot.inputs(root),
        'contract_eligible_ids':None, 'publication_endorsed_contracts':None,
        'environment':trust.environment(), 'deployment_eligible':False,
        'manifest_sha256':None, 'remote_enforcement':'not tested by this local command',
        'github_platform_enforcement':{'status':'HOLD', 'reason':'requires independent current remote evidence'},
        'netlify_platform_enforcement':{'status':'HOLD', 'reason':'requires independent current remote evidence'},
        'publication':{'status':'HOLD', 'reason':'dry-run grants no publication authority'}}
    try:
        sources = canon.load_canon()
        result['contract_eligible_ids'] = list(eligibility.contract_production_eligible_ids(sources))
        result['publication_endorsed_contracts'] = list(eligibility.publication_endorsed_ids(sources))
        result['contracts'] = {'status':'PASS'}
    except (ImportError, ValueError, OSError, KeyError) as exc:
        result['contracts'] = {'status':'HOLD', 'reason':str(exc)}
    for name, operation in [('runtime', runtime.require), ('trust', trust.config)]:
        try: result[name] = {'status':'PASS', 'identity':operation()}
        except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
            result[name] = {'status':'HOLD', 'reason':str(exc)}
    try:
        result['deployment_verifier'] = pilot.netlify_verify(root)
        result['manifest_sha256'] = result['deployment_verifier']['manifest_sha256']
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        result['deployment_verifier'] = {'status':'HOLD', 'reason':str(exc)}
    # A dry run never grants a deployment capability, even with valid inputs.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='dry-run', choices=('dry-run','prepare','sign'))
    parser.add_argument('--environment', choices=('production','test'))
    parser.add_argument('--role', choices=trust.ROLES)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--candidate-sha')
    parser.add_argument('--reviewer')
    parser.add_argument('--route-id')
    parser.add_argument('--page', type=Path)
    parser.add_argument('--page-id')
    parser.add_argument('--audience', nargs='+')
    parser.add_argument('--allow-empty', action='store_true')
    parser.add_argument('--artifact', type=Path)
    parser.add_argument('--expected-receipt-sha256')
    parser.add_argument('--key-file', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--test-only', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'dry-run': result = dry_run()
        else:
            if not all((args.environment, args.role, args.candidate, args.reviewer)):
                parser.error('--environment, --role, --candidate and --reviewer are required')
            ambient = os.environ.get('BTS_REVIEW_ENVIRONMENT')
            if ambient is not None and ambient != args.environment:
                raise ValueError('ambient and explicit environment differ')
            os.environ['BTS_REVIEW_ENVIRONMENT'] = args.environment
            if args.command == 'prepare':
                receipt = prepare(args)
                result = {'receipt_sha256':trust.digest(receipt), 'receipt':receipt, 'approval':False}
            else: result = issue(args)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print('BLOCKED: '+str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
