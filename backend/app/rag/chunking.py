"""Paragraph-aware chunking.

The corpus is short agent letters today, but the chunker is written for the
real-product case: split on blank lines, pack paragraphs into chunks of up to
MAX_CHARS with one paragraph of overlap so context isn't lost at boundaries.
"""
MAX_CHARS = 1200


def chunk_text(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        # PDFs sometimes extract without blank lines — fall back to line groups
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        paragraphs = ["\n".join(lines[i:i + 6]) for i in range(0, len(lines), 6)]

    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for para in paragraphs:
        if current and size + len(para) > MAX_CHARS:
            chunks.append("\n\n".join(current))
            current = [current[-1]]  # one-paragraph overlap
            size = len(current[0])
        current.append(para)
        size += len(para)
    if current:
        chunks.append("\n\n".join(current))
    return chunks
