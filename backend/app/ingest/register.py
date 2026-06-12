"""Ingest subsidiaries.csv into the entities table.

The register is structured data: it lives in SQL, not in the vector store.
Values are stored as-is (including blanks and inconsistencies); data-quality
problems are flagged later by the LLM analysis, not silently fixed at ingest
time.
"""
import csv

from ..config import SUBSIDIARIES_CSV
from ..db import get_conn

COLUMNS = [
    "entity_id", "entity_name", "entity_type", "jurisdiction",
    "incorporation_date", "parent_entity_id", "ownership_pct",
    "registered_address", "board_members", "board_mandate_expiry",
    "annual_filing_due", "annual_filing_status", "registered_agent",
    "status", "asset_class", "asset_description",
]


def _to_float(value) -> float | None:
    """Parse ownership_pct without trusting it. A malformed value (blank, or a
    stray non-numeric string in messy data) becomes NULL rather than crashing
    the whole ingest."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ingest() -> int:
    with open(SUBSIDIARIES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with get_conn() as conn:
        conn.execute("DELETE FROM entities")
        for r in rows:
            conn.execute(
                f"INSERT INTO entities ({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})",
                [_to_float(r.get("ownership_pct")) if c == "ownership_pct" else (r.get(c) or None)
                 for c in COLUMNS],
            )
    return len(rows)
