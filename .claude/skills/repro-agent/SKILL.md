---
name: repro-agent
description: "Reproduce any Plane bug from a GitHub issue URL. Drives a real browser, emits evidence + verdict."
---

# repro-agent

## Before running — bring up the full stack

Run these steps in order. Each step must succeed before moving to the next.

### 1. Start Plane services

**Use `docker-compose.yml` (NOT `docker-compose-local.yml`).** The local compose file only has backend services — no web frontend, no Caddy proxy, and the API image is missing `debug_toolbar`. The full compose file has all 13 services including Caddy on port 80 which unifies frontend and API.

```bash
cd plane && docker compose -f docker-compose.yml up -d
```

Wait for the API to be ready (migrator needs ~30-60s on first run):
```bash
echo "Waiting for API..." && until curl -s http://localhost:80/api/instances/ > /dev/null 2>&1; do sleep 3; done && echo "API ready!"
```

If services aren't healthy after 90 seconds, stop. Don't debug Docker or Caddyfiles — that's a human problem.

### 2. Register admin + create workspace (fresh install only)

Check if the instance needs first-time setup:
```bash
curl -s http://localhost:80/api/instances/ 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('needs_setup:', not d.get('is_setup_done', False))"
```

If `needs_setup: True`, run the setup from `plane/SETUP_REFERENCE.md` — steps 6-8 (register admin, sign in, create workspace). The key commands:

```bash
# Register instance admin
rm -f /tmp/plane-cookies.txt
curl -s -c /tmp/plane-cookies.txt http://localhost:80/auth/get-csrf-token/ > /dev/null
CSRF=$(grep csrftoken /tmp/plane-cookies.txt | awk '{print $NF}')
curl -s -o /dev/null -w "Admin signup: HTTP %{http_code}\n" \
  -b /tmp/plane-cookies.txt -c /tmp/plane-cookies.txt \
  -H "Referer: http://localhost/god-mode/" \
  -d "csrfmiddlewaretoken=${CSRF}" \
  -d "first_name=admin" -d "last_name=admin" \
  -d "email=admin@admin.com" -d "company_name=admin" \
  --data-urlencode "password=qweQWE123!@#" \
  -d "is_telemetry_enabled=True" \
  "http://localhost:80/api/instances/admins/sign-up/"

# Sign in
rm -f /tmp/plane-session.txt
curl -s -c /tmp/plane-session.txt http://localhost:80/auth/get-csrf-token/ > /dev/null
CSRF=$(grep csrftoken /tmp/plane-session.txt | awk '{print $NF}')
curl -s -o /dev/null -w "Sign-in: HTTP %{http_code}\n" \
  -b /tmp/plane-session.txt -c /tmp/plane-session.txt \
  -H "Referer: http://localhost/" \
  -d "csrfmiddlewaretoken=${CSRF}" \
  -d "email=admin@admin.com" \
  --data-urlencode "password=qweQWE123!@#" \
  -d "medium=email" \
  "http://localhost:80/auth/sign-in/"

# Create workspace
curl -s -b /tmp/plane-session.txt \
  -H "Content-Type: application/json" \
  -d '{"name": "Plane Dev", "slug": "plane-dev", "organization_size": "1-10"}' \
  "http://localhost:80/api/workspaces/"
```

### 3. Chrome has remote debugging — port 9222

```bash
curl -s http://localhost:9222/json/version | python3 -c "import sys,json; print(json.load(sys.stdin)['webSocketDebuggerUrl'])"
```

### 4. Seed data exists

```bash
python scripts/seed.py check
```

If exit code 1, populate:
```bash
python scripts/seed.py populate
```

## Context for the browser agent

Before running drive.py, read Plane source to find navigation context that saves the browser agent steps. Plane's web app is at `plane/apps/web/`, NOT `plane/web/`.

Look for: URL routes, `data-testid` attributes, component names, UI structure (dropdowns, menus), relevant API endpoints.

Pass discoveries via `--context` (inline string or file path to `reproductions/<N>/context.txt`).

## What it does

Given a GitHub issue URL, this agent reproduces the bug in a running local Plane instance.
The full pipeline: **fetch → reproduce → generate Playwright test → post to GitHub**.

```bash
# Standard run — always use --post so the verdict is reported on the GitHub issue
python scripts/drive.py --url https://github.com/makeplane/plane/issues/<N> --post

# With source-code context (best results)
python scripts/drive.py --url https://github.com/makeplane/plane/issues/<N> --post \
  --context "Feature URL: /$PLANE_WORKSPACE/projects/<id>/<relevant-path>/"

# Other options
python scripts/drive.py --issue <N> --dry-run          # prompt only, no agent run
python scripts/drive.py --issue <N> --timeout 600      # custom timeout
```

**Always use `--post`.** The job isn't done until the verdict is posted to the GitHub issue.

`drive.py` automatically generates AND runs the Playwright test. Check its output for pass/fail. If the test fails with selector errors, that's expected — the auto-generated selectors use element indices, not stable selectors.

Exit codes: `0` reproduced, `1` not reproduced, `2` inconclusive, `3` error.

## After drive.py completes — verify ALL artifacts and actions

This is mandatory. Do NOT skip any step.

### 1. Check artifacts exist

```bash
ls reproductions/<N>/verdict.md         # must exist — the verdict
ls reproductions/<N>/action-log.json    # must exist — step traces
ls reproductions/<N>/test_<N>.py        # must exist — Playwright regression test
ls reproductions/<N>/github-comment.md  # must exist — posted to GitHub
ls reproductions/<N>/agent-run.gif      # should exist — GIF of browser session
ls reproductions/<N>/evidence-*.png     # should exist — screenshots
```

If any of `verdict.md`, `action-log.json`, `test_<N>.py`, or `github-comment.md` is missing, the run is incomplete. Check drive.py output for errors, fix, and rerun.

### 2. Run the Playwright test independently

drive.py generates and attempts to run the test, but it may fail silently. Always run it yourself:

```bash
pytest reproductions/<N>/test_<N>.py -v
```

Selector-based failures are expected (auto-generated selectors use element indices). Report pass/fail in your summary.

### 3. Verify the GitHub comment was posted

```bash
gh issue view <N> --repo makeplane/plane --json comments --jq '.comments[-1].body' | head -5
```

Confirm the latest comment is the reproduction report, not a stale one.

## Retry loop

If the verdict is not `REPRODUCED`, read the artifacts in `reproductions/<N>/` (action-log, verdict, screenshots), diagnose what went wrong, improve the `--context`, and rerun with `--post`. Max 3 attempts.

## Identity — Reproducer, NOT Fixer

This agent **reproduces** bugs. It does not fix, patch, or resolve them.

**Allowed verdicts:** `REPRODUCED` · `NOT_REPRODUCED` · `INCONCLUSIVE`
**Never use:** "FIXED", "RESOLVED", or any language implying the agent repaired anything.

## Constraints

- **Any issue.** The prompt is built dynamically from the issue body — no hardcoded steps.
- **Structured verdict.** The agent must end with `VERDICT: REPRODUCED|NOT_REPRODUCED|INCONCLUSIVE | <summary>`. Parsed by regex, not keyword matching.
- **Disk-first.** All artifacts are saved during the run. State survives crashes.
- **Step budget.** The agent has a max step limit (see `max_steps` in `scripts/drive.py`) before it must conclude.

Artifacts go to `reproductions/<issue-number>/`. Config is in `.env` with defaults in `scripts/drive.py`. See ARCHITECTURE.md and README.md for full details.