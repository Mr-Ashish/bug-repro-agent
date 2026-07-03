---
name: repro-agent
description: "Reproduce any Plane bug from a GitHub issue URL. Drives a real browser, emits evidence + verdict."
---

# repro-agent

## What it does

Given a GitHub issue URL, this agent reproduces the bug in a running local Plane instance.
It fetches the issue, drives a browser to execute the reproduction steps, and saves evidence.

```
python scripts/drive.py --issue 9329
python scripts/drive.py --url https://github.com/makeplane/plane/issues/9329
```

The script handles everything: fetch the issue via `gh`, build the prompt, run the browser-use agent, parse the verdict, save artifacts.

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
| `action-log.json` | Every agent step (thought, actions, result, URL) |
| `evidence-*.png` | Screenshots at each step |
| `agent-run.gif` | Animated GIF of the session |
| `conversation.json` | Full LLM conversation |
| `traces/full-trace.json` | Complete browser-use agent history |
| `verdict.md` | Parsed verdict + agent result + run stats |

## Config

All via `.env`:
- `OPENROUTER_API_KEY` — LLM access
- `BROWSER_USE_MODEL` — model (default: `anthropic/claude-sonnet-4`)
- `CDP_URL` — Chrome CDP WebSocket
- `PLANE_URL`, `PLANE_EMAIL`, `PLANE_PASSWORD`, `PLANE_WORKSPACE`
- `GITHUB_REPO` — default repo for `--issue` (default: `makeplane/plane`)