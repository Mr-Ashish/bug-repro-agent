# HLD — Bug Reproduction Agent

> **Hackathon:** Browser-Use Hackathon, July 4 2026, Bengaluru
> **Target app:** [Plane](https://github.com/makeplane/plane) (makeplane) — open-source project management
> **One-liner:** A Grok skill that, given a GitHub issue URL from Plane, autonomously reproduces the bug in a running local Plane instance using Stagehand for browser automation, then emits a deterministic Playwright script + evidence artifacts so the reproduction can be replayed without the agent.

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
│  localhost:3000   │  ─────→  │  localhost:80          │
│                   │  HTTP    │                        │
│  Model:           │          │  Next.js + Django +    │
│  gemini-2.5-flash │          │  Postgres + Redis +    │
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

## Complete Flow

### PRE-CHECK (before entering the loop)

1. Validate the URL is a GitHub issue (not a PR, discussion, etc.)
2. Ping Stagehand server (`GET localhost:3000/healthz`)
3. Ping Plane (`GET localhost` — login page loads)
4. Start Stagehand session (`POST /v1/sessions/start`) — one session for the entire loop

If any fail → exit with clear error, don't enter the loop.

### Loop Phases

### 1. READ

**Input:** GitHub issue URL
**Mechanism:** `gh issue view <number> --repo makeplane/plane --json title,body,comments` via bash.
**Output:** Structured issue data (title, body, steps to reproduce, expected vs actual).

### 2. PLAN

**Input:** Issue data from READ
**Action:** Claude Code classifies the bug type and emits a structured plan.
**Output:** `reproductions/<issue>/repro-plan.json` — **written to disk immediately**.

```json
{
  "issue": {
    "number": 9329,
    "title": "Inline work item creation shows generic error on 255+ char title",
    "url": "https://github.com/makeplane/plane/issues/9329"
  },
  "bugClass": "form-validation",
  "preconditions": [
    "Logged in as admin",
    "Navigated to SEED project work items view"
  ],
  "steps": [
    "Click inline 'Add work item' or press shortcut",
    "Type a title that is exactly 256 characters long",
    "Press Enter to submit"
  ],
  "oracle": {
    "type": "screenshot-vision",
    "expected": "Generic error message appears instead of a clear validation error about title length"
  },
  "teardown": "Delete the created work item if any"
}
```

### 3. SEED

**Input:** `repro-plan.json` preconditions
**Action:** Ensure Plane has the required data state. Hybrid approach:
- **Stagehand UI** for visual operations (create stickies, navigate to specific views)
- **Plane REST API** (via fetch) for bulk/fast operations (verify project exists, check issue count)

Claude Code dynamically decides what seeding is needed based on the issue.

**Output:** Plane is in the right state for reproduction.

### 4. DRIVE

**Input:** `repro-plan.json` steps
**First step is always login:** Navigate to login page → fill email/password → click Sign In → verify dashboard loaded.
**Then bug-specific steps** via Stagehand REST API:
- `navigate(url)` — go to the right page
- `act(instruction)` — perform NL-described actions
- `observe(instruction)` — discover available elements when unsure
- `extract(instruction, schema)` — pull structured data from the page

**Execution mechanism:** Claude Code writes small inline TS scripts that import `lib/stagehand-client.ts`, runs them with `npx tsx script.ts`, reads stdout for results.

**Action log:** Each Stagehand call appends an entry to `reproductions/<issue>/action-log.json`:
```json
[
  {"action": "navigate", "instruction": "http://localhost/plane-dev/", "result": {...}, "timestamp": "..."},
  {"action": "act", "instruction": "click Add Work Item button", "result": {...}, "timestamp": "..."}
]
```

**Video:** Playwright records the browser context (`video: 'on'`) throughout DRIVE. Saved to `evidence/video.webm`.

**Output:** Steps executed, page in post-reproduction state, action log on disk.

### 5. VERIFY

**Input:** Current page state after DRIVE
**Action:** Screenshot + Claude Code vision judgment (the **oracle**).
- Take screenshot of current page
- Claude Code (the brain) examines the screenshot
- Produces a structured **verdict**:

```json
{
  "reproduced": true,
  "confidence": "high",
  "reasoning": "Screenshot shows a generic 'Something went wrong' toast after entering a 256-char title, instead of a specific validation message about title length.",
  "evidence_file": "reproductions/9329/evidence/screenshot-after.png"
}
```

**Decision:**
- `reproduced=true` AND `confidence≥medium` → proceed to EMIT
- Otherwise → **adapt steps** (Claude Code reasons about why it failed, adjusts approach), retry DRIVE (max 5 attempts)

**Output:** Verdict + evidence screenshots.

### 6. EMIT

**Input:** All data from phases 1–5 + `action-log.json`
**Action:** Generate deterministic artifacts:
1. **`repro-plan.json`** — finalize the structured plan
2. **`repro.spec.ts`** — Claude Code reads `action-log.json` and translates each Stagehand call into Playwright API equivalents (`page.goto`, `page.click`, `page.fill`, `expect`). Includes login.
3. **`evidence/`** — screenshots (before/after), `video.webm`, console logs
4. **`verdict.md`** — human-readable report: issue summary, steps taken, result, confidence
5. End Stagehand session (`POST /v1/sessions/{id}/end`)

**Output:** All files written to `./reproductions/<issue-number>/`.

### EXIT CONDITIONS

| Condition | When | What happens |
|-----------|------|-------------|
| ✅ Success | `reproduced=true, confidence≥medium` | EMIT artifacts, end session, exit |
| ❌ Max retries | 5 DRIVE→VERIFY cycles failed | Emit partial evidence + "could not reproduce" verdict |
| 🚨 Fatal error | Stagehand/Plane crash, unrecoverable | Exit with error report |
| 💰 Budget exceeded | Token/cost limit hit | Safety exit with partial state |

---

## Roles — Who Does What

| Role | Who | Why |
|------|-----|-----|
| **Meta-agent (brain)** | Claude Code via Grok skill + /loop | Reads issues, plans, decides, judges, compiles. The only thing that reasons. |
| **Browser hands** | Stagehand server-v3 (Gemini Flash) | Resolves NL instructions to DOM actions. Doesn't plan or judge — just executes `act/observe/extract`. |
| **Target app** | Plane (local docker-compose) | The app under test. Passive — just runs. |
| **Verification oracle** | Claude Code (vision) | Screenshots → judgment. Same agent, different phase. |
| **Replay runtime** | Playwright (npx) | Runs emitted `.spec.ts`. No agent in the loop. |

---

## Stagehand Integration

**Server:** Stagehand server-v3 running on `localhost:3000`
**Model:** `google/gemini-2.5-flash` (cheap, fast, good at DOM reasoning)
**Protocol:** REST API over HTTP

**Client:** `lib/stagehand-client.ts` — thin TypeScript fetch wrapper

```typescript
// Core operations
await client.startSession(cdpUrl, modelName)
await client.navigate(url)
await client.act("click the Create Work Item button")
await client.observe("what form fields are visible?")
await client.extract("extract the error message text", schema)
await client.endSession()
```

**Key design decision:** Claude Code is the brain, Stagehand is the hands. Stagehand does NOT plan or reason about bug reproduction strategy — it only resolves natural-language instructions to browser actions. All planning, retry logic, and verification happen in Claude Code.

---

## Plane Adapter Knowledge

Baked into the skill and `lib/plane-adapter.ts`:

| Knowledge | Value |
|-----------|-------|
| Base URL | `http://localhost` |
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
├── reproductions/                    ← output (gitignored)
│   └── 9329/
│       ├── repro-plan.json
│       ├── action-log.json
│       ├── repro.spec.ts
│       ├── evidence/
│       │   ├── screenshot-before.png
│       │   ├── screenshot-after.png
│       │   ├── video.webm
│       │   └── console.log
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

## Demo Flow (Hackathon Stage)

### Act 1 — Live Reproduction (2 min)

1. Show Plane GitHub issue #9329 on screen
2. Run `/repro https://github.com/makeplane/plane/issues/9329`
3. Audience watches: Claude Code reads issue → plans → opens Plane → logs in → types 256-char title → triggers error
4. Agent declares: "Bug reproduced."

### Act 2 — Show Artifacts (1 min)

1. Open `reproductions/9329/` folder
2. Show `repro.spec.ts` — "The agent wrote a Playwright test for this bug"
3. Show `verdict.md` — "Here's the agent's judgment"
4. Show screenshots/video — "Here's the visual evidence"

### Act 3 — Deterministic Replay (1 min)

1. Run `npx playwright test reproductions/9329/repro.spec.ts`
2. Test runs in seconds, no agent, no LLM
3. "Now it's a regression test. Run it a thousand times. Pay for the agent once."

Repeat with bug #9050 if time allows.

---

## Explicitly Out of Scope

| Cut | Why |
|-----|-----|
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
| **Verdict** | Oracle output: `{ reproduced: bool, confidence: high/medium/low, reasoning: string, evidence_file: path }`. |