"""Connection lifecycle: get_conn must commit on success, roll back on error,
and always close the handle (sqlite3's own context manager leaks it)."""
import sqlite3

import pytest

from app.db import get_conn


def test_commit_is_visible_to_a_fresh_connection(db):
    with get_conn() as conn:
        conn.execute("INSERT INTO chat_conversations (id, title) VALUES ('x', 't')")
    # a separate connection sees the committed row
    with get_conn() as conn2:
        n = conn2.execute("SELECT COUNT(*) FROM chat_conversations").fetchone()[0]
    assert n == 1


def test_rollback_on_exception(db):
    with pytest.raises(RuntimeError):
        with get_conn() as conn:
            conn.execute("INSERT INTO chat_conversations (id, title) VALUES ('y', 't')")
            raise RuntimeError("boom")
    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM chat_conversations").fetchone()[0]
    assert n == 0


def test_connection_is_closed_after_block(db):
    with get_conn() as conn:
        pass
    # operating on a closed connection raises ProgrammingError
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")
