"""BM25 keyword search via SQLite FTS5.

FTS5's MATCH ranking *is* the BM25 algorithm (the built-in bm25() function),
so this gives us real BM25 scoring with no extra index to maintain — the
keyword index lives in the same database as the data and is rebuilt with it.
"""
import re

from ..db import get_conn

_TOKEN = re.compile(r"[\w\-]+", re.UNICODE)


def _fts_query(query: str) -> str:
    """Quote each token so user input can't break FTS5 MATCH syntax.
    Tokens are OR-ed: governance queries are entity-name heavy, and requiring
    every term would miss documents that mention only the entity."""
    tokens = _TOKEN.findall(query)
    return " OR ".join(f'"{t}"' for t in tokens) if tokens else '""'


def search(query: str, k: int = 10) -> list[tuple[int, float]]:
    """Return [(chunk_id, bm25_score)] best-first. FTS5 rank is negative
    (lower = better); negate it so higher = better, consistent with FAISS."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT rowid, bm25(chunks_fts) AS score
               FROM chunks_fts WHERE chunks_fts MATCH ?
               ORDER BY score LIMIT ?""",
            (_fts_query(query), k),
        ).fetchall()
    return [(row["rowid"], -row["score"]) for row in rows]
