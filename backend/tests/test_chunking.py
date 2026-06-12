"""Paragraph-aware chunking for retrieval."""
from app.rag.chunking import MAX_CHARS, chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("Hello world.") == ["Hello world."]


def test_empty_text_yields_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n   ") == []


def test_paragraphs_split_on_blank_lines():
    text = "Para one.\n\nPara two.\n\nPara three."
    chunks = chunk_text(text)
    assert all("Para" in c for c in chunks)
    assert "Para one." in chunks[0]


def test_long_text_is_split_with_overlap():
    para = "word " * 100  # ~500 chars
    text = "\n\n".join([para.strip()] * 5)  # ~2500 chars, exceeds MAX_CHARS
    chunks = chunk_text(text)
    assert len(chunks) > 1
    # one-paragraph overlap: the last paragraph of a chunk reappears next
    assert chunks[0].split("\n\n")[-1] == chunks[1].split("\n\n")[0]


def test_no_blank_lines_falls_back_to_line_groups():
    text = "\n".join(f"line {i}" for i in range(20))
    chunks = chunk_text(text)
    assert chunks  # did not return empty
    assert "line 0" in chunks[0]


def test_chunks_respect_max_chars_budget_roughly():
    para = "x" * 400
    text = "\n\n".join([para] * 10)
    for c in chunk_text(text):
        # each chunk is a small number of paragraphs, never the whole document
        assert len(c) <= MAX_CHARS + 400 + len("\n\n")
