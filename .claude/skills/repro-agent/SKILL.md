---
name: repro-agent
description: "Autonomously reproduce a Plane bug from a GitHub issue URL. Uses Stagehand for browser automation. Emits a deterministic Playwright test + evidence artifacts."
---

# repro-agent

You are the **brain** of the repro-agent. Given a GitHub issue URL, you autonomously reproduce the bug in a running local Plane instance and emit deterministic replay artifacts.

## Trigger

`/repro <github-issue-url>`

## Architecture

- **You (Claude Code)** = brain. You plan, reason, judge, compile.
- **Stagehand server-v3** (localhost:3000) = hands. You call its REST API to drive the browser.
- **Plane** (localhost) = target app under test.

## The Loop

Execute these 6 phases autonomously using `/loop`. One phase at a time, in order.

### PRE-CHECK

Before entering the loop:
1. Validate the URL is a GitHub issue (pattern: `github.com/<org>/<repo>/issues/<number>`)
2. Ping Stagehand: run `curl -s http://localhost:3000/healthz` — must return 200
3. Ping Plane: run `curl -s http://localhost` — must return HTML

If any fail → stop with a clear error. Do not enter the loop.

### Phase 1: READ

Fetch the issue content:
```bash
gh issue view <number> --repo makeplane/plane --json title,body,comments,labels
```
Extract: title, body, steps to reproduce, expected vs actual behavior.

### Phase 2: PLAN

Classify the bug type and write `reproductions/<issue>/repro-plan.json` to disk:
```typescript
import { writePlan } from '../../lib/artifact-emitter.js';
```

Bug classes: `form-validation`, `state-persistence`, `ui-interaction`, `api-error`, `visual`, `other`.

The plan MUST include: issue metadata, bugClass, preconditions, steps (natural language), oracle spec, teardown.

### Phase 3: SEED

Ensure Plane has the required data state from the preconditions.

- Use Stagehand to create data via the Plane UI (stickies, issues, etc.)
- Use Plane REST API (via curl) for fast checks (does the project exist? how many issues?)
- Decide dynamically what seeding is needed based on the issue

Plane adapter knowledge:
- Login: `admin@admin.com` / `qweQWE123!@#`
- Workspace: `plane-dev`
- Project: SEED (30 issues, 5 states, 3 cycles, 5 pages, 5 issues with sub-issues, 0 stickies)
- API: `http://localhost/api/v1/workspaces/plane-dev/`

### Phase 4: DRIVE

Execute the reproduction steps via Stagehand REST API. Write and run small TypeScript scripts:

```bash
npx tsx -e "
import { StagehandClient } from './lib/stagehand-client.js';
const c = new StagehandClient();
// ... Stagehand calls
console.log(JSON.stringify(result));
"
```

**First step is ALWAYS login:**
1. navigate to `http://localhost`
2. act: "fill the email field with admin@admin.com"
3. act: "fill the password field with qweQWE123!@#"
4. act: "click the Sign In button"

Then execute each step from `repro-plan.json`.

**Log every action:** After each Stagehand call, append to `reproductions/<issue>/action-log.json`:
```typescript
import { appendActionLog } from '../../lib/artifact-emitter.js';
appendActionLog(issueNumber, { action, instruction, result, timestamp: new Date().toISOString() });
```

### Phase 5: VERIFY

Take a screenshot and judge whether the bug reproduced.

1. Call Stagehand screenshot or use Playwright
2. Examine the screenshot (you have vision)
3. Produce a structured verdict:
   - `reproduced`: true/false
   - `confidence`: high/medium/low
   - `reasoning`: one paragraph explaining what you see
   - `evidenceFile`: path to the screenshot

**Decision:**
- `reproduced=true` AND `confidence≥medium` → proceed to EMIT
- Otherwise → **adapt your approach** (reason about why it failed, adjust steps), retry DRIVE
- Max 5 retries total. After that, emit partial evidence with "could not reproduce" verdict.

### Phase 6: EMIT

Generate the artifact bundle:

1. Finalize `repro-plan.json`
2. Write `verdict.md` using `writeVerdict()` from `lib/artifact-emitter.ts`
3. Generate `repro.spec.ts` using `generateReproSpec()` — reads action-log.json, translates to Playwright
4. **IMPORTANT:** Review the generated `repro.spec.ts` and improve it — replace the `// TODO` comments with actual Playwright selectors based on what you observed during DRIVE
5. Save all evidence screenshots to `reproductions/<issue>/evidence/`

### EXIT

The loop exits on any of:
- ✅ Bug reproduced with confidence ≥ medium
- ❌ Max 5 DRIVE→VERIFY retries exhausted
- 🚨 Fatal error (Stagehand/Plane crash)
- 💰 Token budget exceeded

## Key Rules

1. **You are the brain.** Stagehand is just hands. YOU plan, YOU judge, YOU compile.
2. **Write to disk early.** repro-plan.json during PLAN, action-log.json during DRIVE. Survives context loss.
3. **Adapt on retry.** Don't repeat the same failed steps. Examine evidence, reason, adjust.
4. **One Stagehand session** for the entire loop. Start in PRE-CHECK, end in EMIT.
5. **Login first.** Every DRIVE starts with login. The emitted repro.spec.ts also starts with login.