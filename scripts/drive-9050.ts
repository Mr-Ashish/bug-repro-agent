/**
 * Stagehand-only bug reproduction: Plane issue #9050
 * "Deleted Stickies reappear on page reload"
 *
 * Steps:
 *   1. Login
 *   2. Navigate to Stickies page
 *   3. Create a new sticky with identifiable text
 *   4. Delete the sticky (confirm deletion)
 *   5. Verify sticky is gone
 *   6. Reload the page
 *   7. Check if deleted sticky reappeared (the bug)
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

const ISSUE_ID = "9050";
const REPRO_DIR = `reproductions/${ISSUE_ID}`;
const TRACES_DIR = `${REPRO_DIR}/traces`;
const ACTION_LOG_PATH = `${REPRO_DIR}/action-log.json`;
const STICKY_TEXT = `REPRO-9050-${Date.now()}`;

// ── Trace infrastructure ─────────────────────────────────────

interface Trace {
  step: number;
  action: string;
  instruction: string;
  request: { url: string; body: unknown };
  response: { status: number; body: unknown };
  result: string;
  durationMs: number;
  ts: string;
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
    request: { url, body },
    response: { status: res.status, body: json },
    result, durationMs, ts: new Date().toISOString(),
  };
  traces.push(trace);
  const icon = json?.success === false ? "❌" : "✅";
  console.log(`  [${stepN}] ${icon} ${action}: ${result.slice(0, 120)}  (${durationMs}ms)`);
  return { json, trace };
}

// ── Stagehand wrappers ───────────────────────────────────────

async function createSession() {
  const { json } = await tracedPost("session", "Create session", "/v1/sessions/start", {
    modelName: MODEL, browser: { type: "local", cdpUrl: CDP_URL },
  });
  SESSION_ID = json?.data?.sessionId;
  if (!SESSION_ID) throw new Error(`Session creation failed: ${JSON.stringify(json)}`);
  return SESSION_ID;
}

async function nav(url: string) {
  const { json } = await tracedPost("navigate", url, `/v1/sessions/${SESSION_ID}/navigate`, { url });
  return json;
}

async function act(instruction: string) {
  const { json } = await tracedPost("act", instruction, `/v1/sessions/${SESSION_ID}/act`, { input: instruction });
  return json;
}

async function extract(instruction: string) {
  const { json } = await tracedPost("extract", instruction, `/v1/sessions/${SESSION_ID}/extract`, { instruction });
  const text = json?.data?.result?.extraction
    ?? JSON.stringify(json?.data?.result ?? json?.data ?? json).slice(0, 500);
  return { text: String(text), raw: json };
}

async function observe(instruction: string) {
  const { json } = await tracedPost("observe", instruction, `/v1/sessions/${SESSION_ID}/observe`, { instruction });
  return json?.data?.result ?? [];
}

// ── MAIN ─────────────────────────────────────────────────────

async function main() {
  if (!CDP_URL || !MODEL_API_KEY) {
    console.error("❌ Set CDP_URL and OPENROUTER_API_KEY in .env");
    process.exit(1);
  }
  mkdirSync(REPRO_DIR, { recursive: true });

  console.log("╔══════════════════════════════════════════════╗");
  console.log("║  DRIVE — Issue #9050: Sticky delete bug      ║");
  console.log("╚══════════════════════════════════════════════╝");
  console.log(`  model : ${MODEL}`);
  console.log(`  sticky: "${STICKY_TEXT}"\n`);

  // ── 0. Session ─────────────────────────────────────────────
  console.log("── 0. Create session ──");
  await createSession();
  console.log(`  → ${SESSION_ID}\n`);

  // ── 1. Login ───────────────────────────────────────────────
  console.log("── 1. Login ──");
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

  // ── 2. Navigate to Stickies ────────────────────────────────
  console.log("── 2. Navigate to Stickies ──");
  await nav(`${PLANE_URL}/plane-dev/stickies/`);
  await sleep(3000);

  const stickiesPage = await extract("What page am I on? Do I see a stickies section?");
  console.log(`  → ${stickiesPage.text.slice(0, 100)}\n`);

  // ── 3. Create a sticky ─────────────────────────────────────
  console.log("── 3. Create a sticky ──");
  await act('Click the button to create a new sticky note. Look for a "+" button or "Add sticky" or "New sticky" button.');
  await sleep(2000);

  await act(`Type the following text into the sticky note content area: ${STICKY_TEXT}`);
  await sleep(2000);

  // Click elsewhere to save the sticky
  await act('Click somewhere outside the sticky note to save it, like on the page background or header area');
  await sleep(2000);

  // Verify sticky was created
  const stickyCreated = await extract(`Can you see a sticky note containing the text "${STICKY_TEXT}"? List all sticky notes visible.`);
  console.log(`  → created: ${stickyCreated.text.slice(0, 120)}\n`);

  // ── 4. Delete the sticky ───────────────────────────────────
  console.log("── 4. Delete the sticky ──");
  // Right-click or find the delete option on the sticky
  await act(`Find the sticky note with text "${STICKY_TEXT}" and look for a three-dot menu, context menu, or delete icon on it. Click the menu or options button.`);
  await sleep(2000);

  await act('Click the "Delete" option from the menu');
  await sleep(2000);

  // Confirm deletion if a modal appears
  await act('If a confirmation dialog appeared, click the "Delete" or "Confirm" button to confirm deletion');
  await sleep(3000);

  // ── 5. Verify sticky is gone ───────────────────────────────
  console.log("── 5. Verify sticky is gone after delete ──");
  const afterDelete = await extract(`Is the sticky note with text "${STICKY_TEXT}" still visible on the page? List all visible sticky notes.`);
  console.log(`  → after delete: ${afterDelete.text.slice(0, 150)}\n`);

  // ── 6. Reload the page ─────────────────────────────────────
  console.log("── 6. Reload the page ──");
  await nav(`${PLANE_URL}/plane-dev/stickies/`);
  await sleep(5000);

  // ── 7. Check if sticky reappeared (THE BUG) ────────────────
  console.log("── 7. Check if deleted sticky reappeared ──");
  const afterReload = await extract(`After reloading the page, is the sticky note with text "${STICKY_TEXT}" visible? List all sticky notes you can see.`);
  console.log(`  → after reload: ${afterReload.text.slice(0, 200)}\n`);

  // ── 8. Verdict ─────────────────────────────────────────────
  console.log("── 8. Verdict ──");
  const stickyGone = !afterReload.text.includes(STICKY_TEXT);
  const verdict = stickyGone ? "FIXED" : "REPRODUCED";

  if (verdict === "REPRODUCED") {
    console.log("\n╔══════════════════════════════════════════════╗");
    console.log("║  🐛 BUG REPRODUCED: Deleted sticky came back ║");
    console.log("╚══════════════════════════════════════════════╝");
  } else {
    console.log("\n╔══════════════════════════════════════════════╗");
    console.log("║  ✅ BUG APPEARS FIXED: Sticky stayed deleted  ║");
    console.log("╚══════════════════════════════════════════════╝");
  }

  // Write verdict
  const verdictMd = `# Verdict: Issue #9050

**Issue**: [Deleted Stickies reappear on page reload](https://github.com/makeplane/plane/issues/9050)
**Date**: ${new Date().toISOString().split("T")[0]}
**Model**: ${MODEL}
**Sticky text**: \`${STICKY_TEXT}\`

## Result: ${verdict === "REPRODUCED" ? "BUG REPRODUCED 🐛" : "BUG APPEARS FIXED ✅"}

### After delete (before reload)
${afterDelete.text}

### After reload
${afterReload.text}

### Conclusion
${verdict === "REPRODUCED"
    ? "The deleted sticky reappeared after page reload, confirming the bug described in #9050."
    : "The deleted sticky did NOT reappear after page reload. The bug appears fixed in this build."}
`;
  writeFileSync(`${REPRO_DIR}/verdict.md`, verdictMd);

  saveTraces();
  console.log("\n✅ DRIVE COMPLETE");
}

main().catch((e) => {
  console.error("\n💀 FATAL:", e);
  saveTraces();
  process.exit(1);
});