#!/usr/bin/env python3
"""Validate the generated site's crawl, schema and discovery contracts."""

from __future__ import annotations

import json
import csv
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical = ""
        self.robots = ""
        self.hrefs: list[str] = []
        self.json_ld: list[str] = []
        self._in_json_ld = False
        self._script_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"] or "")
        elif tag == "link" and "canonical" in (values.get("rel") or "").split():
            self.canonical = values.get("href") or ""
        elif tag == "meta" and (values.get("name") or "").lower() == "robots":
            self.robots = values.get("content") or ""
        elif tag == "script" and values.get("type") == "application/ld+json":
            self._in_json_ld = True
            self._script_chunks = []

    def handle_data(self, data: str) -> None:
        if self._in_json_ld:
            self._script_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_json_ld:
            self.json_ld.append("".join(self._script_chunks))
            self._in_json_ld = False


def public_file(path: str) -> Path:
    path = unquote(path).lstrip("/")
    if not path:
        return DIST / "index.html"
    candidate = DIST / path
    if path.endswith("/") or candidate.is_dir():
        return candidate / "index.html"
    return candidate


def main() -> int:
    errors: list[str] = []
    pages: dict[Path, PageParser] = {}
    html_files = sorted(DIST.rglob("*.html"))
    sitemap_root = ElementTree.parse(DIST / "sitemap.xml").getroot()
    sitemap_urls = {
        element.text.strip()
        for element in sitemap_root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        if element.text
    }
    sitemap_hosts = {urlparse(url).netloc for url in sitemap_urls}
    site_host = next(iter(sitemap_hosts), "beatthescam.com")

    for filename in html_files:
        parser = PageParser()
        text = filename.read_text(encoding="utf-8")
        parser.feed(text)
        pages[filename] = parser
        if not parser.canonical:
            errors.append(f"missing canonical: {filename.relative_to(DIST)}")
        for position, payload in enumerate(parser.json_ld, start=1):
            try:
                json.loads(payload)
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON-LD #{position}: {filename.relative_to(DIST)} ({exc})")

    indexable_canonicals = {
        parser.canonical
        for parser in pages.values()
        if parser.canonical and "noindex" not in parser.robots.lower()
    }
    for url in sorted(sitemap_urls):
        if not public_file(urlparse(url).path).is_file():
            errors.append(f"sitemap target missing: {url}")
    for url in sorted(sitemap_urls - indexable_canonicals):
        errors.append(f"sitemap URL is not an indexable canonical: {url}")
    for url in sorted(indexable_canonicals - sitemap_urls):
        errors.append(f"indexable canonical missing from sitemap: {url}")

    broken_links: set[tuple[str, str]] = set()
    for filename, parser in pages.items():
        source = str(filename.relative_to(DIST))
        for href in parser.hrefs:
            parsed = urlparse(href)
            if parsed.scheme in {"mailto", "tel", "javascript", "data"}:
                continue
            if parsed.scheme in {"http", "https"} and parsed.netloc != site_host:
                continue
            if parsed.netloc and parsed.netloc != site_host:
                continue
            if not parsed.path or not parsed.path.startswith("/"):
                continue
            if not public_file(parsed.path).is_file():
                broken_links.add((source, parsed.path))
    for source, target in sorted(broken_links):
        errors.append(f"broken local link: {source} -> {target}")

    priority = {
        "dpd-delivery-scam-text": (3, 2),
        "bank-text-codes-not-arriving": (4, 0),
        "halifax-bank-scam-text-uk": (4, 2),
        "nhs-appointment-scam-text-uk": (4, 2),
        "dvla-vehicle-tax-text-scam": (4, 2),
    }
    for slug, (rows, examples) in priority.items():
        text = (DIST / "guides" / slug / "index.html").read_text(encoding="utf-8")
        actual_rows = text.count('<th scope="row">')
        actual_examples = text.count('<article class="message-example">')
        if (actual_rows, actual_examples) != (rows, examples):
            errors.append(
                f"evidence contract mismatch: {slug} expected {rows}/{examples}, "
                f"found {actual_rows}/{actual_examples}"
            )

    recovery = (DIST / "recovery" / "index.html").read_text(encoding="utf-8")
    if "adsbygoogle" in recovery or 'data-ad-slot=' in recovery:
        errors.append("recovery page must remain ad-free")

    research_index = DIST / "research" / "index.html"
    research_method = DIST / "research" / "methodology" / "index.html"
    if not research_index.is_file() or not research_method.is_file():
        errors.append("research index and methodology pages must be generated")
    for source_path in sorted((ROOT / "content" / "research").glob("*.json")):
        report = json.loads(source_path.read_text(encoding="utf-8"))
        slug = report["slug"]
        report_path = DIST / "research" / slug / "index.html"
        data_dir = DIST / "research" / "data"
        expected_data = [
            data_dir / f"{slug}.json",
            data_dir / f"{slug}-bing-daily.csv",
            data_dir / f"{slug}-bing-pages.csv",
            data_dir / f"{slug}-bing-queries.csv",
            data_dir / f"{slug}-gsc-focus-pages.csv",
        ]
        if not report_path.is_file():
            errors.append(f"research report missing: {slug}")
            continue
        report_html = report_path.read_text(encoding="utf-8")
        if "adsbygoogle" in report_html or 'data-ad-slot=' in report_html:
            errors.append(f"research report must remain ad-free: {slug}")
        report_parser = pages.get(report_path)
        schema_types = []
        if report_parser:
            for payload in report_parser.json_ld:
                value = json.loads(payload)
                schema_types.append(value.get("@type"))
        if "Dataset" not in schema_types:
            errors.append(f"research report missing Dataset schema: {slug}")
        for data_path in expected_data:
            if not data_path.is_file() or not data_path.read_text(encoding="utf-8").strip():
                errors.append(f"research download missing or empty: {data_path.name}")
        public_json = data_dir / f"{slug}.json"
        if public_json.is_file() and json.loads(public_json.read_text(encoding="utf-8")) != report:
            errors.append(f"published research JSON differs from source: {slug}")
        daily_csv = data_dir / f"{slug}-bing-daily.csv"
        if daily_csv.is_file():
            with daily_csv.open(encoding="utf-8", newline="") as handle:
                daily_rows = list(csv.DictReader(handle))
            if len(daily_rows) != report["bing_ai"]["days_returned"]:
                errors.append(f"Bing daily CSV row count mismatch: {slug}")

    for research_html in sorted((DIST / "research").rglob("*.html")):
        text = research_html.read_text(encoding="utf-8")
        if "adsbygoogle" in text or 'data-ad-slot=' in text:
            errors.append(f"research page must remain ad-free: {research_html.relative_to(DIST)}")

    llms_text = (DIST / "llms.txt").read_text(encoding="utf-8")
    if "## Research and datasets" not in llms_text or "/research/methodology/" not in llms_text:
        errors.append("llms.txt must expose research reports and methodology")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    json_ld_blocks = sum(len(parser.json_ld) for parser in pages.values())
    print(
        f"OK — {len(html_files)} HTML files; {len(sitemap_urls)} indexable canonicals; "
        f"{json_ld_blocks} JSON-LD blocks; 0 broken local links"
    )
    print("Priority evidence contracts plus ad-free recovery and research pages: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
