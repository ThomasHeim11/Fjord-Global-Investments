"""Hybrid retrieval: BM25 (FTS5) + dense vectors (FAISS), fused with
Reciprocal Rank Fusion.

Why hybrid: governance text is full of exact tokens (entity names, IDs,
'S.à r.l.', dates) where BM25 wins, while paraphrased questions ('which
entities have compliance problems?') need semantic matching. RRF combines the
two rankings without needing to calibrate their incomparable score scales.
"""
from dataclasses import dataclass

from ..db import get_conn
from . import keyword, vector_store

RRF_K = 60  # standard damping constant from the original RRF paper


@dataclass
class RetrievedChunk:
    chunk_id: int
    text: str
    source_type: str
    source_ref: str
    score: float
    matched_by: list[str]


def _rrf(rankings: dict[str, list[int]]) -> dict[int, tuple[float, list[str]]]:
    fused: dict[int, tuple[float, list[str]]] = {}
    for name, ids in rankings.items():
        for rank, chunk_id in enumerate(ids):
            score, sources = fused.get(chunk_id, (0.0, []))
            fused[chunk_id] = (score + 1.0 / (RRF_K + rank + 1), sources + [name])
    return fused


def search(query: str, k: int = 8, mode: str = "hybrid") -> list[RetrievedChunk]:
    candidates = max(k * 3, 20)
    rankings: dict[str, list[int]] = {}
    if mode in ("hybrid", "bm25"):
        rankings["bm25"] = [cid for cid, _ in keyword.search(query, candidates)]
    if mode in ("hybrid", "vector"):
        rankings["vector"] = [cid for cid, _ in vector_store.search(query, candidates)]

    fused = _rrf(rankings)
    top = sorted(fused.items(), key=lambda kv: kv[1][0], reverse=True)[:k]
    if not top:
        return []

    ids = [cid for cid, _ in top]
    with get_conn() as conn:
        rows = {
            r["id"]: r
            for r in conn.execute(
                f"SELECT id, text, source_type, source_ref FROM chunks "
                f"WHERE id IN ({','.join('?' * len(ids))})",
                ids,
            )
        }
    return [
        RetrievedChunk(
            chunk_id=cid,
            text=rows[cid]["text"],
            source_type=rows[cid]["source_type"],
            source_ref=rows[cid]["source_ref"],
            score=score,
            matched_by=sources,
        )
        for cid, (score, sources) in top
        if cid in rows
    ]
