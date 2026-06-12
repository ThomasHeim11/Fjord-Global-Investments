"""Shared test fixtures.

Every DB-touching test runs against a throwaway SQLite file: we monkeypatch
``app.db.DB_PATH`` (which ``get_conn`` reads at call time) so nothing touches
the real ``storage/fgi.db``. No LLM or network is ever hit — the few endpoint
tests stub the model call.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

# Make `import app...` work when pytest is run from the backend directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db as db_module  # noqa: E402
from app.db import get_conn, init_db  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A fresh, schema-initialised SQLite database for one test."""
    dbfile = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", dbfile)
    init_db()
    return dbfile


def insert_entity(conn: sqlite3.Connection, entity_id: str, **overrides) -> None:
    """Insert a register row with sensible defaults, overridable per field."""
    row = {
        "entity_id": entity_id,
        "entity_name": f"FGI {entity_id} Ltd",
        "entity_type": "Ltd",
        "jurisdiction": "Norway",
        "incorporation_date": "2015-01-01",
        "parent_entity_id": None,
        "ownership_pct": 100.0,
        "registered_address": "Oslo",
        "board_members": "A. Person, B. Person",
        "board_mandate_expiry": "2030-01-01",
        "annual_filing_due": "2027-01-01",
        "annual_filing_status": "Filed",
        "registered_agent": "Agent AS",
        "status": "Active",
        "asset_class": "Holding",
        "asset_description": "desc",
    }
    row.update(overrides)
    cols = ", ".join(row)
    conn.execute(
        f"INSERT INTO entities ({cols}) VALUES ({', '.join('?' * len(row))})",
        list(row.values()),
    )
