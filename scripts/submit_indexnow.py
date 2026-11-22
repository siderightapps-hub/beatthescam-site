#!/usr/bin/env python3
"""Plan one IndexNow batch for an observed production publication or restore.

The command line has no live adapter. The guard accepts no caller-supplied deploy,
manifest, publication flag, credential, URL list or endpoint. Its external boundary
is exercised only by offline tests. Normalized fields below are interface contracts,
not a claim that Netlify exposes a publication journal or maintenance-window lock.

A future adapter must obtain the owner decision and pre-publish site observation
from the attributable, exclusive release window. It must independently read the
pinned Git repository's immutable objects and the complete published artifact of
each exact Netlify deploy. A local build, unverified ZIP or bare commit label is
insufficient. Each authenticated read must either be complete or raise. Unknown
history, partial artifacts, uncertain lock semantics or inability to maintain
exclusivity through submission must keep the command on HOLD.
"""

import argparse
import hashlib
import io
import re
import stat
import sys
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser

HOST = "beatthescam.com"
ORIGIN = f"https://{HOST}"
KEY = "b3c8e1f2a94d7056"
KEY_LOCATION = f"{ORIGIN}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
SITE = "ce7e926f-9b1a-416b-81a2-4c8ac114a5e6"
REPOSITORY = "siderightapps-hub/beatthescam-site"
MAX_URLS = 10_000
MAX_ARCHIVE = 128 * 1024 * 1024
READ_AGE = 60
WINDOW_AGE = 900


class Hold(Exception):
    """No submission was authorized by the guard."""


class Indeterminate(Exception):
    """A request was attempted. Its disposition needs independent reconciliation."""


def require(condition, message):
    if not condition:
        raise Hold(message)


@dataclass(frozen=True)
class Target:
    deploy: str
    commit: str


@dataclass(frozen=True)
class SiteRead:
    site: str
    domain: str
    repository: str
    published: Target
    locked: bool
    at: int


@dataclass(frozen=True)
class DeployRead:
    site: str
    target: Target
    context: str
    branch: str
    state: str
    at: int


@dataclass(frozen=True)
class Decision:
    site: str
    before: Target
    after: Target
    at: int
    expires: int


@dataclass(frozen=True)
class Publication:
    before: Target
    after: Target
    at: int


def timestamp(value):
    return type(value) is int and value > 0


def fresh(value, now, limit):
    return timestamp(value) and timestamp(now) and 0 <= now - value <= limit


def valid_target(target):
    return (isinstance(target, Target)
            and isinstance(target.deploy, str) and re.fullmatch("[0-9a-f]{24}", target.deploy)
            and isinstance(target.commit, str) and re.fullmatch("[0-9a-f]{40}", target.commit)
            and target.commit != "0" * 40 and target.deploy != "0" * 24)


def site_matches(read, target):
    return (isinstance(read, SiteRead) and read.site == SITE and read.domain == HOST
            and read.repository == REPOSITORY and read.published == target
            and type(read.locked) is bool)


def check_publication(boundary, window, capture, decision):
    """The boundary reads the fixed site/deploys, never a caller-selected URL."""
    window.require_exclusive()
    require(window.capture == capture and window.decision == decision, "window changed")
    require(isinstance(decision, Decision) and decision.site == SITE
            and valid_target(decision.before) and valid_target(decision.after)
            and decision.before.deploy != decision.after.deploy, "owner decision")
    require(site_matches(capture, decision.before), "prepublication observation")
    site = boundary.site(SITE)
    require(site_matches(site, decision.after) and site.locked is False, "published pointer or lock")
    for target in (decision.before, decision.after):
        deploy = boundary.deploy(SITE, target.deploy)
        require(isinstance(deploy, DeployRead) and deploy.site == SITE and deploy.target == target
                and (deploy.context, deploy.branch, deploy.state) == ("production", "main", "ready")
                and fresh(deploy.at, boundary.now(), READ_AGE), "production deploy identity or state")

    # Complete ordered production pointer transitions since capture. An adapter
    # with only a build list or last-published timestamp must refuse this read.
    events = boundary.publications(SITE, capture.at, site.at)
    require(isinstance(events, tuple) and len(events) == 1, "predecessor not established")
    event = events[0]
    now = boundary.now()
    require(fresh(site.at, now, READ_AGE) and fresh(capture.at, now, WINDOW_AGE)
            and fresh(decision.at, now, WINDOW_AGE) and timestamp(decision.expires)
            and decision.at <= site.at <= now < decision.expires, "stale or ambiguous window")
    require(isinstance(event, Publication) and timestamp(event.at)
            and (event.before, event.after) == (decision.before, decision.after)
            and capture.at < event.at <= decision.at, "wrong publication transition")
    window.require_exclusive()
    return event, site.at


