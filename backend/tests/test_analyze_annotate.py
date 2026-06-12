"""The precomputed date/reference annotations the model reads (so it never
does arithmetic). This is the change that made expiry detection exact."""
from datetime import date

from app.llm.analyze import _annotate

TODAY = date(2026, 6, 11)


def row(**kw):
    base = dict(entity_id="FGI-001", entity_name="FGI Oslo AS", entity_type="AS",
                jurisdiction="Norway", incorporation_date="2015-01-01",
                parent_entity_id=None, board_mandate_expiry="2030-01-01",
                annual_filing_due="2027-01-01", annual_filing_status="Filed",
                status="Active")
    base.update(kw)
    return base


def test_expired_mandate_is_marked_expired():
    out = _annotate(row(board_mandate_expiry="2026-06-03"), {"FGI-001"}, TODAY)
    assert "EXPIRED 8 days ago" in out


def test_future_mandate_shows_days_remaining():
    out = _annotate(row(board_mandate_expiry="2026-06-21"), {"FGI-001"}, TODAY)
    assert "in 10 days" in out


def test_parent_not_in_register_flagged():
    out = _annotate(row(parent_entity_id="FGI-099X"), {"FGI-001"}, TODAY)
    assert "FGI-099X (NOT IN REGISTER)" in out


def test_valid_parent_marked_valid():
    out = _annotate(row(parent_entity_id="FGI-002"), {"FGI-001", "FGI-002"}, TODAY)
    assert "FGI-002 (VALID)" in out


def test_no_parent_is_top_of_structure():
    out = _annotate(row(parent_entity_id=None), {"FGI-001"}, TODAY)
    assert "none (top of structure)" in out


def test_future_incorporation_flagged():
    out = _annotate(row(incorporation_date="2099-01-01"), {"FGI-001"}, TODAY)
    assert "IN THE FUTURE" in out


def test_unparseable_dates_do_not_crash():
    out = _annotate(row(board_mandate_expiry=None, incorporation_date="n/a"),
                    {"FGI-001"}, TODAY)
    assert "FGI-001" in out  # produced a line rather than raising
