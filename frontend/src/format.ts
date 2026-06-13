/**
 * Pure display helpers, extracted from the components so they can be unit
 * tested in isolation (no DOM, no router, no network).
 */
import type { Source } from "./chatStore";

/** Formats a "YYYY-MM-DD HH:MM:SS" timestamp as "11 Jun 2026"; falls back to the date slice if unparseable. */
export function formatDate(raw: string): string {
  const d = new Date(raw.replace(" ", "T") + "Z");
  return isNaN(d.getTime())
    ? raw.slice(0, 10)
    : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

/** Formats the same timestamp as local "13:50"; returns "" if unparseable. */
export function formatTime(raw: string): string {
  const d = new Date(raw.replace(" ", "T") + "Z");
  return isNaN(d.getTime())
    ? ""
    : d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

/**
 * Tidies an LLM-written finding title for display: drops the "letter says X,
 * register says Y" tail (the comparison box shows it better), "(N/A)"
 * placeholders, and the entity ID when the badge already shows it.
 */
export function cleanTitle(raw: string, entityId: string | null): string {
  let t = raw.split("—")[0];
  t = t.replace(/:?\s*\(N\/A\)/gi, "");
  if (entityId) t = t.replace(`(${entityId})`, "");
  return t.replace(/\s+/g, " ").trim().replace(/[:\-–—·,]\s*$/, "");
}

/** A display-ready cited source: a label, plus the letter filename when openable. */
export interface SourcePart {
  label: string;
  file?: string; // set for letter sources, so the UI can open the PDF
}

/**
 * Collapses cited sources to a de-duplicated, ordered list. Letter sources
 * carry the filename so the UI can link to the in-app PDF viewer; the rest are
 * plain provenance labels.
 */
export function sourceParts(sources: Source[]): SourcePart[] {
  const seen = new Set<string>();
  const parts: SourcePart[] = [];
  for (const s of sources) {
    let label: string;
    let file: string | undefined;
    if (s.kind === "register") label = "the register";
    else if (s.kind === "letter") {
      file = s.ref.replace(/^letter:\s*/i, "").trim();
      label = file;
    } else if (s.kind === "board_update") label = "board notifications";
    else label = "review findings";
    if (seen.has(label)) continue;
    seen.add(label);
    parts.push({ label, file });
  }
  return parts;
}
