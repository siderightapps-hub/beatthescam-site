import hashlib
import html
import csv
import io
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canon as canon_mod   # noqa: E402  — the shared canon loader/validator/renderers
import corpus as corpus_mod  # noqa: E402  — the shared public/source corpus partition

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BASE = (ROOT / "templates/base.html").read_text(encoding="utf-8")


# ─── CATEGORY NORMALISATION ──────────────────────────────────────────────────
CATEGORY_CANON = {
    "website scams":                  "website",
    "email scams":                    "email",
    "payment scams":                  "payment",
    "crypto scams":                   "crypto",
    "phone scams":                    "phone",
    "marketplace scams":              "marketplace",
    "romance scams":                  "dating",
    "job scams":                      "employment",
    "verification scams":             "fraud",
    "government impersonation scams": "government",
    "text message scams":             "sms",
    "pet scams":                      "shopping",
    "impersonation scams":            "fraud",
    "travel scams":                   "travel",
    "ticket scams":                   "shopping",
    "business email scams":           "email",
    "recovery scams":                 "fraud",
    "donation scams":                 "fraud",
}

# Article-level 301 redirects live in scripts/corpus.py, alongside the
# consolidation metadata they partner with — one module owns "which slugs are
# public and where the rest go". Re-exported here because build.py has always
# been the name other scripts import it from.
ARTICLE_REDIRECTS = corpus_mod.ARTICLE_REDIRECTS


# ARTICLE_REDIRECTS above covers slugs with NO source record — deleted pages and
# old slug-collision artifacts. A guide that still exists in posts.json but has
# been consolidated into another declares that on the record itself:
#
#     "consolidated_into": "evri-delivery-scam-guide"
#
# scripts/corpus.py derives the whole consequence from that one field — the
# public/source partition, the 301, internal-link canonicalisation, and
# exclusion from the publication similarity check. It used to take two
# hand-maintained lists here (CONSOLIDATED_LIVE_SLUGS plus a duplicate
# ARTICLE_REDIRECTS entry) that agreed by accident, and a third opinion in
# similarity_report.py that the gate did not share (operator review,
# 2026-07-30).

CATEGORY_LABELS = {
    "marketplace": "Marketplace Scams",
    "sms":         "Text Message Scams",
    "payment":     "Payment Scams",
    "crypto":      "Crypto Scams",
    "tech":        "Tech Support Scams",
    "website":     "Website Scams",
    "government":  "Government Impersonation",
    "employment":  "Employment Scams",
    "social":      "Social Media Scams",
    "dating":      "Romance & Dating Scams",
    "email":       "Email Scams",
    "phone":       "Phone Scams",
    "travel":      "Travel Scams",
    "shopping":    "Shopping Scams",
    "finance":     "Investment & Finance Scams",
    "fraud":       "Fraud & Impersonation",
    "utility":     "Utility Scams",
}

CATEGORY_DESCRIPTIONS = {
    "marketplace": "Guides covering Facebook Marketplace, Gumtree, Vinted, and eBay scams targeting UK buyers and sellers. Spot payment fraud, advance fees, and collection scams.",
    "sms":         "Guides covering fake delivery texts, bank impersonation SMS, HMRC alerts, and smishing attacks. Learn to spot and report suspicious texts targeting UK phones.",
    "payment":     "Guides covering bank transfer fraud, advance fee scams, fake invoices, and APP fraud in the UK. Learn how to verify payment requests and protect your money.",
    "crypto":      "Guides covering fake crypto investment platforms, withdrawal fee traps, and romance fraud. Learn to identify cryptocurrency scams before sending money.",
    "tech":        "Guides covering fake tech support calls, remote access scams, and malicious software targeting UK users. Learn to spot and shut down tech support fraud.",
    "website":     "Guides covering fake online shops, lookalike domains, and website verification. Learn how to check if a website is legitimate before buying or sharing details.",
    "government":  "Guides covering HMRC, DVLA, TV Licensing, and government impersonation scams. Learn to verify official communications and avoid paying fake fines or fees.",
    "employment":  "Guides covering fake job ads, work-from-home schemes, and advance-fee employment fraud targeting UK jobseekers. Learn to spot recruitment scams before applying.",
    "social":      "Guides covering scams on Facebook, Instagram, WhatsApp, and other platforms. Learn to spot fake profiles, impersonation fraud, and social media scam tactics.",
    "dating":      "Guides covering romance scams, fake profiles, and relationship fraud on dating apps. Learn to identify and avoid romance fraud before money or data is lost.",
    "email":       "Guides covering phishing emails, business email compromise, fake invoices, and email impersonation. Learn to identify and report suspicious emails in the UK.",
    "phone":       "Guides covering vishing calls, fake bank calls, HMRC phone scams, and voice fraud targeting UK residents. Learn to verify callers and avoid phone-based scams.",
    "travel":      "Guides covering fake holiday listings, advance-fee travel fraud, and ticket scams targeting UK travellers. Verify travel offers before paying a deposit.",
    "shopping":    "Guides covering fake online retailers, counterfeit goods, pet scams, and marketplace fraud. Learn to shop safely and spot fraudulent sellers in the UK.",
    "finance":     "Guides covering fake investment opportunities, pension fraud, clone firm scams, and financial impersonation targeting UK consumers. Protect your savings.",
    "fraud":       "Guides covering recovery scams, impersonation fraud, and advance-fee tactics targeting UK consumers. Recognise fraud patterns and report them correctly.",
    "utility":     "Guides covering fake energy supplier calls, smart meter scams, and utility impersonation. Learn to verify energy contacts and avoid utility fraud in the UK.",
}


def normalize_category(cat: str) -> str:
    return CATEGORY_CANON.get(cat.strip().lower(), cat.strip().lower())

def category_label(cat: str) -> str:
    return CATEGORY_LABELS.get(cat, cat.replace("-", " ").title())

def category_description(cat: str) -> str:
    return CATEGORY_DESCRIPTIONS.get(cat, f"Guides covering common {cat.replace('-', ' ')} patterns and how to protect yourself.")




# ─── AFFILIATES ────────────────────────────────────────────────────────────

def load_affiliates(root: Path) -> list:
    path = root / "content" / "affiliates.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("products", [])
    except Exception:
        return []


def load_sources(root: Path) -> dict:
    """The verified canon of official UK reporting routes (content/sources.json).

    Delegates to the ONE shared validator in scripts/canon.py, which the
    publication gate also calls. Absent, unparseable or structurally invalid all
    stop the build: there is no second, unreviewed copy of the routes to fall
    back to, because a hard-coded fallback published a geographically unsafe
    sidebar at exactly the moment the single source of truth had failed
    (operator reviews, 2026-07-28/29).

    Returns the whole canon dict — callers that only want the route list use
    `canon.routes_by_role()` or `sources["official_routes"]`.
    """
    try:
        return canon_mod.load_canon(root / "content" / "sources.json")
    except canon_mod.CanonError as exc:
        raise SystemExit(f"ERROR: {exc}")


# Inline canon accessors for list-shaped surfaces, where a prose component does
# not fit but the URL, number, brand and nation must still come from the canon
# rather than being typed again (operator review, 2026-07-30).
def _r(sources: dict, key: str) -> dict:
    return canon_mod.route(sources, key)


def _b(sources: dict, key: str) -> str:
    return canon_mod.brand(canon_mod.route(sources, key))


def _n(sources: dict, key: str) -> str:
    return canon_mod.route(sources, key)["nation"]


def _sms(sources: dict) -> str:
    """The SMS spam shortcode, from the canon."""
    return canon_mod.route(sources, "report-spam-sms")["sms"]


def _email(sources: dict) -> str:
    """The NCSC suspicious-email address, from the canon."""
    return canon_mod.route(sources, "ncsc-sers")["email"]


def _consumer_advice_url(sources: dict) -> str:
    """GOV.UK's nation consumer-advice page — the canon's own cited source for
    the three nation services."""
    return canon_mod.route(sources, "citizens-advice")["source_url"]


def police_route_html(sources: dict, *, phone: bool = True, url: bool = True,
                      link: bool = True) -> str:
    """The nation-scoped police reporting route as linked HTML, from the canon.

    The ONE component every standalone surface uses — the checker page, the
    Disclaimer, the Terms and the contact note. Each of those used to hand-write
    its own version, and three of them drifted into naming Report Fraud with no
    geography at all, or relegating Scotland to a bare `(Police Scotland: 101)`
    parenthetical that is not a self-contained instruction (operator review,
    2026-07-29, `hubs-v10-c.md` §4).
    """
    rf = canon_mod.route(sources, "action-fraud")
    ps = canon_mod.route(sources, "police-scotland")

    def a(href, text):
        if not link:
            return html.escape(text)
        return (f'<a href="{html.escape(href)}" rel="noopener noreferrer" target="_blank">'
                f'{html.escape(text)}</a>')

    rf_bit = a(rf["info_url"], canon_mod.brand(rf))
    if phone:
        rf_bit += f' on <strong>{html.escape(rf["phone"])}</strong>'
    if url:
        host = urlparse(rf["report_url"]).hostname or ""
        rf_bit += f' {"or at" if phone else "at"} {a(rf["report_url"], host.replace("www.", ""))}'
    ps_bit = a(ps["report_url"], f'{canon_mod.brand(ps)} on {ps["phone"]}')
    return (f'{rf_bit} for {html.escape(rf["nation"])}, or {ps_bit} for '
            f'{html.escape(ps["nation"])}')


def consumer_route_html(sources: dict) -> str:
    """The three nation consumer services as linked HTML, from the canon."""
    bits = []
    for r in canon_mod.consumer_advice_routes(sources):
        bits.append(f'<a href="{html.escape(r["info_url"])}" rel="noopener noreferrer" '
                    f'target="_blank">{html.escape(canon_mod.brand(r))}</a> in '
                    f'{html.escape(r["nation"])}')
    return ", ".join(bits[:-1]) + f", or {bits[-1]}"


def report_block(sources: dict) -> str:
    """Render the 'Report this scam' sidebar list from the verified canon
    (on_page routes only). No fallback: load_sources() has already guaranteed
    every nation is covered, so an empty list here is a bug, not a degraded
    mode to paper over."""
    routes = [r for r in sources.get("official_routes", [])
              if r.get("on_page") and r.get("report_url")]
    if not routes:
        raise SystemExit("ERROR: the canon produced no on-page reporting routes")
    items = "".join(
        f'<li><a href="{html.escape(r["report_url"])}" rel="noopener noreferrer" target="_blank">'
        f'{html.escape(r.get("report_label") or r.get("name", "Report"))}</a></li>'
        for r in routes
    )
    return f'<ul class="list-clean">{items}</ul>'


def load_category_hubs(root: Path) -> dict:
    """Optional per-category pillar content (title/description/intro/sections/faq)
    keyed by canonical category slug. Turns a category page into a rankable hub
    that links down to its guides. Missing file/category → plain category page."""
    path = root / "content" / "category-hubs.json"
    if not path.exists():
        return {}
    # FAIL CLOSED. Swallowing the error and returning {} meant a malformed hub
    # file silently published every category as a plain page instead of stopping
    # the build (operator review, 2026-07-27). Absent is a valid state; present
    # but unreadable is not.
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"ERROR: {path} exists but could not be read or parsed: {exc}")


def validate_category_hubs(hubs: dict) -> None:
    """Run the deterministic editorial gate over every hand-authored hub.

    Generated guides are gated before they reach posts.json. Category hubs are
    edited directly, so the build is their publication boundary: a BLOCK issue
    must stop the build before dist/ is deleted or regenerated. FLAG issues stay
    visible in build output for operator review, matching the guide workflow.
    """
    try:
        from content_gate import check_deterministic, SEVERITY_BLOCK
    except ImportError:  # Support importing this file as scripts.build.
        from scripts.content_gate import check_deterministic, SEVERITY_BLOCK

    # Structural validation first. content/category-hubs.json is keyed by canonical
    # category slug at the TOP level. A packet shaped {"hubs": {...}} merges as one
    # unknown key, the renderer skips it, and the build silently publishes nothing
    # — the gate would pass vacuously because the wrapper has no prose to inspect
    # (operator review, 2026-07-27). Fail loudly instead.
    # This runs BEFORE dist/ is removed. A shape the validator waves through but
    # the renderer cannot unpack — `["label"]` in sources_checked, say — would
    # otherwise crash after the committed output tree had already been deleted
    # (operator review, 2026-07-27).
    known = set(CATEGORY_LABELS) | set(CATEGORY_CANON.values())
    structural = []
    if hubs is not None and not isinstance(hubs, dict):
        raise SystemExit(f"ERROR: category hub file must be an object keyed by category slug, "
                         f"got {type(hubs).__name__}")

    def _pairs(slug, field, value, a_name, b_name, require_url=False):
        if value is None:
            return
        if not isinstance(value, list):
            structural.append(f"{slug}: {field!r} must be a list, got {type(value).__name__}")
            return
        for n, pair in enumerate(value):
            if not (isinstance(pair, (list, tuple)) and len(pair) == 2):
                structural.append(f"{slug}: {field}[{n}] must be a [{a_name}, {b_name}] pair")
                continue
            a, b = pair
            if not isinstance(a, str) or not isinstance(b, str):
                structural.append(f"{slug}: {field}[{n}] {a_name}/{b_name} must both be strings")
                continue
            if not a.strip():
                structural.append(f"{slug}: {field}[{n}] {a_name} is empty")
            if not require_url and not b.strip():
                structural.append(f"{slug}: {field}[{n}] {b_name} is empty")
            if require_url:
                parsed = urlparse(b)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    structural.append(f"{slug}: {field}[{n}] {b_name} must be an http(s) URL "
                                      f"with a host, got {b!r}")

    for slug, hub in (hubs or {}).items():
        if slug not in known:
            structural.append(f"unknown category slug {slug!r} — hubs are keyed by canonical "
                              f"category slug at the top level, with no wrapper object")
            continue
        if not isinstance(hub, dict):
            structural.append(f"{slug}: record is {type(hub).__name__}, expected an object")
            continue
        for field in ("title", "description"):
            if not isinstance(hub.get(field), str) or not hub.get(field, "").strip():
                structural.append(f"{slug}: {field!r} must be a non-empty string")
        if "intro" in hub and (not isinstance(hub.get("intro"), str) or not hub["intro"].strip()):
            structural.append(f"{slug}: 'intro' must be a non-empty string")
        sections = hub.get("sections")
        if not isinstance(sections, list) or not sections:
            structural.append(f"{slug}: 'sections' must be a non-empty list")
        else:
            _pairs(slug, "sections", sections, "heading", "body")
        _pairs(slug, "faq", hub.get("faq"), "question", "answer")
        srcs = hub.get("sources_checked")
        if isinstance(srcs, list) and srcs:
            _pairs(slug, "sources_checked", srcs, "label", "url", require_url=True)
        elif hub.get("updated"):
            # A hub carrying a review date is a reviewed hub: it renders a trust
            # layer, so it must have sources to render. Required, not advisory.
            structural.append(f"{slug}: 'sources_checked' must be a non-empty list — this hub "
                              f"declares a review date, so the trust layer renders from it")
        else:
            # Every hub is sourced as of the 2026-07-30 accuracy release, so an
            # unsourced hub is now an error. The `unsourced_legacy` warning
            # branch that used to sit here existed only for the three original
            # hubs and was removed in the same patch that landed all thirteen.
            structural.append(f"{slug}: 'sources_checked' must be a non-empty list — every hub "
                              f"renders a trust layer")
        unknown = set(hub) - {"title", "description", "intro", "sections", "faq",
                              "sources_checked", "updated", "ads_mode"}
        if unknown:
            structural.append(f"{slug}: unknown key(s) {sorted(unknown)} — a misspelling such as "
                              f"'source_checked' would silently drop the trust layer")
        updated = hub.get("updated")
        if updated is not None:
            if not isinstance(updated, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated):
                structural.append(f"{slug}: 'updated' must be an ISO date (YYYY-MM-DD), got {updated!r}")
            else:
                try:
                    datetime.strptime(updated, "%Y-%m-%d")
                except ValueError:
                    structural.append(f"{slug}: 'updated' is not a real date: {updated!r}")
        ads = hub.get("ads_mode")
        if ads is not None and ads not in ("none", "npa", "default"):
            structural.append(f"{slug}: 'ads_mode' must be none|npa|default, got {ads!r}")
    if structural:
        for msg in structural:
            print(f"  Category hub STRUCTURE: {msg}")
        raise SystemExit(f"ERROR: category hub file is malformed: {len(structural)} problem(s)")

    blocking = []
    flagged = []
    for slug, hub in (hubs or {}).items():
        surface = dict(hub or {})
        surface.setdefault("slug", f"category-{slug}")
        surface.setdefault("category", slug)
        surface.setdefault("keywords", [])
        for issue in check_deterministic(surface):
            row = (slug, issue)
            if issue.get("severity") == SEVERITY_BLOCK:
                blocking.append(row)
            else:
                flagged.append(row)

    for slug, issue in flagged:
        print(f"  Category hub accuracy FLAG [{issue.get('check')}]: {slug}: "
              f"{issue.get('span') or issue.get('detail', '')}")
    if blocking:
        details = "; ".join(
            f"{slug} [{issue.get('check')}]: {issue.get('span') or issue.get('detail', '')}"
            for slug, issue in blocking
        )
        raise SystemExit(f"ERROR: category hub accuracy gate failed: {details}")


# Category match alone is 2; each keyword hit adds 1. 3 therefore means
# "right category AND something specific in common".
_AFFILIATE_MIN_SCORE = 3


def affiliate_block(post: dict, affiliates: list) -> str:
    """Return an HTML affiliate card relevant to this post, or empty string."""
    if not affiliates:
        return ""

    # Pages that carry no ads carry no commercial card either. Suppressing the
    # ad tag while still showing a product recommendation on a sextortion or
    # deepfake guide is the same monetisation the exclusion exists to prevent.
    if post_ads_mode(post) == "none":
        return ""

    cat      = post.get("category", "")
    keywords = " ".join(post.get("keywords", [])).lower()
    title    = post.get("title", "").lower()
    haystack = keywords + " " + title

    # Score each product by relevance
    best_score   = 0
    best_product = None

    for product in affiliates:
        score = 0
        if cat in product.get("categories", []):
            score += 2
        for kw in product.get("keywords", []):
            if kw.lower() in haystack:
                score += 1
        if score > best_score:
            best_score   = score
            best_product = product

    # A bare CATEGORY match scored 2 and was enough, so 134 of 185 guides drew a
    # card on category alone with no keyword overlap at all — 170/185 carried one,
    # including all three guides that deliberately run no ads. Requiring the
    # category AND at least one keyword takes it to 33 (18%), which is a real
    # relevance signal rather than a default (audit, 2026-07-31).
    if not best_product or best_score < _AFFILIATE_MIN_SCORE:
        return ""

    p = best_product
    # These are honest editorial recommendations, NOT paid placements: the hrefs
    # are plain destination links, not affiliate tracking URLs (see the _note in
    # content/affiliates.json). Labelling them "Sponsored" / rel="sponsored"
    # would misrepresent unpaid links as paid — an ASA and trust problem on a
    # scam-awareness site. When real affiliate deals + tracking URLs are signed,
    # flip the label back to "Sponsored" and rel to "sponsored noopener...".
    return f'''
    <section class="sidebar-card affiliate-card">
      <p class="note" style="margin:0 0 .4rem;font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;font-weight:800;color:var(--muted)">Recommended</p>
      <h3 style="margin:.15rem 0 .4rem">{html.escape(p["name"])}</h3>
      <p class="note">{html.escape(p["tagline"])}</p>
      <a class="btn btn-secondary" href="{html.escape(p["href"])}" rel="nofollow noopener noreferrer" target="_blank" data-affiliate-id="{html.escape(p["id"])}" data-affiliate-name="{html.escape(p["name"])}" data-commercial-status="unpaid-editorial" style="width:100%;margin-top:.6rem;text-align:center">{html.escape(p["cta"])}</a>
      <p class="note" style="margin:.5rem 0 0;font-size:.72rem;color:var(--muted)">Unpaid editorial pick — we receive no commission.</p>
    </section>
    '''

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")

def load_research_reports(root: Path):
    """Load dated public research sources, newest first."""
    reports_dir = root / "content" / "research"
    if not reports_dir.is_dir():
        return []
    reports = [read_json(path) for path in sorted(reports_dir.glob("*.json"))]
    required = {"slug", "title", "published", "summary", "bing_ai", "google_search", "method", "limitations"}
    for report in reports:
        missing = required - set(report)
        if missing:
            raise SystemExit(f"ERROR: research report {report.get('slug', '<unknown>')} missing {sorted(missing)}")
    return sorted(reports, key=lambda report: report["published"], reverse=True)

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower().strip()).strip("-")


# ─── SEO HELPERS ─────────────────────────────────────────────────────────────

# Populated in build() before any page is rendered so make_base() can inject
# the full category list into the footer without changing function signatures.
_FOOTER_CATS_HTML = ""

def seo_title(post_title: str, site_name: str, max_len: int = 60, brand: bool = True) -> str:
    """Return a <title>-safe string truncated to max_len chars.

    Appends ' | SiteName' suffix (unless brand=False), then truncates the
    post_title portion at the nearest word boundary so the full string fits
    within max_len. Guides pass brand=False: the ' | Beat the Scam' suffix
    costs 16 chars of <title> space, which on a long-tail query site is worth
    more spent on the title itself — and it stops long guide titles being
    guillotined mid-phrase into a dangling "…How to Spot" (2026-06 audit).
    """
    suffix = f" | {site_name}" if brand else ""
    available = max_len - len(suffix)
    if len(post_title) <= available:
        return post_title + suffix
    truncated = post_title[:available].rsplit(" ", 1)[0].rstrip(" :,-–")
    # Drop any trailing connective/stop-word left by truncation, so titles
    # don't read "...How to Spot and | Beat the Scam".
    stop = {"and", "or", "to", "the", "a", "an", "of", "for", "with",
            "in", "on", "your", "how", "is", "vs"}
    words = truncated.split()
    while len(words) > 1 and words[-1].lower().strip(":,-–&") in stop:
        words.pop()
    truncated = " ".join(words).rstrip(" :,-–")
    return truncated + suffix

def seo_description(desc: str, max_len: int = 160, min_acceptable: int = 130) -> str:
    """Trim a meta description for SERP display.

    Strategy (in order):
      1. If already <= max_len, return unchanged.
      2. Prefer the longest sentence-bounded prefix that fits AND is at
         least `min_acceptable` chars. The min stops us preferring a
         short first sentence over fuller content — e.g. a 158-char string
         where the first sentence is only 100 chars would previously cut
         to 100, but with min_acceptable=130 we skip that short cut and
         fall through to the word-boundary trim which keeps more text.
      3. Else fall back to word-boundary trim, but keep the last full clause
         (strip dangling prepositions/auxiliaries that would end the snippet
         mid-thought like "...used by them to.").

    Defaults assume Google's effective SERP description display cap of
    ~160 chars, which is comfortably under the 155 chars Ahrefs flags as
    "too short" for sites still in the cold-start phase.
    """
    desc = (desc or "").strip()
    if len(desc) <= max_len:
        return desc

    # 1) Sentence boundary fit
    sentence_end_re = re.compile(r"([.!?])\s")
    best_end = 0
    for m in sentence_end_re.finditer(desc):
        end = m.end() - 1  # include the punctuation, not the space
        if end <= max_len:
            best_end = end
        else:
            break
    if best_end >= min_acceptable:
        return desc[:best_end].strip()

    # 2) Word-boundary fallback, stripping dangling connector words.
    # Reserve one char for the appended ellipsis so the result stays <= max_len
    # even for a no-space input, and strip any existing trailing "…" so a
    # source description already ending in one can't produce "……".
    truncated = desc[:max_len - 1].rsplit(" ", 1)[0].rstrip(" .,;:…")
    DANGLERS = {
        "to", "the", "a", "an", "of", "for", "with", "and", "or", "but",
        "in", "on", "at", "by", "from", "as", "is", "are", "was", "were",
        "be", "been", "this", "that", "these", "those", "their", "your", "our",
    }
    parts = truncated.split()
    while parts and parts[-1].lower() in DANGLERS:
        parts.pop()
    truncated = " ".join(parts).rstrip(" .,;:…")
    if not truncated:
        return desc[:max_len - 1].rstrip() + "…"
    return truncated + "…"


def first_sentence(text: str) -> str:
    """Return the first sentence of text, or the whole string if no terminator."""
    m = re.search(r"[.!?](\s|$)", text or "")
    if not m:
        return (text or "").strip()
    return text[: m.end() - 1].strip()


def pick_description(post: dict, max_len: int = 160, min_len: int = 130) -> str:
    """Pick the best meta description for a post.

    Targets the 130-160 char sweet spot that Google displays AND Ahrefs
    accepts. Adds extension logic for descriptions that are present but
    too short — they get padded with the hero line or section 1 first
    sentence so we hit ~130+ chars instead of returning a 95-char string
    that Ahrefs flags as "Meta description too short".

    Preference order:
      1. post['description'] verbatim if it's already in the sweet spot.
      2. If description is too short, extend it with the hero line, then
         with section 1's first sentence — whichever fits within max_len.
      3. If description is too long, sentence-aware trim of it.
      4. No description present — fall back to hero, then section 1 trim.
    """
    desc = (post.get("description") or "").strip()
    hero = (post.get("hero") or "").strip()

    # Helper: extract section 1 first sentence
    def section1_first_sentence() -> str:
        sections = post.get("sections") or []
        if not sections:
            return ""
        body = sections[0][1] if isinstance(sections[0], (list, tuple)) and len(sections[0]) >= 2 else ""
        body = _normalize_bullet_body(body).replace("`", "")
        return first_sentence(body)

    # 1) Description already in sweet spot
    if desc and min_len <= len(desc) <= max_len:
        return desc

    # 2) Description too short — extend with hero, then section 1
    if desc and len(desc) < min_len:
        # Try hero first
        if hero and hero.lower() not in desc.lower():
            combined = f"{desc} {hero}"
            if len(combined) <= max_len:
                return combined
            return seo_description(combined, max_len)
        # Then section 1
        sec1 = section1_first_sentence()
        if sec1 and sec1.lower() not in desc.lower():
            combined = f"{desc} {sec1}"
            if len(combined) <= max_len:
                return combined
            return seo_description(combined, max_len)
        # Nothing to extend with — return the short desc rather than nothing
        return desc

    # 3) Description too long — sentence-aware trim
    if desc and len(desc) > max_len:
        return seo_description(desc, max_len)

    # 4) No description at all — hero, then section 1
    if hero:
        if len(hero) <= max_len:
            return hero
        return seo_description(hero, max_len)

    sec1 = section1_first_sentence()
    if sec1:
        if len(sec1) <= max_len:
            return sec1
        return seo_description(sec1, max_len)

    return ""


def _normalize_bullet_body(para) -> str:
    """
    Coerce a section body into clean text. Handles three shapes:
      1. Plain string -> returned as-is.
      2. Actual Python list of strings -> joined with newlines.
      3. String containing a Python list literal like "['- item', '- item']"
         (legacy bug where lists were str()'d before being saved to JSON)
         -> parsed with ast.literal_eval and joined with newlines.
    Output is always a string.
    """
    if isinstance(para, list):
        return "\n".join(str(x) for x in para)
    if not isinstance(para, str):
        return str(para)
    s = para.strip()
    if (s.startswith("['") or s.startswith('["')) and s.endswith("]"):
        try:
            import ast
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                return "\n".join(str(item) for item in parsed)
        except (ValueError, SyntaxError):
            pass
    return para

