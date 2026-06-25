# Beat The Scam

UK consumer-protection site — plain-English scam guides + free AI scam checker.
Live: **https://beatthescam.com**

## Documentation

All canonical project documentation lives in [`docs/`](docs/):

| Doc | What it covers |
|---|---|
| [`docs/README.md`](docs/README.md) | Documentation index + "find by question" map |
| [`docs/project.md`](docs/project.md) | Master project document — tech stack, secrets, monetisation, SEO, security, runbook, valuation. Single source of truth. |
| [`docs/video-pipeline.md`](docs/video-pipeline.md) | HISTORICAL — TikTok / YouTube Shorts video pipeline (production discontinued 2026-06-15) |
| [`docs/youtube-upload-setup.md`](docs/youtube-upload-setup.md) | HISTORICAL — YouTube OAuth setup (video discontinued) |
| [`docs/daily-publish.md`](docs/daily-publish.md) | Claude-native daily content publisher |
| [`docs/project-template.md`](docs/project-template.md) | Generic template for bootstrapping similar future projects |

## Quick commands

```bash
# Build the static site (writes to dist/)
python3 scripts/build.py

# Auto-tweet a published article
python3 scripts/tweet_new_articles.py --slug <slug>
```

## Repository layout

```
beatthescam-site/
├── README.md                # this file
├── docs/                    # all project documentation
├── scripts/                 # build, content generation, social (+ legacy video scripts)
├── content/                 # source-of-truth content (posts.json, queue, etc.)
├── templates/               # HTML shell template
├── assets/                  # CSS, JS (+ legacy video/audio assets)
├── netlify/                 # serverless functions (scam-checker)
├── dist/                    # built site (committed, served by Netlify)
└── .github/workflows/       # daily-publish + Search Console crons
```
