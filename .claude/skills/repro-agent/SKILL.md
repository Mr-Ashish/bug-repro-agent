---
name: repro-agent
description: "Reproduce any Plane bug from a GitHub issue URL. Drives a real browser, emits evidence + verdict."
---

# repro-agent

## Before running

Ensure three things before calling drive.py:
1. **Plane is running** — Docker services up, frontend and API responding at `PLANE_URL` (from `.env`, default in `scripts/drive.py`)
2. **Chrome has remote debugging** — port 9222
3. **Seed data exists** — `python scripts/seed.py check` exits 0. If not, run `python scripts/seed.py populate`.

Sync Plane to latest code first: pull `preview`, merge `plane-local-fixes`.

If Plane isn't healthy after 60 seconds, stop. Don't debug Docker or Caddyfiles — that's a human problem.

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

## After drive.py completes — verify ALL artifacts

This is mandatory. Check that every artifact was generated:

```bash
ls reproductions/<N>/verdict.md         # must exist — the verdict
ls reproductions/<N>/action-log.json    # must exist — step traces
ls reproductions/<N>/test_<N>.py        # must exist — Playwright regression test
ls reproductions/<N>/github-comment.md  # must exist — posted to GitHub
ls reproductions/<N>/agent-run.gif      # should exist — GIF of browser session
ls reproductions/<N>/evidence-*.png     # should exist — screenshots
```

If any of `verdict.md`, `action-log.json`, `test_<N>.py`, or `github-comment.md` is missing, the run is incomplete. Check drive.py output for errors, fix, and rerun.

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