def reading_time(post: dict) -> int:
    words = sum(len((t + " " + b).split()) for t, b in post.get("sections", []))
    words += sum(len((q + " " + a).split()) for q, a in post.get("faq", []))
    return max(1, round(words / 200))

def topic_signature(post: dict) -> str:
    title = post.get("title", "").lower()
    title = re.sub(r"\b(guide|checklist|warning signs|uk guide|uk)\b", "", title)
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()

def rel_url(site, path: str) -> str:
    return (site.get("site_path", "") or "") + path

def abs_url(site, path: str) -> str:
    if path.startswith("http"):
        return path
    return site["domain"].rstrip("/") + rel_url(site, path)

def localize_content_paths(content: str, site: dict) -> str:
    prefix = site.get("site_path", "") or ""
    if not prefix:
        return content
    return (content
            .replace('href="/', f'href="{prefix}/')
            .replace("href='/", f"href='{prefix}/")
            .replace('src="/', f'src="{prefix}/')
            .replace("src='/", f"src='{prefix}/"))

def json_ld(data) -> str:
    # json.dumps handles all special chars correctly, but a literal "<" in a
    # string value could form "</script>" (prematurely closing the block) or
    # "<!--" (an HTML comment opener). Escape every "<" as the JSON-legal
    # backslash-u-0-0-3-c unicode escape rather than pattern-matching
    # "</script>"/"<!--" as literal text: a previous version replaced "<!--"
    # with a literal backslash-bang, which is NOT a valid JSON escape, so any
    # post containing "<!--" (e.g. quoting a phishing email's raw HTML) made
    # the whole JSON-LD block unparseable. The unicode escape is valid JSON
    # and round-trips to the same "<" character on parse, so no content
    # changes — it also neutralises "<!--"/"</script>" regardless of case,
    # which the literal-string replace did not.
    serialised = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    serialised = serialised.replace("<", "\\u003c")
    return '<script type="application/ld+json">' + serialised + "</script>"

def _verification_meta(site: dict) -> str:
    lines = []
    g = (site.get("google_site_verification") or "").strip()
    b = (site.get("bing_site_verification") or "").strip()
    if g:
        lines.append(f'<meta name="google-site-verification" content="{html.escape(g)}">')
    if b:
        lines.append(f'<meta name="msvalidate.01" content="{html.escape(b)}">')
    return "\n  ".join(lines)


def _prev_next_meta(prev_url: str = None, next_url: str = None) -> str:
    parts = []
    if prev_url:
        parts.append(f'<link rel="prev" href="{prev_url}">')
    if next_url:
        parts.append(f'<link rel="next" href="{next_url}">')
    return "\n  ".join(parts)


def _ads_head(site: dict, ads_mode: str) -> str:
    """Build the per-page AdSense <head> snippet.

      "none"    → no ads at all (the /check/ tool — excluded from Auto Ads).
      "npa"     → request NON-personalised ads regardless of consent, for pages
                  about debt, insolvency, money lost to scams, or victim support.
                  Google restricts ad personalisation based on negative financial
                  status, so these must not serve personalised ads even after
                  consent.
      "default" → the standard Auto Ads tag (personalisation still gated by the
                  CMP / Consent Mode).
    """
    client = site["adsense_client"]
    tag = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/'
           f'adsbygoogle.js?client={client}" crossorigin="anonymous"></script>')
    if ads_mode == "none":
        return "<!-- Ads intentionally disabled on this page (excluded from Auto Ads) -->"
    if ads_mode == "npa":
        return ('<script>(adsbygoogle=window.adsbygoogle||[]).requestNonPersonalizedAds=1;</script>\n  '
                + tag)
    return tag


def _ads_resource_hints(ads_mode: str) -> str:
    """Only warm AdSense origins on pages that can actually serve ads."""
    if ads_mode == "none":
        return "<!-- AdSense resource hints intentionally omitted on this page -->"
    return "\n  ".join([
        '<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>',
        '<link rel="preconnect" href="https://tpc.googlesyndication.com" crossorigin>',
        '<link rel="dns-prefetch" href="https://pagead2.googlesyndication.com">',
        '<link rel="dns-prefetch" href="https://tpc.googlesyndication.com">',
    ])


# Pages whose subject implies "negative financial status" — debt/insolvency, or
# recovery scams that target people who have already lost money. Google restricts
# ad personalisation on these, so they get requestNonPersonalizedAds regardless
# of consent. Matched against slug + title + category + keywords (NOT the body),
# so the trigger is the page's TOPIC, not an incidental mention. The list is kept
# deliberately tight: broad words like "victim", "refund", "compensation" or
# "lost money" recur across almost every scam guide and would needlessly switch
# the whole corpus to non-personalised ads.
_NO_ADS_TERMS = (
    # Sexual abuse / extortion and manipulated intimate imagery are excluded
    # from advertising entirely. Non-personalised ads only change targeting;
    # they do not remove content-eligibility risk.
    "sextortion", "intimate image", "intimate-image", "revenge porn",
    "webcam blackmail", "explicit image", "explicit photo", "nude photo",
    "nude image", "deepfake",
    # Prescription medicines and pharmacies are a restricted advertising
    # category. Non-personalised ads only change targeting, not eligibility, so
    # these run ad-free (audit, 2026-07-31).
    "online pharmacy", "fake pharmacy", "prescription medicine",
    "prescription medicines", "prescription drug", "prescription drugs",
)
_NO_ADS_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _NO_ADS_TERMS) + r")", re.I)

_SENSITIVE_FINANCE_TERMS = (
    # Debt / insolvency / negative financial status (stems — leading \b only, so
    # "debt" also catches "debts", "insolven" catches "insolvency/insolvent").
    "debt", "iva", "individual voluntary arrangement", "bankrupt", "insolven",
    "bailiff", "arrears", "ccj", "county court judgment", "loan default",
    "struggling to pay", "repossess",
    # Recovery scams (prey on people who already lost money)
    "recovery scam", "recover your money", "recover stolen", "money recovery",
    "fund recovery", "get your money back",
    # Romance / relationship fraud
    "romance scam", "romance fraud", "catfish", "pig butchering", "pig-butchering",
    "military romance", "dating scam",
    # Identity theft (the victim's own identity stolen — not org impersonation)
    "identity theft", "identity fraud", "stolen identity",
    # Welfare / benefits (government-assistance interest category) and pensions
    # (retirement finances, older/vulnerable audience). "money mule scam" is
    # deliberately narrower than "money mule" so employment guides that merely
    # mention mule recruitment in keywords keep default ads.
    "universal credit", "benefit", "pension", "money mule scam",
    # Loan-fee fraud (loans interest category) and medicines (health interest
    # category). Stems chosen so each matches exactly one guide's topic fields:
    # "advance fee" → advance-fee-scam-uk, "pharmacy" → fake-online-pharmacy-uk-scam.
    "advance fee", "pharmacy",
)
# Leading word boundary only — avoids "iva" matching inside "festival", while
# still matching word-initial stems like "debt"/"debts".
_SENSITIVE_FINANCE_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _SENSITIVE_FINANCE_TERMS) + r")", re.I)

def post_ads_mode(post: dict) -> str:
    """Return no ads for sexual-abuse/deepfake pages, NPA for other sensitive
    financial/relationship topics, and default Auto Ads for other guides."""
    hay = " ".join([
        post.get("slug", ""), post.get("title", ""), post.get("category", ""),
        " ".join(post.get("keywords", []) or []),
    ])
    # Normalise hyphens/underscores to spaces so a hyphenated slug
    # ("military-romance-scam-uk") matches the spaced terms ("military romance").
    hay = hay.replace("-", " ").replace("_", " ")
    if _NO_ADS_RE.search(hay):
        return "none"
    return "npa" if _SENSITIVE_FINANCE_RE.search(hay) else "default"


def hub_ads_mode(slug: str, hub: dict) -> str:
    """Ad mode for a category hub page.

    `render_category_page()` used to pass a flat "default" for every hub, so ten
    long pages covering debt, lost money, identity theft, recovery, romance,
    sextortion and intimate images would all have carried personalised-capable
    Auto Ads — inconsistent with the site's per-page policy and the reason
    `post_ads_mode()` exists (operator review, 2026-07-27).

    Assesses the WHOLE hub, not just the category name: a hub's own prose is
    what a reader and an ad network actually see, and `crypto` or `email` gives
    away nothing about the sextortion and debt material inside.

    An explicit `ads_mode` may only KEEP or INCREASE restriction
    (default < npa < none). A less restrictive explicit value is ignored in
    favour of the content-derived mode, so a record carrying sextortion or
    intimate-image material cannot set "default" and bypass a derived "none".
    """
    explicit = str((hub or {}).get("ads_mode") or "").strip().lower()
    if explicit and explicit not in ("none", "npa", "default"):
        raise SystemExit(f"ERROR: hub {slug}: ads_mode must be none|npa|default, got {explicit!r}")
    hay = " ".join([
        slug, str(hub.get("title") or ""), str(hub.get("description") or ""),
        str(hub.get("intro") or ""),
        " ".join(f"{h} {b}" for h, b in (hub.get("sections") or [])),
        " ".join(f"{q} {a}" for q, a in (hub.get("faq") or [])),
    ]).replace("-", " ").replace("_", " ")
    derived = "none" if _NO_ADS_RE.search(hay) else (
        "npa" if _SENSITIVE_FINANCE_RE.search(hay) else "default")
    if not explicit:
        return derived
    # An explicit value may only be EQUALLY or MORE restrictive. Returning it
    # before scanning let a future record carrying sextortion or intimate-image
    # material set "default" and bypass the safer derived "none".
    rank = {"default": 0, "npa": 1, "none": 2}
    return explicit if rank[explicit] >= rank[derived] else derived


def make_base(content: str, *, title: str, description: str, canonical: str, schema: str, site: dict,
              og_type: str = "website", robots: str = "index,follow", og_title: str = None,
              og_image: str = None, prev_url: str = None, next_url: str = None,
              ads_mode: str = "default"):
    og_image_url = og_image or abs_url(site, "/assets/og-image-v2.png")
    twitter_handle = site.get("twitter") or ""
    replacements = {
        "{{title}}":             html.escape(title),
        "{{description}}":       html.escape(description),
        "{{canonical}}":         canonical,
        "{{robots}}":            robots,
        "{{adsense_client}}":    site["adsense_client"],
        "{{og_type}}":           og_type,
        "{{og_title}}":          html.escape(og_title or title),
        "{{og_image}}":          og_image_url,
        "{{site_name}}":         html.escape(site["site_name"]),
        "{{tagline}}":           html.escape(site["tagline"]),
        "{{twitter_handle}}":    html.escape(twitter_handle),
        "{{content}}":           localize_content_paths(content, site),
        "{{schema}}":            schema,
        "{{asset_prefix}}":      site.get("site_path", ""),
        "{{css_ver}}":           site.get("_asset_ver_css", ""),
        "{{js_ver}}":            site.get("_asset_ver_js", ""),
        "{{ads_head}}":          _ads_head(site, ads_mode),
        "{{ads_resource_hints}}": _ads_resource_hints(ads_mode),
        "{{ga4_id}}":            site["ga4_id"],
        "{{year}}":              str(datetime.now(timezone.utc).year),
        "{{footer_cats}}":       _FOOTER_CATS_HTML,
        "{{prev_next}}":         _prev_next_meta(prev_url, next_url),
        "{{verification_meta}}": _verification_meta(site),
    }
    # Single pass over the TEMPLATE only: chained str.replace would re-scan
    # already-substituted values, so a literal "{{year}}" etc. inside article
    # content (plausible on a site that quotes phishing-template text) would
    # get substituted too. re.sub visits each template token exactly once.
    rendered = re.sub(
        r"\{\{(?:%s)\}\}" % "|".join(re.escape(k[2:-2]) for k in replacements),
        lambda m: replacements[m.group(0)],
        BASE,
    )
    return "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"


# ─── SCHEMA ────────────────────────────────────────────────────────────────

# Official site profiles for schema.org sameAs — entity reconciliation is how
# search and answer engines confirm the publisher is a real organisation.
ORG_SAME_AS = [
    "https://x.com/beatthescam",
    "https://twitter.com/beatthescam",
]

def org_logo(site):
    # PNG ImageObject rather than a bare SVG URL: some parsers (Bing
    # especially) drop SVG-only publisher logos.
    return {
        "@type": "ImageObject",
        "url": abs_url(site, "/favicon-512x512.png"),
        "width": 512,
        "height": 512,
    }

def publisher_org(site):
    return {
        "@type": "Organization",
        "name": site["site_name"],
        "url": site["domain"],
        "logo": org_logo(site),
        "sameAs": ORG_SAME_AS,
    }

def website_schema(site):
    return json_ld({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site["site_name"],
        "url": site["domain"],
        "description": site["tagline"],
        "publisher": publisher_org(site),
        "potentialAction": {
            "@type": "SearchAction",
            "target": abs_url(site, "/guides/?q={search_term_string}"),
            "query-input": "required name=search_term_string"
        }
    })

def org_schema(site):
    return json_ld({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site["site_name"],
        "url": site["domain"],
        "email": site["contact_email"],
        "logo": org_logo(site),
        "sameAs": ORG_SAME_AS,
    })

def page_schema(site, title, description, url, date_modified=None):
    """WebPage schema. `date_modified` is optional and emits ONLY dateModified —
    deliberately no datePublished, because a hand-authored hub has no reliable
    publication date and inventing one would fabricate a history (operator
    review 2026-07-27)."""
    data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": url,
        "isPartOf": {"@type": "WebSite", "name": site["site_name"], "url": site["domain"]}
    }
    if date_modified:
        data["dateModified"] = str(date_modified)
    return json_ld(data)

# Body Markdown subset: only root-relative, slug-safe internal links are
# accepted, so article data cannot inject attributes, scripts, or an
# unreviewed external destination. Used by _inline() when rendering and by
# _schema_plain() when flattening the same text for structured data.
_INTERNAL_MARKDOWN_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((/[a-z0-9/_-]+/?)\)", re.I)


def _schema_plain(text: str) -> str:
    """Strip the body Markdown subset so schema text matches what the reader
    sees. Backticks are cosmetic (<code> on the page), and an internal
    [label](/path/) renders as an anchor whose visible text is the label — so
    the schema must carry the label, not the raw markup. Google requires
    FAQPage content to match the visible answer."""
    text = str(text).strip().replace("`", "")
    return _INTERNAL_MARKDOWN_LINK_RE.sub(lambda m: m.group(1), text)


def faq_schema(pairs):
    if not pairs:
        return ""
    # Skip any malformed entries — must be 2-element sequences with non-empty strings
    valid = [
        (_schema_plain(q), _schema_plain(a))
        for item in pairs
        if isinstance(item, (list, tuple)) and len(item) == 2
        for q, a in [item]
        if str(q).strip() and str(a).strip()
    ]
    if not valid:
        return ""
    return json_ld({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in valid
        ]
    })

def article_schema(site, post, url, og_image_url=None):
    # Author is a real Person — backed by a verifiable LinkedIn profile and
    # cross-publication co-citation across CloudFintech, TuningDigital, and
    # SalesTap. Publisher is kept separate as the Organization that operates
    # the site (Beat the Scam). The Person.sameAs array is what Google reads
    # to confirm cross-publication identity for E-E-A-T.
    ap = site.get("author_profile") or {}
    author = {
        "@type": "Person",
        "name": site["author"],
        "url": site["domain"] + (site.get("editor_url") or "/about/"),
    }
    if ap.get("role"):
        author["jobTitle"] = ap["role"]
    if ap.get("image"):
        author["image"] = abs_url(site, ap["image"])
    if ap.get("sameAs"):
        author["sameAs"] = ap["sameAs"]
    published = post["date"]
    modified  = post.get("updated") or post.get("dateModified") or post["date"]
    image_url = og_image_url or abs_url(site, "/assets/og-image-v2.png")
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post["title"],
        "description": post["description"],
        "datePublished": published,
        "dateModified": modified,
        "author": author,
        "publisher": publisher_org(site),
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "image": [image_url],
        "articleSection": post["category"],
        "keywords": ", ".join(post["keywords"]),
        "inLanguage": site.get("locale", "en_GB").replace("_", "-"),
        "isAccessibleForFree": True,
    }
    # Do not infer an independent reviewer from dateModified. A reviewedBy
    # assertion is only appropriate when a distinct, named reviewer and their
    # credentials are recorded in the content data.
    reviewer = post.get("reviewed_by")
    if isinstance(reviewer, dict) and reviewer.get("name"):
        reviewed_by = {"@type": "Person", "name": reviewer["name"]}
        for key in ("url", "jobTitle"):
            if reviewer.get(key):
                reviewed_by[key] = reviewer[key]
        data["reviewedBy"] = reviewed_by
    return json_ld(data)


def speakable_schema(url, post):
    """WebPage speakable markup pointing voice/AI assistants at the Quick
    answer box. Emitted only for guides that carry a quick_answer field."""
    if not (post.get("quick_answer") or "").strip():
        return ""
    return json_ld({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": url,
        "url": url,
        "speakable": {
            "@type": "SpeakableSpecification",
            "cssSelector": [".quick-answer"],
        },
    })


def breadcrumb_schema(items):
    """items: list of (name, absolute_url) tuples representing the breadcrumb trail."""
    if not items:
        return ""
    return json_ld({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    })


def itemlist_schema(items, list_name=None):
    """items: list of (name, absolute_url) tuples."""
    if not items:
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "numberOfItems": len(items),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "url": url}
            for i, (name, url) in enumerate(items)
        ],
    }
    if list_name:
        data["name"] = list_name
    return json_ld(data)


_STEP_RE      = re.compile(r"\bStep\s+\d+\s*[:.\)\-–]\s*", re.IGNORECASE)
_PAREN_NUM_RE = re.compile(r"\((\d+)\)\s+")


def parse_numbered_steps(text: str):
    """Extract a list of step strings from a paragraph that contains
    explicit numbered markers like 'Step 1:' or '(1)'. Returns [] if
    fewer than 3 distinct steps are detectable."""
    text = (text or "").strip()
    if not text:
        return []
    # "Step N:" pattern
    if _STEP_RE.search(text):
        parts = _STEP_RE.split(text)
        steps = [p.strip().rstrip(".") for p in parts if p.strip()]
        if len(steps) >= 3:
            return steps
    # "(N)" pattern
    if _PAREN_NUM_RE.search(text):
        parts = _PAREN_NUM_RE.split(text)
        # split returns [pre, num, body, num, body, ...] -> take every other from index 2
        steps = []
        for i in range(2, len(parts), 2):
            piece = parts[i].strip().rstrip(";.")
            if piece:
                steps.append(piece)
        if len(steps) >= 3:
            return steps
    return []


def howto_schema(site, post, url):
    """Emit a HowTo schema when a section contains numbered user-action steps.

    Skips the 'how this scam works' section — that describes the attacker's
    procedure, not a how-to for the reader, and would mislead search engines.
    """
    SKIP_KEYWORDS = ("how this scam works", "how the scam works", "how scammers")
    for entry in post.get("sections", []) or []:
        if not (isinstance(entry, (list, tuple)) and len(entry) >= 2):
            continue
        title, body = entry[0], entry[1]
        tlow = (title or "").lower()
        if any(k in tlow for k in SKIP_KEYWORDS):
            continue
        body = _normalize_bullet_body(body)
        if not isinstance(body, str):
            continue
        steps = parse_numbered_steps(body)
        if not steps:
            continue
        return json_ld({
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": title,
            "description": f"{title} — guidance from the {post['title']} guide on {site['site_name']}.",
            # no totalTime: a fabricated fixed duration on every HowTo is
            # worse structured data than omitting the optional field.
            "step": [
                {
                    "@type": "HowToStep",
                    "position": i + 1,
                    "name": f"Step {i + 1}",
                    "text": str(s).replace("`", "")[:500],
                }
                for i, s in enumerate(steps[:8])
            ],
        })
    return ""


# ─── COMPONENTS ────────────────────────────────────────────────────────────

def render_card(post):
    label = category_label(post["category"])
    updated = post.get("updated") or post.get("dateModified")
    date_label = (f'Updated {html.escape(updated)}'
                  if updated and updated != post["date"]
                  else f'Published {html.escape(post["date"])}')
    searchable = (post["title"] + " " + post["description"] + " " + post["category"] + " " + " ".join(post["keywords"])).lower()
    return f'''
    <article class="card guide-card" data-searchable="{html.escape(searchable)}">
      <div class="eyebrow">{html.escape(label)}</div>
      <h3><a href="/guides/{post["slug"]}/">{html.escape(post["title"])}</a></h3>
      <p>{html.escape(post["description"])}</p>
      <p class="meta">{date_label}</p>
    </article>
    '''.strip()


# ─── PAGE RENDERERS ────────────────────────────────────────────────────────

def render_home(site, posts, categories, research_reports=None):
    post_count = len(posts)
    cat_count  = len(categories)

    featured = "".join(render_card(p) for p in posts[:6])

    category_cards = []
    for cat, items in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)[:8]:
        label = category_label(cat)
        desc  = category_description(cat)
        category_cards.append(f'''
        <article class="card category-card">
          <h3><a href="/categories/{slugify(cat)}/">{html.escape(label)}</a></h3>
          <p>{html.escape(desc)}</p>
        </article>
        '''.strip())

    latest_links = "".join(
        f'<li><a href="/guides/{p["slug"]}/">{html.escape(p["title"])}</a></li>'
        for p in posts[:5]
    )

    faq_pairs = [
        ("Does Beat the Scam verify messages for me?",
         "The site provides educational checklists and examples so readers can verify suspicious messages themselves through official channels. The AI scam checker can give you an instant verdict on a specific message."),
        ("Can social media ads or polished emails still be scams?",
         "Yes. Presentation quality is not proof of legitimacy. Verification path matters more than appearance."),
        ("What should I do first if I already paid a scammer?",
         "Contact your bank or card issuer immediately, preserve evidence, secure compromised accounts, and stop further payments while you verify the situation.")
    ]
    faq_html = "".join(
        f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>'
        for q, a in faq_pairs
    )

    research_html = ""
    if research_reports:
        latest = research_reports[0]
        bing = latest["bing_ai"]
        google = latest["google_search"]
        research_html = f'''
    <section class="section" aria-labelledby="latest-research-heading">
      <div class="wrap">
        <div class="callout research-promo">
          <div>
            <div class="kicker">Original data · {html.escape(latest["published"])}</div>
            <h2 id="latest-research-heading">Latest visibility research</h2>
            <p>Our transparent monthly snapshot tracks how UK scam guidance appears in Google Search and in Bing-powered AI answers. The data, method and limitations are published for scrutiny.</p>
            <div class="hero-actions">
              <a class="btn btn-primary" href="/research/{html.escape(latest['slug'])}/">Read the latest report</a>
              <a class="btn btn-secondary" href="/research/methodology/">See the research method</a>
            </div>
          </div>
          <div class="research-promo-metrics" aria-label="Latest research headline figures">
            <div><strong>{bing['total_citations']:,}</strong><span>Bing AI citations</span></div>
            <div><strong>{google['impressions']:,}</strong><span>Google impressions</span></div>
            <div><strong>{bing['cited_page_count']:,}</strong><span>pages cited by Bing AI</span></div>
          </div>
        </div>
      </div>
    </section>
        '''

    content = f'''
    <section class="hero">
      <div class="wrap hero-grid">
        <div class="hero-panel">
          <div class="kicker">UK Consumer Protection</div>
          <h1>Check scams. Protect your money.</h1>
          <p class="lead">Beat the Scam helps you review suspicious texts, emails, websites, calls, job offers, crypto pitches, and payment requests before money or data is lost.</p>
          <div class="hero-actions">
            <a class="btn btn-primary" href="/check/">Check a message</a>
            <a class="btn btn-recovery" href="/recovery/">Recover after a scam</a>
            <a class="btn btn-secondary" href="/guides/">Browse guides</a>
          </div>
          <div class="hero-points">
            <div class="hero-point"><strong>{post_count}</strong><span>guides published</span></div>
            <div class="hero-point"><strong>{cat_count}</strong><span>scam categories</span></div>
            <div class="hero-point"><strong>Free</strong><span>no account needed</span></div>
          </div>
        </div>
        <div class="hero-side">
          <section class="search-panel" id="search-start">
            <h3>Search scam topics</h3>
            <p class="search-note">Try terms like &#8220;Royal Mail text&#8221;, &#8220;job scam&#8221;, &#8220;bank transfer&#8221;, or &#8220;crypto withdrawal fee&#8221;.</p>
            <form class="search-box" action="/guides/" method="get">
              <input type="search" name="q" aria-label="Search scam guides" placeholder="Search guides and scam types">
              <button class="btn btn-dark" type="submit">Search</button>
            </form>
          </section>
          <section class="feature-panel">
            <h3>Latest scam alerts</h3>
            <ul class="list-clean">{latest_links}</ul>
          </section>
          <section class="callout">
            <h3>Quick verification rule</h3>
            <p>Never rely on the link, phone number, QR code, or payment details supplied by the suspicious message itself. Open the official route yourself.</p>
          </section>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="stat-strip">
          <div class="metric-card"><strong>Practical checks</strong><span>Fast steps you can use before clicking a link, paying a fee, or sharing personal information.</span></div>
          <div class="metric-card"><strong>UK-focused advice</strong><span>Guides written for common scams targeting UK consumers, delivery services, marketplaces, and payment methods.</span></div>
          <div class="metric-card"><strong>Plain-English alerts</strong><span>No jargon, no panic language, and no assumptions that every suspicious message is genuine.</span></div>
          <div class="metric-card"><strong>AI scam checker</strong><span>Paste a suspicious message and get an instant analysis powered by Claude AI &#8212; free, no account needed.</span></div>
        </div>
      </div>
    </section>

    {research_html}

    <section class="section">
      <div class="wrap">
        <div class="section-head">
          <div>
            <h2>Scam categories</h2>
            <p>Find guides by scam type. Each category covers warning signs, verification steps, and what to do if you&#8217;ve already interacted.</p>
          </div>
          <a href="/categories/">View all categories</a>
        </div>
        <div class="category-grid">{"".join(category_cards)}</div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="section-head">
          <div>
            <h2>Latest guides</h2>
            <p>Practical guides for the most commonly reported scams affecting UK consumers.</p>
          </div>
          <a href="/guides/">Browse all guides</a>
        </div>
        <div class="grid-3">{featured}</div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="checker-promo">
          <div class="checker-promo-text">
            <h2>Not sure about a message?</h2>
            <p>Paste a suspicious text, email, URL, or job offer into the free AI scam checker and get an instant plain-English verdict &#8212; powered by Claude AI.</p>
            <a class="btn btn-primary" href="/check/">Check a suspicious message &#8594;</a>
          </div>
          <div class="checker-promo-examples">
            <p class="note"><strong>Works with:</strong></p>
            <ul class="list-clean">
              <li>Suspicious texts and SMS</li>
              <li>Unexpected emails</li>
              <li>Unfamiliar website URLs</li>
              <li>Unusual payment requests</li>
              <li>Job offers that seem too good</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap grid-2">
        <section>
          <h2>How to spot a scam quickly</h2>
          <div class="home-checklist">
            <div class="item"><span class="icon-dot"></span><div><strong>Slow the interaction down</strong><p>Urgency and secrecy are common scam tools. Speed benefits the fraudster, not you.</p></div></div>
            <div class="item"><span class="icon-dot"></span><div><strong>Verify through a clean route</strong><p>Open the official site or app yourself. Call published numbers, not the ones in the message.</p></div></div>
            <div class="item"><span class="icon-dot"></span><div><strong>Protect one-time codes and payment details</strong><p>Security codes authorise actions. Treat them like passwords.</p></div></div>
            <div class="item"><span class="icon-dot"></span><div><strong>Pause before irreversible payments</strong><p>Bank transfer and crypto payments need stronger checks than card payments.</p></div></div>
          </div>
        </section>
        <section class="faq-panel">
          <h2>Common questions</h2>
          {faq_html}
        </section>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="section-head"><div><h2>About the site</h2></div></div>
        <div class="trust-grid">
          <article class="trust-card"><h3>Plain-English guidance</h3><p>Every guide is written to be understandable under pressure &#8212; short sections, clear headings, and practical next steps.</p></article>
          <article class="trust-card"><h3>UK-specific content</h3><p>Guides focus on scams reported in the UK: HMRC impersonation, delivery fraud, bank transfer pressure, and UK marketplace platforms.</p></article>
          <article class="trust-card"><h3>No scare tactics</h3><p>The site does not assume every suspicious message is a scam. It helps you verify systematically using official channels.</p></article>
        </div>
      </div>
    </section>
    '''

    schema = website_schema(site) + org_schema(site) + faq_schema(faq_pairs)
    return make_base(
        content,
        title=f'{site["site_name"]} | Scam Alerts, Checks & Protection Guides',
        og_title=f'{site["site_name"]} | Scam Alerts, Checks & Protection Guides',
        description='Free scam alerts, verification guides, and an AI scam checker for suspicious texts, emails, websites, calls, and payment requests.',
        canonical=site["domain"] + '/',
        schema=schema,
        site=site,
        ads_mode="none",
    )


