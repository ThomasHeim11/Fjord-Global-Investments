"""FAISS vector index over chunks, persisted next to the SQLite database.

IndexIDMap keeps FAISS ids aligned with chunks.id in SQLite, so a search
result maps straight back to its text and citation metadata.
"""
import faiss
import numpy as np

from ..config import EMBEDDING_DIM, FAISS_INDEX_PATH
from .embeddings import embed


def build(chunk_ids: list[int], texts: list[str]) -> None:
    index = faiss.IndexIDMap(faiss.IndexFlatIP(EMBEDDING_DIM))
    if texts:
        vecs = embed(texts)
        index.add_with_ids(vecs, np.asarray(chunk_ids, dtype=np.int64))
    faiss.write_index(index, str(FAISS_INDEX_PATH))


def search(query: str, k: int = 10) -> list[tuple[int, float]]:
    """Return [(chunk_id, cosine_similarity)] best-first."""
    index = faiss.read_index(str(FAISS_INDEX_PATH))
    if index.ntotal == 0:
        return []
    scores, ids = index.search(embed([query]), min(k, index.ntotal))
    return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i != -1]
