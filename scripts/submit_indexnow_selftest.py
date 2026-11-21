#!/usr/bin/env python3
"""Offline tests of the publication guard, immutable dist binding and URL delta."""

import contextlib
import copy
import hashlib
import importlib.util
import io
import re
import stat
import sys
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch


DENIED_EVENTS = []


def offline(event, args):
    if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.posix_spawn"}:
        DENIED_EVENTS.append(event)
        raise AssertionError("external I/O forbidden in publication safety tests")


sys.addaudithook(offline)
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("submit_indexnow", HERE / "submit_indexnow.py")
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)

KEY_FILE = app.KEY + ".txt"
A, B, C = "a" * 24, "b" * 24, "c" * 24
NOW = 1_800_000_000
HIDDEN = b"<META content='follow, NOINDEX' name=robots>"
BASE = {KEY_FILE: app.KEY.encode(), "404.html": b"old error", "index.html": b"unchanged",
        "guides/stay/index.html": b"old", "guides/gone/index.html": b"deleted",
        "guides/old/index.html": b"renamed", "private/index.html": HIDDEN,
        "hidden-now.html": b"old public", "visible-now.html": HIDDEN}
NEXT = {KEY_FILE: app.KEY.encode(), "404.html": b"new error", "index.html": b"unchanged",
        "guides/stay/index.html": b"new", "guides/add/index.html": b"added",
        "guides/new/index.html": b"renamed", "private/index.html": HIDDEN + b"text",
        "hidden-now.html": HIDDEN, "visible-now.html": b"public"}


def archive(files, modes=None):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for path, body in files.items():
            info = zipfile.ZipInfo(path)
            info.create_system = 3
            mode = (modes or {}).get(path, stat.S_IFREG | 0o644)
            info.external_attr = mode << 16
            z.writestr(info, body)
    return out.getvalue()


class Objects:
    """Synthetic raw Git objects; no Git process, filesystem repo or commit operation."""

    def __init__(self):
        self.data = {}

    def add(self, kind, data):
        key = hashlib.sha1(b"%s %d\0" % (kind, len(data)) + data).hexdigest()
        self.data[key] = (kind, data)
        return key

    def tree(self, entries):
        rows = sorted(entries, key=lambda row: row[1] + ("/" if row[0] == "40000" else ""))
        raw = b"".join(m.encode() + b" " + n.encode() + b"\0" + bytes.fromhex(k)
                       for m, n, k in rows)
        return self.add(b"tree", raw)

    def revision(self, files, source):
        nested = {}
        for path, data in files.items():
            parts = path.split("/")
            node = nested
            for component in parts[:-1]:
                node = node.setdefault(component, {})
            node[parts[-1]] = data

        def build(node):
            return self.tree([("40000", name, build(value)) if isinstance(value, dict)
                              else ("100644", name, self.add(b"blob", value))
                              for name, value in node.items()])

        root = self.tree([("40000", "dist", build(nested)),
                          ("100644", "source", self.add(b"blob", source))])
        return self.add(b"commit", b"tree " + root.encode() + b"\n\nsynthetic\n")


class Window:
    def __init__(self, capture, decision):
        self.capture = capture
        self.decision = decision
        self.held = False
        self.available = True

    def require_exclusive(self):
        if not self.held or not self.available:
            raise app.Hold("controlled window unavailable")


