import json, os, shutil, re, html
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

def slugify(text):
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"[\s-]+", "-", text)

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def render_template(template, context):
    for key, value in context.items():
        template = template.replace("{{"+key+"}}", str(value))
    return template

def make_base(content, *, title, description, canonical, schema, site, asset_prefix="", robots="index,follow", og_type="website"):
    template = (ROOT / "templates/base.html").read_text(encoding="utf-8")
    context = {
        "title": title,
        "description": description,
        "canonical": canonical,
        "robots": robots,
        "og_type": og_type,
        "schema": schema,
        "content": content,
        "site_name": site["site_name"],
        "tagline": site["tagline"],
        "adsense_client": site["adsense_client"],
        "asset_prefix": asset_prefix,
        "year": datetime.now().year,
    }
    return render_template(template, context)

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def article_schema(site, post, url):
    data = {
        "@context":"https://schema.org",
        "@graph":[
            {
                "@type":"Organization",
                "name":site["site_name"],
                "url":site["domain"]
            },
            {
                "@type":"Article",
                "headline":post["title"],
                "description":post["description"],
                "datePublished":post["date"],
                "dateModified":post["date"],
                "author":{"@type":"Organization","name":site["author"]},
                "publisher":{"@type":"Organization","name":site["site_name"]},
                "mainEntityOfPage":url
            },
            {
                "@type":"FAQPage",
                "mainEntity":[
                    {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}}
                    for q, a in post["faq"]
                ]
            }
        ]
    }
    return '<script type="application/ld+json">%s</script>' % json.dumps(data)

def page_schema(site, title, description, url):
    data = {
        "@context":"https://schema.org",
        "@type":"WebPage",
        "name": title,
        "description": description,
        "url": url,
        "publisher": {"@type":"Organization","name":site["site_name"]}
    }
    return '<script type="application/ld+json">%s</script>' % json.dumps(data)

def render_home(site, posts, categories):
    featured = posts[:6]
    cards = []
    for post in featured:
        cards.append(f'''
        <article class="card guide-card">
          <div class="eyebrow">{html.escape(post["category"])}</div>
          <h3><a href="/guides/{post["slug"]}/">{html.escape(post["title"])}</a></h3>
          <p>{html.escape(post["description"])}</p>
          <p class="meta">{post["date"]}</p>
        </article>''')
    category_cards = []
    for cat, items in categories.items():
        category_cards.append(f'''
        <article class="card guide-card">
          <div class="eyebrow">Category</div>
          <h3><a href="/categories/{slugify(cat)}/">{html.escape(cat)}</a></h3>
          <p>{len(items)} guides</p>
        </article>''')
    content = f'''
    <section class="hero">
      <div class="wrap hero-grid">
        <div>
          <span class="kicker">Scam awareness • search-first content site</span>
          <h1>Spot red flags before you lose money, data, or access.</h1>
          <p class="lead">{html.escape(site["tagline"])}</p>
          <div class="badge-row">
            <span class="badge">Website scams</span>
            <span class="badge">Delivery texts</span>
            <span class="badge">Marketplace fraud</span>
            <span class="badge">Crypto scams</span>
            <span class="badge">Phone scams</span>
          </div>
          <div class="cta-row">
            <a class="btn btn-primary" href="/guides/">Browse guides</a>
            <a class="btn btn-secondary" href="/categories/">View categories</a>
          </div>
          <div class="search-box">
            <span>🔎</span>
            <input id="searchInput" type="search" placeholder="Search guides, for example: paypal email scam">
          </div>
          <p class="note">This site ships with a static search index at <code>/search.json</code>.</p>
        </div>
        <aside class="card panel">
          <h3>What this site is built to do</h3>
          <ul class="list-clean">
            <li>Rank for long-tail scam and phishing queries</li>
            <li>Load fast on GitHub Pages with a custom domain</li>
            <li>Support AdSense code insertion across all pages</li>
            <li>Scale through content updates in a simple JSON workflow</li>
          </ul>
        </aside>
      </div>
    </section>
    <section class="section">
      <div class="wrap">
        <div class="grid-3">
          {''.join(cards)}
        </div>
      </div>
    </section>
    <section class="section">
      <div class="wrap">
        <div class="callout">
          <h2>Simple rule: do not trust the link, the caller, or the payment request until you verify it independently.</h2>
          <p>That single rule neutralises a large share of modern consumer scams.</p>
        </div>
      </div>
    </section>
    <section class="section">
      <div class="wrap">
        <h2>Explore by category</h2>
        <div class="category-grid">{''.join(category_cards)}</div>
      </div>
    </section>
    <script>
      const searchInput = document.getElementById('searchInput');
      if (searchInput) {{
        searchInput.addEventListener('keydown', function(e){{
          if(e.key === 'Enter') {{
            const q = encodeURIComponent(searchInput.value.trim());
            if(q) window.location.href = '/guides/?q=' + q;
          }}
        }});
      }}
    </script>
    '''
    return make_base(
        content,
        title=f'{site["site_name"]} | Scam guides and consumer safety checklists',
        description=site["tagline"],
        canonical=site["domain"] + '/',
        schema=page_schema(site, site["site_name"], site["tagline"], site["domain"] + '/'),
        site=site,
    )

