"""FGI Subsidiary Management API.

  POST /api/digest            run the digest pipeline (rules + LLM)
  GET  /api/digest            latest digest run with findings
  GET  /api/entities          register with filters (jurisdiction, status, q, ...)
  GET  /api/entities/{id}     entity detail: register row, updates, findings, children
  GET  /api/search            hybrid retrieval over letters + updates
  GET  /api/meta              jurisdictions/statuses for filter dropdowns

Run:  uvicorn app.main:app --reload --port 8000
"""
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .analysis.digest import run_digest
from .db import get_conn, init_db
from .ingest import run_ingest


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM entities").fetchone()["n"]
    if count == 0:  # first run: build everything from /data
        run_ingest()
    yield


app = FastAPI(title="FGI Subsidiary Management", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Digest -----------------------------------------------------------------

@app.post("/api/digest")
def trigger_digest(fresh: bool = False) -> dict:
    """Run the review. fresh=true forces real LLM calls (ignores the cache) so
    the pipeline can be demonstrated working live; it leaves the existing cached
    responses untouched, so a normal run still reproduces instantly afterwards."""
    from .llm.client import LLMNotConfigured, LLMQuotaExhausted, set_bypass_cache
    set_bypass_cache(fresh)
    try:
        return run_digest()
    except LLMNotConfigured as exc:
        raise HTTPException(503, str(exc))
    except LLMQuotaExhausted as exc:
        raise HTTPException(429, str(exc))
    except Exception as exc:  # surface cleanly (with CORS) instead of a bare 500
        raise HTTPException(502, f"Review failed: {str(exc)[:200]}")
    finally:
        set_bypass_cache(False)


@app.delete("/api/digest")
def clear_digest() -> dict:
    """Reset the displayed review. The LLM cache is kept on purpose, so the
    next run reproduces instantly and for free instead of re-spending the
    (limited) free-tier token budget."""
    with get_conn() as conn:
        conn.execute("DELETE FROM findings")
        conn.execute("DELETE FROM digest_runs")
    return {"cleared": True}


@app.get("/api/digest")
def get_digest() -> dict:
    with get_conn() as conn:
        run = conn.execute(
            "SELECT * FROM digest_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not run:
            return {"run": None, "findings": []}
        findings = [
            {**dict(r), "evidence": json.loads(r["evidence_json"] or "{}")}
            for r in conn.execute(
                "SELECT * FROM findings WHERE run_id = ? ORDER BY id", (run["id"],)
            )
        ]
    for f in findings:
        f.pop("evidence_json", None)
    return {
        "run": {**dict(run), "stats": json.loads(run["stats_json"] or "{}")},
        "findings": findings,
    }


# --- Register ---------------------------------------------------------------

@app.get("/api/entities")
def list_entities(
    jurisdiction: str | None = None,
    status: str | None = None,
    asset_class: str | None = None,
    filing_status: str | None = None,
    q: str | None = Query(None, description="substring match on name/id"),
) -> list[dict]:
    sql = "SELECT * FROM entities WHERE 1=1"
    params: list = []
    for col, val in [("jurisdiction", jurisdiction), ("status", status),
                     ("asset_class", asset_class), ("annual_filing_status", filing_status)]:
        if val:
            sql += f" AND {col} = ?"
            params.append(val)
    if q:
        sql += " AND (entity_name LIKE ? OR entity_id LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY entity_id"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params)]


@app.get("/api/entities/{entity_id}")
def entity_detail(entity_id: str) -> dict:
    with get_conn() as conn:
        entity = conn.execute(
            "SELECT * FROM entities WHERE entity_id = ?", (entity_id,)
        ).fetchone()
        if not entity:
            raise HTTPException(404, f"Unknown entity {entity_id}")
        updates = [dict(r) for r in conn.execute(
            "SELECT * FROM board_updates WHERE resolved_entity_id = ? ORDER BY date_iso",
            (entity_id,),
        )]
        findings = [
            {**dict(r), "evidence": json.loads(r["evidence_json"] or "{}")}
            for r in conn.execute(
                """SELECT * FROM findings WHERE entity_id = ?
                   AND run_id = (SELECT MAX(id) FROM digest_runs) ORDER BY id""",
                (entity_id,),
            )
        ]
        children = [dict(r) for r in conn.execute(
            "SELECT entity_id, entity_name, jurisdiction, status FROM entities "
            "WHERE parent_entity_id = ? ORDER BY entity_id",
            (entity_id,),
        )]
    for f in findings:
        f.pop("evidence_json", None)
    return {"entity": dict(entity), "updates": updates,
            "findings": findings, "children": children}


# --- Chat -------------------------------------------------------------------

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    from .llm.chat import ask
    from .llm.client import LLMNotConfigured, LLMQuotaExhausted
    try:
        return ask(req.question, req.history)
    except LLMNotConfigured as exc:
        raise HTTPException(503, str(exc))
    except LLMQuotaExhausted:
        raise HTTPException(429,
            "The AI service has hit its free-tier limit for now. Please try "
            "again in a few minutes — the browsing and review pages still work.")
    except Exception as exc:
        raise HTTPException(502, f"Chat failed: {str(exc)[:200]}")


# --- Search -----------------------------------------------------------------

@app.get("/api/search")
def search(q: str, k: int = 8, mode: str = "hybrid") -> list[dict]:
    from .rag.retriever import search as rag_search
    return [vars(r) for r in rag_search(q, k=k, mode=mode)]


# --- Meta -------------------------------------------------------------------

@app.get("/api/meta")
def meta() -> dict:
    with get_conn() as conn:
        return {
            "jurisdictions": [r[0] for r in conn.execute(
                "SELECT DISTINCT jurisdiction FROM entities ORDER BY 1")],
            "statuses": [r[0] for r in conn.execute(
                "SELECT DISTINCT status FROM entities ORDER BY 1")],
            "asset_classes": [r[0] for r in conn.execute(
                "SELECT DISTINCT asset_class FROM entities ORDER BY 1")],
            "filing_statuses": [r[0] for r in conn.execute(
                "SELECT DISTINCT annual_filing_status FROM entities ORDER BY 1")],
        }
