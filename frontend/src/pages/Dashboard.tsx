/**
 * Review page: runs the portfolio review and presents the resulting findings,
 * ranked by severity, with severity/category filters and pagination.
 */
import { useEffect, useMemo, useState } from "react";
import { FindingCard } from "../components/FindingCard";
import { Hero } from "../components/Hero";
import { formatDate, formatTime } from "../format";
import { CATEGORY_LABELS, SEVERITY_LABELS } from "../labels";
import { useReview } from "../ReviewContext";
import type { Severity } from "../types";

const SEVERITIES: Severity[] = ["critical", "warning", "info"];
const PAGE_SIZE = 12;

/** The review page: the Run/Stop control, the findings list and its filters. */
export function Dashboard() {
  // The run lives at app level, so it keeps going if you navigate away.
  const { digest, running, error, notice, runReview, stopReview } = useReview();
  const [severityFilter, setSeverityFilter] = useState<Severity | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  // changing a filter resets to the first page so results stay in view
  useEffect(() => { setPage(1); }, [severityFilter, categoryFilter]);

  const findings = digest?.findings ?? [];
  const categories = useMemo(() => [...new Set(findings.map((f) => f.category))], [findings]);

  // How many findings each category yields under the *current* severity filter,
  // so a chip's count reflects what clicking it would actually show.
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const f of findings) {
      if (severityFilter && f.severity !== severityFilter) continue;
      counts[f.category] = (counts[f.category] ?? 0) + 1;
    }
    return counts;
  }, [findings, severityFilter]);

  const filtered = findings.filter(
    (f) =>
      (!severityFilter || f.severity === severityFilter) &&
      (!categoryFilter || f.category === categoryFilter),
  );

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const pageItems = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);

  const run = digest?.run;
  const filtersActive = severityFilter || categoryFilter;

  return (
    <>
      <Hero />

      <div className="review-bar">
        <div className="review-bar-inner">
          <div className="review-bar-meta">
            {run ? (
              <>
                <span className="review-bar-label">Last reviewed</span>
                <span className="review-bar-value">
                  {formatDate(run.created_at)}
                  {formatTime(run.created_at) && (
                    <span className="review-bar-time"> · {formatTime(run.created_at)}</span>
                  )}
                </span>
              </>
            ) : (
              <span className="review-bar-label">No review run yet</span>
            )}
          </div>
          {/* Run/Stop toggle: while a review is in flight the button stops waiting on it. */}
          {running ? (
            <button className="run-btn stop" onClick={stopReview} title="Stop waiting for this review">
              Stop
            </button>
          ) : (
            <button
              className="run-btn"
              onClick={runReview}
              title="Re-reads your register, notifications and letters, ranks every issue by risk level and recommends an action."
            >
              Run portfolio review
            </button>
          )}
        </div>
      </div>

      <div className="page">
        {notice && <div className="review-notice">{notice}</div>}
        {error && <div className="card error-card">{error}</div>}

        {!run && !running && (
          <div className="review-empty">
            <div className="review-empty-mark">✦</div>
            <h2>Ready when you are</h2>
            <p>
              Press <b>Run review</b> above to analyse the register, board
              notifications and agent letters. The first run takes about a minute;
              after that it is instant.
            </p>
          </div>
        )}
        {running && (
          <div className="reviewing-card">
            <div className="reviewing-spinner" />
            <div>
              <div className="reviewing-title">Reviewing the portfolio…</div>
              <div className="muted">
                Matching notifications, analysing the register and reconciling agent letters. This takes about a minute.
              </div>
            </div>
          </div>
        )}

        {run && (
          <>
            <div className="review-headline">
              <h2>{run.stats.total} issues found</h2>
              <p>
                across the register, board notifications and agent letters.
                Click a card to filter the list below.
              </p>
            </div>
            <div className="stat-row" role="group" aria-label="Filter by risk level">
              <button className={`card stat ${!severityFilter ? "active" : ""}`}
                      aria-pressed={!severityFilter}
                      title="Show all issues"
                      onClick={() => setSeverityFilter(null)}>
                <div className="num">{run.stats.total}</div>
                <div className="label">All issues</div>
              </button>
              {SEVERITIES.map((s) => (
                <button key={s} className={`card stat ${s} ${severityFilter === s ? "active" : ""}`}
                        aria-pressed={severityFilter === s}
                        title={`Filter to ${SEVERITY_LABELS[s]} risk`}
                        onClick={() => setSeverityFilter(severityFilter === s ? null : s)}>
                  <div className="num">{run.stats[s]}</div>
                  <div className="label">{SEVERITY_LABELS[s]}</div>
                </button>
              ))}
            </div>

            {run.summary && (
              <div className="summary-box">
                <h2>Summary</h2>
                {run.summary.split(/\n+/).filter(Boolean).map((para, i) => (
                  <p key={i}>{para.replace(/^[-•*]\s*/, "")}</p>
                ))}
              </div>
            )}

            <div className="controls" role="group" aria-label="Filter by type">
              <span className="controls-label">Filter by type</span>
              {categories.map((c) => {
                const count = categoryCounts[c] ?? 0;
                const selected = categoryFilter === c;
                return (
                  <button key={c} className={`chip ${selected ? "on" : ""}`}
                          aria-pressed={selected}
                          disabled={count === 0 && !selected}
                          onClick={() => setCategoryFilter(selected ? null : c)}>
                    {CATEGORY_LABELS[c] ?? c}
                    <span className="chip-count">{count}</span>
                  </button>
                );
              })}
              {filtersActive && (
                <button className="chip clear"
                        onClick={() => { setSeverityFilter(null); setCategoryFilter(null); }}>
                  Clear filters
                </button>
              )}
            </div>

            <div className="list-head">
              <span>
                {severityFilter ? SEVERITY_LABELS[severityFilter] : "All issues"}
                {categoryFilter ? ` · ${CATEGORY_LABELS[categoryFilter] ?? categoryFilter}` : ""}
              </span>
              <span className="muted">{filtered.length} {filtered.length === 1 ? "issue" : "issues"}</span>
            </div>

            {pageItems.map((f) => <FindingCard key={f.id} finding={f} />)}

            {filtered.length === 0 && (
              <div className="card empty">No issues match the current filters.</div>
            )}

            {pageCount > 1 && (
              <div className="pager">
                <button className="chip" disabled={current === 1} onClick={() => setPage(current - 1)}>
                  ← Previous
                </button>
                <span className="pager-info">Page {current} of {pageCount}</span>
                <button className="chip" disabled={current === pageCount} onClick={() => setPage(current + 1)}>
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
