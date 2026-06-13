"""Build the chunk table and both search indexes (BM25 + FAISS) from
ingested documents and board updates.

Letters are chunked; each board update becomes one small chunk (they're a few
sentences each). The register is deliberately NOT indexed here — structured
facts are answered with SQL, not similarity search.
"""
from ..db import get_conn
from . import vector_store
from .chunking import chunk_text


def build_indexes() -> int:
    """Rebuild the chunks table and both search indexes from scratch.

    Chunks letters, turns each board update into one chunk, syncs the FTS5
    (BM25) index, and rebuilds the FAISS vector index. Returns the chunk count.
    """
    with get_conn() as conn:
        conn.execute("DELETE FROM chunks")
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('delete-all')")

        # Letters → paragraph chunks
        for doc in conn.execute("SELECT id, filename, full_text FROM documents"):
            for i, text in enumerate(chunk_text(doc["full_text"])):
                conn.execute(
                    """INSERT INTO chunks (document_id, source_type, source_ref, chunk_index, text)
                       VALUES (?, 'letter', ?, ?, ?)""",
                    (doc["id"], doc["filename"], i, text),
                )

        # Board updates → one chunk each, prefixed with metadata so both
        # keyword and semantic search can land on them
        for u in conn.execute(
            "SELECT id, date_raw, entity_name_raw, change_type, details, source FROM board_updates"
        ):
            text = (
                f"Board update ({u['change_type']}) for {u['entity_name_raw']} "
                f"dated {u['date_raw']}, reported via {u['source']}: {u['details']}"
            )
            conn.execute(
                """INSERT INTO chunks (source_type, source_ref, chunk_index, text)
                   VALUES ('board_update', ?, 0, ?)""",
                (str(u["id"]), text),
            )

        # Sync FTS5 (BM25) index with the chunks table
        conn.execute(
            "INSERT INTO chunks_fts(rowid, text) SELECT id, text FROM chunks"
        )

        rows = conn.execute("SELECT id, text FROM chunks ORDER BY id").fetchall()

    vector_store.build([r["id"] for r in rows], [r["text"] for r in rows])
    return len(rows)
