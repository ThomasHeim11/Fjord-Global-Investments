"""BM25 keyword search over FTS5, including hostile / empty queries."""
import pytest

from app.db import get_conn
from app.rag import keyword


@pytest.fixture
def chunks(db):
    """Seed a few chunks and their FTS index."""
    rows = [
        (1, "FGI Treasury & Financing S.à r.l. board mandate expiring soon"),
        (2, "FGI Singapore Solar III compliance items outstanding"),
        (3, "Amsterdam office overdue annual filing penalty"),
    ]
    with get_conn() as conn:
        for cid, text in rows:
            conn.execute("INSERT INTO chunks (id, source_type, source_ref, chunk_index, text) "
                         "VALUES (?, 'letter', 'x.pdf', 0, ?)", (cid, text))
            conn.execute("INSERT INTO chunks_fts (rowid, text) VALUES (?, ?)", (cid, text))
    return rows


def test_fts_query_quotes_tokens_and_ors_them():
    assert keyword._fts_query("expiring mandate") == '"expiring" OR "mandate"'


def test_finds_matching_chunk(chunks):
    hits = keyword.search("compliance")
    assert hits and hits[0][0] == 2


def test_scores_are_positive_best_first(chunks):
    hits = keyword.search("filing penalty")
    assert hits
    scores = [s for _, s in hits]
    assert scores == sorted(scores, reverse=True)


def test_reserved_fts_words_do_not_break_query(chunks):
    # "OR" / "AND" / "NEAR" are FTS5 operators; quoting must neutralise them
    hits = keyword.search("AND OR NEAR compliance")
    assert any(cid == 2 for cid, _ in hits)


def test_empty_or_punctuation_only_query_is_safe(chunks):
    # no word tokens -> must not raise an FTS5 syntax error
    assert keyword.search("") == []
    assert keyword.search("!!! ??? ...") == []