GUIDES_PER_PAGE = 30


def _guides_page_url(site, page_num: int) -> str:
    if page_num <= 1:
        return site["domain"] + "/guides/"
    return site["domain"] + f"/guides/page/{page_num}/"


def render_guides_index_page(site, page_posts, page_num: int, total_pages: int, all_posts):
    cards = ''.join(render_card(p) for p in page_posts)

    page_label = "" if page_num == 1 else f" — page {page_num} of {total_pages}"
    canonical = _guides_page_url(site, page_num)
    prev_url  = _guides_page_url(site, page_num - 1) if page_num > 1 else None
    next_url  = _guides_page_url(site, page_num + 1) if page_num < total_pages else None

    pagination_links = []
    if prev_url:
        pagination_links.append(f'<a class="btn btn-secondary" rel="prev" href="{prev_url}">&larr; Previous</a>')
    pagination_links.append(f'<span class="meta">Page {page_num} of {total_pages}</span>')
    if next_url:
        pagination_links.append(f'<a class="btn btn-secondary" rel="next" href="{next_url}">Next &rarr;</a>')
    pagination_html = (
        '<nav class="pagination" aria-label="Guides pagination" style="display:flex;gap:1rem;align-items:center;justify-content:center;margin:2rem 0">'
        + " ".join(pagination_links)
        + '</nav>'
        if total_pages > 1 else ""
    )

    h1 = "Scam guides" if page_num == 1 else f"Scam guides — page {page_num}"
    intro = ("Browse all published guides by scam type, payment method, platform, or impersonation pattern."
             if page_num == 1 else
             f"Page {page_num} of {total_pages} — older guides covering UK scam patterns, payment fraud, and impersonation tactics.")

    search_box = (
        '<div class="search-box" style="max-width:720px">'
        '<input id="pageSearch" type="search" placeholder="Search all guides" aria-label="Search all guides">'
        '</div>'
    ) if page_num == 1 else ""

    # H2 between H1 and the card grid keeps heading hierarchy correct
    # (Semrush flagged H1→H3 skips on guides/ + guides/page/N — 5 pages
    # in the 2026-05-30 audit). Card titles are <h3>, so we need an <h2>
    # ancestor before them.
    grid_heading = ("Latest guides" if page_num == 1
                    else f"Older guides — page {page_num}")
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / Guides{page_label}</div>
        <h1>{html.escape(h1)}</h1>
        <p class="lead">{html.escape(intro)}</p>
        {search_box}
      </div>
    </section>
    <section class="section">
      <div class="wrap">
        <h2>{html.escape(grid_heading)}</h2>
        <div class="grid-3" id="guideGrid">{cards}</div>
        <div class="grid-3" id="searchResults" hidden></div>
        <p id="searchEmpty" class="lead" hidden>No guides match your search. Try a different keyword.</p>
        {pagination_html}
      </div>
    </section>
    '''

    if page_num == 1:
        # Site-wide guide search: filters the full /search.json index (every
        # guide), not just the cards rendered on this page. Empty query restores
        # the normal latest-guides grid + pagination.
        content += '''
    <script>
      (function() {
        var input = document.getElementById('pageSearch');
        if (!input) return;
        var grid = document.getElementById('guideGrid');
        var results = document.getElementById('searchResults');
        var empty = document.getElementById('searchEmpty');
        var pager = document.querySelector('.pagination');
        var indexPromise = null;
        function loadIndex() {
          if (!indexPromise) {
            indexPromise = fetch('/search.json')
              .then(function(r) { return r.ok ? r.json() : []; })
              .catch(function() { return []; });
          }
          return indexPromise;
        }
        function esc(s) {
          return String(s == null ? '' : s).replace(/[&<>"]/g, function(c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
          });
        }
        function render(items) {
          results.innerHTML = items.map(function(it) {
            return '<article class="card guide-card">' +
              '<div class="eyebrow">' + esc(it.category) + '</div>' +
              '<h3><a href="' + esc(it.url) + '">' + esc(it.title) + '</a></h3>' +
              '<p>' + esc(it.description) + '</p>' +
            '</article>';
          }).join('');
        }
        function showSearch(on) {
          results.hidden = !on;
          grid.hidden = on;
          if (pager) pager.style.display = on ? 'none' : '';
        }
        function run(value) {
          var q = (value || '').toLowerCase().trim();
          if (!q) { showSearch(false); empty.hidden = true; return; }
          loadIndex().then(function(items) {
            var hits = items.filter(function(it) {
              var hay = (it.title + ' ' + it.description + ' ' + it.category + ' ' +
                         (it.keywords || []).join(' ')).toLowerCase();
              return hay.indexOf(q) !== -1;
            });
            render(hits);
            showSearch(true);
            empty.hidden = hits.length > 0;
          });
        }
        input.addEventListener('input', function(e) { run(e.target.value); });
        var params = new URLSearchParams(window.location.search);
        if (params.get('q')) { input.value = params.get('q'); run(input.value); }
      })();
    </script>
    '''

    # ItemList schema for this page only (so search engines can read the page's actual contents)
    item_pairs = [(p["title"], site["domain"] + f"/guides/{p['slug']}/") for p in page_posts]
    breadcrumbs = [("Home", site["domain"] + "/"), ("Guides", site["domain"] + "/guides/")]
    if page_num > 1:
        breadcrumbs.append((f"Page {page_num}", canonical))

    schema = (
        page_schema(site, h1, 'Browse all scam guides published on Beat the Scam.', canonical)
        + itemlist_schema(item_pairs, list_name=h1)
        + breadcrumb_schema(breadcrumbs)
    )
    description = (
        'Browse all published UK scam guides by type — from phishing emails and fake texts to crypto fraud, job scams, and marketplace abuse. Free advice, no account needed.'
        if page_num == 1 else
        f'Older UK scam guides, page {page_num} of {total_pages}. Covers phishing, payment fraud, marketplace scams, and impersonation patterns.'
    )
    return make_base(
        content,
        title=seo_title(h1, site["site_name"]),
        description=seo_description(description),
        canonical=canonical,
        schema=schema,
        site=site,
        prev_url=prev_url,
        next_url=next_url,
        ads_mode="none",
    )


def render_categories_index(site, categories):
    items = []
    for cat, posts in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        label = category_label(cat)
        desc  = category_description(cat)
        items.append(f'''
        <article class="card category-card">
          <h3><a href="/categories/{slugify(cat)}/">{html.escape(label)}</a></h3>
          <p>{html.escape(desc)}</p>
          <p class="meta">{len(posts)} guide{"s" if len(posts) != 1 else ""}</p>
        </article>
        '''.strip())
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / Categories</div>
        <h1>Scam categories</h1>
        <p class="lead">Browse guides by scam type. Each category covers a specific pattern &#8212; from SMS phishing to marketplace fraud to government impersonation.</p>
      </div>
    </section>
    <section class="section"><div class="wrap"><div class="category-grid">{"".join(items)}</div></div></section>
    '''
    cat_items = [
        (category_label(cat), site["domain"] + f"/categories/{slugify(cat)}/")
        for cat, _ in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
    ]
    breadcrumbs = [("Home", site["domain"] + "/"), ("Categories", site["domain"] + "/categories/")]
    schema = (
        page_schema(site, 'Categories', 'Browse scam guide categories.', site['domain'] + '/categories/')
        + itemlist_schema(cat_items, list_name='Scam categories')
        + breadcrumb_schema(breadcrumbs)
    )
    return make_base(
        content,
        title=f'Categories | {site["site_name"]}',
        description='Browse all scam categories and find guides relevant to the message or situation you are checking.',
        canonical=site['domain'] + '/categories/',
        schema=schema,
        site=site,
        ads_mode="none",
    )


def render_category_page(site, category, posts, all_categories=None, hub=None):
    label = category_label(category)
    desc  = category_description(category)
    slug  = slugify(category)

    # Related categories — up to 6 sibling categories, sorted by post count
    related_cats_html = ""
    if all_categories:
        siblings = [
            (cat, items) for cat, items in sorted(all_categories.items(), key=lambda x: len(x[1]), reverse=True)
            if cat != category
        ][:6]
        if siblings:
            links = "".join(
                f'<li><a href="/categories/{slugify(c)}/">{html.escape(category_label(c))}</a> <span class="meta">({len(items)} guides)</span></li>'
                for c, items in siblings
            )
            related_cats_html = f'<section class="section"><div class="wrap"><h2>Browse other scam categories</h2><ul class="list-clean">{links}</ul></div></section>'

    # Optional pillar hub content (intro + sections above the guide grid; FAQ
    # below it). Bodies are trusted HTML with hand-picked internal links to the
    # cluster's guides, so they're rendered raw (not escaped).
    hub_body_html = hub_faq_html = ""
    hub_faq_pairs = []
    if hub:
        intro = canonicalize_internal_guide_paths(hub.get("intro", ""))
        secs = "".join(
            f'<section class="section"><div class="wrap"><h2>{html.escape(h)}</h2>{canonicalize_internal_guide_paths(b)}</div></section>'
            for h, b in hub.get("sections", [])
        )
        hub_body_html = (f'<section class="section"><div class="wrap">{intro}</div></section>' if intro else "") + secs
        hub_faq_pairs = [(q, a) for q, a in hub.get("faq", []) if q and a]
        if hub_faq_pairs:
            items = "".join(
                f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>'
                for q, a in hub_faq_pairs
            )
            hub_faq_html = f'<section class="section"><div class="wrap"><h2>Common questions</h2><div class="faq-panel">{items}</div></div></section>'

    # Trust layer for hubs (operator review 2026-07-27): ten long YMYL pages
    # carrying platform policies, reporting routes, legislation and statistics
    # should not make a reader or an answer engine infer the evidence from prose.
    # Reuses the guide source-block markup so the two surfaces look identical.
    hub_trust_html = ""
    if hub:
        hub_sources = [(l, u) for l, u in (hub.get("sources_checked") or []) if l and u]
        reviewed = str(hub.get("updated") or "").strip()
        bits = []
        if hub_sources:
            lis = "".join(
                f'<li><a href="{html.escape(u)}" rel="noopener noreferrer" target="_blank">'
                f'{html.escape(l)}</a></li>' for l, u in hub_sources
            )
            bits.append(f'<h2>Sources checked</h2><ul class="sources-checked">{lis}</ul>')
        if reviewed:
            bits.append(
                f'<p class="meta">Last reviewed <time itemprop="dateModified" '
                f'datetime="{html.escape(reviewed)}">{html.escape(reviewed)}</time>. '
                f'Reporting routes are checked against our verified canon of official UK sources. '
                f'Read about <a href="/methodology/">how Beat the Scam writes guides</a>.</p>')
        if bits:
            hub_trust_html = ('<section class="section"><div class="wrap">'
                              + "".join(bits) + '</div></section>')

    # A hub's differentiated title/description must be the SAME string across the
    # title element, the visible H1, the lead and the schema name — otherwise the
    # carefully distinguished metadata contradicts the page a crawler renders
    # (operator review, 2026-07-27). The short label stays in the breadcrumb,
    # where a compact name is what a reader wants.
    page_title = hub.get("title") if hub and hub.get("title") else label
    page_desc  = hub.get("description") if hub and hub.get("description") else desc

    grid_heading = f"All {html.escape(label.lower())} guides" if hub else f"Latest {html.escape(label.lower())}"
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/categories/">Categories</a> / {html.escape(label)}</div>
        <h1>{html.escape(page_title)}</h1>
        <p class="lead">{html.escape(page_desc)}</p>
      </div>
    </section>
    {hub_body_html}
    <section class="section"><div class="wrap"><h2>{grid_heading}</h2><div class="grid-3">{"".join(render_card(p) for p in posts)}</div></div></section>
    {hub_faq_html}{hub_trust_html}
    {related_cats_html}
    '''
    canonical = site['domain'] + f'/categories/{slug}/'
    item_pairs  = [(p["title"], site["domain"] + f"/guides/{p['slug']}/") for p in posts]
    breadcrumbs = [
        ("Home",          site["domain"] + "/"),
        ("Categories",    site["domain"] + "/categories/"),
        (label,           canonical),
    ]
    schema = (
        page_schema(site, page_title, page_desc, canonical,
                    date_modified=(hub or {}).get('updated'))
        + itemlist_schema(item_pairs, list_name=label)
        + breadcrumb_schema(breadcrumbs)
        + (faq_schema(hub_faq_pairs) if hub_faq_pairs else "")
    )
    return make_base(
        content,
        # brand=False when a reviewed hub title is in play, exactly as guide
        # pages do. With the ' | Beat the Scam' suffix enabled, all ten hub
        # titles were truncated away from the H1 and the schema `name` —
        # three of them into visibly broken endings such as "Travel Scams UK:
        # Fake Holidays, Flights &" (operator review, 2026-07-29,
        # `hubs-v10-c.md` §5). Every full hub title is already inside the
        # 60-char budget, so the suffix bought nothing and cost the title.
        # Plain category pages keep the brand suffix: their labels are short.
        title=seo_title(page_title, site["site_name"], brand=not (hub and hub.get("title"))),
        description=seo_description(page_desc),
        canonical=canonical,
        schema=schema,
        site=site,
        ads_mode=hub_ads_mode(slug, hub) if hub else "none",
    )


def _keyword_set(post):
    return {(k or "").lower().strip() for k in post.get("keywords", []) if k}


def related_posts(posts, current, count=4):
    """Score-based related-post picker.

    Scoring:
      +3  shared category
      +2  per shared keyword token
      +1  per shared significant word in the title (length >= 5, not common stop)
    Topics that share more keywords with the current post bubble up — this
    gives much better cross-category recommendations than same-category-only.
    """
    current_sig   = topic_signature(current)
    current_kws   = _keyword_set(current)
    title_tokens  = {
        t for t in re.findall(r"[a-z]{5,}", current["title"].lower())
        if t not in {"guide", "scams", "scam", "checklist", "messages", "message", "online"}
    }
    seen = {current_sig}

    scored = []
    for p in posts:
        if p["slug"] == current["slug"]:
            continue
        sig = topic_signature(p)
        if sig in seen:
            continue
        score = 0
        if p["category"] == current["category"]:
            score += 3
        shared_kw = current_kws & _keyword_set(p)
        score += 2 * len(shared_kw)
        p_title_tokens = {t for t in re.findall(r"[a-z]{5,}", p["title"].lower())}
        score += len(title_tokens & p_title_tokens)
        if score > 0:
            scored.append((score, p, sig))

    # Score desc, then date desc — equal-score ties go to the NEWEST post,
    # matching the newest-first convention used everywhere else.
    scored.sort(key=lambda x: x[1]["date"], reverse=True)
    scored.sort(key=lambda x: -x[0])  # stable: preserves date order within a score

    out = []
    used_sigs = set(seen)
    for _, p, sig in scored:
        if sig in used_sigs:
            continue
        used_sigs.add(sig)
        out.append(p)
        if len(out) >= count:
            return out

    # Fallback — if nothing scored, fill from same-category, then anywhere.
    if len(out) < count:
        for p in posts:
            if len(out) >= count:
                break
            if p["slug"] == current["slug"]:
                continue
            sig = topic_signature(p)
            if sig in used_sigs:
                continue
            used_sigs.add(sig)
            out.append(p)
    return out


_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
def _inline(text: str) -> str:
    """html-escape, then render `…` markdown code-spans as <code>…</code>.
    Used for example scam domains / messages and technical tokens (URLs, emails)
    so they read as literal, non-clickable strings. Phones are left un-backticked
    in content so linkify_phones can still wrap them in tel: anchors."""
    escaped = html.escape(text)
    escaped = _INLINE_CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    # Content data can use a deliberately narrow Markdown subset for internal
    # links. Only root-relative, slug-safe paths are accepted, so an article
    # cannot inject attributes, scripts, or an unreviewed external destination.
    return _INTERNAL_MARKDOWN_LINK_RE.sub(
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', escaped
    )


def _render_section_body(para) -> str:
    """Render a section body that may freely interleave prose paragraphs and
    '- ' bullet lines: consecutive bullets collapse into one <ul>, runs of
    prose are paragraph-split (Semrush "too-long paragraph" fix) into <p>.
    Backward compatible with pure-prose and pure-bullet bodies, which render
    exactly as the old if/else did."""
    para = _normalize_bullet_body(para)
    parts, prose, bullets = [], [], []
    def flush_prose():
        if prose:
            text = "\n".join(prose).strip("\n")
            if text.strip():
                parts.extend(f"<p>{_inline(p)}</p>" for p in split_into_paragraphs(text))
            prose.clear()
    def flush_bullets():
        if bullets:
            inner = "".join(f"<li>{_inline(b)}</li>" for b in bullets if b)
            if inner:
                parts.append(f"<ul>{inner}</ul>")
            bullets.clear()
    for line in para.split("\n"):
        st = line.strip()
        if st.startswith("- ") or st == "-":
            flush_prose(); bullets.append(st.lstrip("-").strip())
        else:
            flush_bullets(); prose.append(line)
    flush_prose(); flush_bullets()
    return "".join(parts)


def sources_checked_block(post: dict) -> str:
    """Render the optional per-guide 'Sources checked' citation list.

    post['sources_checked'] is a list of [label, url] pairs added by the
    human fact-check review pass (docs/review/<slug>-c.md), not part of the
    AI generation schema. Rendered as real <a> tags directly (unlike section/
    FAQ bodies, which are html.escape'd — see _inline — so markdown [text](url)
    links there would render as literal broken text, not clickable links).
    Uses the same rel/target convention as the other genuine editorial
    citations in this template (plain noopener/noreferrer, no nofollow —
    that's reserved for the affiliate cards, see affiliate_block()).
    """
    items = post.get("sources_checked") or []
    if not items:
        return ""
    lis = "".join(
        f'<li><a href="{html.escape(url)}" rel="noopener noreferrer" target="_blank">{html.escape(label)}</a></li>'
        for label, url in items
    )
    return f'<h2>Sources checked</h2><ul class="sources-checked">{lis}</ul>'


def evidence_snapshot_block(post: dict) -> str:
    """Render optional page-specific evidence and illustrative examples.

    This is intentionally opt-in. A generic template table on every guide
    would add markup without adding evidence; only guides carrying reviewed
    `evidence` or `message_examples` data get the block.
    """
    evidence = post.get("evidence") or []
    examples = post.get("message_examples") or []
    if not evidence and not examples:
        return ""

    parts = ['<section class="evidence-snapshot" aria-labelledby="evidence-snapshot-heading">',
             '<h2 id="evidence-snapshot-heading">Evidence snapshot</h2>']
    checked = post.get("updated") or post.get("dateModified") or post.get("date")
    if checked:
        parts.append(f'<p class="evidence-date">Checked against the cited official sources on {html.escape(checked)}.</p>')

    if evidence:
        rows = []
        for item in evidence:
            signal = html.escape(str(item.get("signal", "")))
            finding = _inline(str(item.get("finding", "")))
            basis = _inline(str(item.get("basis", "")))
            rows.append(
                '<tr>'
                f'<th scope="row">{signal}</th>'
                f'<td>{finding}</td>'
                f'<td>{basis}</td>'
                '</tr>'
            )
        parts.append(
            '<div class="evidence-table-wrap"><table class="evidence-table">'
            '<thead><tr><th scope="col">Check</th><th scope="col">What it means</th><th scope="col">Official basis</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
        )

    if examples:
        parts.append('<div class="message-examples">')
        for item in examples:
            label = html.escape(str(item.get("label", "Illustrative example")))
            message = html.escape(str(item.get("message", "")))
            assessment = _inline(str(item.get("assessment", "")))
            parts.append(
                '<article class="message-example">'
                f'<h3>{label}</h3><code>{message}</code><p>{assessment}</p>'
                '</article>'
            )
        parts.append('</div>')

    parts.append('<p class="evidence-note">Examples are reconstructed from documented scam patterns; they are not presented as verbatim messages received by the publisher.</p></section>')
    return "".join(parts)


def render_post(site, post, all_posts, affiliates=None, sources=None, link_map=None, slug_titles=None):
    url   = site['domain'] + f'/guides/{post["slug"]}/'
    label = category_label(post["category"])
    mins  = reading_time(post)
    cat_slug = slugify(post["category"])

    published = post["date"]
    updated   = post.get("updated") or post.get("dateModified") or published
    updated_html = ""
    if updated and updated != published:
        updated_html = (f' &middot; <time itemprop="dateModified" datetime="{html.escape(updated)}">'
                        f'Updated {html.escape(updated)}</time>')

    section_ids   = []
    section_parts = []
    for title, para in post['sections']:
        sid = slugify(title)
        section_ids.append((sid, title))
        section_parts.append(f'<h2 id="{sid}">{html.escape(title)}</h2>{_render_section_body(para)}')

    toc      = "".join(f'<li><a href="#{sid}">{html.escape(t)}</a></li>' for sid, t in section_ids)
    faq_html = "".join(f'<details><summary>{_inline(q)}</summary><p>{_inline(a)}</p></details>' for q, a in post['faq'])
    # No visible keyword badges. Printing three exact-match search terms under
    # every headline made 185 guides look machine-templated rather than written,
    # which is the impression the corpus can least afford (audit, 2026-07-31).
    # The keywords still drive search.json, related guides and the sitemap —
    # they were never load-bearing for the reader.
    related  = "".join(
        f'<a href="/guides/{p["slug"]}/">{html.escape(p["title"])}<span class="meta">{html.escape(category_label(p["category"]))} &middot; {p["date"]}</span></a>'
        for p in related_posts(all_posts, post)
    )

    # Named byline backed by a real Person — Alex Bacsa, founder & editor.
    # Cross-publication identity (CloudFintech, TuningDigital, SalesTap) is
    # asserted via the Person.sameAs array in article_schema() above.
    author_url = site.get("editor_url") or "/about/"
    byline = f'<a href="{html.escape(author_url)}" rel="author">{html.escape(site["author"])}</a>'

    # Honest review attestation: only guides carrying a real `updated` date have
    # been through human editorial review (the rest show the automated gate +
    # publish date only). Going forward the human-review publishing gate stamps
    # `updated` when the editor approves a guide.
    role = (site.get("author_profile") or {}).get("role") or "Editor"
    if updated != published:
        review_note = (f'Editorially updated by {byline}, {html.escape(role)}, '
                       f'on {html.escape(updated)}.')
    else:
        review_note = f'Published {html.escape(published)}.'

    # Page-specific 2–3 sentence direct answer, rendered above the generic Key
    # rule so AI assistants and skimming readers get the guide's core verdict
    # first. Optional per post; paired with speakable_schema() below.
    qa = (post.get("quick_answer") or "").strip()
    qa_html = ""
    if qa:
        qa_html = f'\n        <div class="quick-answer"><strong>Quick answer:</strong> {_inline(qa)}</div>'

    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/guides/">Guides</a> / <a href="/categories/{cat_slug}/">{html.escape(label)}</a> / <span class="bc-title">{html.escape(post["title"])}</span></div>
      </div>
    </section>
    <section class="wrap article-layout">
      <article class="article" itemscope itemtype="https://schema.org/Article">
        <meta itemprop="inLanguage" content="en-GB">
        <div class="eyebrow">{html.escape(label)}</div>
        <h1 itemprop="headline">{html.escape(post["title"])}</h1>
        <p class="lead" itemprop="description">{html.escape(post["hero"])}</p>
        <p class="meta">
          <span itemprop="author" itemscope itemtype="https://schema.org/Person">By <span itemprop="name">{byline}</span></span>
          &middot; <time itemprop="datePublished" datetime="{html.escape(published)}">Published {html.escape(published)}</time>{updated_html}
          &middot; {mins} min read
        </p>
        {qa_html}
        <div class="notice"><strong>Key rule:</strong> verify through an official route you opened yourself, not the link, number, app, or payment details supplied by the suspicious message.</div>
        <aside class="do-now" aria-label="What to do if you are being targeted right now">
          <p class="do-now-title">Being targeted right now? Do this</p>
          <ol>
            <li><strong>Stop.</strong> Don&#8217;t pay, transfer money, or share passwords, PINs, or one-time codes.</li>
            <li><strong>Contact your bank</strong> on the number on the back of your card if your money or details may be at risk.</li>
            <li><strong>Use the right recovery route.</strong> Follow the <a href="/recovery/">payment, account and identity checklist</a>; reporting differs in Scotland.</li>
          </ol>
        </aside>
        {evidence_snapshot_block(post)}
        <div class="toc"><strong>On this page</strong><ol>{toc}</ol></div>
        {"".join(section_parts)}
        <h2>Frequently asked questions</h2>
        <div class="faq">{faq_html}</div>
        {sources_checked_block(post)}
        <div class="notice" style="margin-top:2rem">
          <strong>Think you&#8217;ve spotted a scam?</strong>
          Use the <a href="/check/">AI scam checker</a> for an automated second opinion, or report it to
          {police_route_html(sources, phone=False, url=False)}.
        </div>
        <p class="meta" style="margin-top:1.4rem">Reporting routes in this guide are checked against our verified canon of official UK sources &#8212; {police_route_html(sources, phone=False, url=False)}, the <a href="{_r(sources, 'ncsc-sers')['info_url']}" rel="noopener" target="_blank">National Cyber Security Centre</a>, and the consumer service for each nation &#8212; by an automated accuracy gate before publication. {review_note} Read about <a href="/methodology/">how Beat the Scam writes guides</a>.</p>
      </article>
      <aside class="sidebar">
        <section class="sidebar-card">
          <h3>Fast checks</h3>
          <ul class="warning-list">
            <li>Pause before sending money or credentials</li>
            <li>Verify with an official site, app, or number</li>
            <li>Never share one-time passcodes</li>
            <li>Be sceptical of bank transfer pressure</li>
          </ul>
        </section>
        <section class="sidebar-card">
          <h3>Related guides</h3>
          <div class="related-links">{related}</div>
        </section>
        <section class="sidebar-card">
          <h3>Report this scam</h3>
          {report_block(sources)}
        </section>
        <section class="sidebar-card">
          <h3>Not sure?</h3>
          <p class="note">Paste the suspicious message into the free AI checker for an instant plain-English verdict.</p>
          <a class="btn btn-primary" href="/check/" style="width:100%;margin-top:.5rem;text-align:center">Check a message</a>
        </section>
        {affiliate_block(post, affiliates or [])}
      </aside>
    </section>
    '''

    breadcrumbs = [
        ("Home",         site["domain"] + "/"),
        ("Guides",       site["domain"] + "/guides/"),
        (label,          site["domain"] + f"/categories/{cat_slug}/"),
        (post["title"], url),
    ]
    og_image_url = abs_url(site, f"/assets/og/{post['slug']}.png")
    schema = (
        article_schema(site, post, url, og_image_url=og_image_url)
        + faq_schema(post['faq'])
        + breadcrumb_schema(breadcrumbs)
        + howto_schema(site, post, url)
        + speakable_schema(url, post)
    )

    # Linkify passes run on the article body ONLY, before make_base() wraps it
    # in the shared header/newsletter-band/footer chrome. Running them on the
    # full page (as before) let a keyword match inside that boilerplate copy —
    # not just the article — so every guide picked up an identical, unrelated
    # auto-link (e.g. the newsletter band's "the latest UK scams" text).
    content = canonicalize_internal_guide_paths(content)
    content = linkify_bare_paths(content, slug_titles or {})
    content = apply_internal_links(content, post['slug'], link_map or {})
    content = linkify_phones(content)
    # Optional blocks can leave indentation-only lines in the article template.
    # Keep generated HTML clean so repository whitespace checks remain useful.
    content = "\n".join(line.rstrip() for line in content.splitlines())

    return make_base(
        content,
        title=seo_title(post["title"], site["site_name"], brand=False),
        og_title=post['title'],
        description=pick_description(post),
        canonical=url,
        schema=schema,
        site=site,
        og_type='article',
        og_image=og_image_url,
        robots="index,follow",
        ads_mode=post_ads_mode(post),
    )


