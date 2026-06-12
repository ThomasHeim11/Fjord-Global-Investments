"""'Ask the portfolio' — natural-language Q&A over the register and documents.

Context assembly per question:
  - the structured register (compact, from SQL — facts come from the database)
  - hybrid retrieval (BM25 + vectors) over letters and notifications — this is
    where the RAG pipeline pays off, and what scales when 3 letters become 3,000
  - the latest digest findings, so answers can reference prior analysis

The answer cites its sources so a lawyer can verify every claim.
"""
from typing import Literal

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
- Ground every claim in the context; never invent entities, dates, values or
  legal suffixes that the context does not contain.
- Answer EXACTLY the question asked. If it asks which entities meet a
  criterion, include ONLY those that meet it — never pad the answer with
  entities that merely match the location, type or topic. An entity whose
  records are in order does not belong in an answer about problems.
- "Compliance issues" / "problems" span ALL risk types in the context, not
  just filings: overdue or unknown-status filings, EXPIRED or soon-expiring
  board mandates, status contradictions, and open items reported in agent
  letters (check the retrieved excerpts — a letter can reveal issues the
  register doesn't show). A 'Pending' filing with a future due date is
  normal, not an issue.
- For each entity you include, say in a few words WHY it qualifies
  (e.g. "FGI-079: annual filing overdue since 2026-03").
- Never list the same entity twice, and never mention entities that have
  nothing wrong ("no issues found" entries do not belong in the answer).
- Trust the date annotations in the register context (EXPIRED / expiring in
  n days) — never judge dates yourself. A date with no annotation is healthy
  and is NOT an issue.
- An entity named in a letter or notification but absent from the register
  still belongs in the answer when it meets the question's criterion — say
  it is not in the register.
- Format the answer with one entity per line, separated by newline characters:
  "Name (ID): the issue in a few words."
- If the context doesn't contain the answer, say so plainly.
- When sources disagree (e.g. a letter vs the register), present both sides.
- Be concise and concrete: name entity IDs, dates and jurisdictions.
- List the sources you actually used. Cite findings by the entity or issue
  they concern (e.g. "mandate expired: FGI-067"), letters by filename,
  register sources by entity IDs. Never cite internal numbers."""


class Source(BaseModel):
    kind: Literal["register", "letter", "board_update", "finding"]
    ref: str       # register: entity IDs; letter: filename; board_update:
                   # entity name; finding: the entity/issue it concerns
    detail: str    # one line: what this source contributed


class ChatAnswer(BaseModel):
    answer: str
    sources: list[Source]


def _register_context() -> str:
    """Register lines with date arithmetic precomputed (same approach as the
    review pipeline) so the model never judges 'soon'/'expired' itself."""
    from datetime import date

    today = date.fromisoformat(REFERENCE_DATE)

    def _annotate(d: str | None) -> str:
        # Annotate only when the date signals an issue — a label on healthy
        # dates ("not soon") just tempts the model to narrate clean entities.
        try:
            days = (date.fromisoformat(d) - today).days
        except (TypeError, ValueError):
            return str(d)
        if days < 0:
            return f"{d} (EXPIRED {-days} days ago)"
        if days <= 60:
            return f"{d} (expiring in {days} days)"
        return str(d)

    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM entities ORDER BY entity_id").fetchall()
    return "\n".join(
        f"{r['entity_id']} | {r['entity_name']} | {r['jurisdiction']} | "
        f"status={r['status']} | mandate={_annotate(r['board_mandate_expiry'])} | "
        f"filing={r['annual_filing_due']} ({r['annual_filing_status']}) | "
        f"parent={r['parent_entity_id']} | {r['asset_class']}"
        for r in rows
    )


def _findings_context() -> str:
    # Compact on purpose: titles only, no recommendations — keeps the chat
    # request small enough to fit every fallback model's per-minute budget.
    # No internal row ids: findings are identified by entity + title so the
    # model cites them in human terms.
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT severity, category, entity_id, title
               FROM findings WHERE run_id = (SELECT MAX(id) FROM digest_runs)
               ORDER BY id"""
        ).fetchall()
    if not rows:
        return "(no review has been run yet)"
    return "\n".join(
        f"- {r['severity']}/{r['category']} | {r['entity_id'] or '-'} | {r['title']}"
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
    # max_tokens kept modest: answers are short, and the request size
    # (input + max_tokens) must fit the smaller models' per-minute budgets.
    result: ChatAnswer = parse_structured(SYSTEM, prompt, ChatAnswer, max_tokens=1200,
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
