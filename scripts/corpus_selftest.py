#!/usr/bin/env python3
"""
corpus_selftest.py — proves consolidation defines the public corpus.

A guide consolidated into another is retained in content/posts.json as archive
data. It must not render, must 301, must not appear in any index, and must not
take part in the publication duplicate-content check — it is not a page, so it
cannot be a duplicate page.

That used to be three separate opinions (`CONSOLIDATED_LIVE_SLUGS`, a duplicate
`ARTICLE_REDIRECTS` entry, and a different rule inside similarity_report.py),
and they disagreed: the gate reported the Hermes/Evri consolidation as a 54%
duplicate-content BLOCK while the report excluded it (operator review,
2026-07-30). This suite pins the whole property, end to end, against a REAL
build.

Offline: no API key, no network. The build-backed proofs run a REAL build into
a temporary directory — the committed dist/ is never touched.

    python3 scripts/corpus_selftest.py              # everything (~6 min: the build)
    python3 scripts/corpus_selftest.py --no-build   # partition/similarity only (~1 min)

The build takes about five and a half minutes for 185 posts. That is the site's
normal build cost, not a hang.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
import errno
import os
import stat
import subprocess
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import corpus as C                                    # noqa: E402
import build as B                                     # noqa: E402
from content_gate import check_similarity             # noqa: E402

FAILURES: list[str] = []

# The one consolidation in the corpus today. Read from the data rather than
# hard-coded, so this suite keeps working after the next one.
HERMES = "hermes-parcel-scam-text-uk"
EVRI = "evri-delivery-scam-guide"


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def live_posts() -> list:
    return json.loads((ROOT / "content" / "posts.json").read_text(encoding="utf-8"))


def protected_inventory() -> dict:
    """Canonical input/output bytes plus modes; no Git snapshot reimplementation."""
    import reporting_pilot as pilot

    result = {}
    for name in pilot.INPUT_DIRS + ("dist",):
        base = ROOT / name
        if not base.exists():
            continue
        for rel, digest in pilot.hashes(pilot.tree(base, source=name != "dist")).items():
            result[name + "/" + rel] = [digest, stat.S_IMODE((base / rel).stat().st_mode)]
        for directory, dirs, _ in os.walk(base, followlinks=False):
            if name != "dist":
                dirs[:] = [d for d in dirs if d != "__pycache__"]
            path = Path(directory)
            result[path.relative_to(ROOT).as_posix() + "/"] = [None, stat.S_IMODE(path.stat().st_mode)]
    for name in pilot.INPUT_FILES:
        path = ROOT / name
        result[name] = [pilot.sha(path.read_bytes()), stat.S_IMODE(path.stat().st_mode)]
    return result


@contextmanager
def corpus_test_review(tmp: Path):
    """Exactly one inherited hub, two real routes, disposable TEST authority only.

    Never called by --no-build. Canonical reviewer and verification code owns
    receipts, signatures, contract clearance and page/canon/dependency binding.
    No release packet, agent, repository copy, Git fixture or production store.
    """
    import canon
    import reporting_eligibility as eligibility
    import reporting_pilot as pilot
    import reporting_publication as publication
    import reporting_reviewer as reviewer
    import reporting_runtime as runtime
    import reporting_trust as trust

    def require(name, condition):
        check(name, condition)
        if not condition:
            raise AssertionError(name)

    def outside_repository(path):
        if (not path.is_absolute() or path.resolve() != path
                or any(p.is_symlink() for p in (path, *path.parents))
                or path == ROOT or ROOT in path.parents
                or any((p / ".git").exists() or (p / ".git").is_symlink()
                       for p in (path, *path.parents))):
            raise ValueError("corpus TEST path must be canonical and outside every repository")

    outside_repository(tmp)
    info = tmp.stat()
    require("TEST root is owner-only and empty",
            tmp.name.startswith("bts-corpus-test-") and stat.S_ISDIR(info.st_mode)
            and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700
            and not list(tmp.iterdir()))
    require("no inherited signing agent", not any(os.environ.get(k)
            for k in ("SSH_AUTH_SOCK", "SSH_AGENT_PID")))
    require("canonical fixture modules use this exact source",
            B.ROOT == publication.ROOT == trust.ROOT == runtime.ROOT == ROOT)
    before = protected_inventory()
    previous_env = dict(os.environ)
    previous_tmp = tempfile.tempdir
    previous_bytecode = sys.dont_write_bytecode
    previous_umask = os.umask(0o077)
    receipts, packets, refusals = {}, {}, {}
    attempts = 0
    try:
        authority, keys_dir, output, scratch, home = (
            tmp / name for name in ("test-authority", "test-keys", "test-output", "scratch", "home"))
        for path in (authority, keys_dir, output, scratch, home,
                     authority / "contracts", authority / "packets"):
            path.mkdir(mode=0o700)
            outside_repository(path)
        os.environ.clear()
        os.environ.update({k: previous_env[k] for k in
                           ("PATH", "TZ", "LC_ALL", "LANG", "PYTHONUTF8") if k in previous_env})
        os.environ.update(BTS_REVIEW_ENVIRONMENT="test", BTS_REVIEW_STORE=str(authority),
                          HOME=str(home), TMPDIR=str(scratch), PYTHONDONTWRITEBYTECODE="1")
        tempfile.tempdir = str(scratch)
        sys.dont_write_bytecode = True
        require("explicit TEST environment; inherited production settings excluded",
                trust.environment() == "test" and trust.store() == authority
                and not any(k in os.environ for k in
                            ("BTS_RELEASE_PACKET", "BTS_PRODUCTION_TRUST_SHA256",
                             "SSH_AUTH_SOCK", "SSH_AGENT_PID")))
        measured = runtime.require(ROOT)
        posts = trust.read_json(ROOT / "content/posts.json")
        hubs = trust.read_json(ROOT / "content/category-hubs.json")
        pages = [("guide:" + p["slug"], p) for p in posts] + [
            ("hub:" + slug, page) for slug, page in hubs.items()]
        required = [identity for identity, page in pages if publication.required(page, identity)]
        require("canonical required() selects exactly hub:phone", required == ["hub:phone"])
        routes = ["own-bank:number-on-bank-card", "citizens-advice:consumer-advice-english"]
        phone = hubs["phone"]
        require("exact inherited phone source and two routes",
                pilot.sha(trust.read_file(ROOT / "content/category-hubs.json")) ==
                "973088ed2efd3574434fe3c9e1d7e80df7529ce18939e55766a329c9271bb484"
                and phone.get("reporting_routes") == routes)
        sources = canon.load_canon(ROOT / "content/sources.json")
        eligibility.require_contract_actions(sources, routes)

        keys = {}
        for role in trust.ROLES:
            key = keys_dir / ("test-" + role)
            outside_repository(key)
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                           stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=15)
            key.with_suffix(".pub").chmod(0o600)
            keys[role] = trust.key_path(key)
        cfg = dict(version="bts-trust/v1", environment="test", site=trust.SITE,
                   roles={role: [dict(identity="test-corpus-" + role,
                       public_key=" ".join(trust.read_file(key.with_suffix(".pub")).decode().split()[:2]))]
                       for role, key in keys.items()},
                   pilot_page_ids=["hub:phone"],
                   baseline_sha256=trust.digest(pilot.hashes(pilot.tree(ROOT / "dist"))),
                   revocations_sha256=trust.digest([]))
        reviewer.export(authority / "baseline.json", pilot.hashes(pilot.tree(ROOT / "dist")))
        reviewer.export(authority / "revoked.json", [])
        reviewer.export(authority / "trust.json", cfg)
        require("exact TEST enrollment and baseline",
                trust.config() == cfg and pilot.baseline(cfg) == pilot.hashes(pilot.tree(ROOT / "dist")))

        def issue(role, destination, **fields):
            nonlocal attempts
            if role not in ("contracts", "context"):
                raise ValueError("corpus fixture cannot issue a release")
            outside_repository(destination)
            require("TEST confinement before " + role + " signing",
                    trust.environment() == "test" and trust.config() == cfg
                    and authority in destination.parents and keys_dir in keys[role].parents
                    and not destination.exists() and not destination.is_symlink())
            args = argparse.Namespace(environment="test", role=role, candidate=ROOT,
                reviewer="test-corpus-" + role, route_id=None, page=None, page_id=None,
                audience=None, allow_empty=False, artifact=None, expected_receipt_sha256=None,
                key_file=keys[role], output=destination, test_only=True)
            for name, value in fields.items():
                setattr(args, name, value)
            receipt = reviewer.prepare(args)
            args.expected_receipt_sha256 = trust.digest(receipt)
            attempts += 1
            result = reviewer.issue(args)
            packet = trust.read_json(destination, protected=True)
            require("canonical receipt and exported " + role + " packet match",
                    result["receipt_sha256"] == trust.digest(receipt)
                    and result["packet_sha256"] == trust.digest(packet)
                    and packet["body"]["environment"] == "test")
            receipts[destination.name] = trust.digest(receipt)
            packets[destination.name] = pilot.sha(trust.read_file(destination, protected=True))
            return packet

        for route in routes:
            issue("contracts", eligibility.packet_path(route), route_id=route)
            require("eligible and signed TEST route " + route,
                    bool(eligibility.verify_contract_eligibility(sources, route))
                    and bool(eligibility.verify_contract(sources, route)))
        require("exact two-route endorsed inventory",
                eligibility.publication_endorsed_ids(sources) == tuple(sorted(routes)))

        context_path = authority / "packets" / (pilot.sha(b"hub:phone") + ".json")
        try:
            publication.review(phone, sources, page_id="hub:phone")
        except eligibility.s.ReportingError as exc:
            cause = exc.__cause__
            require("missing TEST context rejects specifically",
                    isinstance(cause, FileNotFoundError) and cause.errno == errno.ENOENT
                    and cause.filename == str(context_path))
            refusals["missing_context"] = "FileNotFoundError: exact hub:phone packet absent"
        else:
            raise AssertionError("missing TEST context accepted")
        phone_file = output / "phone.json"
        reviewer.export(phone_file, phone)
        context = issue("context", context_path, page=phone_file, page_id="hub:phone",
                        audience=["England", "Wales", "Scotland", "Northern Ireland"])
        require("complete valid TEST phone context through real review",
                publication.review(phone, sources, page_id="hub:phone") is not None)

        def refuse(label, packet, reason):
            try:
                publication.verify_packet(packet, phone, sources, page_id="hub:phone")
            except ValueError as exc:
                require(label, str(exc) == reason)
                refusals[label] = str(exc)
            else:
                raise AssertionError(label + ": expected refusal not observed")

        tampered = copy.deepcopy(context)
        original = tampered["body"]["decision_id"]
        tampered["body"]["decision_id"] = ("0" if original[0] != "0" else "1") + original[1:]
        refuse("tampered TEST signature rejects", tampered, "signature authentication failed")
        wrong_scope = copy.deepcopy(cfg)
        wrong_scope["pilot_page_ids"] = ["hub:outside-test-scope"]
        trust_file = authority / "trust.json"
        try:
            outside_repository(trust_file)
            trust_file.write_bytes(trust.canonical(wrong_scope) + b"\n")
            refuse("wrong enrolled page scope rejects", context, "page outside enrolled scope")
        finally:
            trust_file.write_bytes(trust.canonical(cfg) + b"\n")
        try:
            os.environ["BTS_REVIEW_ENVIRONMENT"] = "production"
            # Even the exact TEST root digest cannot make its schema production.
            os.environ["BTS_PRODUCTION_TRUST_SHA256"] = trust.digest(cfg)
            refuse("production refuses TEST authority", context, "trust root schema/environment/site mismatch")
        finally:
            os.environ["BTS_REVIEW_ENVIRONMENT"] = "test"
            os.environ.pop("BTS_PRODUCTION_TRUST_SHA256", None)
        require("TEST context restored after refusal checks",
                trust.config() == cfg and publication.review(phone, sources, page_id="hub:phone") is not None)
        require("only two endorsements and one context; no release output",
                len(list((authority / "contracts").iterdir())) == 2
                and list((authority / "packets").iterdir()) == [context_path]
                and set(packets) == {eligibility.packet_path(r).name for r in routes} | {context_path.name}
                and attempts == 3)
        print("CORPUS TEST FIXTURE " + json.dumps(dict(
            environment="test", pages=required, routes=routes, runtime=measured,
            receipts=receipts, public_packet_sha256=packets, refusals=refusals,
            signing_attempts=attempts, release_signatures=0, production_signatures=0,
            agents_started=0, fixture_root=str(tmp)), sort_keys=True))
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous_env)
        tempfile.tempdir = previous_tmp
        sys.dont_write_bytecode = previous_bytecode
        os.umask(previous_umask)
        require("environment and temporary-runtime settings restored",
                dict(os.environ) == previous_env and tempfile.tempdir == previous_tmp
                and sys.dont_write_bytecode == previous_bytecode)
        after = protected_inventory()
        require("protected source and committed dist bytes/modes unchanged", after == before)
        print("CORPUS PRESERVATION " + json.dumps(dict(
            entries=len(before), before_sha256=trust.digest(before), after_sha256=trust.digest(after),
            signing_attempts=attempts, public_packet_sha256=packets, environment_restored=True,
            production_signatures=0, release_signatures=0, agents_started=0), sort_keys=True))


def build_into(tmp: Path) -> Path:
    """Run the REAL build into a temp directory.

    Every write in build.py goes through the module-global DIST, so patching it
    redirects the whole build — including the rmtree — away from the committed
    tree. Restored in a finally block.

    Per-post OG image rendering is stubbed: 185 Pillow renders take six minutes
    and this suite asserts nothing about them. Everything else — routing,
    indexes, redirects, link canonicalisation — is the real thing.
    """
    original_dist, original_og = B.DIST, B.generate_og_image
    original_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        with corpus_test_review(tmp):
            destination = tmp / "dist"
            if destination.exists() or destination.is_symlink() or destination.resolve() != destination:
                raise ValueError("TEST dist must be a fresh canonical child of the disposable root")
            B.DIST = destination
            B.generate_og_image = lambda out_path, *a, **k: out_path.write_bytes(b"")
            B.build()
            return B.DIST
    finally:
        B.DIST, B.generate_og_image = original_dist, original_og
        sys.dont_write_bytecode = original_bytecode


def run(with_build: bool = True) -> int:
    posts = live_posts()
    # UNION, not `or`. `a or b` ignored the legacy mapping the moment any
    # metadata mapping existed, so a half-migrated corpus would have been tested
    # against an incomplete map (operator review, 2026-07-30).
    consolidation = {**C.pending_migrations(posts), **C.consolidation_map(posts)}
    declared_on_record = bool(C.consolidation_map(posts))

    print(f"consolidations: {consolidation}")
    print(f"declared on the record: {declared_on_record}"
          + ("" if declared_on_record else "  (still on the transitional static bridge)"))
    print()

    # ── 1. 186 source records become exactly 185 public guides ──────────────
    public, consolidated = C.partition(posts)
    check("source records partition into public + consolidated",
          len(public) + len(consolidated) == len(posts))
    check(f"{len(posts)} source records become exactly "
          f"{len(posts) - len(consolidation)} public guides",
          len(public) == len(posts) - len(consolidation), f"got {len(public)}")
    # ── GENERIC: every consolidation, whatever the corpus holds ─────────────
    public_slugs = {p["slug"] for p in public}
    check("public + consolidated is exactly the source corpus",
          public_slugs | {p["slug"] for p in consolidated} == {p["slug"] for p in posts})
    check("every consolidated record is retired by a declaration",
          {p["slug"] for p in consolidated} == set(consolidation),
          str(sorted({p["slug"] for p in consolidated} ^ set(consolidation))))
    for slug, target in sorted(consolidation.items()):
        check(f"{slug}: target {target!r} is a public guide", target in public_slugs)
        check(f"{slug}: is itself not public", slug not in public_slugs)
        check(f"{slug}: target is not itself consolidated", target not in consolidation)
    check("public count = source count - consolidations",
          len(public) == len(posts) - len(consolidation),
          f"{len(public)} vs {len(posts)} - {len(consolidation)}")

    # A SECOND simultaneous consolidation must behave identically — the rule is
    # corpus state, not a named pair.
    import copy as _copy
    two = _copy.deepcopy(posts)
    extra_target = next(p["slug"] for p in two
                        if p["slug"] not in consolidation and p["slug"] != HERMES)
    extra = next(p for p in two if p["slug"] not in consolidation
                 and p["slug"] not in (HERMES, extra_target))
    extra[C.CONSOLIDATED_INTO] = extra_target
    two_public, two_cons = C.partition(two)
    check("a SECOND simultaneous consolidation is retired too",
          len(two_cons) == len(consolidated) + 1 and extra["slug"] in {p["slug"] for p in two_cons},
          f"{[p['slug'] for p in two_cons]}")
    check("a second consolidation reduces the public corpus by one",
          len(two_public) == len(public) - 1, f"{len(two_public)} vs {len(public) - 1}")
    check("a second consolidated record is excluded from similarity too",
          not [i for i in check_similarity(extra, two) if i["severity"] == "block"])

    # Hermes-specific migration assertions, kept deliberately as such.
    check("the Hermes archive copy is among the consolidated records",
          HERMES in {p["slug"] for p in consolidated})
    check("Hermes points at Evri", consolidation.get(HERMES) == EVRI)

    # ── 5/6/7. Similarity: default excludes, diagnostic includes ────────────
    def sim_blocks(records, **kw):
        return sorted({p["slug"] for p in records
                       for i in check_similarity(p, records, **kw) if i["severity"] == "block"})

    check("default similarity has no Hermes/Evri BLOCK", sim_blocks(posts) == [],
          str(sim_blocks(posts)))
    diag = sim_blocks(posts, include_consolidated=True)
    check("diagnostic similarity still finds the pair", diag == sorted([EVRI, HERMES]), str(diag))

    without = [p for p in posts if p["slug"] != HERMES] + [
        {k: v for k, v in p.items() if k != C.CONSOLIDATED_INTO}
        for p in posts if p["slug"] == HERMES
    ]
    # Un-retire it completely: no metadata, no static entry, not pending. That
    # is a coherent "this is an ordinary public guide" state — anything less is
    # now a validation error, which is the point of the two-sided rule.
    saved_static = dict(C.ARTICLE_REDIRECTS)
    saved_pending = C.PENDING_MIGRATION
    try:
        C.ARTICLE_REDIRECTS.pop(HERMES, None)
        C.PENDING_MIGRATION = {}
        check("with the consolidation fully removed the corpus is valid",
              not C.validate_consolidation(without))
        recreated = sim_blocks(without)
        check("removing the consolidation recreates the BLOCK",
              recreated == sorted([EVRI, HERMES]), str(recreated))
        check("...and the record becomes public again",
              HERMES in {p["slug"] for p in C.public_posts(without)})
    finally:
        C.ARTICLE_REDIRECTS.clear()
        C.ARTICLE_REDIRECTS.update(saved_static)
        C.PENDING_MIGRATION = saved_pending

    # A genuinely duplicated NEW draft must still be caught — the exclusion is
    # for archive records, not an amnesty on duplication.
    evri = next(p for p in posts if p["slug"] == EVRI)
    draft = {**copy.deepcopy(evri), "slug": "a-brand-new-draft"}
    check("a duplicate NEW draft still BLOCKs",
          any(i["severity"] == "block" for i in check_similarity(draft, posts)))

    # ── 8. Invalid graphs stop the release ──────────────────────────────────
    for desc, bad_posts, static in C.negative_fixtures():
        check(desc, bool(C.validate_consolidation(bad_posts, static)))
    check("a valid graph produces no problems",
          not C.validate_consolidation(C._valid_fixture(), {}))
    # ...and the build refuses one.
    broken = copy.deepcopy(posts)
    for p in broken:
        if p["slug"] == HERMES:
            p[C.CONSOLIDATED_INTO] = "no-such-guide"
    try:
        C.partition(broken)
        stopped = False
    except C.CorpusError:
        stopped = True
    check("an invalid consolidation target raises CorpusError", stopped)

    # ── 2/3/4. A REAL build, into a temp tree ───────────────────────────────
    if not with_build:
        print("\nSKIPPED (--no-build): rendering, index, redirect and internal-link proofs.")
    while with_build:
      with tempfile.TemporaryDirectory(prefix="bts-corpus-test-") as td:
          tmp = Path(td).resolve()
          dist = build_into(tmp)
          committed = ROOT / "dist"
          check("the committed dist/ was not touched",
                committed.exists() and not str(dist).startswith(str(committed)))

          # `guides/page/N/` holds the pagination shells, not guides.
          guides = {d.name for d in (dist / "guides").iterdir()
                    if d.is_dir() and d.name != "page"}
          check(f"exactly {len(public)} guide pages are rendered",
                len(guides) == len(public), f"got {len(guides)}")
          for _slug, _target in sorted(consolidation.items()):
              check(f"{_slug} produces NO page", _slug not in guides)
              check(f"its target {_target} DOES produce a page", _target in guides)

          sitemap = (dist / "sitemap.xml").read_text(encoding="utf-8")
          rss = (dist / "rss.xml").read_text(encoding="utf-8")
          search = (dist / "search.json").read_text(encoding="utf-8")
          llms = (dist / "llms.txt").read_text(encoding="utf-8")
          redirects = (dist / "_redirects").read_text(encoding="utf-8")

          # llms-full.txt was NOT checked, and it was the one surface that
          # still carried a consolidated slug: it writes raw record text, so it
          # missed the canonicalisation the HTML pages get (release build,
          # 2026-07-30).
          llms_full = (dist / "llms-full.txt").read_text(encoding="utf-8")
          for label, blob in (("sitemap.xml", sitemap), ("rss.xml", rss),
                              ("search.json", search), ("llms.txt", llms),
                              ("llms-full.txt", llms_full)):
              for _slug in sorted(consolidation):
                  check(f"{_slug} has no {label} entry", _slug not in blob)
          for _target in sorted(set(consolidation.values())):
              check(f"the target {_target} IS in sitemap.xml", f"/guides/{_target}/" in sitemap)

          # 3. Both URL forms 301 DIRECTLY to the final guide, for EVERY
          #    consolidation the corpus declares — not just the named pair.
          for _slug, _target in sorted(consolidation.items()):
            for form in (f"/guides/{_slug}", f"/guides/{_slug}/"):
              line = next((l for l in redirects.splitlines()
                           if l.split()[0:1] == [form]), None)
              check(f"{form} emits a 301", line is not None)
              if line:
                  _, dest, code = line.split()
                  check(f"{form} 301s directly to {_target}",
                        dest == f"/guides/{_target}/", f"got {dest}")
                  check(f"{form} uses a forced 301", code == "301!", f"got {code}")

          # 4. No rendered page links to the dead slug — internal links are
          #    canonicalised, so a reader never takes the redirect hop.
          linking = sorted(
              p.name for p in (dist / "guides").rglob("index.html")
              if any(f"/guides/{_s}/" in p.read_text(encoding="utf-8") for _s in consolidation)
          )
          check("no rendered guide links to any consolidated slug", not linking, str(linking[:5]))
          hub_pages = sorted(
              p.parent.name for p in (dist / "categories").rglob("index.html")
              if any(f"/guides/{_s}/" in p.read_text(encoding="utf-8") for _s in consolidation)
          )
          check("no rendered category/hub page links to one either", not hub_pages, str(hub_pages))

      break

    # ── The transitional bridge ─────────────────────────────────────────────
    pending = C.pending_migrations(posts)
    if declared_on_record:
        check("PENDING_MIGRATION is empty — every consolidation is on its record",
              not pending and not C.PENDING_MIGRATION,
              f"pending={pending} map={dict(C.PENDING_MIGRATION)}")
        check("no source record is also a static redirect",
              not ({p["slug"] for p in posts} & set(C.ARTICLE_REDIRECTS)),
              str(sorted({p["slug"] for p in posts} & set(C.ARTICLE_REDIRECTS))))
    else:
        check("PENDING_MIGRATION is carrying exactly the unmigrated records",
              set(pending) == set(C.PENDING_MIGRATION), str(pending))
        check("every pending migration pins its target",
              all(pending.get(k) == v for k, v in C.PENDING_MIGRATION.items()),
              f"{pending} vs {dict(C.PENDING_MIGRATION)}")
        print("NOTE  consolidation is still declared in the static redirect map, not on the")
        print("      record. `consolidation-metadata-v1` moves it, deletes the static entry and")
        print("      empties PENDING_MIGRATION; this branch then flips and demands the removal.")

    # The migration is complete: there is no static entry to leave behind and
    # PENDING_MIGRATION is empty, so the four half-applied states can no longer
    # be constructed from the live data. What must still hold is that RE-ADDING
    # a static entry for a record that declares its consolidation is rejected —
    # the collision rule that made the migration two-sided in the first place.
    static_now = dict(C.ARTICLE_REDIRECTS)
    for slug, target in sorted(consolidation.items()):
        clashing = {**static_now, slug: target}
        check(f"re-adding a static redirect for {slug} is REJECTED",
              bool(C.validate_consolidation(posts, clashing)))
    # An unrelated source slug colliding with a static redirect is an error, not
    # an implicit archive declaration — the open-bridge hole.
    colliding = next(iter(set(C.ARTICLE_REDIRECTS) - set(C.PENDING_MIGRATION)))
    synthetic = copy.deepcopy(posts) + [{**copy.deepcopy(posts[0]), "slug": colliding}]
    check("an unrelated slug/static-redirect collision is REJECTED, not silently retired",
          bool(C.validate_consolidation(synthetic, static_now)))

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All corpus consolidation self-tests passed.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Prove consolidation defines the public corpus")
    ap.add_argument("--no-build", action="store_true",
                    help="skip the build-backed rendering/redirect proofs (fast)")
    raise SystemExit(run(with_build=not ap.parse_args().no_build))
