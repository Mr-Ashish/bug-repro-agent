/**
 * Stagehand-only bug reproduction: Plane issue #9124
 * "Collapsible sub-tasks require three clicks to expand"
 *
 * Steps:
 *   1. Login
 *   2. Navigate to work items with sub-tasks
 *   3. Find a task with sub-tasks (expand it — should work on 1 click)
 *   4. Find a sub-task with its own sub-tasks
 *   5. Try to expand the sub-task — count how many clicks it takes
 *   6. Report: 1 click = fixed, 3 clicks = bug reproduced
 */
import "dotenv/config";
import { writeFileSync, mkdirSync } from "fs";

const BASE = process.env.STAGEHAND_URL || "http://localhost:3100";
const CDP_URL = process.env.CDP_URL!;
const MODEL = process.env.STAGEHAND_SESSION_MODEL || "gpt-4o";
const MODEL_API_KEY = process.env.OPENROUTER_API_KEY!;
const PLANE_URL = process.env.PLANE_URL || "http://localhost:3000";
const PLANE_EMAIL = process.env.PLANE_EMAIL || "admin@admin.com";
const PLANE_PASSWORD = process.env.PLANE_PASSWORD || "qweQWE123!@#";

const ISSUE_ID = "9124";
const REPRO_DIR = `reproductions/${ISSUE_ID}`;
const TRACES_DIR = `${REPRO_DIR}/traces`;
const ACTION_LOG_PATH = `${REPRO_DIR}/action-log.json`;

// ── Trace infrastructure (same as drive-v3) ──────────────────

interface Trace {
  step: number; action: string; instruction: string;
  request: { url: string; body: unknown };
  response: { status: number; body: unknown };
  result: string; durationMs: number; ts: string;
}

const traces: Trace[] = [];
let stepN = 0;
let SESSION_ID = "";

