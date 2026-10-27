#!/usr/bin/env python3
"""Offline exact-artifact pilot approval. Never publishes or calls a model.

No byte normalization/exclusions. Non-pilot output is frozen by an external
baseline; at most seven explicitly enrolled surfaces may differ. A release
signature binds all bytes, source inputs, context approvals and action claims.
"""
import argparse
from collections import defaultdict
from contextlib import contextmanager
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import zipfile
import subprocess
import canon as canon_module

import reporting_trust as trust
import reporting_publication as publication
import reporting_structured as s
import reporting_eligibility as eligibility

VERSION = 'beatthescam-pilot-release-v4'
MAX_FILES = 5000
MAX_BYTES = 128 * 1024 * 1024
INPUT_DIRS = ('scripts', 'content', 'templates', 'assets', 'static', 'netlify', '.github/workflows')
INPUT_FILES = ('netlify.toml', 'requirements-reporting.txt', 'requirements-reporting.lock', 'requirements-claude.txt', 'package.json', 'package-lock.json', '.python-version', '.nvmrc')


def sha(data): return hashlib.sha256(data).hexdigest()


def path_name(value):
    if (not isinstance(value, str) or len(value) > 300 or not value
            or any(x in ('', '.', '..') or x.casefold() == '.git'
                   or not re.fullmatch(r'[A-Za-z0-9_.-]+', x) for x in value.split('/'))):
        raise ValueError('unsafe/noncanonical artifact path')
    return value


def check_names(names):
    if len(names) > MAX_FILES or len({n.casefold() for n in names}) != len(names):
        raise ValueError('too many or colliding artifact paths')
    for name in names: path_name(name)


def tree(root, *, source=False):
    root = Path(root).absolute()
    if root.resolve() != root or not root.is_dir():
        raise ValueError('artifact root must be a real absolute directory')
    result = {}; total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        # Python cache is never a source input; no exclusion exists for output.
        if source: dirs[:] = [d for d in dirs if d != '__pycache__']
        for d in dirs:
            if (Path(directory) / d).is_symlink(): raise ValueError('symlink directory rejected')
        for f in files:
            p = Path(directory) / f; name = path_name(p.relative_to(root).as_posix())
            data = trust.read_file(p, limit=MAX_BYTES)
            total += len(data)
            if total > MAX_BYTES: raise ValueError('artifact exceeds byte bound')
            result[name] = data
    check_names(result)
    return dict(sorted(result.items()))


def hashes(files): return {p: sha(b) for p,b in sorted(files.items())}


def inputs(root):
    root = Path(root).resolve(); result = {}
    for name in INPUT_DIRS:
        if (root / name).exists():
            result.update({name+'/'+p: h for p,h in hashes(tree(root/name, source=True)).items()})
    for name in INPUT_FILES:
        if (root/name).exists(): result[name] = sha(trust.read_file(root/name))
    return trust.digest(result)


def baseline(cfg):
    value = trust.read_json(trust.store()/'baseline.json', protected=True)
    if not isinstance(value, dict) or trust.digest(value) != cfg['baseline_sha256']:
        raise ValueError('external baseline hash mismatch')
    check_names(value)
    if any(not isinstance(v,str) or not re.fullmatch(r'[a-f0-9]{64}',v) for v in value.values()):
        raise ValueError('invalid baseline digest')
    return value


def protected_output(files, base, selected_paths):
    """One exact output-set rule for the manifest and critical inventory tests."""
    check_names(files)
    check_names(base)
    check_names(list(selected_paths))
    actual = hashes(files)
    if set(actual) != set(base) | set(selected_paths):
        raise ValueError('missing or unexpected protected output')
    if any(actual[p] != h for p,h in base.items() if p not in selected_paths):
        raise ValueError('non-pilot output differs from baseline')
    return actual


def load_pages(root, expected):
    posts = trust.read_json(root/'content/posts.json')
    hubs = trust.read_json(root/'content/category-hubs.json')
    pages = {}; structured = set()
    for identity, page in [('guide:'+p['slug'], p) for p in posts] + [('hub:'+k,v) for k,v in hubs.items()]:
        if identity in pages: raise ValueError('duplicate page identity')
        if not re.fullmatch(r'(guide|hub):[a-z0-9]+(?:-[a-z0-9]+)*', identity): raise ValueError('invalid page identity')
        pages[identity] = page
        if 'reporting_routes' in page:
            if page.get('consolidated_into'): raise ValueError('consolidated pilot page')
            structured.add(identity)
        elif not publication.legacy_unchanged(page, identity):
            raise ValueError('non-pilot content differs from frozen legacy source')
    if structured != set(expected): raise ValueError('unexpected/missing structured pilot surface')
    return {i: pages[i] for i in sorted(expected)}, posts, hubs


