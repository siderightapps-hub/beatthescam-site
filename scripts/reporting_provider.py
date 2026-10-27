#!/usr/bin/env python3
"""Offline provider handoff and exact static readback comparison.

No network client, URL fetching, deployment, signature issuance or enrollment.
An operator later collects bounded response bodies and public metadata. These
are observations, not cryptographic provider attestations. Exact bytes remain
mandatory; the HTML event projection is an additional diagnostic only.
"""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys

import reporting_pilot as pilot
import reporting_publication as publication
import reporting_reviewer as reviewer
import reporting_runtime as runtime
import reporting_trust as trust

VERSION = 'bts-provider-handoff/v1'
RESERVED = frozenset({'_headers', '_redirects'})  # Provider instructions, not HTTP files.


def digest_value(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ValueError('invalid '+label+' digest')
    return value


def target_value(value):
    if not isinstance(value, dict) or set(value) != {'site_id', 'team_id', 'project', 'production_origin'}:
        raise ValueError('invalid provider target schema')
    if (not isinstance(value['site_id'], str) or not re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}', value['site_id'])
            or not isinstance(value['team_id'], str) or not re.fullmatch(r'[a-f0-9]{24}', value['team_id'])
            or not isinstance(value['project'], str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value['project'])
            or len(value['project']) > 63 or value['production_origin'] != 'https://beatthescam.com'):
        raise ValueError('invalid provider target identity')
    return dict(value)


