/**
 * Renders a single review finding: severity/category badges, the source
 * comparison (letter vs register), recommendation, and a button to open the
 * cited letter in the in-app PDF viewer with the quoted line highlighted.
 */
import { lazy, Suspense, useState } from "react";
import { Link } from "react-router-dom";
import { cleanTitle } from "../format";
import { CATEGORY_LABELS, SEVERITY_LABELS, SOURCE_LABELS } from "../labels";
import type { Finding } from "../types";

// Load the PDF viewer (and the heavy PDF.js bundle) only when a letter is
// actually opened, so it stays out of the initial page load.
const PdfViewer = lazy(() => import("./PdfViewer").then((m) => ({ default: m.PdfViewer })));

const API = "http://127.0.0.1:8000/api";

/**
 * Returns the text to highlight in the PDF. For an unknown-entity finding the
 * quote is wrapped ("names 'FGI …'"), so pull the inner name to match the
 * letter; otherwise the quoted value (a date, a board list) is already verbatim.
 */
function pdfSearchTerm(letterSays: string): string {
  const m = letterSays.match(/['"]([^'"]+)['"]/);
  return m ? m[1] : letterSays;
}

/** Card UI for one Finding, with optional source comparison and PDF evidence link. */
export function FindingCard({ finding }: { finding: Finding }) {
  const ev = finding.evidence ?? {};
  const [showPdf, setShowPdf] = useState(false);

  // A source comparison (letter says X / register says Y) is the insight
  // itself — always shown, no toggle.
  const hasComparison = "letter_says" in ev || "register_says" in ev;
  const letter = typeof ev.letter === "string" ? ev.letter : null;
  const letterSays = String(ev.letter_says ?? "not stated");
  const pdfUrl = letter ? `${API}/letters/${encodeURIComponent(letter)}` : null;

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
            <div className="compare-label">
              Per the agent letter
              {letter && pdfUrl && (
                <>
                  {" · "}
                  <button type="button" className="evidence-link" onClick={() => setShowPdf(true)}
                          title="Open the letter and highlight this line">
                    {letter} ↗
                  </button>
                </>
              )}
            </div>
            <div className="compare-val">{letterSays}</div>
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

      {showPdf && letter && pdfUrl && (
        <Suspense fallback={<div className="pdf-overlay"><div className="pdf-status">Loading viewer…</div></div>}>
          <PdfViewer
            url={pdfUrl}
            filename={letter}
            highlight={pdfSearchTerm(letterSays)}
            onClose={() => setShowPdf(false)}
          />
        </Suspense>
      )}
    </div>
  );
}
