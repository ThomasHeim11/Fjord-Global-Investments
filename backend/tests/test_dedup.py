"""De-duplication: the same issue surfaced by two passes collapses to one,
but genuinely distinct issues survive."""
from app.analysis.digest import _dedup
from app.analysis.models import Finding


def f(**kw) -> Finding:
    base = dict(category="mandate", severity="warning", title="t",
                description="d", detected_by="llm:analysis")
    base.update(kw)
    return Finding(**base)


def test_same_entity_and_category_dedups_by_id():
    out = _dedup([
        f(entity_id="FGI-001", title="mandate expired"),
        f(entity_id="FGI-001", title="mandate expired (again)"),
    ])
    assert len(out) == 1


def test_same_entity_different_category_both_kept():
    out = _dedup([
        f(entity_id="FGI-001", category="mandate"),
        f(entity_id="FGI-001", category="filing"),
    ])
    assert len(out) == 2


def test_dedup_by_name_when_no_id():
    out = _dedup([
        f(entity_name="FGI Oslo AS", category="status"),
        f(entity_name="fgi oslo as", category="status"),  # case/space variant
    ])
    assert len(out) == 1


def test_dedup_by_title_when_no_id_or_name():
    out = _dedup([
        f(category="data_integrity", title="Unknown jurisdiction: Noveria"),
        f(category="data_integrity", title="Unknown jurisdiction:  Noveria "),
    ])
    assert len(out) == 1


def test_conflict_on_two_fields_of_one_entity_both_survive():
    out = _dedup([
        f(category="conflict", entity_id="FGI-002", title="mandate date disagrees"),
        f(category="conflict", entity_id="FGI-002", title="board members disagree"),
    ])
    assert len(out) == 2


def test_three_noveria_variants_collapse():
    # one entity-level finding (with id) + two bare jurisdiction notes that the
    # model worded differently and gave no id
    out = _dedup([
        f(category="data_integrity", entity_id="FGI-033",
          title="Jurisdiction not recognised: FGI Noveria Tactical Holdings Corp."),
        f(category="data_integrity", entity_id=None, entity_name=None,
          title="Invalid jurisdiction: Noveria"),
        f(category="data_integrity", entity_id=None, entity_name=None,
          title="Suspicious jurisdiction: Noveria"),
    ])
    # the two bare "Noveria" notes merge; the entity-level finding may stay
    assert sum(1 for x in out if "noveria" in x.title.lower()) <= 2
    titles = [x.title for x in out]
    assert "Invalid jurisdiction: Noveria" in titles
    assert "Suspicious jurisdiction: Noveria" not in titles  # merged away


def test_name_only_finding_collapses_onto_entity_id():
    out = _dedup([
        f(category="data_integrity", entity_id="FGI-014",
          entity_name="FGI Madrid Retail II S.L.", title="Duplicate registration: FGI Madrid Retail II S.L."),
        f(category="data_integrity", entity_id=None,
          entity_name="FGI Madrid Retail II S.L.", title="Duplicate entity name: FGI Madrid Retail II S.L."),
    ])
    assert len(out) == 1
    assert out[0].entity_id == "FGI-014"  # first occurrence wins


def test_preserves_first_occurrence_order():
    out = _dedup([
        f(entity_id="FGI-001", title="first"),
        f(entity_id="FGI-002", title="second"),
        f(entity_id="FGI-001", title="dup"),
    ])
    assert [x.entity_id for x in out] == ["FGI-001", "FGI-002"]
    assert out[0].title == "first"
