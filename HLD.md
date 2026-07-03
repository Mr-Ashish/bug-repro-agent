# HLD — Bug Reproduction Agent

> **Hackathon:** Browser-Use Hackathon, July 4 2026, Bengaluru
> **Target app:** [Plane](https://github.com/makeplane/plane) (makeplane) — open-source project management
> **One-liner:** A Grok skill that, given a GitHub issue URL from Plane, autonomously reproduces the bug in a running local Plane instance using **browser-use** (Python) for browser automation, then emits a deterministic Playwright script + evidence artifacts so the reproduction can be replayed without the agent.

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
│  │                   THE LOOP                            │  │
│  │                                                       │  │
│  │  1. READ ──→ 2. PLAN ──→ 3. SEED ──→                │  │
│  │                                                       │  │
│  │  ──→ 4. DRIVE ──→ 5. VERIFY ──→ 6. EMIT             │  │
│  │          ↑              │                              │  │
│  │          └──── retry ───┘ (if not reproduced)         │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  EXIT CONDITIONS:                                           │
│  ✅ Bug reproduced → emit artifacts, exit success           │
│  ❌ Max retries (5) → emit partial evidence, exit failure   │
│  🚨 Fatal error → exit with error report                    │
│  💰 Token budget exceeded → safety exit                     │
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

## The Two-Phase Model

### Phase 1 — AUTHOR (agentic, expensive, once per bug)

`scripts/drive.py` fetches the issue, builds a prompt, runs a browser-use agent, and saves everything.

```
issue URL/number
    │
    ▼
gh issue view → title + body
    │
    ▼
generic prompt template + issue body + Plane creds
    │
    ▼
browser-use Agent → Chrome CDP → Plane
    │
    ▼
VERDICT: REPRODUCED | <summary>   ← agent's structured output
    │
    ▼
reproductions/<N>/               ← all artifacts saved
    ├── issue.json
    ├── action-log.json
    ├── evidence-*.png
    ├── verdict.md
    └── traces/
```

### Phase 2 — REPLAY (deterministic, cheap, N times)

The emitted `repro.spec.ts` is a standard Playwright test. No agent, no browser-use, no LLM.

```bash
npx playwright test reproductions/9329/repro.spec.ts
```

Assertions baked in from the oracle spec. Runs in seconds. Becomes a regression test.

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

## Roles — Who Does What

| Role | Who | Why |
|------|-----|-----|
| **Meta-agent (brain)** | Claude Code via Grok skill + /loop | Reads issues, plans, decides, judges, compiles. The only thing that reasons. |
| **Browser hands** | browser-use Agent (Claude Sonnet 4 via OpenRouter) | Resolves NL task → DOM actions via Playwright. In-process Python library, no server. |
| **Target app** | Plane (local docker-compose) | The app under test. Passive — just runs. |
| **Verification oracle** | Claude Code (vision) | Screenshots → judgment. Same agent, different phase. |
| **Replay runtime** | Playwright (npx) | Runs emitted `.spec.ts`. No agent in the loop. |

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

## Plane Adapter Knowledge

Baked into the skill and `lib/plane-adapter.ts`:

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
│   └── drive.py                      ← main driver (fetch → prompt → drive → save)
├── .claude/skills/repro-agent/
│   └── SKILL.md                      ← skill definition
├── lib/
│   ├── plane_config.py               ← Plane config (Python)
│   ├── plane-adapter.ts              ← Plane config (TypeScript, for replay specs)
│   ├── repro-plan.schema.ts          ← TypeScript types
│   ├── artifact-emitter.ts           ← generates repro.spec.ts + verdict.md
│   └── __init__.py
├── reproductions/                    ← output directory (populated per-run)
│   └── <issue-number>/
│       ├── issue.json                ← fetched issue content
│       ├── action-log.json           ← step-by-step agent trace
│       ├── evidence-*.png            ← screenshots
│       ├── verdict.md                ← parsed verdict + stats
│       └── traces/full-trace.json    ← complete agent history
├── DESIGN.md
├── HLD.md                            ← this file
├── package.json
├── tsconfig.json
└── plane/                            ← Plane clone (gitignored)
```

---

## Demo Structure (Hackathon Stage)

**Goal:** Show the full loop live, then prove the replay is agent-free.

**Three beats, ~4 min total:**

| Beat | Goal | Key moment |
|------|------|-----------|
| **Live reproduction** (~2 min) | Show the agent reproducing #9329 end-to-end | Audience sees browser moving autonomously |
| **Artifact inspection** (~1 min) | Show what the agent produced | `repro.spec.ts`, `verdict.md`, screenshots/video |
| **Deterministic replay** (~1 min) | Prove the test runs without agent/LLM | `npx playwright test` completes in seconds |

**Principle:** "Pay for the agent once, replay forever." Repeat with #9050 if time allows.

---

## Out of Scope

| Cut | Reason |
|-----|--------|
| Temporal / Dagger replay runtime | `npx playwright test` is enough |
| Testcontainers / per-run isolation | Plane already runs via docker-compose |
| Multi-app support | Hardcoded to Plane — swap adapter later |
| OpenRouter judge | Claude Code IS the judge |
| Python orchestrator | Replaced by skill + /loop |
| HAR capture | Screenshots + video are enough |
| Visual diff oracle | Screenshot + Claude vision is the oracle |

---

## Terminology

| Term | Definition |
|------|-----------|
| **repro-agent** | The system. Name used everywhere — code, docs, demo. |
| **Brain** | Claude Code running the /repro skill. Plans, reasons, judges. The only thing that thinks. |
| **Hands** | browser-use Agent (Python) — resolves NL task → DOM actions via built-in Playwright. In-process, no server. |
| **Skill** | `.claude/skills/repro-agent/SKILL.md` — the packaged prompt + instructions. |
| **/loop** | Grok's autonomous execution mode. The skill runs inside it. |
| **Author (Phase 1)** | Agent-driven reproduction. Expensive, once per bug. |
| **Replay (Phase 2)** | Deterministic Playwright test. Cheap, N times. |
| **Oracle** | The VERIFY mechanism. Screenshot + Claude vision → structured verdict `{reproduced, confidence, reasoning}`. |
| **Adapter** | Plane-specific knowledge (URLs, creds, nav patterns, API endpoints). `lib/plane_config.py` (Python) / `lib/plane-adapter.ts` (TypeScript replay). |
| **Artifact bundle** | The output: `repro-plan.json` + `repro.spec.ts` + `action-log.json` + `evidence/` + `verdict.md`. |
| **Seed** | Creating required app state before reproduction (issues, stickies, etc.). |
| **Action log** | `reproductions/<issue>/action-log.json` — every browser-use agent step during DRIVE, used by EMIT to generate `repro.spec.ts`. |
| **Verdict** | Oracle output: `{ reproduced: bool, confidence: high/medium/low, reasoning: string, evidence_file: path }`. Values are **REPRODUCED**, **NOT REPRODUCED**, or **INCONCLUSIVE** — never "FIXED" or "RESOLVED". |