def render_guides_index(site, posts):
    cards = []
    for post in posts:
        cards.append(f'''
        <article class="card guide-card" data-searchable="{html.escape((post["title"] + ' ' + post["description"] + ' ' + post["category"]).lower())}">
          <div class="eyebrow">{html.escape(post["category"])}</div>
          <h3><a href="/guides/{post["slug"]}/">{html.escape(post["title"])}</a></h3>
          <p>{html.escape(post["description"])}</p>
          <p class="meta">{post["date"]}</p>
        </article>''')
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / Guides</div>
        <h1>Scam guides</h1>
        <p class="lead">Long-tail, evergreen content designed for organic search and reader trust.</p>
        <div class="search-box">
          <span>🔎</span>
          <input id="pageSearch" type="search" placeholder="Filter guides on this page">
        </div>
      </div>
    </section>
    <section class="section">
      <div class="wrap">
        <div id="guideGrid" class="grid-3">{''.join(cards)}</div>
      </div>
    </section>
    <script>
      const params = new URLSearchParams(window.location.search);
      const input = document.getElementById('pageSearch');
      const cards = Array.from(document.querySelectorAll('[data-searchable]'));
      function applyFilter(val) {{
        const q = (val || '').toLowerCase();
        cards.forEach(card => {{
          card.style.display = card.dataset.searchable.includes(q) ? '' : 'none';
        }});
      }}
      input.addEventListener('input', e => applyFilter(e.target.value));
      if(params.get('q')) {{
        input.value = params.get('q');
        applyFilter(input.value);
      }}
    </script>
    '''
    return make_base(
        content,
        title=f'Guides | {site["site_name"]}',
        description='Browse all Beat the Scam guides by scam type and topic.',
        canonical=site["domain"] + '/guides/',
        schema=page_schema(site, 'Guides', 'Browse all scam guides', site["domain"] + '/guides/'),
        site=site,
    )

def render_categories_index(site, categories):
    cards = []
    for cat, items in categories.items():
        cards.append(f'''
        <article class="card guide-card">
          <div class="eyebrow">Category</div>
          <h3><a href="/categories/{slugify(cat)}/">{html.escape(cat)}</a></h3>
          <p>{len(items)} guides</p>
        </article>
        ''')
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / Categories</div>
        <h1>Categories</h1>
        <p class="lead">Browse scam guides by pattern, channel, or payment method.</p>
      </div>
    </section>
    <section class="section">
      <div class="wrap">
        <div class="category-grid">{''.join(cards)}</div>
      </div>
    </section>
    '''
    return make_base(
        content, title=f'Categories | {site["site_name"]}', description='Browse categories',
        canonical=site["domain"] + '/categories/',
        schema=page_schema(site, 'Categories', 'Browse scam categories', site["domain"] + '/categories/'),
        site=site
    )

