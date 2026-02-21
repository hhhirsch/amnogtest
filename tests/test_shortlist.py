import pytest
import json
from app.domain import ComparatorType, Setting, ShortlistRequest, TherapyArea, TherapyLine, TherapyRole, CandidateResult as DomainCandidateResult, ReferenceItem as DomainReferenceItem
from app.models import CandidateResult
from app.shortlist import (
    PatientGroupRecord,
    build_query,
    normalize_candidate,
    recency_weight,
    shortlist,
    load_area_stats,
    derive_reliability,
    detect_red_flags,
    apply_domain_penalties,
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

    candidates, _, _notices, _reasons = shortlist(payload)

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
    _candidates, _ambiguity, notices, _reasons = shortlist(payload)
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
    _candidates, _ambiguity, notices, _reasons = shortlist(payload)
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
    _candidates, _ambiguity, notices, _reasons = shortlist(payload)
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
    _candidates, _ambiguity, notices, _reasons = shortlist(payload)
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
    _candidates, _ambiguity, notices, _reasons = shortlist(payload)
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


# ===== Tests for derive_reliability() =====


def _make_candidate(support_cases: int, confidence: str, support_score: float = 1.0) -> CandidateResult:
    """Helper to create a CandidateResult for testing."""
    return CandidateResult(
        rank=1,
        candidate_text="Test Candidate",
        support_score=support_score,
        confidence=confidence,
        support_cases=support_cases,
        references=[],
    )


def test_derive_reliability_no_result() -> None:
    """no_result -> reliability='niedrig'"""
    rel, reasons = derive_reliability(
        status="no_result",
        candidates=[],
        ambiguity="niedrig",
        reasons=None,
        notices=None,
    )
    assert rel == "niedrig"
    assert "Kein belastbares Ergebnis gefunden." in reasons


def test_derive_reliability_too_generic() -> None:
    """TOO_GENERIC -> reliability='niedrig' + erster Grund 'zu allgemein'"""
    candidates = [_make_candidate(support_cases=3, confidence="hoch")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=["TOO_GENERIC"],
        notices=None,
    )
    assert rel == "niedrig"
    assert "Eingabe ist zu allgemein – bitte präzisieren." == reasons[0]


def test_derive_reliability_weak_evidence_low_conf() -> None:
    """cases=1 + low_conf -> reliability='niedrig'"""
    candidates = [_make_candidate(support_cases=1, confidence="niedrig")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=None,
        notices=None,
    )
    assert rel == "niedrig"
    assert "Sehr wenige ähnliche Entscheidungen vorhanden." in reasons


def test_derive_reliability_weak_evidence_high_amb() -> None:
    """cases=1 + high_amb -> reliability='niedrig'"""
    candidates = [_make_candidate(support_cases=1, confidence="mittel")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="hoch",
        reasons=None,
        notices=None,
    )
    assert rel == "niedrig"
    assert "Sehr wenige ähnliche Entscheidungen vorhanden." in reasons


def test_derive_reliability_strong_evidence_high_conf_no_high_amb() -> None:
    """cases>=3 + conf='hoch' + amb!='hoch' -> reliability='hoch'"""
    candidates = [_make_candidate(support_cases=3, confidence="hoch")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=None,
        notices=None,
    )
    assert rel == "hoch"


def test_derive_reliability_strong_evidence_low_amb_no_fallback() -> None:
    """cases>=3 + amb='niedrig' + no fallback -> reliability='hoch'"""
    candidates = [_make_candidate(support_cases=4, confidence="mittel")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=None,
        notices=[],
    )
    assert rel == "hoch"


def test_derive_reliability_medium_with_fallback() -> None:
    """cases=2 + fallback notice -> reliability='mittel' with fallback reason"""
    candidates = [_make_candidate(support_cases=2, confidence="mittel")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="mittel",
        reasons=None,
        notices=["Ergebnis basiert auf Analogfällen"],
    )
    assert rel == "mittel"
    assert any("Analogfällen" in r for r in reasons)


def test_derive_reliability_reason_priority_blocker_first() -> None:
    """Blocker reasons should appear before warnings."""
    candidates = [_make_candidate(support_cases=1, confidence="niedrig")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="hoch",
        reasons=["TOO_GENERIC"],
        notices=["Ergebnis basiert auf Analogfällen"],
    )
    assert rel == "niedrig"
    # TOO_GENERIC (blocker) should be first
    assert "Eingabe ist zu allgemein" in reasons[0]
    # weak_evid (blocker) should be second
    assert "Sehr wenige ähnliche Entscheidungen" in reasons[1]
    # Fallback or high_amb (warning) should be third (max 3)
    assert len(reasons) == 3
    # The third reason should be a warning (either fallback or high_amb)
    assert any("Analogfällen" in r or "ähnlich plausibel" in r for r in reasons)


def test_derive_reliability_max_three_reasons() -> None:
    """Should return at most 3 reasons."""
    candidates = [_make_candidate(support_cases=1, confidence="niedrig")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="hoch",
        reasons=["TOO_GENERIC"],
        notices=["Ergebnis basiert auf Analogfällen"],
    )
    assert len(reasons) <= 3


def test_derive_reliability_mittel_no_generic_fallback() -> None:
    """For mittel with cases=2 and ambiguity=mittel, concrete limiting reasons are used, not the generic fallback."""
    candidates = [_make_candidate(support_cases=2, confidence="mittel")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="mittel",
        reasons=None,
        notices=None,
    )
    assert rel == "mittel"
    # Must NOT use the generic fallback sentence
    assert "Bewertung basiert auf verfügbaren G-BA-Entscheidungen." not in reasons
    # Must use concrete limiting reasons
    assert "Nur 2 ähnliche Entscheidungen vorhanden." in reasons
    assert "Trennschärfe ist nur mittel – mehrere Optionen bleiben möglich." in reasons


def test_derive_reliability_hoch_positive_bullets() -> None:
    """For hoch with cases>=3, ambiguity=niedrig, conf=hoch: positive bullets, no generic fallback."""
    candidates = [_make_candidate(support_cases=5, confidence="hoch")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=None,
        notices=None,
    )
    assert rel == "hoch"
    assert "Bewertung basiert auf verfügbaren G-BA-Entscheidungen." not in reasons
    assert "5 vergleichbare Entscheidungen stützen die Top-Option." in reasons
    assert "Klare Trennschärfe zwischen Top-Option und Alternativen." in reasons


# ===== Tests for detect_red_flags() =====


def _make_domain_candidate(candidate_text: str, support_cases: int = 1, confidence: str = "mittel") -> DomainCandidateResult:
    """Helper to create a domain CandidateResult for red flag testing."""
    return DomainCandidateResult(
        rank=1,
        candidate_text=candidate_text,
        support_score=1.0,
        confidence=confidence,
        support_cases=support_cases,
        references=[],
    )


def test_red_flag_platin_rechallenge() -> None:
    """Post-platinum progression + cisplatin comparator → triggers flag."""
    query = "Progress nach platinbasierter Chemotherapie"
    candidate = _make_domain_candidate("Cisplatin + 5-Fluorouracil")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "SETTING_MISMATCH_PLATIN" in flags


def test_red_flag_platin_carboplatin() -> None:
    """Post-platinum progression + carboplatin → triggers flag."""
    query = "post-platin Progression"
    candidate = _make_domain_candidate("Carboplatin + Paclitaxel")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "SETTING_MISMATCH_PLATIN" in flags


def test_red_flag_no_platin_mismatch_when_no_post_platin() -> None:
    """Without post-platin markers, cisplatin should not trigger flag."""
    query = "Erstlinientherapie bei fortgeschrittenem Zervixkarzinom"
    candidate = _make_domain_candidate("Cisplatin + Paclitaxel")
    flags = detect_red_flags(query, candidate, TherapyLine.L1)
    assert "SETTING_MISMATCH_PLATIN" not in flags


def test_red_flag_bsc_contradiction() -> None:
    """Systemic therapy suitable + BSC → triggers flag."""
    query = "weitere Systemtherapie möglich, ECOG 0-1"
    candidate = _make_domain_candidate("Best Supportive Care")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "BSC_CONTRADICTION" in flags


def test_red_flag_no_bsc_contradiction_without_marker() -> None:
    """Without therapy-suitable markers, BSC should not trigger flag."""
    query = "Palliative Situation, keine weitere Therapie"
    candidate = _make_domain_candidate("Best Supportive Care")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "BSC_CONTRADICTION" not in flags


def test_red_flag_line_mismatch_1l() -> None:
    """First-line + post-progression candidate → triggers flag."""
    query = "Erstlinientherapie"
    candidate = _make_domain_candidate("Therapie nach Versagen der Erstlinie")
    flags = detect_red_flags(query, candidate, TherapyLine.L1)
    assert "LINE_MISMATCH_1L" in flags


def test_red_flag_no_line_mismatch_for_2l() -> None:
    """Second-line should not trigger LINE_MISMATCH_1L."""
    query = "Zweitlinientherapie"
    candidate = _make_domain_candidate("Therapie nach Versagen der Erstlinie")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "LINE_MISMATCH_1L" not in flags


# ===== Tests for apply_domain_penalties() =====


def test_penalty_platin_rechallenge() -> None:
    """Cisplatin score should drop significantly post-platin."""
    score = 10.0
    adjusted = apply_domain_penalties(
        score,
        query="Progress nach Platin, weitere Systemtherapie",
        candidate_text="Cisplatin + 5-FU",
        line=TherapyLine.L2,
    )
    assert adjusted < 5.0  # 0.3 penalty → 3.0


def test_penalty_bsc_when_therapy_suitable() -> None:
    """BSC score should drop when systemic therapy suitable."""
    score = 10.0
    adjusted = apply_domain_penalties(
        score,
        query="weitere Systemtherapie möglich",
        candidate_text="Best Supportive Care",
        line=TherapyLine.L2,
    )
    assert adjusted < 5.0  # 0.2 penalty → 2.0


def test_penalty_no_effect_when_no_mismatch() -> None:
    """No penalty when there's no mismatch."""
    score = 10.0
    adjusted = apply_domain_penalties(
        score,
        query="Erstlinientherapie Zervixkarzinom",
        candidate_text="Pembrolizumab",
        line=TherapyLine.L1,
    )
    assert adjusted == score


def test_penalty_first_line_post_progression() -> None:
    """First-line + post-progression candidate should be penalized."""
    score = 10.0
    adjusted = apply_domain_penalties(
        score,
        query="Erstlinientherapie",
        candidate_text="nach Versagen der Erstlinie",
        line=TherapyLine.L1,
    )
    assert adjusted < score  # 0.5 penalty → 5.0


def test_penalty_late_line_bsc_boost() -> None:
    """Late-line + BSC should get a boost."""
    score = 10.0
    adjusted = apply_domain_penalties(
        score,
        query="Drittlinientherapie",
        candidate_text="Best Supportive Care",
        line=TherapyLine.SPAETER,
    )
    assert adjusted > score  # 1.5 boost → 15.0


# ===== Tests for derive_reliability with red flags =====


def test_plausibility_downgrade_with_red_flags() -> None:
    """Red flags + 2 cases → reliability niedrig."""
    candidates = [_make_candidate(support_cases=2, confidence="mittel")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="mittel",
        reasons=["SETTING_MISMATCH_PLATIN"],
        notices=[],
    )
    assert rel == "niedrig"
    assert any("Platin-Rechallenge" in r for r in reasons)


def test_plausibility_downgrade_bsc_contradiction() -> None:
    """BSC_CONTRADICTION + few cases → reliability niedrig."""
    candidates = [_make_candidate(support_cases=1, confidence="niedrig")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=["BSC_CONTRADICTION"],
        notices=[],
    )
    assert rel == "niedrig"
    assert any("Best Supportive Care" in r for r in reasons)


def test_red_flags_with_strong_evidence_gives_mittel() -> None:
    """Red flags + strong evidence (>=3 cases) → mittel (not hoch)."""
    candidates = [_make_candidate(support_cases=5, confidence="hoch")]
    rel, _ = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=["SETTING_MISMATCH_PLATIN"],
        notices=[],
    )
    assert rel == "mittel"


