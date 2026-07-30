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
import sys
from datetime import date
from pathlib import Path

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

def apply_full_records(posts: list, records: list, applied_on: str) -> int:
    """FINAL-9 and Shpock: replace the listed fields of an existing record."""
    index = by_slug(posts)
    for rec in records:
        slug = rec["slug"]
        live = index.get(slug)
        if live is None:
            raise ApplyError(f"{slug}: no such live record")
        for key, value in rec.items():
            if key == "slug":
                continue
            live[key] = copy.deepcopy(value)
        live["updated"] = applied_on
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
        "packets": ["scotland-routing-v12", "shpock-scam-uk-v12"],
        "why": "Mandatory companions; neither releases alone. Source rows are re-asserted "
               "after all full-record writes so no overlap row is lost.",
    },
    {
        "id": "nation",
        "title": "Nation consumer routing",
        "packets": ["nation-consumer-routing-v6"],
        "why": "Depends on both upstream stages for its `old` values.",
    },
    {
        "id": "hubs",
        "title": "All thirteen category hubs",
        "packets": ["hubs-v12", "legacy-hubs-v7"],
        "why": "Landed together with the strict source/key enforcement, or the hub "
               "self-test suite is inconsistent with the content.",
    },
    {
        "id": "consolidation",
        "title": "Consolidation metadata",
        "packets": ["consolidation-metadata-v2"],
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
            entry["records_replaced"] = apply_full_records(posts, [data["record"]], applied_on)
        if data.get("payload_shape") == "record_field_add":
            entry.update(apply_record_fields(posts, data["change"],
                                             data["old_state_precondition"]))
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


def code_baseline() -> dict:
    """A digest over the release-critical code, plus the commit it was taken at.

    `minimum_code_commit` in the packets is descriptive: nothing read it, so
    updating the string protected nothing (operator review, 2026-07-30). This is
    a checked precondition — `--apply` refuses to run against code that is not
    the code the manifest was emitted from.
    """
    import subprocess
    files = ["scripts/canon.py", "scripts/corpus.py", "scripts/content_gate.py",
             "scripts/build.py", "scripts/release_manifest.py",
             "scripts/hub_selftest.py", "scripts/corpus_selftest.py",
             "scripts/gate_quickanswer_selftest.py"]
    blobs = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}
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
        stored = packet("scotland-routing-v12")["prerequisite_state"]["record_digests"]
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
        record = packet("shpock-scam-uk-v12")["record"]
    except SystemExit:
        record = None
    if record:
        receipts["shpock-scam-uk-v12"] = {
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
        "receipts": build_receipts(),
        "stages": [],
    }

    for stage in STAGES:
        expects_posts, expects_hubs = corpus_digest(posts), digest(hubs)
        try:
            report = run_stage(stage, posts, hubs, applied_on)
        except (ApplyError, SystemExit) as exc:
            manifest["stages"].append({
                "id": stage["id"], "title": stage["title"], "why": stage["why"],
                "status": "UNAVAILABLE", "reason": str(exc),
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
            "applied": report["packets"],
        })

    return manifest


def cmd_emit(applied_on: str) -> int:
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
    for key in ("digest_spec", "baseline", "stages", "generated_for_application_date"):
        if key not in manifest:
            raise SystemExit(f"ERROR: {MANIFEST.relative_to(ROOT)} has no {key!r} — regenerate it")
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


def cmd_verify() -> int:
    manifest = _require_manifest()
    live = _state(load_posts(), load_hubs())
    print(f"live  {_fmt(live)}")
    same_code = code_baseline()["digest"] == manifest.get("code_baseline", {}).get("digest")
    print("code  " + ("matches the manifest baseline" if same_code else
                      "DIFFERS from the manifest baseline — re-run --emit") + "\n")

    position, matched = None, None
    if live == manifest["baseline"]:
        position = "baseline (nothing applied)"
    for s in manifest["stages"]:
        if s["status"] == "ready" and live == s["produces"]:
            position, matched = f"after stage '{s['id']}'", s

    if position is None:
        print("tree is at: AN UNRECOGNISED STATE — do not apply.")
        print("            Both digests must match a recorded state. A partial application, an")
        print("            edited packet or a different --date all produce an unknown state.")
        for s in manifest["stages"]:
            if s["status"] != "ready":
                continue
            same_posts = live["posts"] == s["produces"]["posts"]
            same_hubs = live["hubs"] == s["produces"]["hubs"]
            if same_posts != same_hubs:
                print(f"            NOTE stage {s['id']!r}: "
                      f"posts {'match' if same_posts else 'differ'}, "
                      f"hubs {'match' if same_hubs else 'differ'} — a half-applied stage.")
        return 1

    print(f"tree is at: {position}")
    try:
        _check_graph(load_posts())
        print("            consolidation graph: valid")
    except SystemExit as exc:
        print(f"            {exc}")
        return 1

    for s in manifest["stages"]:
        mark = "ready" if s["status"] == "ready" else "UNAVAILABLE"
        nxt = s["status"] == "ready" and live == s["expects"]
        print(f"  [{'NEXT ' if nxt else '     '}] {s['id']:18} {mark}")
    return 0


def cmd_apply(applied_on: str, only: str | None) -> int:
    manifest = _require_manifest()

    if manifest["generated_for_application_date"] != applied_on:
        raise SystemExit(
            f"ERROR: the manifest was generated for {manifest['generated_for_application_date']} "
            f"but --date is {applied_on}. Stage outputs include `updated`, so a different date "
            f"is a different release. Re-run --emit with this date."
        )

    live_code = code_baseline()
    if live_code["digest"] != manifest.get("code_baseline", {}).get("digest"):
        raise SystemExit(
            f"ERROR: the release-critical code has changed since the manifest was emitted.\n"
            f"       manifest: {manifest.get('code_baseline', {}).get('digest')}\n"
            f"       on disk:  {live_code['digest']}\n"
            f"       Re-run --emit, or restore the reviewed code."
        )

    known = {s["id"] for s in manifest["stages"]}
    if only and only not in known:
        raise SystemExit(f"ERROR: unknown stage {only!r}. Known stages: {', '.join(sorted(known))}")

    posts, hubs = load_posts(), load_hubs()

    for stage in STAGES:
        if only and stage["id"] != only:
            continue
        recorded = next((s for s in manifest["stages"] if s["id"] == stage["id"]), None)
        if recorded is None or recorded["status"] != "ready":
            raise SystemExit(
                f"ERROR: stage {stage['id']!r} is not recorded as ready in the manifest"
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
        print(f"{stage['id']:18} {report['packets']}")
        print(f"{'':18} {_fmt(after)}  OK")

    _check_graph(posts)
    write_posts(posts)
    write_hubs(hubs)
    print("\nwrote content/posts.json and content/category-hubs.json")
    print("NOT built. Run the five checks, then ONE non-concurrent build.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--emit", action="store_true", help="compute and write the manifest")
    mode.add_argument("--verify", action="store_true", help="report where the tree is in the order")
    mode.add_argument("--apply", action="store_true", help="apply the stages, in order")
    ap.add_argument("--stage", help="apply only this stage id")
    ap.add_argument("--date", default=date.today().isoformat(),
                    help="the ACTUAL application date written to every changed record "
                         "(default: today). Never the packets' 2026-07-27 placeholder.")
    args = ap.parse_args()

    if args.emit:
        return cmd_emit(args.date)
    if args.verify:
        return cmd_verify()
    return cmd_apply(args.date, args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
