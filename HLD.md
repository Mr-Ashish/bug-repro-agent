# HLD — Bug Reproduction Agent

> **Hackathon:** Browser-Use Hackathon, July 4 2026, Bengaluru
> **Target app:** [Plane](https://github.com/makeplane/plane) (makeplane) — open-source project management
> **One-liner:** A Grok skill that, given a GitHub issue URL from Plane, autonomously reproduces the bug in a running local Plane instance using Stagehand for browser automation, then emits a deterministic Playwright script + evidence artifacts so the reproduction can be replayed without the agent.

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
│  Stagehand        │          │  Plane (local)        │
│  server-v3        │          │  docker-compose       │
│  localhost:3100   │  ─────→  │  localhost:3000        │
│                   │  HTTP    │                        │
│  Model: gpt-4o    │          │  Next.js + Django +    │
│  (via OpenRouter)  │          │  Postgres + Redis +    │
│                   │          │  RabbitMQ + MinIO      │
└──────────────────┘          └──────────────────────┘
```

---

## The Two-Phase Model

### Phase 1 — AUTHOR (agentic, expensive, once per bug)

Claude Code is the meta-agent. It reads the issue, reasons about steps, drives the browser via Stagehand, judges the result, and compiles everything into deterministic artifacts.

```
issue URL → READ → PLAN → SEED → DRIVE → VERIFY → EMIT
                                                      │
                                          ┌───────────┴───────────┐
                                          │  repro-plan.json      │
                                          │  repro.spec.ts        │
                                          │  evidence/            │
                                          │    screenshots/       │
                                          │    video/             │
                                          │    console.log        │
                                          │  verdict.md           │
                                          └───────────────────────┘
```

### Phase 2 — REPLAY (deterministic, cheap, N times)

The emitted `repro.spec.ts` is a standard Playwright test. No agent, no Stagehand, no LLM.

```bash
npx playwright test reproductions/9329/repro.spec.ts
```

Assertions baked in from the oracle spec. Runs in seconds. Becomes a regression test.

---

## Phase Goals & Constraints

### PRE-CHECK

**Goal:** Confirm infrastructure is live before entering the loop.

**Constraints:**
- URL must be a GitHub issue (not PR, discussion, etc.)
- Stagehand (`localhost:3100`), Plane (`localhost:3000`), and Chrome CDP (`localhost:9222`) must all respond
- One Stagehand session starts here and spans the entire run
- Any failure → exit with clear error, never enter the loop

### READ

**Goal:** Extract structured reproduction information from the GitHub issue.

**Constraints:**
- Source is `gh issue view` (title, body, comments)
- No disk writes — output lives in context for PLAN

### PLAN

**Goal:** Classify the bug and produce a structured reproduction plan.

**Constraints:**
- Must write `repro-plan.json` to disk immediately (survives context loss)
- Plan contains: issue metadata, bug class, preconditions, ordered steps, oracle spec, teardown
- See `lib/repro-plan.schema.ts` for the canonical shape

### SEED

**Goal:** Get Plane into the data state the bug requires.

**Constraints:**
- Use Stagehand UI for visual operations (create stickies, navigate views)
- Use Plane REST API for fast checks (project exists, issue counts)
- Decide dynamically per bug — no fixed seeding strategy

### DRIVE

**Goal:** Execute the reproduction steps in the browser.

**Constraints:**
- Login is always step zero — every DRIVE begins with authentication
- Every Stagehand call appends to `action-log.json` (instruction, result, timestamp)
- Main drive script: `scripts/drive-v3.ts` (`npm run drive`)
- Every Stagehand call is traced to `reproductions/<issue>/traces/` for introspection
- On retry, adapt — examine evidence, reason about failure, change approach. Never replay identical failed steps.

### VERIFY

**Goal:** Determine whether the bug was reproduced.

**Constraints:**
- Evidence: screenshot of current page state
- Judge: Claude Code vision (the oracle)
- Verdict is structured: `{ reproduced, confidence, reasoning, evidenceFile }`
- Proceed to EMIT only when `reproduced=true AND confidence≥medium`
- Otherwise retry DRIVE (max 5 DRIVE→VERIFY cycles)

### EMIT

**Goal:** Generate deterministic replay artifacts from the action log.

**Constraints:**
- `repro.spec.ts` is generated by translating `action-log.json` → Playwright API calls. Must include login.
- Evidence: screenshots, Stagehand extract/observe results
- `verdict.md`: human-readable report
- Stagehand session ends here
- All output to `reproductions/<issue-number>/`

### Exit Conditions

| Condition | What happens |
|-----------|-------------|
| ✅ `reproduced=true, confidence≥medium` | EMIT artifacts, end session, exit |
| ❌ 5 DRIVE→VERIFY cycles exhausted | Emit partial evidence + "could not reproduce" verdict |
| 🚨 Stagehand/Plane crash | Exit with error report |
| 💰 Token budget exceeded | Safety exit with partial state |

---

## Roles — Who Does What

| Role | Who | Why |
|------|-----|-----|
| **Meta-agent (brain)** | Claude Code via Grok skill + /loop | Reads issues, plans, decides, judges, compiles. The only thing that reasons. |
| **Browser hands** | Stagehand server-v3 (GPT-4o via OpenRouter) | Resolves NL instructions to DOM actions. Doesn't plan or judge — just executes `act/observe/extract`. |
| **Target app** | Plane (local docker-compose) | The app under test. Passive — just runs. |
| **Verification oracle** | Claude Code (vision) | Screenshots → judgment. Same agent, different phase. |
| **Replay runtime** | Playwright (npx) | Runs emitted `.spec.ts`. No agent in the loop. |

---

## Stagehand Integration

| Property | Value |
|----------|-------|
| Server | Stagehand server-v3, `localhost:3100` |
| Model | `gpt-4o` via OpenRouter (must support structured output) |
| Protocol | REST API over HTTP |
| Client | `lib/stagehand-client.ts` (reusable) or raw fetch with tracing (drive script) |
| Operations | `startSession`, `navigate`, `act`, `observe`, `extract`, `screenshot`, `endSession` |
| API key | Passed per-request via `x-model-api-key` header |
| Traces | Every call saved to `reproductions/<issue>/traces/step-NN-action.json` |

**Principle:** Stagehand resolves NL instructions → DOM actions. It does not plan, judge, or reason about bug reproduction. All strategy lives in Claude Code.

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

## Demo Bugs

| # | Bug | Repro Steps | Bug Class |
|---|-----|-------------|-----------|
| **9329** | 255+ char title shows generic error | Type long title → press Enter → see unhelpful error | form-validation |
| **9050** | Deleted stickies reappear on reload | Delete a sticky → reload page → sticky is back | state-persistence |
| **9124** | Sub-task expand requires 3 clicks | Click expand chevron → nothing → click again → nothing → 3rd click works | ui-interaction |

---

## File Structure

```
bug-repro-agent/
├── .claude/
│   └── skills/
│       └── repro-agent/
│           └── SKILL.md              ← skill prompt + /loop instructions
├── lib/
│   ├── stagehand-client.ts           ← thin REST client for Stagehand server
│   ├── repro-plan.schema.ts          ← TypeScript types for repro-plan.json
│   ├── plane-adapter.ts              ← Plane-specific knowledge
│   └── artifact-emitter.ts           ← generates repro.spec.ts + verdict.md
├── reproductions/                    ← output (tracked in git)
│   └── 9329/
│       ├── repro-plan.json
│       ├── action-log.json
│       ├── repro.spec.ts
│       ├── traces/                   ← per-step Stagehand introspection
│       │   ├── step-01-session.json
│       │   ├── step-03-act.json
│       │   └── ...
│       ├── evidence-*.png
│       └── verdict.md
├── DESIGN.md                         ← original design (to be updated)
├── HLD.md                            ← this file
├── HACKATHON_CONTEXT.md
├── ISSUE_ANALYSIS.md
├── GRILLING.md
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
| Browser-Use Agent class | Replaced by Claude Code + Stagehand |
| Python orchestrator | Replaced by skill + /loop |
| HAR capture | Screenshots + video are enough |
| Visual diff oracle | Screenshot + Claude vision is the oracle |

---

## Terminology

| Term | Definition |
|------|-----------|
| **repro-agent** | The system. Name used everywhere — code, docs, demo. |
| **Brain** | Claude Code running the /repro skill. Plans, reasons, judges. The only thing that thinks. |
| **Hands** | Stagehand server — executes browser actions, doesn't reason about bugs. Translates NL → DOM clicks. |
| **Skill** | `.claude/skills/repro-agent/SKILL.md` — the packaged prompt + instructions. |
| **/loop** | Grok's autonomous execution mode. The skill runs inside it. |
| **Author (Phase 1)** | Agent-driven reproduction. Expensive, once per bug. |
| **Replay (Phase 2)** | Deterministic Playwright test. Cheap, N times. |
| **Oracle** | The VERIFY mechanism. Screenshot + Claude vision → structured verdict `{reproduced, confidence, reasoning}`. |
| **Adapter** | Plane-specific knowledge (URLs, creds, nav patterns, API endpoints). `lib/plane-adapter.ts`. |
| **Artifact bundle** | The output: `repro-plan.json` + `repro.spec.ts` + `action-log.json` + `evidence/` + `verdict.md`. |
| **Seed** | Creating required app state before reproduction (issues, stickies, etc.). |
| **Action log** | `reproductions/<issue>/action-log.json` — every Stagehand call during DRIVE, used by EMIT to generate `repro.spec.ts`. |
| **Verdict** | Oracle output: `{ reproduced: bool, confidence: high/medium/low, reasoning: string, evidence_file: path }`. Values are **REPRODUCED**, **NOT REPRODUCED**, or **INCONCLUSIVE** — never "FIXED" or "RESOLVED". |