def test_no_red_flags_strong_evidence_still_hoch() -> None:
    """Without red flags, strong evidence still produces 'hoch'."""
    candidates = [_make_candidate(support_cases=5, confidence="hoch")]
    rel, _ = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=[],
        notices=[],
    )
    assert rel == "hoch"


# ===== Tests for Watchful Waiting / BSC drift fix =====


def test_red_flag_watchful_waiting_contradiction() -> None:
    """systemtherapiefähig + watchful waiting candidate → BSC_CONTRADICTION flag."""
    query = "systemtherapiefähig, weitere Standardtherapie möglich"
    candidate = _make_domain_candidate("watchful waiting")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "BSC_CONTRADICTION" in flags


def test_red_flag_beobachtendes_abwarten_contradiction() -> None:
    """therapiefähig + beobachtendes Abwarten → BSC_CONTRADICTION flag."""
    query = "Patient therapiefähig, standardtherapie kommt in frage"
    candidate = _make_domain_candidate("Beobachtendes Abwarten")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "BSC_CONTRADICTION" in flags


def test_penalty_watchful_waiting_when_therapy_ok() -> None:
    """Watchful waiting score should drop strongly when systemic therapy suitable."""
    score = 10.0
    adjusted = apply_domain_penalties(
        score,
        query="systemtherapiefähig, weitere Systemtherapie möglich",
        candidate_text="watchful waiting",
        line=TherapyLine.L2,
    )
    assert adjusted == pytest.approx(0.5)  # 0.05 penalty → 0.5


def test_no_penalty_if_user_requests_passive() -> None:
    """No BSC penalty when user explicitly requests BSC as comparator type."""
    score = 10.0
    # build_query would produce "Comparator-Typ: BSC" in query → _query_requests_passive returns True
    adjusted = apply_domain_penalties(
        score,
        query="weitere Systemtherapie möglich\nComparator-Typ: BSC",
        candidate_text="bsc",
        line=TherapyLine.L2,
    )
    assert adjusted == score


def test_bsc_contradiction_always_niedrig_with_strong_evidence() -> None:
    """BSC_CONTRADICTION is a hard corridor exit: always 'niedrig' regardless of cases."""
    candidates = [_make_candidate(support_cases=5, confidence="hoch")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=["BSC_CONTRADICTION"],
        notices=[],
    )
    assert rel == "niedrig"
    assert any("Best Supportive Care" in r for r in reasons)
