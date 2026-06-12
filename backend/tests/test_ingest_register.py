"""Register ingest must survive messy data, not crash on it."""
from app.db import get_conn
from app.ingest import register


def test_to_float_parses_or_nulls():
    assert register._to_float("100.0") == 100.0
    assert register._to_float("100") == 100.0
    assert register._to_float("") is None
    assert register._to_float(None) is None
    assert register._to_float("n/a") is None   # would previously crash ingest


def test_ingest_handles_blank_and_bad_ownership(db, tmp_path, monkeypatch):
    csv_text = (
        "entity_id,entity_name,entity_type,jurisdiction,incorporation_date,"
        "parent_entity_id,ownership_pct,registered_address,board_members,"
        "board_mandate_expiry,annual_filing_due,annual_filing_status,"
        "registered_agent,status,asset_class,asset_description\n"
        "FGI-001,FGI One AS,AS,Norway,2015-01-01,,100.0,Oslo,A,2030-01-01,"
        "2027-01-01,Filed,Agent,Active,Holding,desc\n"
        # messy row: non-numeric ownership, blank name
        "FGI-002,,Ltd,Noveria,2015-01-01,,oops,Nowhere,B,2030-01-01,"
        "2027-01-01,Unknown,Agent,Active,Holding,desc\n"
    )
    csv_file = tmp_path / "subs.csv"
    csv_file.write_text(csv_text, encoding="utf-8")
    monkeypatch.setattr(register, "SUBSIDIARIES_CSV", csv_file)

    n = register.ingest()
    assert n == 2

    with get_conn() as conn:
        rows = {r["entity_id"]: r for r in conn.execute("SELECT * FROM entities")}
    assert rows["FGI-001"]["ownership_pct"] == 100.0
    assert rows["FGI-002"]["ownership_pct"] is None      # bad value -> NULL, no crash
    assert rows["FGI-002"]["entity_name"] is None        # blank -> NULL (a real finding later)
