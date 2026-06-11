"""Ingest board_updates.json.

Raw values are preserved; dates are additionally normalized to ISO where
parseable. Entity names are NOT matched against the register here — fuzzy
resolution is an LLM job (phase 2) and its result lands in resolved_entity_id.
"""
import json

from ..config import BOARD_UPDATES_JSON
from ..db import get_conn
from ..utils.dates import to_iso


def ingest() -> int:
    with open(BOARD_UPDATES_JSON, encoding="utf-8") as f:
        items = json.load(f)

    with get_conn() as conn:
        conn.execute("DELETE FROM board_updates")
        for u in items:
            conn.execute(
                """INSERT INTO board_updates
                   (date_raw, date_iso, entity_name_raw, change_type, details, source)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    u.get("date"),
                    to_iso(u.get("date", "")),
                    u.get("entity_name"),
                    u.get("change_type"),
                    u.get("details"),
                    u.get("source"),
                ),
            )
    return len(items)
