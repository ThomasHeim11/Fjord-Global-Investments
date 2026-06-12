"""Server-side PortfolioGPT conversation persistence."""
from app import chat_store


def test_new_conversation_created_and_listed(db):
    cid = chat_store.ensure_conversation(None, "What expires soon?")
    assert cid
    convos = chat_store.list_conversations()
    assert len(convos) == 1
    assert convos[0]["id"] == cid
    assert convos[0]["title"] == "What expires soon?"


def test_long_title_is_truncated():
    # pure function, no DB needed
    long_q = "x" * 200
    title = chat_store._title_from(long_q)
    assert title.endswith("…")
    assert len(title) <= 57


def test_messages_round_trip_with_sources(db):
    cid = chat_store.ensure_conversation(None, "q1")
    chat_store.add_message(cid, "user", "hello")
    chat_store.add_message(cid, "assistant", "hi", [{"kind": "register", "ref": "FGI-001", "detail": "x"}])
    msgs = chat_store.get_messages(cid)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert "sources" not in msgs[0]
    assert msgs[1]["sources"][0]["ref"] == "FGI-001"


def test_get_conversation_includes_messages(db):
    cid = chat_store.ensure_conversation(None, "q1")
    chat_store.add_message(cid, "user", "hello")
    conv = chat_store.get_conversation(cid)
    assert conv["id"] == cid
    assert len(conv["messages"]) == 1


def test_get_missing_conversation_returns_none(db):
    assert chat_store.get_conversation("does-not-exist") is None


def test_ensure_with_existing_id_reuses_it(db):
    cid = chat_store.ensure_conversation(None, "q1")
    again = chat_store.ensure_conversation(cid, "q2")
    assert again == cid
    assert len(chat_store.list_conversations()) == 1


def test_delete_removes_conversation_and_messages(db):
    cid = chat_store.ensure_conversation(None, "q1")
    chat_store.add_message(cid, "user", "hello")
    chat_store.delete_conversation(cid)
    assert chat_store.list_conversations() == []
    assert chat_store.get_messages(cid) == []


def test_list_orders_most_recently_updated_first(db):
    from app.db import get_conn

    a = chat_store.ensure_conversation(None, "older")
    b = chat_store.ensure_conversation(None, "newer")
    # set explicit timestamps so the ordering assertion is deterministic
    with get_conn() as conn:
        conn.execute("UPDATE chat_conversations SET updated_at = ? WHERE id = ?", ("2026-01-01 00:00:00", a))
        conn.execute("UPDATE chat_conversations SET updated_at = ? WHERE id = ?", ("2026-06-01 00:00:00", b))
    ids = [c["id"] for c in chat_store.list_conversations()]
    assert ids == [b, a]
