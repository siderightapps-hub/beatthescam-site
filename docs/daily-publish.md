Daily publishing system for Beat the Scam

Files:
- .github/workflows/daily-publish.yml
- scripts/run_daily_publish.py
- content/daily-publish-queue.csv

What it does:
1. Every day at 05:07 UTC, or when triggered manually, GitHub Actions runs.
2. It picks the next unpublished rows from content/daily-publish-queue.csv.
3. It writes those rows into content/topics-claude-template.csv.
4. It runs scripts/generate_content_claude.py in Claude mode with Claude Haiku.
   Each draft must PASS the accuracy gate (scripts/content_gate.py — deterministic
   checks for hardcoded org phone numbers / banned entities / absolute claims, plus
   an LLM judge) before publish; failures are quarantined, never shipped.
5. It rebuilds the site.
6. Human-review gate (since 2026-06-25): it does NOT commit or push to main.
   It opens a review pull request (branch auto/daily-publish-<date>-<run_id>,
   label auto-content) containing the new content and rebuilt dist/. Nothing
   publishes, gets ads, or is tweeted until the operator merges the PR — this
   satisfies Google's policy that auto-generated content must be reviewed
   before it carries ads.
7. On merge, a separate workflow (.github/workflows/tweet-on-publish.yml) tweets
   the slug(s) added by that push (diff-based, capped at 3, deduped via
   content/tweeted_posts.json) — tweeting is no longer part of this workflow.
8. It marks published rows in the queue file (by TOPIC slug) once the PR merges.

The sibling cron .github/workflows/daily-search-console.yml (05:23 UTC) runs the
same generate -> gate -> review-PR flow, filling Search Console content gaps
instead of working the queue.

Validate the gate after any change to content_gate.py: run the "Gate self-test"
GitHub Action (.github/workflows/gate-selftest.yml) or
ANTHROPIC_API_KEY=... python3 scripts/gate_selftest.py

Setup required:
1. Add repository secret ANTHROPIC_API_KEY in GitHub.
2. Enable "Allow GitHub Actions to create and approve pull requests"
   (Settings -> Actions -> General) so the workflow can open its review PR.
3. Copy the workflow and runner files into your repo.
4. Commit and push.
5. Optionally edit batch size in the workflow or use manual workflow_dispatch.
