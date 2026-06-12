"""Reciprocal Rank Fusion — the core of hybrid retrieval."""
from app.rag.retriever import RRF_K, _rrf


def test_single_ranking_orders_by_position():
    fused = _rrf({"bm25": [10, 20, 30]})
    # earlier rank -> higher score
    assert fused[10][0] > fused[20][0] > fused[30][0]
    assert fused[10][1] == ["bm25"]


def test_score_matches_formula():
    fused = _rrf({"bm25": [42]})
    assert fused[42][0] == 1.0 / (RRF_K + 0 + 1)


def test_chunk_in_both_rankings_sums_and_records_both_sources():
    fused = _rrf({"bm25": [7, 8], "vector": [8, 7]})
    # 8 is rank1 in bm25 and rank0 in vector; 7 is rank0 in bm25, rank1 in vector
    assert set(fused[7][1]) == {"bm25", "vector"}
    assert set(fused[8][1]) == {"bm25", "vector"}
    # both appear in both lists, so their fused scores are equal
    assert fused[7][0] == fused[8][0]


def test_agreement_beats_single_list_hit():
    fused = _rrf({"bm25": [1, 2], "vector": [2, 99]})
    # 2 is found by both; 1 only by bm25. 2 should win.
    assert fused[2][0] > fused[1][0]


def test_empty_rankings_produce_empty_fusion():
    assert _rrf({}) == {}
    assert _rrf({"bm25": []}) == {}
