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

2. **Verify Plane is running** at `localhost:80` with backend services healthy:
   ```
   curl -sf http://localhost:80/api/instances/ > /dev/null && echo "Plane OK" || echo "Plane DOWN"
   docker ps --filter "name=plane" --format '{{.Names}}: {{.Status}}'
   ```
   If Plane Docker services are down, start them:
   ```
   cd plane && docker compose up -d
   ```
   Wait up to 45 seconds for services to become healthy before continuing.

3. **Verify Chrome** is running with remote debugging on port 9222:
   ```
   curl -sf http://localhost:9222/json/version > /dev/null && echo "Chrome OK" || echo "Chrome not running"
   ```
   If Chrome is not running, start it:
   ```
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
   Creates a SEED project with work items, states, cycles, modules, and pages.
   Idempotent — safe to run multiple times. Re-run `check` after to verify.

Only proceed to drive.py after `seed.py check` exits 0.

## ⏱ Infrastructure time boundary

If Plane is not healthy after **60 seconds** of checking/waiting, STOP and report:
> "Plane infrastructure not ready. Run setup manually."

Do NOT attempt to debug Docker, edit Caddyfiles, or modify docker-compose.yml.
The `plane-local-fixes` branch contains all required infrastructure fixes.
If something is broken beyond that, it's a human problem.

## Guiding the browser agent with Plane source code

Before running drive.py, you can improve the agent's success rate by reading Plane's source code to find relevant URL patterns and UI structure. For example:
```bash
# Find URL routes for the feature mentioned in the bug
grep -r "states" plane/web/app/ --include="*.tsx" -l | head -10
grep -r "settings" plane/web/helpers/route*.ts 2>/dev/null | head -10
```
This helps you understand where in the app the bug lives, so you can provide better context in the task prompt or verify the agent navigated to the right place.

## What it does

Given a GitHub issue URL, this agent reproduces the bug in a running local Plane instance.
It fetches the issue, drives a browser to execute the reproduction steps, and saves evidence.

```
python scripts/drive.py --issue 9329
python scripts/drive.py --url https://github.com/makeplane/plane/issues/9329
python scripts/drive.py --issue 9329 --dry-run       # prompt only, no agent run
python scripts/drive.py --issue 9329 --timeout 600    # custom timeout
```

The script handles everything: fetch the issue via `gh`, build the prompt, run the browser-use agent, parse the verdict, save artifacts.

Post the reproduction report back to GitHub:
```
python scripts/post_comment.py --issue 9329
python scripts/post_comment.py --issue 9329 --dry-run  # generate file only
```

Exit codes: `0` reproduced, `1` not reproduced, `2` inconclusive, `3` error.

## Identity — Reproducer, NOT Fixer

This agent **reproduces** bugs. It does not fix, patch, or resolve them.

**Allowed verdicts:** `REPRODUCED` · `NOT_REPRODUCED` · `INCONCLUSIVE`
**Never use:** "FIXED", "RESOLVED", or any language implying the agent repaired anything.

## How it works

1. `gh issue view` fetches the issue title + body
2. A generic prompt template injects the issue content + Plane login credentials
3. browser-use agent drives Chrome via CDP to reproduce the steps described in the issue
4. The agent ends with a structured verdict line: `VERDICT: REPRODUCED | <summary>`
5. `drive.py` parses that line, saves all artifacts to `reproductions/<issue-number>/`

## Constraints

- **Any issue.** The prompt is built dynamically from the issue body — no hardcoded steps.
- **Structured verdict.** The agent must end with `VERDICT: REPRODUCED|NOT_REPRODUCED|INCONCLUSIVE | <summary>`. Parsed by regex, not keyword matching.
- **Disk-first.** All artifacts are saved during the run. State survives crashes.
- **Max 50 steps.** The agent has up to 50 browser actions before it must conclude.

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
| `error.txt` | Error details (written on crash/timeout) |
| `github-comment.md` | GitHub comment (generated by `post_comment.py`) |

## Config

All via `.env`:
- `OPENROUTER_API_KEY` — LLM access
- `BROWSER_USE_MODEL` — model (default: `anthropic/claude-sonnet-4`)
- `CDP_URL` — Chrome CDP WebSocket (leave blank for auto-discovery)
- `PLANE_URL` — Plane instance URL (default: `http://localhost:80` via Caddy proxy)
- `PLANE_EMAIL`, `PLANE_PASSWORD`, `PLANE_WORKSPACE`
- `GITHUB_REPO` — default repo for `--issue` (default: `makeplane/plane`)