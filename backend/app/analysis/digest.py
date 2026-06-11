"""Digest orchestration: the POST /digest pipeline. Pure LLM by design —
every finding comes from a model pass.

  1. resolution   — LLM matches messy update names → register ids
  2. unresolved   — updates that match nothing become unknown_entity findings
  3. analyze      — LLM reviews register + notifications, surfaces all risks
  4. reconcile    — LLM compares each agent letter against the register
  5. recommend    — LLM writes one action per finding + executive summary

Requires ANTHROPIC_API_KEY; raises LLMNotConfigured otherwise.
"""
import json

from ..config import LLM_MODEL
from ..db import get_conn
from .models import SEVERITY_ORDER, Finding


def _unresolved_update_findings() -> list[Finding]:
    """Board updates whose entity name resolved to nothing in the register."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT entity_name_raw, resolution_note,
                      COUNT(*) AS n, GROUP_CONCAT(change_type, '; ') AS change_types
               FROM board_updates
               WHERE resolved_entity_id IS NULL AND resolution_confidence IS NOT NULL
               GROUP BY entity_name_raw"""
        ).fetchall()
    return [
        Finding(
            category="unknown_entity",
            severity="warning",
            title=f"Notification for entity not in register: {r['entity_name_raw']}",
            description=(
                f"{r['n']} notification(s) ({r['change_types']}) reference "
                f"'{r['entity_name_raw']}', which could not be matched to any register entity. "
                f"Either the register is missing an entity or the notification is not the fund's."
            ),
            detected_by="llm:resolution",
            entity_name=r["entity_name_raw"],
            evidence={"resolution_note": r["resolution_note"]},
        )
        for r in rows
    ]


def _dedup(findings: list[Finding]) -> list[Finding]:
    """Collapse the same issue surfaced by more than one pass.

    A finding is a duplicate of an earlier one when they share a category AND
    refer to the same entity — matched by register ID, by entity name, or (for
    findings carrying neither, e.g. a jurisdiction note) by normalized title.
    Distinct issues for one entity survive because the category differs, and a
    genuinely multi-field conflict (e.g. a letter disagreeing on both mandate
    date and board) survives because each carries a distinct title.
    """
    seen: set[tuple] = set()
    out: list[Finding] = []
    for f in findings:
        ident = (
            f"id:{f.entity_id}" if f.entity_id
            else f"name:{(f.entity_name or '').lower().strip()}" if f.entity_name
            else f"title:{' '.join(f.title.lower().split())[:60]}"
        )
        # 'conflict' findings include the title in the key, so a letter that
        # disagrees with the register on two fields keeps both findings; for
        # every other category it's one finding per (entity, category).
        key = ((f.category, ident, " ".join(f.title.lower().split())[:60])
               if f.category == "conflict" else (f.category, ident))
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _log(msg: str) -> None:
    print(f"[digest] {msg}", flush=True)


def run_digest() -> dict:
    from ..llm.analyze import analyze
    from ..llm.recommend import recommend
    from ..llm.reconcile import reconcile_letters
    from ..llm.resolution import resolve_all

    _log("1/5 matching notification names to the register…")
    resolve_all()
    findings = _unresolved_update_findings()
    _log("2/5 analysing the register (this is the longest step)…")
    findings += analyze()
    _log(f"    register analysis: {len(findings)} findings so far")
    _log("3/5 reconciling agent letters against the register…")
    findings += reconcile_letters()

    findings = _dedup(findings)
    _log(f"4/5 {len(findings)} findings after de-duplication")

    _log("5/5 writing recommendations and executive summary…")
    summary = recommend(findings)
    _log("done — saving review")

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.category))

    stats = {
        "total": len(findings),
        "critical": sum(1 for f in findings if f.severity == "critical"),
        "warning": sum(1 for f in findings if f.severity == "warning"),
        "info": sum(1 for f in findings if f.severity == "info"),
    }

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO digest_runs (status, summary, model, stats_json) VALUES (?, ?, ?, ?)",
            ("completed", summary, LLM_MODEL, json.dumps(stats)),
        )
        run_id = cur.lastrowid
        for f in findings:
            conn.execute(
                """INSERT INTO findings
                   (run_id, category, severity, entity_id, entity_name, title,
                    description, evidence_json, recommendation, detected_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, f.category, f.severity, f.entity_id, f.entity_name,
                 f.title, f.description, json.dumps(f.evidence, ensure_ascii=False),
                 f.recommendation, f.detected_by),
            )

    return {"run_id": run_id, "status": "completed", "summary": summary, "stats": stats}
