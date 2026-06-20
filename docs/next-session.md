# Start here next session

> **Last touched:** 2026-06-20 — **Executive Verdict remediation complete & live.** Worked through an external review end-to-end: hardened the content accuracy gate (deterministic absolute-claim check after the LLM judge leaked fabricated stats into a sextortion guide) + cleaned the whole corpus (46 hardcoded org phone numbers, 0/185 fail); checker reporting-link domain allow-list; site-wide search (uses the now-lean `search.json`); de-dangled 53 SEO titles; affiliate cards "Sponsored"→"Recommended" (unpaid); **E-tier:** durable checker rate-limit + `DAILY_CALL_CAP=2000`/day spend cap via Netlify Blobs (first `package.json`), **newsletter → double opt-in**, and **Google certified CMP** for UK/EEA consent (app.js defers to it). All pushed & live, functions smoke-tested. Gate self-test green via the new `Gate self-test` Action. Full detail: `docs/project.md` (Section 20 gotchas 22–24) + memory `e-tier-hardening-pending-push`.
> **✅ Newsletter (double opt-in, LIVE & verified):** capture → **confirmation email** → click → welcome → one-click unsubscribe, all confirmed working. `RESEND_API_KEY` + `RESEND_AUDIENCE_ID` + `UNSUBSCRIBE_SECRET` all set in Netlify (the secret is now **required for signup** and also signs the confirm link).
> **✅ Tier 2 outreach sent** (2026-06-10): Lovemoney, Money to the Masses, This Is Money, MoneyMagpie, Graham Cluley — all logged in [`outreach-log.md`](outreach-log.md). Be Clever With Your Cash = deliberately skipped (auto-spams link asks). **When replies land, log the outcome (✅ live / ✖ declined) in the log.**
> **Next focus:** (1) **monitor + respond to Tier 2 replies** over the next ~1-2 weeks; (2) start **Tier 3 — Featured.com/HARO** (answer ~5 UK scam queries/week → journalist quotes) and the **Reddit/Quora cadence** (templates in [`outreach-templates.md`](outreach-templates.md)); (3) chase AdSense + affiliate hrefs; (4) read the F1 retention number. **For future newsletters:** send as Resend **Broadcasts** + `{{{RESEND_UNSUBSCRIBE_URL}}}` footer token (Resend handles unsubscribe automatically there; the welcome email self-hosts it because that token does NOT work on `/emails`).
> **What you need from yourself:** a Featured.com (HARO) account for Tier 3; otherwise nothing blocking.

This doc is the **fast-start punch list** for the next session — read it before re-opening anything else and you'll be productive in 2 minutes instead of 20.

The exhaustive context lives in `docs/project.md`. This file is the index.

---

## Where things stand (as of last close)

- **Done 2026-06-05→09** (full detail in `project.md` §21): reclaimed the DPD/Yodel/UPS courier guides **plus a 2nd purged batch** (Amazon-call / chargeback / Gumtree / Google-Voice) the AdSense purge had 301'd away; built the **top-3 category hubs** (SMS, Payment, Government pillar pages — `content/category-hubs.json`); fixed GSC auth + added `scripts/gsc_report.py`; reached the cross-platform video verdict (**YouTube Shorts + the site win**); fixed the `shorten_warning` truncation bug; built the **Tier 1 citation/E-E-A-T foundation** (`docs/outreach-log.md`).
- **Newsletter (double opt-in since 2026-06-20):** sitewide email-capture band (above the footer on every page) → `subscribe.js` emails an HMAC-signed confirm link (adds nobody yet) → `confirm-subscribe.js` adds the Resend Audience contact + sends the welcome only on confirm (GET=confirm page, POST=mutate, scanner-safe) → `unsubscribe.js`. All hardened (rate limit, origin allow-list, consent + honeypot). **Routing gotcha:** every `/api/*` rewrite (`subscribe`, `confirm-subscribe`, `unsubscribe`, `csp-report`) lives in `dist/_redirects` (emitted by `build()`), NOT `netlify.toml` — new toml `[[redirects]]` beyond the grandfathered `/api/check-scam` rule are silently ignored at the edge here.
- **Site Health 98%**, **AI Search Health 99%**, Lighthouse mobile 92–97 / SEO 100. Technical build 100% complete; ~191 residual Semrush warnings are Google's AdSense CDN (irreducible).
- **~185 guides** (grows ~1/day via the gated cron), 17 categories, daily publish via GitHub Actions. **Video production discontinued 2026-06-15** (built no authority/backlinks — see `MD Files/BeatTheScam/VideoProductionHandoff.md`).
- **E-E-A-T:** Alex Bacsa named author across all guides + `/author/` page, role standardised to "Founder & Editor" everywhere, `sameAs` to LinkedIn + 3 sister pubs. Disavow file (66 domains), security.txt, llms.txt, full UK Terms all live.