def render_category_page(site, category, posts):
    cards = []
    for post in posts:
        cards.append(f'''
        <article class="card guide-card">
          <div class="eyebrow">{html.escape(post["category"])}</div>
          <h3><a href="/guides/{post["slug"]}/">{html.escape(post["title"])}</a></h3>
          <p>{html.escape(post["description"])}</p>
        </article>
        ''')
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/categories/">Categories</a> / {html.escape(category)}</div>
        <h1>{html.escape(category)}</h1>
        <p class="lead">{len(posts)} guide{"s" if len(posts)!=1 else ""} currently published in this category.</p>
      </div>
    </section>
    <section class="section"><div class="wrap"><div class="grid-3">{''.join(cards)}</div></div></section>
    '''
    slug = slugify(category)
    return make_base(
        content, title=f'{category} | {site["site_name"]}', description=f'Guides about {category.lower()}',
        canonical=site["domain"] + f'/categories/{slug}/',
        schema=page_schema(site, category, f'Guides about {category.lower()}', site["domain"] + f'/categories/{slug}/'),
        site=site
    )

def render_post(site, post):
    url = site["domain"] + f'/guides/{post["slug"]}/'
    section_html = []
    for section_title, para in post["sections"]:
        section_html.append(f'<h2>{html.escape(section_title)}</h2><p>{html.escape(para)}</p>')
    faq_html = "".join(
        f'<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>'
        for q,a in post["faq"]
    )
    keyword_badges = "".join(f'<span class="badge">{html.escape(k)}</span>' for k in post["keywords"])
    content = f'''
    <section class="hero">
      <div class="wrap">
        <div class="breadcrumbs"><a href="/">Home</a> / <a href="/guides/">Guides</a> / {html.escape(post["title"])}</div>
      </div>
    </section>
    <section class="wrap article-layout">
      <article class="article">
        <div class="eyebrow">{html.escape(post["category"])}</div>
        <h1>{html.escape(post["title"])}</h1>
        <p class="lead">{html.escape(post["hero"])}</p>
        <p class="meta">Published {post["date"]}</p>
        <div class="badge-row">{keyword_badges}</div>
        <div class="notice">
          <strong>Quick rule:</strong> verify through an official route you opened yourself, not the one supplied in the message, advert, or call.
        </div>
        {''.join(section_html)}
        <div class="inline-ad">Ad placement placeholder. Replace or supplement with your AdSense ad units after site approval.</div>
        <h2>Frequently asked questions</h2>
        <div class="faq">{faq_html}</div>
      </article>
      <aside class="sidebar">
        <div class="card panel">
          <h3>Fast checks</h3>
          <ul class="list-clean">
            <li>Pause before sending money</li>
            <li>Verify with an official site or number</li>
            <li>Never share one-time codes</li>
            <li>Be cautious with bank transfers</li>
          </ul>
        </div>
        <div class="card panel" style="margin-top:1rem">
          <h3>More guides</h3>
          <ul class="list-clean">
            <li><a href="/guides/phone-call-scam-red-flags/">Phone call scam red flags</a></li>
            <li><a href="/guides/facebook-marketplace-scam-signs/">Marketplace scam signs</a></li>
            <li><a href="/guides/job-scam-checklist-uk/">Job scam checklist</a></li>
          </ul>
        </div>
      </aside>
    </section>
    '''
    return make_base(
        content, title=f'{post["title"]} | {site["site_name"]}', description=post["description"],
        canonical=url, schema=article_schema(site, post, url), site=site, og_type="article"
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
    <section class="section">
      <div class="wrap">
        <article class="article">{body}</article>
      </div>
    </section>
    '''
    return make_base(
        content, title=f'{title} | {site["site_name"]}', description=description,
        canonical=site["domain"] + f'/{slug}/',
        schema=page_schema(site, title, description, site["domain"] + f'/{slug}/'), site=site
    )

