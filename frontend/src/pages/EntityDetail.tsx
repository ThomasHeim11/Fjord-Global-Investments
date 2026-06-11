import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { FindingCard } from "../components/FindingCard";
import type { EntityDetail as Detail } from "../types";

export function EntityDetail() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) api.getEntity(id).then(setDetail).catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <div className="page"><div className="card">{error}</div></div>;
  if (!detail) return <div className="page"><div className="empty">Loading…</div></div>;

  const { entity, updates, findings, children } = detail;

  return (
    <div className="page">
      <p className="muted"><Link to="/entities">← Register</Link></p>
      <h1>{entity.entity_name || `${entity.entity_id} (name missing)`}</h1>
      <p className="muted">{entity.entity_id} · {entity.entity_type} · {entity.jurisdiction}</p>

      <div className="card" style={{ marginTop: 16 }}>
        <dl className="kv">
          <dt>Status</dt><dd>{entity.status}</dd>
          <dt>Asset</dt><dd>{entity.asset_class} — {entity.asset_description}</dd>
          <dt>Incorporated</dt><dd>{entity.incorporation_date}</dd>
          <dt>Parent</dt>
          <dd>{entity.parent_entity_id
            ? <Link to={`/entities/${entity.parent_entity_id}`}>{entity.parent_entity_id}</Link>
            : "— (top of structure)"}{entity.ownership_pct != null && ` · ${entity.ownership_pct}% owned`}</dd>
          <dt>Registered address</dt><dd>{entity.registered_address}</dd>
          <dt>Registered agent</dt><dd>{entity.registered_agent}</dd>
          <dt>Board</dt><dd>{entity.board_members}</dd>
          <dt>Mandate expiry</dt><dd>{entity.board_mandate_expiry}</dd>
          <dt>Annual filing</dt>
          <dd>due {entity.annual_filing_due} · {entity.annual_filing_status}</dd>
        </dl>
      </div>

      {findings.length > 0 && (
        <>
          <h2 className="section-title">Findings ({findings.length})</h2>
          {findings.map((f) => <FindingCard key={f.id} finding={f} />)}
        </>
      )}

      {updates.length > 0 && (
        <>
          <h2 className="section-title">Board-change notifications ({updates.length})</h2>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table>
              <thead>
                <tr><th>Date</th><th>Type</th><th>Details</th><th>Source</th><th>Match</th></tr>
              </thead>
              <tbody>
                {updates.map((u) => (
                  <tr key={u.id} style={{ cursor: "default" }}>
                    <td>{u.date_iso ?? u.date_raw}</td>
                    <td>{u.change_type}</td>
                    <td>{u.details}</td>
                    <td className="muted">{u.source}</td>
                    <td>{u.resolution_confidence != null &&
                      <span className="badge neutral" title={u.resolution_note ?? ""}>
                        {(u.resolution_confidence * 100).toFixed(0)}%
                      </span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {children.length > 0 && (
        <>
          <h2 className="section-title">Direct subsidiaries ({children.length})</h2>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table>
              <thead><tr><th>ID</th><th>Name</th><th>Jurisdiction</th><th>Status</th></tr></thead>
              <tbody>
                {children.map((c) => (
                  <tr key={c.entity_id}>
                    <td><Link to={`/entities/${c.entity_id}`}>{c.entity_id}</Link></td>
                    <td><Link to={`/entities/${c.entity_id}`}>{c.entity_name || "(name missing)"}</Link></td>
                    <td>{c.jurisdiction}</td>
                    <td>{c.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
