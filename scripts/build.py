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


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def abs_url(site, path: str) -> str:
    if path.startswith("http"):
        return path
    return site["domain"].rstrip("/") + site.get("site_path", "") + path

def json_ld(data) -> str:
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"


def make_base(content: str, *, title: str, description: str, canonical: str, schema: str, site: dict,
              og_type: str = "website", robots: str = "index,follow", og_title: str | None = None):
    replacements = {
        "{{title}}": html.escape(title),
        "{{description}}": html.escape(description),
        "{{canonical}}": canonical,
        "{{robots}}": robots,
        "{{og_type}}": og_type,
        "{{og_title}}": html.escape(og_title or title),
        "{{og_image}}": abs_url(site, "/assets/og-image.png"),
        "{{site_name}}": html.escape(site["site_name"]),
        "{{tagline}}": html.escape(site["tagline"]),
        "{{content}}": content,
        "{{schema}}": schema,
        "{{asset_prefix}}": site.get("site_path", ""),
        "{{adsense_client}}": site["adsense_client"],
        "{{ga4_id}}": site["ga4_id"],
        "{{year}}": str(datetime.utcnow().year),
    }
    page = BASE
    for key, value in replacements.items():
        page = page.replace(key, value)
    return page


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
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a}
            }
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


def render_card(post):
    return f'''
    <article class="card guide-card" data-searchable="{html.escape((post["title"] + ' ' + post["description"] + ' ' + post["category"] + ' ' + ' '.join(post["keywords"])).lower())}">
      <div class="eyebrow">{html.escape(post["category"])}</div>
      <h3><a href="/guides/{post["slug"]}/">{html.escape(post["title"])}</a></h3>
      <p>{html.escape(post["description"])}</p>
      <p class="meta">Updated {post["date"]}</p>
    </article>
    '''


