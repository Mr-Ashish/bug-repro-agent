# repro-agent

Point a browser agent at any GitHub issue. Watch it reproduce the bug — live.

Built for the **Browser-Use Hackathon** (July 4, 2026, Bengaluru).

## What it does

```bash
python scripts/drive.py --url https://github.com/makeplane/plane/issues/9329 --post
```

1. **Fetches** the GitHub issue via `gh` CLI
2. **Builds** a task prompt from the issue body (no hardcoded steps)
3. **Drives** the browser via [browser-use](https://github.com/browser-use/browser-use) to reproduce the bug
4. **Parses** the agent's structured verdict: `VERDICT: REPRODUCED | <summary>`
5. **Saves** evidence: screenshots, action log, GIF, video, full trace
6. **Reports** a rich reproduction report back to the GitHub issue (with `--post`)

Works on **any** Plane issue — not just pre-selected ones.

## Architecture

```
Human → Grok (meta-agent, reads SKILL.md) → drive.py (infra) → browser-use Agent (bug reasoning)
```

```
Fetch:   gh issue view → issue title + body
Prompt:  generic template + issue body + Plane credentials + source-code context
Agent:   browser-use (Python) → Claude Sonnet 4 via OpenRouter → Chrome CDP
Target:  Plane (local docker-compose via Caddy — URL from .env PLANE_URL, default in scripts/drive.py)
Output:  reproductions/<issue-number>/ (verdict, screenshots, traces, HTML report)
```

**One script does everything:** `scripts/drive.py` fetches, prompts, drives, parses, saves, and posts.

## Output

```
reproductions/<N>/
├── issue.json               # fetched issue (title, body, URL)
├── task-prompt.txt           # full prompt sent to agent
├── action-log.json          # every agent step (thought, actions, result)
├── evidence-*.png           # screenshots at each step
├── agent-run.gif            # animated GIF of browser session
├── conversation.json        # full LLM conversation
├── verdict.md               # parsed verdict + agent result + run stats
├── report.html              # self-contained HTML report
├── github-comment.md        # GitHub comment (with --post)
├── error.txt                # error details (on crash/timeout)
└── traces/
    └── full-trace.json      # complete browser-use agent history
```

## Prerequisites

- [Plane](https://github.com/makeplane/plane) running locally (port from `.env` `PLANE_URL`, default in `scripts/drive.py`)
- Chrome with `--remote-debugging-port=9222`
- Python 3.11+
- OpenRouter API key
- `gh` CLI authenticated

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env                 # add OPENROUTER_API_KEY
```

> **Note:** CDP_URL is auto-discovered from Chrome on port 9222. You only need to set it manually if Chrome is on a different port.

## Pre-run environment check

Before running the agent, verify Plane is up and has seed data:

```bash
# Check if Plane is ready (auth, workspace, projects, states, work items)
python scripts/seed.py check

# If check fails — populate seed data (idempotent, safe to re-run)
python scripts/seed.py populate
```

`seed.py check` exits 0 when ready, 1 when not. `seed.py populate` creates:
- **SEED project** with identifier `SEED`
- **5 states** (Backlog, Todo, In Progress, Done, Cancelled)
- **5 work items** including edge cases (256-char title, special characters, hierarchy parent)

## Usage

```bash
# Full E2E — reproduce + post verdict to GitHub
python scripts/drive.py --url https://github.com/makeplane/plane/issues/9329 --post

# With source-code context from the meta-agent (best results)
python scripts/drive.py --url https://github.com/makeplane/plane/issues/9329 --post \
  --context "Feature URL: /$PLANE_WORKSPACE/projects/<id>/issues/"

# By issue number (uses GITHUB_REPO from .env, default: makeplane/plane)
python scripts/drive.py --issue 9329 --post

# Dry run — generate prompt without running agent (saves API cost)
python scripts/drive.py --issue 9329 --dry-run

# Custom timeout (default: 300s)
python scripts/drive.py --issue 9329 --timeout 600
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Bug reproduced |
| 1 | Bug not reproduced |
| 2 | Inconclusive |
| 3 | Error |

## Verdict protocol

The agent ends with a structured verdict line:

```
VERDICT: REPRODUCED | <what was observed>
VERDICT: NOT_REPRODUCED | <the feature worked correctly>
VERDICT: INCONCLUSIVE | <why it couldn't be determined>
```

`drive.py` parses this with a regex — no per-issue keyword matching needed.

## Design

**Identity:** This agent is a **reproducer**, not a fixer.
Allowed verdicts: `REPRODUCED` · `NOT_REPRODUCED` · `INCONCLUSIVE`

**Prompt:** One generic template works for all issues. The issue body IS the reproduction plan — the LLM figures out the steps.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system design.

## License

MIT