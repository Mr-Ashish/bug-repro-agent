# HLD — Bug Reproduction Agent

> **Hackathon:** Browser-Use Hackathon, July 4 2026, Bengaluru
> **Target app:** [Plane](https://github.com/makeplane/plane) (makeplane) — open-source project management
> **One-liner:** Given a GitHub issue URL, autonomously reproduces the bug in a running local Plane instance using browser-use (Python) for browser automation, and emits evidence artifacts (screenshots, action log, verdict, traces).

---

## Identity — Reproducer, NOT Fixer

This agent is a **bug reproducer**. It does not fix, patch, or resolve bugs. It attempts to reproduce a reported issue and reports the outcome.

**Allowed verdicts:**

| Verdict | Meaning |
|---------|---------|
| **REPRODUCED** | The reported bug behavior was observed |
| **NOT REPRODUCED** | The reported bug behavior was NOT observed — the feature worked correctly |
| **INCONCLUSIVE** | Evidence was ambiguous; cannot confirm or deny the bug |

**Never use:** "FIXED", "BUG APPEARS FIXED", "RESOLVED", "PATCHED", or any language that implies the agent repaired anything. The agent observes and reports — it does not judge whether something was fixed, only whether the reported bug behavior was or was not observed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  /repro <github-issue-url>                                  │
│  ═══════════════════════════                                │
│                                                             │
│  Grok Skill (.claude/skills/repro-agent/SKILL.md)           │
│  Internally uses /loop for autonomous execution             │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  python scripts/drive.py --issue <N>                  │  │
│  │                                                       │  │
│  │  1. gh issue view → fetch title + body                │  │
│  │  2. Build prompt (generic template + issue body)      │  │
│  │  3. browser-use Agent → drive Chrome via CDP          │  │
│  │  4. Parse verdict: REPRODUCED / NOT / INCONCLUSIVE    │  │
│  │  5. Save artifacts to reproductions/<N>/              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
          │                              │
          ▼                              ▼
┌──────────────────┐          ┌──────────────────────┐
│  browser-use      │          │  Plane (local)        │
│  (Python, in-proc)│          │  docker-compose       │
│  No server needed │  ─────→  │  localhost:3000        │
│                   │  CDP     │                        │
│  Model: Claude    │          │  Next.js + Django +    │
│  Sonnet 4         │          │  Postgres + Redis +    │
│  (via OpenRouter)  │          │  RabbitMQ + MinIO      │
└──────────────────┘          └──────────────────────┘
```

---

## How `drive.py` Works

One script does everything. No multi-phase orchestration.

```
python scripts/drive.py --issue 9329

    1. gh issue view 9329 → title + body
    2. Generic prompt template + issue body + Plane creds → task
    3. browser-use Agent(task=...) → Chrome CDP → Plane
    4. Agent ends with: VERDICT: REPRODUCED | <summary>
    5. Parse verdict, save all artifacts to reproductions/9329/
```

---

## How It Works

### 1. Fetch

`gh issue view <N> --repo makeplane/plane --json title,body,url,number`

Gets the issue title and body. No manual input needed — the issue IS the reproduction plan.

### 2. Build prompt

A generic template injects the issue body + Plane credentials. The LLM reads the bug report and figures out its own steps. No hardcoded per-issue logic.

### 3. Drive

browser-use `Agent(task=prompt, llm=...).run()` drives Chrome via CDP. The agent logs in, navigates, executes steps, observes results. Max 50 steps.

### 4. Verdict

The prompt instructs the agent to end with a structured line:
```
VERDICT: REPRODUCED | <one-line summary>
VERDICT: NOT_REPRODUCED | <one-line summary>
VERDICT: INCONCLUSIVE | <one-line summary>
```
`drive.py` parses this with a regex. No per-issue keyword matching.

### 5. Save

All artifacts saved to `reproductions/<issue-number>/`: screenshots, action log, verdict, traces, GIF, video.

### Exit Conditions

| Condition | What happens |
|-----------|-------------|
| ✅ Agent emits `VERDICT: REPRODUCED` | Artifacts saved, exit success |
| ❌ Agent emits `NOT_REPRODUCED` or `INCONCLUSIVE` | Artifacts saved, exit |
| 🚨 browser-use/Plane crash | Exit with error report |
| 📊 50 steps exhausted | Agent must conclude with whatever evidence it has |

---

## Roles

| Role | Who |
|------|-----|
| **Driver script** | `scripts/drive.py` — fetches, prompts, runs, saves |
| **Browser agent** | browser-use Agent (Claude Sonnet 4 via OpenRouter) — drives Chrome |
| **Target app** | Plane (local docker-compose on `:3000`) |

---

## browser-use Integration

| Property | Value |
|----------|-------|
| Library | `browser-use` (Python, `pip install browser-use`) |
| Model | Claude Sonnet 4 via OpenRouter (`ChatOpenAI` with OpenRouter base_url) |
| Connection | CDP to existing Chrome (`ws://localhost:9222/...`) |
| Driver | `scripts/drive.py --issue <N>` or `--url <github-url>` |
| Operations | Single `Agent(task=..., llm=...).run()` — agent handles all navigation/actions |
| Built-in | Screenshots, GIF generation, conversation saving, video recording |
| Traces | `history.save_to_file()` → `reproductions/<issue>/traces/full-trace.json` |

**Principle:** browser-use resolves NL task → DOM actions via built-in Playwright. No separate server process. All strategy lives in the task prompt and Claude Code.

---

## Plane Knowledge

Configured via `.env` and injected into the prompt by `drive.py`:

| Knowledge | Value |
|-----------|-------|
| Base URL | `http://localhost:3000` |
| Login | `admin@admin.com` / `qweQWE123!@#` |
| Workspace | `plane-dev` |
| Project | SEED (Seed Demo Project) |
| Nav pattern | `/plane-dev/projects/<id>/issues/` |
| API base | `/api/v1/workspaces/plane-dev/` |
| Auth flow | Email + password login page |
| Existing data | 30 issues, 5 states, 3 cycles, 4 modules, 5 pages, sub-issues |

---

## Demo Bugs (Hackathon Examples)

The agent works on any Plane issue. These are good demos because they're visual and fast:

| # | Bug | Bug Class |
|---|-----|-----------|
| **9329** | 255+ char title shows generic error | form-validation |
| **9050** | Deleted stickies reappear on reload | state-persistence |
| **9124** | Sub-task expand requires 3 clicks | ui-interaction |

---

## File Structure

```
bug-repro-agent/
├── scripts/
│   └── drive.py                      ← the entire agent (375 lines)
├── .claude/skills/repro-agent/
│   └── SKILL.md                      ← skill definition
├── reproductions/                    ← output directory (populated per-run)
│   └── <issue-number>/
│       ├── issue.json
│       ├── action-log.json
│       ├── evidence-*.png
│       ├── verdict.md
│       └── traces/full-trace.json
├── .env.example                      ← config template
├── requirements.txt                  ← Python deps
├── pyproject.toml                    ← Python project config
├── DESIGN.md
├── HLD.md                            ← this file
└── plane/                            ← Plane clone (gitignored)
```

---

## Demo Structure (Hackathon Stage)

**Two beats, ~3 min total:**

| Beat | Goal | Key moment |
|------|------|-----------|
| **Live reproduction** (~2 min) | Run `drive.py --issue 9329` live | Audience sees browser moving autonomously |
| **Artifact inspection** (~1 min) | Show verdict.md, screenshots, action-log | Evidence the bug was found |

---

## Terminology

| Term | Definition |
|------|-----------|
| **repro-agent** | The system. |
| **drive.py** | The single Python script that does everything. |
| **browser-use** | Python library — resolves NL task → DOM actions via built-in Playwright. In-process, no server. |
| **Verdict** | `REPRODUCED`, `NOT_REPRODUCED`, or `INCONCLUSIVE`. Structured line parsed from agent output. |
| **Artifact bundle** | The output: `issue.json` + `action-log.json` + `evidence-*.png` + `verdict.md` + `traces/`. |
| **Action log** | `reproductions/<issue>/action-log.json` — every browser-use agent step (thought, action, result, URL). |