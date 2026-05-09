import html
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
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

def seo_description(desc: str, max_len: int = 155) -> str:
    """Truncate a meta description to max_len chars at a word boundary."""
    if len(desc) <= max_len:
        return desc
    truncated = desc[:max_len].rsplit(" ", 1)[0].rstrip(" .,;:")
    return truncated + "."


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
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"

def make_base(content: str, *, title: str, description: str, canonical: str, schema: str, site: dict,
              og_type: str = "website", robots: str = "index,follow", og_title: str = None):
    replacements = {
        "{{title}}":          html.escape(title),
        "{{description}}":    html.escape(description),
        "{{canonical}}":      canonical,
        "{{robots}}":         robots,
        "{{og_type}}":        og_type,
        "{{og_title}}":       html.escape(og_title or title),
        "{{og_image}}":       abs_url(site, "/assets/og-image.png"),
        "{{site_name}}":      html.escape(site["site_name"]),
        "{{tagline}}":        html.escape(site["tagline"]),
        "{{content}}":        localize_content_paths(content, site),
        "{{schema}}":         schema,
        "{{asset_prefix}}":   site.get("site_path", ""),
        "{{adsense_client}}": site["adsense_client"],
        "{{ga4_id}}":         site["ga4_id"],
        "{{year}}":           str(datetime.utcnow().year),
        "{{footer_cats}}":    _FOOTER_CATS_HTML,
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
    return json_ld({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in pairs
        ]
    })

def article_schema(site, post, url):
    return json_ld({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post["title"],
        "description": post["description"],
        "datePublished": post["date"],
        "dateModified": post["date"],
        "author": {"@type": "Organization", "name": site["author"]},
        "publisher": {
            "@type": "Organization",
            "name": site["site_name"],
            "logo": {"@type": "ImageObject", "url": abs_url(site, "/assets/logo-mark.svg")}
        },
        "mainEntityOfPage": url,
        "image": [abs_url(site, "/assets/og-image.png")],
        "articleSection": post["category"],
        "keywords": ", ".join(post["keywords"])
    })


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


def render_guides_index(site, posts):
    cards = ''.join(render_card(p) for p in posts)
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / Guides</div>
        <h1>Scam guides</h1>
        <p class="lead">Browse all published guides by scam type, payment method, platform, or impersonation pattern.</p>
        <div class="search-box" style="max-width:720px">
          <input id="pageSearch" type="search" placeholder="Filter guides on this page" aria-label="Filter guides">
        </div>
      </div>
    </section>
    <section class="section">
      <div class="wrap">
        <div class="grid-3" id="guideGrid">{cards}</div>
      </div>
    </section>
    <script>
      const params = new URLSearchParams(window.location.search);
      const input = document.getElementById('pageSearch');
      const cards = Array.from(document.querySelectorAll('[data-searchable]'));
      function applyFilter(value) {{
        const q = (value || '').toLowerCase().trim();
        cards.forEach(card => {{
          card.style.display = card.dataset.searchable.includes(q) ? '' : 'none';
        }});
      }}
      input.addEventListener('input', e => applyFilter(e.target.value));
      if (params.get('q')) {{ input.value = params.get('q'); applyFilter(input.value); }}
    </script>
    '''
    schema = page_schema(site, 'Guides', 'Browse all scam guides published on Beat the Scam.', site['domain'] + '/guides/')
    return make_base(content, title=f'Scam Guides | {site["site_name"]}', description='Browse all published UK scam guides by type — from phishing emails and fake texts to crypto fraud, job scams, and marketplace abuse. Free advice, no account needed.', canonical=site['domain'] + '/guides/', schema=schema, site=site)


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
    return make_base(
        content,
        title=f'Categories | {site["site_name"]}',
        description='Browse all scam categories and find guides relevant to the message or situation you are checking.',
        canonical=site['domain'] + '/categories/',
        schema=page_schema(site, 'Categories', 'Browse scam guide categories.', site['domain'] + '/categories/'),
        site=site
    )


def render_category_page(site, category, posts, all_categories=None):
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

    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/categories/">Categories</a> / {html.escape(label)}</div>
        <h1>{html.escape(label)}</h1>
        <p class="lead">{html.escape(desc)}</p>
      </div>
    </section>
    <section class="section"><div class="wrap"><div class="grid-3">{"".join(render_card(p) for p in posts)}</div></div></section>
    {related_cats_html}
    '''
    return make_base(
        content,
        title=seo_title(label, site["site_name"]),
        description=seo_description(desc),
        canonical=site['domain'] + f'/categories/{slug}/',
        schema=page_schema(site, label, desc, site['domain'] + f'/categories/{slug}/'),
        site=site
    )


def related_posts(posts, current, count=4):
    current_sig = topic_signature(current)
    seen = {current_sig}
    ordered = []
    same_cat = [p for p in posts if p['slug'] != current['slug'] and p['category'] == current['category']]
    others   = [p for p in posts if p['slug'] != current['slug'] and p['category'] != current['category']]
    for p in same_cat + others:
        sig = topic_signature(p)
        if sig in seen:
            continue
        seen.add(sig)
        ordered.append(p)
        if len(ordered) >= count:
            break
    return ordered