def deploy_value(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{24}', value):
        raise ValueError('invalid immutable deploy identity')
    return value


class Projection(HTMLParser):
    """Ordered tags/attributes/text, including all links and endpoint-free actions.

    HTMLParser decodes character references once; no whitespace, attribute,
    timestamp, script, method or qualifier is removed. This is not a browser or
    a semantic authorization engine. Raw-byte equality is checked separately.
    """
    def __init__(self, data):
        super().__init__(convert_charrefs=True)
        self.events = []
        self.feed(data.decode('utf-8', errors='strict'))
        self.close()

    def handle_starttag(self, tag, attrs):
        self.events.append(['start', tag, [list(a) for a in attrs]])

    def handle_startendtag(self, tag, attrs):
        self.events.append(['empty', tag, [list(a) for a in attrs]])

    def handle_endtag(self, tag):
        self.events.append(['end', tag])

    def handle_data(self, data):
        self.events.append(['text', data])

    def handle_comment(self, data):
        self.events.append(['comment', data])

    def handle_decl(self, decl):
        self.events.append(['declaration', decl])


def projections(files):
    return {name: trust.digest(Projection(data).events) for name, data in sorted(files.items())
            if name.endswith('.html')}


def served_paths(files):
    result = {}
    for name in files:
        pilot.path_name(name)
        if name in RESERVED:
            continue
        path = '/'+name
        if name == 'index.html' or name.endswith('/index.html'):
            path = path[:-len('index.html')]
        if path in result.values():
            raise ValueError('colliding served URL paths')
        result[name] = path
    return result


def prepare(root, files, packet, *, environment, target, source_revision):
    """Reauthenticate current authority/output; the returned record cannot deploy."""
    if environment not in ('test', 'production') or trust.environment() != environment:
        raise ValueError('explicit matching handoff environment required')
    if Path(root) != publication.ROOT:
        raise ValueError('run handoff from the exact reviewed candidate')
    target = target_value(target)
    if not isinstance(source_revision, str) or not re.fullmatch(r'[a-f0-9]{40}', source_revision):
        raise ValueError('explicit full source revision required')
    measured = runtime.require(root)
    import reporting_revision
    revision = reporting_revision.worktree(root, source_revision)
    data = pilot.zip_bytes(files)
    verified = (pilot.verify_test_bundle(packet, root, data, source_revision=revision) if environment == 'test'
                else pilot.verify_bundle(packet, root, data, source_revision=revision))
    manifest = packet['body']['manifest']  # Equal to freshly recomputed manifest above.
    # The declared revision must now match both Git bytes and signed release.
    return {'version': VERSION, 'environment': environment, 'deployment_authority': False,
            'target': target, 'declared_source_revision': source_revision,
            'candidate_inputs_sha256': manifest['inputs_sha256'],
            'manifest_sha256': verified['manifest_sha256'],
            'canonical_archive_sha256': verified['archive_sha256'],
            'release_packet_sha256': trust.digest(packet), 'runtime': measured,
            'files': manifest['files'], 'served_paths': served_paths(files),
            'html_projection_sha256': projections(files), 'pages': manifest['pages'],
            'provider_config_sha256': pilot.sha(trust.read_file(root/'netlify.toml')),
            'function_source_sha256': pilot.hashes(pilot.tree(root/'netlify/functions', source=True)),
            'package_lock_sha256': pilot.sha(trust.read_file(root/'package-lock.json')),
            'provider_boundary': 'HOLD: compiled Functions, effective routing/headers/transforms and capture provenance require owner/platform evidence'}


def expected_observation(record, deploy_id):
    """Public metadata schema; templates are not observations or provider proof."""
    deploy_id = deploy_value(deploy_id)
    target = target_value(record['target'])
    origins = {'deploy': 'https://'+deploy_id+'--'+target['project']+'.netlify.app',
               'production': target['production_origin']}
    return {'version': 'bts-provider-observation/v1', 'site_id': target['site_id'],
            'team_id': target['team_id'], 'deploy_id': deploy_id,
            'source_revision': record['declared_source_revision'],
            'candidate_inputs_sha256': record['candidate_inputs_sha256'],
            'manifest_sha256': record['manifest_sha256'],
            'canonical_archive_sha256': record['canonical_archive_sha256'],
            'responses': {origin: {name: {'url': base+path, 'status': 200,
                'sha256': record['files'][name]} for name, path in record['served_paths'].items()}
                for origin, base in origins.items()}}


def compare(record, expected_digest, observation, captured, *, deploy_id):
    """Pure bounded comparison. The trusted digest must come from the reviewed handoff.

    Callers must also freshly authenticate the candidate/approvals; the CLI does
    so. A successful comparison does not attest the collector, provider's code,
    routing, headers or current production authority.
    """
    digest_value(expected_digest, 'expected handoff')
    if trust.digest(record) != expected_digest:
        raise ValueError('handoff identity mismatch')
    if record.get('version') != VERSION or record.get('deployment_authority') is not False:
        raise ValueError('invalid handoff version or authority')
    expected = expected_observation(record, deploy_id)
    if observation != expected:
        raise ValueError('provider observation identity/URL/status/hash mismatch')
    wanted = {origin+'/'+name: record['files'][name]
              for origin in ('deploy', 'production') for name in record['served_paths']}
    pilot.check_names(captured)
    if set(captured) != set(wanted):
        raise ValueError('missing or unexpected captured path')
    # No warning-only difference and no normalized-byte fallback.
    if pilot.hashes(captured) != wanted:
        raise ValueError('served byte mismatch')
    for origin in ('deploy', 'production'):
        actual = projections({name: captured[origin+'/'+name] for name in record['served_paths']})
        if actual != record['html_projection_sha256']:
            raise ValueError('security projection mismatch')
    return {'static_readback': 'PASS', 'environment': record['environment'],
            'deploy_id': deploy_id, 'handoff_sha256': expected_digest,
            'compared_responses': len(wanted), 'deployment_eligible': False,
            'production_acceptance': 'HOLD', 'provider_boundary': record['provider_boundary']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'compare'))
    parser.add_argument('--environment', required=True, choices=('test', 'production'))
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--packet', required=True, type=Path)
    parser.add_argument('--target', required=True, type=Path)
    parser.add_argument('--source-revision', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--handoff', type=Path)
    parser.add_argument('--expected-handoff-sha256')
    parser.add_argument('--observation', type=Path)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--expected-deploy-id')
    args = parser.parse_args()
    try:
        root = publication.ROOT
        artifact = reviewer.exact_path(args.artifact, 'artifact')
        files = pilot.tree(artifact)
        packet = trust.read_json(reviewer.exact_path(args.packet, 'release packet'))
        record = prepare(root, files, packet, environment=args.environment,
                         target=trust.read_json(reviewer.exact_path(args.target, 'target')),
                         source_revision=args.source_revision)
        if args.command == 'prepare':
            if not args.output or any((args.handoff, args.expected_handoff_sha256, args.observation,
                                       args.capture, args.expected_deploy_id)):
                raise ValueError('prepare requires only an explicit new external --output')
            result = {'handoff_sha256': trust.digest(record), 'deployment_eligible': False}
        else:
            if args.output or not all((args.handoff, args.expected_handoff_sha256, args.observation,
                                      args.capture, args.expected_deploy_id)):
                raise ValueError('compare requires explicit handoff/digest/observation/capture/deploy identity')
            saved = trust.read_json(reviewer.exact_path(args.handoff, 'handoff'))
            if saved != record:
                raise ValueError('handoff differs from currently authenticated candidate')
            captured = pilot.tree(reviewer.exact_path(args.capture, 'capture'))
            observation = trust.read_json(reviewer.exact_path(args.observation, 'observation'))
            result = compare(saved, args.expected_handoff_sha256, observation, captured,
                             deploy_id=args.expected_deploy_id)
            if pilot.hashes(pilot.tree(args.capture)) != pilot.hashes(captured):
                raise ValueError('capture changed during comparison')
        # Reauthenticate after comparison/export preparation, before any result.
        if pilot.hashes(pilot.tree(artifact)) != pilot.hashes(files) or prepare(
                root, files, packet, environment=args.environment,
                target=record['target'], source_revision=args.source_revision) != record:
            raise ValueError('candidate/artifact/authority changed during handoff')
        if args.command == 'prepare':
            reviewer.export(args.output, record)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        # Do not echo arbitrary metadata/URLs or response bodies on failure.
        print('BLOCKED: provider handoff/readback rejected ('+type(exc).__name__+')', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
