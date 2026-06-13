/**
 * Register browser: a searchable, filterable, sortable table of all
 * subsidiary entities. Rows link through to the single-entity drilldown.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Entity, Meta } from "../types";

type SortKey = keyof Pick<Entity,
  "entity_id" | "entity_name" | "jurisdiction" | "status" |
  "annual_filing_status" | "board_mandate_expiry" | "asset_class">;

// Maps a filing/status value to its badge variant (colour) in the table.
const FILING_BADGE: Record<string, string> = {
  Filed: "ok", Pending: "info", Overdue: "critical", Unknown: "warning",
};
const STATUS_BADGE: Record<string, string> = {
  Active: "ok", Dissolved: "neutral", "In liquidation": "warning", Dormant: "neutral",
};

/** The register browser: search box, dropdown filters and the sortable entity table. */
export function Entities() {
  const navigate = useNavigate();
  const [entities, setEntities] = useState<Entity[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "entity_id", dir: 1 });

  // load the filter dropdown options once
  useEffect(() => { api.getMeta().then(setMeta); }, []);
  // re-query the server whenever the filters or search text change
  useEffect(() => {
    const params = { ...filters };
    if (q) params.q = q;
    api.getEntities(params).then(setEntities);
  }, [filters, q]);

  // client-side sort of the server's result set by the active column and direction
  const sorted = useMemo(() => {
    return [...entities].sort((a, b) => {
      const va = a[sort.key] ?? "";
      const vb = b[sort.key] ?? "";
      return va < vb ? -sort.dir : va > vb ? sort.dir : 0;
    });
  }, [entities, sort]);

  // click a column: sort by it, or flip direction if it is already the sort key
  const toggleSort = (key: SortKey) =>
    setSort((s) => ({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : 1 }));

  // set or clear a single filter; an empty value removes the key entirely
  const setFilter = (key: string, value: string) =>
    setFilters((f) => {
      const next = { ...f };
      if (value) next[key] = value; else delete next[key];
      return next;
    });

  const arrow = (key: SortKey) => (sort.key === key ? (sort.dir === 1 ? " ↑" : " ↓") : "");

  return (
    <div className="page">
      <h1>Subsidiary register</h1>
      <p className="muted">{sorted.length} entities</p>

      <div className="controls">
        <input type="text" placeholder="Search name or ID…" value={q}
               onChange={(e) => setQ(e.target.value)} style={{ minWidth: 220 }} />
        {meta && (
          <>
            <select value={filters.jurisdiction ?? ""}
                    onChange={(e) => setFilter("jurisdiction", e.target.value)}>
              <option value="">All jurisdictions</option>
              {meta.jurisdictions.map((j) => <option key={j}>{j}</option>)}
            </select>
            <select value={filters.status ?? ""}
                    onChange={(e) => setFilter("status", e.target.value)}>
              <option value="">All statuses</option>
              {meta.statuses.map((s) => <option key={s}>{s}</option>)}
            </select>
            <select value={filters.asset_class ?? ""}
                    onChange={(e) => setFilter("asset_class", e.target.value)}>
              <option value="">All asset classes</option>
              {meta.asset_classes.map((a) => <option key={a}>{a}</option>)}
            </select>
            <select value={filters.filing_status ?? ""}
                    onChange={(e) => setFilter("filing_status", e.target.value)}>
              <option value="">All filing statuses</option>
              {meta.filing_statuses.map((f) => <option key={f}>{f}</option>)}
            </select>
          </>
        )}
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead>
            <tr>
              <th onClick={() => toggleSort("entity_id")}>ID{arrow("entity_id")}</th>
              <th onClick={() => toggleSort("entity_name")}>Name{arrow("entity_name")}</th>
              <th onClick={() => toggleSort("jurisdiction")}>Jurisdiction{arrow("jurisdiction")}</th>
              <th onClick={() => toggleSort("asset_class")}>Asset class{arrow("asset_class")}</th>
              <th onClick={() => toggleSort("status")}>Status{arrow("status")}</th>
              <th onClick={() => toggleSort("annual_filing_status")}>Filing{arrow("annual_filing_status")}</th>
              <th onClick={() => toggleSort("board_mandate_expiry")}>Mandate expiry{arrow("board_mandate_expiry")}</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((e) => (
              <tr key={e.entity_id} onClick={() => navigate(`/entities/${e.entity_id}`)}>
                <td>{e.entity_id}</td>
                <td>{e.entity_name || <span className="badge critical">missing name</span>}</td>
                <td>{e.jurisdiction}</td>
                <td>{e.asset_class}</td>
                <td><span className={`badge ${STATUS_BADGE[e.status] ?? "neutral"}`}>{e.status}</span></td>
                <td><span className={`badge ${FILING_BADGE[e.annual_filing_status] ?? "neutral"}`}>{e.annual_filing_status}</span></td>
                <td>{e.board_mandate_expiry}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
