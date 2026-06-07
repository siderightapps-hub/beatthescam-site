# Brand assets

Off-site marketing assets (logos, social banners) for Beat the Scam. These are
**not** part of the website — `build.py` only copies `assets/` and `static/`
into `dist/`, so nothing in `brand/` is ever deployed or served.

## Where to store what (the policy)

| Asset type | Lives in | Why |
|---|---|---|
| **Own-brand off-site assets** (logos, LinkedIn/social banners, profile images) | **`brand/`** (here) | Versioned + backed up on GitHub, one source of truth, never deployed. Small files. |
| **Site-served assets** (favicons, OG image, on-page logo SVG, author headshot) | `assets/` and `static/` | Used by the build and served at `beatthescam.com`. |
| **Licensed third-party files** (stock music, stock photos) | **Out of the repo** — local-only or a private drive | Most licenses forbid redistributing the raw file; a repo/deploy would expose it. (e.g. `assets/audio/news-bed.mp3` is gitignored + excluded from `dist/`.) |
| **Editable source** (Canva/Figma projects) | The design tool / a cloud drive | The repo holds the exported finals, not the working files. |

**Rule of thumb:** if you made it and it's final, commit it here. If someone else
owns it (a license), keep it off GitHub.

## Contents

### `logos/`
The mark is a white tick on the brand navy. Source vector: `assets/logo-mark.svg`.
- `logo-mark-512-on-white.png` — 512², white background (best for light UIs, e.g. Trustpilot)
- `logo-mark-512-transparent.png` — 512², transparent
- `logo-mark-300-transparent.png` — 300², transparent (LinkedIn/Crunchbase min size)
- `logo-mark-300-on-navy.png` — 300², navy background

### `social/`
- `linkedin-personal-banner-1584x396.png` — Alex Bacsa's personal cover (BeatTheScam · SalesTap · CloudFintech · TuningDigital)
- `linkedin-company-banner-1128x191.png` — Beat the Scam Company Page cover ("Check scams. Protect your money.")

## Brand specs (for regenerating)

- **Navy** (backgrounds) `#0a1630` / `#0b1220`
- **Accent blue** `#3a86ff` · **eyebrow blue** `#5e8bef`
- **Orange accent** `#ff7a1a` · **alert red** `#ff5c5c` (video cards)
- **Muted grey** (sub-text) `#8893a8`
- **Typeface:** Arial Bold / Arial (banners); the site uses a system-font stack via CSS
- **Motif:** deep-navy background + subtle grid + a short orange accent bar + a letter-spaced blue eyebrow

The banners/logos were generated with one-off Pillow scripts (see session history);
re-run with the specs above to make new sizes or variants.