def render_check_page(site, sources):
    content = '''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / Check a message</div>
        <h1>AI scam checker</h1>
        <p class="lead">Paste a suspicious message, email, URL, or job offer below and get an instant plain-English verdict powered by Claude AI.</p>
      </div>
    </section>

    <section class="section">
      <div class="wrap checker-layout">
        <div class="checker-form-col">
          <div class="card checker-card">
            <div class="checker-type-row">
              <label for="scamType" class="checker-label">What type of message is it?</label>
              <select id="scamType" class="checker-select">
                <option value="SMS or text message">SMS or text message</option>
                <option value="email">Email</option>
                <option value="phone call">Phone call</option>
                <option value="website or URL">Website or URL</option>
                <option value="job offer">Job offer</option>
                <option value="social media message">Social media message</option>
                <option value="investment opportunity">Investment or crypto opportunity</option>
                <option value="other message">Other</option>
              </select>
            </div>
            <label for="scamInput" class="checker-label">Paste the message, URL, or describe the call</label>
            <p class="checker-safety" role="note"><strong>Keep yourself safe:</strong> never paste passwords, PINs, full card numbers, or one-time security codes &mdash; a scam check never needs them.</p>
            <textarea
              id="scamInput"
              class="checker-textarea"
              placeholder="e.g. Your Royal Mail parcel is on hold. Pay 1.45 to release it: rm-parcel-uk.com/pay"
              rows="7"
              maxlength="3000"
            ></textarea>
            <div class="checker-footer-row">
              <span class="checker-char-count" id="charCount">0 / 3000</span>
              <button id="checkBtn" class="btn btn-primary checker-submit">Analyse message</button>
            </div>
            <p class="note" style="margin-top:.75rem">Your message is sent to Claude AI for analysis and is not stored by Beat the Scam.</p>
          </div>
        </div>

        <div class="checker-result-col" id="resultCol" hidden>
          <div class="card checker-result" id="checkerResult">
            <div id="resultLoading" class="checker-loading" hidden>
              <div class="checker-spinner"></div>
              <p>Analysing&hellip;</p>
            </div>
            <div id="resultContent" hidden></div>
          </div>
        </div>
      </div>

      <div class="wrap" style="margin-top:2rem">
        <div class="notice">
          <strong>This tool provides educational guidance only.</strong>
          It is not a definitive fraud verdict. If you have already sent money or shared personal details,
          contact your bank immediately and report it to <!--POLICE_ROUTE_PLAIN-->.
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap" style="max-width:780px">
        <h2>How the scam checker works</h2>
        <p>Paste the suspicious content above and the checker sends it to an AI model (Anthropic&#8217;s Claude) prompted to recognise the patterns behind common UK scams. In a few seconds it returns a plain-English verdict, the specific red flags it spotted, any reassuring signs, the practical steps to take next, and the official UK routes to report it. Nothing you paste is stored by Beat the Scam, and the reporting links in your result are restricted to an allow-list of official UK bodies &mdash; so a manipulated message can&#8217;t slip a fake &#8220;report here&#8221; link into the answer.</p>

        <h2>What you can check</h2>
        <ul>
          <li><strong>Text messages (SMS):</strong> &#8220;missed delivery&#8221; parcel texts, fake bank fraud-alert texts, DVLA or HMRC refund texts.</li>
          <li><strong>Emails:</strong> phishing that imitates your bank, a retailer, a delivery firm, or a government department.</li>
          <li><strong>Websites and links:</strong> lookalike shop, login, or &#8220;verification&#8221; pages built to capture your details.</li>
          <li><strong>Phone calls:</strong> describe what the caller said &mdash; bank or police impersonation, &#8220;your account is at risk&#8221;, or tech-support claims.</li>
          <li><strong>Job offers:</strong> work-from-home, mystery-shopping, or recruitment messages that ask for money or documents up front.</li>
          <li><strong>Investment and crypto:</strong> &#8220;guaranteed returns&#8221;, celebrity-endorsed trading platforms, or recovery offers after a previous loss.</li>
        </ul>

        <h2>How to read your result</h2>
        <p>The checker gives one of four verdicts, each with a confidence level:</p>
        <ul>
          <li><strong>Likely a scam</strong> &mdash; several strong fraud signals are present. Don&#8217;t click, reply, pay, or call back.</li>
          <li><strong>Possibly a scam</strong> &mdash; some warning signs; treat it with caution and verify independently.</li>
          <li><strong>Probably legitimate</strong> &mdash; nothing obvious stands out, but this is never a guarantee &mdash; still verify before acting on anything important.</li>
          <li><strong>Unclear</strong> &mdash; not enough to judge; check directly with the organisation via its official website or app.</li>
        </ul>
        <p>Because scam tactics change constantly, treat the result as a guide, not a final verdict. The single safest habit is to verify through a channel you open yourself &mdash; the number on the back of your card, or an address you type into your browser &mdash; rather than any link, number, or detail supplied in the message itself.</p>

        <h2>If you have already responded</h2>
        <p>If you have paid, shared bank or card details, or shared a one-time passcode, act straight away. Contact your bank on the number on the back of your card, report it to <!--POLICE_ROUTE-->, and forward scam texts to <strong><!--SMS_CODE--></strong> and suspicious emails to <strong><!--NCSC_EMAIL--></strong>. For step-by-step help by scam type, browse our <a href="/guides/">scam guides</a>.</p>

        <h2>Common questions</h2>
        <div class="faq">
          <details><summary>Is the scam checker free?</summary><p>Yes &mdash; it&#8217;s completely free and needs no account. It exists to help you make a quick, safer judgement before you click, pay, or share anything.</p></details>
          <details><summary>Do you store the message I paste?</summary><p>No. Your text is sent to the AI for analysis and is not stored by Beat the Scam. Please don&#8217;t paste passwords, PINs, full card numbers, or one-time codes &mdash; a scam check never needs them.</p></details>
          <details><summary>Can the checker be wrong?</summary><p>Yes. It&#8217;s an educational tool and can both flag genuine messages and miss real scams. Use it as one input alongside independent verification, not as the final word.</p></details>
          <details><summary>It says &#8220;probably legitimate&#8221; &mdash; am I safe to proceed?</summary><p>Not necessarily. A reassuring result is not a green light. If money, credentials, or personal data are involved, confirm through the organisation&#8217;s official website, app, or published phone number first.</p></details>
        </div>
      </div>
    </section>

    <script>
    (function() {
      var input      = document.getElementById("scamInput");
      var typeEl     = document.getElementById("scamType");
      var btn        = document.getElementById("checkBtn");
      var resultCol  = document.getElementById("resultCol");
      var resultContent = document.getElementById("resultContent");
      var loadingEl  = document.getElementById("resultLoading");
      var charCount  = document.getElementById("charCount");

      input.addEventListener("input", function() {
        charCount.textContent = input.value.length + " / 3000";
      });

      btn.addEventListener("click", function() {
        var message = input.value.trim();
        if (!message || message.length < 10) { input.focus(); return; }
        var startedAt = Date.now();
        if (typeof window.btsTrackEvent === "function") {
          window.btsTrackEvent("scam_check_submitted", {
            checker_type: typeEl.value
          });
        }
        btn.disabled = true;
        btn.textContent = "Analysing\u2026";
        resultCol.hidden = false;
        loadingEl.hidden = false;
        resultContent.hidden = true;

        fetch("/api/check-scam", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: message, type: typeEl.value })
        })
        .then(function(res) {
          if (!res.ok) throw new Error("status " + res.status);
          return res.json();
        })
        .then(function(data) {
          renderResult(data);
          if (typeof window.btsTrackEvent === "function") {
            window.btsTrackEvent("scam_check_success", {
              checker_type: typeEl.value,
              verdict: data.verdict || "unclear",
              confidence: data.confidence || "unknown",
              duration_ms: Date.now() - startedAt
            });
          }
        })
        .catch(function(err) {
          renderError();
          if (typeof window.btsTrackEvent === "function") {
            window.btsTrackEvent("scam_check_error", {
              checker_type: typeEl.value,
              error_reason: (err && err.message) || "unknown",
              duration_ms: Date.now() - startedAt
            });
          }
        })
        .finally(function() {
          btn.disabled = false;
          btn.textContent = "Analyse message";
          loadingEl.hidden = true;
        });
      });

      function verdictClass(v) {
        if (v === "likely_scam")         return "verdict-scam";
        if (v === "possibly_scam")       return "verdict-warn";
        if (v === "probably_legitimate") return "verdict-ok";
        return "verdict-unclear";
      }

      function verdictLabel(v) {
        if (v === "likely_scam")         return "&#9888; Likely a scam";
        if (v === "possibly_scam")       return "&#9888; Possibly a scam";
        if (v === "probably_legitimate") return "&#10003; Probably legitimate";
        return "&#63; Unclear &mdash; proceed with caution";
      }

      // Safe DOM builder — no innerHTML, eliminates XSS risk
      function el(tag, attrs, text) {
        var node = document.createElement(tag);
        if (attrs) Object.keys(attrs).forEach(function(k){ node.setAttribute(k, attrs[k]); });
        if (text !== undefined) node.textContent = text;
        return node;
      }

      function renderResult(data) {
        var frag = document.createDocumentFragment();

        var verdict = el("div", {"class": "checker-verdict " + verdictClass(data.verdict)});
        var strong = document.createElement("strong");
        strong.innerHTML = verdictLabel(data.verdict);
        verdict.appendChild(strong);
        if (data.confidence) {
          verdict.appendChild(el("span", {"class": "checker-confidence"}, " (" + data.confidence + " confidence)"));
        }
        frag.appendChild(verdict);

        if (data.summary) frag.appendChild(el("p", {"style": "margin:.75rem 0"}, data.summary));

        if (data.red_flags && data.red_flags.length) {
          frag.appendChild(el("h3", null, "Red flags identified"));
          var ul = el("ul");
          data.red_flags.forEach(function(f){ ul.appendChild(el("li", null, f)); });
          frag.appendChild(ul);
        }
        if (data.green_flags && data.green_flags.length) {
          frag.appendChild(el("h3", null, "Reassuring signs"));
          var ul2 = el("ul");
          data.green_flags.forEach(function(f){ ul2.appendChild(el("li", null, f)); });
          frag.appendChild(ul2);
        }
        if (data.recommended_actions && data.recommended_actions.length) {
          frag.appendChild(el("h3", null, "Recommended actions"));
          var ol = el("ol");
          data.recommended_actions.forEach(function(a){ ol.appendChild(el("li", null, a)); });
          frag.appendChild(ol);
        }
        if (data.reporting_links && data.reporting_links.length) {
          frag.appendChild(el("h3", null, "Reporting links"));
          var ul3 = el("ul");
          data.reporting_links.forEach(function(l) {
            var href = String(l.url || "");
            if (!href.startsWith("https://")) return;
            var a = el("a", {"href": href, "rel": "noopener noreferrer", "target": "_blank"}, l.name);
            var li = el("li");
            li.appendChild(a);
            ul3.appendChild(li);
          });
          frag.appendChild(ul3);
        }

        resultContent.textContent = "";
        resultContent.appendChild(frag);
        resultContent.hidden = false;
        resultCol.scrollIntoView({ behavior: "smooth", block: "start" });
      }

      function renderError() {
        var p = el("p", {"class": "notice"}, "Sorry, the checker could not be reached right now. Please try again, or ");
        // Rendered from the canon, like every other route on this page.
        var routes = document.createElement("span");
        routes.innerHTML = "<!--POLICE_ROUTE_JS-->";
        p.appendChild(document.createTextNode("report it to "));
        p.appendChild(routes);
        p.appendChild(document.createTextNode("."));
        resultContent.textContent = "";
        resultContent.appendChild(p);
        resultContent.hidden = false;
      }
    })();
    </script>
    '''

    # The block above is a plain (non-f) triple-quoted string because it embeds
    # JavaScript full of braces. The nation-scoped police route is substituted
    # here so the checker page uses the SAME canon component as the Disclaimer,
    # the Terms and the methodology page (operator review, 2026-07-29).
    content = content.replace("<!--POLICE_ROUTE-->", police_route_html(sources))
    content = content.replace("<!--POLICE_ROUTE_PLAIN-->",
                              police_route_html(sources, phone=False, url=False))
    content = content.replace("<!--SMS_CODE-->", _sms(sources))
    content = content.replace("<!--NCSC_EMAIL-->", _email(sources))
    # The error-state route is assembled in JavaScript, so it is injected as an
    # HTML string inside a JS double-quoted literal: escape the quotes.
    content = content.replace(
        "<!--POLICE_ROUTE_JS-->",
        police_route_html(sources, phone=False, url=False).replace('"', '\\"'),
    )
    assert "<!--POLICE_ROUTE" not in content

    schema = page_schema(
        site,
        'AI Scam Checker',
        'Paste a suspicious message and get an instant plain-English verdict powered by Claude AI.',
        site['domain'] + '/check/'
    )
    return make_base(
        content,
        title=f'AI Scam Checker | {site["site_name"]}',
        description='Paste a suspicious text, email, URL, or job offer and get an instant scam verdict powered by Claude AI. Free, no account needed.',
        canonical=site['domain'] + '/check/',
        schema=schema,
        site=site,
        ads_mode="none",
    )


def render_newsletter_confirmed_page(site):
    """Static success page reached only after the double-opt-in POST succeeds.

    app.js records the consented confirmation event from the marker below. The
    Resend audience remains the source of truth for the total subscriber count,
    because visitors who decline analytics are intentionally not measured in GA4.
    """
    content = '''
    <section class="hero" id="newsletter-confirmed" data-newsletter-confirmed="true">
      <div class="wrap" style="max-width:760px">
        <div class="breadcrumbs"><a href="/">Home</a> / Newsletter confirmed</div>
        <h1>You&#8217;re on the list</h1>
        <p class="lead">Your subscription is confirmed. Look out for plain-English scam alerts and practical checks in your inbox.</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="/guides/">Browse scam guides</a>
          <a class="btn btn-secondary" href="/check/">Check a suspicious message</a>
        </div>
      </div>
    </section>
    '''
    return make_base(
        content,
        title=f'Newsletter confirmed | {site["site_name"]}',
        description='Your Beat the Scam newsletter subscription is confirmed.',
        canonical=site['domain'] + '/newsletter-confirmed/',
        schema=page_schema(
            site,
            'Newsletter confirmed',
            'Your Beat the Scam newsletter subscription is confirmed.',
            site['domain'] + '/newsletter-confirmed/',
        ),
        site=site,
        robots='noindex,follow',
        ads_mode='none',
    )
def research_dataset_schema(site, report):
    slug = report["slug"]
    bing = report["bing_ai"]
    google = report["google_search"]
    return json_ld({
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": report["title"],
        "description": report["summary"],
        "url": f'{site["domain"]}/research/{slug}/',
        "datePublished": report["published"],
        "creator": {
            "@type": "Organization",
            "name": site["site_name"],
            "url": site["domain"],
        },
        "distribution": [
            {
                "@type": "DataDownload",
                "encodingFormat": "application/json",
                "contentUrl": f'{site["domain"]}/research/data/{slug}.json',
            },
            {
                "@type": "DataDownload",
                "encodingFormat": "text/csv",
                "contentUrl": f'{site["domain"]}/research/data/{slug}-bing-daily.csv',
            },
        ],
        "variableMeasured": [
            "Bing AI citations",
            "Bing AI cited pages",
            "Google Search clicks",
            "Google Search impressions",
            "Google Search click-through rate",
        ],
        "temporalCoverage": f'{min(bing["start_date"], google["start_date"])}/{max(bing["end_date"], google["end_date"])}',
        "spatialCoverage": "United Kingdom",
        "isAccessibleForFree": True,
    })


def _research_chart(daily):
    if len(daily) < 2:
        return ""
    width, height, pad = 760, 260, 32
    values = [row["citations"] for row in daily]
    peak = max(values) or 1
    points = []
    for index, value in enumerate(values):
        x = pad + index * (width - 2 * pad) / (len(values) - 1)
        y = height - pad - value * (height - 2 * pad) / peak
        points.append(f"{x:.1f},{y:.1f}")
    start = html.escape(daily[0]["date"])
    end = html.escape(daily[-1]["date"])
    return f'''
    <figure class="research-chart">
      <svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="citation-chart-title citation-chart-desc">
        <title id="citation-chart-title">Daily Bing AI citations</title>
        <desc id="citation-chart-desc">Daily citations from {start} to {end}; the highest daily count was {peak:,}.</desc>
        <line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" class="chart-axis"/>
        <line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" class="chart-axis"/>
        <polyline points="{' '.join(points)}" class="chart-line"/>
        <text x="{pad}" y="{height-8}" class="chart-label">{start}</text>
        <text x="{width-pad}" y="{height-8}" text-anchor="end" class="chart-label">{end}</text>
        <text x="{pad+6}" y="{pad+4}" class="chart-label">Peak {peak:,}</text>
      </svg>
      <figcaption>Daily Bing AI citations in the exported period. Platform counts can be revised; this is a dated snapshot.</figcaption>
    </figure>
    '''


def render_research_index(site, reports, stats_page=None):
    cards = []
    if stats_page:
        cards.append(f'''
        <article class="card research-card">
          <div class="eyebrow">Reference dataset · updated quarterly</div>
          <h2><a href="/research/{html.escape(stats_page['slug'])}/">{html.escape(stats_page['title'])}</a></h2>
          <p>{html.escape(stats_page['summary'])}</p>
          <p class="meta">Updated {html.escape(stats_page['updated'])} · Includes downloadable CSV and JSON</p>
        </article>
        ''')
    for report in reports:
        bing = report["bing_ai"]
        cards.append(f'''
        <article class="card research-card">
          <div class="eyebrow">Monthly visibility report</div>
          <h2><a href="/research/{html.escape(report['slug'])}/">{html.escape(report['title'])}</a></h2>
          <p>{html.escape(report['summary'])}</p>
          <div class="badge-row">
            <span class="badge">{bing['total_citations']:,} AI citations</span>
            <span class="badge">{bing['cited_page_count']:,} cited pages</span>
          </div>
          <p class="meta">Published {html.escape(report['published'])} · Includes downloadable JSON and CSV</p>
        </article>
        ''')
    description = "Original, downloadable datasets tracking how Beat the Scam guidance appears in Google Search and Bing-powered AI answers, with a transparent method."
    content = f'''
    <section class="hero research-hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / Research</div>
        <div class="kicker">Open methods · Downloadable data</div>
        <h1>Research and visibility datasets</h1>
        <p class="lead">We publish recurring snapshots of search discovery and AI citations so readers, journalists and researchers can inspect the numbers behind our visibility claims.</p>
        <div class="notice"><strong>Scope:</strong> these reports measure visibility for Beat the Scam. They are not estimates of UK scam incidence, financial loss or population-wide search demand.</div>
        <div class="hero-actions"><a class="btn btn-secondary" href="/research/methodology/">Read the research method</a></div>
      </div>
    </section>
    <section class="section"><div class="wrap research-list">{''.join(cards)}</div></section>
    '''
    schema = page_schema(site, "Research and visibility datasets", description, site["domain"] + "/research/")
    schema += itemlist_schema(
        [(report["title"], f'{site["domain"]}/research/{report["slug"]}/') for report in reports],
        "Beat the Scam research reports",
    )
    return make_base(content, title=f'Research & Data | {site["site_name"]}', description=description,
                     canonical=site["domain"] + "/research/", schema=schema, site=site, ads_mode="none")


def render_research_methodology(site):
    title = "Search and AI visibility research methodology"
    description = "How Beat the Scam collects, normalises, publishes and interprets Google Search Console and Bing AI Performance visibility data."
    content = f'''
    <section class="hero"><div class="wrap">
      <div class="breadcrumbs"><a href="/">Home</a> / <a href="/research/">Research</a> / Methodology</div>
      <h1>{title}</h1>
      <p class="lead">A repeatable method for measuring search discovery, AI citations, consolidation effects and click-through rate without overstating what the data can prove.</p>
    </div></section>
    <section class="section"><div class="wrap"><article class="article">
      <h2>What we measure</h2>
      <p><strong>Google Search Console:</strong> final web-search clicks, impressions, CTR and average position for the latest complete 28-day period, compared with the immediately preceding equal period. Page and query views are retained internally; the public dataset includes site totals and named focus pages.</p>
      <p><strong>Bing AI Performance:</strong> total citations, daily cited-page counts, cited URLs and the grounding-query sample supplied by Bing Webmaster Tools. The public report uses the dashboard&#8217;s 30-day exports; a three-month export is retained internally for longer comparisons.</p>

      <h2>Monthly collection process</h2>
      <ol>
        <li>Export the 30-day and three-month Overview, Pages and Grounding queries CSV files from Bing AI Performance.</li>
        <li>Run the measurement script, which retrieves final Search Console data, normalises the Bing exports and creates an immutable dated snapshot.</li>
        <li>Check totals, date coverage and focus-page mappings before publishing the normalized public JSON and CSV files.</li>
        <li>Compare equal 28-day periods. Use seven-day results only as an early directional check.</li>
        <li>For a redirected or consolidated guide, assess the old and new URLs together until the source URL disappears from platform reports.</li>
      </ol>

      <h2>Interpretation rules</h2>
      <ul>
        <li>A Bing citation is a source appearance, not a ranking, endorsement, visit or guarantee of prominent placement.</li>
        <li>Bing grounding queries are a sample, and Bing&#8217;s generated intent and topic labels can change.</li>
        <li>Search Console omits anonymized queries; filtering and aggregation can make dimension totals differ.</li>
        <li>Average position is contextual. We prioritize impressions, clicks and CTR, then use position to diagnose page-level changes.</li>
        <li>An editorial release is treated as an intervention. A before-and-after change can correlate with the release but does not prove causation.</li>
        <li>Visibility data for this site is not evidence of national scam prevalence or financial harm.</li>
      </ul>

      <h2>Privacy and reproducibility</h2>
      <p>No message submitted to the scam checker, personal information or subscriber data is collected for these reports. Each release names its source periods, publishes normalized files and preserves its raw source exports internally for audit.</p>

      <h2>Primary platform documentation</h2>
      <ul>
        <li><a href="https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview" rel="noopener noreferrer">Bing: AI Performance in Webmaster Tools</a></li>
        <li><a href="https://support.google.com/webmasters/answer/12919192?hl=en" rel="noopener noreferrer">Google: exporting Search Console performance data</a></li>
        <li><a href="https://support.google.com/webmasters/answer/17010961?hl=en" rel="noopener noreferrer">Google: common Search Console analysis tasks</a></li>
      </ul>
      <p class="note">Method version 1.0 · Published 18 July 2026. Material changes will be documented on this page.</p>
    </article></div></section>
    '''
    return make_base(content, title=f'{title} | {site["site_name"]}', description=description,
                     canonical=site["domain"] + "/research/methodology/",
                     schema=page_schema(site, title, description, site["domain"] + "/research/methodology/"),
                     site=site, ads_mode="none")


