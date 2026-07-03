/**
 * DRIVE v2: Careful step-by-step login + reproduce bug #9329
 * Each step validates before proceeding.
 */
import "dotenv/config";
import { StagehandClient } from "../lib/stagehand-client.js";
import { writeFileSync, existsSync, readFileSync } from "fs";

const SESSION_ID = "3f16adbc-860c-47d9-8914-daac0d9e4fa7";
const LOG = "reproductions/9329/action-log.json";
const EVIDENCE = "reproductions/9329/evidence";
const LONG_TITLE = "A".repeat(256);

interface LogEntry { action: string; instruction: string; result: unknown; timestamp: string; }

function log(entry: LogEntry) {
  const entries: LogEntry[] = existsSync(LOG) ? JSON.parse(readFileSync(LOG, "utf-8")) : [];
  entries.push(entry);
  writeFileSync(LOG, JSON.stringify(entries, null, 2));
}

const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));

async function main() {
  const c = new StagehandClient();
  c.sessionId = SESSION_ID;

  // --- LOGIN ---
  console.log("=== LOGIN ===");
  
  let r = await c.navigate("http://localhost:3000");
  log({ action: "navigate", instruction: "http://localhost:3000", result: r, timestamp: new Date().toISOString() });
  console.log("1. Navigate to Plane:", r.success);
  await sleep(3000);

  r = await c.act('Clear the email input field, then type "admin@admin.com" into the email input field');
  log({ action: "act", instruction: "clear and type email", result: { success: r.success }, timestamp: new Date().toISOString() });
  console.log("2. Email:", r.success);
  await sleep(1500);

  r = await c.act('Click the "Continue" button');
  log({ action: "act", instruction: "click Continue", result: { success: r.success }, timestamp: new Date().toISOString() });
  console.log("3. Continue:", r.success);
  await sleep(2000);

  r = await c.act('Type "qweQWE123!@#" into the password input field');
  log({ action: "act", instruction: "type password", result: { success: r.success }, timestamp: new Date().toISOString() });
  console.log("4. Password:", r.success);
  await sleep(1000);

  r = await c.act('Click the "Sign in" button to log in');
  log({ action: "act", instruction: "click Sign in", result: { success: r.success }, timestamp: new Date().toISOString() });
  console.log("5. Sign in:", r.success);
  await sleep(5000);

  // Verify login
  let ext = await c.extract("What page am I on now? Am I logged in? What do I see?");
  log({ action: "extract", instruction: "verify login", result: ext.data, timestamp: new Date().toISOString() });
  console.log("6. Login check:", JSON.stringify(ext.data));
  
  // --- NAVIGATE TO WORK ITEMS ---
  console.log("\n=== NAVIGATE ===");
  
  r = await c.act('Click on the first project visible in the sidebar menu to open it');
  log({ action: "act", instruction: "click project in sidebar", result: { success: r.success }, timestamp: new Date().toISOString() });
  console.log("7. Click project:", r.success);
  await sleep(3000);

  r = await c.act('Click on "Work Items" in the left sidebar navigation menu');
  log({ action: "act", instruction: "click Work Items", result: { success: r.success }, timestamp: new Date().toISOString() });
  console.log("8. Work Items:", r.success);
  await sleep(3000);

  // Verify we're on work items
  ext = await c.extract("What page am I on? Can I see a list of work items/issues?");
  log({ action: "extract", instruction: "verify work items page", result: ext.data, timestamp: new Date().toISOString() });
  console.log("9. Page check:", JSON.stringify(ext.data));

  // --- REPRODUCE BUG ---
  console.log("\n=== REPRODUCE ===");

  r = await c.act('Click the "Add Work Item" button or the "+" button to create a new work item inline (not a modal). Look for a row at the bottom of the list or a "Create Work Item" link');
  log({ action: "act", instruction: "click inline Add Work Item", result: { success: r.success }, timestamp: new Date().toISOString() });
  console.log("10. Add work item:", r.success);
  await sleep(2000);

  // Type the long title
  r = await c.act(`Type the following exact text into the title input field that just appeared: ${LONG_TITLE}`);
  log({ action: "act", instruction: "type 256-char title", result: { success: r.success }, timestamp: new Date().toISOString() });
  console.log("11. Long title:", r.success);
  await sleep(1000);

  // Press Enter
  r = await c.act("Press the Enter key to submit the new work item");
  log({ action: "act", instruction: "press Enter to submit", result: { success: r.success }, timestamp: new Date().toISOString() });
  console.log("12. Enter:", r.success);
  await sleep(3000);

  // --- CAPTURE EVIDENCE ---
  console.log("\n=== EVIDENCE ===");

  // Extract error
  ext = await c.extract("Is there any error message, toast notification, or alert visible on the page? What does it say? Is the work item created or did it fail?");
  log({ action: "extract", instruction: "extract error after submit", result: ext.data, timestamp: new Date().toISOString() });
  console.log("13. Error extract:", JSON.stringify(ext.data));

  // Observe for toasts
  const obs = await c.observe("Look for any toast notifications, error messages, alerts, or popups on the page");
  log({ action: "observe", instruction: "observe toast/error", result: obs.data, timestamp: new Date().toISOString() });
  console.log("14. Observe:", JSON.stringify(obs.data));

  console.log("\n=== DRIVE V2 COMPLETE ===");
}

main().catch(console.error);