/**
 * Display labels mapping internal enum values (severity, category, detection
 * source) to the human-facing wording shown in the UI.
 */
import type { Severity } from "./types";

/**
 * Risk level: the standard High/Medium/Low scale legal, tax and compliance
 * teams use on risk registers and audit findings. Conveys severity; the
 * per-finding "What to do" carries the action.
 */
export const SEVERITY_LABELS: Record<Severity, string> = {
  critical: "High",
  warning: "Medium",
  info: "Low",
};

/** Plain-language names for each finding category. */
export const CATEGORY_LABELS: Record<string, string> = {
  data_integrity: "Record problem",
  mandate: "Board mandate",
  filing: "Annual filing",
  status: "Entity status",
  governance: "Governance",
  conflict: "Records disagree",
  unknown_entity: "Unknown entity",
};

/** Describes how a finding was detected, by the agent pipeline that produced it. */
export const SOURCE_LABELS: Record<string, string> = {
  "llm:reconciliation": "Agent letter checked against the register",
  "llm:analysis": "Register review",
  "llm:resolution": "Notification matched to the register",
};
