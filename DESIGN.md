# Bug Reproduction Agent — Design Document

> **Target app:** [Plane](https://github.com/makeplane/plane) (makeplane) — open-source project management
> **Architecture:** Claude Code (Grok) as meta-agent + Stagehand for browser automation
> **See also:** [HLD.md](./HLD.md) for the locked architecture decisions

---

## Core Architectural Principle

Split every reproduction into **"agent-authored" vs "deterministic-runtime."** Claude Code does the reasoning-heavy authoring on the first encounter with an issue; it compiles that into artifacts (Playwright scripts, plan specs) that replay without the agent. Reproduce once with intelligence, replay forever with determinism.

---

## The Two-Phase Model

```
PHASE 1 — AUTHOR (Claude Code + Stagehand, agentic, expensive, once)
  issue → READ → PLAN → SEED → DRIVE → VERIFY
        → EMIT: repro-plan.json + repro.spec.ts + evidence/ + verdict.md

PHASE 2 — REPLAY (Playwright, deterministic, cheap, N times)
  npx playwright test reproductions/<issue>/repro.spec.ts
```

---

## System Components

### 1. Meta-agent — Claude Code (Grok skill + /loop)

The brain. Reads the issue, decides the plan, drives Stagehand, judges the result, emits artifacts. Packaged as a skill (`/repro <issue-url>`) that internally uses `/loop` for autonomous execution.

### 2. Browser hands — Stagehand server-v3

Stagehand (https://github.com/browserbase/stagehand) runs as a local server on `localhost:3000`. Claude Code calls its REST API via a TypeScript client: `act()`, `observe()`, `extract()`, `navigate()`. Stagehand uses `google/gemini-2.5-flash` for its internal DOM reasoning — cheap and fast. It doesn't plan or judge; it just translates NL instructions to browser actions.

### 3. Target app — Plane (local docker-compose)

Plane runs locally via `docker-compose-local.yml`. Full stack: Next.js frontend + Django API + PostgreSQL + Redis + RabbitMQ + MinIO. Pre-seeded with workspace `plane-dev`, project SEED with 30 issues.

### 4. Verification oracle — Claude Code vision

After executing repro steps, Claude Code takes a screenshot and uses vision to judge: "Does this match the expected bug behavior?" No separate judge LLM — Claude Code IS the judge.

### 5. Artifact emitter

Compiles the agent's work into deterministic artifacts:
- `repro-plan.json` — structured reproduction plan
- `repro.spec.ts` — Playwright test for replay
- `evidence/` — screenshots, video, console logs
- `verdict.md` — human-readable report

### 6. Seeder — dynamic, hybrid

Claude Code ensures Plane has the right data state before reproduction. Uses Stagehand UI for visual operations (create stickies) and Plane REST API for bulk/fast ops. Decides what seeding is needed per bug.

---

## What Lives Where

| Layer | Phase 1 (Claude Code) | Phase 2 (Deterministic) |
|---|---|---|
| Orchestrate | skill + /loop | (not needed) |
| Plan | LLM → `repro-plan.json` | (frozen plan) |
| Seed | Stagehand UI + Plane API | (pre-seeded state) |
| Drive | Stagehand `act/observe` | `repro.spec.ts` (Playwright) |
| Verify | screenshot + vision | Playwright assertions |
| Capture | Stagehand screenshots | Playwright video/trace |

---

## Why This Shape

- **Claude Code earns its place** on the three genuinely hard jobs: turning messy issues into plans, resolving ambiguous UI steps, and judging fuzzy oracles.
- **Determinism is recovered** by compiling agent decisions into replayable Playwright scripts.
- **Cost is controlled** — pay for the agent once per issue, replay for free.
- **It becomes a regression system**, not just a repro toy.

---

## Design Ancestry

This design evolved from an earlier "full-fat" 9-layer architecture that targeted Panel (HoloViz). The key shifts:
- Panel → Plane (widget library → full-stack web app)
- Temporal replay runtime → `npx playwright test`
- Testcontainers/Dagger → existing docker-compose
- Python seeder scripts → dynamic hybrid seeding (UI + API)
- Three-tier oracle → screenshot + Claude vision
- Separate Python orchestrator → Grok skill + /loop

The original's core insight — agent-authored vs deterministic-runtime split — survived intact.
