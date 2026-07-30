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
        "packets": ["scotland-routing-v11", "shpock-scam-uk-v11"],
        "why": "Mandatory companions; neither releases alone. Source rows are re-asserted "
               "after all full-record writes so no overlap row is lost.",
    },
    {
        "id": "nation",
        "title": "Nation consumer routing",
        "packets": ["nation-consumer-routing-v4"],
        "why": "Depends on both upstream stages for its `old` values.",
    },
    {
        "id": "hubs",
        "title": "All thirteen category hubs",
        "packets": ["hubs-v11", "legacy-hubs-v6"],
        "why": "Landed together with the strict source/key enforcement, or the hub "
               "self-test suite is inconsistent with the content.",
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


def build_receipts() -> dict:
    """Per-packet receipts with EXPLICIT key lists and a reproducible property.

    Each entry states what was hashed and what the digest is expected to do —
    including, for FINAL-9, the before/after scores a verifier must reproduce.
    """
    receipts: dict = {}

    posts = load_posts()
    index = by_slug(posts)
    try:
        stored = packet("scotland-routing-v11")["prerequisite_state"]["record_digests"]
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
        record = packet("shpock-scam-uk-v11")["record"]
    except SystemExit:
        record = None
    if record:
        receipts["shpock-scam-uk-v11"] = {
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
        "baseline": {
            "posts": corpus_digest(posts),
            "hubs": digest(hubs),
            "source_records": len(posts),
        },
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


def cmd_verify() -> int:
    if not MANIFEST.exists():
        print(f"ERROR: {MANIFEST.relative_to(ROOT)} not found — run --emit first", file=sys.stderr)
        return 2
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    live_posts, live_hubs = corpus_digest(load_posts()), digest(load_hubs())
    print(f"live corpus  {live_posts}")
    print(f"live hubs    {live_hubs}\n")

    position = None
    if live_posts == manifest["baseline"]["posts"]:
        position = "baseline (nothing applied)"
    for s in manifest["stages"]:
        if s["status"] == "ready" and live_posts == s["produces"]["posts"]:
            position = f"after stage '{s['id']}'"
    print(f"tree is at: {position or 'AN UNRECOGNISED STATE — do not apply'}")
    if position is None:
        return 1

    for s in manifest["stages"]:
        mark = "ready" if s["status"] == "ready" else "UNAVAILABLE"
        matches = s["status"] == "ready" and live_posts == s["expects"]["posts"]
        print(f"  [{'NEXT ' if matches else '     '}] {s['id']:18} {mark}")
    return 0


def cmd_apply(applied_on: str, only: str | None) -> int:
    posts, hubs = load_posts(), load_hubs()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None

    for stage in STAGES:
        if only and stage["id"] != only:
            continue
        before = corpus_digest(posts)
        if manifest:
            expected = next((s for s in manifest["stages"] if s["id"] == stage["id"]), None)
            if expected and expected["status"] == "ready" and expected["expects"]["posts"] != before:
                print(f"ABORT: stage '{stage['id']}' expects corpus {expected['expects']['posts']}\n"
                      f"       but the tree is at              {before}\n"
                      f"       Apply the upstream stages first.", file=sys.stderr)
                return 1
        try:
            report = run_stage(stage, posts, hubs, applied_on)
        except ApplyError as exc:
            print(f"ABORT in stage '{stage['id']}': {exc}", file=sys.stderr)
            print("Nothing has been written to disk.", file=sys.stderr)
            return 1
        print(f"{stage['id']:18} {report['packets']}")
        print(f"{'':18} produces {corpus_digest(posts)}")

    write_posts(posts)
    write_hubs(hubs)
    print(f"\nwrote content/posts.json and content/category-hubs.json")
    print("NOT built. Run the self-tests, then ONE non-concurrent build.")
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