def output_path(identity):
    kind, slug = identity.split(':')
    return ('guides/' if kind == 'guide' else 'categories/')+slug+'/index.html'


def render_selected(root, selected, posts, hubs, canon, files):
    """Same context/projections as build(); assets are exact bundled bytes."""
    import build as b
    import corpus
    import copy
    normalized = copy.deepcopy(posts)
    for p in normalized: p['category'] = b.normalize_category(p['category'])
    all_posts = b.disambiguate_slugs(normalized)
    public, _ = corpus.partition(all_posts, b.ARTICLE_REDIRECTS)
    b.EFFECTIVE_REDIRECTS = corpus.redirect_map(all_posts, b.ARTICLE_REDIRECTS)
    categories = defaultdict(list)
    for p in public: categories[p['category']].append(p)
    site = trust.read_json(root/'content/site.json')
    for key, filename in (('_asset_ver_css','styles.css'),('_asset_ver_js','app.js')):
        site[key] = hashlib.md5(files['assets/'+filename]).hexdigest()[:10]
    b._FOOTER_CATS_HTML = '\n'.join(f'<li><a href="/categories/{b.slugify(cat)}/">{html.escape(b.category_label(cat))}</a></li>'
        for cat in sorted(categories, key=lambda c: len(categories[c]), reverse=True))
    affiliates = b.load_affiliates(root)
    links = b.build_internal_link_map(public); titles = {p['slug']:p['title'] for p in public}
    result = {}
    for identity,page in selected.items():
        if identity.startswith('guide:'):
            rendered = b.render_post(site, page, public, affiliates=affiliates, sources=canon, link_map=links, slug_titles=titles)
        else:
            slug = identity.split(':')[1]
            rendered = b.render_category_page(site, slug, categories.get(slug,[]), all_categories=categories,
                hub=page, reporting_sources=canon)
        result[output_path(identity)] = rendered.encode()
    return result


def candidate(root, files, *, source_revision=None):
    """Recompute, never trust a submitted manifest's claims or path list."""
    import reporting_runtime
    reporting_runtime.require()
    root = Path(root).resolve(); cfg = trust.config(); ids = cfg['pilot_page_ids']
    if not 1 <= len(ids) <= 7: raise ValueError('pilot must enroll one to seven exact surfaces')
    check_names(files)
    before = inputs(root)
    base = baseline(cfg)
    selected, posts, hubs = load_pages(root, ids)
    import canon as canon_module
    sources = canon_module.load_canon(root/'content/sources.json')
    selected_paths = {output_path(i) for i in selected}
    actual = protected_output(files, base, selected_paths)
    pages = []
    for identity,page in selected.items():
        trust.require_page_scope(cfg, identity, 'release')
        catalog = eligibility.require_actions(sources, page.get('reporting_routes'))
        packet = trust.read_json(trust.store()/'packets'/(sha(identity.encode())+'.json'), protected=True)
        publication.review(page, sources, packet, page_id=identity)
        path = output_path(identity)
        pages.append({'page_id':identity, 'path':path, 'source_sha256':s.digest(page),
            'route_ids':sorted(page['reporting_routes']),
            'action_plan_sha256':s.action_plan_sha256(catalog, page['reporting_routes']),
            'context_packet_sha256':trust.digest(packet), 'html_sha256':actual[path]})
    rendered = render_selected(root, selected, posts, hubs, sources, files)
    if set(rendered) != selected_paths or any(rendered[p] != files[p] for p in selected_paths):
        raise ValueError('artifact differs from authenticated deterministic page render')
    if inputs(root) != before or trust.config() != cfg:
        raise ValueError('source/trust changed during verification')
    from reporting_actions import VERSION as ACTION_VERSION
    import reporting_revision
    revision = (reporting_revision.materialized(root, files, source_revision)
                if source_revision is not None else None)
    return {'version':'pilot-output/v4', 'source_revision':revision, 'schema_version':ACTION_VERSION,
        'contract_model_sha256':s.contract_model_sha256(), 'policy_sha256':trust.digest(cfg), 'inputs_sha256':before,
        'canon_sha256':s.digest(sources), 'dependencies':publication.dependencies(), 'pages':pages, 'files':actual}