def render_home(site, posts, categories):
    featured = "".join(render_card(p) for p in posts[:6])
    category_cards = []
    for cat, items in sorted(categories.items(), key=lambda item: len(item[1]), reverse=True)[:8]:
        category_cards.append(f'''
        <article class="card category-card">
          <h3><a href="/categories/{slugify(cat)}/">{html.escape(cat)}</a></h3>
          <p>{len(items)} guide{'s' if len(items) != 1 else ''} covering common verification patterns and recovery steps.</p>
        </article>
        ''')
    latest_links = "".join(f'<li><a href="/guides/{p["slug"]}/">{html.escape(p["title"])}</a></li>' for p in posts[:5])
    faq_pairs = [
        ("Does Beat the Scam verify messages for me?", "The site provides educational checklists and examples so readers can verify suspicious messages themselves through official channels."),
        ("Can social media ads or polished emails still be scams?", "Yes. Presentation quality is not proof of legitimacy. Verification path matters more than appearance."),
        ("What should I do first if I already paid a scammer?", "Contact your bank or card issuer immediately, preserve evidence, secure compromised accounts, and stop further payments while you verify the situation.")
    ]
    faq_html = "".join(f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q, a in faq_pairs)
    content = f'''
    <section class="hero">
      <div class="wrap hero-grid">
        <div class="hero-panel">
          <div class="kicker">Consumer protection hub</div>
          <h1>Check scams. Protect your money.</h1>
          <p class="lead">Beat the Scam helps readers review suspicious texts, emails, websites, calls, job offers, crypto pitches, and payment requests before money or data is lost.</p>
          <div class="hero-actions">
            <a class="btn btn-primary" href="/guides/">Browse guides</a>
            <a class="btn btn-secondary" href="#search-start">Search scam topics</a>
          </div>
          <div class="hero-points">
            <div class="hero-point"><strong>20</strong><span>launch guides</span></div>
            <div class="hero-point"><strong>12</strong><span>scam categories</span></div>
            <div class="hero-point"><strong>Fast</strong><span>plain-English checks</span></div>
          </div>
        </div>
        <div class="hero-side">
          <section class="search-panel" id="search-start">
            <h3>Search scam topics</h3>
            <p class="search-note">Try terms like “Royal Mail text”, “job scam”, “bank transfer”, or “crypto withdrawal fee”.</p>
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
          <div class="metric-card"><strong>Organic-ready</strong><span>Structured titles, meta descriptions, schema, sitemap, RSS, and internal linking built in.</span></div>
          <div class="metric-card"><strong>GA4</strong><span>Analytics installed with consent-aware configuration and outbound-click tracking.</span></div>
          <div class="metric-card"><strong>AdSense-ready</strong><span>Publisher ID inserted and ads.txt generated for review and monetisation setup.</span></div>
          <div class="metric-card"><strong>Trust pages</strong><span>Privacy, cookies, about, terms, and contact pages included for compliance and review.</span></div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="section-head">
          <div>
            <h2>High-intent scam categories</h2>
            <p>These category pages are built to support internal linking, discovery, and long-tail content expansion over time.</p>
          </div>
          <a href="/categories/">View all categories</a>
        </div>
        <div class="category-grid">{''.join(category_cards)}</div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="section-head">
          <div>
            <h2>Featured guides</h2>
            <p>Editorial-style article cards designed to look more credible than a thin niche blog while staying lightweight and fast.</p>
          </div>
          <a href="/guides/">Browse all guides</a>
        </div>
        <div class="grid-3">{featured}</div>
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
        <div class="section-head">
          <div>
            <h2>Why users and reviewers trust the site more</h2>
            <p>The layout, legal pages, and content model are designed to read like a serious consumer-protection publication rather than a thin affiliate microsite.</p>
          </div>
        </div>
        <div class="trust-grid">
          <article class="trust-card"><h3>Editorial positioning</h3><p>Plain-English explanations, clear checklists, and practical action steps instead of generic filler content.</p></article>
          <article class="trust-card"><h3>Technical SEO</h3><p>Structured markup, canonical tags, Open Graph tags, sitemap, robots, RSS, and homepage indexability configured.</p></article>
          <article class="trust-card"><h3>Monetisation readiness</h3><p>Consent-aware analytics, AdSense script integration, ads.txt, and policy pages included for site review.</p></article>
        </div>
      </div>
    </section>
    '''
    schema = website_schema(site) + org_schema(site) + faq_schema(faq_pairs)
    return make_base(
        content,
        title=f'{site["site_name"]} | Scam Alerts, Checks & Protection Guides',
        og_title=f'{site["site_name"]} | Scam Alerts, Checks & Protection Guides',
        description='Scam alerts, verification guides, and plain-English checks for suspicious texts, emails, websites, calls, and payment requests.',
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
    return make_base(content, title=f'Guides | {site["site_name"]}', description='Browse all scam guides.', canonical=site['domain'] + '/guides/', schema=schema, site=site)


def render_categories_index(site, categories):
    items = []
    for cat, posts in sorted(categories.items(), key=lambda item: len(item[1]), reverse=True):
        items.append(f'''
        <article class="card category-card guide-card">
          <div class="eyebrow">Category</div>
          <h3><a href="/categories/{slugify(cat)}/">{html.escape(cat)}</a></h3>
          <p>{len(posts)} guide{'s' if len(posts) != 1 else ''} currently published in this cluster.</p>
        </article>
        ''')
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / Categories</div>
        <h1>Categories</h1>
        <p class="lead">Organised content hubs for search discovery and internal linking.</p>
      </div>
    </section>
    <section class="section"><div class="wrap"><div class="category-grid">{''.join(items)}</div></div></section>
    '''
    return make_base(content, title=f'Categories | {site["site_name"]}', description='Browse scam categories.', canonical=site['domain'] + '/categories/', schema=page_schema(site, 'Categories', 'Browse scam guide categories.', site['domain'] + '/categories/'), site=site)


def render_category_page(site, category, posts):
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/categories/">Categories</a> / {html.escape(category)}</div>
        <h1>{html.escape(category)}</h1>
        <p class="lead">{len(posts)} guide{'s' if len(posts) != 1 else ''} in this category, designed to capture closely related search intent.</p>
      </div>
    </section>
    <section class="section"><div class="wrap"><div class="grid-3">{''.join(render_card(p) for p in posts)}</div></div></section>
    '''
    slug = slugify(category)
    return make_base(content, title=f'{category} | {site["site_name"]}', description=f'Guides about {category.lower()}.', canonical=site['domain'] + f'/categories/{slug}/', schema=page_schema(site, category, f'Guides about {category.lower()}.', site['domain'] + f'/categories/{slug}/'), site=site)


def related_posts(posts, current, count=4):
    same_cat = [p for p in posts if p['slug'] != current['slug'] and p['category'] == current['category']]
    others = [p for p in posts if p['slug'] != current['slug'] and p['category'] != current['category']]
    return (same_cat + others)[:count]


def render_post(site, post, all_posts):
    url = site['domain'] + f'/guides/{post["slug"]}/'
    section_ids = []
    section_html = []
    for title, para in post['sections']:
        sid = slugify(title)
        section_ids.append((sid, title))
        section_html.append(f'<h2 id="{sid}">{html.escape(title)}</h2><p>{html.escape(para)}</p>')
    toc = ''.join(f'<li><a href="#{sid}">{html.escape(title)}</a></li>' for sid, title in section_ids)
    faq_html = ''.join(f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>' for q, a in post['faq'])
    badges = ''.join(f'<span class="badge">{html.escape(k)}</span>' for k in post['keywords'])
    related = ''.join(f'<a href="/guides/{p["slug"]}/">{html.escape(p["title"])}<span class="meta">{html.escape(p["category"])} · {p["date"]}</span></a>' for p in related_posts(all_posts, post))
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/guides/">Guides</a> / {html.escape(post['title'])}</div>
      </div>
    </section>
    <section class="wrap article-layout">
      <article class="article">
        <div class="eyebrow">{html.escape(post['category'])}</div>
        <h1>{html.escape(post['title'])}</h1>
        <p class="lead">{html.escape(post['hero'])}</p>
        <p class="meta">Published {post['date']} · {html.escape(site['author'])}</p>
        <div class="badge-row">{badges}</div>
        <div class="notice"><strong>Key rule:</strong> verify through an official route you opened yourself, not the link, number, app, or payment details supplied by the suspicious message.</div>
        <div class="toc"><strong>On this page</strong><ol>{toc}</ol></div>
        {''.join(section_html)}
        <div class="inline-ad">AdSense Auto Ads can fill this article naturally after site approval. Keep content value higher than ad density.</div>
        <h2>Frequently asked questions</h2>
        <div class="faq">{faq_html}</div>
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
          <h3>Need more context?</h3>
          <p class="note">Read the legal and trust pages so AdSense reviewers and users can see a complete, transparent publication footprint.</p>
          <p><a href="/about/">About the site</a><br><a href="/privacy/">Privacy Policy</a><br><a href="/cookies/">Cookie Policy</a></p>
        </section>
      </aside>
    </section>
    '''
    schema = article_schema(site, post, url) + faq_schema(post['faq'])
    return make_base(content, title=f'{post["title"]} | {site["site_name"]}', og_title=post['title'], description=post['description'], canonical=url, schema=schema, site=site, og_type='article')


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
    <p><strong>{html.escape(site["site_name"])}</strong> is a consumer-protection content site focused on helping readers recognise scam patterns before they send money, share credentials, or install malicious software.</p>
    <p>The editorial model is simple: fast checks, plain-English explanations, and practical actions. The site is not a law firm, bank, or regulator. It is an educational publication designed to reduce avoidable losses.</p>
    <div class="tablelike">
      <div class="table-row"><strong>Editorial focus</strong><span>Scam alerts, payment risk, impersonation patterns, delivery fraud, marketplace abuse, crypto scams, and recovery scams.</span></div>
      <div class="table-row"><strong>How guides are structured</strong><span>Each guide targets a specific scam type or search intent and explains what to verify, what to avoid, and what to do next.</span></div>
      <div class="table-row"><strong>Commercial model</strong><span>Advertising-supported publication using Google AdSense, with scope for future consumer-safety partnerships.</span></div>
    </div>
    <h2>Editorial standards</h2>
    <p>Content is written to be understandable under pressure. That means short sections, clear headings, and advice that pushes readers towards independent verification through official channels.</p>
    <h2>Contact</h2>
    <p>Editorial contact and correction requests: <a href="mailto:{site['contact_email']}">{site['contact_email']}</a></p>
    '''

    privacy = f'''
    <p>This Privacy Policy explains how {html.escape(site["site_name"])} uses analytics, advertising, and standard website technologies when you browse the site.</p>
    <h2>What information we collect</h2>
    <p>The site does not offer user accounts, comments, or direct purchases. Standard server logs may record technical information such as browser type, device type, approximate location, referral source, and requested pages.</p>
    <h2>Google Analytics</h2>
    <p>The site uses Google Analytics 4 to understand page performance and traffic trends. The configured measurement ID is <strong>{html.escape(site['ga4_id'])}</strong>. Analytics cookies are only enabled after consent where required.</p>
    <h2>Advertising</h2>
    <p>The site uses Google AdSense with publisher ID <strong>{html.escape(site['adsense_client'])}</strong>. If advertising is active, Google and its partners may use cookies or similar technologies to deliver and measure ads, subject to your consent choices and applicable law.</p>
    <h2>Cookie choices</h2>
    <p>A cookie banner allows you to accept or reject non-essential cookies. Your preference is stored locally in your browser so the site can remember that choice.</p>
    <h2>Your rights</h2>
    <p>If you are in the UK or EEA, you may have rights relating to access, correction, or deletion of personal data depending on the context. Because the site is intentionally low-data, many visits involve minimal personal data processing.</p>
    <h2>Contact</h2>
    <p>For privacy-related queries, email <a href="mailto:{site['contact_email']}">{site['contact_email']}</a>.</p>
    '''

    cookies = f'''
    <p>This Cookie Policy explains what cookies and similar technologies may be used on {html.escape(site["site_name"])}.</p>
    <h2>Essential storage</h2>
    <p>The site stores a small preference in your browser to remember whether you accepted or rejected non-essential cookies. This supports compliance and avoids repeatedly showing the same banner after a choice has been made.</p>
    <h2>Analytics cookies</h2>
    <p>If you accept analytics cookies, Google Analytics 4 may collect information about page views, device type, referral source, and interaction patterns so site performance can be measured and improved.</p>
    <h2>Advertising cookies</h2>
    <p>If advertising is active and you consent, Google AdSense may use cookies or similar technologies to support ad delivery, frequency management, measurement, and related services.</p>
    <h2>How to manage cookies</h2>
    <p>You can change browser cookie settings at any time. You can also use the site's Cookie settings link in the footer to reopen the consent banner on your device.</p>
    <h2>Contact</h2>
    <p>Questions about cookies or data use can be sent to <a href="mailto:{site['contact_email']}">{site['contact_email']}</a>.</p>
    '''

    terms = '''
    <p>The content on this site is provided for general educational purposes only. It is not legal, financial, investment, cybersecurity, or regulatory advice.</p>
    <h2>No guarantee of outcome</h2>
    <p>Scam tactics change quickly. While the site aims to provide useful guidance, no article can guarantee that a specific interaction is safe or fraudulent.</p>
    <h2>User responsibility</h2>
    <p>You remain responsible for verifying urgent or high-value matters through official channels, qualified professionals, or regulated entities where appropriate.</p>
    <h2>External links</h2>
    <p>The site may link to third-party services or official resources for convenience. Those external sites operate under their own terms and privacy policies.</p>
    '''

    contact = f'''
    <p>For editorial contact, corrections, or partnership enquiries, email <a href="mailto:{site['contact_email']}">{site['contact_email']}</a>.</p>
    <p>At launch, the site uses email rather than a form to keep the site fast, simple, and low-maintenance.</p>
    <div class="tablelike">
      <div class="table-row"><strong>Editorial corrections</strong><span>Send the page URL and the correction you want reviewed.</span></div>
      <div class="table-row"><strong>Advertising or partnerships</strong><span>Include the business name, proposal, and relevant website.</span></div>
      <div class="table-row"><strong>Privacy queries</strong><span>Reference “Privacy request” in the subject line.</span></div>
    </div>
    '''

    return about, privacy, cookies, terms, contact


def build():
    site = read_json(ROOT / 'content/site.json')
    posts = sorted(read_json(ROOT / 'content/posts.json'), key=lambda p: p['date'], reverse=True)
    categories = defaultdict(list)
    for post in posts:
        categories[post['category']].append(post)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    shutil.copytree(ROOT / 'assets', DIST / 'assets')

    write(DIST / 'index.html', render_home(site, posts, categories))
    write(DIST / 'guides/index.html', render_guides_index(site, posts))
    write(DIST / 'categories/index.html', render_categories_index(site, categories))
    for cat, items in categories.items():
        write(DIST / 'categories' / slugify(cat) / 'index.html', render_category_page(site, cat, items))
    for post in posts:
        write(DIST / 'guides' / post['slug'] / 'index.html', render_post(site, post, posts))

    about, privacy, cookies, terms, contact = build_legal_bodies(site)
    write(DIST / 'about/index.html', render_simple_page(site, 'About', 'Why the site exists, how it is written, and what it is designed to do.', about, 'about'))
    write(DIST / 'privacy/index.html', render_simple_page(site, 'Privacy Policy', 'How the site uses analytics, advertising, and limited technical data.', privacy, 'privacy'))
    write(DIST / 'cookies/index.html', render_simple_page(site, 'Cookie Policy', 'How cookies and local browser storage are used on the site.', cookies, 'cookies'))
    write(DIST / 'terms/index.html', render_simple_page(site, 'Terms', 'Terms for using this educational content site.', terms, 'terms'))
    write(DIST / 'contact/index.html', render_simple_page(site, 'Contact', 'How to reach the site for corrections, privacy questions, or partnerships.', contact, 'contact'))

    not_found = make_base(
        '''
        <section class="hero"><div class="wrap"><h1>Page not found</h1><p class="lead">The page may have moved or the address may be incorrect. Try the guides index or homepage.</p><div class="hero-actions"><a class="btn btn-primary" href="/">Home</a><a class="btn btn-secondary" href="/guides/">Guides</a></div></div></section>
        ''',
        title=f'404 | {site["site_name"]}',
        description='Page not found.',
        canonical=site['domain'] + '/404.html',
        schema=page_schema(site, '404', 'Page not found.', site['domain'] + '/404.html'),
        site=site,
        robots='noindex,follow'
    )
    write(DIST / '404.html', not_found)
    write(DIST / 'CNAME', 'beatthescam.com')
    write(DIST / 'ads.txt', f'google.com, {site["adsense_client"].replace("ca-", "")}, DIRECT, f08c47fec0942fa0')

    search_items = []
    for post in posts:
        blob = ' '.join([post['title'], post['description'], post['category'], *post['keywords'], *[s[0] + ' ' + s[1] for s in post['sections']]])
        search_items.append({
            'title': post['title'],
            'url': f'/guides/{post["slug"]}/',
            'description': post['description'],
            'category': post['category'],
            'content': blob
        })
    write(DIST / 'search.json', json.dumps(search_items, indent=2))

    rss_items = []
    for post in posts[:30]:
        rss_items.append(f'''
        <item>
          <title>{html.escape(post['title'])}</title>
          <link>{site['domain']}/guides/{post['slug']}/</link>
          <guid>{site['domain']}/guides/{post['slug']}/</guid>
          <pubDate>{datetime.strptime(post['date'], '%Y-%m-%d').strftime('%a, %d %b %Y 00:00:00 +0000')}</pubDate>
          <description>{html.escape(post['description'])}</description>
        </item>
        ''')
    rss = f'''<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <title>{html.escape(site['site_name'])}</title>
        <link>{site['domain']}</link>
        <description>{html.escape(site['tagline'])}</description>
        {''.join(rss_items)}
      </channel>
    </rss>'''
    write(DIST / 'rss.xml', rss)

    urls = ['/', '/guides/', '/categories/', '/about/', '/privacy/', '/cookies/', '/terms/', '/contact/']
    urls += [f'/guides/{p["slug"]}/' for p in posts]
    urls += [f'/categories/{slugify(cat)}/' for cat in categories]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        sitemap.append(f'  <url><loc>{site["domain"]}{url}</loc></url>')
    sitemap.append('</urlset>')
    write(DIST / 'sitemap.xml', '\n'.join(sitemap))

    robots = f'''User-agent: *
Allow: /

Sitemap: {site['domain']}/sitemap.xml
'''
    write(DIST / 'robots.txt', robots)


if __name__ == '__main__':
    build()
