export interface Entity {
  entity_id: string;
  entity_name: string | null;
  entity_type: string;
  jurisdiction: string;
  incorporation_date: string;
  parent_entity_id: string | null;
  ownership_pct: number | null;
  registered_address: string;
  board_members: string;
  board_mandate_expiry: string;
  annual_filing_due: string;
  annual_filing_status: string;
  registered_agent: string;
  status: string;
  asset_class: string;
  asset_description: string;
}

export type Severity = "critical" | "warning" | "info";

export interface Finding {
  id: number;
  run_id: number;
  category: string;
  severity: Severity;
  entity_id: string | null;
  entity_name: string | null;
  title: string;
  description: string;
  evidence: Record<string, unknown>;
  recommendation: string | null;
  detected_by: string;
}

export interface DigestRun {
  id: number;
  created_at: string;
  status: "completed" | "failed";
  summary: string | null;
  model: string;
  stats: { total: number; critical: number; warning: number; info: number };
}

export interface DigestResponse {
  run: DigestRun | null;
  findings: Finding[];
}

export interface BoardUpdate {
  id: number;
  date_raw: string;
  date_iso: string | null;
  entity_name_raw: string;
  change_type: string;
  details: string;
  source: string;
  resolved_entity_id: string | null;
  resolution_confidence: number | null;
  resolution_note: string | null;
}

export interface EntityDetail {
  entity: Entity;
  updates: BoardUpdate[];
  findings: Finding[];
  children: Pick<Entity, "entity_id" | "entity_name" | "jurisdiction" | "status">[];
}

export interface Meta {
  jurisdictions: string[];
  statuses: string[];
  asset_classes: string[];
  filing_statuses: string[];
}
