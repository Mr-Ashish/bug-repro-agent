/**
 * Plane adapter — domain knowledge for the Plane app.
 * URLs, credentials, navigation patterns, API endpoints.
 */

export const PlaneAdapter = {
  // ── Connection ─────────────────────────────────────────────
  baseUrl: process.env.PLANE_URL || "http://localhost",
  email: process.env.PLANE_EMAIL || "admin@admin.com",
  password: process.env.PLANE_PASSWORD || "qweQWE123!@#",
  workspace: process.env.PLANE_WORKSPACE || "plane-dev",
  project: process.env.PLANE_PROJECT || "SEED",

  // ── URLs ───────────────────────────────────────────────────
  get loginUrl() {
    return `${this.baseUrl}/`;
  },
  get workspaceUrl() {
    return `${this.baseUrl}/${this.workspace}/`;
  },
  get projectUrl() {
    return `${this.baseUrl}/${this.workspace}/projects/`;
  },
  get apiBase() {
    return `${this.baseUrl}/api/v1/workspaces/${this.workspace}`;
  },

  // ── API helpers ────────────────────────────────────────────
  apiHeaders(cookie?: string): Record<string, string> {
    const h: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (cookie) h["Cookie"] = cookie;
    return h;
  },

  // ── Navigation patterns ────────────────────────────────────
  issuesPath(projectId: string) {
    return `/${this.workspace}/projects/${projectId}/issues/`;
  },
  stickiesPath() {
    return `/${this.workspace}/stickies/`;
  },
  cyclesPath(projectId: string) {
    return `/${this.workspace}/projects/${projectId}/cycles/`;
  },

  // ── Existing seed data ─────────────────────────────────────
  seedData: {
    issues: 30,
    states: 5,
    cycles: 3,
    modules: 4,
    pages: 5,
    subIssues: 5, // 5 issues with sub-issues
    stickies: 0,  // need to be created for bug #9050
  },
} as const;