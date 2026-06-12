"""HTTP surface tests via FastAPI's TestClient.

The DB is a throwaway file seeded with two entities, so the startup lifespan
sees a non-empty register and skips ingestion (no model load, no /data needed).
The chat and digest endpoints stub the LLM call.
"""
import pytest
from fastapi.testclient import TestClient

from conftest import insert_entity

from app import db as db_module
from app.db import get_conn, init_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    dbfile = tmp_path / "api.db"
    monkeypatch.setattr(db_module, "DB_PATH", dbfile)
    init_db()
    with get_conn() as conn:
        insert_entity(conn, "FGI-001", jurisdiction="Norway", status="Active")
        insert_entity(conn, "FGI-002", jurisdiction="Spain", status="Dormant",
                      parent_entity_id="FGI-001")
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_meta_lists_distinct_values(client):
    body = client.get("/api/meta").json()
    assert "Norway" in body["jurisdictions"]
    assert "Spain" in body["jurisdictions"]


def test_list_entities_and_filter(client):
    assert len(client.get("/api/entities").json()) == 2
    spain = client.get("/api/entities?jurisdiction=Spain").json()
    assert [e["entity_id"] for e in spain] == ["FGI-002"]


def test_entity_search_substring(client):
    hits = client.get("/api/entities?q=FGI-001").json()
    assert [e["entity_id"] for e in hits] == ["FGI-001"]


def test_entity_detail_includes_children(client):
    body = client.get("/api/entities/FGI-001").json()
    assert body["entity"]["entity_id"] == "FGI-001"
    assert [c["entity_id"] for c in body["children"]] == ["FGI-002"]


def test_entity_detail_404(client):
    assert client.get("/api/entities/NOPE").status_code == 404


def test_digest_empty_state(client):
    body = client.get("/api/digest").json()
    assert body == {"run": None, "findings": []}


def test_chat_persists_conversation(client, monkeypatch):
    from app.llm import chat as chat_module

    def fake_ask(question, history):
        return {"answer": f"echo: {question}", "sources": [], "retrieved": []}

    monkeypatch.setattr(chat_module, "ask", fake_ask)

    res = client.post("/api/chat", json={"question": "Which entities are dormant?"})
    assert res.status_code == 200
    cid = res.json()["conversation_id"]
    assert res.json()["answer"].startswith("echo:")

    # it was persisted and is listable
    chats = client.get("/api/chats").json()
    assert [c["id"] for c in chats] == [cid]

    conv = client.get(f"/api/chats/{cid}").json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant"]

    # follow-up reuses the same conversation
    res2 = client.post("/api/chat", json={"question": "and active?", "conversation_id": cid})
    assert res2.json()["conversation_id"] == cid
    conv2 = client.get(f"/api/chats/{cid}").json()
    assert len(conv2["messages"]) == 4

    # delete
    assert client.delete(f"/api/chats/{cid}").status_code == 200
    assert client.get("/api/chats").json() == []


def test_chat_failure_does_not_persist(client, monkeypatch):
    from app.llm import chat as chat_module

    def boom(question, history):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(chat_module, "ask", boom)
    res = client.post("/api/chat", json={"question": "anything"})
    assert res.status_code == 502
    # nothing should have been saved on failure
    assert client.get("/api/chats").json() == []


def test_get_missing_conversation_404(client):
    assert client.get("/api/chats/nope").status_code == 404


def test_letter_pdf_served_inline(client):
    # the real agent letters ship in data/letters/
    res = client.get("/api/letters/luxembourg_mandate_warning.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    # 'inline' so the browser opens it in its viewer rather than downloading
    assert "inline" in res.headers.get("content-disposition", "")


def test_letter_pdf_missing_is_404(client):
    assert client.get("/api/letters/does_not_exist.pdf").status_code == 404


def test_letter_pdf_rejects_path_traversal(client):
    assert client.get("/api/letters/secret..pdf").status_code == 400


def test_digest_endpoint_returns_run(client, monkeypatch):
    import app.main as main_module

    monkeypatch.setattr(main_module, "run_digest",
                        lambda fresh=False: {"run_id": 1, "status": "completed",
                                             "summary": "ok", "stats": {"total": 0}})
    res = client.post("/api/digest")
    assert res.status_code == 200
    assert res.json()["status"] == "completed"
