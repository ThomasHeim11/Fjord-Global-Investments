"""LLM reconciliation: agent letters vs the register.

Decomposed into two focused LLM passes per letter — small, single-purpose
prompts are far more reliable on a small model than one prompt juggling
existence + value-comparison + formatting:

  EXISTENCE pass — given the names a letter mentions and an exact-lookup
    verdict for each, the LLM writes one finding per entity the fund has no
    record of (the headline "agent administering an unknown entity" risk).
  CONFLICT pass — for entities that DO exist, the LLM compares each field the
    letter asserts against the register and reports the differences.

Both are pure LLM; the exact-match cross-check is data preparation (the
structured-data retrieval step), exactly like the date annotations in
analyze.py.
"""
import re
from typing import Literal

from pydantic import BaseModel

from ..analysis.models import Finding
from ..config import GROQ_REASONING_MODEL
from ..db import get_conn
from .client import parse_structured

_SUFFIX = (r"(?:S\.à r\.l\.|B\.V\.|Pte\. Ltd\.|Ltd\.?|ApS|GmbH|K\.K\.|LLC|AB|AS|"
           r"Ltda|S\.L\.|S\.A\.|Pty Ltd|Inc\.|Oy|Corp\.)")
_ROMAN = r"(?:VIII|VII|VI|IX|IV|V|X|III|II|I)"


def _candidate_names(text: str) -> set[str]:
    """Every distinct FGI entity name the letter mentions. Table rows land on
    their own line after PDF extraction; prose mentions are caught by pattern.

    The line and regex passes can produce several spellings of one name (with
    and without the legal suffix, with and without the roman numeral). We keep
    only maximal names — any candidate that is a substring of a longer one is
    dropped — so the same entity isn't sent downstream two or three times.
    """
    raw = set()
    for line in text.splitlines():
        s = line.strip().rstrip(",.;:")
        if s.startswith("FGI ") and len(s) < 70:
            raw.add(s)
    for m in re.finditer(rf"FGI [\w&.\-'À-ü ]{{2,50}}?{_SUFFIX}", text):
        raw.add(m.group(0).strip())
    for m in re.finditer(rf"FGI [A-Za-zÀ-ü ]{{2,40}} {_ROMAN}\b", text):
        raw.add(m.group(0).strip())

    return {
        name for name in raw
        if not any(other != name and name in other for other in raw)
    }


def _classify_names(text: str, register) -> tuple[list[str], dict[str, str]]:
    """Split the names a letter mentions into (absent, {present_name: id})
    by exact lookup. Existence is string matching, not judgment — computed
    here so each LLM pass receives a clean, single-purpose input."""
    by_name = {(r["entity_name"] or "").lower(): r["entity_id"] for r in register}
    absent, present = [], {}
    for cand in sorted(_candidate_names(text)):
        hit = by_name.get(cand.lower())
        if hit:
            present[cand] = hit
        else:
            absent.append(cand)
    return absent, present


# ---- Pass 1: existence -----------------------------------------------------

EXISTENCE_SYSTEM = """You are a corporate-governance analyst. An agent letter names several entities;
an exact lookup has already determined which are absent from the fund's
register. For EACH absent name, write one finding: the agent is administering
(and may be billing for) an entity the fund has no record of — a serious gap.
Mark it 'unknown_entity' (severity critical if the letter shows open
obligations like an unfiled return or outstanding fee, otherwise warning),
UNLESS the name is clearly a typo/variant of a similar register name, in
which case mark it 'conflict' and name the likely match. Write one finding
per absent name — no more, no fewer."""

EXISTENCE_TITLE = ('Titles MUST be specific and plain, e.g. "Unknown entity in '
                   'agent letter: FGI Amsterdam Office II B.V.". Never use the '
                   'em-dash character in titles.')


class ExistenceFinding(BaseModel):
    category: Literal["unknown_entity", "conflict"]
    severity: Literal["critical", "warning"]
    entity_name: str           # the absent name as written in the letter
    title: str
    description: str
    likely_register_match: str | None   # similar register name if it's a variant


class ExistenceResult(BaseModel):
    findings: list[ExistenceFinding]


# ---- Pass 2: value conflicts ----------------------------------------------

