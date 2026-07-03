/**
 * Stagehand-only bug reproduction driver.
 *
 * - Model: configurable via STAGEHAND_SESSION_MODEL env var (default: gpt-4o)
 *   Must support structured output (response_format: json_schema).
 *   Claude via OpenRouter does NOT work — Stagehand can't parse the response.
 * - Every browser action goes through Stagehand REST API
 * - Full trace logging: every request + response saved for introspection
 *
 * Flow: session → login → navigate → type 256-char title → submit → evidence
 */
import "dotenv/config";
import { writeFileSync, mkdirSync } from "fs";
import { chromium } from "playwright-core";

const BASE = process.env.STAGEHAND_URL || "http://localhost:3100";
const CDP_URL = process.env.CDP_URL!;
const MODEL = process.env.STAGEHAND_SESSION_MODEL || "gpt-4o";
const PLANE_URL = process.env.PLANE_URL || "http://localhost:3000";
const PLANE_EMAIL = process.env.PLANE_EMAIL || "admin@admin.com";
const PLANE_PASSWORD = process.env.PLANE_PASSWORD || "qweQWE123!@#";
const MODEL_API_KEY = process.env.OPENROUTER_API_KEY!;

const ISSUE_ID = "9329";
const REPRO_DIR = `reproductions/${ISSUE_ID}`;
const TRACES_DIR = `${REPRO_DIR}/traces`;
const ACTION_LOG_PATH = `${REPRO_DIR}/action-log.json`;
const LONG_TITLE = "A".repeat(256);

// ── Trace infrastructure ─────────────────────────────────────

interface Trace {
  step: number;
  action: string;       // session | navigate | act | extract | observe
  instruction: string;  // what we asked Stagehand to do
  request: { url: string; body: unknown };
  response: { status: number; body: unknown };
  result: string;       // human-readable summary
  durationMs: number;
  ts: string;
}

const traces: Trace[] = [];
let stepN = 0;
let SESSION_ID = "";

function saveTraces() {
  mkdirSync(TRACES_DIR, { recursive: true });

  // Full traces — every request/response
  writeFileSync(`${TRACES_DIR}/full-trace.json`, JSON.stringify(traces, null, 2));

  // Compact action log — just step/action/instruction/result
  const compact = traces.map(({ step, action, instruction, result, durationMs, ts }) => ({
    step, action, instruction, result, durationMs, ts,
  }));
  writeFileSync(ACTION_LOG_PATH, JSON.stringify(compact, null, 2));

  // Per-step trace files for easy inspection
  for (const t of traces) {
    writeFileSync(
      `${TRACES_DIR}/step-${String(t.step).padStart(2, "0")}-${t.action}.json`,
      JSON.stringify(t, null, 2),
    );
  }

  console.log(`\n  📁 Traces: ${traces.length} steps → ${TRACES_DIR}/`);
  console.log(`  📁 Action log → ${ACTION_LOG_PATH}`);
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// ── HTTP layer with tracing ──────────────────────────────────

async function tracedPost(
  action: string,
  instruction: string,
  path: string,
  body: Record<string, unknown>,
): Promise<{ json: any; trace: Trace }> {
  stepN++;
  const url = `${BASE}${path}`;
  const t0 = Date.now();

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-model-api-key": MODEL_API_KEY,
    },
    body: JSON.stringify(body),
  });

  const json = await res.json();
  const durationMs = Date.now() - t0;

  // Build human-readable result
  // IMPORTANT: action-specific formatting MUST come before the generic success check,
  // otherwise extract/observe results just show "ok" instead of actual content.
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
    step: stepN,
    action,
    instruction,
    request: { url, body },
    response: { status: res.status, body: json },
    result,
    durationMs,
    ts: new Date().toISOString(),
  };

  traces.push(trace);
  const icon = json?.success === false ? "❌" : "✅";
  console.log(`  [${stepN}] ${icon} ${action}: ${result.slice(0, 120)}  (${durationMs}ms)`);

  return { json, trace };
}

// ── Stagehand API wrappers ───────────────────────────────────

