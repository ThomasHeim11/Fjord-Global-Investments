"""Local embeddings via sentence-transformers.

Chosen over an embeddings API on purpose: zero per-token cost, no network
dependency during the demo, and at this corpus size quality differences are
negligible. Swapping to a hosted model is a one-function change.
"""
import numpy as np

_model = None


def _get_model():
    """Lazily load and cache the SentenceTransformer, so import stays cheap."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        from ..config import EMBEDDING_MODEL
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed(texts: list[str]) -> np.ndarray:
    """L2-normalized float32 embeddings, so inner product == cosine similarity."""
    vecs = _get_model().encode(texts, normalize_embeddings=True)
    return np.asarray(vecs, dtype=np.float32)
