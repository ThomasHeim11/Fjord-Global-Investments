"""LLM entity resolution: match messy board-update names to the register.

To fit free-tier token budgets (and to scale past 100 entities), each messy
name gets a candidate shortlist first (cheap string similarity), and the LLM
only adjudicates among candidates. 'No match' is an explicitly valid answer —
forcing a match is how 'Northwind Capital Partners LLP' ends up attributed to
an FGI entity.
"""
import difflib

from pydantic import BaseModel

from ..db import get_conn
from .client import parse_structured

CANDIDATES_PER_NAME = 8

SYSTEM = """You are a corporate-governance data specialist. You match messy entity names
from notifications against candidate entries from a subsidiary register. Names
may have typos, stray punctuation, missing legal suffixes (Ltd, B.V., Pte.
Ltd., K.K., S.à r.l.) or abbreviated forms. Match only when you are genuinely
confident it is the same legal entity. If no candidate is a plausible match,
return entity_id null — some notifications reference entities that are not in
the register at all, and identifying those is more valuable than forcing a
match."""


class Resolution(BaseModel):
    raw_name: str
    entity_id: str | None      # None = no plausible match in the register
    confidence: float          # 0.0 - 1.0
    note: str                  # short reasoning, e.g. "suffix missing, otherwise exact"


class ResolutionBatch(BaseModel):
    resolutions: list[Resolution]


def _shortlist(raw: str, register: list) -> list:
    """Top candidates by string similarity — recall-oriented, the LLM decides."""
    scored = sorted(
        register,
        key=lambda r: difflib.SequenceMatcher(
            None, raw.lower(), (r["entity_name"] or "").lower()
        ).ratio(),
        reverse=True,
    )
    return scored[:CANDIDATES_PER_NAME]


def resolve_all() -> int:
    with get_conn() as conn:
        register = conn.execute(
            "SELECT entity_id, entity_name, jurisdiction FROM entities ORDER BY entity_id"
        ).fetchall()
        raw_names = [r["entity_name_raw"] for r in conn.execute(
            "SELECT DISTINCT entity_name_raw FROM board_updates"
        )]

    blocks = []
    for raw in raw_names:
        cands = "\n".join(
            f"  {c['entity_id']} | {c['entity_name']} | {c['jurisdiction']}"
            for c in _shortlist(raw, register)
        )
        blocks.append(f"MESSY NAME: {raw}\nCANDIDATES:\n{cands}")

    prompt = ("Resolve each messy name against its candidates "
              "(one resolution per name, same order):\n\n" + "\n\n".join(blocks))

    batch: ResolutionBatch = parse_structured(SYSTEM, prompt, ResolutionBatch,
                                              max_tokens=4000)

    with get_conn() as conn:
        for r in batch.resolutions:
            conn.execute(
                """UPDATE board_updates
                   SET resolved_entity_id = ?, resolution_confidence = ?, resolution_note = ?
                   WHERE entity_name_raw = ?""",
                (r.entity_id, r.confidence, r.note, r.raw_name),
            )
    return len(batch.resolutions)