def build():
    site = read_json(ROOT / "content/site.json")
    posts = sorted(read_json(ROOT / "content/posts.json"), key=lambda p: p["date"], reverse=True)
    categories = {}
    for post in posts:
        categories.setdefault(post["category"], []).append(post)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    shutil.copytree(ROOT / "assets", DIST / "assets")

    write(DIST / "index.html", render_home(site, posts, categories))
    write(DIST / "guides/index.html", render_guides_index(site, posts))
    write(DIST / "categories/index.html", render_categories_index(site, categories))

    for category, items in categories.items():
        write(DIST / "categories" / slugify(category) / "index.html", render_category_page(site, category, items))

    for post in posts:
        write(DIST / "guides" / post["slug"] / "index.html", render_post(site, post))

    about_body = '''
    <p><strong>Beat the Scam</strong> is an educational content site focused on helping ordinary consumers recognise scam patterns before they send money, share credentials, or install malicious software.</p>
    <p>The editorial style is deliberately plain-English. The aim is to turn anxious, high-intent search traffic into practical action steps quickly.</p>
    <div class="tablelike">
      <div class="table-row"><strong>Audience</strong><span>Consumers, online shoppers, sellers, job-seekers, and families checking suspicious messages.</span></div>
      <div class="table-row"><strong>Content model</strong><span>Evergreen guides plus regular updates for new scam variants and branded scam searches.</span></div>
      <div class="table-row"><strong>Monetisation</strong><span>AdSense-first, with scope for consumer-safety affiliate offers later.</span></div>
    </div>
    '''
    privacy_body = '''
    <p>This site uses standard server logs and may use privacy-conscious analytics to understand page performance. If ads are enabled, advertising partners may use cookies or similar technologies as described in their own policies.</p>
    <p>You should replace this starter privacy text with a version tailored to your final analytics, ad, and contact tooling before going live.</p>
    <h2>Data minimisation</h2>
    <p>The base project does not collect user accounts, comments, or payment information. That keeps operational and compliance overhead low.</p>
    '''
    terms_body = '''
    <p>The content on this site is provided for general educational purposes only. It is not legal, regulatory, or financial advice. Readers should verify urgent matters through official channels.</p>
    <p>You are responsible for ensuring the final live site, content, policies, and monetisation setup comply with local law and platform requirements.</p>
    '''
    contact_body = f'''
    <p>For editorial contact or correction requests, email <a href="mailto:{site["contact_email"]}">{site["contact_email"]}</a>.</p>
    <p>A lightweight contact page tends to convert better for trust while avoiding the overhead of running a form backend.</p>
    '''
    not_found_content = make_base(
        '''
        <section class="hero"><div class="wrap">
          <h1>Page not found</h1>
          <p class="lead">The page may have moved. Try the guides index or homepage.</p>
          <div class="cta-row"><a class="btn btn-primary" href="/">Home</a><a class="btn btn-secondary" href="/guides/">Guides</a></div>
        </div></section>
        ''',
        title=f'404 | {site["site_name"]}',
        description='Page not found',
        canonical=site["domain"] + '/404.html',
        schema=page_schema(site, '404', 'Page not found', site["domain"] + '/404.html'),
        site=site,
        robots="noindex,follow"
    )

    write(DIST / "about/index.html", render_simple_page(site, "About", "Why this site exists and how it is designed to grow.", about_body, "about"))
    write(DIST / "privacy/index.html", render_simple_page(site, "Privacy", "Starter privacy policy for the site template.", privacy_body, "privacy"))
    write(DIST / "terms/index.html", render_simple_page(site, "Terms", "Starter terms page for the site template.", terms_body, "terms"))
    write(DIST / "contact/index.html", render_simple_page(site, "Contact", "Editorial contact information.", contact_body, "contact"))
    write(DIST / "404.html", not_found_content)
    write(DIST / "CNAME", "beatthescam.com")

    search_items = []
    for post in posts:
        text_blob = " ".join([post["title"], post["description"], post["category"], *[s[0] + " " + s[1] for s in post["sections"]]])
        search_items.append({
            "title": post["title"],
            "url": f'/guides/{post["slug"]}/',
            "description": post["description"],
            "category": post["category"],
            "content": text_blob
        })
    write(DIST / "search.json", json.dumps(search_items, indent=2))

    items = []
    for post in posts[:20]:
        items.append(f'''
        <item>
          <title>{html.escape(post["title"])}</title>
          <link>{site["domain"]}/guides/{post["slug"]}/</link>
          <guid>{site["domain"]}/guides/{post["slug"]}/</guid>
          <pubDate>{datetime.strptime(post["date"], "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 +0000")}</pubDate>
          <description>{html.escape(post["description"])}</description>
        </item>''')
    rss = f'''<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
      <channel>
        <title>{html.escape(site["site_name"])}</title>
        <link>{site["domain"]}</link>
        <description>{html.escape(site["tagline"])}</description>
        {''.join(items)}
      </channel>
    </rss>'''
    write(DIST / "rss.xml", rss)

    urls = ["/", "/guides/", "/categories/", "/about/", "/privacy/", "/terms/", "/contact/"]
    urls += [f'/guides/{p["slug"]}/' for p in posts]
    urls += [f'/categories/{slugify(cat)}/' for cat in categories]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        lines.append(f'  <url><loc>{site["domain"]}{url}</loc></url>')
    lines.append('</urlset>')
    write(DIST / "sitemap.xml", "\n".join(lines))

    robots = f'''User-agent: *
Allow: /

Sitemap: {site["domain"]}/sitemap.xml
'''
    write(DIST / "robots.txt", robots)

if __name__ == "__main__":
    build()
