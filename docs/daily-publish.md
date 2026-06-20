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
6. It commits and pushes the updated content and dist output.
7. It marks published rows in the queue file (by TOPIC slug).

Validate the gate after any change to content_gate.py: run the "Gate self-test"
GitHub Action (.github/workflows/gate-selftest.yml) or
ANTHROPIC_API_KEY=... python3 scripts/gate_selftest.py

Setup required:
1. Add repository secret ANTHROPIC_API_KEY in GitHub.
2. Copy the workflow and runner files into your repo.
3. Commit and push.
4. Optionally edit batch size in the workflow or use manual workflow_dispatch.
