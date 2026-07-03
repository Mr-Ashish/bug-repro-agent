/**
 * DRIVE Step 0: Start Stagehand session with CDP browser
 */
import "dotenv/config";
import { StagehandClient } from "../lib/stagehand-client.js";

const client = new StagehandClient();

const CDP_URL = "ws://localhost:9222/devtools/browser/2204546f-b687-434c-9e78-c656e5d9bc42";

async function main() {
  console.log("Starting Stagehand session...");
  const result = await client.startSession(CDP_URL);
  console.log("Session result:", JSON.stringify(result, null, 2));
  console.log("Session ID:", client.sessionId);
}

main().catch(console.error);