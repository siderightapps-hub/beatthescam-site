# Search and AI visibility measurement

This process creates a retained monthly snapshot of Google Search discovery and
Bing-powered AI citations, then publishes a smaller normalized dataset at
`/research/`. It measures visibility for Beat the Scam; it does not measure UK
scam incidence, financial loss or population-wide search demand.

## Source systems

- Google Search Console Search Analytics API: final web-search data for two
  equal 28-day windows. The script retrieves totals, queries, pages,
  page/query pairs and daily rows, paginated to the API's 50,000-row daily
  export ceiling.
- Bing Webmaster Tools AI Performance: dashboard CSV exports for Overview,
  Pages and Grounding queries, using both 30-day and three-month ranges. The
  standard Bing Webmaster API does not currently document the AI Performance
  report, so this part of collection is manual.

Official references:

- [Bing AI Performance](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview)
- [Google Search Console bulk export and API limits](https://support.google.com/webmasters/answer/12919192?hl=en)
- [Google Search Console analysis guidance](https://support.google.com/webmasters/answer/17010961?hl=en)

## Monthly runbook

1. In Bing Webmaster Tools, select `beatthescam.com` and open AI Performance.
2. Select 30 days. Download Overview, all Pages and all Grounding queries.
3. Select three months and download those same three files.
4. Add any material release, redirect or consolidation to
   `analytics/search-ai/interventions.json` before collecting the new snapshot.
5. Run the command below, replacing the six export paths and snapshot date:

   ```bash
   python3 scripts/search_ai_measurement.py \
     --snapshot-date YYYY-MM-DD \
     --bing-overview-30 /path/to/overview-30d.csv \
     --bing-pages-30 /path/to/pages-30d.csv \
     --bing-queries-30 /path/to/queries-30d.csv \
     --bing-overview-90 /path/to/overview-3m.csv \
     --bing-pages-90 /path/to/pages-3m.csv \
     --bing-queries-90 /path/to/queries-3m.csv \
     --public-output content/research/uk-scam-search-ai-trends-YYYY-MM.json
   ```

6. Review `analytics/search-ai/YYYY-MM-DD/scorecard.md`, then spot-check the
   normalized totals against both dashboards.
7. Run `python3 scripts/build.py` and `python3 scripts/validate_dist.py`.
8. Publish the build. Submit only genuinely new or materially changed report
   URLs for indexing; the sitemap and `llms.txt` expose every report.

The raw Bing exports and full Search Console snapshot remain internal under the
dated analytics folder. The public report contains equal-period Google totals,
named focus pages and combined redirect clusters, the top 25 Bing pages and
grounding-query sample, plus the complete Bing daily series. No scam-checker
input or personal data is included.

## Interventions and comparison rules

- Record the intervention date and exact focus URLs before evaluating results.
- Use seven days only as an early directional view; use complete, equal 28-day
  windows for the main comparison.
- For a consolidation, add the source and target metrics until the old URL no
  longer appears. Do not call source-to-target movement a gain by itself.
- Prioritize clicks, impressions and CTR. Use average position diagnostically,
  because low-volume query mix can move it sharply.
- Keep Google and Bing periods separately labelled. They should not be forced
  into one artificial common date range.
- Treat a citation as a source appearance, not a ranking, endorsement, visit or
  guarantee of visible placement.
- Treat before-and-after movement as correlation unless a stronger design can
  rule out seasonality, platform changes and unrelated editorial effects.

## July 2026 baseline

The 18 July snapshot is a pre-change baseline for the 18 July editorial release:

- Google final period, 19 June–16 July: 549 impressions, 3 clicks, 0.55% CTR,
  average position 50.7.
- Previous equal period, 22 May–18 June: 555 impressions, 3 clicks, 0.54% CTR,
  average position 36.5.
- Bing AI export, 18 June–16 July: 11,481 citations, 52.9 average cited pages
  per returned day, 97 cited pages and 118 sampled grounding queries.

The first meaningful post-release comparison is the first complete 28-day
window after 18 July. A seven-day check may be recorded sooner but should not be
used for a growth claim.
