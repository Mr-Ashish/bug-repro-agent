---
name: repro-agent
description: "Reproduce any Plane bug from a GitHub issue URL. Drives a real browser, emits evidence + verdict."
---

# repro-agent

## Before running

Pre-flight checklist — run in this exact order:

1. **Sync Plane to latest code:**
   ```
   cd plane && git pull --rebase origin preview && git merge plane-local-fixes --no-edit && cd ..
   ```
   This ensures we run against the latest Plane code with our local infrastructure fixes applied.

2. **Verify Plane is running** (URL from `.env` `PLANE_URL`, default in `scripts/drive.py`):
   ```bash
   # Read PLANE_URL from .env, fall back to drive.py default
   PLANE_URL=$(grep PLANE_URL .env 2>/dev/null | cut -d= -f2 || python3 -c "import scripts.drive as d; print(d.PLANE_URL)")
   curl -sf ${PLANE_URL}/api/instances/ > /dev/null && echo "Plane OK" || echo "Plane DOWN"
   docker ps --filter "name=plane" --format '{{.Names}}: {{.Status}}'
   ```
   If Plane Docker services are down, start them:
   ```
   cd plane && docker compose up -d
   ```
   Wait up to 45 seconds for services to become healthy before continuing.

3. **Verify Chrome** is running with remote debugging (port from `scripts/drive.py` `discover_cdp_url()`):
   ```bash
   curl -sf http://localhost:9222/json/version > /dev/null && echo "Chrome OK" || echo "Chrome not running"
   ```
   If Chrome is not running, start it:
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --start-maximized
   ```

4. **Check infrastructure + seed data:**
   ```
   python scripts/seed.py check
   ```
   Exit code 0 = ready. Exit code 1 = not ready (read the output to see what's missing).

5. **Populate seed data (if check fails):**
   ```
   python scripts/seed.py populate
   ```
   Creates seed data defined in `scripts/seed.py` (`SEED_STATES` and `SEED_ISSUES` lists).
   Idempotent — safe to run multiple times. Re-run `check` after to verify.

Only proceed to drive.py after `seed.py check` exits 0.

## ⏱ Infrastructure time boundary

If Plane is not healthy after **60 seconds** of checking/waiting, STOP and report:
> "Plane infrastructure not ready. Run setup manually."

Do NOT attempt to debug Docker, edit Caddyfiles, or modify docker-compose.yml.
The `plane-local-fixes` branch contains all required infrastructure fixes.
If something is broken beyond that, it's a human problem.

## Guiding the browser agent with Plane source code

Before running drive.py, read Plane's source code to discover context that helps the browser agent navigate faster. **Then pass it via `--context`.**

**Important:** Plane's web app is at `plane/apps/web/`, NOT `plane/web/`. Always use the `apps/` prefix.

### Step 1: Discover context from Plane source

Read the issue first, identify the feature area, then grep for relevant code:

```bash
# Find URL routes for the feature mentioned in the bug
# Replace <feature> with the area from the issue (e.g., cycles, modules, pages, issues)
find plane/apps/web/app -type d -name "<feature>" 2>/dev/null
grep -r "<feature>" plane/apps/web/app/ --include="*.tsx" -l | head -10

# Find component names, selectors, data-testid attributes
grep -r "data-testid" plane/apps/web/app/ --include="*.tsx" | head -10
```

### Step 2: Pass context to the browser agent

Use `--context` to inject your discoveries into the browser agent's prompt:

```bash
# Inline context string (adapt to whatever the bug is about)
python scripts/drive.py --url https://github.com/makeplane/plane/issues/<N> --post \
  --context "Feature URL: /$PLANE_WORKSPACE/projects/<project-id>/<feature-path>/
Key UI element is behind a ⋯ dropdown.
Component: plane/apps/web/app/.../<feature>/page.tsx"

# Or write context to a file first, then pass the path
python scripts/drive.py --url https://github.com/makeplane/plane/issues/<N> --post \
  --context reproductions/<N>/context.txt
```

### What to include in context

Good context = fewer wasted browser steps. Focus on:
- **URL patterns**: Direct URLs the agent can navigate to (derived from the issue's feature area)
- **UI structure**: Where buttons/menus/dropdowns live
- **Component names**: Helps the agent identify the right part of the page
- **Data attributes**: `data-testid` values the agent can target
- **API endpoints**: Relevant REST endpoints the feature uses

## What it does

Given a GitHub issue URL, this agent reproduces the bug in a running local Plane instance.
The full pipeline: **fetch → reproduce → generate Playwright test → post to GitHub**.

```bash
# Standard run (reproduce + generate Playwright test)
python scripts/drive.py --url https://github.com/makeplane/plane/issues/<N>