async function createSession() {
  const { json } = await tracedPost("session", "Create Stagehand session", "/v1/sessions/start", {
    modelName: MODEL,
    browser: { type: "local", cdpUrl: CDP_URL },
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

async function screenshot(label: string): Promise<string | null> {
  const { json } = await tracedPost("screenshot", label, `/v1/sessions/${SESSION_ID}/screenshot`, {});
  const b64 = json?.data?.screenshot || json?.data?.base64;
  if (b64) {
    const filename = `evidence-${String(stepN).padStart(2, "0")}-${label.replace(/[^a-z0-9]/gi, "-").toLowerCase()}.png`;
    const filepath = `${REPRO_DIR}/${filename}`;
    writeFileSync(filepath, Buffer.from(b64, "base64"));
    console.log(`  📸 Saved ${filepath}`);
    return filepath;
  }
  return null;
}

// ── MAIN ─────────────────────────────────────────────────────

async function main() {
  if (!CDP_URL) {
    console.error("❌ Set CDP_URL in .env (e.g. ws://localhost:9222/devtools/browser/...)");
    process.exit(1);
  }
  if (!MODEL_API_KEY) {
    console.error("❌ Set OPENROUTER_API_KEY in .env");
    process.exit(1);
  }

  mkdirSync(REPRO_DIR, { recursive: true });

  // ── Video recording via Playwright CDP ─────────────────────
  // Connect to the SAME browser Stagehand will use, record everything
  console.log("── Video: connecting Playwright recorder to CDP ──");
  let videoRecorder: { context: any; page: any } | null = null;
  try {
    const browser = await chromium.connectOverCDP(CDP_URL);
    const context = await browser.newContext({
      recordVideo: { dir: REPRO_DIR, size: { width: 1280, height: 720 } },
    });
    const page = await context.newPage();
    await page.goto(PLANE_URL);
    videoRecorder = { context, page };
    console.log(`  🎬 Recording video to ${REPRO_DIR}/\n`);
  } catch (e) {
    console.warn(`  ⚠️ Video recording skipped (CDP connect failed): ${e}`);
  }

  console.log("╔══════════════════════════════════════════════╗");
  console.log("║  DRIVE — Stagehand-only bug repro            ║");
  console.log("╚══════════════════════════════════════════════╝");
  console.log(`  model    : ${MODEL}`);
  console.log(`  stagehand: ${BASE}`);
  console.log(`  cdp      : ${CDP_URL}`);
  console.log(`  plane    : ${PLANE_URL}`);
  console.log(`  traces   : ${TRACES_DIR}/\n`);

  // ── 0. Create session ──────────────────────────────────────
  console.log("── 0. Create session ──");
  await createSession();
  console.log(`  → session: ${SESSION_ID}\n`);

  // ── 1. Login ───────────────────────────────────────────────
  // Proven sequence from curl testing:
  //   navigate → act(type email) → act(Continue) → act(type password) → act(Go to workspace)
  console.log("── 1. Login ──");
  await nav(PLANE_URL);
  await sleep(3000);

  await act(`Click on the email input field and type "${PLANE_EMAIL}"`);
  await sleep(2000);

  await act('Click the Continue button');
  await sleep(5000);  // Critical: password form needs time to render

  await act(`Click on the password input field and type "${PLANE_PASSWORD}"`);
  await sleep(2000);

  await act('Click the "Go to workspace" button');
  await sleep(8000);  // Critical: workspace load takes time

  // Verify login
  const loginCheck = await extract("What page am I on? Is this a dashboard or login page?");
  console.log(`  → login: ${loginCheck.text.slice(0, 120)}\n`);
  await screenshot("after-login");

  if (loginCheck.text.toLowerCase().includes("sign") || loginCheck.text.toLowerCase().includes("login")) {
    console.error("❌ Login failed — still on login page");
    saveTraces();
    process.exit(1);
  }

  // ── 2. Navigate to work items ──────────────────────────────
  console.log("── 2. Navigate to work items ──");
  // Use Plane's known project URL
  await nav(`${PLANE_URL}/plane-dev/projects/9e2a160f-a44f-4777-a761-564ab5e572a4/issues`);
  await sleep(4000);

  const pageCheck = await extract("What page am I on? Can I see work items or issues?");
  console.log(`  → page: ${pageCheck.text.slice(0, 120)}\n`);
  await screenshot("work-items-list");

  // ── 3. Add work item ───────────────────────────────────────
  console.log("── 3. Add work item ──");
  await act('Click the "Add work item" button');
  await sleep(2000);

  // ── 4. Type 256-char title ─────────────────────────────────
  console.log("── 4. Type 256-char title (trigger bug) ──");
  await act(`Click on the Title input field and type the following text: ${LONG_TITLE}`);
  await sleep(1000);

  await screenshot("256-char-title-typed");

  // ── 5. Submit ──────────────────────────────────────────────
  console.log("── 5. Submit ──");
  await act("Press the Enter key to submit the work item");
  await sleep(5000);

  // ── 6. Capture evidence ────────────────────────────────────
  console.log("── 6. Capture evidence ──");
  await screenshot("after-submit");
  const evidence = await extract(
    'Is there any error message, validation message, or toast? Look for text mentioning "255", "characters", "error", or "try again". Report the exact text.'
  );
  console.log(`  → evidence: ${evidence.text.slice(0, 200)}\n`);

  await observe("Find any red text, validation messages, error banners, or toast notifications");

  // ── 7. Verdict ─────────────────────────────────────────────
  console.log("── 7. Verdict ──");
  const verdict = await extract(
    'After submitting a 256-character title, what happened? Answer DESCRIPTIVE if you see "Title should be less than 255 characters", GENERIC if you see "Some error occurred", or NONE if no error appeared.'
  );

  console.log("\n╔══════════════════════════════════════════════╗");
  console.log(`║  VERDICT: ${verdict.text.slice(0, 35).padEnd(35)}║`);
  console.log("╚══════════════════════════════════════════════╝");

  saveTraces();

  // ── Close video recorder ───────────────────────────────────
  if (videoRecorder) {
    try {
      await videoRecorder.page.close();
      await videoRecorder.context.close();
      console.log(`  🎬 Video saved to ${REPRO_DIR}/`);
    } catch (e) {
      console.warn(`  ⚠️ Video close failed: ${e}`);
    }
  }

  console.log("\n✅ DRIVE COMPLETE");
}

main().catch(async (e) => {
  console.error("\n💀 FATAL:", e);
  saveTraces();
  process.exit(1);
});