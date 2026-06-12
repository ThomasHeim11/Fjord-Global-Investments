"""Date normalisation — the one bit of parsing the whole pipeline trusts."""
from app.utils.dates import to_iso


def test_iso_passthrough():
    assert to_iso("2026-05-31") == "2026-05-31"


def test_us_slash_is_month_first():
    # 05/25/2026 is only valid read month-first; that is the documented choice.
    assert to_iso("05/25/2026") == "2026-05-25"


def test_day_month_year_long_and_short():
    assert to_iso("15 May 2026") == "2026-05-15"
    assert to_iso("15 Jun 2026") == "2026-06-15"


def test_whitespace_is_trimmed():
    assert to_iso("  2026-05-31  ") == "2026-05-31"


def test_unparseable_returns_none():
    assert to_iso("not a date") is None
    assert to_iso("31/31/2026") is None  # impossible month-first


def test_empty_and_none_safe():
    assert to_iso("") is None
    assert to_iso(None) is None


def test_impossible_calendar_date_rejected():
    assert to_iso("2026-02-30") is None


def test_non_string_input_does_not_crash():
    # a date arriving as a number (messy JSON) must not raise
    assert to_iso(20260531) is None
    assert to_iso(0) is None