If anything in the above feels stale on re-read, the canonical source is `docs/project.md` Section 21 "Recently completed".

---

## 1. Social analytics review — ✅ DONE (2026-06-07)

> **Verdict reached:** it's platform fit, not a universal hook. YouTube Shorts holds **35%+ retention** (the format works); TikTok ~4s / ~1% (swipe-away); IG/X negligible reach. **YouTube Shorts + the site are the two real channels.** One TikTok creative A/B (`--motion-hook` fade-in reveal) is running on the F1 video — read the retention number ~2026-06-14 to confirm keep-or-drop. Original methodology kept below for reference.

> **Why first:** the data is time-sensitive — the longer videos sit, the less actionable the post-publish retention signals become.

### What to bring to the session

Open these four dashboards in browser tabs **before** opening Claude:

| Platform | Where | What to grab |
|---|---|---|
| **YouTube Shorts** | YouTube Studio → Content → individual Short → Analytics tab | Views, average view duration, % viewed, watch time |
| **TikTok** | TikTok app → profile → Analytics (Pro/Creator account, free) → individual video | Views, average watch time, **completion rate**, full-video views |
| **Instagram Reels** | IG app (mobile) → Reels → Insights on each Reel (Creator account needed — already done) | Plays, **initial plays**, accounts reached, watch time |
| **Twitter / X** | analytics.twitter.com → per-post View analytics (manual — free API tier doesn't expose this) | Impressions, link clicks, engagement rate |

Best videos to pull data on (last ~30 days, sorted oldest first so retention has matured):
- HMRC Tax Rebate (oldest, most data)
- WhatsApp Hi Mum recreate
- Facebook Marketplace
- Festival camping
- The 4 Instagram Reels seeded on 2026-05-30

### The question we're answering

**Does the first-second drop-off problem hold across all three video platforms, or is it platform-specific?**

- If **all three** show heavy < 3s drop-off → it's the hook. We test the alternative openers we parked: kinetic-text reveal, shocking-number open, curiosity-gap question.
- If **Reels holds better than Shorts/TikTok** → it's audience/platform fit. We double down on Reels-first creative.
- If **Twitter is flat (low impressions)** → tweet format is the bottleneck. Test natively attaching the Short to the tweet for reach instead of a bare link.

### Reference docs

- `docs/video-pipeline.md` Section 11 "Cross-platform analytics review" — has the where-to-look + what-to-measure table verbatim
- `docs/video-pipeline.md` Section 10 "Analytics — what's working so far" — the prior baseline (HMRC 210 YT views, FB Marketplace 268 TT, etc.) for comparison

### What to expect from this session's Claude work

After you share the data: a side-by-side comparison table, the retention verdict, and a concrete A/B testing plan for the next 2-3 videos. Not analytics dashboards — diagnosis and next-step planning.

---

## 2. Backlinks & outreach push — Tier 1 ✅ DONE, Tier 2 next

> **Tier 1 (citations/foundation) complete** — see `docs/outreach-log.md`: About.me, Trustpilot, Owler, F6S, LinkedIn personal + company pages all live; Take Five / FAS / Get Safe Online affiliations sent. **Next = Tier 2 link insertions** (the real dofollow lever): pitch the courier/bank-text guides to UK money blogs that already cover these scams. Shortlist + 3 templates ready in `docs/outreach-templates.md`. Original playbook kept below.

> **Why this matters:** Authority Score is **2**. The technical SEO ceiling has been hit. The single biggest growth lever remaining is **earning quality backlinks**, which is pure outreach work that cannot be automated.

### Reference doc

Full playbook is `docs/project.md` Section 14 "Backlinks, Authority & Domain Authority Plan". Read it once before the session.

### What to bring to the session

| Item | Where to get it |
|---|---|
| **Target list** (5-10 UK consumer-finance / fraud-prevention sites) | We'll build this together in the session — bring any sites you already read or admire |
| **HARO / Featured.com account** | Sign up at <https://featured.com/> (free) — takes 2 minutes |
| **Spreadsheet for outreach tracking** | Either your existing Project Tracker (.xlsx) or a fresh sheet — columns: domain, contact name, email, date contacted, response, link earned (Y/N) |
| **Personal email** to send outreach from | The `hello@beatthescam.com` mailbox or a personal address that doesn't go to spam filters |

### Per-week cadence target (Section 14)

| Tactic | Frequency | Target wins/month |
|---|---|---|
| Directory submissions | 5/week × 6 weeks then maintenance | 5–10 links |
| Reddit r/Scams + r/UKPersonalFinance contributions | 3–5/week | 2–4 links (natural mentions) |
| Quora answers | 2/week | 2–4 links |
| Link-insertion outreach (email pitches) | 5–10/week | 1–3 placements |
| Guest post pitches | 3/week | 1 placement/month |
| HARO responses | 5/week | 1–2 quotes/month |

### What to expect from this session's Claude work

We'll:
1. Triage a starter list of **20-30 UK target sites** by relevance and reach-difficulty
2. Draft **3 email templates** (cold outreach, link-insertion, guest-post pitch) you can paste and personalise
3. Pick the first 5 directories to submit to + walk through the submission process
4. Set up the Reddit/Quora cadence with the topical angles you'll lead with
5. Optionally extend `docs/project.md` with an outreach-log section so wins are tracked over time

---

## 3. Smaller items if time allows

Pulled forward from `docs/project.md` Section 21 in priority order. None are blocking.

- [ ] **Semrush Position Tracking** — swap Spain (Spanish) → United Kingdom (English). Dashboard task, 1 minute. The free tier's 1-target limit means delete-then-add (not add-then-delete).
- [x] **Activate mailbox aliases — DONE 2026-06-09.** `abuse@`, `hello@`, `legal@`, `privacy@`, `security@`, `socialmedia@` are all live. Site copy now routes to dedicated inboxes (driven by new `site.json` keys `security_email`/`privacy_email`/`legal_email`): `security.txt` + contact page → `security@`; Privacy Policy + Cookie Policy → `privacy@`; Terms-legal + copyright → `legal@`; general/editorial/corrections stay on `hello@`. About/Terms now names **Alex Bacsa, Founder & Editor** as the editorial decision-maker (was "editorial team").
- [ ] **Confirm Twitter API keys** are stored in GitHub Secrets (not just `.env`) — currently risk-zone if a daily-publish ever fails on a Twitter-keys-missing path.
- [ ] **Video music bed** — `assets/audio/news-bed.mp3` is empty (two candidates rejected). Search YouTube Audio Library Mood=Dark + Genre=Electronic/Cinematic; or Pixabay terms "documentary tension", "investigation", "cybersecurity". Target tone: vigilant, deliberate, investigative — not alarmist.
- [ ] **Top 3 category hub pages** (600–800 words each) — editorial work. Pick the three highest-traffic categories from GSC and expand the existing landing page bodies.
- [ ] **PageSpeed re-check** — confirm the homepage's pre-deploy amber FCP/LCP cleared after the 2026-06-04 preconnect commit landed. URL: <https://pagespeed.web.dev/analysis?url=https%3A%2F%2Fbeatthescam.com%2F>.

---

## How to start the next session in 30 seconds

**Open Claude and paste:**

> Picking up from last session — see `docs/next-session.md`. Today I want to do [analytics review / backlinks kickoff / both]. I have [data ready / questions about X / dashboard tabs open]. Let's go.

That's it. Claude reads this doc first, knows the state, and dives straight into productive work.

---

## What this doc is NOT

- **Not** the canonical reference for site state — that's `docs/project.md` (1400+ lines, full history)
- **Not** the runbook — that's `docs/daily-publish.md` (operational details for the daily pipeline)
- **Not** the video pipeline docs — that's `docs/video-pipeline.md` (full pipeline + analytics methodology)
- **Not** the YouTube setup guide — that's `docs/youtube-upload-setup.md` (one-time OAuth setup)

This doc is **the front door**. Read it, then the others on demand.