def verify_release(packet, root, files, *, production=True, source_revision=None):
    if production and trust.environment() != 'production': raise ValueError('test authority cannot authorize production deployment')
    if not isinstance(packet,dict) or set(packet) != {'body','signature'}: raise ValueError('missing release signature')
    b = packet['body']
    if (not isinstance(b,dict) or set(b) != {'version','environment','site','reviewer','decision_id','issued_at','expires_at','manifest'}
            or b['version'] != VERSION): raise ValueError('wrong release schema')
    trust.verify(b, packet['signature'], 'release', VERSION)
    import reporting_revision
    reporting_revision.validate(source_revision)
    if b['manifest'].get('source_revision') != source_revision:
        raise ValueError('approval source revision mismatch')
    current = candidate(root, files, source_revision=source_revision)
    if b['manifest'] != current: raise ValueError('approved manifest differs from current candidate/output')
    return current


def zip_bytes(files):
    check_names(files); output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for path,data in sorted(files.items()):
            info = zipfile.ZipInfo(path, date_time=(1980,1,1,0,0,0)); info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info,data)
    return output.getvalue()


def zip_files(data):
    if len(data) > MAX_BYTES: raise ValueError('bundle too large')
    files = {}; total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            name = path_name(info.filename)
            if (name in files or info.compress_type != zipfile.ZIP_STORED or info.flag_bits & 1
                    or stat.S_IFMT(info.external_attr >> 16) != stat.S_IFREG):
                raise ValueError('ambiguous/compressed/nonregular archive entry')
            total += info.file_size
            if total > MAX_BYTES or len(files) >= MAX_FILES: raise ValueError('archive bound exceeded')
            files[name] = archive.read(info)
    check_names(files)
    # A unique deterministic container, not merely equivalent extracted files.
    if zip_bytes(files) != data: raise ValueError('noncanonical archive encoding')
    return files


def verify_bundle(packet, root, data, *, production=True, source_revision=None):
    manifest = verify_release(packet, root, zip_files(data), production=production,
                              source_revision=source_revision)
    return {'deployment_eligible':production, 'environment':trust.environment(),
            'archive_sha256':sha(data), 'manifest_sha256':trust.digest(manifest),
            'source_revision': manifest['source_revision'],
            'pages':[p['page_id'] for p in manifest['pages']]}


def verify_test_bundle(packet, root, data, *, source_revision=None):
    """Non-publishing rehearsal using the real independent contract predicate."""
    if trust.environment() != 'test': raise ValueError('test verifier requires TEST authority')
    sources = canon_module.load_canon(Path(root)/'content/sources.json')
    for page in packet['body']['manifest']['pages']:
        eligibility.require_contract_actions(sources, page['route_ids'])
    return verify_bundle(packet, root, data, production=False, source_revision=source_revision)


@contextmanager
def public_review_store(root):
    """Snapshot the candidate's PUBLIC mirror; consumers must authenticate it."""
    if not (root/'deployment/review-store').is_dir(): raise ValueError('production public review material is not provisioned')
    material = tree(root/'deployment/review-store')
    for name in material:
        if name not in ('trust.json','baseline.json','revoked.json','release.json') and not re.fullmatch(r'(contracts|packets)/[a-f0-9]{64}\.json',name):
            raise ValueError('unexpected verification material')
    # Preserve the exact public bytes, then validate trust against the pin that
    # is configured outside Git. No repository configuration supplies that pin.
    with tempfile.TemporaryDirectory(prefix='bts-production-verify-') as tmp:
        destination = Path(tmp).resolve()
        for name,data in material.items():
            target = destination/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
        old = os.environ.get('BTS_REVIEW_STORE')
        os.environ['BTS_REVIEW_STORE'] = str(destination)
        try:
            yield destination
        finally:
            if old is None: os.environ.pop('BTS_REVIEW_STORE',None)
            else: os.environ['BTS_REVIEW_STORE'] = old


