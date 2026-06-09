import hashlib
import html
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

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

# Article-level 301 redirects. Used when an article is deleted but its URL
# may have inbound links from Google's index, Search Console history, or
# external sites. The value is either:
#   - another article slug (the canonical replacement), or
#   - "__CAT__:<category-slug>" to redirect to a category landing page.
#
# Populated as part of the AdSense "Low value content" remediation on
# 2026-05-24: 51 short / duplicate articles were removed (the bimodal
# distribution of 49 articles <300 words alongside 155 articles >800 words
# was flagged by an AdSense reviewer). _redirects entries are emitted by
# build() so the deleted URLs still resolve via 301.
ARTICLE_REDIRECTS = {
    # ── Slug-collision artifacts (the "-2" duplicates) ──────────────────
    # Older builds auto-generated these "-2" URLs when two posts.json
    # entries shared a base slug. Deduplicating posts.json on 2026-05-24
    # stopped them being generated, so they 404'd — and Google had
    # discovered/indexed several (showed up as "Not found (404)" in Search
    # Console on 2026-05-28). Redirect each to its surviving canonical.
    "facebook-marketplace-scam-uk-guide-2":       "facebook-marketplace-scam-uk",
    "fake-online-pharmacy-uk-scam-2":             "fake-online-pharmacy-uk-scam",
    "is-temu-a-scam-uk-2":                        "is-temu-a-scam-uk",
    "concert-ticket-scam-uk-2":                   "concert-ticket-scam-uk",
    "forex-trading-scam-uk-2":                    "forex-trading-scam-uk",
    "evri-text-scam-uk-2":                        "evri-delivery-scam-guide",
    # ── Thin/duplicate articles removed in the AdSense remediation ──────
    "paypal-email-scam-signs":                    "__CAT__:payment",
    "facebook-marketplace-scam-uk-guide":         "facebook-marketplace-scam-uk",
    "facebook-marketplace-scam-signs":            "facebook-marketplace-scam-uk",
    "hmrc-tax-refund-scam-checklist":             "__CAT__:government",
    "gumtree-scam-uk":                            "__CAT__:marketplace",
    "parking-fine-scam-text-messages-uk":         "parking-fine-scam-text-uk",
    "bank-transfer-scam-warning-signs":           "__CAT__:payment",
    "crypto-investment-scam-checklist":           "__CAT__:crypto",
    # GSC 2026-06-04: flagged as Not found (404). The canonical live guide
    # on this exact topic is crypto-investment-scams-uk-protection — article
    # → article redirect preserves more SEO juice than article → category.
    "crypto-investment-scam-uk-guide":            "crypto-investment-scams-uk-protection",
    "phone-call-scam-red-flags":                  "__CAT__:phone",
    "romance-scam-slow-burn-patterns":            "__CAT__:dating",
    "job-scam-checklist-uk":                      "__CAT__:employment",
    "puppy-sale-scam-checklist":                  "__CAT__:shopping",
    "travel-booking-scam-checklist":              "__CAT__:travel",
    "ticket-resale-scam-checklist":               "__CAT__:shopping",
    "shein-scam-or-legit-uk":                     "__CAT__:website",
    "ebay-scam-buyer-protection-uk":              "__CAT__:marketplace",
    "evri-text-scam-uk":                          "__CAT__:sms",
    # royal-mail-text-scam-guide 404'd (no post at that slug); redirect to the live
    # royal-mail-text-scam-uk so the "royal mail parcel scams" demand lands somewhere real.
    "royal-mail-text-scam-guide":                 "royal-mail-text-scam-uk",
    # dpd-delivery-scam-text, yodel-scam-text-messages and
    # ups-delivery-scam-text-messages-uk were resurrected as full ~1,000-word
    # guides on 2026-06-05 — they were the site's highest-demand URLs (DPD alone
    # had 1,905 GSC impressions at pos 10.2) but the 2026-05-24 purge 301'd them
    # to a thin category page. Redirects removed so build() serves the real
    # guide pages again. See scripts/recover_courier_guides.py.
    "paypal-email-scam-uk":                       "__CAT__:payment",
    "invoice-scam-email-uk":                      "__CAT__:payment",
    "refund-scam-uk":                             "__CAT__:payment",
    "direct-debit-scam-uk":                       "__CAT__:payment",
    "hmrc-tax-refund-scam-awareness":             "__CAT__:government",
    "dvla-scam-email-awareness":                  "__CAT__:government",
    "nhs-covid-scam-message":                     "__CAT__:government",
    "forex-trading-scams-uk-protection-guide":    "__CAT__:crypto",
    "trading-signal-scam-uk":                     "__CAT__:crypto",
    "work-from-home-scams-uk":                    "__CAT__:employment",
    "romance-scam-signs-uk-dating":               "__CAT__:dating",
    "puppy-scam-uk":                              "__CAT__:marketplace",
    "ticket-scam-uk":                             "__CAT__:marketplace",
    "holiday-booking-scam-uk":                    "__CAT__:travel",
    # 2nd purge-recovery batch (2026-06-07, see recover_purged_pages_2.py):
    # amazon-scam-email-uk → redirected to its live twin (consolidates the demand);
    # amazon-phone-call-scam-uk / chargeback / gumtree / google-voice resurrected as full guides.
    "amazon-scam-email-uk":                       "amazon-order-scam-email-checklist",
    "amazon-refund-scam-uk":                      "__CAT__:payment",
    "google-voice-scam-uk":                       "__CAT__:tech",
    "apple-id-scam-email-uk":                     "__CAT__:tech",
    "whatsapp-family-scam-urgent-money-messages": "__CAT__:social",
    "instagram-scam-message-uk":                  "__CAT__:social",
    "snapchat-scam-account-awareness":            "__CAT__:social",
    "energy-bill-scam-uk":                        "__CAT__:utility",
    "credit-score-scam-uk":                       "__CAT__:finance",
}

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
    "marketplace": "Guides covering Facebook Marketplace, Gumtree, Vinted, and eBay scams targeting UK buyers and sellers. Spot fake payment fraud, advance fees, and collection scams.",
    "sms":         "Guides covering fake delivery texts, bank impersonation SMS, HMRC alerts, and smishing attacks. Learn to identify and report suspicious texts targeting UK phones.",
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
    "travel":      "Guides covering fake holiday listings, advance-fee travel fraud, and ticket scams targeting UK travellers. Learn to verify travel offers before paying a deposit.",
    "shopping":    "Guides covering fake online retailers, counterfeit goods, pet scams, and marketplace fraud. Learn to shop safely and spot fraudulent sellers in the UK.",
    "finance":     "Guides covering fake investment opportunities, pension fraud, clone firm scams, and financial impersonation targeting UK consumers. Learn to protect your savings.",
    "fraud":       "Guides covering recovery scams, impersonation fraud, and advance-fee tactics targeting UK consumers. Learn to recognise fraud patterns and report them correctly.",
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


