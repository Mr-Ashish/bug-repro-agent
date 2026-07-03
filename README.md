# repro-agent

Point a browser agent at any GitHub issue. Watch it reproduce the bug — live.

Built for the **Browser-Use Hackathon** (July 4, 2026, Bengaluru).

## What it does

```bash
python scripts/drive.py --issue 9329
python scripts/drive.py --url https://github.com/makeplane/plane/issues/5432
```

1. **Fetches** the GitHub issue via `gh` CLI
2. **Builds** a task prompt from the issue body (no hardcoded steps)
3. **Drives** the browser via [browser-use](https://github.com/browser-use/browser-use) to reproduce the bug
4. **Parses** the agent's structured verdict: `VERDICT: REPRODUCED | <summary>`
5. **Saves** evidence: screenshots, action log, GIF, video, full trace
6. **Reports** (optional): posts a rich reproduction report back to the GitHub issue

Works on **any** Plane issue — not just pre-selected ones.

## Architecture

```
Fetch:  gh issue view → issue title + body
Prompt: generic template + issue body + Plane credentials
Agent:  browser-use (Python) → Claude Sonnet 4 via OpenRouter → Chrome CDP
Target: Plane (local docker-compose)
Output: reproductions/<issue-number>/ (verdict, screenshots, traces)
```

**One script does everything:** `scripts/drive.py` fetches, prompts, drives, parses, saves.

## Output

```
reproductions/9329/
├── issue.json               # fetched issue (title, body, URL)
├── task-prompt.txt           # full prompt sent to agent
├── action-log.json          # every agent step (thought, actions, result)
├── evidence-*.png           # screenshots at each step
├── agent-run.gif            # animated GIF of browser session
├── conversation.json        # full LLM conversation
├── verdict.md               # parsed verdict + agent result + run stats
├── error.txt                # error details (on crash/timeout)
├── github-comment.md        # GitHub comment (from post_comment.py)
└── traces/
    └── full-trace.json      # complete browser-use agent history
```

## Prerequisites

- [Plane](https://github.com/makeplane/plane) running locally on `:3000`
- Chrome with `--remote-debugging-port=9222`
- Python 3.11+
- OpenRouter API key
- `gh` CLI authenticated

## Setup

```bash
pip install browser-use python-dotenv
cp .env.example .env                 # add OPENROUTER_API_KEY
```

> **Note:** CDP_URL is auto-discovered from Chrome on port 9222. You only need to set it manually if Chrome is on a different port.

## Usage

```bash
# By issue number (uses GITHUB_REPO from .env, default: makeplane/plane)
python scripts/drive.py --issue 9329

# By full URL (auto-detects repo)
python scripts/drive.py --url https://github.com/makeplane/plane/issues/9050

# Specify a different repo
python scripts/drive.py --issue 42 --repo someorg/somerepo

# Dry run — generate prompt without running agent (saves API cost)
python scripts/drive.py --issue 9329 --dry-run

# Custom timeout (default: 300s)
python scripts/drive.py --issue 9329 --timeout 600
```

### Post reproduction report to GitHub

```bash
# After a successful drive run, post a comment to the issue
python scripts/post_comment.py --issue 9329

# Dry run — generate comment file without posting
python scripts/post_comment.py --issue 9329 --dry-run
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Bug reproduced |
| 1 | Bug not reproduced |
| 2 | Inconclusive |
| 3 | Error |

## Verdict protocol

The agent is instructed to end with a structured verdict line:

```
VERDICT: REPRODUCED | The 256-char title showed "Some error occurred" instead of a descriptive message
VERDICT: NOT_REPRODUCED | The feature worked correctly — descriptive error was shown
VERDICT: INCONCLUSIVE | Could not find the stickies section in the UI
```

`drive.py` parses this with a regex — no per-issue keyword matching needed.

## Design

**Identity:** This agent is a **reproducer**, not a fixer.
Allowed verdicts: `REPRODUCED` · `NOT_REPRODUCED` · `INCONCLUSIVE`

**Prompt:** One generic template works for all issues. The issue body IS the reproduction plan — the LLM figures out the steps.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system design, UML sequence diagram, and layer ownership.

## License

MIT