def render_research_report(site, report):
    slug = report["slug"]
    bing = report["bing_ai"]
    google = report["google_search"]
    previous = google.get("previous_period", {})
    previous_focus = google.get("focus_pages_previous", {})
    def change(current, old):
        return "n/a" if not old else f"{((current - old) / old * 100):+.1f}%"
    top_page_rows = "".join(
        f'<tr><td><a href="{html.escape(row["page"])}">{html.escape(row["page"].replace(site["domain"], ""))}</a></td><td>{row["citations"]:,}</td></tr>'
        for row in bing["top_pages"][:15]
    )
    query_rows = "".join(
        f'<tr><td>{html.escape(row["grounding_query"])}</td><td>{html.escape(row.get("intent", ""))}</td><td>{row["citations"]:,}</td><td>{html.escape(row.get("citation_share", ""))}</td></tr>'
        for row in bing["top_grounding_queries"][:15]
    )
    focus_rows = []
    for url, metrics in google["focus_pages"].items():
        old = previous_focus.get(url, {})
        focus_rows.append(
            f'<tr><td>{html.escape(url.replace(site["domain"], ""))}</td>'
            f'<td>{metrics.get("impressions", 0):g}</td><td>{old.get("impressions", 0):g}</td>'
            f'<td>{change(metrics.get("impressions", 0), old.get("impressions", 0))}</td>'
            f'<td>{metrics.get("clicks", 0):g}</td><td>{metrics.get("ctr", 0) * 100:.2f}%</td>'
            f'<td>{old.get("ctr", 0) * 100:.2f}%</td><td>{metrics.get("position", 0):.1f}</td></tr>'
        )
    focus_rows = "".join(focus_rows)
    consolidation_rows = "".join(
        f'<tr><td>{html.escape(item["from"].replace(site["domain"], ""))}<br>+ {html.escape(item["to"].replace(site["domain"], ""))}</td>'
        f'<td>{item["combined_current"]["impressions"]:g}</td><td>{item["combined_previous"]["impressions"]:g}</td>'
        f'<td>{item["combined_current"]["clicks"]:g}</td><td>{item["combined_previous"]["clicks"]:g}</td>'
        f'<td>{item["combined_current"]["ctr"] * 100:.2f}%</td><td>{item["combined_previous"]["ctr"] * 100:.2f}%</td></tr>'
        for item in google.get("consolidations", [])
    )
    method_items = "".join(f"<li>{html.escape(item)}</li>" for item in report["method"])
    limitation_items = "".join(f"<li>{html.escape(item)}</li>" for item in report["limitations"])
    content = f'''
    <section class="hero research-hero"><div class="wrap">
      <div class="breadcrumbs"><a href="/">Home</a> / <a href="/research/">Research</a> / {html.escape(report['title'])}</div>
      <div class="kicker">Monthly dataset · {html.escape(report['published'])}</div>
      <h1>{html.escape(report['title'])}</h1>
      <p class="lead">{html.escape(report['summary'])}</p>
      <div class="notice"><strong>Read this first:</strong> {html.escape(report['scope_note'])}</div>
    </div></section>

    <section class="section"><div class="wrap">
      <div class="stat-strip research-stat-strip">
        <div class="metric-card"><strong>{bing['total_citations']:,}</strong><span>Bing AI citations</span></div>
        <div class="metric-card"><strong>{bing['average_cited_pages']:.1f}</strong><span>average cited pages per returned day</span></div>
        <div class="metric-card"><strong>{google['impressions']:,}</strong><span>Google impressions</span></div>
        <div class="metric-card"><strong>{google['ctr'] * 100:.2f}%</strong><span>Google click-through rate</span></div>
      </div>
    </div></section>

    <section class="section"><div class="wrap"><article class="article research-article">
      <h2>What the snapshot shows</h2>
      <p>Between <strong>{html.escape(bing['start_date'])}</strong> and <strong>{html.escape(bing['end_date'])}</strong>, Bing recorded {bing['total_citations']:,} citations across {bing['cited_page_count']:,} Beat the Scam pages. Its export returned {bing['days_returned']} days and {bing['grounding_query_sample_count']:,} sampled grounding queries.</p>
      <p>Google&#8217;s separate final-data window runs from <strong>{html.escape(google['start_date'])}</strong> to <strong>{html.escape(google['end_date'])}</strong>: {google['impressions']:,} impressions, {google['clicks']:g} clicks, {google['ctr'] * 100:.2f}% CTR and an average position of {google['average_position']:.1f}. Source periods differ because the platforms expose complete data on different schedules.</p>
      <div class="evidence-table-wrap"><table class="evidence-table"><thead><tr><th scope="col">Google signal</th><th scope="col">Current 28 days</th><th scope="col">Previous 28 days</th><th scope="col">Change</th></tr></thead><tbody>
        <tr><th scope="row">Impressions</th><td>{google['impressions']:,}</td><td>{previous.get('impressions', 0):,}</td><td>{change(google['impressions'], previous.get('impressions', 0))}</td></tr>
        <tr><th scope="row">Clicks</th><td>{google['clicks']:g}</td><td>{previous.get('clicks', 0):g}</td><td>{change(google['clicks'], previous.get('clicks', 0))}</td></tr>
        <tr><th scope="row">CTR</th><td>{google['ctr'] * 100:.2f}%</td><td>{previous.get('ctr', 0) * 100:.2f}%</td><td>{(google['ctr'] - previous.get('ctr', 0)) * 100:+.2f} pp</td></tr>
        <tr><th scope="row">Average position</th><td>{google['average_position']:.1f}</td><td>{previous.get('average_position', 0):.1f}</td><td>{google['average_position'] - previous.get('average_position', 0):+.1f}</td></tr>
      </tbody></table></div>
      <p class="note">Both Google periods end before the 18 July editorial release. They are the baseline for future comparisons, not evidence of a post-release effect.</p>

      {_research_chart(bing['daily'])}

      <h2>Most-cited pages</h2>
      <div class="evidence-table-wrap"><table class="evidence-table"><thead><tr><th scope="col">Page</th><th scope="col">Citations</th></tr></thead><tbody>{top_page_rows}</tbody></table></div>

      <h2>Sampled grounding queries</h2>
      <p>Bing describes these as a sample of the queries used to ground AI answers. Citation share is the share Bing reports for the site on that sampled query; it is not conventional search rank.</p>
      <div class="evidence-table-wrap"><table class="evidence-table"><thead><tr><th scope="col">Grounding query</th><th scope="col">Intent</th><th scope="col">Citations</th><th scope="col">Citation share</th></tr></thead><tbody>{query_rows}</tbody></table></div>

      <h2>Google focus-page baseline</h2>
      <p>These are the pages named before the 18 July editorial release. They create a pre-change baseline for later seven- and 28-day comparisons.</p>
      <div class="evidence-table-wrap"><table class="evidence-table"><thead><tr><th scope="col">Page</th><th scope="col">Impr. current</th><th scope="col">Impr. previous</th><th scope="col">Change</th><th scope="col">Clicks current</th><th scope="col">CTR current</th><th scope="col">CTR previous</th><th scope="col">Position current</th></tr></thead><tbody>{focus_rows}</tbody></table></div>

      <h2>Consolidation baseline</h2>
      <p>Redirect source and target URLs are combined so migration between them cannot be mistaken for a visibility gain or loss.</p>
      <div class="evidence-table-wrap"><table class="evidence-table"><thead><tr><th scope="col">Source + target cluster</th><th scope="col">Impr. current</th><th scope="col">Impr. previous</th><th scope="col">Clicks current</th><th scope="col">Clicks previous</th><th scope="col">CTR current</th><th scope="col">CTR previous</th></tr></thead><tbody>{consolidation_rows}</tbody></table></div>

      <h2>Download the data</h2>
      <div class="download-grid">
        <a class="card" href="/research/data/{slug}.json" download><strong>Normalized report</strong><span>JSON · headline, daily, page, query and focus-page data</span></a>
        <a class="card" href="/research/data/{slug}-bing-daily.csv" download><strong>Bing daily trend</strong><span>CSV · citations and cited pages by day</span></a>
        <a class="card" href="/research/data/{slug}-bing-pages.csv" download><strong>Bing cited pages</strong><span>CSV · top 25 published pages</span></a>
        <a class="card" href="/research/data/{slug}-bing-queries.csv" download><strong>Bing query sample</strong><span>CSV · top 25 published grounding queries</span></a>
        <a class="card" href="/research/data/{slug}-gsc-focus-pages.csv" download><strong>Google comparisons</strong><span>CSV · focus pages and consolidation clusters across equal periods</span></a>
      </div>

      <h2>Method</h2><ol>{method_items}</ol>
      <h2>Limitations</h2><ul>{limitation_items}</ul>
      <p><a href="/research/methodology/">Read the full recurring measurement method</a>.</p>
    </article></div></section>
    '''
    schema = research_dataset_schema(site, report)
    schema += breadcrumb_schema([
        ("Home", site["domain"] + "/"),
        ("Research", site["domain"] + "/research/"),
        (report["title"], f'{site["domain"]}/research/{slug}/'),
    ])
    return make_base(content, title=seo_title(report["title"], site["site_name"], brand=False),
                     description=report["summary"], canonical=f'{site["domain"]}/research/{slug}/',
                     schema=schema, site=site, og_type="article", ads_mode="none")


def load_stats_page(root: Path):
    """Load the curated UK scam statistics dataset (optional page)."""
    path = root / "content" / "uk-scam-statistics.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"slug", "title", "updated", "summary", "sections", "gaps"}
    missing = required - set(data)
    if missing:
        raise SystemExit(f"ERROR: uk-scam-statistics.json missing {sorted(missing)}")
    return data


def stats_dataset_schema(site, data):
    slug = data["slug"]
    url = f'{site["domain"]}/research/{slug}/'
    return json_ld({
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": data["title"],
        "description": data["summary"],
        "url": url,
        "dateModified": data["updated"],
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": {"@type": "Organization", "name": site["site_name"], "url": site["domain"]},
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "text/csv",
             "contentUrl": f'{site["domain"]}/research/data/{slug}.csv'},
            {"@type": "DataDownload", "encodingFormat": "application/json",
             "contentUrl": f'{site["domain"]}/research/data/{slug}.json'},
        ],
    })


def render_stats_page(site, data):
    slug = data["slug"]
    url = f'{site["domain"]}/research/{slug}/'
    section_parts = []
    for sec in data["sections"]:
        rows = []
        for st in sec["stats"]:
            meta_bits = [st["period"], st["publisher"], f'published {st["published"]}']
            if st.get("geography"):
                meta_bits.insert(1, st["geography"])
            notes = f'<p class="note">{html.escape(st["notes"])}</p>' if st.get("notes") else ""
            rows.append(f'''
            <article class="card stat-record">
              <h3>{html.escape(st["metric"])}</h3>
              <p class="stat-value">{html.escape(st["value"])}</p>
              <p class="meta">{html.escape(" · ".join(meta_bits))} ·
                <a href="{html.escape(st["source_url"])}" rel="noopener noreferrer" target="_blank">Source</a></p>
              {notes}
            </article>''')
        intro = f'<p>{html.escape(sec["intro"])}</p>' if sec.get("intro") else ""
        sid = slugify(sec["heading"])
        section_parts.append(f'<h2 id="{sid}">{html.escape(sec["heading"])}</h2>{intro}{"".join(rows)}')

    gaps_html = "".join(f'<li>{html.escape(g)}</li>' for g in data["gaps"])
    content = f'''
    <section class="hero research-hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/research/">Research</a> / UK Scam Statistics</div>
        <div class="kicker">Original data · Updated {html.escape(data["updated"])}</div>
        <h1>{html.escape(data["title"])}</h1>
        <p class="lead">{html.escape(data["summary"])}</p>
        <div class="notice"><strong>Reading the numbers:</strong> {html.escape(data["scope_note"])}</div>
      </div>
    </section>
    <section class="section"><div class="wrap">
      {"".join(section_parts)}
      <h2 id="data-gaps">Known data gaps</h2>
      <p>Honest limits of the current official data — recorded so a missing figure is not mistaken for a missing problem.</p>
      <ul>{gaps_html}</ul>
      <h2 id="downloads">Download the dataset</h2>
      <div class="cards download-grid">
        <a class="card" href="/research/data/{slug}.csv" download><strong>Full dataset</strong><span>CSV · every figure with period, publisher, publication date and source URL</span></a>
        <a class="card" href="/research/data/{slug}.json" download><strong>Structured data</strong><span>JSON · the same records grouped by section, plus gap notes</span></a>
      </div>
      <h2 id="method">Method and update cadence</h2>
      <p>{html.escape(data["methodology_note"])}</p>
      <p>{html.escape(data["cadence_note"])} Next scheduled refresh: {html.escape(data.get("next_update", "quarterly"))}.</p>
      <p class="meta">Cite as: {html.escape(site["site_name"])}, &#8220;{html.escape(data["title"])}&#8221;, {html.escape(data["updated"])}, {html.escape(url)}. Licensed CC BY 4.0 &#8212; reuse with attribution.</p>
    </div></section>
    '''
    breadcrumbs = [
        ("Home", site["domain"] + "/"),
        ("Research", site["domain"] + "/research/"),
        (data["title"], url),
    ]
    schema = (page_schema(site, data["title"], data["summary"], url)
              + stats_dataset_schema(site, data)
              + breadcrumb_schema(breadcrumbs))
    return make_base(content, title=seo_title(data["title"], site["site_name"], brand=False),
                     description=data["summary"], canonical=url,
                     schema=schema, site=site, og_type="article", ads_mode="none")


def write_stats_data(data):
    slug = data["slug"]
    out = DIST / "research" / "data"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for sec in data["sections"]:
        for st in sec["stats"]:
            rows.append({
                "section": sec["heading"], "metric": st["metric"], "value": st["value"],
                "period": st["period"], "geography": st.get("geography", ""),
                "publisher": st["publisher"],
                "published": st["published"], "source_url": st["source_url"],
                "notes": st.get("notes", ""),
            })
    write(out / f"{slug}.csv", _csv_text(
        ["section", "metric", "value", "period", "geography", "publisher", "published", "source_url", "notes"], rows))
    write(out / f"{slug}.json", json.dumps(data, indent=2, ensure_ascii=False))