def netlify_verify(root):
    """Verify public material against the external pin; never sign or deploy."""
    import reporting_runtime
    reporting_runtime.require()
    if trust.environment() != 'production': raise ValueError('Netlify requires production trust')
    with public_review_store(root) as destination:
        trust.config()
        import reporting_revision
        revision = reporting_revision.worktree(root, os.environ.get('COMMIT_REF'))
        packet_path = Path(os.environ.get('BTS_RELEASE_PACKET', ''))
        if (not packet_path.is_absolute() or packet_path.resolve() != packet_path
                or Path(root).resolve() in packet_path.parents):
            raise ValueError('explicit detached release packet outside candidate required')
        packet = trust.read_json(packet_path, protected=True)
        files = tree(root/'dist')
        result = verify_bundle(packet,root,zip_bytes(files),source_revision=revision)
        if hashes(tree(root/'dist')) != hashes(files): raise ValueError('dist changed during verification')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inventory','status','candidate','issue-reviewed','bundle','verify-bundle','verify-deploy','test-verify-bundle','netlify-verify'))
    parser.add_argument('--artifact', type=Path, default=publication.ROOT/'dist')
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--private-key', type=Path)
    parser.add_argument('--reviewer')
    parser.add_argument('--human-reviewed', action='store_true')
    parser.add_argument('--candidate-sha')
    args = parser.parse_args(); root = publication.ROOT
    try:
        if args.command == 'status':
            sources = canon_module.load_canon()
            records = trust.read_json(root/'content/posts.json')
            hubs = trust.read_json(root/'content/category-hubs.json')
            surfaces = [{'page_id':'guide:'+x['slug'],'route_ids':x['reporting_routes']} for x in records if 'reporting_routes' in x]
            surfaces += [{'page_id':'hub:'+k,'route_ids':x['reporting_routes']} for k,x in hubs.items() if 'reporting_routes' in x]
            result = {'contracts':eligibility.inventory(sources),'surfaces':surfaces,'deployment_eligible':False}
            try: result.update(netlify_verify(root))
            except (ValueError,OSError,TypeError,KeyError,canon_module.CanonError) as exc: result['hold_reason']=str(exc)
            print(json.dumps(result,indent=2)); return int(not result['deployment_eligible'])
        if args.command == 'netlify-verify':
            print(json.dumps(netlify_verify(root),indent=2)); return 0
        if args.command == 'inventory':
            import canon
            print(json.dumps(eligibility.inventory(canon.load_canon()),indent=2)); return 0
        if args.command == 'candidate':
            import reporting_revision
            revision = reporting_revision.worktree(root, args.candidate_sha)
            print(json.dumps(candidate(root,tree(args.artifact),source_revision=revision),indent=2)); return 0
        if args.command == 'issue-reviewed':
            raise ValueError('use reporting_reviewer.py prepare/sign with explicit role, environment, candidate, artifact and expected receipt')
        packet = trust.read_json(args.packet) if args.packet else trust.read_json(trust.store()/'release.json',protected=True)
        import reporting_revision
        revision = reporting_revision.worktree(root, args.candidate_sha)
        if args.command in ('verify-bundle','test-verify-bundle'):
            if args.bundle is None: raise ValueError('--bundle required')
            data = trust.read_file(args.bundle,limit=MAX_BYTES)
            result = (verify_test_bundle(packet,root,data,source_revision=revision) if args.command=='test-verify-bundle'
                      else verify_bundle(packet,root,data,source_revision=revision))
        else:
            files = tree(args.artifact); verify_release(packet,root,files,source_revision=revision)
            data = zip_bytes(files)
            result = verify_bundle(packet,root,data,source_revision=revision)
            if args.command == 'bundle':
                if args.bundle is None or root == args.bundle.absolute() or root in args.bundle.absolute().parents:
                    raise ValueError('--bundle must be a new file outside the repository')
                with args.bundle.open('xb') as handle: handle.write(data)
            # Guard against an artifact change during expensive rendering. A
            # later host compromise remains outside this process trust boundary.
            if hashes(tree(args.artifact)) != hashes(files): raise ValueError('artifact changed during verification')
        print(json.dumps(result,indent=2)); return 0
    except (ValueError,OSError,TypeError,KeyError,zipfile.BadZipFile,canon_module.CanonError,subprocess.SubprocessError) as exc:
        print('BLOCKED: '+str(exc),file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
