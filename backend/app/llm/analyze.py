"""LLM register analysis — the primary risk-detection pass.

Structured as three LLM passes, each sized to fit free-tier token budgets and
to scale linearly with register size:

  1. per-entity review, in batches — mandates, filings, status, record quality
  2. cross-entity review, compact projection — duplicates, broken ownership
     references, director concentration, structural oddities
  3. notifications review — duplicates, contradictions, implausible updates

Design decision (deliberate): the LLM is the analyst on every pass, so the
review generalises to risk patterns nobody anticipated and absorbs new
jurisdictions or letter formats without code changes. Batching is what makes
the same pipeline work at 100 or 10,000 entities.
"""
from typing import Literal

from pydantic import BaseModel

from ..analysis.models import Finding
from ..config import LLM_PROVIDER, REFERENCE_DATE
from ..db import get_conn
from .client import parse_structured

# Small local models (Ollama/gemma) reliably handle only a handful of entities
# per call; hosted models take the full batch. Adapt so the pipeline completes
# on either backend.
ENTITY_BATCH = 5 if LLM_PROVIDER == "ollama" else 25

TITLE_RULE = """
Titles MUST be specific: name the entity (legal name when known) and the
concrete issue, e.g. "Annual filing overdue: FGI Dublin Mixed-Use III Ltd".
Never a generic label like "Overdue Filing". Never use the em-dash character,
"(N/A)", or a parenthesised register ID in the title (the ID goes in the
entity_id field); if the entity name is unknown, use the register ID alone."""


class AnalysisFinding(BaseModel):
    category: Literal["data_integrity", "mandate", "filing", "status", "governance"]
    severity: Literal["critical", "warning", "info"]
    entity_id: str | None     # register ID (FGI-xxx) or null
    entity_name: str | None
    title: str
    description: str
    evidence: str             # the specific data values supporting the finding


class AnalysisResult(BaseModel):
    findings: list[AnalysisFinding]


PER_ENTITY_SYSTEM = f"""You are a senior governance lawyer reviewing entries from a sovereign wealth
fund's subsidiary register, days before a board meeting. Today's date is
{REFERENCE_DATE}. All date arithmetic and reference checks are PRECOMPUTED in
annotations: mandate expiries say "(EXPIRED n days ago)" or "(in n days)",
incorporation dates say "(IN THE FUTURE)" when invalid, parent references say
"(VALID)" or "(NOT IN REGISTER)". The annotations are authoritative — never
contradict them and never redo the arithmetic yourself.

For EACH entity given, report findings ONLY for:
- Board mandate annotated EXPIRED (critical), or annotated as expiring in 60
  days or fewer (warning). Do NOT flag mandates beyond 60 days.
- Annual filing status exactly 'Overdue' (critical) or 'Unknown' (warning).
  'Pending' and 'Filed' are normal — never flag them on their own.
- Record quality: missing entity name (critical), incorporation date whose
  annotation LITERALLY CONTAINS the text "IN THE FUTURE" (warning) — if that
  exact text is not present, the date is valid; never flag it, never compute
  your own. jurisdiction outside the fund's operating list / not a real country
  (critical — investigate immediately), parent annotated NOT IN REGISTER
  (critical — never flag a parent annotated VALID).
- Status: dissolved/dormant/in-liquidation entities still carrying Pending or
  Overdue filing obligations (warning), or otherwise contradictory records.

One finding per issue per entity, quoting the data values in the evidence
field. Report nothing for clean entities. Be exhaustive on real issues; do
not invent borderline ones.
Categories: mandate (board mandates), filing (annual filings), status
(status contradictions), data_integrity (record quality).""" + TITLE_RULE

CROSS_ENTITY_SYSTEM = """You are a senior governance lawyer reviewing a sovereign wealth fund's full
subsidiary register for STRUCTURAL patterns (single-entity issues are handled
elsewhere — do not repeat them). Check and report:
- Duplicate entity names: distinct register rows sharing one legal name
  (warning, one finding per duplicated name, list the row IDs).
- Director concentration: individuals holding 8 or more board seats (one
  info finding per such person). In the evidence list ONLY the entity IDs
  whose board membership actually contains that exact name; the seat count
  you state must equal the number of entities you list — do not include an
  entity unless the person's name literally appears in its board.
- Any other structural oddity a General Counsel should hear about (suspicious
  clusters, implausible ownership patterns).
Do NOT report single-entity record issues (missing names, broken parent
references, bad dates) — those are handled elsewhere.
Quote the names, IDs and counts in the description AND evidence — a duplicate
name finding must list the duplicated name and every row ID sharing it.
Categories: data_integrity (duplicates), governance (concentration, patterns).""" + TITLE_RULE