CONFLICT_SYSTEM = """You are a corporate-governance analyst comparing what an agent letter asserts
against the fund's register, for entities KNOWN to exist in both. Report one
'conflict' finding per field that DIFFERS — mandate expiry date, board
members, filing due date, filing status, or entity status. Quote both values.
If a field agrees, say nothing about it; if everything agrees, return an empty
list. NEVER emit placeholder findings like 'No conflict found'. Severity
'critical' for mandate/board/status/existence contradictions, 'warning'
otherwise. Titles MUST name the entity and the field that differs, e.g.
"Mandate expiry conflict: FGI Treasury & Financing S.à r.l." — keep the
differing VALUES out of the title (they belong in letter_says/register_says),
never use the em-dash character in titles, and put the register ID only in
the entity_id field, not the title."""


class ConflictFinding(BaseModel):
    severity: Literal["critical", "warning"]
    entity_id: str             # register id (FGI-xxx)
    entity_name: str
    title: str
    description: str
    letter_says: str
    register_says: str


class ConflictResult(BaseModel):
    findings: list[ConflictFinding]


def reconcile_letters() -> list[Finding]:
    """Reconcile every agent letter against the register, running the existence and
    value-conflict passes per letter and returning all resulting findings."""
    with get_conn() as conn:
        letters = conn.execute(
            "SELECT id, filename, title, full_text FROM documents WHERE source_type = 'letter'"
        ).fetchall()
        register = conn.execute(
            """SELECT entity_id, entity_name, jurisdiction, status, board_members,
                      board_mandate_expiry, annual_filing_due, annual_filing_status
               FROM entities ORDER BY entity_id"""
        ).fetchall()

    reg_by_id = {r["entity_id"]: r for r in register}
    findings: list[Finding] = []

    for letter in letters:
        absent, present = _classify_names(letter["full_text"], register)

        # Pass 1 — existence (only the absent names; one focused job)
        if absent:
            prompt = (f"LETTER ({letter['filename']}):\n{letter['full_text']}\n\n"
                      f"NAMES CONFIRMED ABSENT FROM THE REGISTER (write one finding each):\n"
                      + "\n".join(f"- {n}" for n in absent)
                      + f"\n\n{EXISTENCE_TITLE}")
            result: ExistenceResult = parse_structured(
                EXISTENCE_SYSTEM, prompt, ExistenceResult, max_tokens=2500)
            for f in result.findings:
                findings.append(Finding(
                    category=f.category, severity=f.severity,
                    title=f.title, description=f.description,
                    detected_by="llm:reconciliation", entity_id=None,
                    entity_name=f.entity_name,
                    evidence={"letter": letter["filename"],
                              "letter_says": f"names '{f.entity_name}'",
                              "register_says": f"not present"
                              + (f" (similar: {f.likely_register_match})"
                                 if f.likely_register_match else "")},
                ))

        # Pass 2 — value conflicts (only entities that exist; uses the stronger
        # model since field-by-field comparison is the harder reasoning task)
        if present:
            rows = "\n".join(
                f"{eid} | {reg_by_id[eid]['entity_name']} | status={reg_by_id[eid]['status']} | "
                f"board=[{reg_by_id[eid]['board_members']}] | "
                f"mandate_expiry={reg_by_id[eid]['board_mandate_expiry']} | "
                f"filing_due={reg_by_id[eid]['annual_filing_due']} "
                f"({reg_by_id[eid]['annual_filing_status']})"
                for eid in present.values()
            )
            prompt = (f"LETTER ({letter['filename']}):\n{letter['full_text']}\n\n"
                      f"REGISTER ROWS for the entities this letter discusses "
                      f"(compare field by field):\n{rows}")
            cresult: ConflictResult = parse_structured(
                CONFLICT_SYSTEM, prompt, ConflictResult, max_tokens=3000,
                model=GROQ_REASONING_MODEL)
            for f in cresult.findings:
                findings.append(Finding(
                    category="conflict", severity=f.severity,
                    title=f.title, description=f.description,
                    detected_by="llm:reconciliation",
                    entity_id=f.entity_id if f.entity_id in reg_by_id else None,
                    entity_name=f.entity_name,
                    evidence={"letter": letter["filename"],
                              "letter_says": f.letter_says,
                              "register_says": f.register_says},
                ))
    return findings
