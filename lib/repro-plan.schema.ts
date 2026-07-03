/**
 * TypeScript types for the repro-plan.json artifact.
 */

export interface ReproPlan {
  issue: {
    number: number;
    title: string;
    url: string;
  };
  bugClass: BugClass;
  preconditions: string[];
  steps: string[];
  oracle: OracleSpec;
  teardown?: string;
}

export type BugClass =
  | "form-validation"
  | "state-persistence"
  | "ui-interaction"
  | "api-error"
  | "visual"
  | "other";

export interface OracleSpec {
  type: "screenshot-vision";
  expected: string;
}

export interface ActionLogEntry {
  action: "navigate" | "act" | "observe" | "extract" | "screenshot";
  instruction: string;
  result: Record<string, unknown>;
  timestamp: string;
}

export interface Verdict {
  reproduced: boolean;
  confidence: "high" | "medium" | "low";
  reasoning: string;
  evidenceFile: string;
}