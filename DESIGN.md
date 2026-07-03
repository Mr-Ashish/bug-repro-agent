# Bug Reproduction Agent — Full-Fat Redesign

> **Variation A** — Archit's design. Claude Code as the meta-agent.
> **Target app:** [Panel](https://github.com/holoviz/panel) (HoloViz)

---

## The Key Shift

Claude Code doesn't just *sequence* the layers — it **plans, authors, and supervises** them, while the deterministic artifacts it produces become the durable, replayable system. Agent for the hard once-per-issue reasoning; compiled scripts for everything repeatable.

---

## Core Architectural Principle

Split every layer into **"agent-authored" vs "deterministic-runtime."** Claude Code does the reasoning-heavy authoring on the first encounter with an issue; it compiles that into artifacts (seed manifests, Stagehand/Playwright scripts, assertion specs) that replay without the agent. This is what makes it both intelligent *and* a regression asset — reproduce once, emit replayable script.

---

## Layer-by-Layer Redesign

### 1. Meta-orchestrator — Claude Code (agent loop)

The top-level driver. Reads the issue, decides the plan, invokes each layer as tools/subagents, observes results, retries, and decides "reproduced / not / can't tell." Its durable output per issue is a **run manifest** (what it did) plus the compiled artifacts. This replaces Temporal *as the author*; but see layer 8 — Temporal still runs the compiled replays.

### 2. Planner — Claude Code + a schema contract

Claude Code reads the Panel/GitHub issue and emits a structured `repro-plan.json`:

```json
{
  "preconditions": ["Panel app seed specs"],
  "steps": ["natural-language + resolved selectors"],
  "oracle": { "type": "...", "target": "...", "expected": "..." },
  "teardown": "kill server + cleanup"
}
```

The schema is the contract every downstream layer consumes. This is where the open/axial-coding instinct helps: the planner classifies the issue (widget-state bug? layout/rendering bug? callback bug? server-side bug?) because bug *class* determines seeding and oracle strategy.

### 3. Devbox — bash-driven, but as a real provisioning subagent

Full version (not the sleep-loop): Claude Code drives **Testcontainers** or a **Dagger** pipeline via bash for programmatic lifecycle, per-run network isolation, and volume snapshotting. For Panel, the devbox boots a Python environment with Panel + its dependencies, launches `panel serve app.py`, and verifies the Bokeh server is healthy. Claude Code supervises health via the server's ready signal (HTTP 200 on the served app URL), not a fixed sleep.

### 4. App adapter — a Skill (`CLAUDE.md` playbook) per app

This is the generic/specific boundary. The **Panel adapter Skill** encodes: how to install Panel and its dependencies, readiness signal (Bokeh server health endpoint), the Python API seed patterns, widget/layout quirks, common Bokeh model selectors, and Panel-specific DOM structure. Swapping to another app later = swap the Skill. Claude Code loads the relevant adapter and stays app-agnostic in its core logic.

### 5. Seeder — Claude Code authors, Python scripts execute

Claude Code translates `preconditions` into a **seed script** — a Python file that constructs the Panel app state needed to reproduce the bug. This uses Panel's Python API directly (e.g., `pn.widgets.Select(...)`, `pn.Column(...)`, `pn.serve(...)`) to build the exact app configuration described in the issue. The compiled seed script is deterministic and replayable — the agent isn't in the loop on replay. It also emits **dependency-ordered** setup (data sources before widgets, widgets before layouts), which is exactly the kind of reasoning an agent does well and a template does badly.

### 6. UI driver — Claude Code authors Stagehand, compiles to Playwright

First run: Claude Code writes Stagehand `act/observe` calls from the natural-language steps — resolving ambiguous steps against the live DOM (Panel renders via Bokeh, so selectors target Bokeh model elements). Then it **caches the resolved actions and emits a pure Playwright script**. This is the crucial move: Stagehand (with the LLM) for authoring/self-healing; compiled Playwright for deterministic replay. You get adaptability once and reproducibility forever.

### 7. Verification oracle — Claude Code + compiled assertions

Full version, three tiers Claude Code selects between based on bug class:

- **Deterministic:** Playwright web-first assertions (element state, text, count) — compiled into the replay script.
- **Visual:** Screenshot diff against expected, for rendering/layout bugs (common in Panel).
- **Semantic:** Claude Code inspects trace + DOM + console/network and judges whether *this specific bug* manifested — for fuzzy cases assertions can't express (e.g., "widget updates feel laggy" or "callback fires twice").

The oracle spec goes into the plan schema so replays self-verify without the agent.

### 8. Capture — Playwright native

Video + trace + HAR + console, one config. Trace is what feeds the semantic oracle and your eventual regression review. Free under the compiled Playwright script.

### 9. Replay runtime — Temporal (or Dagger), agent NOT in loop

The compiled artifacts (seed script + Playwright script + oracle spec) become a **durable workflow**: boot → install Panel env → run seed app → run Playwright → assert → capture → teardown, with retries and isolation. This is your regression harness. Claude Code produced it; Temporal runs it a thousand times deterministically and cheaply. This resolves the cost/non-determinism cautions — you pay for the agent once per issue, not per run.

---

## The Two-Phase Mental Model

```
PHASE 1 — AUTHOR (Claude Code, agentic, expensive, once)
  issue → plan → boot → seed(author) → drive(author, self-heal)
        → verify(author) → EMIT: seed_app.py + repro.spec.ts + oracle.json + video

PHASE 2 — REPLAY (Temporal, deterministic, cheap, N times)
  artifacts → boot → install env → seed_app.py → repro.spec.ts
            → oracle.json → video → teardown
```

---

## What Lives Where

| Layer | Author-time (Claude Code) | Runtime (deterministic) |
|---|---|---|
| Orchestrate | agent loop | Temporal workflow |
| Plan | LLM → schema | (frozen plan) |
| Devbox | supervises Testcontainers | Testcontainers/Dagger |
| Adapter | reads Skill | (baked into scripts) |
| Seed | authors seed script | `seed_app.py` (Panel Python API) |
| Drive | authors via Stagehand | `repro.spec.ts` (Playwright) |
| Oracle | selects + authors | `oracle.json` assertions |
| Capture | — | Playwright config |

---

## Why This Is the Right Full-Fat Shape

- **Claude Code earns its place** on the three genuinely hard, reasoning-heavy jobs: turning messy issues into plans, resolving ambiguous UI steps, and judging fuzzy oracles. Those are agent-shaped problems.
- **Determinism is recovered** by compiling agent decisions into replayable artifacts — you're not stuck choosing between "smart but flaky" and "dumb but stable."
- **The generic goal holds:** only the adapter Skill and seeder patterns are app-specific; swap them for another app and the whole machine moves.
- **It becomes a regression system, not just a repro toy** — which is where the eval-infra background makes this genuinely valuable beyond the hackathon.

**The one hard problem this doesn't magic away:** the **semantic oracle** for bugs that can't be expressed as assertions. That's the frontier piece. Everything else here is buildable with today's tools.

---

## Open Decision

> Draft the **Panel adapter Skill** or the **plan-schema contract** first?
