import { Link } from "react-router-dom";
import { CATEGORY_LABELS, SEVERITY_LABELS, SOURCE_LABELS } from "../labels";
import type { Finding } from "../types";

// Tidy LLM-written titles for display: drop the "letter says X, register
// says Y" tail (the comparison box shows it better), "(N/A)" placeholders,
// and the entity ID when the badge already shows it.
function cleanTitle(raw: string, entityId: string | null): string {
  let t = raw.split("—")[0];
  t = t.replace(/:?\s*\(N\/A\)/gi, "");
  if (entityId) t = t.replace(`(${entityId})`, "");
  return t.replace(/\s+/g, " ").trim().replace(/[:\-–—·,]\s*$/, "");
}

export function FindingCard({ finding }: { finding: Finding }) {
  const ev = finding.evidence ?? {};

  // A source comparison (letter says X / register says Y) is the insight
  // itself — always shown, no toggle.
  const hasComparison = "letter_says" in ev || "register_says" in ev;
  const letter = typeof ev.letter === "string" ? ev.letter : null;

  return (
    <div className={`card finding ${finding.severity}`}>
      <div className="head">
        <span className={`badge ${finding.severity}`}>{SEVERITY_LABELS[finding.severity]}</span>
        <span className="badge neutral">
          {CATEGORY_LABELS[finding.category] ?? finding.category}
        </span>
        <h3>{cleanTitle(finding.title, finding.entity_id)}</h3>
        {finding.entity_id && (
          <Link to={`/entities/${finding.entity_id}`} className="badge ok">
            {finding.entity_id}
          </Link>
        )}
      </div>

      <p className="desc">{finding.description}</p>

      {hasComparison && (
        <div className="compare">
          <div className="compare-col letter">
            <div className="compare-label">Per the agent letter{letter ? ` · ${letter}` : ""}</div>
            <div className="compare-val">{String(ev.letter_says ?? "not stated")}</div>
          </div>
          <div className="compare-arrow">vs</div>
          <div className="compare-col register">
            <div className="compare-label">Per our register</div>
            <div className="compare-val">{String(ev.register_says ?? "not stated")}</div>
          </div>
        </div>
      )}

      {finding.recommendation && (
        <div className="reco">
          <b>What to do</b>
          <span>{finding.recommendation}</span>
        </div>
      )}

      <div className="finding-foot">
        <span className="provenance">{SOURCE_LABELS[finding.detected_by] ?? finding.detected_by}</span>
      </div>
    </div>
  );
}
