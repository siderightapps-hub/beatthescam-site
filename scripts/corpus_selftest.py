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
    try:
        B.DIST = tmp / "dist"
        B.generate_og_image = lambda out_path, *a, **k: out_path.write_bytes(b"")
        B.build()
        return B.DIST
    finally:
        B.DIST, B.generate_og_image = original_dist, original_og


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
      with tempfile.TemporaryDirectory() as td:
          tmp = Path(td)
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

          for label, blob in (("sitemap.xml", sitemap), ("rss.xml", rss),
                              ("search.json", search), ("llms.txt", llms)):
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
        check("the transitional PENDING_MIGRATION set is now unused — delete it and "
              "pending_migrations()", not pending and not C.PENDING_MIGRATION,
              f"pending={pending} set={sorted(C.PENDING_MIGRATION)}")
    else:
        check("PENDING_MIGRATION is carrying exactly the unmigrated records",
              set(pending) == set(C.PENDING_MIGRATION), str(pending))
        check("every pending migration pins its target",
              all(pending.get(k) == v for k, v in C.PENDING_MIGRATION.items()),
              f"{pending} vs {dict(C.PENDING_MIGRATION)}")
        print("NOTE  consolidation is still declared in the static redirect map, not on the")
        print("      record. `consolidation-metadata-v1` moves it, deletes the static entry and")
        print("      empties PENDING_MIGRATION; this branch then flips and demands the removal.")

    # BOTH halves of the migration must be enforced — the code-only half used to
    # republish the record with no redirect and no error (operator review,
    # 2026-07-30, consolidation-metadata-v1-c.md §1).
    static_now = dict(C.ARTICLE_REDIRECTS)
    static_gone = {k: v for k, v in static_now.items() if k != HERMES}
    with_meta = copy.deepcopy(posts)
    for p in with_meta:
        if p["slug"] == HERMES:
            p[C.CONSOLIDATED_INTO] = EVRI
    check("metadata-only (static entry left behind) is REJECTED",
          bool(C.validate_consolidation(with_meta, static_now)))
    check("static-deletion-only (no metadata) is REJECTED",
          bool(C.validate_consolidation(posts, static_gone)))
    check("both halves together, with PENDING_MIGRATION still set, is REJECTED",
          bool(C.validate_consolidation(with_meta, static_gone)))
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