# Full E2E (reproduce + Playwright test + post verdict to GitHub issue)
python scripts/drive.py --url https://github.com/makeplane/plane/issues/<N> --post

# Full E2E with source-code context (best results — adapt context to the bug's feature area)
python scripts/drive.py --url https://github.com/makeplane/plane/issues/<N> --post \
  --context "Feature URL: /$PLANE_WORKSPACE/projects/<id>/<relevant-path>/"

# Other options
python scripts/drive.py --issue <N> --dry-run          # prompt only, no agent run
python scripts/drive.py --issue <N> --timeout 600      # custom timeout
```

**Always use `--post` for demo runs** so the verdict appears directly on the GitHub issue.

After drive.py completes, review the generated Playwright test:
```bash
# The test is auto-generated at reproductions/<N>/test_<N>.py
cat reproductions/<N>/test_<N>.py

# Run it (selectors may need refinement for full replay)
pytest reproductions/<N>/test_<N>.py -v --headed
```

Exit codes: `0` reproduced, `1` not reproduced, `2` inconclusive, `3` error.

## Retry loop (max 3 attempts)

If the verdict is `INCONCLUSIVE` or `NOT_REPRODUCED`, **read the artifacts before giving up**:

1. Read `reproductions/<N>/action-log.json` — check for steps with `"error"` fields or empty `"actions"`
2. Read `reproductions/<N>/verdict.md` — read the agent's own explanation of what happened
3. Diagnose: wrong page/view? missed a UI element? timed out? Pydantic errors?
4. Write an improved `reproductions/<N>/context.txt` that fixes the gap (e.g. "Switch to List view first", "Click the ⋯ menu, not the title")
5. Rerun with `--context reproductions/<N>/context.txt`

Stop retrying when: verdict is `REPRODUCED`, or you've hit 3 attempts, or the same failure repeats with no new information.

**Only use `--post` on the final attempt** so the GitHub issue gets one clean comment, not three.

## Identity — Reproducer, NOT Fixer

This agent **reproduces** bugs. It does not fix, patch, or resolve them.

**Allowed verdicts:** `REPRODUCED` · `NOT_REPRODUCED` · `INCONCLUSIVE`
**Never use:** "FIXED", "RESOLVED", or any language implying the agent repaired anything.

## How it works

1. `gh issue view` fetches the issue title + body
2. A principles-based prompt template injects the issue content + Plane login credentials
3. browser-use agent drives Chrome via CDP to reproduce the steps described in the issue
4. The agent ends with a structured verdict line: `VERDICT: REPRODUCED | <summary>`
5. `drive.py` parses that line, saves all artifacts to `reproductions/<issue-number>/`
6. A Playwright regression test is auto-generated from the action log
7. With `--post`, the verdict is posted as a comment on the GitHub issue

## Constraints

- **Any issue.** The prompt is built dynamically from the issue body — no hardcoded steps.
- **Structured verdict.** The agent must end with `VERDICT: REPRODUCED|NOT_REPRODUCED|INCONCLUSIVE | <summary>`. Parsed by regex, not keyword matching.
- **Disk-first.** All artifacts are saved during the run. State survives crashes.
- **Step budget.** The agent has a max step limit (see `max_steps` in `scripts/drive.py`) before it must conclude.

## Artifacts

All output goes to `reproductions/<issue-number>/`:

| File | What |
|------|------|
| `issue.json` | Fetched issue (title, body, URL) |
| `task-prompt.txt` | Full prompt sent to agent |
| `action-log.json` | Every agent step (thought, actions, result, URL) |
| `evidence-*.png` | Screenshots at each step |
| `agent-run.gif` | Animated GIF of the session |
| `conversation.json` | Full LLM conversation |
| `traces/full-trace.json` | Complete browser-use agent history |
| `verdict.md` | Parsed verdict + agent result + run stats |
| `test_<N>.py` | Auto-generated Playwright regression test |
| `error.txt` | Error details (written on crash/timeout) |
| `github-comment.md` | GitHub comment (generated by `post_comment.py`) |

## Config

All via `.env`. Defaults are in `scripts/drive.py`. See `CLAUDE.md` → "Configuration source of truth" for the full reference table.

- `OPENROUTER_API_KEY` — LLM access
- `BROWSER_USE_MODEL` — model (see `scripts/drive.py` `MODEL` default)
- `CDP_URL` — Chrome CDP WebSocket (leave blank — auto-discovered by `discover_cdp_url()`)
- `PLANE_URL` — Plane instance URL (see `scripts/drive.py` `PLANE_URL` default)
- `PLANE_EMAIL`, `PLANE_PASSWORD`, `PLANE_WORKSPACE`
- `GITHUB_REPO` — default repo (see `scripts/drive.py` `DEFAULT_REPO`)