def _csv_text(fieldnames, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def write_research_data(report):
    slug = report["slug"]
    target = DIST / "research" / "data"
    bing = report["bing_ai"]
    google = report["google_search"]
    write(target / f"{slug}.json", json.dumps(report, ensure_ascii=False, indent=2))
    write(target / f"{slug}-bing-daily.csv", _csv_text(["date", "citations", "cited_pages"], bing["daily"]))
    write(target / f"{slug}-bing-pages.csv", _csv_text(["page", "citations"], bing["top_pages"]))
    write(target / f"{slug}-bing-queries.csv", _csv_text(
        ["grounding_query", "intent", "topic", "citations", "citation_share"],
        bing["top_grounding_queries"],
    ))
    previous_focus = google.get("focus_pages_previous", {})
    focus_rows = []
    for url, metrics in google["focus_pages"].items():
        old = previous_focus.get(url, {})
        focus_rows.append({
            "row_type": "focus_page", "page_or_cluster": url,
            "current_clicks": metrics.get("clicks", 0),
            "previous_clicks": old.get("clicks", 0),
            "current_impressions": metrics.get("impressions", 0),
            "previous_impressions": old.get("impressions", 0),
            "current_ctr": metrics.get("ctr", 0),
            "previous_ctr": old.get("ctr", 0),
            "current_position": metrics.get("position", 0),
            "previous_position": old.get("position", 0),
        })
    for item in google.get("consolidations", []):
        current = item["combined_current"]
        old = item["combined_previous"]
        focus_rows.append({
            "row_type": "consolidation", "page_or_cluster": f'{item["from"]} + {item["to"]}',
            "current_clicks": current["clicks"], "previous_clicks": old["clicks"],
            "current_impressions": current["impressions"], "previous_impressions": old["impressions"],
            "current_ctr": current["ctr"], "previous_ctr": old["ctr"],
            "current_position": current["position"], "previous_position": old["position"],
        })
    write(target / f"{slug}-gsc-focus-pages.csv", _csv_text(
        ["row_type", "page_or_cluster", "current_clicks", "previous_clicks",
         "current_impressions", "previous_impressions", "current_ctr", "previous_ctr",
         "current_position", "previous_position"], focus_rows,
    ))


def render_simple_page(site, title, description, body, slug):
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / {html.escape(title)}</div>
        <h1>{html.escape(title)}</h1>
        <p class="lead">{html.escape(description)}</p>
      </div>
    </section>
    <section class="section"><div class="wrap"><article class="article">{body}</article></div></section>
    '''
    # Legal / trust pages (about, privacy, cookies, terms, contact, disclaimer)
    # carry no ads — they are not content surfaces and AdSense guidance is to keep
    # ads off legal/utility pages.
    return make_base(content, title=f'{title} | {site["site_name"]}', description=description, canonical=site['domain'] + f'/{slug}/', schema=page_schema(site, title, description, site['domain'] + f'/{slug}/'), site=site, ads_mode="none")


def render_author_page(site):
    """Render /author/ — the canonical author page for Alex Bacsa.

    Mirrors the structure of cloudfintech.ai/author and tuningdigital.com/about
    so cross-publication identity reads consistently to both human readers and
    search engines. The Person.sameAs JSON-LD block is the machine-readable
    equivalent of the visible "Also publishes on" section below.
    """
    ap = site.get("author_profile") or {}
    if not ap:
        return None
    name      = ap.get("name", site.get("author", ""))
    role      = ap.get("role", "Founder & Editor")
    image     = ap.get("image", "")
    linkedin  = ap.get("linkedin", "")
    email     = ap.get("email", site.get("contact_email", ""))
    based_in  = ap.get("based_in", "")
    bio       = ap.get("bio", "")
    expertise = ap.get("expertise") or []
    same_as   = ap.get("sameAs") or []
    pubs      = ap.get("publications") or []

    expertise_html = ""
    if expertise:
        chips = " ".join(f'<span class="badge">{html.escape(e)}</span>' for e in expertise)
        expertise_html = f'<div class="badges" style="display:flex;flex-wrap:wrap;gap:.4rem;margin:.6rem 0 1.2rem">{chips}</div>'

    pubs_html = ""
    if pubs:
        cards = "".join(
            f'''<article class="trust-card">
                <h3><a href="{html.escape(p["url"])}" rel="noopener noreferrer" target="_blank">{html.escape(p["name"])}</a></h3>
                <p class="note" style="margin:.25rem 0 .5rem;color:#666"><strong>{html.escape(p.get("role",""))}</strong></p>
                <p style="margin:0">{html.escape(p.get("topic",""))}</p>
                <p style="margin:.75rem 0 0;font-size:.9rem"><a href="{html.escape(p.get("author_url", p["url"]))}" rel="noopener noreferrer" target="_blank">Author profile &rarr;</a></p>
            </article>''' for p in pubs
        )
        pubs_html = f'''
        <h2>Also publishes on</h2>
        <p>Independent UK-based publications I founded or edit. Same author identity, separate editorial focus per site.</p>
        <div class="grid-3" style="margin-top:1rem">{cards}</div>
        '''

    bio_paragraphs = "".join(f"<p>{html.escape(para.strip())}</p>" for para in bio.split("\n\n") if para.strip())

    social_links = []
    if linkedin:
        social_links.append(f'<a href="{html.escape(linkedin)}" rel="noopener noreferrer" target="_blank">LinkedIn</a>')
    if email:
        social_links.append(f'<a href="mailto:{html.escape(email)}">{html.escape(email)}</a>')
    social_html = " &middot; ".join(social_links)

    # JSON-LD Person block. Person.sameAs is the cross-publication signal Google
    # reads to confirm identity across CloudFintech, TuningDigital, SalesTap and
    # the LinkedIn profile.
    person = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": name,
        "url": site["domain"] + ap.get("url", "/author/"),
        "jobTitle": role,
        "worksFor": {"@type": "Organization", "name": site["site_name"], "url": site["domain"]},
        "description": bio,
    }
    if image:
        person["image"] = abs_url(site, image)
    if email:
        person["email"] = email
    if same_as:
        person["sameAs"] = same_as
    if based_in:
        person["address"] = {"@type": "PostalAddress", "addressCountry": "GB"}
    schema = json_ld(person) + breadcrumb_schema([
        ("Home",   site["domain"] + "/"),
        ("Author", site["domain"] + "/author/"),
    ])

    # object-fit:cover means any future drop-in image (square or not)
    # crops to fill the circle instead of stretching. loading="lazy"
    # because the headshot is below-the-fold on the author page.
    image_html = (
        f'<img src="{html.escape(image)}" alt="{html.escape(name)}" width="160" height="160" '
        f'loading="lazy" decoding="async" '
        f'style="border-radius:50%;border:1px solid var(--line);background:#fafafa;'
        f'object-fit:cover;display:block">'
    ) if image else ""

    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / Author</div>
        <h1>{html.escape(name)}</h1>
        <p class="lead">{html.escape(role)} &middot; {html.escape(site["site_name"])}{(" &middot; Based in " + html.escape(based_in)) if based_in else ""}</p>
      </div>
    </section>
    <section class="section">
      <div class="wrap" style="display:flex;gap:2rem;align-items:flex-start;flex-wrap:wrap">
        <div style="flex:0 0 160px">{image_html}</div>
        <article class="article" style="flex:1;min-width:280px">
          {bio_paragraphs}
          {expertise_html}
          {pubs_html}
          <h2>Connect</h2>
          <p>{social_html}</p>
          <p class="note" style="margin-top:1.5rem;color:#666;font-size:.9rem">For editorial enquiries about {html.escape(site["site_name"])} specifically, including corrections and partnership proposals, see the <a href="/contact/">contact page</a>.</p>
        </article>
      </div>
    </section>
    '''
    return make_base(
        content,
        title=f'{name} — {role}, {site["site_name"]}',
        description=f'{name} is the {role.lower()} of {site["site_name"]}. Also publishes on CloudFintech, Tuning Digital, and SalesTap. UK-based.',
        canonical=site["domain"] + "/author/",
        schema=schema,
        site=site,
        ads_mode="none",
    )


def build_legal_bodies(site, sources):
    about = f'''
    <p><strong>{html.escape(site["site_name"])}</strong> is a consumer-protection content site focused on helping UK residents recognise scam patterns before they send money, share credentials, or install malicious software.</p>

    <div class="author-card" style="margin:1.5rem 0;padding:1.2rem;border:1px solid var(--line);border-radius:14px;background:#fafafa">
      <p style="margin:0 0 .35rem 0"><strong>Who runs this site</strong></p>
      <p style="margin:0 0 .5rem 0;font-size:.95rem;color:#555">{html.escape(site["site_name"])} is founded and edited by <a href="/author/"><strong>{html.escape(site["author"])}</strong></a>, an independent UK-based publisher who also runs <a href="https://cloudfintech.ai" rel="noopener noreferrer" target="_blank">CloudFintech</a> (fintech &amp; banking technology), <a href="https://tuningdigital.com" rel="noopener noreferrer" target="_blank">Tuning Digital</a> (AI &amp; SaaS productivity tools), and <a href="https://salestap.com" rel="noopener noreferrer" target="_blank">SalesTap</a> (B2B sales). He uses AI tooling to surface scam patterns and translate official UK guidance into plain-English checks.</p>
      <p style="margin:0;font-size:.95rem;color:#555">He is not a journalist, lawyer, regulator, banker, or accredited consumer-affairs professional. This is an educational publication that prefers primary official sources for reporting routes, legal and regulatory claims, while clearly labelling relevant secondary sources.</p>
    </div>

    <p>The editorial model is simple: fast checks, plain-English explanations, and practical actions. The site is not a law firm, bank, or regulator. It is a free educational publication designed to reduce avoidable losses.</p>

    <div class="tablelike">
      <div class="table-row"><strong>Editorial focus</strong><span>Scam alerts, payment risk, impersonation patterns, delivery fraud, marketplace abuse, crypto scams, and recovery scams.</span></div>
      <div class="table-row"><strong>Audience</strong><span>UK residents who have received a suspicious message, are considering an unfamiliar purchase, or want to understand current fraud tactics.</span></div>
      <div class="table-row"><strong>How guides are written</strong><span>Each guide targets a specific scam type and explains what to verify, what to avoid, and what to do if you have already interacted.</span></div>
      <div class="table-row"><strong>AI scam checker</strong><span>A free tool that analyses suspicious messages and gives a plain-English verdict with recommended actions.</span></div>
      <div class="table-row"><strong>Commercial model</strong><span>Advertising-supported using Google AdSense, with scope for consumer-safety partnerships.</span></div>
    </div>

    <h2>How guides are fact-checked</h2>
    <p>Guides use AI-assisted drafting and a deterministic accuracy gate, followed by editorial review. The gate catches defined error classes; it is not a substitute for checking each material claim against a current source. Existing guides are re-audited in scheduled corpus sweeps, and pages that need substantive work are removed from discovery and advertising until reviewed. See the full <a href="/methodology/">editorial methodology</a> and public <a href="/corrections/">corrections log</a>.</p>

    <h2>About the AI scam checker</h2>
    <p>The free scam checker on this site sends the suspicious message text you paste to Anthropic&#8217;s Claude API for analysis. The text is processed in real time to produce a verdict, list of red flags, and recommended actions &mdash; then discarded. Beat the Scam does not store the suspicious text you submit, and does not link it to your identity. To keep the free tool available and block abuse, the checker keeps a rate-limit counter keyed to a hashed form of your IP address &mdash; used only to enforce per-minute and daily usage limits, and never linked to your submission. As the processor, Anthropic may retain the text you submit and the model&#8217;s response for up to 30 days under its standard API data policy (and longer only where required for legal or safety reasons); it does not use API inputs or outputs to train its models.</p>
    <p>For your own safety, do not paste full passwords, full bank account numbers, or other sensitive credentials into the checker. The tool is designed to analyse the suspicious content itself (the message, link, or scam pattern), not your private credentials.</p>
    <p>The checker&#8217;s output is educational. It is not a definitive fraud determination. If you are unsure about a real-world payment or account access decision, contact your bank&#8217;s fraud team using the number on the back of your card.</p>

    <h2>Contact</h2>
    <p>Editorial contact and correction requests: <a href="mailto:{site["editorial_email"]}">{site["editorial_email"]}</a></p>

    <p class="note" style="margin-top:2rem;color:#666;font-size:.9rem">Last reviewed: 18 July 2026. The site is reviewed periodically and updated as scam patterns and reporting routes change.</p>
    '''

    methodology = f'''
    <p>This page explains, in detail, how {html.escape(site["site_name"])} researches, drafts, checks, and corrects its guides &mdash; so a reader, a journalist, an ad-network reviewer, or an AI system deciding whether to cite this site can see the actual process rather than take &#8220;fact-checked&#8221; on faith.</p>

    <h2>How content is researched and produced</h2>
    <p>Each guide on this site is drafted using AI assistance against a strict editorial template that forbids inventing statistics, quotes, or specific unverifiable claims, and that standardises the official UK reporting routes, scoped by nation &#8212; {police_route_html(sources, phone=False, url=False)}; the NCSC; and {consumer_route_html(sources)}.</p>
    <p>The drafting step uses Anthropic&#8217;s Claude API. The model is given a structured prompt covering the scam type, target audience, and required sections (what the scam looks like, warning signs, step-by-step pattern, verification, recovery actions, reporting routes). It is explicitly instructed not to invent statistics, predict outcomes, generate fake quotes, or assert specific claims about named companies or people.</p>

    <h2>The accuracy gate</h2>
    <p>Before publication, drafts pass an automated gate with narrow, testable checks: non-canon organisation phone numbers, known unsafe entities, defined reader-safety absolutes, reporting emails, selected UK consumer-protection errors, legislation flags, and reporting routes validated against a maintained canon. The publishing pipeline can also run a low-temperature AI critic to flag possible fabrication. These checks reduce repeat errors; they do not establish that every sentence is true, and a clean result is never presented as proof of accuracy.</p>

    <h2>Editorial review before publication</h2>
    <p>The gate is not the last step. New and updated guides are opened for editorial review before publication. An update date means the named editor changed and reviewed the page on that date; it does not imply review by an independent lawyer, regulator or financial professional. Where a distinct qualified reviewer is used, that person and role will be named explicitly.</p>

    <h2>Ongoing accuracy checks after publication</h2>
    <p>Facts drift after publication &mdash; a reporting route changes, a scheme is renamed, or a threshold is updated. High-stakes claims flagged during drafting are recorded for review, and scheduled corpus sweeps re-run deterministic checks and identify stale or weakly sourced pages. A sweep is triage, not a claim that every sentence has been independently verified. Pages needing substantive work can be made ad-free and removed from indexes while the review is completed.</p>

    <h2>Sources we verify against</h2>
    <p>Verification draws on UK-specific public sources, including:</p>
    <ul>
      <li><a href="{_r(sources, 'action-fraud')['info_url']}" rel="noopener noreferrer" target="_blank">{_b(sources, 'action-fraud')}</a> (formerly Action Fraud) &mdash; the police fraud reporting service for {_n(sources, 'action-fraud')}</li>
      <li><a href="{_r(sources, 'police-scotland')['report_url']}" rel="noopener noreferrer" target="_blank">{_b(sources, 'police-scotland')} on {_r(sources, 'police-scotland')['phone']}</a> &mdash; the police reporting route for {_n(sources, 'police-scotland')}</li>
      <li><a href="{_r(sources, 'ncsc-sers')['info_url']}" rel="noopener noreferrer" target="_blank">National Cyber Security Centre (NCSC)</a> &mdash; for phishing reporting routes and current threat patterns</li>
      <li><a href="{_consumer_advice_url(sources)}" rel="noopener noreferrer" target="_blank">GOV.UK consumer advice</a> &mdash; the consumer service for each UK nation: Citizens Advice in England and Wales, Advice Direct Scotland in Scotland, Consumerline in Northern Ireland</li>
      <li><a href="https://www.fca.org.uk/consumers/fca-firm-checker" rel="noopener noreferrer" target="_blank">FCA Firm Checker</a> &mdash; for investment and financial services scams</li>
      <li><a href="https://takefive-stopfraud.org.uk/" rel="noopener noreferrer" target="_blank">Take Five</a> &mdash; UK banking sector consumer fraud campaign</li>
      <li>Government UK pages for HMRC, DVLA, TV Licensing, and other public bodies commonly impersonated</li>
    </ul>

    <h2>Editorial standards</h2>
    <p>Content is written to be understandable under pressure. That means short sections, clear headings, and advice that directs readers towards independent verification through official channels &mdash; never through links, numbers, or payment details supplied by a suspicious message.</p>
    <p>Where the site recommends an official reporting route &mdash; the police reporting route for the reader's nation, the NCSC, or the consumer service where they live &mdash; it uses the official published channel and states which nations it covers. For organisation-specific contact details, always confirm the number or web address against the official website, or the details on your card, bill, or statement, rather than relying solely on any number reproduced in a guide.</p>

    <h2>Corrections</h2>
    <p>If a guide contains an error, email <a href="mailto:{site["editorial_email"]}">{site["editorial_email"]}</a> with the page URL, disputed wording and supporting source. Material factual changes are recorded in the public <a href="/corrections/">corrections log</a>; minor spelling and formatting edits are not normally logged.</p>

    <p class="note" style="margin-top:2rem;color:#666;font-size:.9rem">Last materially reviewed: 18 July 2026.</p>
    '''

    corrections = f'''
    <p class="note" style="color:#666;font-size:.95rem"><strong>Last updated:</strong> 23 July 2026</p>
    <p>This log records material factual corrections to published Beat the Scam guides. It does not list spelling, formatting, accessibility, or purely stylistic changes.</p>

    <h2>How to request a correction</h2>
    <p>Email <a href="mailto:{site["editorial_email"]}">{site["editorial_email"]}</a> with the page URL, the wording you believe is wrong, and a primary or authoritative source where possible. We assess the claim, update the guide when warranted, and record a material change below.</p>

    <h2>23 July 2026</h2>
    <p>Following a full corpus fact re-check against current primary sources:</p>
    <ul>
      <li><strong>DPD text guide:</strong> the reporting section no longer directs readers to a DPD fraud-reporting route that DPD UK's phishing guidance does not offer; reporting now goes via {_sms(sources)}, the NCSC, and the police reporting route for the reader's nation ({police_route_html(sources, phone=False, url=False)}), and the guide's sources now cite DPD UK rather than DPD Germany.</li>
      <li><strong>TV Licence email guide:</strong> sender-address guidance updated &mdash; TV Licensing warns that scammers can spoof its genuine addresses, and its current Themis Recoveries trial legitimately emails from mailing@themisglobal.co.uk about expired licences; a matching sender address is no longer presented as proof an email is genuine.</li>
      <li><strong>Microsoft account email guide:</strong> restored Microsoft's published phishing-forwarding mailbox for non-Outlook clients (phish@office365.microsoft.com, sent as an attachment so headers are preserved), which the guide previously said no longer existed; the Microsoft Defender portal's Submissions page is now described as an administrator route.</li>
      <li><strong>TalkTalk call guide:</strong> call-back guidance now uses TalkTalk's current published customer-service number (0345 172 0088, free from TalkTalk home phones) rather than the legacy 150 short code, which TalkTalk's current contact page no longer lists.</li>
      <li><strong>O2 text guide:</strong> replaced a defunct NCSC reporting URL and narrowed blanket &ldquo;a genuine O2 text will never&hellip;&rdquo; claims to O2's published commitment (no requests for codes, passwords or security information).</li>
      <li><strong>Shpock guide:</strong> Buyer Protection is now described as optional paid cover that the seller must enable and the buyer must purchase with the in-app payment, with claim deadlines of seven days from proof of postage (24 hours from receipt for Parcel2Go deliveries); reporting is now routed via the item page or Shpock's trust team.</li>
      <li><strong>Rightmove rental guide:</strong> deposit-protection wording updated for the end of assured shorthold tenancies in England and occupation contracts in Wales.</li>
      <li><strong>Google Voice code guide:</strong> clarified that Google Voice registration targets US numbers; for UK numbers the read-back code may relate to a different or undetermined Google security flow (or another service's one-time code), and remediation steps were reworked accordingly.</li>
      <li><strong>Bitcoin ATM guide:</strong> replaced check-the-register framing with the FCA's actual position that no registered firm is approved to operate crypto ATMs and any machine in the UK is operating illegally.</li>
      <li><strong>IVA guide:</strong> verification route corrected &mdash; IVAs are run by licensed insolvency practitioners outside FCA authorisation, so the guide now points to the Insolvency Service's register of insolvency practitioners.</li>
      <li><strong>Online pharmacy guide:</strong> scoped the MHRA online medicine seller register to Northern Ireland-based sellers; Great Britain checks rely on the GPhC register.</li>
      <li><strong>Invoice redirection checklist:</strong> added the mandatory APP reimbursement scheme's eligibility scope &mdash; individuals, qualifying micro-enterprises and qualifying charities; larger businesses fall outside the mandatory scheme but retain recall and complaint routes.</li>
      <li><strong>Santander call guide:</strong> removed an unsourced description of Santander's outbound-call identity checks in favour of hang-up-and-call-back guidance.</li>
      <li><strong>Passport guide:</strong> stopped describing third-party application websites as &ldquo;check and send&rdquo; services, to avoid confusion with the Post Office's official Check and Send service.</li>
      <li><strong>Jet2 holiday guide:</strong> Manage My Booking instructions corrected &mdash; Jet2holidays package logins use the lead passenger's date of birth; the departure date applies to jet2.com flight-only bookings.</li>
      <li><strong>Smart meter call guide:</strong> removed the overbroad claim that genuine engineers always have a confirmed appointment; installations are booked in advance, but suppliers can have other legitimate reasons to visit &mdash; verify by calling the supplier on an independently found number.</li>
      <li><strong>Etsy guide:</strong> Section 75 wording corrected to the statutory cash-price test (over &pound;100 and no more than &pound;30,000), which can apply even where only part of the payment was made by credit card.</li>
      <li><strong>Cryptocurrency payment guide:</strong> clarified that crypto investments are generally outside FSCS protection even when a firm is FCA-registered.</li>
      <li><strong>Court summons email guide:</strong> a matching @justice.gov.uk sender address is no longer presented as proof an email is genuine &mdash; HMCTS warns its addresses can be spoofed; verification now routes through GOV.UK's court finder.</li>
      <li><strong>Pension liberation guide:</strong> Pension Wise guidance is now signposted through MoneyHelper, its current delivery route.</li>
    </ul>

    <h2>18 July 2026</h2>
    <ul>
      <li><strong>DPD scam text guide:</strong> removed the blanket claim that DPD never requests payment by text. The guide now distinguishes fraudulent redelivery fees from genuine import duties or taxes and requires independent parcel verification.</li>
      <li><strong>Website-checking guide:</strong> removed universal company-number, Companies House, product-photography, and one-working-day response tests. Added sole-trader, new-company, statutory-rights, PayPal-deadline, APP-timetable, and Section 75 qualifications.</li>
      <li><strong>Amazon phone-call guide:</strong> replaced the unsupported claim that Amazon never cold-calls with the narrower, sourced rules on OTPs, confidential information, remote access and independent account verification.</li>
      <li><strong>Concert-ticket and holiday-compensation guides:</strong> corrected Section 75 wording from an inclusive £100 threshold or generic card payment to a qualifying credit purchase with a cash price over £100 and no more than £30,000, subject to the required relationship and other conditions.</li>
      <li><strong>Methodology and structured data:</strong> clarified the limits of automated checks and stopped inferring an independent <code>reviewedBy</code> reviewer from an update date.</li>
    </ul>

    <h2>Editorial status</h2>
    <p>Pages found to be too thin or insufficiently distinctive are made ad-free and removed from search/discovery inventories while they are rewritten or consolidated. This is a publishing control, not a claim that unlisted pages are unsafe.</p>
    '''

    recovery = f'''
    <p class="note" style="color:#666;font-size:.95rem"><strong>Information checked:</strong> 18 July 2026</p>
    <p>If you have paid a scammer, entered banking details, shared a password, installed software, or lost control of an account, start with the row that matches what happened. Do not wait for a police report before contacting a bank or securing an account.</p>

    <h2>What to do first</h2>
    <div class="tablelike">
      <div class="table-row"><strong>You only received the message</strong><span>Do not reply, click, or call a number in it. Forward a suspicious SMS to {_sms(sources)} free of charge. For WhatsApp, iMessage, RCS and other app messages, also use the app or phone's built-in block and report controls.</span></div>
      <div class="table-row"><strong>You opened a link</strong><span>If you did not enter information, download a file or install software, the NCSC says further action is unlikely to be needed, but watch for unusual account activity. If anything downloaded or installed, disconnect the device from the internet and run a full security scan.</span></div>
      <div class="table-row"><strong>You shared a password</strong><span>Use a clean device to change it immediately. Change every account where the password was reused, starting with the email account used for password resets. Sign out other sessions and turn on strong multi-factor authentication.</span></div>
      <div class="table-row"><strong>You shared card or bank details</strong><span>Contact the bank or card issuer immediately through its official app or the number printed on the card. Ask it to secure the account or card and identify any payment or account change you did not authorise.</span></div>
      <div class="table-row"><strong>You approved or sent a bank transfer</strong><span>Tell the sending bank immediately that the payment was induced by fraud and ask it to contact the receiving bank. Ask whether the APP reimbursement rules apply; do not describe an authorised scam payment merely as an unauthorised transaction.</span></div>
      <div class="table-row"><strong>You installed remote-access software</strong><span>Disconnect the device, end the remote session and contact the bank from a different trusted device. Remove the software, run a full scan, change exposed passwords, and do not use the affected device for banking until it is secure.</span></div>
      <div class="table-row"><strong>You shared identity documents or personal data</strong><span>Secure the affected accounts, check your credit-reference files for applications you do not recognise — Experian, Equifax and TransUnion are the three main agencies, and MoneyHelper also lists Crediva, and consider Cifas Protective Registration where identity misuse is a realistic risk.</span></div>
    </div>

    <h2>Which money-recovery route applies?</h2>
    <div class="evidence-table-wrap"><table class="evidence-table">
      <thead><tr><th scope="col">How you paid</th><th scope="col">What to ask for</th><th scope="col">Important limits</th></tr></thead>
      <tbody>
        <tr><th scope="row">UK bank transfer</th><td>Report an APP scam claim to the bank or payment firm immediately.</td><td>For eligible Faster Payments and CHAPS payments made on or after 7 October 2024, firms normally decide within five business days. They can stop the clock for information, but must reach an outcome within 35 business days. Scope, exclusions, vulnerability rules, a possible excess of up to £100 and the £85,000 reimbursement cap can affect a claim.</td></tr>
        <tr><th scope="row">Debit, credit or prepaid card</th><td>Ask the issuer to secure the card and whether chargeback fits the transaction.</td><td>Chargeback is a card-scheme process, not a statutory right. MoneyHelper says claims commonly need to be made within 120 days, with timing depending on the transaction, so contact the issuer promptly.</td></tr>
        <tr><th scope="row">Qualifying credit purchase</th><td>Ask whether Section 75 of the Consumer Credit Act 1974 applies.</td><td>The cash price must be over £100 and no more than £30,000, and the required debtor-creditor-supplier relationship and other conditions must be present. It is not generic protection for every card payment.</td></tr>
        <tr><th scope="row">PayPal Goods and Services</th><td>Open the Resolution Centre immediately and check Buyer Protection.</td><td>PayPal's UK terms give 180 days for Item Not Received. A Significantly Not as Described dispute must be opened by the earlier of 30 days after delivery or 180 days after payment.</td></tr>
        <tr><th scope="row">Cash, gift card or cryptocurrency</th><td>Contact the platform, exchange or gift-card issuer immediately and preserve the transaction details.</td><td>Recovery can be difficult, but a fast report may help stop an unused balance or identify a destination. Never pay a recovery service that promises guaranteed results.</td></tr>
      </tbody>
    </table></div>

    <h2>Report the incident</h2>
    <ul>
      <li><strong>{_n(sources, 'action-fraud')}:</strong> use <a href="{_r(sources, 'action-fraud')['info_url']}" rel="noopener noreferrer" target="_blank">{_b(sources, 'action-fraud')}</a> online or call {_r(sources, 'action-fraud')['phone']}.</li>
      <li><strong>{_n(sources, 'police-scotland')}:</strong> report fraud and cybercrime to {_b(sources, 'police-scotland')} on {_r(sources, 'police-scotland')['phone']}. Call 999 if a crime is happening now or someone is in immediate danger.</li>
      <li><strong>Suspicious SMS:</strong> forward it to {_sms(sources)} free of charge. For other message types, use the relevant app or device reporting controls as well.</li>
      <li><strong>Phishing email:</strong> forward it to <a href="mailto:{_email(sources)}">{_email(sources)}</a>. The NCSC also accepts suspicious website reports.</li>
      <li><strong>Impersonated organisation:</strong> tell the bank, retailer, courier, platform or public body through contact details you find independently.</li>
    </ul>

    <h2>Preserve useful evidence</h2>
    <p>Keep the original message, screenshots, sender details, website address, payment receipt, account number or wallet address, call time, and a short timeline of what happened. Do not keep a malicious page open merely to collect evidence. Never send passwords, PINs or full one-time codes in a report.</p>

    <h2>If the bank rejects the claim</h2>
    <p>Ask for the decision and reasons in writing, then use the firm's formal complaints process. If the complaint is not resolved, ask the <a href="https://www.financial-ombudsman.org.uk/consumers/how-to-complain" rel="noopener noreferrer" target="_blank">Financial Ombudsman Service</a> whether it can consider the case. Time limits apply, so do not delay.</p>

    <h2>Primary sources</h2>
    <ul class="sources-checked">
      <li><a href="https://www.ncsc.gov.uk/section/respond-recover/phishing" rel="noopener noreferrer" target="_blank">National Cyber Security Centre — phishing response and recovery</a></li>
      <li><a href="https://www.psr.org.uk/news-and-updates/latest-news/news/groundbreaking-new-protections-for-victims-of-app-scams-start-today/" rel="noopener noreferrer" target="_blank">Payment Systems Regulator — APP reimbursement protections</a></li>
      <li><a href="https://www.moneyhelper.org.uk/en/everyday-money/credit/how-youre-protected-when-you-pay-by-card" rel="noopener noreferrer" target="_blank">MoneyHelper — Section 75 and chargeback</a></li>
      <li><a href="{_r(sources, 'action-fraud')['info_url']}" rel="noopener noreferrer" target="_blank">{_b(sources, 'action-fraud')} — reporting routes for {_n(sources, 'action-fraud')}</a></li>
      <li><a href="{_r(sources, 'police-scotland')['report_url']}" rel="noopener noreferrer" target="_blank">{_b(sources, 'police-scotland')} on {_r(sources, 'police-scotland')['phone']} — the reporting route for {_n(sources, 'police-scotland')}</a></li>
      <li><a href="https://www.ofcom.org.uk/phones-and-broadband/scam-calls-and-messages/what-to-do-about-a-scam-call-text-or-message" rel="noopener noreferrer" target="_blank">Ofcom — reporting suspicious calls and messages</a></li>
      <li><a href="https://www.paypal.com/uk/legalhub/buyer-protection?locale.x=en_US" rel="noopener noreferrer" target="_blank">PayPal UK — Buyer Protection terms</a></li>
    </ul>

    <p class="note" style="margin-top:2rem">This checklist is general educational information, not legal or financial advice. Payment protections depend on the facts of the transaction.</p>
    '''

    # Bump PRIVACY_LAST_UPDATED when materially revising the Privacy Policy below.
    PRIVACY_LAST_UPDATED = "31 July 2026"
    privacy = f'''
    <p class="note" style="color:#666;font-size:.95rem"><strong>Last updated:</strong> {PRIVACY_LAST_UPDATED}</p>

    <p>This Privacy Policy explains how {html.escape(site["site_name"])} uses analytics, advertising, and website technologies when you browse the site. {html.escape(site["site_name"])} is operated by SideRight Apps; for data-protection purposes, <strong>SideRight Apps is the data controller</strong>, and you can contact us at <a href="mailto:{site["privacy_email"]}">{site["privacy_email"]}</a>.</p>
    <h2>What information we collect</h2>
    <p>The site does not offer user accounts, comments, or direct purchases. Standard server logs may record technical data such as browser type, device type, and approximate location.</p>
    <h2>AI scam checker</h2>
    <p>When you use the AI scam checker, the text you submit is sent to Anthropic&#8217;s Claude API for analysis. This text is not stored by Beat the Scam. To prevent abuse of the free tool, the checker keeps a rate-limit counter keyed to a hashed form of your IP address; it is used only to enforce per-minute and daily limits, is never linked to your submission, and is not used to identify you. Do not include full passwords or bank account numbers in checker submissions.</p>
    <h2>Google Analytics</h2>
    <p>The site uses Google Analytics 4. Analytics cookies are only enabled after consent where required.</p>
    <h2>Advertising</h2>
    <p>The site uses Google AdSense. To serve, measure, and (with your consent) personalise ads, Google and its partners may use <strong>cookies, web beacons (pixel tags), your IP address, and device or online identifiers</strong>. In the UK and EEA, your consent for advertising and analytics cookies is collected through Google&#8217;s certified Consent Management Platform (the consent message you see on your first visit), which records your choice under the IAB Transparency &amp; Consent Framework. Until you consent, ads are non-personalised and no advertising-personalisation cookies are set; if you consent, Google and its partners may use the technologies above to personalise and measure ads. On pages dealing with debt, insolvency, or money lost to scams, ads are served non-personalised regardless of consent. You can change your choice any time via the Cookie settings link in the footer: on pages that carry ads this reopens Google&#8217;s consent message, and on pages we serve without ads &#8212; including this one &#8212; it opens this site&#8217;s own cookie choice, which is what governs analytics there. For more on how Google uses this data, see <a href="https://policies.google.com/technologies/partner-sites" rel="noopener noreferrer" target="_blank">How Google uses information from sites that use its services</a>.</p>
    <p>Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this website or other websites. Google&#8217;s use of advertising cookies enables it and its partners to serve ads to you based on your visits to this site and/or other sites on the internet. You can opt out of personalised advertising from Google at any time in <a href="https://adssettings.google.com/" rel="noopener noreferrer" target="_blank">Google Ads Settings</a>, and opt out of many other third-party vendors&#8217; personalised-ad cookies at <a href="https://www.aboutads.info/choices" rel="noopener noreferrer" target="_blank">aboutads.info/choices</a> or, in the UK and Europe, <a href="https://www.youronlinechoices.com/" rel="noopener noreferrer" target="_blank">youronlinechoices.com</a>.</p>
    <h2>Newsletter</h2>
    <p>If you subscribe to email updates we use double opt-in: we email you a confirmation link, and your address is only added to our list once you click it (so no one can sign up an address that isn't theirs). Your email address and consent are then stored by, and the emails delivered through, <strong>Resend</strong> (our email provider). We use your address only to send Beat the Scam updates, never sell or share it, and every email carries a one-click unsubscribe link.</p>
    <h2>Who processes your data</h2>
    <p>We deliberately keep the list of third parties ("sub-processors") that may handle your data short. Each links to its own privacy policy:</p>
    <ul class="list-clean">
      <li><strong>Google</strong> &mdash; Analytics (GA4) and AdSense. Usage data, and &mdash; only after you accept &mdash; advertising and analytics cookies. <a href="https://policies.google.com/privacy" rel="noopener noreferrer" target="_blank">Policy</a>.</li>
      <li><strong>Anthropic</strong> &mdash; processes the text you submit to the AI checker to produce a verdict. We do not store it; Anthropic may retain it for up to 30 days under its standard API policy and does not train on it. <a href="https://www.anthropic.com/legal/privacy" rel="noopener noreferrer" target="_blank">Policy</a>.</li>
      <li><strong>Resend</strong> &mdash; stores newsletter subscribers and delivers our emails. <a href="https://resend.com/legal/privacy-policy" rel="noopener noreferrer" target="_blank">Policy</a>.</li>
      <li><strong>Netlify</strong> &mdash; hosts the site; its server logs may briefly record your IP address and request details for security and reliability. <a href="https://www.netlify.com/privacy/" rel="noopener noreferrer" target="_blank">Policy</a>.</li>
      <li><strong>Ahrefs</strong> &mdash; cookieless visitor analytics, with no personal profiles or cross-site tracking. <a href="https://ahrefs.com/privacy-policy" rel="noopener noreferrer" target="_blank">Policy</a>.</li>
    </ul>
    <h2>Data retention</h2>
    <p>Checker submissions are processed in real time and not stored by Beat the Scam, though Anthropic &mdash; the API provider that analyses the text &mdash; may retain it for up to 30 days under its standard policy. Newsletter data is kept until you unsubscribe. Analytics and server-log data are retained according to each provider's standard periods.</p>
    <h2>Cookie choices</h2>
    <p>In the UK and EEA, a Google-certified consent message lets you accept or reject non-essential (advertising and analytics) cookies on the pages that carry ads, and change your choice at any time via the Cookie settings link in the footer. Pages we serve without ads &#8212; the homepage, the checker, our research and these legal pages &#8212; run no advertising cookies at all, so there the same link opens this site&#8217;s own cookie choice, covering analytics. Elsewhere, a simple cookie banner offers the same accept/reject choice, stored locally in your browser.</p>
    <h2>Our lawful bases</h2>
    <p>We rely on your <strong>consent</strong> for advertising and analytics cookies and for newsletter emails &mdash; you can withdraw it at any time (via the Cookie settings link, by unsubscribing, or by contacting us), without affecting any processing already carried out. We rely on <strong>legitimate interests</strong> for essential security and server logging and for operating the AI checker you choose to use.</p>
    <h2>Automated decisions and international transfers</h2>
    <p>The AI scam checker returns an automated, educational assessment of the text you submit; it does <strong>not</strong> make any decision that produces a legal or similarly significant effect on you. Some processors (for example Google and Anthropic) may process data outside the UK/EEA; where they do, transfers are covered by appropriate safeguards such as the UK International Data Transfer Addendum or EU Standard Contractual Clauses.</p>
    <h2>Your rights</h2>
    <p>If you are in the UK or EEA you have the right to <strong>access</strong>, <strong>rectify</strong>, <strong>erase</strong>, <strong>restrict</strong> or <strong>object</strong> to the processing of your personal data, to <strong>data portability</strong>, and to <strong>withdraw consent</strong> at any time. To exercise any of these, email <a href="mailto:{site["privacy_email"]}">{site["privacy_email"]}</a>. You also have the right to lodge a complaint with the UK <strong>Information Commissioner&#8217;s Office (ICO)</strong> at <a href="https://ico.org.uk/" rel="noopener noreferrer" target="_blank">ico.org.uk</a> (or, in the EEA, your local data-protection authority) &mdash; though we&#8217;d appreciate the chance to put things right first.</p>
    '''

    cookies = f'''
    <p>This Cookie Policy explains what cookies and similar technologies may be used on {html.escape(site["site_name"])}.</p>
    <h2>Essential storage</h2>
    <p>The site stores a small preference in your browser to remember whether you accepted or rejected non-essential cookies.</p>
    <h2>Analytics cookies</h2>
    <p>If you accept analytics cookies, Google Analytics 4 may collect information about page views, device type, and interaction patterns.</p>
    <h2>Advertising cookies</h2>
    <p>If advertising is active and you consent, Google AdSense may use cookies to support ad delivery and measurement. In the UK and EEA your advertising and analytics consent is collected through Google&#8217;s certified Consent Management Platform under the IAB Transparency &amp; Consent Framework; until you consent, ads are non-personalised. Third-party vendors, including Google, use cookies to serve ads based on your prior visits to this website or other websites; you can opt out of personalised advertising in <a href="https://adssettings.google.com/" rel="noopener noreferrer" target="_blank">Google Ads Settings</a> or at <a href="https://www.aboutads.info/choices" rel="noopener noreferrer" target="_blank">aboutads.info/choices</a>.</p>
    <h2>How to manage cookies</h2>
    <p>Change browser cookie settings at any time, or use the Cookie settings link in the footer. On a page carrying ads that reopens Google&#8217;s certified consent message; on a page without ads it opens this site&#8217;s own cookie choice, since no advertising cookies are set there.</p>
    <h2>Contact</h2>
    <p>Cookie and privacy questions: <a href="mailto:{site["privacy_email"]}">{site["privacy_email"]}</a>.</p>
    '''

    # Bump TERMS_LAST_UPDATED when materially revising the Terms text below.
    # The date is shown to users at the top of /terms/ as the legal effective date.
    TERMS_LAST_UPDATED = "23 June 2026"
    terms = f'''
    <p class="note" style="color:#666;font-size:.95rem"><strong>Last updated:</strong> {TERMS_LAST_UPDATED}</p>

    <p>These Terms set out the rules for using <strong>beatthescam.com</strong> ("the Site"). By using the Site you agree to them. If you do not agree, please do not use the Site.</p>

    <h2>About this site</h2>
    <p>Beat the Scam publishes plain-English guides about scams and fraud affecting UK consumers, and offers a free AI scam checker. The Site is operated by SideRight Apps. Editorial decisions are made by Alex Bacsa, Founder &amp; Editor.</p>

    <h2>Educational purpose &mdash; not professional advice</h2>
    <p>Everything published here is general educational information. It is <strong>not</strong> legal, financial, investment, tax, medical, cybersecurity, or regulatory advice, and reading it does not create an advisor&ndash;client relationship. See our full <a href="/disclaimer/">Disclaimer</a> for the detail.</p>
    <p>Scam tactics change rapidly. No article can guarantee that a specific message, listing, website or interaction is safe or fraudulent. If anything you read here is material to your circumstances, verify it through official UK channels &#8212; the police reporting route for your nation ({police_route_html(sources, phone=False, url=False)}), the FCA Register, Companies House, the consumer service for your nation, or your bank&#8217;s published fraud line &#8212; or seek qualified professional advice.</p>

    <h2>The AI scam checker</h2>
    <p>The AI scam checker is an educational tool that returns an automated plain-English assessment. Its output is <strong>not</strong> a definitive fraud determination and we make no warranty that it will identify every scam or that flagged messages are necessarily fraudulent.</p>
    <p>Do not rely on the checker alone for high-stakes decisions. If you have already sent money, shared bank details, or shared one-time codes, contact your bank immediately and report the incident to {police_route_html(sources)}.</p>

    <h2>Your responsibilities</h2>
    <p>You agree to use the Site lawfully and reasonably. You must not:</p>
    <ul>
      <li>Submit content to the AI scam checker that contains other people&#8217;s personal data (full names, account numbers, ID document numbers) &mdash; redact before pasting</li>
      <li>Scrape, mirror, or republish substantial portions of the Site without prior written permission</li>
      <li>Use automated tools to overload the Site or the AI scam checker</li>
      <li>Use the Site to commit, promote, or facilitate fraud</li>
      <li>Misrepresent any Site content as the official position of any third party the Site discusses</li>
    </ul>

    <h2>Intellectual property</h2>
    <p>All original content on the Site &mdash; articles, guides, images, the brand, and the structure of the AI scam checker output &mdash; is copyright Beat the Scam / SideRight Apps unless stated otherwise. You may quote up to a short paragraph with attribution and a link back to the source article. For larger reproductions, please ask first at <a href="mailto:{site["legal_email"]}">{site["legal_email"]}</a>.</p>

    <h2>Advertising and product recommendations</h2>
    <p>The Site is funded by display advertising (currently Google AdSense). Some guides also link to third-party products and services we consider genuinely useful (such as credit-file monitoring, identity-protection, and consumer-legal services). At present these are <strong>independent, unpaid editorial recommendations</strong>: we earn no commission on them, they carry a <code>rel="nofollow"</code> attribute, and they never change the editorial position of any guide.</p>
    <p>If we enter a paid affiliate arrangement in future, we will disclose it clearly beside the recommendation and mark those links <code>rel="sponsored"</code>, as required by the UK Advertising Standards Authority CAP Code and by Google&#8217;s quality guidelines. We only recommend products we would suggest a friend use. If you would like us to remove a specific recommendation, write to us at the contact address below.</p>

    <h2>External links</h2>
    <p>The Site links to third-party services and official resources (government sites, regulators, banks, news outlets). Those sites operate under their own terms and privacy policies and we have no control over their content, accuracy, or availability.</p>

    <h2>Privacy and cookies</h2>
    <p>How we handle personal data and cookies is explained in our <a href="/privacy/">Privacy Policy</a> and <a href="/cookies/">Cookie Policy</a>. Use of the Site is subject to those documents as well as these Terms.</p>

    <h2>Limitation of liability</h2>
    <p>To the maximum extent permitted by law, Beat the Scam, SideRight Apps, and its publisher and editor are not liable for any loss, damage, or expense arising from your use of the Site or your reliance on its content &mdash; including the AI scam checker. We make no warranty that the Site will be uninterrupted, error-free, or secure.</p>
    <p><strong>Nothing in these Terms limits or excludes our liability for:</strong> (a) death or personal injury caused by our negligence; (b) fraud or fraudulent misrepresentation; (c) any other liability that cannot lawfully be limited or excluded under English, Scots, or Northern Ireland law &mdash; including your statutory rights as a consumer.</p>

    <h2>Changes to these Terms</h2>
    <p>We may update these Terms from time to time to reflect changes to the Site, to the law, or to industry practice. The &#8220;Last updated&#8221; date at the top of this page shows when the current version took effect. Continuing to use the Site after a change means you accept the updated Terms.</p>

    <h2>Governing law and jurisdiction</h2>
    <p>These Terms are governed by the laws of <strong>England and Wales</strong>. If you are resident in <strong>Scotland</strong>, these Terms are governed by <strong>Scots law</strong> and the Scottish courts have non-exclusive jurisdiction over any dispute arising from them. If you are resident in <strong>Northern Ireland</strong>, the courts of Northern Ireland have non-exclusive jurisdiction. None of this affects your mandatory statutory consumer rights in your country of residence.</p>

    <h2>Contact</h2>
    <p>For questions about these Terms, copyright, or other legal matters, email <a href="mailto:{site["legal_email"]}">{site["legal_email"]}</a>. For corrections to a guide, email <a href="mailto:{site["editorial_email"]}">{site["editorial_email"]}</a> with the page URL and the change requested. For privacy and data-protection requests, see the <a href="/privacy/">Privacy Policy</a>.</p>
    '''

    contact = f'''
    <p>For editorial contact or corrections, email <a href="mailto:{site["editorial_email"]}">{site["editorial_email"]}</a>. For partnership enquiries, email <a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a>. For privacy, legal, or security matters, please use the dedicated addresses below.</p>
    <div class="tablelike">
      <div class="table-row"><strong>Editorial &amp; corrections</strong><span><a href="mailto:{site["editorial_email"]}">{site["editorial_email"]}</a> &mdash; send the page URL and the correction you want reviewed.</span></div>
      <div class="table-row"><strong>Advertising or partnerships</strong><span><a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a> &mdash; include the business name, proposal, and relevant website.</span></div>
      <div class="table-row"><strong>Privacy &amp; data protection</strong><span><a href="mailto:{site["privacy_email"]}">{site["privacy_email"]}</a> &mdash; reference &#8220;Privacy request&#8221; in the subject line.</span></div>
      <div class="table-row"><strong>Legal &amp; copyright</strong><span><a href="mailto:{site["legal_email"]}">{site["legal_email"]}</a> &mdash; Terms, intellectual property, and reproduction requests.</span></div>
      <div class="table-row"><strong>Security disclosure</strong><span><a href="mailto:{site["security_email"]}">{site["security_email"]}</a> &mdash; see also our <a href="/.well-known/security.txt">security.txt</a>.</span></div>
    </div>
    <p class="note" style="margin-top:1.5rem">To report a scam to UK authorities directly, use {police_route_html(sources, phone=False, url=False)}. Ofcom says suspicious SMS texts can be forwarded to <strong>{_sms(sources)}</strong> free of charge; use the relevant app's own reporting tool for non-SMS messages.</p>
    '''

    disclaimer = f'''
    <p class="note" style="color:#666;font-size:.95rem"><strong>Last updated:</strong> 24 June 2026</p>

    <p>Everything published on <strong>{html.escape(site["site_name"])}</strong> &mdash; the guides, the AI scam checker, and any other material &mdash; is provided for <strong>general education and consumer awareness only</strong>. This page sets out the limits of that information. By using the Site you accept this disclaimer alongside our <a href="/terms/">Terms</a>.</p>

    <h2>Not professional advice</h2>
    <p>The content here is <strong>not</strong> legal, financial, investment, tax, accounting, cybersecurity, or regulatory advice, and reading it does <strong>not</strong> create an advisor&ndash;client or other professional relationship. It cannot account for your individual circumstances. Before acting on anything that materially affects your money, identity, or legal position, seek advice from a suitably qualified professional or an official UK body &mdash; for example the <a href="https://www.fca.org.uk/" rel="noopener noreferrer" target="_blank">FCA</a>, the <a href="{_consumer_advice_url(sources)}" rel="noopener noreferrer" target="_blank">consumer service for your nation</a>, or your bank&#8217;s published fraud line.</p>

    <h2>No guarantees about specific messages or websites</h2>
    <p>Scam tactics change constantly. No guide, and no result from the AI scam checker, can guarantee that a particular message, email, website, listing, phone call, or investment is either safe or fraudulent. A &#8220;probably legitimate&#8221; result is not a green light, and the absence of a warning is not a guarantee of safety. Always verify independently through an official channel you find yourself &mdash; never through a link, phone number, or payment detail supplied in the suspicious message.</p>

    <h2>About the AI scam checker</h2>
    <p>The scam checker returns an <strong>automated, educational</strong> assessment generated by an AI model. It can be wrong in both directions &mdash; flagging genuine messages and missing real scams &mdash; and it does <strong>not</strong> make any decision that produces a legal or similarly significant effect on you. Do not rely on it alone for a high-stakes decision. The text you submit is processed to produce a verdict and is not stored by Beat the Scam; see the <a href="/privacy/">Privacy Policy</a> for how it handles data.</p>

    <h2>Accuracy and corrections</h2>
    <p>We take accuracy seriously: every guide passes an automated accuracy gate before publication and is reviewed on a recurring schedule. Even so, the Site may contain errors, omissions, or information that has gone out of date. If you spot something wrong, please email <a href="mailto:{site["editorial_email"]}">{site["editorial_email"]}</a> with the page URL and we will correct it promptly.</p>

    <h2>External links</h2>
    <p>The Site links to third-party resources such as government sites, regulators, banks, and news outlets. Those sites operate under their own terms and privacy policies, and we have no control over and accept no responsibility for their content, accuracy, or availability.</p>

    <h2>If you think you have been scammed</h2>
    <p>If you have already sent money, shared bank or card details, or shared one-time passcodes, act immediately: contact your bank using the number on the back of your card, and report it to {police_route_html(sources)}. You can forward scam texts to <strong>{_sms(sources)}</strong> and suspicious emails to <strong>{_email(sources)}</strong>.</p>

    <h2>Liability</h2>
    <p>To the maximum extent permitted by law, Beat the Scam and SideRight Apps accept no liability for any loss or damage arising from your use of, or reliance on, the Site or the AI scam checker. Nothing here limits any liability that cannot lawfully be excluded &mdash; including for death or personal injury caused by negligence, or for fraud. The full limitation of liability is set out in our <a href="/terms/">Terms</a>.</p>
    '''

    return about, privacy, cookies, terms, contact, disclaimer, methodology, corrections, recovery


# ─── DEDUPLICATE ────────────────────────────────────────────────────────────

def disambiguate_slugs(posts: list) -> list:
    """Ensure every post keeps a unique slug, preserving all posts.

    For colliding slugs, the newest post wins the canonical slug; older
    posts get -2, -3 suffixes. This avoids the previous behaviour of
    silently dropping duplicates and losing indexable content.

    Posts that share a slug AND identical (title, description) — i.e.
    obvious accidental re-imports of the same article — are still
    deduplicated (newer kept) since they offer no SEO value as two pages.
    """
    by_slug: dict = {}
    for post in posts:
        by_slug.setdefault(post["slug"], []).append(post)

    out = []
    for slug, group in by_slug.items():
        group.sort(key=lambda p: p["date"], reverse=True)

        # Drop literal duplicates (same title+description) — keep newest only.
        seen_key = set()
        unique = []
        for p in group:
            key = (p.get("title", "").strip().lower(), p.get("description", "").strip().lower())
            if key in seen_key:
                continue
            seen_key.add(key)
            unique.append(p)

        if len(unique) == 1:
            out.append(unique[0])
            continue

        # First entry keeps the canonical slug; rest get -2, -3, ...
        # CAUTION: some "-2" slugs are ARTICLE_REDIRECTS keys (dead pages that
        # now 301). A new collision minting one of those slugs would resurrect
        # a URL the forced 301 then shadows — build() asserts against this.
        out.append(unique[0])
        for idx, p in enumerate(unique[1:], start=2):
            new_slug = f"{slug}-{idx}"
            p = dict(p)
            p["slug"] = new_slug
            out.append(p)
            print(f"  slug-collision: '{slug}' → kept newest, renamed older to '{new_slug}'")

    return sorted(out, key=lambda p: p["date"], reverse=True)


# ─── PARAGRAPH SPLITTING ───────────────────────────────────────────────────

def split_into_paragraphs(body: str, max_words: int = 100) -> list:
    """Split a section body into HTML-paragraph-sized chunks.

    The AI content generator emits each section as a single 130–215 word
    blob with no `\\n\\n` breaks, which renders as one giant `<p>` and
    triggers Semrush's "paragraphs are too long" warning on every guide
    (~157 pages in the 2026-05-30 audit). Hand-written sections that do
    use `\\n\\n` are respected verbatim.

    Algorithm:
      1. Respect any explicit `\\n\\n` author breaks first.
      2. For each resulting paragraph still over max_words, split at
         sentence boundaries (end-of-sentence punctuation followed by a
         capital letter) and re-pack into chunks up to max_words.

    Returns a list of paragraph strings (still plain text — caller is
    responsible for html-escaping + wrapping in `<p>`).
    """
    body = (body or "").strip()
    if not body:
        return []
    raw = [p.strip() for p in body.split("\n\n") if p.strip()]
    out = []
    for para in raw:
        if len(para.split()) <= max_words:
            out.append(para)
            continue
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", para)
        chunk: list = []
        chunk_words = 0
        for s in sentences:
            sw = len(s.split())
            if chunk and chunk_words + sw > max_words:
                out.append(" ".join(chunk))
                chunk = []
                chunk_words = 0
            chunk.append(s)
            chunk_words += sw
        if chunk:
            out.append(" ".join(chunk))
    return out


# ─── INTERNAL LINKING ──────────────────────────────────────────────────────

# Regions inside these tags are skipped for auto-linking. Avoids:
# - Double-wrapping existing <a>
# - Linking inside headings (already strong signals)
# - Mangling code/pre blocks
# - CRITICAL: injecting <a> tags into <title>, <meta>, or <script> inside <head>
#   (previously caused raw HTML to appear in the <title> element when a guide's
#   title contained a phrase matching another guide's keyword)
_INTERNAL_LINK_EXCLUDED_RE = re.compile(
    r'<head\b[^>]*>.*?</head>'           # entire <head> block — protects <title>, <meta>, <link>
    r'|<script\b[^>]*>.*?</script>'      # inline/external scripts anywhere in the document
    r'|<style\b[^>]*>.*?</style>'        # inline styles
    r'|<noscript\b[^>]*>.*?</noscript>'  # noscript blocks
    r'|<a\s[^>]*>.*?</a>'               # existing anchor tags (prevent double-wrapping)
    r'|<span[^>]*class="bc-title"[^>]*>.*?</span>'  # breadcrumb title text
    r'|<h[1-6][^>]*>.*?</h[1-6]>'       # headings
    r'|<code[^>]*>.*?</code>'            # inline code
    r'|<pre[^>]*>.*?</pre>',             # code blocks
    re.IGNORECASE | re.DOTALL,
)

# Phrases too generic to auto-link — would over-fire across the site.
_INTERNAL_LINK_STOPWORDS = {
    "uk bank", "text message", "text messages", "phone scam",
    "email scam", "text scam", "scam email", "scam text",
    "bank scam", "uk", "scam", "phone", "text",
}

# Ambiguous phrases are not auto-linked unless editorially assigned here. This
# prevents list order from silently deciding which of several competing guides
# receives every link for a shared keyword.
_CANONICAL_KEYWORD_OWNERS = {
    "remote access scam uk": "remote-access-scam-uk",
}


def build_internal_link_map(posts):
    """Build a phrase → guide-URL map from each post's keywords.

    Filters keywords to phrases that are 2+ words long, lowercase and not
    stop-listed. A duplicated phrase is excluded unless it has an explicit
    editorial owner in _CANONICAL_KEYWORD_OWNERS.
    """
    phrase_posts = defaultdict(list)
    for post in posts:
        slug = post.get("slug")
        if not slug:
            continue
        for kw in post.get("keywords", []):
            phrase = (kw or "").lower().strip()
            if not phrase or len(phrase.split()) < 2:
                continue
            if phrase in _INTERNAL_LINK_STOPWORDS:
                continue
            if slug not in phrase_posts[phrase]:
                phrase_posts[phrase].append(slug)

    live_slugs = {p.get("slug") for p in posts}
    link_map: dict = {}
    for phrase, slugs in phrase_posts.items():
        owner = _CANONICAL_KEYWORD_OWNERS.get(phrase)
        if owner:
            if owner not in live_slugs:
                raise SystemExit(f"ERROR: internal-link owner {owner!r} for {phrase!r} is not live")
            link_map[phrase] = f"/guides/{owner}/"
        elif len(slugs) == 1:
            link_map[phrase] = f"/guides/{slugs[0]}/"
    return link_map


_ANCHOR_SPAN_RE = re.compile(r"<a\b[^>]*>.*?</a>", re.IGNORECASE | re.DOTALL)


def _pos_inside_anchor(text: str, pos: int) -> bool:
    """True if `pos` in `text` falls inside any `<a>...</a>` span.

    Used by apply_internal_links to skip matches that would create
    nested anchor tags (illegal HTML, and Semrush flags the resulting
    empty outer anchor as 'no anchor text').
    """
    for m in _ANCHOR_SPAN_RE.finditer(text):
        if m.start() <= pos < m.end():
            return True
        if m.start() > pos:
            return False
    return False


def _pos_inside_tag(text: str, pos: int) -> bool:
    """True if `pos` falls inside an HTML tag (between '<' and '>'), i.e. in
    attribute space rather than a text node.

    The excluded-zone regexes protect whole ELEMENTS (<a>…</a>, headings,
    <head>…), but a "plain" zone still contains other elements' opening tags —
    e.g. <img alt="royal mail text example">. Substituting there would inject
    an <a> INTO the attribute value and silently corrupt the page, so every
    linkifier must skip matches at these positions.
    """
    lt = text.rfind("<", 0, pos)
    if lt == -1:
        return False
    return text.rfind(">", 0, pos) < lt


def apply_internal_links(html_str: str, current_slug: str, link_map: dict, max_total: int = 5) -> str:
    """Auto-link plain-text occurrences of mapped phrases inside post HTML.

    Rules:
    - Skips text inside <a>, <h1-6>, <code>, <pre>
    - Skips phrases pointing to the current post (no self-links)
    - Max one link per phrase, max max_total links per article
    - Longer phrases matched first (avoids partial-overlap issues)
    - Whole-word match, case-insensitive, original case preserved
    """
    if not link_map or not html_str:
        return html_str

    self_url = f"/guides/{current_slug}/"
    candidates = sorted(
        ((p, u) for p, u in link_map.items() if u != self_url),
        key=lambda kv: -len(kv[0]),
    )
    if not candidates:
        return html_str

    zones = []
    last_end = 0
    for m in _INTERNAL_LINK_EXCLUDED_RE.finditer(html_str):
        if m.start() > last_end:
            zones.append(("plain", html_str[last_end:m.start()]))
        zones.append(("excluded", m.group()))
        last_end = m.end()
    if last_end < len(html_str):
        zones.append(("plain", html_str[last_end:]))

    used = set()
    added = 0
    out = []
    for kind, text in zones:
        if kind == "excluded" or added >= max_total:
            out.append(text)
            continue
        for phrase, url in candidates:
            if phrase in used or added >= max_total:
                continue
            pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
            # Iterate matches so we can skip ones that fall inside an
            # anchor we inserted on an earlier candidate. Without this
            # guard we produce nested <a><a></a> — the outer one ends up
            # with no anchor text (the Semrush "links with no anchor
            # text" warning on 7 pages in the 2026-05-30 audit).
            for m in pat.finditer(text):
                if _pos_inside_anchor(text, m.start()) or _pos_inside_tag(text, m.start()):
                    continue
                text = text[:m.start()] + f'<a href="{url}">{m.group()}</a>' + text[m.end():]
                used.add(phrase)
                added += 1
                break
        out.append(text)
    return "".join(out)


# ─── OG IMAGE GENERATION ───────────────────────────────────────────────────

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except Exception:
    _PIL_OK = False


_OG_W, _OG_H = 1200, 630


def _load_font(size: int):
    """Best-effort font load — try common system fonts, fall back to default."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int):
    words = text.split()
    lines = []
    current = []
    for word in words:
        trial = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def generate_og_image(out_path: Path, title: str, category_label: str, site_name: str):
    """Write a 1200x630 branded OG image for a single post. No-op if Pillow missing."""
    if not _PIL_OK:
        return False
    img = Image.new("RGB", (_OG_W, _OG_H), color=(11, 18, 32))  # matches theme-color #0b1220
    draw = ImageDraw.Draw(img)

    # Subtle accent bar
    draw.rectangle([(0, 0), (_OG_W, 12)], fill=(58, 134, 255))

    # Bottom branding strip
    draw.rectangle([(0, _OG_H - 90), (_OG_W, _OG_H)], fill=(15, 24, 42))

    pad = 80
    body_width = _OG_W - pad * 2

    cat_font   = _load_font(34)
    title_font = _load_font(64)
    brand_font = _load_font(36)
    tag_font   = _load_font(28)

    # Eyebrow / category
    draw.text((pad, 90), category_label.upper(), font=cat_font, fill=(140, 198, 255))

    # Title — wrap and cap at 4 lines
    lines = _wrap_text(draw, title, title_font, body_width)[:4]
    y = 160
    line_height = 78
    for line in lines:
        draw.text((pad, y), line, font=title_font, fill=(255, 255, 255))
        y += line_height

    # Brand
    draw.text((pad, _OG_H - 72), site_name, font=brand_font, fill=(255, 255, 255))
    draw.text((pad, _OG_H - 36), "Scam alerts, plain-English checks", font=tag_font, fill=(140, 198, 255))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)
    return True


# ─── BARE-PATH LINKIFY ─────────────────────────────────────────────────────

_BARE_PATH_RE = re.compile(r"(?<![\"'>=/])(/guides/[a-z0-9][a-z0-9-]+/)(?![A-Za-z0-9-])")

_BARE_PATH_EXCLUDED_RE = re.compile(
    r'<head\b[^>]*>.*?</head>'
    r'|<script\b[^>]*>.*?</script>'
    r'|<style\b[^>]*>.*?</style>'
    r'|<noscript\b[^>]*>.*?</noscript>'
    r'|<a\s[^>]*>.*?</a>'
    r'|<code[^>]*>.*?</code>'
    r'|<pre[^>]*>.*?</pre>',
    re.IGNORECASE | re.DOTALL,
)


def linkify_bare_paths(html_str: str, slug_titles: dict) -> str:
    """Convert AI-generated bare '/guides/xyz/' text into proper anchor tags.

    Skips inside <head>, <script>, <style>, existing <a>, <code>, <pre> — same
    zones as apply_internal_links to avoid double-wrapping or touching
    metadata/structured-data blocks.
    """
    if not html_str:
        return html_str

    zones = []
    last_end = 0
    for m in _BARE_PATH_EXCLUDED_RE.finditer(html_str):
        if m.start() > last_end:
            zones.append(("plain", html_str[last_end:m.start()]))
        zones.append(("excluded", m.group()))
        last_end = m.end()
    if last_end < len(html_str):
        zones.append(("plain", html_str[last_end:]))

    out = []
    for kind, text in zones:
        if kind == "excluded":
            out.append(text)
        else:
            def replace_match(m, _text=text):
                if _pos_inside_tag(_text, m.start()):   # e.g. an href/content attribute
                    return m.group(0)
                path = m.group(1)
                slug = path.strip("/").split("/")[-1]
                link_text = slug_titles.get(slug) or slug.replace("-", " ")
                return f'<a href="{path}">{html.escape(link_text)}</a>'
            out.append(_BARE_PATH_RE.sub(replace_match, text))
    return "".join(out)


# Static redirects PLUS every consolidation declared on a record. build()
# populates this from corpus.redirect_map() before rendering starts; it is the
# single map the edge rules and the internal-link canonicaliser both read, so a
# consolidated guide cannot be 301'd at the edge while internal links still
# point at the dead slug.
EFFECTIVE_REDIRECTS: dict = dict(ARTICLE_REDIRECTS)


def canonicalize_internal_guide_paths(html_str: str) -> str:
    """Replace internal links to redirected guide slugs with final URLs.

    Edge redirects remain for external/history traffic, but internal navigation
    should not add a crawl hop after articles are consolidated.
    """
    for old_slug, target in EFFECTIVE_REDIRECTS.items():
        if target.startswith("__CAT__:"):
            continue
        html_str = html_str.replace(
            f"/guides/{old_slug}/", f"/guides/{target}/")
    return html_str


# ─── PHONE LINKIFY ─────────────────────────────────────────────────────────

# Match UK helpline patterns: 0300/0800/0808/0345 prefix, then space-separated digits.
_PHONE_RE = re.compile(r"\b(0(?:300|800|808|345|371|370)\s\d{3}\s\d{3,4})\b")


def linkify_phones(html_str: str) -> str:
    """Wrap UK consumer-helpline numbers in tel: anchors so they're tappable on mobile."""
    if not html_str:
        return html_str
    zones = []
    last_end = 0
    for m in _BARE_PATH_EXCLUDED_RE.finditer(html_str):
        if m.start() > last_end:
            zones.append(("plain", html_str[last_end:m.start()]))
        zones.append(("excluded", m.group()))
        last_end = m.end()
    if last_end < len(html_str):
        zones.append(("plain", html_str[last_end:]))

    out = []
    for kind, text in zones:
        if kind == "excluded":
            out.append(text)
        else:
            def replace(m, _text=text):
                if _pos_inside_tag(_text, m.start()):   # e.g. an aria-label/alt value
                    return m.group(0)
                number = m.group(1)
                tel = "+44" + number.replace(" ", "")[1:]
                return f'<a href="tel:{tel}">{number}</a>'
            out.append(_PHONE_RE.sub(replace, text))
    return "".join(out)


# ─── MAIN BUILD ────────────────────────────────────────────────────────────

def build():
    site     = read_json(ROOT / 'content/site.json')
    raw_posts = read_json(ROOT / 'content/posts.json')
    research_reports = load_research_reports(ROOT)
    stats_page = load_stats_page(ROOT)

    affiliates = load_affiliates(ROOT)
    sources    = load_sources(ROOT)
    category_hubs = load_category_hubs(ROOT)
    validate_category_hubs(category_hubs)

    # Normalise category names
    for post in raw_posts:
        post["category"] = normalize_category(post["category"])

    # Disambiguate slug collisions — preserve all posts, never silently drop.
    # Validate the RAW records first. disambiguate_slugs() renames a duplicate
    # to `<slug>-2`, so running it before the validator meant the duplicate-slug
    # rule could never fire — the validator only ever saw a deduplicated list
    # (operator review, 2026-07-30). Duplicate source slugs make "which record
    # is consolidated?" order-dependent, so they must stop the build.
    raw_problems = corpus_mod.validate_consolidation(raw_posts, ARTICLE_REDIRECTS)
    if raw_problems:
        for msg in raw_problems:
            print(f"  posts.json: {msg}")
        raise SystemExit(
            f"ERROR: content/posts.json is invalid before normalisation "
            f"({len(raw_problems)} problem(s))"
        )

    all_posts = disambiguate_slugs(raw_posts)

    # Source records → the PUBLIC corpus. A record carrying `consolidated_into`
    # is retained archive data: never rendered, 301'd at the edge, and outside
    # the publication similarity check. scripts/corpus.py owns that partition
    # and validates the whole graph — missing, self-referencing or unknown
    # targets, chains, cycles, duplicate slugs, and any collision with the
    # static redirect map all stop the build here rather than producing a
    # half-published corpus.
    global EFFECTIVE_REDIRECTS
    try:
        posts, consolidated = corpus_mod.partition(all_posts, ARTICLE_REDIRECTS)
        EFFECTIVE_REDIRECTS = corpus_mod.redirect_map(all_posts, ARTICLE_REDIRECTS)
    except corpus_mod.CorpusError as exc:
        raise SystemExit(f"ERROR: {exc}")

    # A live guide must never share a slug with a redirect key: the 301 is
    # emitted with "301!" (forced), which overrides the static file at the edge,
    # so the page would build fine yet be unreachable with no error anywhere.
    # Fail the build loudly instead.
    shadowed = set(EFFECTIVE_REDIRECTS) & {p["slug"] for p in posts}
    if shadowed:
        raise SystemExit(
            f"ERROR: live guide slug(s) shadowed by a forced 301: "
            f"{sorted(shadowed)} — rename the guide slug or drop the redirect.")

    categories = defaultdict(list)
    for post in posts:
        categories[post['category']].append(post)

    # Slug → title map for bare-path linkification (used per-guide below)
    slug_titles = {p["slug"]: p["title"] for p in posts}

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    # Copy assets → dist, but never the audio/ bed: it's a local video-render
    # asset (licensed stock music). Serving the raw file publicly would breach
    # most free-music licenses (no standalone redistribution) and bloat the deploy.
    # video/ (end-card for the discontinued video pipeline) and the superseded
    # og-image.png (og-image-v2.png is the referenced card) are local-only too.
    shutil.copytree(ROOT / 'assets', DIST / 'assets',
                    ignore=shutil.ignore_patterns('audio', '*.mp3', '*.wav', '*.aac',
                                                  'video', 'og-image.png', '.DS_Store'))

    # Minify styles.css + app.js in place — clears the Semrush
    # "unminified JS/CSS" warnings (counted on every crawled page, so the
    # cost of one minify wipes hundreds of warnings). Falls back silently
    # if rcssmin/rjsmin aren't installed so a missing dep never breaks
    # the build for a dev who hasn't pip-installed them yet.
    try:
        import rcssmin, rjsmin
        for path, fn in [
            (DIST / 'assets' / 'styles.css', rcssmin.cssmin),
            (DIST / 'assets' / 'app.js',     rjsmin.jsmin),
        ]:
            if not path.exists():
                continue
            original = path.read_text(encoding='utf-8')
            minified = fn(original)
            path.write_text(minified, encoding='utf-8')
            saved = len(original) - len(minified)
            pct = (saved / len(original) * 100) if original else 0
            print(f"  Minified {path.name}: {len(original)}B → {len(minified)}B (-{pct:.0f}%)")
    except ImportError:
        print("  (minify skipped — `pip install rcssmin rjsmin` to enable)")

    # Cache-busting asset versions. styles.css/app.js are served with a 1-year
    # `immutable` cache and non-versioned filenames, so returning visitors keep
    # stale CSS/JS after a deploy unless the URL changes. Append ?v=<hash> of the
    # FINAL (post-minify) dist file: stable when content is unchanged (cache hit
    # preserved), new when it changes (forces a fresh fetch). Computed here,
    # after minify and before any page render, so every page embeds it.
    def _asset_ver(path):
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()[:10]
        except OSError:
            return ""
    site['_asset_ver_css'] = _asset_ver(DIST / 'assets' / 'styles.css')
    site['_asset_ver_js']  = _asset_ver(DIST / 'assets' / 'app.js')

    # Populate footer category links (used by make_base via {{footer_cats}})
    global _FOOTER_CATS_HTML
    _FOOTER_CATS_HTML = "\n".join(
        f'<li><a href="/categories/{slugify(cat)}/">{html.escape(category_label(cat))}</a></li>'
        for cat in sorted(categories.keys(), key=lambda c: len(categories[c]), reverse=True)
    )

    # Copy root-level static files (favicons, webmanifest) → dist/ root
    # so they're served from /favicon.svg, /favicon.ico, /site.webmanifest etc.
    static_dir = ROOT / 'static'
    if static_dir.is_dir():
        for src in static_dir.iterdir():
            if src.is_file():
                shutil.copy2(src, DIST / src.name)

    write(DIST / 'index.html',       render_home(site, posts, categories, research_reports))
    write(DIST / 'categories/index.html', render_categories_index(site, categories))
    for cat, items in categories.items():
        write(DIST / 'categories' / slugify(cat) / 'index.html', render_category_page(site, cat, items, categories, hub=category_hubs.get(cat)))

    # Paginated /guides/ index (30 per page, with rel=next/prev wired through make_base)
    total_pages = max(1, (len(posts) + GUIDES_PER_PAGE - 1) // GUIDES_PER_PAGE)
    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * GUIDES_PER_PAGE
        page_posts = posts[start:start + GUIDES_PER_PAGE]
        html_page = render_guides_index_page(site, page_posts, page_num, total_pages, posts)
        out_path = DIST / 'guides' / 'index.html' if page_num == 1 else DIST / 'guides' / 'page' / str(page_num) / 'index.html'
        write(out_path, html_page)

    # Build phrase → URL map once for the whole site, then auto-link
    # contextual mentions inside each rendered guide before writing.
    link_map = build_internal_link_map(posts)

    # Per-post OG image generation (no-op if Pillow missing)
    og_dir = DIST / 'assets' / 'og'
    og_dir.mkdir(parents=True, exist_ok=True)
    og_gen_count = 0

    for post in posts:
        # Generate the OG image first so the rendered HTML references a real file.
        og_out = og_dir / f"{post['slug']}.png"
        if generate_og_image(og_out, post["title"], category_label(post["category"]), site["site_name"]):
            og_gen_count += 1

        html_out = render_post(site, post, posts, affiliates, sources,
                                link_map=link_map, slug_titles=slug_titles)
        write(DIST / 'guides' / post['slug'] / 'index.html', html_out)

    if not _PIL_OK:
        print("  Pillow not installed — per-post OG images skipped (using site default).")
    else:
        print(f"  Generated {og_gen_count} per-post OG images in /assets/og/")

    write(DIST / 'check/index.html', render_check_page(site, sources))
    write(DIST / 'newsletter-confirmed/index.html', render_newsletter_confirmed_page(site))

    # Public research section. Reports are generated from retained, dated
    # platform snapshots and rendered ad-free with normalized downloads.
    write(DIST / 'research/index.html', render_research_index(site, research_reports, stats_page))
    write(DIST / 'research/methodology/index.html', render_research_methodology(site))
    for report in research_reports:
        write(DIST / 'research' / report['slug'] / 'index.html', render_research_report(site, report))
        write_research_data(report)
    if stats_page:
        write(DIST / 'research' / stats_page['slug'] / 'index.html', render_stats_page(site, stats_page))
        write_stats_data(stats_page)

    about, privacy, cookies, terms, contact, disclaimer, methodology, corrections, recovery = build_legal_bodies(site, sources)
    write(DIST / 'about/index.html',   render_simple_page(site, 'About',          'Beat the Scam is a free UK consumer protection site. Learn who runs it, how it is funded, and how the AI scam checker works.',        about,   'about'))
    write(DIST / 'privacy/index.html', render_simple_page(site, 'Privacy Policy', 'How Beat the Scam uses Google Analytics, Google AdSense, and the Anthropic Claude API. Understand your data choices and cookie consent options.',          privacy, 'privacy'))
    write(DIST / 'cookies/index.html', render_simple_page(site, 'Cookie Policy',  'How Beat the Scam uses cookies for analytics, advertising, and consent preferences. Learn what is stored and how to manage your cookie settings.',                   cookies, 'cookies'))
    write(DIST / 'terms/index.html',   render_simple_page(site, 'Terms',          'Terms of use for Beat the Scam. Educational scam guidance only — not legal or financial advice. Read before relying on any content for important decisions.',                                 terms,   'terms'))
    write(DIST / 'contact/index.html', render_simple_page(site, 'Contact',        'Contact Beat the Scam for editorial corrections, privacy questions, or partnership enquiries. We aim to respond to all editorial requests promptly.',     contact, 'contact'))
    write(DIST / 'disclaimer/index.html', render_simple_page(site, 'Disclaimer',  'Beat the Scam disclaimer: the guides and AI scam checker are general consumer-awareness information only — not legal, financial, or professional advice.', disclaimer, 'disclaimer'))
    write(DIST / 'methodology/index.html', render_simple_page(site, 'How We Fact-Check', 'How Beat the Scam researches, drafts, gate-checks, human-reviews, and re-verifies every guide — the sources we check against and how corrections work.', methodology, 'methodology'))
    write(DIST / 'corrections/index.html', render_simple_page(site, 'Corrections', 'Material corrections to Beat the Scam guides, including what changed, when it changed, and how to request a review.', corrections, 'corrections'))
    write(DIST / 'recovery/index.html', render_simple_page(site, 'Scam Recovery Checklist', 'Act quickly after a scam: the UK steps for bank transfers, card payments, passwords, remote access, identity details, reporting and complaints.', recovery, 'recovery'))

    # Named author page — Alex Bacsa, cross-linked with CloudFintech /
    # TuningDigital / SalesTap via the Person.sameAs block in the page schema.
    author_html = render_author_page(site)
    author_rendered = bool(author_html)
    if author_html:
        write(DIST / 'author/index.html', author_html)

    not_found_html = make_base(
        '<section class="hero"><div class="wrap"><h1>Page not found</h1><p class="lead">The page may have moved or the address may be incorrect.</p><div class="hero-actions"><a class="btn btn-primary" href="/">Home</a><a class="btn btn-secondary" href="/guides/">Guides</a></div></div></section>',
        title=f'404 | {site["site_name"]}',
        description='Page not found.',
        canonical=site['domain'] + '/404.html',
        schema=page_schema(site, '404', 'Page not found.', site['domain'] + '/404.html'),
        site=site,
        robots='noindex,follow',
        ads_mode='none'
    )
    write(DIST / '404.html', not_found_html)
    write(DIST / 'CNAME', 'beatthescam.com')
    write(DIST / 'ads.txt', f'google.com, {site["adsense_client"].replace("ca-", "")}, DIRECT, f08c47fec0942fa0')

    # Search index powering the site-wide guide search on /guides/. Lean fields
    # only (title/description/category/keywords — no full body) so the browser
    # can fetch it cheaply for filter-as-you-type across every guide.
    search_items = []
    for post in posts:
        search_items.append({
            'title': post['title'], 'url': f'/guides/{post["slug"]}/',
            'description': post['description'], 'category': category_label(post['category']),
            'keywords': post.get('keywords', []),
        })
    write(DIST / 'search.json', json.dumps(search_items, ensure_ascii=False))

    # RSS — newest first so feed readers detect updates from the top item.
    # lastBuildDate + atom:link self-ref + isPermaLink GUIDs added 2026-06-15
    # (external audit P3): stronger update detection and stable item identity.
    rss_posts = sorted(posts, key=lambda p: p["date"], reverse=True)[:30]
    rss_items = []
    for post in rss_posts:
        rss_items.append(f'''
        <item>
          <title>{html.escape(post["title"])}</title>
          <link>{site["domain"]}/guides/{post["slug"]}/</link>
          <guid isPermaLink="true">{site["domain"]}/guides/{post["slug"]}/</guid>
          <pubDate>{datetime.strptime(post["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 +0000")}</pubDate>
          <description>{html.escape(post["description"])}</description>
        </item>''')
    # lastBuildDate = newest item's date (content-derived, not the build clock,
    # so a no-op rebuild doesn't churn the feed's freshness signal).
    # NEWEST CONTENT CHANGE, not newest publish date. `date` is when a guide was
    # first published and never moves, so an editorial correction left the feed
    # and every collection page claiming the site had not changed since the last
    # NEW guide — 186 of 186 records carried an `updated` later than their
    # `date`, which made the signal stale by construction (audit, 2026-07-31).
    # Still content-derived, so a no-op rebuild does not churn freshness.
    _newest_change = max(
        [(p.get("updated") or p.get("dateModified") or p["date"]) for p in posts],
        default="",
    )
    last_build = (datetime.strptime(_newest_change, "%Y-%m-%d")
                  .strftime("%a, %d %b %Y 00:00:00 +0000")) if _newest_change else ""
    rss = (
        '<?xml version="1.0" encoding="UTF-8" ?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f'<title>{html.escape(site["site_name"])}</title>'
        f'<link>{site["domain"]}</link>'
        f'<description>{html.escape(site["tagline"])}</description>'
        f'<lastBuildDate>{last_build}</lastBuildDate>'
        f'<atom:link href="{site["domain"]}/rss.xml" rel="self" type="application/rss+xml" />'
        f'{"".join(rss_items)}</channel></rss>'
    )
    write(DIST / 'rss.xml', rss)

    # Sitemap — lastmod reflects actual content dates, not the build timestamp
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    newest_post_date = max((p["date"] for p in posts), default=today)
    # Collection pages (the paginated /guides/ list, the feed) must move when a
    # guide is CORRECTED, not only when a new one is published — see the
    # lastBuildDate note above.
    newest_change_date = max(
        [(p.get("updated") or p.get("dateModified") or p["date"]) for p in posts],
        default=newest_post_date,
    )

    # Static pages change rarely — pin their sitemap lastmod to the date their
    # content last materially changed (bump STATIC_LASTMOD when you edit them),
    # NOT the build timestamp, so unchanged pages don't advertise false freshness
    # on every rebuild.
    STATIC_LASTMOD = "2026-06-23"
    # Pages materially edited today — kept separate from STATIC_LASTMOD so the
    # untouched legal pages don't advertise false freshness on every rebuild.
    RECENT_LASTMOD = "2026-07-18"
    static_url_lastmods = {
        '/':             newest_post_date,
        '/guides/':      newest_post_date,
        '/categories/':  newest_post_date,
        '/check/':       STATIC_LASTMOD,
        '/about/':       RECENT_LASTMOD,
        '/methodology/': RECENT_LASTMOD,
        '/corrections/': RECENT_LASTMOD,
        '/recovery/':    RECENT_LASTMOD,
        '/research/':    max((r['published'] for r in research_reports), default=RECENT_LASTMOD),
        '/research/methodology/': RECENT_LASTMOD,
        # /author/ only renders when site.json has an author_profile — keep the
        # sitemap consistent with what was actually written to dist/.
        **({'/author/': STATIC_LASTMOD} if author_rendered else {}),
        '/privacy/':    STATIC_LASTMOD,
        '/cookies/':    STATIC_LASTMOD,
        '/terms/':      STATIC_LASTMOD,
        '/disclaimer/': STATIC_LASTMOD,
        '/contact/':    STATIC_LASTMOD,
    }

    sitemap_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod in static_url_lastmods.items():
        freq = 'daily' if url == '/' else 'weekly'
        sitemap_lines.append(f'<url><loc>{site["domain"]}{url}</loc><lastmod>{lastmod}</lastmod><changefreq>{freq}</changefreq></url>')

    # Paginated /guides/ pages — each its own URL
    for page_num in range(2, total_pages + 1):
        sitemap_lines.append(
            f'<url><loc>{site["domain"]}/guides/page/{page_num}/</loc>'
            f'<lastmod>{newest_change_date}</lastmod><changefreq>weekly</changefreq></url>'
        )

    for p in posts:
        post_lastmod = p.get("updated") or p.get("dateModified") or p["date"]
        sitemap_lines.append(
            f'<url><loc>{site["domain"]}/guides/{p["slug"]}/</loc>'
            f'<lastmod>{post_lastmod}</lastmod><changefreq>monthly</changefreq></url>'
        )

    for report in research_reports:
        sitemap_lines.append(
            f'<url><loc>{site["domain"]}/research/{report["slug"]}/</loc>'
            f'<lastmod>{report["published"]}</lastmod><changefreq>monthly</changefreq></url>'
        )
    if stats_page:
        sitemap_lines.append(
            f'<url><loc>{site["domain"]}/research/{stats_page["slug"]}/</loc>'
            f'<lastmod>{stats_page["updated"]}</lastmod><changefreq>monthly</changefreq></url>'
        )

    for cat, items in categories.items():
        # Category lastmod = newest member's date (or build today if empty). For a
        # hub category the page also carries hand-authored prose, so an editorial
        # revision to the hub moves the page even when no member guide changed —
        # take the later of the two (operator review, 2026-07-27).
        cat_lastmod = max((p.get("updated") or p.get("dateModified") or p["date"] for p in items), default=today)
        hub_reviewed = str((category_hubs.get(cat) or {}).get("updated") or "").strip()
        if hub_reviewed:
            cat_lastmod = max(cat_lastmod, hub_reviewed)
        sitemap_lines.append(
            f'<url><loc>{site["domain"]}/categories/{slugify(cat)}/</loc>'
            f'<lastmod>{cat_lastmod}</lastmod><changefreq>weekly</changefreq></url>'
        )
    sitemap_lines.append('</urlset>')
    write(DIST / 'sitemap.xml', '\n'.join(sitemap_lines))

    # humans.txt — small editorial transparency signal
    humans_txt = (
        f"/* SITE */\n"
        f"Name: {site['site_name']}\n"
        f"Site: {site['domain']}\n"
        f"Contact: {site['contact_email']}\n"
        f"Coverage: UK consumer protection — scam alerts, verification guides, AI scam checker\n\n"
        f"/* PUBLISHER */\n"
        f"Name: {site['author']}\n"
        f"Notes: Independent educational publication. Not a law firm, bank, or regulator.\n"
        f"Methodology: see {site['domain']}/methodology/\n\n"
        f"Corrections: see {site['domain']}/corrections/\n\n"
        f"/* SOURCES */\n"
        f"{_b(sources, 'action-fraud')} ({_n(sources, 'action-fraud')}) — {_r(sources, 'action-fraud')['info_url']}\n"
        f"{_b(sources, 'police-scotland')} on {_r(sources, 'police-scotland')['phone']} "
        f"({_n(sources, 'police-scotland')}) — {_r(sources, 'police-scotland')['report_url']}\n"
        f"NCSC — {_r(sources, 'ncsc-sers')['info_url']}\n"
        f"Consumer advice by nation (Citizens Advice in England and Wales, Advice Direct Scotland, "
        f"Consumerline in Northern Ireland) — {_consumer_advice_url(sources)}\n"
        f"FCA Firm Checker — https://www.fca.org.uk/consumers/fca-firm-checker\n\n"
        f"/* LAST UPDATE */\n"
        f"{today}\n"
    )
    write(DIST / 'humans.txt', humans_txt)

    # Robots
    robots_content = (
        'User-agent: *\n'
        'Allow: /\n'
        'Disallow: /search/\n'
        'Disallow: /*.php$\n'
        'Disallow: /*?l=\n'
        'Disallow: /api/\n'
        'Disallow: /.netlify/\n'
        '\n'
        f'Sitemap: {site["domain"]}/sitemap.xml\n'
    )
    write(DIST / 'robots.txt', robots_content)

    # llms.txt — markdown index for LLM crawlers (ChatGPT, Claude,
    # Perplexity, Gemini etc.) per https://llmstxt.org/. Groups every
    # guide by category so retrieval systems see the topic structure
    # rather than a flat URL list. Clears the Semrush "Llms.txt not
    # found" notice and is a direct GEO/AEO signal — currently 0
    # AI Visibility / 2 cited pages, so there's real lift to be had.
    domain = site["domain"].rstrip("/")
    llms_lines = [
        "# Beat the Scam",
        "",
        "> Independent, plain-English UK consumer-protection publication covering scams, fraud, and checks to run before paying. Guides use AI-assisted drafting followed by editorial review and an automated accuracy gate.",
    ]
    if research_reports:
        llms_lines.extend(["", "## Research and datasets", ""])
        llms_lines.append(
            f'- [Research index]({domain}/research/): recurring search-discovery and AI-citation reports with downloadable normalized data'
        )
        llms_lines.append(
            f'- [Research methodology]({domain}/research/methodology/): collection cadence, source definitions, interpretation rules and limitations'
        )
        for report in research_reports:
            llms_lines.append(
                f'- [{report["title"]}]({domain}/research/{report["slug"]}/): {report["summary"]}'
            )
    if stats_page:
        llms_lines.append(
            f'- [{stats_page["title"]}]({domain}/research/{stats_page["slug"]}/): {stats_page["summary"]}'
        )
    llms_lines.extend(["", "## Categories", ""])
    sorted_cats = sorted(categories.keys(), key=lambda c: category_label(c).lower())
    for cat in sorted_cats:
        llms_lines.append(
            f'- [{category_label(cat)}]({domain}/categories/{slugify(cat)}/): {len(categories[cat])} guide(s)'
        )
    llms_lines.extend(["", "## Guides", ""])
    for cat in sorted_cats:
        items = sorted(categories[cat], key=lambda p: p["title"].lower())
        llms_lines.append(f"### {category_label(cat)}")
        llms_lines.append("")
        for p in items:
            desc = (p.get("description") or "").strip().replace("\n", " ")
            llms_lines.append(
                f'- [{p["title"]}]({domain}/guides/{p["slug"]}/): {desc}'
            )
        llms_lines.append("")
    llms_lines.extend([
        "## Optional",
        "",
        f"- [About]({domain}/about/): who runs the site",
        f"- [Methodology]({domain}/methodology/): how guides are researched, gate-checked, human-reviewed, and re-verified",
        f"- [Corrections]({domain}/corrections/): material editorial corrections and how to request one",
        f"- [Scam recovery checklist]({domain}/recovery/): payment, account, device, identity and reporting steps after a scam",
        f"- [Contact]({domain}/contact/): how to reach the publisher and editor",
        f"- [Privacy]({domain}/privacy/): data handling & cookies",
        f"- [Full corpus]({domain}/llms-full.txt): every guide's complete text in one file",
        "",
    ])
    write(DIST / "llms.txt", "\n".join(llms_lines))

    # llms-full.txt — the complete guide corpus inline (llmstxt.org
    # convention), so agentic fetchers can ingest every guide in a single
    # request instead of crawling 180+ pages. ~1 MB of plain markdown.
    full_lines = [
        "# Beat the Scam",
        "",
        "> Full text of every Beat the Scam guide — an independent, plain-English UK",
        "> consumer-protection publication. Index of guides: " + domain + "/llms.txt",
        "",
    ]
    for cat in sorted_cats:
        items = sorted(categories[cat], key=lambda p: p["title"].lower())
        for p in items:
            full_lines.append(f'## {p["title"]}')
            full_lines.append("")
            full_lines.append(f'URL: {domain}/guides/{p["slug"]}/')
            full_lines.append(f'Category: {category_label(cat)} · Updated: {p.get("updated") or p.get("date")}')
            full_lines.append("")
            # Canonicalise internal paths here too. This file writes the RAW
            # record text, so a consolidated slug survived here while the
            # rendered HTML page correctly pointed at the replacement — the same
            # content disagreeing across two surfaces, which is the class of bug
            # this release exists to remove (found in the release build,
            # 2026-07-30).
            desc = canonicalize_internal_guide_paths((p.get("description") or "").strip())
            if desc:
                full_lines.append(desc)
                full_lines.append("")
            for heading, body in p.get("sections", []):
                full_lines.append(f"### {heading}")
                full_lines.append("")
                full_lines.append(canonicalize_internal_guide_paths(body.strip()))
                full_lines.append("")
            faqs = p.get("faq") or []
            if faqs:
                full_lines.append("### Frequently asked questions")
                full_lines.append("")
                for q, a in faqs:
                    full_lines.append(f"**{q}**")
                    full_lines.append("")
                    full_lines.append(canonicalize_internal_guide_paths(a.strip()))
                    full_lines.append("")
    write(DIST / "llms-full.txt", "\n".join(full_lines))

    # IndexNow key — tells Bing/Yandex about new/updated pages instantly.
    # Key must match the filename. Generate once and keep stable.
    indexnow_key = "b3c8e1f2a94d7056"
    write(DIST / f'{indexnow_key}.txt', indexnow_key)

    # security.txt (RFC 9116) — tells security researchers how to disclose
    # vulnerabilities. Auto-regenerated every build so the Expires field
    # always stays under the 1-year RFC ceiling without manual upkeep.
    # Lives at /.well-known/security.txt per the spec.
    expires_iso = (datetime.now(timezone.utc) + timedelta(days=335)).strftime("%Y-%m-%dT00:00:00.000Z")
    security_txt = (
        f"# Security policy for {site['domain'].replace('https://','').replace('http://','')}\n"
        f"# In scope: beatthescam.com and its subdomains.\n"
        f"# If you've found a security vulnerability, please report it via the\n"
        f"# channels below. We aim to respond to all credible reports within 5\n"
        f"# working days. Thank you for helping keep readers safe.\n"
        f"\n"
        f"Contact: mailto:{site['security_email']}\n"
        f"Contact: {site['domain']}/contact/\n"
        f"Expires: {expires_iso}\n"
        f"Preferred-Languages: en\n"
        f"Canonical: {site['domain']}/.well-known/security.txt\n"
    )
    write(DIST / '.well-known' / 'security.txt', security_txt)

    # _redirects (Netlify)
    # Category slug 301s — auto-derived from CATEGORY_CANON.
    # Lives in dist/_redirects rather than netlify.toml because [[redirects]]
    # in toml weren't being applied at edge despite headers and the API
    # redirect from the same toml working correctly.
    # API function rewrites live here, NOT netlify.toml: new toml [[redirects]]
    # beyond the original /api/check-scam rule are not applied at the edge on
    # this site (same quirk as the category 301s). _redirects is the reliable
    # mechanism, and a 200 rewrite must precede any catch-all to win.
    # HOST CANONICALISATION — must come FIRST; Netlify takes the first match.
    #
    # beatthescam.co.uk is an ALIAS of this same Netlify site: it served the whole
    # corpus at HTTP 200 with a byte-identical etag, so every page existed twice
    # for Google and at least one .co.uk URL had already surfaced in search
    # (audit, 2026-07-31). Because it is an alias, _redirects reaches it — the
    # article 301s already fired there — so this is fixable in the build rather
    # than in DNS.
    #
    # A full-URL source is what scopes a rule to one hostname; a path-only rule
    # would loop on the canonical host. Both schemes and the www form are listed
    # because a rule only matches the exact scheme+host it names.
    redirect_lines = ["# Host canonicalisation (auto-generated from site.alternate_domains)"]
    canonical = site["domain"].rstrip("/")
    for alt in site.get("alternate_domains", []):
        alt = alt.strip().replace("https://", "").replace("http://", "").strip("/")
        if not alt:
            continue
        for host in (alt, f"www.{alt}"):
            for scheme in ("http", "https"):
                redirect_lines.append(
                    f"{scheme}://{host}/*    {canonical}/:splat    301!")
    redirect_lines.append("")

    # /index.html NORMALISATION. Netlify serves both /path/ and /path/index.html
    # as 200, so every directory page existed twice (audit, 2026-07-31). One rule
    # per directory depth present in dist/ — `:a` matches exactly one path
    # segment, so these cannot collapse a deeper URL onto a shallower one.
    redirect_lines.append("# Index-file normalisation (auto-generated)")
    redirect_lines.append("/index.html    /    301!")
    # Depth is DERIVED from what was actually rendered, so a new deeper page
    # (a nested research sub-page, say) is covered without editing this list.
    # +1 of headroom, because a rule for a depth that has no pages is inert
    # while a missing rule silently leaves a duplicate URL live.
    _rendered_depths = [
        len(f.relative_to(DIST).parts) - 1
        for f in DIST.rglob("index.html")
    ]
    _MAX_DIR_DEPTH = (max(_rendered_depths) if _rendered_depths else 0) + 1
    for depth in range(1, _MAX_DIR_DEPTH + 1):
        params = "/".join(f":seg{i}" for i in range(depth))
        redirect_lines.append(f"/{params}/index.html    /{params}/    301!")
    redirect_lines.append("")

    redirect_lines += [
        "# API function rewrites (auto-generated)",
        "/api/subscribe          /.netlify/functions/subscribe          200",
        "/api/confirm-subscribe  /.netlify/functions/confirm-subscribe  200",
        "/api/unsubscribe        /.netlify/functions/unsubscribe        200",
        "/api/csp-report         /.netlify/functions/csp-report         200",
        "",
        "# Category slug normalisation (auto-generated from CATEGORY_CANON)",
    ]
    seen = set()
    for old_label, new_slug in CATEGORY_CANON.items():
        old_slug = old_label.replace(" ", "-")
        if old_slug == new_slug or old_slug in seen:
            continue
        seen.add(old_slug)
        redirect_lines.append(f"/categories/{old_slug}    /categories/{new_slug}/    301!")
        redirect_lines.append(f"/categories/{old_slug}/*    /categories/{new_slug}/:splat    301!")

    # Article-level 301s (auto-generated from ARTICLE_REDIRECTS).
    # For each deleted slug, emit two rules (with + without trailing slash)
    # so Netlify catches both forms cleanly.
    redirect_lines.append("")
    redirect_lines.append("# Article 301s (static map + every `consolidated_into` record)")
    for old_slug, target in EFFECTIVE_REDIRECTS.items():
        if target.startswith("__CAT__:"):
            destination = f"/categories/{target[len('__CAT__:'):]}/"
        else:
            destination = f"/guides/{target}/"
        redirect_lines.append(f"/guides/{old_slug}    {destination}    301!")
        redirect_lines.append(f"/guides/{old_slug}/    {destination}    301!")

    write(DIST / '_redirects', "\n".join(redirect_lines) + "\n")

    print(f"Built {len(posts)} posts across {len(categories)} categories -> {DIST}")

if __name__ == "__main__":
    build()