def load_category_hubs(root: Path) -> dict:
    """Optional per-category pillar content (title/description/intro/sections/faq)
    keyed by canonical category slug. Turns a category page into a rankable hub
    that links down to its guides. Missing file/category → plain category page."""
    path = root / "content" / "category-hubs.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def affiliate_block(post: dict, affiliates: list) -> str:
    """Return an HTML affiliate card relevant to this post, or empty string."""
    if not affiliates:
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

    if not best_product or best_score == 0:
        return ""

    p = best_product
    return f'''
    <section class="sidebar-card affiliate-card">
      <p class="note" style="margin:0 0 .4rem;font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;font-weight:800;color:var(--muted)">Sponsored</p>
      <h3 style="margin:.15rem 0 .4rem">{html.escape(p["name"])}</h3>
      <p class="note">{html.escape(p["tagline"])}</p>
      <a class="btn btn-secondary" href="{html.escape(p["href"])}" rel="sponsored noopener noreferrer" target="_blank" style="width:100%;margin-top:.6rem;text-align:center">{html.escape(p["cta"])}</a>
    </section>
    '''

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower().strip()).strip("-")


# ─── SEO HELPERS ─────────────────────────────────────────────────────────────

# Populated in build() before any page is rendered so make_base() can inject
# the full category list into the footer without changing function signatures.
_FOOTER_CATS_HTML = ""

def seo_title(post_title: str, site_name: str, max_len: int = 60) -> str:
    """Return a <title>-safe string truncated to max_len chars.

    Appends ' | SiteName' suffix, then truncates the post_title portion at
    the nearest word boundary so the full string fits within max_len.
    """
    suffix = f" | {site_name}"
    available = max_len - len(suffix)
    if len(post_title) <= available:
        return post_title + suffix
    truncated = post_title[:available].rsplit(" ", 1)[0].rstrip(" :,-–")
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

    # 2) Word-boundary fallback, stripping dangling connector words
    truncated = desc[:max_len].rsplit(" ", 1)[0].rstrip(" .,;:")
    DANGLERS = {
        "to", "the", "a", "an", "of", "for", "with", "and", "or", "but",
        "in", "on", "at", "by", "from", "as", "is", "are", "was", "were",
        "be", "been", "this", "that", "these", "those", "their", "your", "our",
    }
    parts = truncated.split()
    while parts and parts[-1].lower() in DANGLERS:
        parts.pop()
    truncated = " ".join(parts).rstrip(" .,;:")
    if not truncated:
        return desc[:max_len].rstrip()
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
        body = _normalize_bullet_body(body)
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
    # json.dumps handles all special chars correctly, but if any string value
    # contains "</script>" it would prematurely close the <script> block and
    # break the JSON. Replace with the safe unicode escape <\/script>.
    serialised = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    serialised = serialised.replace("</script>", r"<\/script>").replace("<!--", r"<\!--")
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


def make_base(content: str, *, title: str, description: str, canonical: str, schema: str, site: dict,
              og_type: str = "website", robots: str = "index,follow", og_title: str = None,
              og_image: str = None, prev_url: str = None, next_url: str = None):
    og_image_url = og_image or abs_url(site, "/assets/og-image-v2.png")
    twitter_handle = site.get("twitter") or ""
    replacements = {
        "{{title}}":             html.escape(title),
        "{{description}}":       html.escape(description),
        "{{canonical}}":         canonical,
        "{{robots}}":            robots,
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
        "{{adsense_client}}":    site["adsense_client"],
        "{{ga4_id}}":            site["ga4_id"],
        "{{year}}":              str(datetime.utcnow().year),
        "{{footer_cats}}":       _FOOTER_CATS_HTML,
        "{{prev_next}}":         _prev_next_meta(prev_url, next_url),
        "{{verification_meta}}": _verification_meta(site),
    }
    page = BASE
    for key, value in replacements.items():
        page = page.replace(key, value)
    return page


# ─── SCHEMA ────────────────────────────────────────────────────────────────

def website_schema(site):
    return json_ld({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site["site_name"],
        "url": site["domain"],
        "description": site["tagline"],
        "publisher": {
            "@type": "Organization",
            "name": site["site_name"],
            "url": site["domain"],
            "logo": abs_url(site, "/assets/logo-mark.svg")
        },
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
        "logo": abs_url(site, "/assets/logo-mark.svg")
    })

def page_schema(site, title, description, url):
    return json_ld({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": url,
        "isPartOf": {"@type": "WebSite", "name": site["site_name"], "url": site["domain"]}
    })

def faq_schema(pairs):
    if not pairs:
        return ""
    # Skip any malformed entries — must be 2-element sequences with non-empty strings
    valid = [
        (str(q).strip(), str(a).strip())
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
        "publisher": {
            "@type": "Organization",
            "name": site["site_name"],
            "url": site["domain"],
            "logo": {"@type": "ImageObject", "url": abs_url(site, "/assets/logo-mark.svg")}
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "image": [image_url],
        "articleSection": post["category"],
        "keywords": ", ".join(post["keywords"]),
        "inLanguage": site.get("locale", "en_GB").replace("_", "-"),
        "isAccessibleForFree": True,
    }
    if modified and modified != published:
        data["reviewedBy"] = author
    return json_ld(data)


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
            "totalTime": "PT5M",
            "step": [
                {
                    "@type": "HowToStep",
                    "position": i + 1,
                    "name": f"Step {i + 1}",
                    "text": s[:500],
                }
                for i, s in enumerate(steps[:8])
            ],
        })
    return ""