function saveTraces() {
  mkdirSync(TRACES_DIR, { recursive: true });
  writeFileSync(`${TRACES_DIR}/full-trace.json`, JSON.stringify(traces, null, 2));
  const compact = traces.map(({ step, action, instruction, result, durationMs, ts }) => ({
    step, action, instruction, result, durationMs, ts,
  }));
  writeFileSync(ACTION_LOG_PATH, JSON.stringify(compact, null, 2));
  for (const t of traces) {
    writeFileSync(
      `${TRACES_DIR}/step-${String(t.step).padStart(2, "0")}-${t.action}.json`,
      JSON.stringify(t, null, 2),
    );
  }
  console.log(`\n  📁 Traces: ${traces.length} steps → ${TRACES_DIR}/`);
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function tracedPost(
  action: string, instruction: string, path: string, body: Record<string, unknown>,
): Promise<{ json: any; trace: Trace }> {
  stepN++;
  const url = `${BASE}${path}`;
  const t0 = Date.now();
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-model-api-key": MODEL_API_KEY },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  const durationMs = Date.now() - t0;

  let result: string;
  if (action === "session") {
    result = `session_id=${json?.data?.sessionId ?? "UNKNOWN"}`;
  } else if (json?.success === false) {
    result = `FAIL: ${json?.message ?? JSON.stringify(json).slice(0, 200)}`;
  } else if (action === "extract") {
    const text = json?.data?.result?.extraction;
    result = text ? String(text).slice(0, 300) : JSON.stringify(json?.data?.result ?? json?.data ?? json).slice(0, 300);
  } else if (action === "observe") {
    const items = json?.data?.result ?? [];
    result = items.map((i: any) => i.description).join(" | ").slice(0, 300) || "(none)";
  } else if (json?.success === true) {
    result = "ok";
  } else {
    result = JSON.stringify(json).slice(0, 200);
  }

  const trace: Trace = {
    step: stepN, action, instruction,
    request: { url, body }, response: { status: res.status, body: json },
    result, durationMs, ts: new Date().toISOString(),
  };
  traces.push(trace);
  const icon = json?.success === false ? "❌" : "✅";
  console.log(`  [${stepN}] ${icon} ${action}: ${result.slice(0, 120)}  (${durationMs}ms)`);
  return { json, trace };
}

async function createSession() {
  const { json } = await tracedPost("session", "Create session", "/v1/sessions/start", {
    modelName: MODEL, browser: { type: "local", cdpUrl: CDP_URL },
  });
  SESSION_ID = json?.data?.sessionId;
  if (!SESSION_ID) throw new Error(`Session creation failed`);
  return SESSION_ID;
}

async function nav(url: string) {
  return (await tracedPost("navigate", url, `/v1/sessions/${SESSION_ID}/navigate`, { url })).json;
}
async function act(instruction: string) {
  return (await tracedPost("act", instruction, `/v1/sessions/${SESSION_ID}/act`, { input: instruction })).json;
}
async function extract(instruction: string) {
  const { json } = await tracedPost("extract", instruction, `/v1/sessions/${SESSION_ID}/extract`, { instruction });
  const text = json?.data?.result?.extraction ?? JSON.stringify(json?.data?.result ?? json?.data ?? json).slice(0, 500);
  return { text: String(text), raw: json };
}
async function observe(instruction: string) {
  return (await tracedPost("observe", instruction, `/v1/sessions/${SESSION_ID}/observe`, { instruction })).json?.data?.result ?? [];
}

// ── MAIN ─────────────────────────────────────────────────────

async function main() {
  if (!CDP_URL || !MODEL_API_KEY) { console.error("❌ Set CDP_URL and OPENROUTER_API_KEY in .env"); process.exit(1); }
  mkdirSync(REPRO_DIR, { recursive: true });

  console.log("╔══════════════════════════════════════════════╗");
  console.log("║  DRIVE — Issue #9124: Sub-task expand bug     ║");
  console.log("╚══════════════════════════════════════════════╝");
  console.log(`  model: ${MODEL}\n`);

  // ── 0. Session ─────────────────────────────────────────────
  console.log("── 0. Create session ──");
  await createSession();

  // ── 1. Login ───────────────────────────────────────────────
  console.log("\n── 1. Login ──");
  await nav(PLANE_URL);
  await sleep(3000);
  await act(`Click on the email input field and type "${PLANE_EMAIL}"`);
  await sleep(2000);
  await act('Click the Continue button');
  await sleep(5000);
  await act(`Click on the password input field and type "${PLANE_PASSWORD}"`);
  await sleep(2000);
  await act('Click the "Go to workspace" button');
  await sleep(8000);

  const loginCheck = await extract("What page am I on?");
  console.log(`  → ${loginCheck.text.slice(0, 80)}\n`);

  // ── 2. Navigate to work items ──────────────────────────────
  console.log("── 2. Navigate to work items ──");
  await nav(`${PLANE_URL}/plane-dev/projects/9e2a160f-a44f-4777-a761-564ab5e572a4/issues`);
  await sleep(4000);

  // ── 3. Check for tasks with sub-tasks ──────────────────────
  console.log("── 3. Find tasks with sub-tasks ──");
  const taskList = await extract("List all work items visible. Which ones have a chevron/expand icon indicating they have sub-tasks?");
  console.log(`  → ${taskList.text.slice(0, 200)}\n`);

  // ── 4. Expand a parent task ────────────────────────────────
  console.log("── 4. Expand a parent task (should work in 1 click) ──");
  await act('Find a work item that has a chevron or expand arrow indicating sub-tasks. Click the expand chevron to show its sub-tasks.');
  await sleep(2000);

  const afterExpand = await extract("Are sub-tasks now visible under the expanded parent task? List what you see.");
  console.log(`  → ${afterExpand.text.slice(0, 200)}\n`);

  // ── 5. Try expanding a sub-task (the bug) ──────────────────
  console.log("── 5. Try expanding a sub-task (the bug is here) ──");
  
  // First click
  console.log("  → Click 1:");
  await act('Find a sub-task that also has its own expand chevron (indicating sub-sub-tasks). Click that expand chevron once.');
  await sleep(2000);

  const afterClick1 = await extract("Did the sub-task expand to show sub-sub-tasks? Or did nothing happen?");
  console.log(`    ${afterClick1.text.slice(0, 120)}\n`);

  // Second click
  console.log("  → Click 2:");
  await act('Click the same sub-task expand chevron again.');
  await sleep(2000);

  const afterClick2 = await extract("Did the sub-task expand now? Are sub-sub-tasks visible?");
  console.log(`    ${afterClick2.text.slice(0, 120)}\n`);

  // Third click
  console.log("  → Click 3:");
  await act('Click the same sub-task expand chevron one more time.');
  await sleep(2000);

  const afterClick3 = await extract("Did the sub-task finally expand? Are sub-sub-tasks visible now?");
  console.log(`    ${afterClick3.text.slice(0, 120)}\n`);

  // ── 6. Verdict ─────────────────────────────────────────────
  console.log("── 6. Verdict ──");
  const verdictExtract = await extract(
    'Summarize: How many clicks did it take to expand the sub-task? Did it expand on the 1st click (FIXED), or did it require 2-3 clicks (BUG)? Answer with FIXED or REPRODUCED and explain.'
  );

  const verdictText = verdictExtract.text;
  const isReproduced = verdictText.toUpperCase().includes("REPRODUCED") || verdictText.includes("3 clicks") || verdictText.includes("three clicks");

  if (isReproduced) {
    console.log("\n╔══════════════════════════════════════════════╗");
    console.log("║  🐛 BUG REPRODUCED: 3 clicks needed          ║");
    console.log("╚══════════════════════════════════════════════╝");
  } else {
    console.log("\n╔══════════════════════════════════════════════╗");
    console.log("║  ✅ BUG NOT REPRODUCED / FIXED                ║");
    console.log("╚══════════════════════════════════════════════╝");
  }

  console.log(`\n  Verdict: ${verdictText.slice(0, 200)}`);

  const verdictMd = `# Verdict: Issue #9124

**Issue**: [Collapsible sub-tasks require three clicks to expand](https://github.com/makeplane/plane/issues/9124)
**Date**: ${new Date().toISOString().split("T")[0]}
**Model**: ${MODEL}

## Result: ${isReproduced ? "BUG REPRODUCED 🐛" : "NOT REPRODUCED / FIXED ✅"}

### Click-by-click results

| Click | Result |
|-------|--------|
| 1st | ${afterClick1.text.slice(0, 200)} |
| 2nd | ${afterClick2.text.slice(0, 200)} |
| 3rd | ${afterClick3.text.slice(0, 200)} |

### Agent verdict
${verdictText}
`;
  writeFileSync(`${REPRO_DIR}/verdict.md`, verdictMd);

  saveTraces();
  console.log("\n✅ DRIVE COMPLETE");
}

main().catch((e) => { console.error("\n💀 FATAL:", e); saveTraces(); process.exit(1); });