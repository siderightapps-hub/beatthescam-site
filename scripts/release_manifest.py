#!/usr/bin/env python3
"""
release_manifest.py — apply, order-enforce and receipt the accuracy release.

WHY THIS EXISTS
---------------
Each content packet carried its own digests over its own fields, and the
operator's reviews found that none of them actually enforced the release order:

  * scotland-routing-v10 hashed nine FINAL-9 records over a key list its own
    prose described wrongly — following the written method literally gave 0/9
    matches even AFTER FINAL-9 (`scotland-routing-v10-c.md` §1);
  * nation-consumer-routing-v3 hashed `{quick_answer, sections, faq}` on its own
    14 target records, which passes identically in FIVE different corpus states
    — including one where Scotland's 202 source rows were never written and one
    where Shpock was never applied (`nation-consumer-routing-v3-c.md`);
  * shpock-scam-uk-v10 compared a compact-JSON digest against a `jq -S`
    pretty-JSON digest and called them a match, and folded a placeholder
    `updated` date into the receipt (`shpock-scam-uk-v10-c.md` §1–2);
  * legacy-hubs-v5 claimed "unchanged from v4" with no v4 payload or digest
    retained (`legacy-hubs-v5-c.md` §2).

A digest over the fields a packet happens to touch cannot prove what happened to
records it does not touch. So the receipt here is a digest over the WHOLE
corpus after each stage. There is exactly one corpus state that produces it, so
"apply in this order" stops being a sentence in a document and becomes a
precondition the tool refuses to proceed without.

USAGE
-----
    python3 scripts/release_manifest.py --emit      # compute and write the manifest
    python3 scripts/release_manifest.py --verify    # which stages are applied? is the tree sane?
    python3 scripts/release_manifest.py --apply     # apply every stage, in order, with receipts
    python3 scripts/release_manifest.py --apply --stage final9   # one stage only

`--apply` writes content/posts.json and content/category-hubs.json. It does NOT
build. Run the self-tests and the single non-concurrent build afterwards.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import stat
import sys
from datetime import date
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corpus as corpus_mod  # noqa: E402  — the shared public/source corpus partition

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs" / "review"
POSTS = ROOT / "content" / "posts.json"
HUBS = ROOT / "content" / "category-hubs.json"
MANIFEST = REVIEW / "release-manifest.json"

# ─── THE DIGEST SPEC, STATED ONCE ────────────────────────────────────────────
# Every digest in this release is computed exactly this way. Ambiguity here is
# what let a compact-JSON hash be compared against a `jq -S` hash and reported
# as a match.
DIGEST_SPEC = {
    "algorithm": "SHA-256",
    "encoding": "UTF-8",
    "serialization": "json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))",
    "trailing_newline": False,
    "note": "Applies to record digests, corpus digests and hub digests alike.",
}


def _iso_date(value: str) -> date:
    """Exactly YYYY-MM-DD.

    `date.fromisoformat()` on Python 3.11+ also accepts basic form (20260730)
    and ISO week dates (2026-W31-4), so it was not enforcing the documented
    contract (operator review, 2026-07-30).
    """
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{value!r} is not YYYY-MM-DD")
    return date.fromisoformat(value)


def digest(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def record_digest(record: dict, keys) -> str:
    """Digest of a record restricted to an EXPLICIT key list.

    `keys` is always spelled out by the caller — never "the keys the packet
    replaces", which is the phrasing that made the FINAL-9 receipts
    unreproducible from their own documentation.
    """
    return digest({k: record[k] for k in keys if k in record})


def corpus_digest(posts: list) -> str:
    """Digest of the ENTIRE corpus. This is the order-enforcing receipt: it sees
    every record, every field and every `sources_checked` row, so it cannot be
    satisfied by a state in which an upstream packet was skipped."""
    return digest(posts)


# Content identity, excluding the mutable application date, so a packet can be
# proved unchanged between versions without freezing `updated`.
STABLE_EXCLUDE = ("updated",)


def stable_digest(record: dict) -> str:
    return digest({k: v for k, v in record.items() if k not in STABLE_EXCLUDE})


# ─── LOADING ─────────────────────────────────────────────────────────────────

def load_posts() -> list:
    return json.loads(POSTS.read_text(encoding="utf-8"))


def load_hubs() -> dict:
    return json.loads(HUBS.read_text(encoding="utf-8"))


def write_posts(posts: list) -> None:
    # Byte-exact round-trip convention: indent=2, ensure_ascii=False, no
    # trailing newline (CLAUDE.md invariant 5).
    POSTS.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")


def write_hubs(hubs: dict) -> None:
    HUBS.write_text(json.dumps(hubs, indent=2, ensure_ascii=False), encoding="utf-8")


def packet(name: str) -> dict:
    path = REVIEW / f"{name}.json"
    if not path.exists():
        raise SystemExit(
            f"ERROR: {path} is missing. docs/review/ is gitignored — the packets exist "
            f"only on the machine that produced them."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def by_slug(posts: list) -> dict:
    return {p["slug"]: p for p in posts}


class ApplyError(Exception):
    """A precondition failed. The caller must abort the WHOLE release."""


# ─── APPLIERS ────────────────────────────────────────────────────────────────
# Each implements one packet's documented application contract. Every one
# asserts its `old` values before writing, and aborts the entire release on the
# first mismatch rather than half-applying an index-anchored patch to a corpus
# it was not built against.

def apply_full_records(posts: list, records: list, applied_on: str,
                       delete_keys: Optional[list] = None,
                       expect_keys: Optional[dict] = None) -> int:
    """FINAL-9 and Shpock: replace the listed fields of an existing record.

    `delete_keys` REMOVES named legacy fields. Overwriting only the keys a
    packet carries left Shpock's obsolete `content` and `excerpt` in place —
    Action Fraud branding, a built-in-payment description and an automatic
    PayPal-protection claim — even though the packet's application contract
    required their deletion (operator review, 2026-07-30).

    `expect_keys` is a postcondition: the exact key set each record must end
    with, so "the applied record is the proposed record" is checked, not assumed.
    """
    index = by_slug(posts)
    delete_keys = delete_keys or []
    for rec in records:
        slug = rec["slug"]
        live = index.get(slug)
        if live is None:
            raise ApplyError(f"{slug}: no such live record")
        for key, value in rec.items():
            if key == "slug":
                continue
            live[key] = copy.deepcopy(value)
        for key in delete_keys:
            live.pop(key, None)
        live["updated"] = applied_on
        want = (expect_keys or {}).get(slug)
        if want is not None and sorted(live) != sorted(want):
            raise ApplyError(
                f"{slug}: applied key set is {sorted(live)}, packet expects {sorted(want)}. "
                f"Extra keys: {sorted(set(live) - set(want))}; missing: "
                f"{sorted(set(want) - set(live))}"
            )
    return len(records)


def apply_field_mutations(posts: list, guides: dict, applied_on: str) -> dict:
    """Scotland and nation: per-slug field mutations with exact `old` assertions.

    `sections`/`faq` keys are indices into the live arrays; the recorded
    `heading`/`question` is checked too, so a reordered array is detected rather
    than silently mis-patched.
    """
    index = by_slug(posts)
    stats = {"guides": 0, "fields": 0, "sources_added": 0, "sources_present": 0}

    for slug, spec in guides.items():
        live = index.get(slug)
        if live is None:
            raise ApplyError(f"{slug}: no such live record")
        touched = False

        for field in ("quick_answer", "hero", "description", "title"):
            if field not in spec:
                continue
            change = spec[field]
            if live.get(field) != change["old"]:
                raise ApplyError(
                    f"{slug}.{field}: live value does not match the packet's `old`.\n"
                    f"  live: {live.get(field)!r:.200}\n  old:  {change['old']!r:.200}"
                )
            live[field] = change["new"]
            stats["fields"] += 1
            touched = True

        for field, anchor in (("sections", "heading"), ("faq", "question")):
            for raw_idx, change in (spec.get(field) or {}).items():
                idx = int(raw_idx)
                array = live.get(field) or []
                if idx >= len(array):
                    raise ApplyError(f"{slug}.{field}[{idx}]: index out of range ({len(array)} items)")
                pair = array[idx]
                if change.get(anchor) is not None and pair[0] != change[anchor]:
                    raise ApplyError(
                        f"{slug}.{field}[{idx}]: {anchor} is {pair[0]!r}, packet expected "
                        f"{change[anchor]!r} — the array has been reordered"
                    )
                if pair[1] != change["old"]:
                    raise ApplyError(
                        f"{slug}.{field}[{idx}]: body does not match the packet's `old`.\n"
                        f"  live: {pair[1]!r:.200}\n  old:  {change['old']!r:.200}"
                    )
                pair[1] = change["new"]
                stats["fields"] += 1
                touched = True

        for label, url in spec.get("sources_checked_add") or []:
            rows = live.setdefault("sources_checked", [])
            if any(existing_url == url for _, existing_url in rows):
                stats["sources_present"] += 1
                continue
            rows.append([label, url])
            stats["sources_added"] += 1
            touched = True

        if touched:
            live["updated"] = applied_on
            stats["guides"] += 1

    return stats


def reassert_sources(posts: list, guides: dict) -> int:
    """Re-append every `sources_checked_add` URL after ALL full-record writes.

    A later full-record replacement overwrites `sources_checked` wholesale and
    silently drops rows an earlier packet added — measured at 11 rows across six
    job guides when Scotland is applied before FINAL-9
    (`scotland-routing-v10-c.md`). This runs last so the final state is correct
    whatever order the writes happened in.
    """
    index = by_slug(posts)
    restored = 0
    for slug, spec in guides.items():
        live = index.get(slug)
        if live is None:
            continue
        rows = live.setdefault("sources_checked", [])
        for label, url in spec.get("sources_checked_add") or []:
            if not any(existing_url == url for _, existing_url in rows):
                rows.append([label, url])
                restored += 1
    return restored


def apply_record_fields(posts: list, change: dict, precondition: dict) -> dict:
    """consolidation-metadata-v1: add named fields to existing records.

    Deliberately NOT a date bump: no reader-visible text changes, and marking a
    non-rendering archive record as editorially revised would be a false claim.
    """
    index = by_slug(posts)
    stats = {"records": 0, "fields_added": 0}
    slug = precondition.get("slug")
    live = index.get(slug)
    if live is None:
        raise ApplyError(f"{slug}: no such live record")
    if precondition.get("consolidated_into_absent") and "consolidated_into" in live:
        raise ApplyError(
            f"{slug} already carries 'consolidated_into' ({live['consolidated_into']!r}) — "
            f"the packet was written against a corpus where it was absent"
        )
    want = precondition.get("record_digest_sha256")
    if want and digest(live) != want:
        raise ApplyError(
            f"{slug}: record digest is {digest(live)} but the packet expects {want}"
        )
    # The fourth precondition, previously declared but never read: the packet is
    # written against a specific static redirect, and applying it against a
    # different one would move the record's 301 (operator review, 2026-07-30).
    want_static = precondition.get("static_redirect_target")
    if want_static is not None:
        have = corpus_mod.ARTICLE_REDIRECTS.get(slug)
        if have != want_static:
            raise ApplyError(
                f"{slug}: static redirect target is {have!r} but the packet expects "
                f"{want_static!r}. The packet was written against a different redirect state."
            )
    for target_slug, spec in change.items():
        rec = index.get(target_slug)
        if rec is None:
            raise ApplyError(f"{target_slug}: no such live record")
        for key, value in (spec.get("add") or {}).items():
            if key in rec:
                raise ApplyError(f"{target_slug} already has {key!r}")
            rec[key] = copy.deepcopy(value)
            stats["fields_added"] += 1
        stats["records"] += 1
    return stats


def apply_code_patch(patch: list, *, dry_run: bool) -> dict:
    """Apply exact, reviewed source edits as part of a content stage.

    WHY THIS EXISTS
    ---------------
    The consolidation migration is not expressible as a content change. It needs
    `consolidated_into` on a record AND the removal of the static redirect AND
    the emptying of the transitional map — and the tool enforces a code baseline,
    so editing the code first invalidates the manifest, while editing it second
    means the applier's own final graph check fails on the state it just wrote.
    The release was therefore not executable in any order (operator review,
    2026-07-30, reproduced end to end).

    Each entry is `{file, old, new}` with `old` asserted exactly, so the patch is
    reviewable in the packet the same way prose mutations are. `dry_run` computes
    the resulting text without touching disk, so the whole transaction can be
    validated before anything is written.
    """
    results: dict = {}
    for n, entry in enumerate(patch):
        path = ROOT / entry["file"]
        if not path.exists():
            raise ApplyError(f"{entry['file']}: no such file")
        # Read the STAGED text if an earlier entry already edited this file.
        # Re-reading from disk each time meant several patches to one file did
        # not compose — only the last one survived, silently. The static-entry
        # and PENDING_MIGRATION edits both target corpus.py.
        text = results.get(entry["file"]) or path.read_text(encoding="utf-8")
        old, new = entry["old"], entry["new"]
        if text.count(old) != 1:
            raise ApplyError(
                f"{entry['file']}: patch[{n}] `old` text appears {text.count(old)} times, "
                f"expected exactly once. The reviewed code state has moved, or an earlier "
                f"entry in this patch already changed it."
            )
        results[entry["file"]] = text.replace(old, new, 1)

    # An exact-match patch can still produce invalid code — clipping a
    # continuation line off a multi-line statement leaves an IndentationError
    # that nothing catches until the next import. Compile every patched Python
    # file before it reaches disk.
    for name, text in results.items():
        if name.endswith(".py"):
            try:
                compile(text, name, "exec")
            except SyntaxError as exc:
                raise ApplyError(
                    f"{name}: the patched source does not compile — {exc.msg} at line "
                    f"{exc.lineno}. The patch's `old`/`new` text does not cover a whole statement."
                )
    if not dry_run:
        for name, text in results.items():
            (ROOT / name).write_text(text, encoding="utf-8")
    return results


def staged_corpus_module(staged: dict):
    """Import the ACTUAL staged corpus.py in an isolated context.

    `final_state` in the packet is a DECLARATION. Trusting it meant a patch whose
    real edits disagreed with the declaration passed preflight and failed only
    after source files had been written — leaving Hermes with no metadata, no
    static redirect and no pending entry (operator review, 2026-07-30). The
    declaration is now a receipt to compare against, not the authority.
    """
    import importlib.util
    import tempfile

    text = staged.get("scripts/corpus.py")
    if text is None:
        return corpus_mod
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "staged_corpus.py"
        path.write_text(text, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("staged_corpus", path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise ApplyError(f"the staged scripts/corpus.py does not import: {exc}")
    return module


def final_graph_inputs(patch: list, packet_data: dict, staged: dict) -> dict:
    """The graph inputs the patch ACTUALLY produces, cross-checked against what
    the packet declares."""
    module = staged_corpus_module(staged)
    derived_static = dict(getattr(module, "ARTICLE_REDIRECTS", {}))
    derived_pending = dict(getattr(module, "PENDING_MIGRATION", {}))

    final = packet_data.get("final_state") or {}
    declared_removed = sorted(final.get("remove_static_redirects") or [])
    declared_pending = dict(final.get("pending_migration_after") or {})
    actually_removed = sorted(set(corpus_mod.ARTICLE_REDIRECTS) - set(derived_static))

    if actually_removed != declared_removed:
        raise ApplyError(
            f"the code patch removes static redirects {actually_removed} but `final_state` "
            f"declares {declared_removed}. The declaration and the patch disagree."
        )
    if derived_pending != declared_pending:
        raise ApplyError(
            f"the code patch leaves PENDING_MIGRATION as {derived_pending} but `final_state` "
            f"declares {declared_pending}."
        )
    return {"static_after": derived_static, "pending_after": derived_pending}


def apply_hub_records(hubs: dict, records: dict, applied_on: str) -> int:
    """hubs-v11: ten complete new hub records, written whole."""
    for key, record in records.items():
        hubs[key] = copy.deepcopy(record)
        hubs[key]["updated"] = applied_on
    return len(records)


def apply_hub_patches(hubs: dict, patches: dict, applied_on: str) -> dict:
    """legacy-hubs-v6: PARTIAL patches to three existing hubs.

    Not a replacement map — only the keys present per hub are applied, and
    `sections`/`faq` keys are indices with a recorded heading/question anchor.
    Treating this payload as a record replacement writes the patch spec itself
    into content/category-hubs.json, which produces sections like `["0"]`.

    `sources_checked` REPLACES the hub's list, and the contract requires the
    live hub to have none: an intervening source review must not be silently
    overwritten.
    """
    stats = {"hubs": 0, "fields": 0, "source_lists_written": 0}
    for key, spec in patches.items():
        live = hubs.get(key)
        if live is None:
            raise ApplyError(f"hub {key!r}: no such live hub")

        if "sources_checked" in spec or "updated" in spec:
            if live.get("sources_checked"):
                raise ApplyError(
                    f"hub {key!r} already has {len(live['sources_checked'])} source row(s). "
                    f"The patch would replace them — abort rather than overwrite an "
                    f"intervening source review."
                )
            if live.get("updated"):
                raise ApplyError(f"hub {key!r} already has updated={live['updated']!r}")

        if "intro" in spec:
            change = spec["intro"]
            if live.get("intro") != change["old"]:
                raise ApplyError(f"hub {key!r}.intro does not match the patch's `old`")
            live["intro"] = change["new"]
            stats["fields"] += 1

        for field, anchor in (("sections", "heading"), ("faq", "question")):
            for raw_idx, change in (spec.get(field) or {}).items():
                idx = int(raw_idx)
                array = live.get(field) or []
                if idx >= len(array):
                    raise ApplyError(f"hub {key!r}.{field}[{idx}]: index out of range")
                pair = array[idx]
                if change.get(anchor) is not None and pair[0] != change[anchor]:
                    raise ApplyError(
                        f"hub {key!r}.{field}[{idx}]: {anchor} is {pair[0]!r}, patch expected "
                        f"{change[anchor]!r} — the array has been reordered"
                    )
                if pair[1] != change["old"]:
                    raise ApplyError(f"hub {key!r}.{field}[{idx}] does not match the patch's `old`")
                pair[1] = change["new"]
                stats["fields"] += 1

        if "sources_checked" in spec:
            live["sources_checked"] = copy.deepcopy(spec["sources_checked"])
            stats["source_lists_written"] += 1

        live["updated"] = applied_on
        stats["hubs"] += 1
    return stats


# ─── STAGES ──────────────────────────────────────────────────────────────────
# The release order, executable. Stage N's `expects` is the corpus digest the
# tree must already have; there is exactly one state that produces it.

STAGES = [
    {
        "id": "final9",
        "title": "FINAL-9 guides",
        "packets": ["FINAL-9-guides-v4"],
        "why": "Scotland's patch map overlaps these nine records, so they must land first.",
    },
    {
        "id": "scotland-shpock",
        "title": "Scotland routing + Yodel, with Shpock",
        "packets": ["scotland-routing-v15", "shpock-scam-uk-v15"],
        "why": "Mandatory companions; neither releases alone. Source rows are re-asserted "
               "after all full-record writes so no overlap row is lost.",
    },
    {
        "id": "nation",
        "title": "Nation consumer routing",
        "packets": ["nation-consumer-routing-v9"],
        "why": "Depends on both upstream stages for its `old` values.",
    },
    {
        "id": "hubs",
        "title": "All thirteen category hubs",
        "packets": ["hubs-v15", "legacy-hubs-v10"],
        "why": "Landed together with the strict source/key enforcement, or the hub "
               "self-test suite is inconsistent with the content.",
    },
    {
        "id": "consolidation",
        "title": "Consolidation metadata",
        "packets": ["consolidation-metadata-v5"],
        "why": "Moves the last consolidation declaration onto its own record. ATOMIC with "
               "deleting the matching static ARTICLE_REDIRECTS entry — leaving both is a "
               "validation error by design, so a half-applied patch fails loudly.",
    },
]


def run_stage(stage: dict, posts: list, hubs: dict, applied_on: str) -> dict:
    """Apply one stage in memory. Returns a report."""
    report = {"id": stage["id"], "title": stage["title"], "packets": {}}

    for name in stage["packets"]:
        data = packet(name)
        entry: dict = {}

        if "guides" in data and isinstance(data["guides"], list):
            entry["records_replaced"] = apply_full_records(posts, data["guides"], applied_on)
        elif "guides" in data and isinstance(data["guides"], dict):
            entry.update(apply_field_mutations(posts, data["guides"], applied_on))
        if "record" in data:
            entry["records_replaced"] = apply_full_records(
                posts, [data["record"]], applied_on,
                delete_keys=data.get("delete_keys"),
                expect_keys={data["record"]["slug"]:
                             sorted(set(data["record"]) | {"updated"})})
            if data.get("delete_keys"):
                entry["keys_deleted"] = sorted(data["delete_keys"])
        if data.get("payload_shape") == "record_field_add":
            entry.update(apply_record_fields(posts, data["change"],
                                             data["old_state_precondition"]))
        if data.get("code_patch"):
            # Stage the patched text, IMPORT it, and validate the final graph
            # against what the staged code actually says — before writing a byte.
            staged = apply_code_patch(data["code_patch"], dry_run=True)
            inputs = final_graph_inputs(data["code_patch"], data, staged)
            problems = corpus_mod.validate_consolidation(
                posts, inputs["static_after"], inputs["pending_after"])
            if problems:
                raise ApplyError(
                    "the FINAL graph (under the STAGED code) would be invalid:\n"
                    + "\n".join(f"    - {x}" for x in problems))
            entry["code_patch_files"] = sorted(staged)
            entry["_staged_files"] = staged
            entry["_final_static_after"] = inputs["static_after"]
            entry["_pending_after"] = inputs["pending_after"]
        if "hubs" in data:
            # Two different payload shapes. hubs-v11 carries complete new
            # records; legacy-hubs-v6 carries PARTIAL patches into three
            # existing ones. Applying the second as the first writes the patch
            # spec into the content file.
            if data.get("payload_shape") == "partial_patches":
                entry.update(apply_hub_patches(hubs, data["hubs"], applied_on))
            else:
                entry["hubs_written"] = apply_hub_records(hubs, data["hubs"], applied_on)
        if not entry:
            raise ApplyError(
                f"{name}: no recognised payload. A packet must carry `guides` (list or map), "
                f"`record`, or `hubs`. hubs-v10 was a bare {{slug: record}} map, which a wrapper "
                f"key would silently turn into a hub called 'packet_version'."
            )

        report["packets"][name] = entry

    # Overlap-safe re-assertion, AFTER every full-record write in this stage.
    for name in stage["packets"]:
        data = packet(name)
        if isinstance(data.get("guides"), dict):
            restored = reassert_sources(posts, data["guides"])
            if restored:
                report["packets"][name]["sources_reasserted"] = restored

    return report


# The FINAL-9 receipts scotland-routing-v10 carries were computed over THIS key
# list. Its prose said "restricted to the keys FINAL-9 replaces", which omits
# `slug` and gives 0/9 matches even after FINAL-9 has been applied. `slug` is a
# lookup key, not a replaced field — declaring it explicitly is the whole point
# of a `digest_keys` array (`scotland-routing-v10-c.md` §1).
FINAL9_DIGEST_KEYS = ["slug", "description", "hero", "quick_answer",
                      "sections", "faq", "sources_checked"]


def code_baseline(overrides: dict | None = None) -> dict:
    """A digest over the release-critical code, plus the commit it was taken at.

    `minimum_code_commit` in the packets is descriptive: nothing read it, so
    updating the string protected nothing (operator review, 2026-07-30). This is
    a checked precondition — `--apply` refuses to run against code that is not
    the code the manifest was emitted from.
    """
    import subprocess
    # The release-critical state: the applier and everything that decides what
    # gets published, PLUS the inputs that decide how it renders. The eight-file
    # version omitted the audit callers, the canon JS bridge, the checker and
    # its tests, the CI workflow and the canon itself; the twenty-file version
    # still omitted the template, site/affiliate config and assets. Both gaps
    # let a file change between --emit and --apply without invalidating the
    # baseline (operator reviews, 2026-07-30).
    files = [
        "scripts/canon.py", "scripts/corpus.py", "scripts/content_gate.py",
        "scripts/build.py", "scripts/release_manifest.py",
        "scripts/hub_selftest.py", "scripts/corpus_selftest.py",
        "scripts/gate_quickanswer_selftest.py", "scripts/release_selftest.py",
        "scripts/audit_corpus.py", "scripts/fact_reverify.py",
        "scripts/similarity_report.py", "scripts/sync_canon_js.py",
        "netlify/functions/check-scam.js",
        "netlify/functions/lib/allowed-domains.js",
        "netlify/functions/lib/canon-routes.js",
        "netlify/functions/lib/reporting-links.js",
        "netlify/functions/lib/reporting-links.test.js",
        ".github/workflows/gate-selftest.yml",
        # Canon input, plus the other inputs that change RENDERED output. The
        # 20-file version was a release-CONTROL surface only, so a template or
        # site-config edit between --emit and --apply was invisible to it
        # (operator review, 2026-07-30).
        "content/sources.json",
        "content/site.json",
        "content/affiliates.json",
        "templates/base.html",
        "assets/app.js",
        "assets/styles.css",
    ]
    overrides = overrides or {}
    blobs = {}
    missing = []
    for f in files:
        if f in overrides:
            blobs[f] = hashlib.sha256(overrides[f].encode("utf-8")).hexdigest()
        elif (ROOT / f).exists():
            blobs[f] = hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
        else:
            missing.append(f)
    if missing:
        # Silently omitting a missing file produced a baseline that attested to
        # less than it claimed.
        raise SystemExit(f"ERROR: release-critical file(s) missing: {missing}")
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--"] + files, cwd=ROOT,
                                    capture_output=True, text=True, check=True).stdout.strip())
    except Exception:
        head, dirty = None, None
    return {"files": blobs, "digest": digest(blobs), "head": head, "uncommitted_changes": dirty}


def build_receipts() -> dict:
    """Per-packet receipts with EXPLICIT key lists and a reproducible property.

    Each entry states what was hashed and what the digest is expected to do —
    including, for FINAL-9, the before/after scores a verifier must reproduce.
    """
    receipts: dict = {}

    posts = load_posts()
    index = by_slug(posts)
    try:
        stored = packet("scotland-routing-v15")["prerequisite_state"]["record_digests"]
        f9 = packet("FINAL-9-guides-v4")["guides"]
    except SystemExit:
        return receipts

    def score(idx):
        return sum(1 for slug, want in stored.items()
                   if slug in idx and record_digest(idx[slug], FINAL9_DIGEST_KEYS) == want)

    before = score(index)
    after_posts = copy.deepcopy(posts)
    apply_full_records(after_posts, f9, "2026-07-30")
    after = score(by_slug(after_posts))

    receipts["FINAL-9-guides-v4"] = {
        "purpose": "Prove FINAL-9 has landed before the first Scotland write.",
        "digest_keys": FINAL9_DIGEST_KEYS,
        "digest_keys_note": "`slug` is a LOOKUP key and is included in the hash. Omitting it — "
                            "which is what 'the keys FINAL-9 replaces' describes — scores 0/9 "
                            "before AND after, so the receipt proves nothing.",
        "expected_matches_before": f"0/{len(stored)}",
        "expected_matches_after": f"{len(stored)}/{len(stored)}",
        "measured_matches_before": f"{before}/{len(stored)}",
        "measured_matches_after": f"{after}/{len(stored)}",
        "reproduces": before == 0 and after == len(stored),
        "record_digests": stored,
    }

    # Shpock: content identity and applied state are DIFFERENT receipts. Folding
    # a placeholder `updated` into one hash and calling it proof of a future
    # applied state is the defect (`shpock-scam-uk-v10-c.md` §2).
    try:
        record = packet("shpock-scam-uk-v15")["record"]
    except SystemExit:
        record = None
    if record:
        receipts["shpock-scam-uk-v15"] = {
            "purpose": "Prove the approved reader record is the one applied.",
            "digest_keys": "the whole record",
            "stable_content_digest": stable_digest(record),
            "stable_excludes": list(STABLE_EXCLUDE),
            "note": "The stable digest excludes `updated` so content identity survives the date "
                    "being set at application time. The applied-record digest is only meaningful "
                    "AFTER the real date is written, and appears in the stage `produces` corpus "
                    "digest rather than as a separate pre-computed hash.",
        }

    return receipts


def build_manifest(applied_on: str) -> dict:
    posts, hubs = load_posts(), load_hubs()
    manifest = {
        "generated_for_application_date": applied_on,
        "digest_spec": DIGEST_SPEC,
        "contract": [
            "Stage N may only be applied to a corpus whose digest equals stage N's `expects`.",
            "`expects` and `produces` are digests over the WHOLE corpus, not over the fields a "
            "packet happens to touch: a per-packet digest cannot prove what happened to records "
            "the packet does not name.",
            "`digest_keys` is always an explicit list. Never 'the keys the packet replaces'.",
            "Record digests exclude `updated` (`stable`) so content identity can be proved across "
            "packet versions, and include it (`applied`) so the written state can be proved.",
        ],
        "baseline": {"posts": corpus_digest(posts), "hubs": digest(hubs)},
        "baseline_source_records": len(posts),
        "code_baseline": code_baseline(),
        # Filled in below: the code state the release's own patches produce. A
        # successful release CHANGES the code, so `--verify` afterwards must
        # recognise the post-release baseline rather than reporting drift
        # against the pre-release one.
        "code_baseline_after": None,
        "receipts": build_receipts(),
        "stages": [],
    }

    # The static/pending maps as each simulated stage leaves them. A stage
    # carrying a code_patch changes what "valid" means for every stage after it.
    stage_static: dict = dict(corpus_mod.ARTICLE_REDIRECTS)
    stage_pending: dict = dict(corpus_mod.PENDING_MIGRATION)
    patched_files: dict = {}

    for stage in STAGES:
        expects_posts, expects_hubs = corpus_digest(posts), digest(hubs)
        code_before = code_baseline(patched_files)["digest"]
        try:
            report = run_stage(stage, posts, hubs, applied_on)
            for entry in report["packets"].values():
                if entry.get("_staged_files"):
                    patched_files.update(entry["_staged_files"])
                if entry.get("_final_static_after") is not None:
                    stage_static = dict(entry["_final_static_after"])
                    stage_pending = dict(entry.get("_pending_after") or {})
        except (ApplyError, SystemExit) as exc:
            manifest["stages"].append({
                "id": stage["id"], "title": stage["title"], "why": stage["why"],
                "status": "UNAVAILABLE", "reason": str(exc),
                "expects": {"posts": expects_posts, "hubs": expects_hubs},
            })
            break
        # Validate the graph AFTER each simulated stage. Without this, emit
        # recorded the invalid metadata-plus-static final state as `status:
        # ready` and the problem only surfaced at the very end of a real
        # application (operator review, 2026-07-30). A manifest that cannot be
        # applied must not be emitted as ready.
        graph_problems = corpus_mod.validate_consolidation(
            posts, stage_static or None, stage_pending)
        if graph_problems:
            manifest["stages"].append({
                **{k: stage[k] for k in ("id", "title", "why")},
                "status": "INVALID",
                "reason": "the graph after this stage is invalid: " + "; ".join(graph_problems),
                "expects": {"posts": expects_posts, "hubs": expects_hubs},
            })
            break
        manifest["stages"].append({
            **{k: stage[k] for k in ("id", "title", "why")},
            "status": "ready",
            "packets": list(stage["packets"]),
            # Packet identity, verified before mutation. Without this an edited
            # gitignored packet could be applied against a stale manifest.
            "packet_digests": {n: digest(packet(n)) for n in stage["packets"]},
            "expects": {"posts": expects_posts, "hubs": expects_hubs},
            "produces": {"posts": corpus_digest(posts), "hubs": digest(hubs)},
            # Cumulative CODE receipts. A stage carrying a code_patch leaves the
            # tree at a legitimate intermediate code state that matches neither
            # the global pre- nor post-release baseline; comparing only the
            # global digest made `--stage consolidation` impossible after
            # `--stage hubs` (operator review, 2026-07-30).
            "code_expects": code_before,
            "code_produces": code_baseline(patched_files)["digest"],
            "applied": {n: {k: v for k, v in e.items() if not k.startswith("_")}
                        for n, e in report["packets"].items()},
        })

    manifest["code_baseline_after"] = code_baseline(patched_files)
    return manifest


def cmd_emit(applied_on: str) -> int:
    _refuse_if_journal("--emit")
    manifest = build_manifest(applied_on)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(ROOT)}\n")
    print(f"baseline corpus  {manifest['baseline']['posts']}")
    for s in manifest["stages"]:
        if s["status"] != "ready":
            print(f"\n  {s['id']:18} UNAVAILABLE — {s['reason'].splitlines()[0]}")
            continue
        print(f"\n  {s['id']:18} {s['title']}")
        print(f"    expects  {s['expects']['posts']}")
        print(f"    produces {s['produces']['posts']}")
        for name, stats in s["applied"].items():
            print(f"    {name}: {stats}")
    return 0


def _state(posts: list, hubs: dict) -> dict:
    """The FULL release state. Both corpora, always together.

    Comparing only `posts` is what let an after-nation tree report as "after
    hubs": the nation and hubs stages deliberately produce the same posts digest,
    because hubs do not touch posts. The consolidation stage then applied
    successfully with all ten new hub records still absent (operator review,
    2026-07-30, reproduced in four separate replies).
    """
    return {"posts": corpus_digest(posts), "hubs": digest(hubs)}


def _fmt(state: dict) -> str:
    return f"posts {state['posts'][:16]}…  hubs {state['hubs'][:16]}…"


def _require_manifest() -> dict:
    """A stale or absent manifest must never downgrade application to unchecked
    mode. `--apply` used to treat it as optional."""
    if not MANIFEST.exists():
        raise SystemExit(
            f"ERROR: {MANIFEST.relative_to(ROOT)} not found. The manifest is the release "
            f"receipt, not an optional convenience — run --emit first."
        )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in ("digest_spec", "baseline", "stages", "generated_for_application_date",
                "code_baseline"):
        if key not in manifest:
            raise SystemExit(f"ERROR: {MANIFEST.relative_to(ROOT)} has no {key!r} — regenerate it")

    # STRICT schema. A bogus "ready" stage added to the manifest used to make
    # `--apply --stage bogus` return success without executing anything, because
    # the known-stage check read the MANIFEST rather than the executable STAGES
    # (operator review, 2026-07-30).
    recorded = [e["id"] for e in manifest["stages"]]
    expected = [x["id"] for x in STAGES]
    if recorded != expected[:len(recorded)]:
        raise SystemExit(
            f"ERROR: manifest stage order {recorded} is not a prefix of the executable order "
            f"{expected}. Regenerate the manifest."
        )
    for entry in manifest["stages"]:
        stage = next((x for x in STAGES if x["id"] == entry["id"]), None)
        if stage is None:
            raise SystemExit(f"ERROR: manifest records unknown stage {entry['id']!r}")
        if entry.get("status") != "ready":
            continue
        if list(entry.get("packets") or []) != list(stage["packets"]):
            raise SystemExit(
                f"ERROR: stage {entry['id']!r} records packets {entry.get('packets')} but the "
                f"executable stage applies {stage['packets']}"
            )
        if set(entry.get("packet_digests") or {}) != set(stage["packets"]):
            raise SystemExit(
                f"ERROR: stage {entry['id']!r} packet digests cover "
                f"{sorted(entry.get('packet_digests') or {})}, expected {sorted(stage['packets'])}"
            )
        for key in ("expects", "produces"):
            if set(entry.get(key) or {}) != {"posts", "hubs"}:
                raise SystemExit(
                    f"ERROR: stage {entry['id']!r} {key!r} must record exactly posts and hubs"
                )
        # Code receipts are REQUIRED, not optional. cmd_apply() treated a missing
        # `code_expects` as "do not check code", so deleting one line from the
        # manifest let a stage apply against changed release-critical files
        # (operator review, 2026-07-30).
        for key in ("code_expects", "code_produces"):
            value = entry.get(key)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise SystemExit(
                    f"ERROR: stage {entry['id']!r} has no valid {key!r} (expected a 64-character "
                    f"SHA-256 hex digest). Regenerate the manifest."
                )
    if manifest.get("digest_spec") != DIGEST_SPEC:
        raise SystemExit("ERROR: the manifest's digest_spec differs from this tool's — "
                         "its digests were computed a different way. Regenerate it.")
    after = manifest.get("code_baseline_after")
    if not isinstance(after, dict) or "digest" not in after:
        raise SystemExit("ERROR: the manifest has no usable `code_baseline_after` — regenerate it")
    # Chain: each stage must start from the code the previous stage produced.
    ready = [e for e in manifest["stages"] if e.get("status") == "ready"]
    for prev, nxt in zip(ready, ready[1:]):
        if nxt["code_expects"] != prev["code_produces"]:
            raise SystemExit(
                f"ERROR: stage {nxt['id']!r} expects code {nxt['code_expects'][:16]}… but stage "
                f"{prev['id']!r} produces {prev['code_produces'][:16]}… — the receipts do not chain."
            )
    if ready and ready[0]["code_expects"] != manifest.get("code_baseline", {}).get("digest"):
        raise SystemExit("ERROR: the first ready stage does not start from the manifest's "
                         "pre-release code baseline")
    if ready and ready[-1]["code_produces"] != (manifest.get("code_baseline_after") or {}).get("digest"):
        raise SystemExit("ERROR: the last ready stage does not end at `code_baseline_after`")

    try:
        _iso_date(manifest["generated_for_application_date"])
    except (TypeError, ValueError):
        raise SystemExit(
            f"ERROR: manifest application date "
            f"{manifest['generated_for_application_date']!r} is not YYYY-MM-DD"
        )
    return manifest


def _packet_identity(name: str) -> str:
    """Digest of the packet FILE as it will be applied."""
    return digest(packet(name))


def _check_packet_identity(stage_manifest: dict) -> None:
    """A packet edited after the manifest was emitted is a different release.

    The packets' own `payload_digest` / `stable_content_digests` are descriptive
    only — the applier never read them, so a locally altered gitignored packet
    could be applied against a stale manifest.
    """
    recorded = stage_manifest.get("packet_digests") or {}
    if not recorded:
        raise SystemExit(
            f"ERROR: stage {stage_manifest['id']!r} records no packet digests — regenerate "
            f"the manifest so packet identity can be verified before mutation."
        )
    for name, want in recorded.items():
        got = _packet_identity(name)
        if got != want:
            raise SystemExit(
                f"ERROR: packet {name!r} has changed since the manifest was emitted.\n"
                f"       manifest: {want}\n       on disk:  {got}\n"
                f"       Regenerate the manifest, or restore the reviewed packet."
            )


def _check_graph(posts: list) -> None:
    """The consolidation graph must be valid before anything is written, and
    before a state is reported as applied."""
    try:
        corpus_mod.partition(posts)
    except corpus_mod.CorpusError as exc:
        raise SystemExit(f"ERROR: the resulting corpus is invalid:\n{exc}")


JOURNAL = ROOT / ".release-journal.json"
TMP_SUFFIX = ".release-tmp"

# Deterministic failure injection for scripts/release_selftest.py. Making a
# directory unwritable always failed on the FIRST temp-file creation, so tests
# labelled "late failure" proved only that nothing had been written yet — they
# exercised no rollback at all (operator review, 2026-07-30).
_FAIL_AFTER = os.environ.get("RELEASE_SELFTEST_FAIL_AFTER")
_FAIL_VALIDATION = os.environ.get("RELEASE_SELFTEST_FAIL_VALIDATION")
# Simulates an interruption: everything is written, the journal survives.
_LEAVE_JOURNAL = os.environ.get("RELEASE_SELFTEST_LEAVE_JOURNAL")


def _snapshot(names) -> dict:
    """Existence, bytes and MODE for every path the transaction will touch.

    Mode matters: replacing a file via a fresh temp file gives it the default
    0644, so a successful release silently turned tracked `scripts/hub_selftest.py`
    from 100755 into 100644 — an unreceipted repository change that also made
    "leave the tree exactly as it was" false on rollback.
    """
    snap = {}
    for name in names:
        path = ROOT / name
        if path.exists():
            snap[name] = {"exists": True,
                          "text": path.read_text(encoding="utf-8"),
                          "mode": stat.S_IMODE(path.stat().st_mode)}
        else:
            snap[name] = {"exists": False, "text": None, "mode": None}
    return snap


def _restore(snap: dict) -> None:
    for name, entry in snap.items():
        path = ROOT / name
        if entry["exists"]:
            path.write_text(entry["text"], encoding="utf-8")
            if entry["mode"] is not None:
                path.chmod(entry["mode"])
        else:
            path.unlink(missing_ok=True)


def _clear_temps() -> None:
    for path in ROOT.rglob("*" + TMP_SUFFIX):
        path.unlink(missing_ok=True)


def _commit_transaction(payload: dict) -> dict:
    """Write every file, preserving modes, under a journal. Returns the snapshot.

    The journal is NOT removed here. The caller must validate the written state
    and then call `_finalize_transaction()`. Deleting it before post-write
    validation meant a failing live graph check left the tree fully mutated with
    no recovery available (operator review, 2026-07-30).
    """
    snap = _snapshot(payload)
    JOURNAL.write_text(json.dumps(
        {"note": "release_manifest.py transaction in progress — run --recover to undo",
         "snapshot": snap, "writing": sorted(payload)},
        ensure_ascii=False), encoding="utf-8")

    written: list = []
    try:
        for n, (name, text) in enumerate(sorted(payload.items())):
            if _FAIL_AFTER is not None and n == int(_FAIL_AFTER):
                raise OSError(f"injected failure after {n} replacement(s)")
            path = ROOT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + TMP_SUFFIX)
            tmp.write_text(text, encoding="utf-8")
            mode = snap[name]["mode"]
            if mode is not None:
                tmp.chmod(mode)                  # carry the original mode across
            tmp.replace(path)
            written.append(name)
    except Exception as exc:
        _restore({k: v for k, v in snap.items() if k in written})
        _clear_temps()
        JOURNAL.unlink(missing_ok=True)
        raise SystemExit(
            f"ERROR: write failed ({exc}). All {len(written)} already-written file(s) were "
            f"ROLLED BACK, including their modes; the tree is unchanged."
        )
    return snap


def _finalize_transaction() -> None:
    _clear_temps()
    if _LEAVE_JOURNAL:
        raise SystemExit("ERROR: injected interruption — the journal was left in place. "
                         "Run --recover.")
    JOURNAL.unlink(missing_ok=True)


def _rollback_from_journal(reason: str) -> None:
    if JOURNAL.exists():
        data = json.loads(JOURNAL.read_text(encoding="utf-8"))
        _restore(data.get("snapshot", {}))
        _clear_temps()
        JOURNAL.unlink(missing_ok=True)
    raise SystemExit(f"ERROR: {reason}\nThe transaction was ROLLED BACK; the tree is unchanged.")


def _refuse_if_journal(mode: str) -> None:
    """An unresolved transaction must block everything except --recover.

    A journal left by an interruption used to be ignored: `--verify` reported the
    final state and exited 0, and a fresh `--apply` OVERWROTE the only snapshot
    of the pre-transaction tree.
    """
    if JOURNAL.exists():
        raise SystemExit(
            f"ERROR: an unresolved transaction journal exists ({JOURNAL.name}).\n"
            f"       A previous run was interrupted. Run --recover first; {mode} refuses to "
            f"proceed while a journal could still be the only snapshot of the original tree."
        )


def cmd_recover() -> int:
    """Undo an interrupted transaction from its journal."""
    if not JOURNAL.exists():
        _clear_temps()
        print("No transaction journal — nothing to recover.")
        return 0
    data = json.loads(JOURNAL.read_text(encoding="utf-8"))
    snap = data.get("snapshot", {})
    _restore(snap)
    _clear_temps()
    JOURNAL.unlink(missing_ok=True)
    print(f"Recovered {len(snap)} file(s) from the transaction journal, including modes.")
    return 0


def cmd_verify() -> int:
    _refuse_if_journal("--verify")
    manifest = _require_manifest()
    live = _state(load_posts(), load_hubs())
    live_code = code_baseline()["digest"]
    print(f"live  {_fmt(live)}  code {live_code[:16]}…\n")

    # ONE INDIVISIBLE POSITION. Content and code used to be recognised
    # separately, so a tree with after-nation content and after-hubs code exited
    # 0, labelled the data "after nation", labelled the code "after hubs" and
    # marked hubs as next (operator review, 2026-07-30). A mixed tuple is not a
    # state this release knows.
    def tup(posts_d, hubs_d, code_d):
        return (posts_d, hubs_d, code_d)

    known = {tup(manifest["baseline"]["posts"], manifest["baseline"]["hubs"],
                 manifest.get("code_baseline", {}).get("digest")): "baseline (nothing applied)"}
    for entry in manifest["stages"]:
        if entry.get("status") != "ready":
            continue
        known[tup(entry["produces"]["posts"], entry["produces"]["hubs"],
                  entry["code_produces"])] = f"after stage '{entry['id']}'"

    here = tup(live["posts"], live["hubs"], live_code)
    position = known.get(here)

    if position is None:
        print("tree is at: AN UNRECOGNISED STATE — do not apply.")
        print("            posts, hubs AND code must all match one recorded stage.")
        for entry in manifest["stages"]:
            if entry.get("status") != "ready":
                continue
            parts = {"posts": live["posts"] == entry["produces"]["posts"],
                     "hubs": live["hubs"] == entry["produces"]["hubs"],
                     "code": live_code == entry["code_produces"]}
            if any(parts.values()) and not all(parts.values()):
                match = ", ".join(k for k, v in parts.items() if v)
                differ = ", ".join(k for k, v in parts.items() if not v)
                print(f"            NOTE stage {entry['id']!r}: {match} match, {differ} differ "
                      f"— a MIXED position, not a valid release state.")
        return 1

    print(f"tree is at: {position}")
    try:
        _check_graph(load_posts())
        print("            consolidation graph: valid")
    except SystemExit as exc:
        print(f"            {exc}")
        return 1

    drift = []
    for entry in manifest["stages"]:
        if entry.get("status") != "ready":
            continue
        for name, want in (entry.get("packet_digests") or {}).items():
            try:
                if _packet_identity(name) != want:
                    drift.append(f"packet {name}")
            except SystemExit:
                drift.append(f"packet {name} (missing)")

    for entry in manifest["stages"]:
        mark = "ready" if entry["status"] == "ready" else "UNAVAILABLE"
        nxt = (entry["status"] == "ready"
               and here == tup(entry["expects"]["posts"], entry["expects"]["hubs"],
                               entry["code_expects"]))
        print(f"  [{'NEXT ' if nxt else '     '}] {entry['id']:18} {mark}")
    if drift:
        print(f"\nDRIFT: {', '.join(sorted(set(drift)))} — re-run --emit before applying.")
        return 1
    return 0


def cmd_apply(applied_on: str, only: str | None) -> int:
    _refuse_if_journal("--apply")
    manifest = _require_manifest()

    try:
        _iso_date(applied_on)
    except (TypeError, ValueError):
        raise SystemExit(f"ERROR: --date {applied_on!r} is not YYYY-MM-DD. It would be written "
                         f"verbatim into every `updated` field.")

    if manifest["generated_for_application_date"] != applied_on:
        raise SystemExit(
            f"ERROR: the manifest was generated for {manifest['generated_for_application_date']} "
            f"but --date is {applied_on}. Stage outputs include `updated`, so a different date "
            f"is a different release. Re-run --emit with this date."
        )

    known = {s["id"] for s in manifest["stages"]}
    if only and only not in known:
        raise SystemExit(f"ERROR: unknown stage {only!r}. Known stages: {', '.join(sorted(known))}")

    posts, hubs = load_posts(), load_hubs()
    staged_code: list = []

    for stage in STAGES:
        if only and stage["id"] != only:
            continue
        recorded = next((s for s in manifest["stages"] if s["id"] == stage["id"]), None)
        if recorded is None or recorded["status"] != "ready":
            raise SystemExit(
                f"ERROR: stage {stage['id']!r} is not recorded as ready in the manifest"
            )

        # PRECONDITION: the code this stage expects. Cumulative, so a staged
        # workflow can continue from a stage that patched code — and, in a
        # one-shot run, so does the IN-MEMORY state, because code patches are
        # written only in the final transaction.
        pending_code: dict = {}
        for files in staged_code:
            pending_code.update(files)
        live_code = code_baseline(pending_code)["digest"]
        want_code = recorded.get("code_expects")
        if want_code and live_code != want_code:
            raise SystemExit(
                f"ERROR: stage {stage['id']!r} expects code baseline {want_code}\n"
                f"       but the tree is at                        {live_code}\n"
                f"       Either an upstream code patch has not been applied, or the "
                f"release-critical code has changed since --emit. Re-run --emit, or restore "
                f"the reviewed code."
            )

        # PRECONDITION: both corpora.
        before = _state(posts, hubs)
        if before != recorded["expects"]:
            raise SystemExit(
                f"ERROR: stage {stage['id']!r} precondition failed.\n"
                f"       expects  {_fmt(recorded['expects'])}\n"
                f"       tree is  {_fmt(before)}\n"
                f"       Apply the upstream stages first — including any that touch only hubs."
            )
        _check_packet_identity(recorded)

        try:
            report = run_stage(stage, posts, hubs, applied_on)
        except ApplyError as exc:
            raise SystemExit(f"ABORT in stage {stage['id']!r}: {exc}\nNothing was written to disk.")

        # POSTCONDITION: both corpora, against what the manifest promised.
        after = _state(posts, hubs)
        if after != recorded["produces"]:
            raise SystemExit(
                f"ERROR: stage {stage['id']!r} did not produce its recorded output.\n"
                f"       expected {_fmt(recorded['produces'])}\n"
                f"       produced {_fmt(after)}\n"
                f"       Nothing was written to disk."
            )
        for entry in report["packets"].values():
            if entry.get("_staged_files"):
                staged_code.append(entry["_staged_files"])
        print(f"{stage['id']:18} "
              f"{ {n: {k: v for k, v in e.items() if not k.startswith('_')} for n, e in report['packets'].items()} }")
        print(f"{'':18} {_fmt(after)}  OK")

    # ── COMMIT: one transaction, or nothing ────────────────────────────────
    # Every resulting byte is computed first, then written under a journal with
    # rollback. Writing sequentially with no rollback left half-applied releases
    # under induced I/O failure: build.py changed while the next code file and
    # both content files stayed old, and all code plus posts.json changed while
    # category-hubs.json stayed old (operator review, 2026-07-30).
    payload: dict = {}
    for files in staged_code:
        payload.update(files)
    payload["content/posts.json"] = json.dumps(posts, indent=2, ensure_ascii=False)
    payload["content/category-hubs.json"] = json.dumps(hubs, indent=2, ensure_ascii=False)

    _commit_transaction(payload)

    # Re-validate from what is now ON DISK, under the code that is now on disk.
    # The journal is still live: any failure here rolls the whole thing back.
    import importlib
    try:
        importlib.reload(corpus_mod)
        if _FAIL_VALIDATION:
            raise SystemExit("injected post-write validation failure")
        _check_graph(load_posts())
        for name, text in payload.items():
            if (ROOT / name).read_text(encoding="utf-8") != text:
                raise SystemExit(f"{name} on disk does not match what was written")
    except SystemExit as exc:
        _rollback_from_journal(f"post-write validation failed: {exc}")
    _finalize_transaction()
    print(f"\nwrote {len(payload)} file(s) in one transaction")
    print("NOT built. Run the post-application suites, then ONE non-concurrent build.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--emit", action="store_true", help="compute and write the manifest")
    mode.add_argument("--verify", action="store_true", help="report where the tree is in the order")
    mode.add_argument("--apply", action="store_true", help="apply the stages, in order")
    mode.add_argument("--recover", action="store_true",
                      help="undo an interrupted transaction from its journal")
    ap.add_argument("--stage", help="apply only this stage id")
    ap.add_argument("--date", default=date.today().isoformat(),
                    help="the ACTUAL application date written to every changed record "
                         "(default: today). Never the packets' 2026-07-27 placeholder.")
    args = ap.parse_args()

    try:
        _iso_date(args.date)
    except (TypeError, ValueError):
        raise SystemExit(f"ERROR: --date {args.date!r} is not YYYY-MM-DD.")

    if args.emit:
        return cmd_emit(args.date)
    if args.recover:
        return cmd_recover()
    if args.verify:
        return cmd_verify()
    return cmd_apply(args.date, args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