NOTIFICATIONS_SYSTEM = """You are a senior governance lawyer reviewing board-change notifications
received by a sovereign wealth fund. The fund's register entity names are
provided for reference. Check and report:
- Duplicate notifications: the same event reported more than once from
  different sources (info, list the notification ids).
- Notifications that contradict each other or describe implausible events.
- Notifications about entities whose register status makes the update odd
  (e.g. board changes at a dissolved entity).
Do NOT flag name-matching issues (handled elsewhere). Quote notification ids
and values in the evidence.
Categories: data_integrity (duplicates), status (status mismatches),
governance (other oddities).""" + TITLE_RULE


def _to_findings(result: AnalysisResult, valid_ids: set[str], pass_name: str) -> list[Finding]:
    return [
        Finding(
            category=f.category,
            severity=f.severity if f.severity in ("critical", "warning", "info") else "warning",
            title=f.title,
            description=f.description,
            detected_by=f"llm:{pass_name}",
            entity_id=f.entity_id if f.entity_id in valid_ids else None,
            entity_name=f.entity_name,
            evidence={"observation": f.evidence},
        )
        for f in result.findings
    ]


def _annotate(r, valid_ids: set[str], today) -> str:
    """Precompute the arithmetic so the model only does judgment. The LLM
    still decides what is a finding — this is data preparation, like the
    date normalization at ingest."""
    from datetime import date

    expiry = r["board_mandate_expiry"]
    try:
        days = (date.fromisoformat(expiry) - today).days
        mandate = f"{expiry} ({'EXPIRED ' + str(-days) + ' days ago' if days < 0 else 'in ' + str(days) + ' days'})"
    except (TypeError, ValueError):
        mandate = str(expiry)

    parent = r["parent_entity_id"]
    parent_note = (
        "none (top of structure)" if not parent
        else f"{parent} ({'VALID' if parent in valid_ids else 'NOT IN REGISTER'})"
    )

    inc = r["incorporation_date"]
    try:
        inc_note = f"{inc} (IN THE FUTURE)" if date.fromisoformat(inc) > today else inc
    except (TypeError, ValueError):
        inc_note = str(inc)

    return (
        f"{r['entity_id']} | {r['entity_name']} | {r['entity_type']} | {r['jurisdiction']} | "
        f"inc={inc_note} | parent={parent_note} | "
        f"mandate_expiry={mandate} | filing_due={r['annual_filing_due']} "
        f"({r['annual_filing_status']}) | status={r['status']}"
    )


def analyze() -> list[Finding]:
    from datetime import date

    with get_conn() as conn:
        register = conn.execute("SELECT * FROM entities ORDER BY entity_id").fetchall()
        updates = conn.execute("SELECT * FROM board_updates ORDER BY id").fetchall()

    valid_ids = {r["entity_id"] for r in register}
    today = date.fromisoformat(REFERENCE_DATE)
    findings: list[Finding] = []

    # Jurisdiction roster: context for the "implausible jurisdiction" check.
    # The brief says the fund operates in 18 jurisdictions.
    jurisdictions = sorted({r["jurisdiction"] for r in register})
    roster = (f"Jurisdictions appearing in the register: {', '.join(jurisdictions)}. "
              f"The fund operates in 18 jurisdictions — if this list contains more "
              f"than 18 entries, the extras are suspect; flag any that is not a "
              f"real country or not plausible for a sovereign wealth fund.")

    # Pass 1 — per-entity review in batches
    for start in range(0, len(register), ENTITY_BATCH):
        batch = register[start:start + ENTITY_BATCH]
        lines = "\n".join(_annotate(r, valid_ids, today) for r in batch)
        prompt = f"{roster}\n\nENTITIES TO REVIEW ({len(batch)}):\n{lines}"
        result = parse_structured(PER_ENTITY_SYSTEM, prompt, AnalysisResult, max_tokens=4000)
        findings += _to_findings(result, valid_ids, "analysis")

    # Pass 2 — cross-entity structure (compact projection of the full register)
    compact = "\n".join(
        f"{r['entity_id']} | {r['entity_name']} | {r['jurisdiction']} | "
        f"parent={r['parent_entity_id']} | status={r['status']} | board=[{r['board_members']}]"
        for r in register
    )
    result = parse_structured(CROSS_ENTITY_SYSTEM,
                              f"FULL REGISTER ({len(register)} entities):\n{compact}",
                              AnalysisResult, max_tokens=4000)
    findings += _to_findings(result, valid_ids, "analysis")

    # Pass 3 — notifications hygiene
    update_lines = "\n".join(
        f"[{u['id']}] {u['date_raw']} | {u['entity_name_raw']} | {u['change_type']} | "
        f"{u['details']} | via {u['source']}"
        for u in updates
    )
    names = "\n".join(f"{r['entity_id']} {r['entity_name']} ({r['status']})" for r in register)
    result = parse_structured(NOTIFICATIONS_SYSTEM,
                              f"REGISTER ENTITIES:\n{names}\n\nNOTIFICATIONS:\n{update_lines}",
                              AnalysisResult, max_tokens=3000)
    findings += _to_findings(result, valid_ids, "analysis")

    return findings
