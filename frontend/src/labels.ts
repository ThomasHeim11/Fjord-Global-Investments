import type { Severity } from "./types";

// Plain language for non-technical (legal / tax) users — no dev jargon.
export const SEVERITY_LABELS: Record<Severity, string> = {
  critical: "Act now",
  warning: "Review soon",
  info: "For awareness",
};

export const CATEGORY_LABELS: Record<string, string> = {
  data_integrity: "Record problem",
  mandate: "Board mandate",
  filing: "Annual filing",
  status: "Entity status",
  governance: "Governance",
  conflict: "Records disagree",
  unknown_entity: "Unknown entity",
};

export const SOURCE_LABELS: Record<string, string> = {
  "llm:reconciliation": "Agent letter checked against the register",
  "llm:analysis": "Register review",
  "llm:resolution": "Notification matched to the register",
};