def object_id(kind, raw):
    return hashlib.sha1(kind + b" " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def object_bytes(boundary, kind, oid):
    actual_kind, raw = boundary.git_object(REPOSITORY, oid)
    require(actual_kind == kind and type(raw) is bytes and object_id(kind, raw) == oid,
            "immutable Git object mismatch")
    return raw


def safe_name(name):
    require(re.fullmatch(r"[A-Za-z0-9._~-]+", name) and name not in (".", "..")
            and name.lower() != ".git", "unsafe path component")


def tree_entries(raw):
    pos = 0
    seen = set()
    while pos < len(raw):
        space = raw.index(b" ", pos)
        end = raw.index(b"\0", space + 1)
        mode = raw[pos:space]
        name = raw[space + 1:end].decode("ascii")
        safe_name(name)
        require(name.lower() not in seen and end + 21 <= len(raw), "ambiguous Git tree")
        seen.add(name.lower())
        yield mode, name, raw[end + 1:end + 21].hex()
        pos = end + 21


def dist_tree(boundary, revision):
    commit = object_bytes(boundary, b"commit", revision)
    header, separator, _ = commit.partition(b"\n\n")
    roots = [line[5:] for line in header.splitlines() if line.startswith(b"tree ")]
    require(separator and len(roots) == 1 and re.fullmatch(b"[0-9a-f]{40}", roots[0]),
            "missing or ambiguous commit tree")
    root = object_bytes(boundary, b"tree", roots[0].decode("ascii"))
    dist = [oid for mode, name, oid in tree_entries(root) if name == "dist" and mode == b"40000"]
    require(len(dist) == 1, "missing dist tree")
    files = {}
    pending = [("", dist[0])]
    entries_seen = 0
    while pending:
        prefix, oid = pending.pop()
        for mode, name, child in tree_entries(object_bytes(boundary, b"tree", oid)):
            entries_seen += 1
            path = prefix + name
            require(entries_seen <= 50_000 and len(path) <= 2048, "oversized dist inventory or path")
            if mode == b"40000":
                pending.append((path + "/", child))
            else:
                require(mode in (b"100644", b"100755"), "unsafe dist entry type")
                files[path] = child
    return files


class Robots(HTMLParser):
    noindex = False

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        attributes = dict(attrs)
        name = (attributes.get("name") or "").strip().lower()
        if name in ("robots", "bingbot", "googlebot") or any(
                k == "name" and (v or "").strip().lower() in ("robots", "bingbot", "googlebot")
                for k, v in attrs):
            require(len(attrs) == len(attributes) and isinstance(attributes.get("content"), str),
                    "ambiguous robots directive")
            tokens = re.split(r"[\s,]+", attributes["content"].strip().lower())
            self.noindex |= bool({"noindex", "none"}.intersection(tokens))


def public_url(path):
    if path == "index.html":
        return ORIGIN + "/"
    if path.endswith("/index.html"):
        return ORIGIN + "/" + path[:-len("index.html")]
    return ORIGIN + "/" + path


def published_html(boundary, target):
    """Bind an independent, complete, deploy-specific archive to the exact Git dist tree."""
    expected = dist_tree(boundary, target.commit)
    archive = boundary.published_archive(SITE, target.deploy)
    require(type(archive) is bytes and len(archive) <= MAX_ARCHIVE, "missing or oversized artifact")
    seen = set()
    pages = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        entries = z.infolist()
        require(len(entries) == len(expected) and sum(e.file_size for e in entries) <= MAX_ARCHIVE,
                "incomplete or oversized artifact inventory")
        for e in entries:
            path = e.orig_filename
            require(path == e.filename and path in expected and path not in seen
                    and stat.S_ISREG(e.external_attr >> 16) and not e.flag_bits & 1,
                    "unexpected, duplicate or unsafe artifact entry")
            seen.add(path)
            data = z.read(e)
            require(object_id(b"blob", data) == expected[path], "published artifact differs from Git")
            if path == f"{KEY}.txt":
                require(data in (KEY.encode(), (KEY + "\n").encode(), (KEY + "\r\n").encode()),
                        "public verification key bytes")
            if path.endswith(".html") and path != "404.html":
                parser = Robots()
                parser.feed(data.decode("utf-8"))
                parser.close()
                pages[public_url(path)] = (expected[path], not parser.noindex)
    require(seen == set(expected) and f"{KEY}.txt" in seen, "incomplete artifact or missing key")
    return pages


def delta(before, after):
    # A newly noindex page is excluded. A genuinely removed page is submitted
    # only if it was public before the transition.
    urls = {url for url, entry in after.items() if entry[1] and before.get(url) != entry}
    urls.update(url for url, entry in before.items() if entry[1] and url not in after)
    require(len(urls) <= MAX_URLS and all(len(url.encode("ascii")) <= 2048 for url in urls),
            "invalid or oversized URL batch")
    return sorted(urls)


class ClosedBoundary:
    def controlled_window(self):
        raise Hold("authenticated release window, provider evidence and submission adapter unavailable")


def notify(boundary, dry_run=False):
    """Only the test boundary can reach the recorder. No live transport is shipped."""
    attempted = False
    try:
        with boundary.controlled_window() as window:
            capture, decision = window.capture, window.decision
            event, first_read = check_publication(boundary, window, capture, decision)
            before = published_html(boundary, decision.before)
            after = published_html(boundary, decision.after)
            urls = delta(before, after)
            if not urls or dry_run:
                return urls
            payload = {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
            final_event, final_read = check_publication(boundary, window, capture, decision)
            require(final_event == event and final_read >= first_read, "publication evidence changed")
            attempted = True
            status = boundary.post(ENDPOINT, payload)
            if status not in (200, 202):
                raise Indeterminate("submission attempted; reconcile independently")
            return urls
    except Exception as exc:
        if attempted:
            raise Indeterminate("submission attempted; reconcile independently") from None
        if isinstance(exc, Hold):
            raise
        raise Hold("missing, malformed or unavailable authenticated evidence") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Guarded post-publication IndexNow notification",
                                     allow_abbrev=False)
    parser.add_argument("--dry-run", action="store_true", help="report only")
    args = parser.parse_args(argv)
    try:
        notify(ClosedBoundary(), dry_run=args.dry_run)
    except Hold as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
