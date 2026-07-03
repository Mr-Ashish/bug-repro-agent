/**
 * DRIVE: Login to Plane, then reproduce bug #9329
 * - Navigate to login → authenticate
 * - Navigate to Work Items list view
 * - Click inline "Add work item"
 * - Type 256-char title
 * - Press Enter
 * - Observe the error message
 */
import "dotenv/config";
import { StagehandClient } from "../lib/stagehand-client.js";
import { writeFileSync, existsSync, readFileSync } from "fs";

const SESSION_ID = "3f16adbc-860c-47d9-8914-daac0d9e4fa7";
const ACTION_LOG_PATH = "reproductions/9329/action-log.json";

// Build a 256-char title
const LONG_TITLE = "A".repeat(256);

interface ActionLogEntry {
  action: string;
  instruction: string;
  result: unknown;
  timestamp: string;
}

function appendLog(entry: ActionLogEntry) {
  let log: ActionLogEntry[] = [];
  if (existsSync(ACTION_LOG_PATH)) {
    log = JSON.parse(readFileSync(ACTION_LOG_PATH, "utf-8"));
  }
  log.push(entry);
  writeFileSync(ACTION_LOG_PATH, JSON.stringify(log, null, 2));
}

async function main() {
  const client = new StagehandClient();
  client.sessionId = SESSION_ID;

  // Step 1: Navigate to Plane login
  console.log("Step 1: Navigate to Plane...");
  const nav1 = await client.navigate("http://localhost:3000");
  appendLog({ action: "navigate", instruction: "http://localhost:3000", result: nav1, timestamp: new Date().toISOString() });
  console.log("  navigate:", nav1.success);

  // Wait a moment for page load
  await new Promise(r => setTimeout(r, 2000));

  // Step 2: Fill email
  console.log("Step 2: Fill email...");
  const fillEmail = await client.act('Type "admin@admin.com" into the email input field');
  appendLog({ action: "act", instruction: 'Type "admin@admin.com" into the email input field', result: fillEmail, timestamp: new Date().toISOString() });
  console.log("  fillEmail:", fillEmail.success);

  await new Promise(r => setTimeout(r, 1000));

  // Step 3: Click Continue/Go button
  console.log("Step 3: Click Continue...");
  const clickContinue = await client.act('Click the "Continue" or "Go" button to proceed');
  appendLog({ action: "act", instruction: 'Click the "Continue" or "Go" button to proceed', result: clickContinue, timestamp: new Date().toISOString() });
  console.log("  clickContinue:", clickContinue.success);

  await new Promise(r => setTimeout(r, 2000));

  // Step 4: Fill password
  console.log("Step 4: Fill password...");
  const fillPassword = await client.act('Type "qweQWE123!@#" into the password input field');
  appendLog({ action: "act", instruction: 'Type "qweQWE123!@#" into the password input field', result: fillPassword, timestamp: new Date().toISOString() });
  console.log("  fillPassword:", fillPassword.success);

  await new Promise(r => setTimeout(r, 1000));

  // Step 5: Click Sign in
  console.log("Step 5: Sign in...");
  const clickSignIn = await client.act('Click the "Sign in" or "Continue" button to log in');
  appendLog({ action: "act", instruction: 'Click the "Sign in" or "Continue" button to log in', result: clickSignIn, timestamp: new Date().toISOString() });
  console.log("  clickSignIn:", clickSignIn.success);

  // Wait for dashboard to load
  await new Promise(r => setTimeout(r, 4000));

  // Step 6: Take screenshot to confirm login
  console.log("Step 6: Screenshot after login...");
  const ss1 = await client.screenshot();
  appendLog({ action: "screenshot", instruction: "screenshot after login", result: { success: ss1.success }, timestamp: new Date().toISOString() });
  console.log("  screenshot:", ss1.success);

  // Save screenshot if we got base64 data
  if (ss1.success && ss1.data) {
    const screenshotData = (ss1.data as any).screenshot || (ss1.data as any).base64;
    if (screenshotData) {
      writeFileSync("reproductions/9329/evidence/screenshot-after-login.png", Buffer.from(screenshotData, "base64"));
      console.log("  Saved screenshot-after-login.png");
    }
  }

  // Step 7: Navigate to Work Items — we need to find the project first
  console.log("Step 7: Navigate to a project...");
  const clickProject = await client.act('Click on the first project in the sidebar, or navigate to the "SEED" project or any project listed');
  appendLog({ action: "act", instruction: 'Click on the first project in the sidebar', result: clickProject, timestamp: new Date().toISOString() });
  console.log("  clickProject:", clickProject.success);

  await new Promise(r => setTimeout(r, 3000));

  // Step 8: Navigate to Work Items / Issues
  console.log("Step 8: Go to Work Items...");
  const clickWorkItems = await client.act('Click on "Work Items" or "Issues" in the sidebar navigation');
  appendLog({ action: "act", instruction: 'Click on "Work Items" or "Issues" in the sidebar', result: clickWorkItems, timestamp: new Date().toISOString() });
  console.log("  clickWorkItems:", clickWorkItems.success);

  await new Promise(r => setTimeout(r, 3000));

  // Step 9: Screenshot the work items list
  console.log("Step 9: Screenshot work items view...");
  const ss2 = await client.screenshot();
  appendLog({ action: "screenshot", instruction: "screenshot work items list", result: { success: ss2.success }, timestamp: new Date().toISOString() });
  if (ss2.success && ss2.data) {
    const d = (ss2.data as any).screenshot || (ss2.data as any).base64;
    if (d) {
      writeFileSync("reproductions/9329/evidence/screenshot-work-items.png", Buffer.from(d, "base64"));
      console.log("  Saved screenshot-work-items.png");
    }
  }

  // Step 10: Click inline "Add work item"
  console.log("Step 10: Click inline Add work item...");
  const clickAdd = await client.act('Click the inline "Add work item" button or the "+ New Work Item" button at the bottom of the list, NOT the modal/sidebar create button');
  appendLog({ action: "act", instruction: 'Click inline Add work item button', result: clickAdd, timestamp: new Date().toISOString() });
  console.log("  clickAdd:", clickAdd.success);

  await new Promise(r => setTimeout(r, 2000));

  // Step 11: Type 256-char title
  console.log("Step 11: Type 256-char title...");
  const typeTitle = await client.act(`Type the following text into the work item title input field: "${LONG_TITLE}"`);
  appendLog({ action: "act", instruction: "Type 256-character title", result: typeTitle, timestamp: new Date().toISOString() });
  console.log("  typeTitle:", typeTitle.success);

  await new Promise(r => setTimeout(r, 1000));

  // Step 12: Press Enter to submit
  console.log("Step 12: Press Enter...");
  const pressEnter = await client.act("Press the Enter key to submit the work item");
  appendLog({ action: "act", instruction: "Press Enter to submit", result: pressEnter, timestamp: new Date().toISOString() });
  console.log("  pressEnter:", pressEnter.success);

  // Wait for error to appear
  await new Promise(r => setTimeout(r, 3000));

  // Step 13: Screenshot the error state
  console.log("Step 13: Screenshot after submit...");
  const ss3 = await client.screenshot();
  appendLog({ action: "screenshot", instruction: "screenshot after 256-char title submit", result: { success: ss3.success }, timestamp: new Date().toISOString() });
  if (ss3.success && ss3.data) {
    const d = (ss3.data as any).screenshot || (ss3.data as any).base64;
    if (d) {
      writeFileSync("reproductions/9329/evidence/screenshot-after-submit.png", Buffer.from(d, "base64"));
      console.log("  Saved screenshot-after-submit.png");
    }
  }

  // Step 14: Extract error message
  console.log("Step 14: Extract error message...");
  const extractError = await client.extract("Extract any error message, toast notification, or validation message visible on the page", {
    type: "object",
    properties: {
      errorMessage: { type: "string", description: "The error or toast message text" },
      hasError: { type: "boolean", description: "Whether an error message is visible" }
    }
  });
  appendLog({ action: "extract", instruction: "Extract error message after submit", result: extractError, timestamp: new Date().toISOString() });
  console.log("  extractError:", JSON.stringify(extractError, null, 2));

  console.log("\n=== DRIVE COMPLETE ===");
  console.log("Action log written to:", ACTION_LOG_PATH);
}

main().catch(console.error);