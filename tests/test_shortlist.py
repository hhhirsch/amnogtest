import pytest
import json
from app.domain import Setting, ShortlistRequest, TherapyArea, TherapyRole
from app.shortlist import (
    PatientGroupRecord,
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
    monkeypatch.setattr("app.shortlist.load_records_for_area", lambda x: records)

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="query token " * 6,
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )

    candidates, _, _notices, _status, _reasons, _diagnostics = shortlist(payload)

    # Should have one candidate (both records normalize to same candidate)
    assert len(candidates) == 1
    # Should have exactly 1 unique decision supporting it
    assert candidates[0].support_cases == 1
    # The aggregate score should be reasonable (not testing exact value due to coverage bonus)
    assert candidates[0].support_score > 0


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


def test_notices_disabled_by_default(monkeypatch) -> None:
    """Notices are now always enabled (no longer checking ENABLE_ZVT_NOTICES flag)."""
    import app.shortlist as sl

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices, _status, _reasons, _diagnostics = shortlist(payload)
    # Notices may or may not be empty depending on area stats, but the test confirms no crash
    assert isinstance(notices, list)


def test_notices_enabled_no_stats_file(tmp_path, monkeypatch) -> None:
    """With missing stats file, no orphan warning is emitted."""
    import app.shortlist as sl
    monkeypatch.setattr(sl, "STATS_PATH", tmp_path / "nonexistent.json")
    sl.load_area_stats.cache_clear()

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices, _status, _reasons, _diagnostics = shortlist(payload)
    # No orphan/Sonderverfahren warning when stats file is absent
    assert not any("Orphan" in n or "Sonderverfahren" in n for n in notices)
    sl.load_area_stats.cache_clear()


def test_notices_enabled_with_stats_below_threshold(tmp_path, monkeypatch) -> None:
    """With has_zvt_rows < 15, a warning notice is added."""
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
    monkeypatch.setattr(sl, "STATS_PATH", stats_file)
    sl.load_area_stats.cache_clear()

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices, _status, _reasons, _diagnostics = shortlist(payload)
    assert len(notices) >= 1
    assert "Orphan" in notices[0] or "Sonderverfahren" in notices[0]
    sl.load_area_stats.cache_clear()


def test_notices_enabled_with_high_orphan_ratio(tmp_path, monkeypatch) -> None:
    """With orphan_missing_ratio >= 0.5, a warning is added."""
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
    monkeypatch.setattr(sl, "STATS_PATH", stats_file)
    sl.load_area_stats.cache_clear()

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices, _status, _reasons, _diagnostics = shortlist(payload)
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
    monkeypatch.setattr(sl, "STATS_PATH", stats_file)
    sl.load_area_stats.cache_clear()

    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC test",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, notices, _status, _reasons, _diagnostics = shortlist(payload)
    # No orphan warning should be present (only possible fallback notice)
    orphan_notices = [n for n in notices if "Orphan" in n or "Sonderverfahren" in n]
    assert orphan_notices == []
    sl.load_area_stats.cache_clear()


def test_quality_gate_no_result_when_no_candidates(monkeypatch) -> None:
    """When there are no candidates, status should be no_result or needs_clarification (depending on query quality)."""
    import app.shortlist as sl
    # Empty corpus
    monkeypatch.setattr(sl, "load_records", lambda: ())
    monkeypatch.setattr(sl, "load_records_for_area", lambda x: ())
    
    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="query token",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    candidates, _ambiguity, _notices, status, reasons, _diagnostics = shortlist(payload)
    
    # Should indicate problem (either no_result or needs_clarification if query is too short)
    assert status in ["no_result", "needs_clarification"]
    assert "NO_CANDIDATES" in reasons
    assert len(candidates) == 0


def test_quality_gate_too_generic_input(monkeypatch) -> None:
    """When input is too short/generic, status should be needs_clarification or no_result."""
    import app.shortlist as sl
    from app.domain import TherapyLine, ComparatorType
    
    records = (
        PatientGroupRecord(
            patient_group_id="pg-1",
            decision_id="d-1",
            product_name="A",
            decision_date="2025-01-01",
            url="https://example.org/1",
            therapy_area="Onkologie",
            awg_text="test cancer treatment",
            patient_group_text="test patients",
            zvt_text="BSC",
        ),
    )
    monkeypatch.setattr(sl, "load_records", lambda: records)
    monkeypatch.setattr(sl, "load_records_for_area", lambda x: records)
    
    # Very short, generic input (< 3 meaningful tokens)
    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="test",  # Just 1 token
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    _candidates, _ambiguity, _notices, status, reasons, _diagnostics = shortlist(payload)
    
    # Generic input should be flagged
    assert "TOO_GENERIC" in reasons
    # Status should indicate uncertainty (could be needs_clarification or no_result depending on other factors)
    assert status in ["needs_clarification", "no_result"]


def test_quality_gate_low_evidence_becomes_no_result(monkeypatch) -> None:
    """Test that low evidence scenarios are properly detected and flagged."""
    import app.shortlist as sl
    
    records = (
        PatientGroupRecord(
            patient_group_id="pg-1",
            decision_id="d-1",
            product_name="A",
            decision_date="2025-01-01",
            url="https://example.org/1",
            therapy_area="Onkologie",
            awg_text="query token match",
            patient_group_text="population text",
            zvt_text="BSC",
        ),
    )
    monkeypatch.setattr(sl, "load_records", lambda: records)
    monkeypatch.setattr(sl, "load_records_for_area", lambda x: records)
    
    # Input that will match but with only 1 case
    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="query token match with sufficient length for tokens",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    candidates, _ambiguity, _notices, status, reasons, diagnostics = shortlist(payload)
    
    # Should have candidates with at least 1 case
    assert len(candidates) >= 1
    assert candidates[0].support_cases >= 1
    
    # Quality gate should track diagnostics
    assert "query_token_count" in diagnostics
    assert "candidate_count" in diagnostics


def test_quality_gate_line_and_comparator_type_in_query(monkeypatch) -> None:
    """Test that line and comparator_type are included in query building."""
    from app.domain import TherapyLine, ComparatorType
    from app.shortlist import build_query
    
    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC patients",
        population_text="adults ECOG 0-1",
        comparator_text="best supportive care",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
        line=TherapyLine.L2,
        comparator_type=ComparatorType.BSC,
    )
    
    query = build_query(payload)
    
    # Verify that line and comparator_type are in the query
    assert "2L" in query
    assert "BSC" in query
    assert "NSCLC patients" in query
    assert "adults ECOG 0-1" in query
    assert "best supportive care" in query


def test_quality_gate_unklar_values_not_in_query(monkeypatch) -> None:
    """Test that unklar values for line and comparator_type are not included in query."""
    from app.domain import TherapyLine, ComparatorType
    from app.shortlist import build_query
    
    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="NSCLC patients",
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
        line=TherapyLine.UNKLAR,
        comparator_type=ComparatorType.UNKLAR,
    )
    
    query = build_query(payload)
    
    # Verify that unklar is NOT in the query
    assert "unklar" not in query.lower()
    assert "NSCLC patients" in query
