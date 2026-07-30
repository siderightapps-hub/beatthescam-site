#!/usr/bin/env python3
"""
release_selftest.py — exercises release_manifest.py's control paths.

CI watched `release_manifest.py` but never ran it. Every control it advertises
— paired {posts, hubs} preconditions, packet identity, the code baseline, ISO
dates, stage schema, final graph validity — was asserted in prose and verified
only by hand. A suite that actually executed the applier would have caught the
consolidation stage being impossible to apply at all (operator review,
2026-07-30, `hubs-v12-c.md` §6 and `consolidation-metadata-v2-c.md` §10).

Every case runs in a THROWAWAY COPY of the repository, so the real
content/posts.json, content/category-hubs.json, scripts/ and dist/ are never
touched. Cases that need the review packets are skipped when docs/review/ is
absent (it is gitignored), and the suite says so rather than passing silently.

Offline: no API key, no network, no build.

    python3 scripts/release_selftest.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "docs" / "review"

FAILURES: list[str] = []
SKIPPED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def sandbox() -> Path:
    """A copy of the repo with the (gitignored) review packets included."""
    tmp = Path(tempfile.mkdtemp(prefix="release-selftest-"))
    subprocess.run(["git", "archive", "HEAD"], cwd=ROOT, check=True,
                   stdout=(tmp / "t.tar").open("wb"))
    subprocess.run(["tar", "-xf", "t.tar"], cwd=tmp, check=True)
    (tmp / "t.tar").unlink()
    # Uncommitted working-tree state matters: the suite must test the code as it
    # is now, not as it was at HEAD.
    for rel in ("scripts", "netlify", "content", ".github"):
        if (ROOT / rel).exists():
            shutil.rmtree(tmp / rel, ignore_errors=True)
            shutil.copytree(ROOT / rel, tmp / rel)
    if REVIEW.exists():
        shutil.copytree(REVIEW, tmp / "docs" / "review", dirs_exist_ok=True)
    return tmp


def run(tmp: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, "scripts/release_manifest.py", *args],
                       cwd=tmp, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


DATE = "2026-07-30"


def main() -> int:
    if not REVIEW.exists() or not list(REVIEW.glob("*.json")):
        print("SKIP  docs/review/ is absent (it is gitignored) — the manifest control paths")
        print("      cannot be exercised without the packets. This is not a pass.")
        return 0

    tmp = sandbox()
    try:
        rc, out = run(tmp, "--emit", "--date", DATE)
        check("--emit succeeds against the reviewed packets", rc == 0, out[-400:])
        manifest_path = tmp / "docs" / "review" / "release-manifest.json"
        check("--emit writes a manifest", manifest_path.exists())
        if not manifest_path.exists():
            return 1
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Every recorded stage must be applicable. A stage recorded `ready` that
        # cannot be applied is the exact defect this suite exists for.
        statuses = {s["id"]: s["status"] for s in manifest["stages"]}
        check("every recorded stage is ready (none INVALID)",
              all(v == "ready" for v in statuses.values()), str(statuses))

        # ── The whole release, end to end ───────────────────────────────────
        rc, out = run(tmp, "--apply", "--date", DATE)
        check("the COMPLETE release applies through the tool", rc == 0, out[-600:])
        rc, out = run(tmp, "--verify")
        check("--verify reports the final stage afterwards",
              rc == 0 and "after stage 'consolidation'" in out, out[-300:])

        # ── Controls, each in a fresh sandbox ───────────────────────────────
        def fresh():
            t = sandbox()
            run(t, "--emit", "--date", DATE)
            return t

        t = fresh()
        rc, out = run(t, "--apply", "--date", "not-a-date")
        check("a non-ISO --date is rejected", rc != 0 and "not an ISO date" in out, out[-200:])
        shutil.rmtree(t, ignore_errors=True)

        t = fresh()
        rc, out = run(t, "--apply", "--date", "2026-08-01")
        check("a --date differing from the manifest is rejected",
              rc != 0 and "different release" in out, out[-200:])
        shutil.rmtree(t, ignore_errors=True)

        t = fresh()
        rc, out = run(t, "--apply", "--stage", "bogus", "--date", DATE)
        check("an unknown --stage is rejected", rc != 0 and "unknown stage" in out, out[-200:])
        shutil.rmtree(t, ignore_errors=True)

        # A bogus stage INSIDE the manifest must not be honoured either.
        t = fresh()
        mp = t / "docs" / "review" / "release-manifest.json"
        m = json.loads(mp.read_text(encoding="utf-8"))
        m["stages"].append({"id": "bogus", "title": "x", "why": "x", "status": "ready",
                            "packets": [], "packet_digests": {},
                            "expects": m["baseline"], "produces": m["baseline"]})
        mp.write_text(json.dumps(m), encoding="utf-8")
        rc, out = run(t, "--apply", "--stage", "bogus", "--date", DATE)
        check("a bogus stage injected into the manifest is rejected",
              rc != 0 and ("unknown stage" in out or "not a prefix" in out), out[-250:])
        shutil.rmtree(t, ignore_errors=True)

        t = fresh()
        (t / "docs" / "review" / "release-manifest.json").unlink()
        rc, out = run(t, "--apply", "--date", DATE)
        check("a MISSING manifest aborts instead of applying unchecked",
              rc != 0 and "not found" in out, out[-200:])
        shutil.rmtree(t, ignore_errors=True)

        # Packet identity.
        t = fresh()
        pkt = t / "docs" / "review" / "FINAL-9-guides-v4.json"
        data = json.loads(pkt.read_text(encoding="utf-8"))
        data["_tampered"] = True
        pkt.write_text(json.dumps(data), encoding="utf-8")
        rc, out = run(t, "--apply", "--date", DATE)
        check("an edited packet is rejected before mutation",
              rc != 0 and "has changed since the manifest" in out, out[-250:])
        rc, out = run(t, "--verify")
        check("--verify EXITS NONZERO on packet drift", rc != 0 and "DRIFT" in out, out[-250:])
        shutil.rmtree(t, ignore_errors=True)

        # Code baseline — including a file the old eight-file digest missed.
        for target in ("netlify/functions/lib/allowed-domains.js", "scripts/corpus.py"):
            t = fresh()
            f = t / target
            probe = "# baseline probe\n" if target.endswith(".py") else "// baseline probe\n"
            f.write_text(f.read_text(encoding="utf-8") + "\n" + probe, encoding="utf-8")
            rc, out = run(t, "--apply", "--date", DATE)
            check(f"editing {target} invalidates the code baseline",
                  rc != 0 and "release-critical code has changed" in out, out[-250:])
            shutil.rmtree(t, ignore_errors=True)

        # Paired precondition: the hubs half cannot be skipped.
        t = fresh()
        for sid in ("final9", "scotland-shpock", "nation"):
            run(t, "--apply", "--stage", sid, "--date", DATE)
        rc, out = run(t, "--apply", "--stage", "consolidation", "--date", DATE)
        check("skipping the hubs stage blocks consolidation",
              rc != 0 and "precondition failed" in out, out[-300:])
        check("...and the failure names the hubs digest, not just posts",
              "hubs" in out, out[-300:])
        rc, out = run(t, "--verify")
        check("--verify does NOT report 'after hubs' when only posts match",
              "after stage 'hubs'" not in out, out[-300:])
        shutil.rmtree(t, ignore_errors=True)

        # Content drift under the applier's feet.
        t = fresh()
        posts_path = t / "content" / "posts.json"
        posts = json.loads(posts_path.read_text(encoding="utf-8"))
        posts[0]["hero"] = posts[0].get("hero", "") + " drifted"
        posts_path.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")
        rc, out = run(t, "--apply", "--date", DATE)
        check("a corpus that drifted after --emit is rejected",
              rc != 0 and "precondition failed" in out, out[-300:])
        shutil.rmtree(t, ignore_errors=True)

        # Nothing is written when a stage aborts.
        t = fresh()
        before = (t / "content" / "posts.json").read_bytes()
        run(t, "--apply", "--date", "2026-08-02")
        check("an aborted run writes nothing to posts.json",
              (t / "content" / "posts.json").read_bytes() == before)
        shutil.rmtree(t, ignore_errors=True)

        # A code patch that no longer matches must abort, not half-apply.
        t = fresh()
        cp = t / "scripts" / "corpus.py"
        cp.write_text(cp.read_text(encoding="utf-8").replace(
            'PENDING_MIGRATION = {"hermes-parcel-scam-text-uk": "evri-delivery-scam-guide"}',
            'PENDING_MIGRATION = {"hermes-parcel-scam-text-uk": "evri-delivery-scam-guide"}  # moved'),
            encoding="utf-8")
        rc, out = run(t, "--emit", "--date", DATE)
        rc, out = run(t, "--apply", "--date", DATE)
        check("a code patch whose `old` text has moved aborts the release",
              rc != 0, out[-300:])
        shutil.rmtree(t, ignore_errors=True)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All release-manifest control self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
