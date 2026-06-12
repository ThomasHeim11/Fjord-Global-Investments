// Pure display helpers, extracted from the components so they can be unit
// tested in isolation (no DOM, no router, no network).
import type { Source } from "./chatStore";

// "2026-06-11 13:50:52" -> "11 Jun 2026"
export function formatDate(raw: string): string {
  const d = new Date(raw.replace(" ", "T") + "Z");
  return isNaN(d.getTime())
    ? raw.slice(0, 10)
    : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

// Tidy an LLM-written finding title for display: drop the "letter says X,
// register says Y" tail (the comparison box shows it better), "(N/A)"
// placeholders, and the entity ID when the badge already shows it.
export function cleanTitle(raw: string, entityId: string | null): string {
  let t = raw.split("—")[0];
  t = t.replace(/:?\s*\(N\/A\)/gi, "");
  if (entityId) t = t.replace(`(${entityId})`, "");
  return t.replace(/\s+/g, " ").trim().replace(/[:\-–—·,]\s*$/, "");
}

// Collapse a list of cited sources to one de-duplicated provenance line:
// "the register · luxembourg_mandate_warning.pdf · review findings".
export function sourceSummary(sources: Source[]): string {
  const parts = new Set<string>();
  for (const s of sources) {
    if (s.kind === "register") parts.add("the register");
    else if (s.kind === "letter") parts.add(s.ref.replace(/^letter:/i, ""));
    else if (s.kind === "board_update") parts.add("board notifications");
    else parts.add("review findings");
  }
  return [...parts].join(" · ");
}
