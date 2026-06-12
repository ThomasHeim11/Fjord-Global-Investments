"""Letter entity extraction and the exact-lookup present/absent split that
feeds the reconciliation passes."""
from app.llm.reconcile import _candidate_names, _classify_names


def test_extracts_table_row_names():
    text = (
        "Re: Board mandates\n"
        "FGI Treasury & Financing S.à r.l.\n"
        "FGI Aurora Storage Holdings S.à r.l.\n"
    )
    names = _candidate_names(text)
    assert "FGI Treasury & Financing S.à r.l." in names
    assert "FGI Aurora Storage Holdings S.à r.l." in names


def test_substring_variants_collapse_to_maximal_name():
    # both the bare and suffixed form should not both survive
    text = "FGI Amsterdam Office II\nFGI Amsterdam Office II B.V.\n"
    names = _candidate_names(text)
    assert "FGI Amsterdam Office II B.V." in names
    assert "FGI Amsterdam Office II" not in names


def test_non_fgi_lines_ignored():
    text = "Van der Berg Corporate Services B.V.\nDear team,\n"
    assert _candidate_names(text) == set()


def test_classify_splits_present_and_absent():
    register = [
        {"entity_id": "FGI-010", "entity_name": "FGI Treasury & Financing S.à r.l."},
        {"entity_id": "FGI-011", "entity_name": "FGI Europe Holdings B.V."},
    ]
    text = "FGI Treasury & Financing S.à r.l.\nFGI Ghost Entity S.à r.l.\n"
    absent, present = _classify_names(text, register)
    assert present == {"FGI Treasury & Financing S.à r.l.": "FGI-010"}
    assert "FGI Ghost Entity S.à r.l." in absent


def test_classify_is_case_insensitive_on_lookup():
    register = [{"entity_id": "FGI-010", "entity_name": "FGI Europe Holdings B.V."}]
    text = "FGI Europe Holdings B.V.\n"
    absent, present = _classify_names(text, register)
    assert present == {"FGI Europe Holdings B.V.": "FGI-010"}
    assert absent == []
