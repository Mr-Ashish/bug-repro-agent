/**
 * Thin TypeScript REST client for Stagehand server-v3.
 * Ported from the Python StagehandClient in bug-qa-agent.
 *
 * Usage (from a script run via `npx tsx`):
 *   import { StagehandClient } from './stagehand-client.js';
 *   const client = new StagehandClient();
 *   await client.startSession('ws://localhost:9222');
 *   await client.navigate('http://localhost');
 *   await client.act('click the login button');
 *   await client.endSession();
 */

export interface StagehandResult {
  success: boolean;
  data?: Record<string, unknown>;
  error?: string;
}

export class StagehandClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  sessionId: string | null = null;

  constructor(
    baseUrl: string = process.env.STAGEHAND_URL || "http://localhost:3100",
    modelApiKey: string = process.env.OPENROUTER_API_KEY || ""
  ) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.headers = { "Content-Type": "application/json" };
    if (modelApiKey) {
      this.headers["x-model-api-key"] = modelApiKey;
    }
  }

  // ── Session lifecycle ──────────────────────────────────────

  async startSession(
    cdpUrl: string,
    modelName: string = process.env.STAGEHAND_SESSION_MODEL || "gpt-4o"
  ): Promise<StagehandResult> {
    const payload = {
      modelName,
      browser: { type: "local", cdpUrl },
    };
    const res = await this.post("/v1/sessions/start", payload);
    if (res.data && (res.data as any).sessionId) {
      this.sessionId = (res.data as any).sessionId;
    }
    return res;
  }

  async endSession(): Promise<StagehandResult> {
    this.requireSession();
    const res = await this.post(`/v1/sessions/${this.sessionId}/end`, {});
    this.sessionId = null;
    return res;
  }

  // ── Core actions ───────────────────────────────────────────

  async act(instruction: string): Promise<StagehandResult> {
    this.requireSession();
    return this.post(`/v1/sessions/${this.sessionId}/act`, {
      input: instruction,
    });
  }

  async extract(
    instruction: string,
    schema?: Record<string, unknown>
  ): Promise<StagehandResult> {
    this.requireSession();
    const payload: Record<string, unknown> = { instruction };
    if (schema) payload.schema = schema;
    return this.post(`/v1/sessions/${this.sessionId}/extract`, payload);
  }

  async observe(instruction?: string): Promise<StagehandResult> {
    this.requireSession();
    const payload: Record<string, unknown> = {};
    if (instruction) payload.instruction = instruction;
    return this.post(`/v1/sessions/${this.sessionId}/observe`, payload);
  }

  async navigate(url: string): Promise<StagehandResult> {
    this.requireSession();
    return this.post(`/v1/sessions/${this.sessionId}/navigate`, { url });
  }

  // ── Screenshot ─────────────────────────────────────────────

  async screenshot(): Promise<StagehandResult> {
    this.requireSession();
    return this.post(`/v1/sessions/${this.sessionId}/screenshot`, {});
  }

  // ── Health ─────────────────────────────────────────────────

  async healthcheck(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/healthz`);
      return res.ok;
    } catch {
      return false;
    }
  }

  // ── Internal ───────────────────────────────────────────────

  private requireSession(): void {
    if (!this.sessionId) {
      throw new Error("No active session. Call startSession() first.");
    }
  }

  private async post(
    path: string,
    body: Record<string, unknown>
  ): Promise<StagehandResult> {
    const url = `${this.baseUrl}${path}`;
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: this.headers,
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const text = await res.text();
        return { success: false, error: `${res.status}: ${text}` };
      }
      const json = await res.json();
      return { success: true, data: json.data ?? json };
    } catch (err) {
      return {
        success: false,
        error: err instanceof Error ? err.message : String(err),
      };
    }
  }
}