class Boundary:
    """Only boundary replaced: attributed operator record, provider, object store, clock and POST."""

    def __init__(self, old=BASE, new=NEXT, restore=False):
        self.objects = Objects()
        a = app.Target(A, self.objects.revision(old, b"before"))
        b = app.Target(B, self.objects.revision(new, b"after"))
        self.reads = []
        self.before, self.after = (b, a) if restore else (a, b)
        self.clock = NOW
        self.live = app.SiteRead(app.SITE, app.HOST, app.REPOSITORY, self.after, False, NOW)
        capture = replace(self.live, published=self.before, at=NOW - 20)
        self.window = Window(capture, app.Decision(app.SITE, self.before, self.after, NOW - 5, NOW + 30))
        self.journal = (app.Publication(self.before, self.after, NOW - 10),)
        self.deploys = {x.deploy: app.DeployRead(app.SITE, x, "production", "main", "ready", NOW)
                       for x in (a, b)}
        self.archives = {A: archive(old), B: archive(new)}
        self.on_final = None
        self.site_reads = 0
        self.attempts = []
        self.response = 202

    @contextlib.contextmanager
    def controlled_window(self):
        self.window.held = True
        try:
            yield self.window
        finally:
            self.window.held = False

    def now(self):
        return self.clock

    def site(self, site):
        assert site == app.SITE
        self.site_reads += 1
        if self.site_reads == 2 and self.on_final:
            self.on_final()
        return self.live

    def deploy(self, site, name):
        assert site == app.SITE
        return self.deploys[name]

    def publications(self, site, start, end):
        assert site == app.SITE and (start, end) == (self.window.capture.at, self.live.at)
        return self.journal

    def git_object(self, repo, oid):
        assert repo == app.REPOSITORY
        self.reads.append(oid)
        return self.objects.data[oid]

    def published_archive(self, site, deploy):
        assert site == app.SITE
        return self.archives[deploy]

    def post(self, endpoint, payload):
        self.attempts.append((endpoint, copy.deepcopy(payload)))
        self.window.require_exclusive()
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class Safety(unittest.TestCase):
    def tearDown(self):
        self.assertEqual(DENIED_EVENTS, [])

    def held(self, b):
        with self.assertRaises(app.Hold):
            app.notify(b)
        self.assertEqual(b.attempts, [])
        self.assertFalse(b.window.held)

    def positive(self, b, paths):
        urls = sorted("https://beatthescam.com/" + path for path in paths)
        self.assertEqual(app.notify(b), urls)
        self.assertEqual(b.attempts, [("https://api.indexnow.org/indexnow", {
            "host": "beatthescam.com", "key": "b3c8e1f2a94d7056",
            "keyLocation": "https://beatthescam.com/b3c8e1f2a94d7056.txt", "urlList": urls})])
        self.assertEqual(b.site_reads, 2)
        self.assertFalse(b.window.held)

    def test_actual_publish_with_skipped_revision(self):
        b = Boundary()
        skipped = b.objects.revision({**BASE, "unshipped.html": b"never published"}, b"skip")
        self.positive(b, ["guides/add/", "guides/gone/", "guides/new/", "guides/old/",
                          "guides/stay/", "visible-now.html"])
        self.assertNotIn(skipped, b.reads)

    def test_actual_restore_inverse_public_delta(self):
        self.positive(Boundary(restore=True), ["guides/add/", "guides/gone/", "guides/new/",
                                               "guides/old/", "guides/stay/", "hidden-now.html"])

    def test_source_only_forward_reverse_and_non_html_delta(self):
        for b in (Boundary(new=BASE), Boundary(new=BASE, restore=True),
                  Boundary(new={**BASE, "asset.css": b"changed"})):
            self.assertNotEqual(b.before.commit, b.after.commit)
            self.assertEqual(app.notify(b), [])
            self.assertEqual(b.attempts, [])

    def test_unshipped_main_and_unexecuted_restore(self):
        for b in (Boundary(), Boundary(restore=True)):
            b.live = replace(b.live, published=b.before)
            self.held(b)

    def test_ready_behind_lock_and_ambiguous_lock(self):
        for lock in (True, None, 0):
            b = Boundary()
            b.live = replace(b.live, locked=lock)
            self.held(b)

    def test_failed_preview_branch_and_wrong_deploy_commit(self):
        for changes in ({"state": "error"}, {"context": "deploy-preview"}, {"branch": "other"},
                        {"site": "wrong"}, {"target": app.Target(C, "f" * 40)},
                        {"target": app.Target(B, "f" * 40)}, {"at": NOW - 61}):
            for key in (A, B):
                b = Boundary()
                b.deploys[key] = replace(b.deploys[key], **changes)
                self.held(b)

    def test_site_identity_capture_approval_and_credential(self):
        for changes in ({"domain": "example.com"}, {"site": "wrong"}, {"repository": "wrong"},
                        {"at": NOW - 61}, {"at": NOW + 10}):
            b = Boundary()
            b.live = replace(b.live, **changes)
            self.held(b)
        for changes in ({"before": app.Target("short", "f" * 40)}, {"after": app.Target(B, "abc")},
                        {"expires": NOW}, {"site": "wrong"}, {"at": NOW - 30}):
            b = Boundary()
            b.window.decision = replace(b.window.decision, **changes)
            self.held(b)
        for capture in (None, "caller supplied approval"):
            b = Boundary()
            b.window.capture = capture
            self.held(b)
        b = Boundary()
        b.window.capture = replace(b.window.capture, at=NOW - 901)
        self.held(b)
        for denied in ("expired", "unavailable"):
            b = Boundary()
            with patch.object(b, "deploy", side_effect=PermissionError(denied)):
                self.held(b)

    def test_missing_partial_intervening_and_arbitrary_predecessor(self):
        for journal in (None, (), "ever published"):
            b = Boundary()
            b.journal = journal
            self.held(b)
        b = Boundary()
        other = app.Target(C, "e" * 40)
        b.journal = (app.Publication(b.before, other, NOW - 15),
                     app.Publication(other, b.after, NOW - 10))
        self.held(b)
        b.journal = (app.Publication(other, b.after, NOW - 10),)
        self.held(b)

    def test_partial_or_unreadable_provider_response(self):
        for configure in (lambda b: setattr(b, "live", {"published_deploy": B}),
                          lambda b: b.deploys.pop(A), lambda b: b.archives.pop(B),
                          lambda b: setattr(b, "journal", ({"before": A, "after": B},))):
            b = Boundary()
            configure(b)
            self.held(b)

    def test_final_pointer_lock_history_and_exclusive_window(self):
        for action in (lambda b: setattr(b, "live", replace(b.live, published=b.before)),
                       lambda b: setattr(b, "live", replace(b.live, locked=True)),
                       lambda b: setattr(b, "clock", NOW + 70),
                       lambda b: setattr(b.window, "available", False),
                       lambda b: setattr(b, "journal", (replace(b.journal[0], at=NOW - 9),)),
                       lambda b: setattr(b, "journal", ())):
            b = Boundary()
            b.on_final = lambda: action(b)
            self.held(b)
            self.assertEqual(b.site_reads, 2)

    def test_artifact_and_repository_binding_for_both_deploys(self):
        for which, files in ((A, BASE), (B, NEXT)):
            for path in ("404.html", "guides/stay/index.html", KEY_FILE):
                b = Boundary()
                b.archives[which] = archive({**files, path: b"unexpected bytes"})
                self.held(b)
            b = Boundary()
            b.archives[which] = archive({k: v for k, v in files.items() if k != "404.html"})
            self.held(b)
            b = Boundary()
            b.archives[which] = archive({**files, "extra.txt": b"x"})
            self.held(b)
            b = Boundary()
            b.archives[which] = archive(files, {"index.html": stat.S_IFLNK | 0o777})
            self.held(b)
            b = Boundary()
            b.archives[which] = b"not a ZIP"
            self.held(b)
        b = Boundary()
        b.objects.data[b.after.commit] = b.objects.data[b.before.commit]
        self.held(b)
        b = Boundary()
        del b.objects.data[b.before.commit]
        self.held(b)

    def test_path_types_key_and_oversized_batch(self):
        for name in ("../escape.html", "dir//bad.html", "bad%2Fname.html", "x?a.html",
                     "bang#frag.html", "back\\slash.html", "guide\nx.html"):
            self.held(Boundary(new={**NEXT, name: b"x"}))
        self.held(Boundary(new={**NEXT, KEY_FILE: b"wrong key"}))
        self.held(Boundary(new={k: v for k, v in NEXT.items() if k != KEY_FILE}))
        self.held(Boundary(new={**NEXT, "X.html": b"1", "x.html": b"2"}))
        b = Boundary(new={KEY_FILE: app.KEY.encode(),
                          **{f"g{i}.html": b"x" for i in range(10_001)}})
        self.held(b)

    def test_dry_run_legacy_cli_and_operational_refusal(self):
        b = Boundary()
        self.assertTrue(app.notify(b, dry_run=True))
        self.assertEqual(b.attempts, [])
        for argv in (["--all"], ["--before", "0" * 40], ["--endpoint", "https://example.com"],
                     ["--published", B]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as out:
                app.main(argv)
            self.assertEqual(out.exception.code, 2)
        for argv in ([], ["--dry-run"]):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(app.main(argv), 2)
        self.assertEqual(b.attempts, [])

    def test_uncertain_submission_consumes_all_attempts(self):
        for outcome in (TimeoutError(), 503, 429):
            b = Boundary()
            b.response = outcome
            with self.assertRaises(app.Indeterminate):
                app.notify(b)
            self.assertEqual(len(b.attempts), 1)
            self.assertFalse(b.window.held)

    def test_actions_contains_only_offline_regression(self):
        # This test accepts two literal workflow forms. Every input character
        # must be consumed, including indentation and the final line feed.
        workflow = (HERE.parent / ".github/workflows/indexnow.yml").read_bytes().decode("utf-8")
        paths = (
            "    paths:\n"
            "      - '.github/workflows/indexnow.yml'\n"
            "      - 'scripts/submit_indexnow.py'\n"
            "      - 'scripts/submit_indexnow_selftest.py'\n"
        )
        checkout_pin = "3d3c42e5aac5ba805825da76410c181273ba90b1"
        python_pin = "6d4fd22b20465ccc0f7354476588e8df7c9ca0e0"
        structure = (
            ("triggers-and-paths", "name: IndexNow publication safety\n\non:\n"
             "  push:\n" + paths + "  pull_request:\n" + paths),
            ("permissions", "\npermissions:\n  contents: read\n"),
            ("job-runner-steps", "\njobs:\n  regression:\n    runs-on: ubuntu-latest\n    steps:\n"),
            ("checkout-pin", f"      - uses: actions/checkout@{checkout_pin} # v7.0.1\n"),
            ("credentials", "        with:\n          persist-credentials: false\n"),
            ("python-pin", f"      - uses: actions/setup-python@{python_pin} # v7.1.0\n"),
            ("python-inputs", "        with:\n          python-version: '3.12'\n"),
        )
        command = "python3 -I -B scripts/submit_indexnow_selftest.py"
        direct = "      - run: " + command + "\n"
        inert_name = "      - name: Run offline regression\n"
        named = inert_name + "        run: " + command + "\n"
        all_checks = tuple(group for group, _ in structure) + ("command", "no-extra-execution")

        def inspect_form(document):
            remaining = document
            checked = []
            for group, literal in structure:
                if not remaining.startswith(literal):
                    return group, tuple(checked)
                remaining = remaining[len(literal):]
                checked.append(group)
            for spelling in (direct, named):
                if remaining.startswith(spelling):
                    remaining = remaining[len(spelling):]
                    break
            else:
                return "command", tuple(checked)
            checked.append("command")
            if remaining:
                return "no-extra-execution", tuple(checked)
            checked.append("no-extra-execution")
            return "ACCEPT", tuple(checked)

        def change(control, old, new):
            self.assertEqual(control.count(old), 1, "fixture anchor must be unique")
            result = control.replace(old, new, 1)
            self.assertNotEqual(result, control)
            return result

        def observe(case_id, text, expected):
            actual, checked = inspect_form(text)
            print(f"workflow {case_id} expected={expected} actual={actual} "
                  f"checked={','.join(checked)}", flush=True)
            self.assertEqual(actual, expected)
            if expected == "ACCEPT":
                self.assertEqual(checked, all_checks)

        # Both controls must pass before deriving a single-purpose mutation.
        observe("W00-actual", workflow, "ACCEPT")
        named_control = change(workflow, direct, named)
        observe("W01-inert-name", named_control, "ACCEPT")
        marker = "echo fixture"
        extra = "      - run: " + marker + "\n"
        py_input = "          python-version: '3.12'\n"
        cases = (
            ("W02-extra-direct", workflow, direct, direct + extra, "no-extra-execution"),
            ("W03-extra-named", named_control, named, named + inert_name + "        run: " + marker + "\n", "no-extra-execution"),
            ("W04-literal", workflow, direct, "      - run: |\n          " + command + "\n          " + marker + "\n", "command"),
            ("W05-folded", named_control, named, inert_name + "        run: >\n          " + command + "\n          " + marker + "\n", "command"),
            ("W06-continuation", workflow, direct, direct[:-1] + " \\\n          && " + marker + "\n", "command"),
            ("W07-and", workflow, direct, direct[:-1] + " && " + marker + "\n", "command"),
            ("W08-semicolon", named_control, named, named[:-1] + "; " + marker + "\n", "command"),
            ("W09-or", workflow, direct, direct[:-1] + " || " + marker + "\n", "command"),
            ("W10-pipe", workflow, direct, direct[:-1] + " | " + marker + "\n", "command"),
            ("W11-duplicate-run", named_control, named, named + "        run: " + marker + "\n", "no-extra-execution"),
            ("W12-duplicate-steps", workflow, direct, direct + "    steps:\n" + extra, "no-extra-execution"),
            ("W13-extra-job", workflow, direct, direct + "  second:\n    runs-on: ubuntu-latest\n    steps:\n" + extra, "no-extra-execution"),
            ("W14-flow", workflow, direct, "      - {run: " + marker + "}\n", "command"),
            ("W15-alias", workflow, direct, "      - &extra {run: " + marker + "}\n      - *extra\n", "command"),
            ("W16-quoted-key", workflow, direct, direct.replace("- run:", "- 'run':"), "command"),
            ("W17-event", workflow, "  pull_request:\n", "  workflow_dispatch:\n", "triggers-and-paths"),
            ("W18-path", workflow, "  push:\n" + paths, "  push:\n" + paths.replace("submit_indexnow.py", "other.py"), "triggers-and-paths"),
            ("W19-unpinned", workflow, checkout_pin, "main", "checkout-pin"),
            ("W20-wrong-pin", workflow, python_pin, "0" * 40, "python-pin"),
            ("W21-extra-action", workflow, direct, "      - uses: actions/checkout@main\n" + direct, "command"),
            ("W22-write", workflow, "  contents: read\n", "  contents: write\n", "permissions"),
            ("W23-extra-permission", workflow, "  contents: read\n", "  issues: write\n  contents: read\n", "permissions"),
            ("W24-job-permission", workflow, "  regression:\n", "  regression:\n    permissions: write-all\n", "job-runner-steps"),
            ("W25-persist", workflow, "persist-credentials: false", "persist-credentials: true", "credentials"),
            ("W26-secret", workflow, command, command + " ${{ secrets.TEST_ONLY }}", "command"),
            ("W27-expression", named_control, command, "${{ github.job }}", "command"),
            ("W28-env", named_control, named, inert_name + "        env: {MODE: fixture}\n        run: " + command + "\n", "command"),
            ("W29-shell", named_control, named, named + "        shell: bash\n", "no-extra-execution"),
            ("W30-submit", workflow, command, "python3 scripts/submit_indexnow.py", "command"),
            ("W31-endpoint", workflow, command, command + " --endpoint https://example.invalid/", "command"),
            ("W32-runner", workflow, "runs-on: ubuntu-latest", "runs-on: self-hosted", "job-runner-steps"),
            ("W33-action-input", workflow, py_input, py_input.replace("3.12", "3.11"), "python-inputs"),
            ("W34-command-indent", workflow, direct, direct.replace("      -", "     -"), "command"),
            ("W35-extra-checkout-input", workflow, "persist-credentials: false", "token: fixture\n          persist-credentials: false", "credentials"),
            ("W36-changed-name", named_control, "name: Run offline regression", "name: Other", "command"),
        )
        for case_id, control, old, new, expected in cases:
            with self.subTest(case=case_id):
                observe(case_id, change(control, old, new), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
