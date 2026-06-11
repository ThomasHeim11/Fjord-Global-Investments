"""'Ask the portfolio' — natural-language Q&A over the register and documents.

Context assembly per question:
  - the structured register (compact, from SQL — facts come from the database)
  - hybrid retrieval (BM25 + vectors) over letters and notifications — this is
    where the RAG pipeline pays off, and what scales when 3 letters become 3,000
  - the latest digest findings, so answers can reference prior analysis

The answer cites its sources so a lawyer can verify every claim.
"""
from pydantic import BaseModel

from ..config import REFERENCE_DATE
from ..db import get_conn
from ..rag.retriever import search
from .client import parse_structured

SYSTEM = f"""You are the assistant for Fjord Global Investments' Subsidiary & Corporate
Management team. Answer questions about the fund's ~100 subsidiaries using ONLY
the provided context: the subsidiary register, retrieved document excerpts
(agent letters, board-change notifications), and the latest digest findings.
Today's date is {REFERENCE_DATE}.

Rules:
- Ground every claim in the context; never invent entities, dates or values.
- If the context doesn't contain the answer, say so plainly.
- When sources disagree (e.g. a letter vs the register), present both sides.
- Be concise and concrete: name entity IDs, dates and jurisdictions.
- List the sources you actually used."""


class Source(BaseModel):
    kind: str      # 'register' | 'letter' | 'board_update' | 'finding'
    ref: str       # entity_id, filename, or update/finding id
    detail: str    # one line: what this source contributed


class ChatAnswer(BaseModel):
    answer: str
    sources: list[Source]


def _register_context() -> str:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM entities ORDER BY entity_id").fetchall()
    return "\n".join(
        f"{r['entity_id']} | {r['entity_name']} | {r['jurisdiction']} | "
        f"status={r['status']} | mandate={r['board_mandate_expiry']} | "
        f"filing={r['annual_filing_due']} ({r['annual_filing_status']}) | "
        f"parent={r['parent_entity_id']} | {r['asset_class']}"
        for r in rows
    )


def _findings_context() -> str:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, severity, category, entity_id, title, recommendation
               FROM findings WHERE run_id = (SELECT MAX(id) FROM digest_runs)
               ORDER BY id"""
        ).fetchall()
    if not rows:
        return "(no digest has been run yet)"
    return "\n".join(
        f"[finding {r['id']}] {r['severity']}/{r['category']} | {r['entity_id'] or '-'} | "
        f"{r['title']}" + (f" | action: {r['recommendation']}" if r["recommendation"] else "")
        for r in rows
    )


def ask(question: str, history: list[dict] | None = None) -> dict:
    retrieved = search(question, k=8)
    chunks_text = "\n\n".join(
        f"[{c.source_type}:{c.source_ref}] {c.text}" for c in retrieved
    ) or "(nothing retrieved)"

    history_text = "\n".join(
        f"{m.get('role', 'user')}: {m.get('content', '')}" for m in (history or [])[-6:]
    )

    # Lead AND close with the question so smaller models don't lose it behind
    # the context block.
    convo = f"CONVERSATION SO FAR:\n{history_text}\n\n" if history_text else ""
    prompt = f"""QUESTION TO ANSWER: {question}

Answer the question above using only the context below. Cite the sources you used.

=== SUBSIDIARY REGISTER ===
{_register_context()}

=== RETRIEVED DOCUMENT EXCERPTS (hybrid BM25 + vector search) ===
{chunks_text}

=== LATEST DIGEST FINDINGS ===
{_findings_context()}

{convo}Now answer this question, grounded in the context above: {question}"""

    # No local fallback for chat — a small local model gives poor free-form
    # answers; better to return a clear "try again" than a garbage reply.
    result: ChatAnswer = parse_structured(SYSTEM, prompt, ChatAnswer, max_tokens=2500,
                                          allow_local_fallback=False)
    return {
        "answer": result.answer,
        "sources": [s.model_dump() for s in result.sources],
        "retrieved": [
            {"source_type": c.source_type, "source_ref": c.source_ref,
             "matched_by": c.matched_by}
            for c in retrieved
        ],
    }
