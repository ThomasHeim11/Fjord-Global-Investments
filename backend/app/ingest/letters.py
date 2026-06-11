"""Ingest agent letters (PDF → text → documents table).

Text extraction is local (pypdf) — the LLM is used later for *interpreting*
letters, not for reading them, which keeps ingestion free and offline.
"""
from pypdf import PdfReader

from ..config import LETTERS_DIR
from ..db import get_conn


def extract_text(path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def ingest() -> int:
    pdfs = sorted(LETTERS_DIR.glob("*.pdf"))
    with get_conn() as conn:
        conn.execute("DELETE FROM chunks")  # chunks reference documents
        conn.execute("DELETE FROM documents")
        for pdf in pdfs:
            text = extract_text(pdf)
            title = pdf.stem.replace("_", " ").title()
            conn.execute(
                "INSERT INTO documents (filename, title, source_type, full_text) VALUES (?, ?, 'letter', ?)",
                (pdf.name, title, text),
            )
    return len(pdfs)
