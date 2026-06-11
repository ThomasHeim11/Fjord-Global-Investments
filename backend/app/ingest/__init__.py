"""Ingestion pipeline: source files in /data → SQLite + search indexes.

Idempotent — safe to re-run; tables are cleared and rebuilt each time so the
database always reflects the source data exactly.
"""
from .. import db
from . import letters, register, updates
from ..rag import indexer


def run_ingest() -> dict:
    db.init_db()
    stats = {}
    stats["entities"] = register.ingest()
    stats["board_updates"] = updates.ingest()
    stats["letters"] = letters.ingest()
    stats["chunks_indexed"] = indexer.build_indexes()
    return stats
