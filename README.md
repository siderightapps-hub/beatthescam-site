# Beat the Scam — ready-to-deploy static site

A static SEO site for **beatthescam.com**, designed for:
- GitHub Pages deployment
- custom-domain use
- AdSense insertion
- long-tail scam / fraud search traffic
- low-maintenance content scaling

## What is included
- Static site generator in `scripts/build.py`
- Home page, guide index, categories, about, contact, privacy, terms, 404
- 10 seed guides in `content/posts.json`
- Structured data (Article, FAQPage, WebPage)
- `robots.txt`, `sitemap.xml`, `rss.xml`, `search.json`
- GitHub Actions deployment workflow to Pages
- `CNAME` file for `beatthescam.com`

## Fast start
1. Create a new public GitHub repository.
2. Upload all files from this project.
3. In `content/site.json`, replace:
   - `ca-pub-XXXXXXXXXXXXXXXX` with your AdSense publisher ID
   - `G-XXXXXXXXXX` in `templates/base.html` with your GA4 measurement ID if you want analytics
   - contact email and any branding details
4. Push to `main`.
5. In GitHub:
   - Settings → Pages → Source = GitHub Actions
6. Add your custom domain in Pages settings.
7. Configure DNS at your registrar for GitHub Pages.
8. After deployment and DNS propagation, add the site in AdSense and place your approved ad units.

## Content workflow
Edit `content/posts.json`, then push to `main`.
The workflow rebuilds and deploys the site automatically.

Each post requires:
- slug
- title
- description
- category
- date
- keywords
- hero
- sections
- faq

## Suggested next content expansion
To improve SEO depth, add branded search pages such as:
- Is [brand] a scam?
- [Courier] text scam
- [Bank] phone scam warning signs
- [Marketplace] payment scam

## Important
This project is technically deployment-ready, but the starter privacy / terms copy should be reviewed before the live launch. AdSense approval still depends on site quality, policy compliance, and successful ownership verification.
