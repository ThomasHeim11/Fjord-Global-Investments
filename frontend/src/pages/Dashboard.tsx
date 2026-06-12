import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { FindingCard } from "../components/FindingCard";
import { Hero } from "../components/Hero";
import { CATEGORY_LABELS, SEVERITY_LABELS } from "../labels";
import type { DigestResponse, Severity } from "../types";

const SEVERITIES: Severity[] = ["critical", "warning", "info"];
const PAGE_SIZE = 12;

// "2026-06-11 13:50:52" → "11 Jun 2026"
function formatDate(raw: string): string {
  const d = new Date(raw.replace(" ", "T") + "Z");
  return isNaN(d.getTime())
    ? raw.slice(0, 10)
    : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function Dashboard() {
  const [digest, setDigest] = useState<DigestResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<Severity | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const load = () => api.getDigest().then(setDigest).catch((e) => setError(String(e)));
  useEffect(() => { load(); }, []);
  useEffect(() => { setPage(1); }, [severityFilter, categoryFilter]);

  // One button: run a genuine live re-scan first. If the AI is rate-limited,
  // fall back to replaying the last cached scan so a result always appears.
  const runDigest = async () => {
    setRunning(true);
    setError(null);
    setNotice(null);
    try {
      await api.triggerDigest(true);   // live re-scan
      await load();
    } catch {
      try {
        await api.triggerDigest(false); // fall back to the cached scan
        await load();
        setNotice("The live scan was rate-limited, so this shows your last cached review. Try again in a moment for a fresh scan.");
      } catch (e2) {
        setError(String(e2));
      }
    } finally {
      setRunning(false);
    }
  };

  const findings = digest?.findings ?? [];
  const categories = useMemo(() => [...new Set(findings.map((f) => f.category))], [findings]);

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
      {running && (
        <div className="progress-top" role="progressbar" aria-label="Reviewing">
          <span />
        </div>
      )}
      <Hero />

      <div className="review-bar">
        <div className="review-bar-inner">
          <div className="review-bar-meta">
            {run ? (
              <>
                <span className="review-bar-label">Last reviewed</span>
                <span className="review-bar-value">{formatDate(run.created_at)}</span>
                <span className="review-bar-dot" />
                <span className="review-bar-value">{run.stats.total} issues found</span>
              </>
            ) : (
              <span className="review-bar-label">No review run yet</span>
            )}
          </div>
          <button className="run-btn" onClick={runDigest} disabled={running}>
            {running ? "Reviewing…" : run ? "Run review again" : "Run review"}
          </button>
        </div>
      </div>

      <div className="page">
        <p className="review-explainer">
          <strong>Run review</strong> reads your register, board notifications and
          agent letters, finds every governance issue, ranks each one
          (Act now / Review soon / For awareness) and writes a recommended action.
          Each press runs a fresh live scan; if the AI is momentarily
          rate-limited it falls back to your last cached review, so you always
          get a result.
        </p>

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

        {run?.summary && (
          <div className="summary-box">
            <h2>Summary for the General Counsel</h2>
            {run.summary.split(/\n+/).filter(Boolean).map((para, i) => (
              <p key={i}>{para.replace(/^[-•*]\s*/, "")}</p>
            ))}
          </div>
        )}

        {run && (
          <>
            <div className="stat-hint">Click a card to filter the list</div>
            <div className="stat-row">
              <button className={`card stat ${!severityFilter ? "active" : ""}`}
                      onClick={() => setSeverityFilter(null)}>
                <div className="num">{run.stats.total}</div>
                <div className="label">All issues</div>
              </button>
              {SEVERITIES.map((s) => (
                <button key={s} className={`card stat ${s} ${severityFilter === s ? "active" : ""}`}
                        onClick={() => setSeverityFilter(severityFilter === s ? null : s)}>
                  <div className="num">{run.stats[s]}</div>
                  <div className="label">{SEVERITY_LABELS[s]}</div>
                </button>
              ))}
            </div>

            <div className="controls">
              <span className="controls-label">Filter by type</span>
              {categories.map((c) => (
                <button key={c} className={`chip ${categoryFilter === c ? "on" : ""}`}
                        onClick={() => setCategoryFilter(categoryFilter === c ? null : c)}>
                  {CATEGORY_LABELS[c] ?? c}
                </button>
              ))}
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