# ─── COMPONENTS ────────────────────────────────────────────────────────────

def render_card(post):
    label = category_label(post["category"])
    searchable = (post["title"] + " " + post["description"] + " " + post["category"] + " " + " ".join(post["keywords"])).lower()
    return f'''
    <article class="card guide-card" data-searchable="{html.escape(searchable)}">
      <div class="eyebrow">{html.escape(label)}</div>
      <h3><a href="/guides/{post["slug"]}/">{html.escape(post["title"])}</a></h3>
      <p>{html.escape(post["description"])}</p>
      <p class="meta">Updated {post["date"]}</p>
    </article>
    '''


# ─── PAGE RENDERERS ────────────────────────────────────────────────────────

def render_home(site, posts, categories):
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
        ''')

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

    content = f'''
    <section class="hero">
      <div class="wrap hero-grid">
        <div class="hero-panel">
          <div class="kicker">UK Consumer Protection</div>
          <h1>Check scams. Protect your money.</h1>
          <p class="lead">Beat the Scam helps you review suspicious texts, emails, websites, calls, job offers, crypto pitches, and payment requests before money or data is lost.</p>
          <div class="hero-actions">
            <a class="btn btn-primary" href="/guides/">Browse guides</a>
            <a class="btn btn-secondary" href="/check/">Check a message</a>
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
        '<input id="pageSearch" type="search" placeholder="Filter guides on this page" aria-label="Filter guides">'
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
        {pagination_html}
      </div>
    </section>
    '''

    if page_num == 1:
        content += '''
    <script>
      (function() {{
        var params = new URLSearchParams(window.location.search);
        var input = document.getElementById('pageSearch');
        if (!input) return;
        var cards = Array.from(document.querySelectorAll('[data-searchable]'));
        function applyFilter(value) {{
          var q = (value || '').toLowerCase().trim();
          cards.forEach(function(card) {{ card.style.display = card.dataset.searchable.includes(q) ? '' : 'none'; }});
        }}
        input.addEventListener('input', function(e) {{ applyFilter(e.target.value); }});
        if (params.get('q')) {{ input.value = params.get('q'); applyFilter(input.value); }}
      }})();
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
    )


