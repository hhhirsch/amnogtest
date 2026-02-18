import pytest
import json
from app.domain import ComparatorType, Setting, ShortlistRequest, TherapyArea, TherapyLine, TherapyRole
from app.shortlist import (
    PatientGroupRecord,
    build_query,
    normalize_candidate,
    recency_weight,
    shortlist,
    load_area_stats,
)


def test_normalize_candidate_bsc_variants_dedup_key() -> None:
    assert normalize_candidate("Best supportive care") == "bsc"
    assert normalize_candidate("Best supportive care (BSC)") == "bsc"
    assert normalize_candidate("B.S.C.") == "bsc"


def test_normalize_candidate_physician_wording_stable() -> None:
    normalized = normalize_candidate(
        "patientenindividuelle Therapie nach ärztlicher Maßgabe"
    )
    assert normalized == "pit nach arztlicher maßgabe"

    normalized_alt = normalize_candidate(
        "Optimierte Standardtherapie nach Maßgabe des Arztes"
    )
    assert "nach arztlicher maßgabe" in normalized_alt


def test_shortlist_caps_score_per_decision(monkeypatch) -> None:
    records = (
        PatientGroupRecord(
            patient_group_id="pg-1",
            decision_id="d-1",
            product_name="A",
            decision_date="2025-01-01",
            url="https://example.org/1",
            therapy_area="Onkologie",
            awg_text="query token",
            patient_group_text="query token",
            zvt_text="Best supportive care",
        ),
        PatientGroupRecord(
            patient_group_id="pg-2",
            decision_id="d-1",
            product_name="A",
            decision_date="2025-01-01",
            url="https://example.org/2",
            therapy_area="Onkologie",
            awg_text="query token",
            patient_group_text="query token",
            zvt_text="BSC",
        ),
    )

    monkeypatch.setattr("app.shortlist.load_records", lambda: records)

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="query token " * 6,
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )

    candidates, _, _notices = shortlist(payload)

    assert len(candidates) == 1
    assert candidates[0].support_cases == 1
    assert candidates[0].support_score == pytest.approx(
        max(ref.score for ref in candidates[0].references), rel=1e-4
    )


def test_recency_weight_invalid_date_fallback() -> None:
    assert recency_weight("invalid") == 0.8


def test_load_area_stats_missing_file_returns_empty(tmp_path, monkeypatch) -> None:
    """load_area_stats() must never crash and return {} when the file is absent."""
    import app.shortlist as sl
    monkeypatch.setattr(sl, "STATS_PATH", tmp_path / "nonexistent.json")
    sl.load_area_stats.cache_clear()
    assert sl.load_area_stats() == {}
    sl.load_area_stats.cache_clear()


def test_load_area_stats_corrupt_file_returns_empty(tmp_path, monkeypatch) -> None:
    """load_area_stats() must never crash and return {} when the file is corrupt."""
    import app.shortlist as sl
    bad_file = tmp_path / "patient_groups_stats.json"
    bad_file.write_text("NOT JSON", encoding="utf-8")
    monkeypatch.setattr(sl, "STATS_PATH", bad_file)
    sl.load_area_stats.cache_clear()
    assert sl.load_area_stats() == {}
    sl.load_area_stats.cache_clear()


def test_notices_disabled_when_flag_off(monkeypatch) -> None:
    """With ENABLE_ZVT_NOTICES=0 (explicitly disabled), notices must always be empty."""
    import app.shortlist as sl
    monkeypatch.setattr(sl, "ENABLE_ZVT_NOTICES", False)

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices = shortlist(payload)
    assert notices == []


def test_notices_enabled_no_stats_file(tmp_path, monkeypatch) -> None:
    """With ENABLE_ZVT_NOTICES=1 and missing stats file, no orphan warning is emitted."""
    import app.shortlist as sl
    monkeypatch.setattr(sl, "ENABLE_ZVT_NOTICES", True)
    monkeypatch.setattr(sl, "STATS_PATH", tmp_path / "nonexistent.json")
    sl.load_area_stats.cache_clear()

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices = shortlist(payload)
    # No orphan/Sonderverfahren warning when stats file is absent
    assert not any("Orphan" in n or "Sonderverfahren" in n for n in notices)
    sl.load_area_stats.cache_clear()


