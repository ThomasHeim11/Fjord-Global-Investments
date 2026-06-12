"""PortfolioGPT conversation persistence.

Chat history lives in SQLite alongside the rest of the application state, so
conversations survive a reload and the server stays the single source of truth.
There are no user accounts yet, so history is global; the schema is ready to
gain a user_id column the day authentication is added.
"""
import json
import uuid

from .db import get_conn


def _title_from(question: str) -> str:
    t = " ".join(question.split())
    return f"{t[:56]}…" if len(t) > 56 else t


def list_conversations() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_conversations "
            "ORDER BY updated_at DESC, created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_messages(conversation_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content, sources_json FROM chat_messages "
            "WHERE conversation_id = ? ORDER BY id",
            (conversation_id,),
        ).fetchall()
    out: list[dict] = []
    for r in rows:
        msg: dict = {"role": r["role"], "content": r["content"]}
        if r["sources_json"]:
            msg["sources"] = json.loads(r["sources_json"])
        out.append(msg)
    return out


def get_conversation(conversation_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
    if not row:
        return None
    return {**dict(row), "messages": get_messages(conversation_id)}


def _exists(conversation_id: str) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM chat_conversations WHERE id = ?", (conversation_id,)
        ).fetchone() is not None


def ensure_conversation(conversation_id: str | None, first_question: str) -> str:
    """Return an existing conversation id, or create a new one titled by the
    first question. IDs are server-generated."""
    if conversation_id and _exists(conversation_id):
        return conversation_id
    cid = uuid.uuid4().hex
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_conversations (id, title) VALUES (?, ?)",
            (cid, _title_from(first_question)),
        )
    return cid


def add_message(conversation_id: str, role: str, content: str,
                sources: list | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (conversation_id, role, content, sources_json) "
            "VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, json.dumps(sources) if sources else None),
        )
        conn.execute(
            "UPDATE chat_conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )


def delete_conversation(conversation_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM chat_conversations WHERE id = ?", (conversation_id,))
