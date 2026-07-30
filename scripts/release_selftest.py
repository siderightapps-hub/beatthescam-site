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
touched.

The review packets are gitignored, so with them absent — the state GitHub
Actions receives — the suite builds SYNTHETIC packets (one content stage, one
code-patch stage) and runs every control against those. It used to print a SKIP
and return 0, executing zero assertions while CI reported green. A missing local
packet now changes WHAT is exercised, never WHETHER anything is; if the fixtures
cannot be built, that is a hard failure.

Offline: no API key, no network, no build.

    python3 scripts/release_selftest.py

RETIRED — ONE-OFF. This applied the 2026-07-30 accuracy release and is no longer
run by CI. Its self-test is explicitly PRE-application and fails from the applied
state by design, so leaving it in the workflow would have made CI permanently red
after the release landed.

The release's safety boundary is now Git plus the final CI suites plus the
committed dist/ snapshot, supported by the validators in corpus.py and canon.py —
not a bespoke local transaction engine. Kept for the audit trail: it records
exactly how the release was applied and what each stage produced.
"""
from __future__ import annotations

import json
import os
import re
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
    """A throwaway copy of everything the applier touches.

    Copied from the WORKING TREE, not `git archive HEAD`: the suite must test
    the code as it is now, and a clean extracted checkout has no .git to archive
    from — which made the whole suite fail to start in exactly the environment
    it most needs to run in.

    `dist/` is excluded: it is large and the applier never reads or writes it.
    """
    tmp = Path(tempfile.mkdtemp(prefix="release-selftest-"))
    for rel in ("scripts", "netlify", "content", ".github", "templates", "assets"):
        src = ROOT / rel
        if src.exists():
            shutil.copytree(src, tmp / rel)
    for name in ("package.json", ".gitignore"):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, tmp / name)
    (tmp / "docs").mkdir(exist_ok=True)
    if REVIEW.exists():
        shutil.copytree(REVIEW, tmp / "docs" / "review", dirs_exist_ok=True)
    return tmp


def run(tmp: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run([sys.executable, "scripts/release_manifest.py", *args],
                       cwd=tmp, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


DATE = "2026-07-30"


SYNTHETIC_STAGES = (
    "STAGES = [\n"
    '    {"id": "syn-content", "title": "Synthetic content", "why": "fixture",\n'
    '     "packets": ["synthetic-content-v1"]},\n'
    '    {"id": "syn-hubs", "title": "Synthetic hubs-only", "why": "fixture",\n'
    '     "packets": ["synthetic-hubs-v1"]},\n'
    '    {"id": "syn-code", "title": "Synthetic code patch", "why": "fixture",\n'
    '     "packets": ["synthetic-code-v1"]},\n'
    "]\n"
)


def synthesise_packets(tmp: Path) -> None:
    """Build a minimal, self-contained release inside the sandbox.

    The real packets are gitignored, so in a clean checkout — the state GitHub
    Actions receives — this suite printed a SKIP and returned 0, executing ZERO
    of its assertions while CI reported green (operator review, 2026-07-30).
    These fixtures make every control run everywhere, so a missing local packet
    downgrades WHAT is exercised, never WHETHER anything is.
    """
    review = tmp / "docs" / "review"
    review.mkdir(parents=True, exist_ok=True)
    posts = json.loads((tmp / "content" / "posts.json").read_text(encoding="utf-8"))

    # A content stage: one field mutation with an exact `old`.
    (review / "synthetic-content-v1.json").write_text(json.dumps({
        "packet_version": "synthetic-content-v1",
        "guides": {posts[0]["slug"]: {"hero": {"old": posts[0]["hero"],
                                               "new": posts[0]["hero"] + " (synthetic)"}}},
    }, ensure_ascii=False), encoding="utf-8")

    # A code-patch stage, so the code-receipt and transaction paths are covered.
    anchor = 'CONSOLIDATED_INTO = "consolidated_into"\n'
    corpus_text = (tmp / "scripts" / "corpus.py").read_text(encoding="utf-8")
    if corpus_text.count(anchor) != 1:
        raise SystemExit("ERROR: synthetic patch anchor not found in scripts/corpus.py — "
                         "the fixtures cannot be built, so the controls cannot run.")
    pending_now = {"hermes-parcel-scam-text-uk": "evri-delivery-scam-guide"} \
        if "hermes-parcel-scam-text-uk" in corpus_text else {}
    (review / "synthetic-code-v1.json").write_text(json.dumps({
        "packet_version": "synthetic-code-v1",
        "payload_shape": "record_field_add",
        "old_state_precondition": {"slug": posts[1]["slug"], "consolidated_into_absent": True},
        "change": {posts[1]["slug"]: {"add": {"_synthetic_marker": True}}},
        "code_patch": [{"file": "scripts/corpus.py", "why": "synthetic marker",
                        "old": anchor,
                        "new": anchor + "# synthetic release-selftest marker\n"}],
        "final_state": {"remove_static_redirects": [],
                        "pending_migration_after": pending_now},
    }, ensure_ascii=False), encoding="utf-8")

    # A HUBS-ONLY middle stage: it leaves the posts digest untouched, which is
    # the exact shape of the original skip-hubs bypass. Without it the clean-CI
    # fixture had only two stages, so both stage-skip assertions were guarded
    # out and CI never ran the highest-risk regression (operator review,
    # 2026-07-30).
    hubs = json.loads((tmp / "content" / "category-hubs.json").read_text(encoding="utf-8"))
    key = sorted(hubs)[0]
    patched = json.loads(json.dumps(hubs[key]))
    patched["intro"] = patched.get("intro", "") + "<p>Synthetic.</p>"
    (review / "synthetic-hubs-v1.json").write_text(json.dumps({
        "packet_version": "synthetic-hubs-v1",
        "hubs": {key: patched},
    }, ensure_ascii=False), encoding="utf-8")

    rm = tmp / "scripts" / "release_manifest.py"
    text = rm.read_text(encoding="utf-8")
    start = text.index("STAGES = [")
    end = text.index("\n]\n", start) + len("\n]\n")
    rm.write_text(text[:start] + SYNTHETIC_STAGES + text[end:], encoding="utf-8")


def main() -> int:
    real = bool(REVIEW.exists() and list(REVIEW.glob("*.json")))
    print(f"Fixtures: {'REAL packets (local)' if real else 'SYNTHETIC (clean checkout / CI)'}\n")

    tmp = sandbox()
    if not real:
        synthesise_packets(tmp)
    try:
        rc, out = run(tmp, "--emit", "--date", DATE)
        check("--emit succeeds against the packets", rc == 0, out[-400:])
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
        stage_ids = [x["id"] for x in manifest["stages"]]
        rc, out = run(tmp, "--verify")
        check("--verify reports the final stage afterwards",
              rc == 0 and f"after stage '{stage_ids[-1]}'" in out, out[-300:])

        # ── Controls, each in a fresh sandbox ───────────────────────────────
        def fresh():
            t = sandbox()
            if not real:
                synthesise_packets(t)
            run(t, "--emit", "--date", DATE)
            return t

        t = fresh()
        rc, out = run(t, "--apply", "--date", "not-a-date")
        check("a non-ISO --date is rejected", rc != 0 and "not YYYY-MM-DD" in out, out[-200:])
        shutil.rmtree(t, ignore_errors=True)

        # Basic form and ISO week dates are ALSO rejected: date.fromisoformat()
        # accepts both on 3.11+, so it was not enforcing the documented contract.
        for bad_date in ("20260730", "2026-W31-4"):
            t = fresh()
            rc, out = run(t, "--apply", "--date", bad_date)
            check(f"--date {bad_date!r} is rejected", rc != 0 and "not YYYY-MM-DD" in out,
                  out[-200:])
            shutil.rmtree(t, ignore_errors=True)
        t = fresh()
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
        pkt = t / "docs" / "review" / f"{manifest['stages'][0]['packets'][0]}.json"
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
        # Skipping a stage must block the one after it.
        # THE ORIGINAL REGRESSION: skip the hubs-shaped middle stage — the one
        # that leaves the posts digest untouched — and the stage after it must
        # refuse. Unconditional: every fixture set has at least three stages.
        t = fresh()
        check("the fixture has a skippable middle stage", len(stage_ids) >= 3,
              f"stages: {stage_ids}")
        for sid in stage_ids[:-2]:
            run(t, "--apply", "--stage", sid, "--date", DATE)
        rc, out = run(t, "--apply", "--stage", stage_ids[-1], "--date", DATE)
        check("skipping the hubs-shaped stage blocks the one after it",
              rc != 0 and ("precondition failed" in out or "expects code baseline" in out),
              out[-300:])
        check("...and the failure names the position, not just a digest",
              "Apply the upstream stages first" in out or "code" in out, out[-300:])
        rc, out = run(t, "--verify")
        check("--verify does not report the skipped stage as done",
              f"after stage '{stage_ids[-2]}'" not in out, out[-300:])
        shutil.rmtree(t, ignore_errors=True)

        # ── The STAGED workflow, end to end, ACROSS a code-patch stage ──────
        # `--stage hubs` patches build.py; the next command then rejected that
        # legitimate intermediate code state because only the global pre-release
        # digest was accepted (operator review, 2026-07-30).
        t = fresh()
        staged_ok = True
        for sid in stage_ids:
            rc, out = run(t, "--apply", "--stage", sid, "--date", DATE)
            if rc != 0:
                staged_ok = False
                check(f"staged workflow: --stage {sid} succeeds", False, out[-400:])
                break
        check("every stage applies individually, in order", staged_ok)
        if staged_ok:
            rc, out = run(t, "--verify")
            check("--verify accepts the fully staged result", rc == 0, out[-300:])
        shutil.rmtree(t, ignore_errors=True)

        # ── REAL late-failure injection ─────────────────────────────────────
        # Making content/ unwritable always failed on the FIRST temp file, so
        # both "late failure" tests proved only that nothing had been written
        # yet — they exercised no rollback (operator review, 2026-07-30). The
        # applier now honours RELEASE_SELFTEST_FAIL_AFTER=<n> (raise after n
        # replacements) and RELEASE_SELFTEST_FAIL_VALIDATION=1 (fail the
        # post-write on-disk validation), so failures land exactly where needed.
        def run_env(t, env, *args):
            e = dict(os.environ); e.update(env)
            r = subprocess.run([sys.executable, "scripts/release_manifest.py", *args],
                               cwd=t, capture_output=True, text=True, env=e)
            return r.returncode, (r.stdout + r.stderr)

        # The watched set is DERIVED from the transaction's own journal, so it
        # cannot silently omit a file the release writes. A hard-coded five-path
        # list omitted scripts/corpus_selftest.py, and disabling restoration for
        # that file still passed every "every byte" assertion (operator review,
        # 2026-07-30).
        t_probe = fresh()
        run_env(t_probe, {"RELEASE_SELFTEST_FAIL_AFTER": "0"}, "--apply", "--date", DATE)
        jp = t_probe / ".release-journal.json"
        watched = tuple(sorted(json.loads(jp.read_text())["writing"])) if jp.exists() else ()
        if not watched:
            _, probe_out = run_env(t_probe, {"RELEASE_SELFTEST_LEAVE_JOURNAL": "1"},
                                   "--apply", "--date", DATE)
            watched = tuple(sorted(json.loads(jp.read_text())["writing"])) if jp.exists() else ()
        shutil.rmtree(t_probe, ignore_errors=True)
        check("the watched set is derived from the transaction, not hard-coded",
              len(watched) >= 2, f"watched={watched}")

        def snapshot(t):
            return {f: ((t / f).read_bytes(), (t / f).stat().st_mode)
                    for f in watched if (t / f).exists()}

        # How many files does THIS release actually write? Injection points must
        # land inside the write loop; the watched-file count is not the same
        # number, and using it silently pushed two injections past the end so
        # the run succeeded and the test compared a legitimately changed tree.
        t0 = fresh()
        _, out0 = run_env(t0, {}, "--apply", "--date", DATE)
        m = re.search(r"wrote (\d+) file\(s\)", out0)
        n_writes = int(m.group(1)) if m else 0
        shutil.rmtree(t0, ignore_errors=True)
        check("the release writes at least two files (so injection is meaningful)",
              n_writes >= 2, f"writes={n_writes}")

        points = [("after the FIRST replacement", 1)]
        if n_writes >= 3:
            points.append(("mid-way through the replacements", n_writes // 2))
        points.append(("before the LAST replacement", n_writes - 1))
        points.append(("after ALL replacements", n_writes))

        for label, fail_after in [(l, str(n)) for l, n in points]:
            t = fresh()
            before = snapshot(t)
            rc, out = run_env(t, {"RELEASE_SELFTEST_FAIL_AFTER": fail_after},
                              "--apply", "--date", DATE)
            after = snapshot(t)
            changed = sorted(f for f in before if before[f][0] != after.get(f, (None,))[0])
            modes = sorted(f for f in before if before[f][1] != after.get(f, (None, None))[1])
            check(f"a failure {label} rolls every byte back",
                  rc != 0 and not changed, f"exit={rc}; changed: {changed}")
            check(f"a failure {label} restores every mode", not modes, f"modes changed: {modes}")
            check(f"a failure {label} leaves no journal",
                  not (t / ".release-journal.json").exists())
            check(f"a failure {label} leaves no temp files",
                  not list(t.rglob("*.release-tmp")))
            shutil.rmtree(t, ignore_errors=True)

        # Failure AFTER every write, during the on-disk validation — the case
        # that used to leave the tree fully mutated with the journal deleted.
        t = fresh()
        before = snapshot(t)
        rc, out = run_env(t, {"RELEASE_SELFTEST_FAIL_VALIDATION": "1"}, "--apply", "--date", DATE)
        after = snapshot(t)
        changed = sorted(f for f in before if before[f][0] != after.get(f, (None,))[0])
        modes = sorted(f for f in before if before[f][1] != after.get(f, (None, None))[1])
        check("a POST-WRITE validation failure rolls everything back",
              rc != 0 and not changed, f"exit={rc}; changed: {changed}")
        check("...and restores every mode", not modes, f"modes changed: {modes}")
        check("...and leaves no journal", not (t / ".release-journal.json").exists())
        check("...and leaves no temp files", not list(t.rglob("*.release-tmp")))
        shutil.rmtree(t, ignore_errors=True)

        # ── A name-sensitive corpus.py failure ──────────────────────────────
        # Compile-valid, passes the staged import under its production name only
        # if that import really uses the production name. Proves automatic
        # rollback AND that a fresh --recover process can still start.
        t = fresh()
        cp = t / "scripts" / "corpus.py"
        cp.write_text(cp.read_text(encoding="utf-8")
                      + '\nif __name__ == "corpus":\n'
                        '    raise RuntimeError("name-sensitive failure fixture")\n',
                      encoding="utf-8")
        before = snapshot(t)          # AFTER injecting the fixture, not before
        rc, out = run_env(t, {}, "--emit", "--date", DATE)
        rc, out = run_env(t, {}, "--apply", "--date", DATE)
        after = snapshot(t)
        changed = sorted(f for f in before if before[f][0] != after.get(f, (None,))[0])
        check("a name-sensitive corpus.py failure is caught BEFORE any write",
              rc != 0 and not changed, f"exit={rc}; changed: {changed}")
        check("...and --recover can still start afterwards",
              run(t, "--recover")[0] == 0)
        shutil.rmtree(t, ignore_errors=True)

        # ── Pre-existing MODE drift must invalidate the baseline ────────────
        t = fresh()
        victim = t / "scripts" / "hub_selftest.py"
        victim.chmod(0o644)
        rc, out = run_env(t, {}, "--apply", "--date", DATE)
        check("a mode change with identical bytes invalidates the code baseline",
              rc != 0 and "release-critical code has changed" in out, out[-250:])
        shutil.rmtree(t, ignore_errors=True)

        # ── A false but well-formed final code receipt ──────────────────────
        t = fresh()
        mp = t / "docs" / "review" / "release-manifest.json"
        m2 = json.loads(mp.read_text(encoding="utf-8"))
        m2["stages"][-1]["code_produces"] = "0" * 64
        m2["code_baseline_after"]["digest"] = "0" * 64
        mp.write_text(json.dumps(m2, indent=2, ensure_ascii=False), encoding="utf-8")
        before = snapshot(t)
        rc, out = run_env(t, {}, "--apply", "--date", DATE)
        after = snapshot(t)
        changed = sorted(f for f in before if before[f][0] != after.get(f, (None,))[0])
        check("a well-formed but FALSE final code receipt is rejected before any write",
              rc != 0 and not changed, f"exit={rc}; changed: {changed}")
        shutil.rmtree(t, ignore_errors=True)

        # ── Modes survive a SUCCESSFUL release ──────────────────────────────
        t = fresh()
        before = snapshot(t)
        rc, out = run_env(t, {}, "--apply", "--date", DATE)
        after = snapshot(t)
        modes = sorted(f for f in before if before[f][1] != after.get(f, (None, None))[1])
        check("a SUCCESSFUL release preserves every file mode", rc == 0 and not modes,
              f"exit={rc}; modes changed: {modes}")
        check("...and leaves no journal or temp files",
              not (t / ".release-journal.json").exists() and not list(t.rglob("*.release-tmp")))
        shutil.rmtree(t, ignore_errors=True)

        # ── An unresolved journal must block everything but --recover ───────
        t = fresh()
        (t / ".release-journal.json").write_text(json.dumps(
            {"snapshot": {}, "writing": []}), encoding="utf-8")
        for mode in ("--verify", "--emit", "--apply"):
            rc, out = run(t, mode, *(["--date", DATE] if mode != "--verify" else []))
            check(f"{mode} refuses while a transaction journal exists",
                  rc != 0 and "unresolved transaction journal" in out, out[-200:])
        rc, out = run(t, "--recover")
        check("--recover clears the journal", rc == 0
              and not (t / ".release-journal.json").exists(), out[-200:])
        shutil.rmtree(t, ignore_errors=True)

        # ── --recover restores bytes AND modes ──────────────────────────────
        t = fresh()
        before = snapshot(t)
        run_env(t, {"RELEASE_SELFTEST_FAIL_AFTER": "0"}, "--apply", "--date", DATE)
        # Re-run with an interruption that leaves the journal in place.
        rc, out = run_env(t, {"RELEASE_SELFTEST_LEAVE_JOURNAL": "1"}, "--apply", "--date", DATE)
        check("an interrupted run LEAVES its journal", (t / ".release-journal.json").exists())
        rc, out = run(t, "--recover")
        after = snapshot(t)
        changed = sorted(f for f in before if before[f] != after.get(f))
        check("--recover restores bytes and modes exactly", rc == 0 and not changed,
              f"changed: {changed}")
        check("--recover leaves no temp files", not list(t.rglob("*.release-tmp")))
        shutil.rmtree(t, ignore_errors=True)

        # ── A code_patch that disagrees with its final_state ────────────────
        t = fresh()
        code_stage = next((x for x in manifest["stages"]
                           if any("_code_patch" in str(v) or "code_patch_files" in v
                                  for v in (x.get("applied") or {}).values())), None)
        if code_stage:
            pp = t / "docs" / "review" / f"{code_stage['packets'][0]}.json"
            data = json.loads(pp.read_text(encoding="utf-8"))
            data.setdefault("final_state", {})["remove_static_redirects"] = ["not-touched-by-patch"]
            pp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            run(t, "--emit", "--date", DATE)
            before = (t / "content" / "posts.json").read_bytes()
            rc, out = run(t, "--apply", "--date", DATE)
            check("a code_patch disagreeing with final_state aborts before any write",
                  rc != 0 and (t / "content" / "posts.json").read_bytes() == before, out[-300:])
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

        # A code patch whose `old` text has MOVED must abort, not half-apply.
        # Targets whatever anchor the release's own patch uses, so this works for
        # the real packets and the synthetic fixture alike.
        t = fresh()
        anchor = None
        for entry in manifest["stages"]:
            if entry.get("status") != "ready":
                continue
            for name in entry.get("packets", []):
                data = json.loads((t / "docs" / "review" / f"{name}.json").read_text(encoding="utf-8"))
                for cp in data.get("code_patch") or []:
                    anchor = (cp["file"], cp["old"])
                    break
                if anchor:
                    break
            if anchor:
                break
        if anchor:
            f = t / anchor[0]
            text = f.read_text(encoding="utf-8")
            f.write_text(text.replace(anchor[1], anchor[1].rstrip("\n") + "  # moved\n", 1),
                         encoding="utf-8")
            run(t, "--emit", "--date", DATE)
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