def render_guides_index(site, posts):
    """Backwards-compat: render only the first page (used by callers that
    expect a single HTML string). Full pagination is handled in build()."""
    total_pages = max(1, (len(posts) + GUIDES_PER_PAGE - 1) // GUIDES_PER_PAGE)
    return render_guides_index_page(site, posts[:GUIDES_PER_PAGE], 1, total_pages, posts)


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
        ''')
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
        site=site
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
        intro = hub.get("intro", "")
        secs = "".join(
            f'<section class="section"><div class="wrap"><h2>{html.escape(h)}</h2>{b}</div></section>'
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

    grid_heading = f"All {html.escape(label.lower())} guides" if hub else f"Latest {html.escape(label.lower())}"
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/categories/">Categories</a> / {html.escape(label)}</div>
        <h1>{html.escape(label)}</h1>
        <p class="lead">{html.escape(desc)}</p>
      </div>
    </section>
    {hub_body_html}
    <section class="section"><div class="wrap"><h2>{grid_heading}</h2><div class="grid-3">{"".join(render_card(p) for p in posts)}</div></div></section>
    {hub_faq_html}
    {related_cats_html}
    '''
    canonical = site['domain'] + f'/categories/{slug}/'
    item_pairs  = [(p["title"], site["domain"] + f"/guides/{p['slug']}/") for p in posts]
    breadcrumbs = [
        ("Home",          site["domain"] + "/"),
        ("Categories",    site["domain"] + "/categories/"),
        (label,           canonical),
    ]
    page_title = hub.get("title") if hub and hub.get("title") else label
    page_desc  = hub.get("description") if hub and hub.get("description") else desc
    schema = (
        page_schema(site, label, page_desc, canonical)
        + itemlist_schema(item_pairs, list_name=label)
        + breadcrumb_schema(breadcrumbs)
        + (faq_schema(hub_faq_pairs) if hub_faq_pairs else "")
    )
    return make_base(
        content,
        title=seo_title(page_title, site["site_name"]),
        description=seo_description(page_desc),
        canonical=canonical,
        schema=schema,
        site=site
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

    scored.sort(key=lambda x: (-x[0], x[1]["date"]), reverse=False)
    scored.sort(key=lambda x: -x[0])  # primary: score desc

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


def render_post(site, post, all_posts, affiliates=None):
    url   = site['domain'] + f'/guides/{post["slug"]}/'
    label = category_label(post["category"])
    mins  = reading_time(post)
    cat_slug = slugify(post["category"])

    published = post["date"]
    updated   = post.get("updated") or post.get("dateModified") or published
    updated_html = ""
    if updated and updated != published:
        updated_html = f' &middot; <time datetime="{html.escape(updated)}">Updated {html.escape(updated)}</time>'

    section_ids   = []
    section_parts = []
    for title, para in post['sections']:
        sid = slugify(title)
        section_ids.append((sid, title))
        para = _normalize_bullet_body(para)
        if para.strip().startswith("-"):
            lines = [l.strip().lstrip("- ") for l in para.strip().splitlines() if l.strip().lstrip("- ")]
            inner = "".join(f"<li>{html.escape(l)}</li>" for l in lines)
            section_parts.append(f'<h2 id="{sid}">{html.escape(title)}</h2><ul>{inner}</ul>')
        else:
            # Split long blob paragraphs into ≤100-word chunks at sentence
            # boundaries — clears Semrush "paragraphs too long" (157 pages
            # in the 2026-05-30 audit) and reads better on mobile.
            paragraphs = split_into_paragraphs(para)
            paragraphs_html = "".join(f'<p>{html.escape(p)}</p>' for p in paragraphs)
            section_parts.append(f'<h2 id="{sid}">{html.escape(title)}</h2>{paragraphs_html}')

    toc      = "".join(f'<li><a href="#{sid}">{html.escape(t)}</a></li>' for sid, t in section_ids)
    faq_html = "".join(f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q, a in post['faq'])
    badges   = "".join(f'<span class="badge">{html.escape(k)}</span>' for k in post['keywords'])
    related  = "".join(
        f'<a href="/guides/{p["slug"]}/">{html.escape(p["title"])}<span class="meta">{html.escape(category_label(p["category"]))} &middot; {p["date"]}</span></a>'
        for p in related_posts(all_posts, post)
    )

    # Named byline backed by a real Person — Alex Bacsa, founder & editor.
    # Cross-publication identity (CloudFintech, TuningDigital, SalesTap) is
    # asserted via the Person.sameAs array in article_schema() above.
    author_url = site.get("editor_url") or "/about/"
    byline = f'<a href="{html.escape(author_url)}" rel="author">{html.escape(site["author"])}</a>'

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
        <div class="badge-row">{badges}</div>
        <div class="notice"><strong>Key rule:</strong> verify through an official route you opened yourself, not the link, number, app, or payment details supplied by the suspicious message.</div>
        <div class="toc"><strong>On this page</strong><ol>{toc}</ol></div>
        {"".join(section_parts)}
        <h2>Frequently asked questions</h2>
        <div class="faq">{faq_html}</div>
        <div class="notice" style="margin-top:2rem">
          <strong>Think you&#8217;ve spotted a scam?</strong>
          Use the <a href="/check/">AI scam checker</a> for an instant analysis, or report it to
          <a href="https://www.reportfraud.police.uk" rel="noopener noreferrer" target="_blank">Action Fraud</a>.
        </div>
        <p class="meta" style="margin-top:1.4rem">Reviewed against current UK reporting guidance from <a href="https://www.actionfraud.police.uk/" rel="noopener" target="_blank">Action Fraud</a>, the <a href="https://www.ncsc.gov.uk/" rel="noopener" target="_blank">National Cyber Security Centre</a>, and <a href="https://www.citizensadvice.org.uk/consumer/scams/" rel="noopener" target="_blank">Citizens Advice</a>. Last reviewed {html.escape(updated or published)}. Read about <a href="/about/">how Beat the Scam writes guides</a>.</p>
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
          <ul class="list-clean">
            <li><a href="https://www.reportfraud.police.uk" rel="noopener noreferrer" target="_blank">Action Fraud (UK)</a></li>
            <li><a href="https://www.ncsc.gov.uk/collection/phishing-scams" rel="noopener noreferrer" target="_blank">NCSC &#8212; report phishing</a></li>
            <li><a href="https://www.citizensadvice.org.uk/consumer/scams/reporting-a-scam/" rel="noopener noreferrer" target="_blank">Citizens Advice</a></li>
          </ul>
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
    )
    return make_base(
        content,
        title=seo_title(post["title"], site["site_name"]),
        og_title=post['title'],
        description=pick_description(post),
        canonical=url,
        schema=schema,
        site=site,
        og_type='article',
        og_image=og_image_url,
    )


def render_check_page(site):
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
            <p class="note" style="margin-top:.75rem">Your message is sent to Claude AI for analysis and is not stored by Beat the Scam. Do not include passwords or full bank account numbers.</p>
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
          contact your bank immediately and report to
          <a href="https://www.reportfraud.police.uk" rel="noopener noreferrer" target="_blank">Action Fraud</a>.
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
        })
        .catch(function() {
          renderError();
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
        var a = el("a", {"href": "https://www.reportfraud.police.uk", "rel": "noopener noreferrer", "target": "_blank"}, "report directly to the Police");
        p.appendChild(a);
        resultContent.textContent = "";
        resultContent.appendChild(p);
        resultContent.hidden = false;
      }
    })();
    </script>
    '''

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
    )


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
    return make_base(content, title=f'{title} | {site["site_name"]}', description=description, canonical=site['domain'] + f'/{slug}/', schema=page_schema(site, title, description, site['domain'] + f'/{slug}/'), site=site)


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
    )


def build_legal_bodies(site):
    about = f'''
    <p><strong>{html.escape(site["site_name"])}</strong> is a consumer-protection content site focused on helping UK residents recognise scam patterns before they send money, share credentials, or install malicious software.</p>

    <div class="author-card" style="margin:1.5rem 0;padding:1.2rem;border:1px solid var(--line);border-radius:14px;background:#fafafa">
      <p style="margin:0 0 .35rem 0"><strong>Who runs this site</strong></p>
      <p style="margin:0 0 .5rem 0;font-size:.95rem;color:#555">{html.escape(site["site_name"])} is founded and edited by <a href="/author/"><strong>{html.escape(site["author"])}</strong></a>, an independent UK-based publisher who also runs <a href="https://cloudfintech.ai" rel="noopener noreferrer" target="_blank">CloudFintech</a> (fintech &amp; banking technology), <a href="https://tuningdigital.com" rel="noopener noreferrer" target="_blank">Tuning Digital</a> (AI &amp; SaaS productivity tools), and <a href="https://salestap.com" rel="noopener noreferrer" target="_blank">SalesTap</a> (B2B sales). He uses AI tooling to surface scam patterns and translate official UK guidance into plain-English checks.</p>
      <p style="margin:0;font-size:.95rem;color:#555">He is not a journalist, lawyer, regulator, banker, or accredited consumer-affairs professional. This is an educational publication &mdash; every recommendation on the site directs you to the official UK authority that owns that decision.</p>
    </div>

    <p>The editorial model is simple: fast checks, plain-English explanations, and practical actions. The site is not a law firm, bank, or regulator. It is a free educational publication designed to reduce avoidable losses.</p>

    <div class="tablelike">
      <div class="table-row"><strong>Editorial focus</strong><span>Scam alerts, payment risk, impersonation patterns, delivery fraud, marketplace abuse, crypto scams, and recovery scams.</span></div>
      <div class="table-row"><strong>Audience</strong><span>UK residents who have received a suspicious message, are considering an unfamiliar purchase, or want to understand current fraud tactics.</span></div>
      <div class="table-row"><strong>How guides are written</strong><span>Each guide targets a specific scam type and explains what to verify, what to avoid, and what to do if you have already interacted.</span></div>
      <div class="table-row"><strong>AI scam checker</strong><span>A free tool that analyses suspicious messages and gives a plain-English verdict with recommended actions.</span></div>
      <div class="table-row"><strong>Commercial model</strong><span>Advertising-supported using Google AdSense, with scope for consumer-safety partnerships.</span></div>
    </div>

    <h2>How content is researched and produced</h2>
    <p>Each guide on this site goes through the same process: pick a specific scam type or pattern that is currently active in the UK, draft the content using AI assistance against a strict editorial template, then verify reporting routes and recommended actions against current sources before publishing.</p>
    <p>The drafting step uses Anthropic&#8217;s Claude API. The model is given a structured prompt covering the scam type, target audience, and required sections (what the scam looks like, warning signs, step-by-step pattern, verification, recovery actions, reporting routes). It is not asked to invent statistics, predict outcomes, or generate fake quotes. The output is then checked for accuracy and corrected where needed.</p>
    <p>Verification draws on UK-specific public sources, including:</p>
    <ul>
      <li><a href="https://www.actionfraud.police.uk/" rel="noopener noreferrer" target="_blank">Action Fraud</a> &mdash; the UK&#8217;s national reporting centre for fraud and cybercrime</li>
      <li><a href="https://www.ncsc.gov.uk/" rel="noopener noreferrer" target="_blank">National Cyber Security Centre (NCSC)</a> &mdash; for phishing reporting routes and current threat patterns</li>
      <li><a href="https://www.citizensadvice.org.uk/" rel="noopener noreferrer" target="_blank">Citizens Advice</a> &mdash; consumer protection guidance and helpline routes</li>
      <li><a href="https://www.fca.org.uk/scamsmart" rel="noopener noreferrer" target="_blank">FCA ScamSmart</a> &mdash; for investment and financial services scams</li>
      <li><a href="https://takefive-stopfraud.org.uk/" rel="noopener noreferrer" target="_blank">Take Five</a> &mdash; UK banking sector consumer fraud campaign</li>
      <li>Government UK pages for HMRC, DVLA, TV Licensing, and other public bodies commonly impersonated</li>
    </ul>

    <h2>Editorial standards</h2>
    <p>Content is written to be understandable under pressure. That means short sections, clear headings, and advice that directs readers towards independent verification through official channels &mdash; never through links, numbers, or payment details supplied by a suspicious message.</p>
    <p>Where the site recommends a reporting route, that route has been checked against the current public guidance from the relevant UK authority. Where the site cites a phone number or web address, it has been verified against the official source.</p>
    <p>If a guide contains an error, email <a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a> with the page URL and the issue. Corrections are made promptly.</p>

    <h2>About the AI scam checker</h2>
    <p>The free scam checker on this site sends the suspicious message text you paste to Anthropic&#8217;s Claude API for analysis. The text is processed in real time to produce a verdict, list of red flags, and recommended actions &mdash; then discarded. Beat the Scam does not store the text, your IP address, or any identifying data linked to your submission.</p>
    <p>For your own safety, do not paste full passwords, full bank account numbers, or other sensitive credentials into the checker. The tool is designed to analyse the suspicious content itself (the message, link, or scam pattern), not your private credentials.</p>
    <p>The checker&#8217;s output is educational. It is not a definitive fraud determination. If you are unsure about a real-world payment or account access decision, contact your bank&#8217;s fraud team using the number on the back of your card.</p>

    <h2>Contact</h2>
    <p>Editorial contact and correction requests: <a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a></p>

    <p class="note" style="margin-top:2rem;color:#666;font-size:.9rem">Last reviewed: May 2026. The site is reviewed periodically and updated as scam patterns and reporting routes change.</p>
    '''

    privacy = f'''
    <p>This Privacy Policy explains how {html.escape(site["site_name"])} uses analytics, advertising, and website technologies when you browse the site.</p>
    <h2>What information we collect</h2>
    <p>The site does not offer user accounts, comments, or direct purchases. Standard server logs may record technical data such as browser type, device type, and approximate location.</p>
    <h2>AI scam checker</h2>
    <p>When you use the AI scam checker, the text you submit is sent to Anthropic&#8217;s Claude API for analysis. This text is not stored by Beat the Scam. Do not include full passwords or bank account numbers in checker submissions.</p>
    <h2>Google Analytics</h2>
    <p>The site uses Google Analytics 4. Analytics cookies are only enabled after consent where required.</p>
    <h2>Advertising</h2>
    <p>The site uses Google AdSense. If advertising is active, Google and its partners may use cookies subject to your consent choices.</p>
    <h2>Cookie choices</h2>
    <p>A cookie banner allows you to accept or reject non-essential cookies. Your preference is stored locally in your browser.</p>
    <h2>Your rights</h2>
    <p>If you are in the UK or EEA you may have rights relating to your personal data. Contact us at <a href="mailto:{site["privacy_email"]}">{site["privacy_email"]}</a>.</p>
    '''

    cookies = f'''
    <p>This Cookie Policy explains what cookies and similar technologies may be used on {html.escape(site["site_name"])}.</p>
    <h2>Essential storage</h2>
    <p>The site stores a small preference in your browser to remember whether you accepted or rejected non-essential cookies.</p>
    <h2>Analytics cookies</h2>
    <p>If you accept analytics cookies, Google Analytics 4 may collect information about page views, device type, and interaction patterns.</p>
    <h2>Advertising cookies</h2>
    <p>If advertising is active and you consent, Google AdSense may use cookies to support ad delivery and measurement.</p>
    <h2>How to manage cookies</h2>
    <p>Change browser cookie settings at any time, or use the Cookie settings link in the footer to reopen the consent banner.</p>
    <h2>Contact</h2>
    <p>Cookie and privacy questions: <a href="mailto:{site["privacy_email"]}">{site["privacy_email"]}</a>.</p>
    '''

    # Bump TERMS_LAST_UPDATED when materially revising the Terms text below.
    # The date is shown to users at the top of /terms/ as the legal effective date.
    TERMS_LAST_UPDATED = "4 June 2026"
    terms = f'''
    <p class="note" style="color:#666;font-size:.95rem"><strong>Last updated:</strong> {TERMS_LAST_UPDATED}</p>

    <p>These Terms set out the rules for using <strong>beatthescam.com</strong> ("the Site"). By using the Site you agree to them. If you do not agree, please do not use the Site.</p>

    <h2>About this site</h2>
    <p>Beat the Scam publishes plain-English guides about scams and fraud affecting UK consumers, and offers a free AI scam checker. The Site is operated by SideRight Apps. Editorial decisions are made by Alex Bacsa, Founder &amp; Editor.</p>

    <h2>Educational purpose &mdash; not professional advice</h2>
    <p>Everything published here is general educational information. It is <strong>not</strong> legal, financial, investment, tax, medical, cybersecurity, or regulatory advice, and reading it does not create an advisor&ndash;client relationship.</p>
    <p>Scam tactics change rapidly. No article can guarantee that a specific message, listing, website or interaction is safe or fraudulent. If anything you read here is material to your circumstances, verify it through official UK channels (Action Fraud, the FCA Register, Companies House, Citizens Advice, your bank&#8217;s published fraud line) or seek qualified professional advice.</p>

    <h2>The AI scam checker</h2>
    <p>The AI scam checker is an educational tool that returns an automated plain-English assessment. Its output is <strong>not</strong> a definitive fraud determination and we make no warranty that it will identify every scam or that flagged messages are necessarily fraudulent.</p>
    <p>Do not rely on the checker alone for high-stakes decisions. If you have already sent money, shared bank details, or shared one-time codes, contact your bank immediately and report the incident to Action Fraud (<a href="https://www.actionfraud.police.uk/" rel="noopener noreferrer" target="_blank">actionfraud.police.uk</a> or 0300 123 2040).</p>

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

    <h2>Advertising and affiliate disclosure</h2>
    <p>The Site is funded by display advertising (currently Google AdSense) and by affiliate commissions on a small number of third-party products (such as credit-file monitoring and identity-protection services). When you click an affiliate link and complete a purchase, we may receive a small commission at no extra cost to you.</p>
    <p>Affiliate placements never change the editorial position of any guide. We only recommend products we would suggest a friend use, and we mark affiliate links with <code>rel="sponsored"</code> as required by the UK Advertising Standards Authority CAP Code and by Google&#8217;s quality guidelines. If you would like us to remove a specific affiliate placement, write to us at the contact address below.</p>

    <h2>External links</h2>
    <p>The Site links to third-party services and official resources (government sites, regulators, banks, news outlets). Those sites operate under their own terms and privacy policies and we have no control over their content, accuracy, or availability.</p>

    <h2>Privacy and cookies</h2>
    <p>How we handle personal data and cookies is explained in our <a href="/privacy/">Privacy Policy</a> and <a href="/cookies/">Cookie Policy</a>. Use of the Site is subject to those documents as well as these Terms.</p>

    <h2>Limitation of liability</h2>
    <p>To the maximum extent permitted by law, Beat the Scam, SideRight Apps, and the editorial team are not liable for any loss, damage, or expense arising from your use of the Site or your reliance on its content &mdash; including the AI scam checker. We make no warranty that the Site will be uninterrupted, error-free, or secure.</p>
    <p><strong>Nothing in these Terms limits or excludes our liability for:</strong> (a) death or personal injury caused by our negligence; (b) fraud or fraudulent misrepresentation; (c) any other liability that cannot lawfully be limited or excluded under English, Scots, or Northern Ireland law &mdash; including your statutory rights as a consumer.</p>

    <h2>Changes to these Terms</h2>
    <p>We may update these Terms from time to time to reflect changes to the Site, to the law, or to industry practice. The &#8220;Last updated&#8221; date at the top of this page shows when the current version took effect. Continuing to use the Site after a change means you accept the updated Terms.</p>

    <h2>Governing law and jurisdiction</h2>
    <p>These Terms are governed by the laws of <strong>England and Wales</strong>. If you are resident in <strong>Scotland</strong>, these Terms are governed by <strong>Scots law</strong> and the Scottish courts have non-exclusive jurisdiction over any dispute arising from them. If you are resident in <strong>Northern Ireland</strong>, the courts of Northern Ireland have non-exclusive jurisdiction. None of this affects your mandatory statutory consumer rights in your country of residence.</p>

    <h2>Contact</h2>
    <p>For questions about these Terms, copyright, or other legal matters, email <a href="mailto:{site["legal_email"]}">{site["legal_email"]}</a>. For corrections to a guide, email <a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a> with the page URL and the change requested. For privacy and data-protection requests, see the <a href="/privacy/">Privacy Policy</a>.</p>
    '''

    contact = f'''
    <p>For editorial contact, corrections, or partnership enquiries, email <a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a>. For privacy, legal, or security matters, please use the dedicated addresses below.</p>
    <div class="tablelike">
      <div class="table-row"><strong>Editorial &amp; corrections</strong><span><a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a> &mdash; send the page URL and the correction you want reviewed.</span></div>
      <div class="table-row"><strong>Advertising or partnerships</strong><span><a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a> &mdash; include the business name, proposal, and relevant website.</span></div>
      <div class="table-row"><strong>Privacy &amp; data protection</strong><span><a href="mailto:{site["privacy_email"]}">{site["privacy_email"]}</a> &mdash; reference &#8220;Privacy request&#8221; in the subject line.</span></div>
      <div class="table-row"><strong>Legal &amp; copyright</strong><span><a href="mailto:{site["legal_email"]}">{site["legal_email"]}</a> &mdash; Terms, intellectual property, and reproduction requests.</span></div>
      <div class="table-row"><strong>Security disclosure</strong><span><a href="mailto:{site["security_email"]}">{site["security_email"]}</a> &mdash; see also our <a href="/.well-known/security.txt">security.txt</a>.</span></div>
    </div>
    <p class="note" style="margin-top:1.5rem">To report a scam to UK authorities directly, use <a href="https://www.reportfraud.police.uk/" rel="noopener noreferrer" target="_blank">Action Fraud</a> or forward suspicious texts to <strong>7726</strong> (free on all UK networks).</p>
    '''

    return about, privacy, cookies, terms, contact


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
        out.append(unique[0])
        for idx, p in enumerate(unique[1:], start=2):
            new_slug = f"{slug}-{idx}"
            p = dict(p)
            p["slug"] = new_slug
            out.append(p)
            print(f"  slug-collision: '{slug}' → kept newest, renamed older to '{new_slug}'")

    return sorted(out, key=lambda p: p["date"], reverse=True)


# Backwards-compat alias used by any external caller / test.
deduplicate_posts = disambiguate_slugs


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


def build_internal_link_map(posts):
    """Build a phrase → guide-URL map from each post's keywords.

    Filters keywords to phrases that are 2+ words long, lowercase, not
    stop-listed, not duplicated. First post wins on duplicates (since
    posts are deduped + date-sorted newest-first, this gives links to
    the freshest authoritative post on a phrase).
    """
    link_map: dict = {}
    for post in posts:
        slug = post.get("slug")
        if not slug:
            continue
        url = f"/guides/{slug}/"
        for kw in post.get("keywords", []):
            phrase = (kw or "").lower().strip()
            if not phrase or len(phrase.split()) < 2:
                continue
            if phrase in _INTERNAL_LINK_STOPWORDS:
                continue
            if phrase in link_map:
                continue
            link_map[phrase] = url
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
                if _pos_inside_anchor(text, m.start()):
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

    def replace_match(m):
        path = m.group(1)
        slug = path.strip("/").split("/")[-1]
        link_text = slug_titles.get(slug) or slug.replace("-", " ")
        return f'<a href="{path}">{html.escape(link_text)}</a>'

    out = []
    for kind, text in zones:
        if kind == "excluded":
            out.append(text)
        else:
            out.append(_BARE_PATH_RE.sub(replace_match, text))
    return "".join(out)


# ─── PHONE LINKIFY ─────────────────────────────────────────────────────────

# Match UK helpline patterns: 0300/0800/0808/0345 prefix, then space-separated digits.
_PHONE_RE = re.compile(r"\b(0(?:300|800|808|345|371|370|345)\s\d{3}\s\d{3,4})\b")


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

    def replace(m):
        number = m.group(1)
        tel = "+44" + number.replace(" ", "")[1:]
        return f'<a href="tel:{tel}">{number}</a>'

    out = []
    for kind, text in zones:
        out.append(text if kind == "excluded" else _PHONE_RE.sub(replace, text))
    return "".join(out)


# ─── MAIN BUILD ────────────────────────────────────────────────────────────

def build():
    site     = read_json(ROOT / 'content/site.json')
    raw_posts = read_json(ROOT / 'content/posts.json')

    affiliates = load_affiliates(ROOT)
    category_hubs = load_category_hubs(ROOT)

    # Normalise category names
    for post in raw_posts:
        post["category"] = normalize_category(post["category"])

    # Disambiguate slug collisions — preserve all posts, never silently drop
    posts = disambiguate_slugs(raw_posts)

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
    shutil.copytree(ROOT / 'assets', DIST / 'assets',
                    ignore=shutil.ignore_patterns('audio', '*.mp3', '*.wav', '*.aac'))

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

    write(DIST / 'index.html',       render_home(site, posts, categories))
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

        html_out = render_post(site, post, posts, affiliates)
        html_out = linkify_bare_paths(html_out, slug_titles)
        html_out = apply_internal_links(html_out, post['slug'], link_map)
        html_out = linkify_phones(html_out)
        write(DIST / 'guides' / post['slug'] / 'index.html', html_out)

    if not _PIL_OK:
        print("  Pillow not installed — per-post OG images skipped (using site default).")
    else:
        print(f"  Generated {og_gen_count} per-post OG images in /assets/og/")

    write(DIST / 'check/index.html', render_check_page(site))

    about, privacy, cookies, terms, contact = build_legal_bodies(site)
    write(DIST / 'about/index.html',   render_simple_page(site, 'About',          'Beat the Scam is a free UK consumer protection site. Learn how guides are researched, who writes them, and how the AI scam checker works.',        about,   'about'))
    write(DIST / 'privacy/index.html', render_simple_page(site, 'Privacy Policy', 'How Beat the Scam uses Google Analytics, Google AdSense, and the Anthropic Claude API. Understand your data choices and cookie consent options.',          privacy, 'privacy'))
    write(DIST / 'cookies/index.html', render_simple_page(site, 'Cookie Policy',  'How Beat the Scam uses cookies for analytics, advertising, and consent preferences. Learn what is stored and how to manage your cookie settings.',                   cookies, 'cookies'))
    write(DIST / 'terms/index.html',   render_simple_page(site, 'Terms',          'Terms of use for Beat the Scam. Educational scam guidance only — not legal or financial advice. Read before relying on any content for important decisions.',                                 terms,   'terms'))
    write(DIST / 'contact/index.html', render_simple_page(site, 'Contact',        'Contact Beat the Scam for editorial corrections, privacy questions, or partnership enquiries. We aim to respond to all editorial requests promptly.',     contact, 'contact'))

    # Named author page — Alex Bacsa, cross-linked with CloudFintech /
    # TuningDigital / SalesTap via the Person.sameAs block in the page schema.
    author_html = render_author_page(site)
    if author_html:
        write(DIST / 'author/index.html', author_html)

    not_found_html = make_base(
        '<section class="hero"><div class="wrap"><h1>Page not found</h1><p class="lead">The page may have moved or the address may be incorrect.</p><div class="hero-actions"><a class="btn btn-primary" href="/">Home</a><a class="btn btn-secondary" href="/guides/">Guides</a></div></div></section>',
        title=f'404 | {site["site_name"]}',
        description='Page not found.',
        canonical=site['domain'] + '/404.html',
        schema=page_schema(site, '404', 'Page not found.', site['domain'] + '/404.html'),
        site=site,
        robots='noindex,follow'
    )
    write(DIST / '404.html', not_found_html)
    write(DIST / 'CNAME', 'beatthescam.com')
    write(DIST / 'ads.txt', f'google.com, {site["adsense_client"].replace("ca-", "")}, DIRECT, f08c47fec0942fa0')

    # Search index
    search_items = []
    for post in posts:
        blob = ' '.join([post['title'], post['description'], post['category'],
                         *post['keywords'], *[s[0] + ' ' + s[1] for s in post['sections']]])
        search_items.append({
            'title': post['title'], 'url': f'/guides/{post["slug"]}/',
            'description': post['description'], 'category': category_label(post['category']),
            'content': blob
        })
    write(DIST / 'search.json', json.dumps(search_items, indent=2))

    # RSS
    rss_items = []
    for post in posts[:30]:
        rss_items.append(f'''
        <item>
          <title>{html.escape(post["title"])}</title>
          <link>{site["domain"]}/guides/{post["slug"]}/</link>
          <guid>{site["domain"]}/guides/{post["slug"]}/</guid>
          <pubDate>{datetime.strptime(post["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 +0000")}</pubDate>
          <description>{html.escape(post["description"])}</description>
        </item>''')
    rss = f'<?xml version="1.0" encoding="UTF-8" ?>\n<rss version="2.0"><channel><title>{html.escape(site["site_name"])}</title><link>{site["domain"]}</link><description>{html.escape(site["tagline"])}</description>{"".join(rss_items)}</channel></rss>'
    write(DIST / 'rss.xml', rss)

    # Sitemap — lastmod reflects actual content dates, not the build timestamp
    today = datetime.utcnow().strftime("%Y-%m-%d")
    newest_post_date = max((p["date"] for p in posts), default=today)

    static_url_lastmods = {
        '/':            newest_post_date,
        '/guides/':     newest_post_date,
        '/categories/': newest_post_date,
        '/check/':      today,
        '/about/':      today,
        '/author/':     today,
        '/privacy/':    today,
        '/cookies/':    today,
        '/terms/':      today,
        '/contact/':    today,
    }

    sitemap_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lastmod in static_url_lastmods.items():
        freq = 'daily' if url == '/' else 'weekly'
        sitemap_lines.append(f'<url><loc>{site["domain"]}{url}</loc><lastmod>{lastmod}</lastmod><changefreq>{freq}</changefreq></url>')

    # Paginated /guides/ pages — each its own URL
    for page_num in range(2, total_pages + 1):
        sitemap_lines.append(
            f'<url><loc>{site["domain"]}/guides/page/{page_num}/</loc>'
            f'<lastmod>{newest_post_date}</lastmod><changefreq>weekly</changefreq></url>'
        )

    for p in posts:
        post_lastmod = p.get("updated") or p.get("dateModified") or p["date"]
        sitemap_lines.append(
            f'<url><loc>{site["domain"]}/guides/{p["slug"]}/</loc>'
            f'<lastmod>{post_lastmod}</lastmod><changefreq>monthly</changefreq></url>'
        )

    for cat, items in categories.items():
        # Category lastmod = newest member's date (or build today if empty)
        cat_lastmod = max((p.get("updated") or p.get("dateModified") or p["date"] for p in items), default=today)
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
        f"Methodology: see {site['domain']}/about/\n\n"
        f"/* SOURCES */\n"
        f"Action Fraud — https://www.actionfraud.police.uk/\n"
        f"NCSC — https://www.ncsc.gov.uk/\n"
        f"Citizens Advice — https://www.citizensadvice.org.uk/consumer/scams/\n"
        f"FCA ScamSmart — https://www.fca.org.uk/scamsmart\n\n"
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
        "# Beat The Scam",
        "",
        "> Plain-English UK consumer-protection guides covering scams, fraud, and how to spot them before paying. New guide published daily by an editorial team focused on UK consumers.",
        "",
        "## Categories",
        "",
    ]
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
        f"- [About]({domain}/about/): site & methodology",
        f"- [Contact]({domain}/contact/): how to reach the editorial team",
        f"- [Privacy]({domain}/privacy/): data handling & cookies",
        "",
    ])
    write(DIST / "llms.txt", "\n".join(llms_lines))

    # IndexNow key — tells Bing/Yandex about new/updated pages instantly.
    # Key must match the filename. Generate once and keep stable.
    indexnow_key = "b3c8e1f2a94d7056"
    write(DIST / f'{indexnow_key}.txt', indexnow_key)

    # security.txt (RFC 9116) — tells security researchers how to disclose
    # vulnerabilities. Auto-regenerated every build so the Expires field
    # always stays under the 1-year RFC ceiling without manual upkeep.
    # Lives at /.well-known/security.txt per the spec.
    expires_iso = (datetime.utcnow() + timedelta(days=335)).strftime("%Y-%m-%dT00:00:00.000Z")
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
    redirect_lines = [
        "# API function rewrites (auto-generated)",
        "/api/subscribe      /.netlify/functions/subscribe      200",
        "/api/unsubscribe    /.netlify/functions/unsubscribe    200",
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
    redirect_lines.append("# Article 301s (auto-generated from ARTICLE_REDIRECTS)")
    for old_slug, target in ARTICLE_REDIRECTS.items():
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
