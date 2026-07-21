# Beat The Scam

UK consumer-protection site — plain-English scam guides + free AI scam checker.
Live: **https://beatthescam.com**

## Documentation

Start with [`AGENTS.md`](AGENTS.md) or [`CLAUDE.md`](CLAUDE.md), which are intentionally byte-for-byte identical, then use the documentation set below:

| Doc | What it covers |
|---|---|
| [`AGENTS.md`](AGENTS.md) / [`CLAUDE.md`](CLAUDE.md) | Critical repository invariants for Codex and Claude; update both together |
| [`docs/next-session.md`](docs/next-session.md) | Current verified baseline and outstanding priorities |
| [`docs/README.md`](docs/README.md) | Documentation index + "find by question" map |
| [`docs/project.md`](docs/project.md) | Master project document — tech stack, secrets, monetisation, SEO, security, runbook, valuation. Single source of truth. |
| [`docs/search-ai-measurement.md`](docs/search-ai-measurement.md) | Search Console and Bing AI measurement method |
| [`docs/buyer-data-room/README.md`](docs/buyer-data-room/README.md) | Sale-readiness and buyer-evidence index |
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
├── AGENTS.md / CLAUDE.md    # identical agent instructions
├── docs/                    # all project documentation
├── analytics/               # retained search/AI + commercial evidence
├── scripts/                 # build, content generation, social (+ legacy video scripts)
├── content/                 # source-of-truth content (posts.json, queue, etc.)
├── templates/               # HTML shell template
├── assets/                  # CSS, JS (+ legacy video/audio assets)
├── netlify/                 # serverless functions (scam-checker)
├── dist/                    # built site (committed, served by Netlify)
└── .github/workflows/       # daily-publish + Search Console crons
```