def test_notices_enabled_with_stats_below_threshold(tmp_path, monkeypatch) -> None:
    """With ENABLE_ZVT_NOTICES=1 and has_zvt_rows < 15, a warning notice is added."""
    import app.shortlist as sl
    stats = {
        "Onkologie": {
            "total_rows": 20,
            "has_zvt_rows": 5,
            "orphan_rows": 2,
            "orphan_missing_zvt_rows": 1,
        }
    }
    stats_file = tmp_path / "patient_groups_stats.json"
    stats_file.write_text(json.dumps(stats), encoding="utf-8")
    monkeypatch.setattr(sl, "ENABLE_ZVT_NOTICES", True)
    monkeypatch.setattr(sl, "STATS_PATH", stats_file)
    sl.load_area_stats.cache_clear()

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices = shortlist(payload)
    assert len(notices) >= 1
    assert "Orphan" in notices[0] or "Sonderverfahren" in notices[0]
    sl.load_area_stats.cache_clear()


def test_notices_enabled_with_high_orphan_ratio(tmp_path, monkeypatch) -> None:
    """With ENABLE_ZVT_NOTICES=1 and orphan_missing_ratio >= 0.5, a warning is added."""
    import app.shortlist as sl
    stats = {
        "Onkologie": {
            "total_rows": 10,
            "has_zvt_rows": 20,  # > 15 so threshold 1 not triggered
            "orphan_rows": 6,
            "orphan_missing_zvt_rows": 5,  # ratio = 5/10 = 0.5
        }
    }
    stats_file = tmp_path / "patient_groups_stats.json"
    stats_file.write_text(json.dumps(stats), encoding="utf-8")
    monkeypatch.setattr(sl, "ENABLE_ZVT_NOTICES", True)
    monkeypatch.setattr(sl, "STATS_PATH", stats_file)
    sl.load_area_stats.cache_clear()

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices = shortlist(payload)
    assert len(notices) >= 1
    sl.load_area_stats.cache_clear()


def test_notices_no_warning_when_thresholds_not_met(tmp_path, monkeypatch) -> None:
    """With sufficient zVT coverage, no Orphan warning should appear."""
    import app.shortlist as sl
    stats = {
        "Onkologie": {
            "total_rows": 100,
            "has_zvt_rows": 80,  # >= 15
            "orphan_rows": 4,
            "orphan_missing_zvt_rows": 3,  # ratio = 3/100 = 0.03 < 0.5
        }
    }
    stats_file = tmp_path / "patient_groups_stats.json"
    stats_file.write_text(json.dumps(stats), encoding="utf-8")
    monkeypatch.setattr(sl, "ENABLE_ZVT_NOTICES", True)
    monkeypatch.setattr(sl, "STATS_PATH", stats_file)
    sl.load_area_stats.cache_clear()

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices = shortlist(payload)
    # No orphan warning should be present (only possible fallback notice)
    orphan_notices = [n for n in notices if "Orphan" in n or "Sonderverfahren" in n]
    assert orphan_notices == []
    sl.load_area_stats.cache_clear()


def test_notices_enabled_by_default() -> None:
    """ENABLE_ZVT_NOTICES should default to True (default env value '1')."""
    import app.shortlist as sl
    assert sl.ENABLE_ZVT_NOTICES is True


def test_build_query_includes_line_and_comparator_type() -> None:
    """build_query should include line and comparator_type when provided."""
    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
        line=TherapyLine.L2,
        comparator_type=ComparatorType.AKTIV,
    )
    query = build_query(payload)
    assert "Therapielinie: 2L" in query
    assert "Comparator-Typ: aktiv" in query


def test_build_query_without_optional_fields() -> None:
    """build_query should work without line and comparator_type."""
    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    query = build_query(payload)
    assert "NSCLC" in query
    assert "Therapielinie" not in query
    assert "Comparator-Typ" not in query