def render_post(site, post, all_posts, affiliates=None):
    url   = site['domain'] + f'/guides/{post["slug"]}/'
    label = category_label(post["category"])
    mins  = reading_time(post)

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
            section_parts.append(f'<h2 id="{sid}">{html.escape(title)}</h2><p>{html.escape(para)}</p>')

    toc      = "".join(f'<li><a href="#{sid}">{html.escape(t)}</a></li>' for sid, t in section_ids)
    faq_html = "".join(f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q, a in post['faq'])
    badges   = "".join(f'<span class="badge">{html.escape(k)}</span>' for k in post['keywords'])
    related  = "".join(
        f'<a href="/guides/{p["slug"]}/">{html.escape(p["title"])}<span class="meta">{html.escape(category_label(p["category"]))} &middot; {p["date"]}</span></a>'
        for p in related_posts(all_posts, post)
    )

    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/guides/">Guides</a> / <a href="/categories/{post["category"]}/">{html.escape(label)}</a> / <span class="bc-title">{html.escape(post["title"])}</span></div>
      </div>
    </section>
    <section class="wrap article-layout">
      <article class="article">
        <div class="eyebrow">{html.escape(label)}</div>
        <h1>{html.escape(post["title"])}</h1>
        <p class="lead">{html.escape(post["hero"])}</p>
        <p class="meta">Published {post["date"]} &middot; {html.escape(site["author"])} &middot; {mins} min read</p>
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
    schema = article_schema(site, post, url) + faq_schema(post['faq'])
    return make_base(
        content,
        title=seo_title(post["title"], site["site_name"]),
        og_title=post['title'],
        description=seo_description(post['description']),
        canonical=url,
        schema=schema,
        site=site,
        og_type='article'
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


def build_legal_bodies(site):
    about = f'''
    <p><strong>{html.escape(site["site_name"])}</strong> is a consumer-protection content site focused on helping UK residents recognise scam patterns before they send money, share credentials, or install malicious software.</p>

    <div class="author-card" style="margin:1.5rem 0;padding:1.2rem;border:1px solid var(--line);border-radius:14px;background:#fafafa">
      <p style="margin:0 0 .35rem 0"><strong>Edited by James Carter</strong> &middot; Editor, {html.escape(site["site_name"])}</p>
      <p style="margin:0;font-size:.95rem;color:#555">Background in UK consumer affairs writing with a focus on fraud, online safety, and digital payment risk. Reviews scam patterns regularly and updates guides as new variants emerge.</p>
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
    <p>If you are in the UK or EEA you may have rights relating to your personal data. Contact us at <a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a>.</p>
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
    <p>Questions: <a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a>.</p>
    '''

    terms = '''
    <p>The content on this site is provided for general educational purposes only. It is not legal, financial, investment, cybersecurity, or regulatory advice.</p>
    <h2>No guarantee of outcome</h2>
    <p>Scam tactics change quickly. While the site aims to provide useful guidance, no article can guarantee that a specific interaction is safe or fraudulent.</p>
    <h2>AI scam checker</h2>
    <p>The AI scam checker is an educational tool. Its output is not a definitive fraud determination. Always verify through official channels and contact your bank immediately if you have already sent money or shared account details.</p>
    <h2>User responsibility</h2>
    <p>You remain responsible for verifying urgent or high-value matters through official channels or qualified professionals.</p>
    <h2>External links</h2>
    <p>The site may link to third-party services or official resources. Those sites operate under their own terms and privacy policies.</p>
    '''

    contact = f'''
    <p>For editorial contact, corrections, or partnership enquiries, email <a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a>.</p>
    <div class="tablelike">
      <div class="table-row"><strong>Editorial corrections</strong><span>Send the page URL and the correction you want reviewed.</span></div>
      <div class="table-row"><strong>Advertising or partnerships</strong><span>Include the business name, proposal, and relevant website.</span></div>
      <div class="table-row"><strong>Privacy queries</strong><span>Reference &#8220;Privacy request&#8221; in the subject line.</span></div>
    </div>
    <p class="note" style="margin-top:1.5rem">To report a scam to UK authorities directly, use <a href="https://www.reportfraud.police.uk/" rel="noopener noreferrer" target="_blank">Action Fraud</a> or forward suspicious texts to <strong>7726</strong> (free on all UK networks).</p>
    '''

    return about, privacy, cookies, terms, contact


# ─── DEDUPLICATE ────────────────────────────────────────────────────────────

def deduplicate_posts(posts: list) -> list:
    """Keep only the most recent post per slug."""
    seen: dict = {}
    for post in posts:
        slug = post["slug"]
        if slug not in seen or post["date"] > seen[slug]["date"]:
            seen[slug] = post
    return sorted(seen.values(), key=lambda p: p["date"], reverse=True)


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
            m = pat.search(text)
            if m:
                text = text[:m.start()] + f'<a href="{url}">{m.group()}</a>' + text[m.end():]
                used.add(phrase)
                added += 1
        out.append(text)
    return "".join(out)


# ─── MAIN BUILD ────────────────────────────────────────────────────────────

def build():
    site     = read_json(ROOT / 'content/site.json')
    raw_posts = read_json(ROOT / 'content/posts.json')

    affiliates = load_affiliates(ROOT)

    # Normalise category names
    for post in raw_posts:
        post["category"] = normalize_category(post["category"])

    # Deduplicate — keep newest per slug
    posts = deduplicate_posts(raw_posts)

    categories = defaultdict(list)
    for post in posts:
        categories[post['category']].append(post)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copytree(ROOT / 'assets', DIST / 'assets')

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
    write(DIST / 'guides/index.html', render_guides_index(site, posts))
    write(DIST / 'categories/index.html', render_categories_index(site, categories))
    for cat, items in categories.items():
        write(DIST / 'categories' / slugify(cat) / 'index.html', render_category_page(site, cat, items, categories))

    # Build phrase → URL map once for the whole site, then auto-link
    # contextual mentions inside each rendered guide before writing.
    link_map = build_internal_link_map(posts)

    for post in posts:
        html_out = render_post(site, post, posts, affiliates)
        html_out = apply_internal_links(html_out, post['slug'], link_map)
        write(DIST / 'guides' / post['slug'] / 'index.html', html_out)

    write(DIST / 'check/index.html', render_check_page(site))

    about, privacy, cookies, terms, contact = build_legal_bodies(site)
    write(DIST / 'about/index.html',   render_simple_page(site, 'About',          'Beat the Scam is a free UK consumer protection site. Learn how guides are researched, who writes them, and how the AI scam checker works.',        about,   'about'))
    write(DIST / 'privacy/index.html', render_simple_page(site, 'Privacy Policy', 'How Beat the Scam uses Google Analytics, Google AdSense, and the Anthropic Claude API. Understand your data choices and cookie consent options.',          privacy, 'privacy'))
    write(DIST / 'cookies/index.html', render_simple_page(site, 'Cookie Policy',  'How Beat the Scam uses cookies for analytics, advertising, and consent preferences. Learn what is stored and how to manage your cookie settings.',                   cookies, 'cookies'))
    write(DIST / 'terms/index.html',   render_simple_page(site, 'Terms',          'Terms of use for Beat the Scam. Educational scam guidance only — not legal or financial advice. Read before relying on any content for important decisions.',                                 terms,   'terms'))
    write(DIST / 'contact/index.html', render_simple_page(site, 'Contact',        'Contact Beat the Scam for editorial corrections, privacy questions, or partnership enquiries. We aim to respond to all editorial requests promptly.',     contact, 'contact'))

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

    # Sitemap — includes lastmod dates so crawlers can prioritise fresh content
    today = datetime.utcnow().strftime("%Y-%m-%d")
    static_urls = ['/', '/guides/', '/categories/', '/check/', '/about/', '/privacy/', '/cookies/', '/terms/', '/contact/']
    sitemap_lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in static_urls:
        sitemap_lines.append(f'<url><loc>{site["domain"]}{url}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>')
    for p in posts:
        sitemap_lines.append(f'<url><loc>{site["domain"]}/guides/{p["slug"]}/</loc><lastmod>{p["date"]}</lastmod><changefreq>monthly</changefreq></url>')
    for cat in categories:
        sitemap_lines.append(f'<url><loc>{site["domain"]}/categories/{slugify(cat)}/</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>')
    sitemap_lines.append('</urlset>')
    write(DIST / 'sitemap.xml', '\n'.join(sitemap_lines))

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

    # IndexNow key — tells Bing/Yandex about new/updated pages instantly.
    # Key must match the filename. Generate once and keep stable.
    indexnow_key = "b3c8e1f2a94d7056"
    write(DIST / f'{indexnow_key}.txt', indexnow_key)

    # _redirects (Netlify)
    # Category slug 301s — auto-derived from CATEGORY_CANON.
    # Lives in dist/_redirects rather than netlify.toml because [[redirects]]
    # in toml weren't being applied at edge despite headers and the API
    # redirect from the same toml working correctly.
    redirect_lines = ["# Category slug normalisation (auto-generated from CATEGORY_CANON)"]
    seen = set()
    for old_label, new_slug in CATEGORY_CANON.items():
        old_slug = old_label.replace(" ", "-")
        if old_slug == new_slug or old_slug in seen:
            continue
        seen.add(old_slug)
        redirect_lines.append(f"/categories/{old_slug}    /categories/{new_slug}/    301!")
        redirect_lines.append(f"/categories/{old_slug}/*    /categories/{new_slug}/:splat    301!")
    write(DIST / '_redirects', "\n".join(redirect_lines) + "\n")

    print(f"Built {len(posts)} posts across {len(categories)} categories -> {DIST}")

if __name__ == "__main__":
    build()
