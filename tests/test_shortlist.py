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
    is_menu_zvt,
    is_passive_candidate_text,
    split_zvt_items,
    comparator_id,
    MAX_CANDIDATE_KEYS,
    _query_requests_passive,
    _query_implies_active_intent,
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
    # aggregate_score adds a coverage-breadth bonus (log-based), so support_score
    # is slightly higher than the best single reference score.  The key invariant
    # is: no double-counting (score < 2× best ref) while being at least as large
    # as the best reference.
    max_ref_score = max(ref.score for ref in candidates[0].references)
    assert candidates[0].support_score >= max_ref_score
    assert candidates[0].support_score < 2 * max_ref_score


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


# ===== Tests for is_menu_zvt() =====


def test_is_menu_zvt_physician_discretion() -> None:
    """Menu markers are detected case-insensitively."""
    assert is_menu_zvt("nach ärztlicher maßgabe")
    assert is_menu_zvt("nach arztlicher maßgabe")   # normalized form
    assert is_menu_zvt("patientenindividuelle therapie")
    assert is_menu_zvt("unter auswahl von")
    assert is_menu_zvt("auswahl aus")
    assert is_menu_zvt("unter berücksichtigung von")
    assert is_menu_zvt("unter beruecksichtigung von")


def test_is_menu_zvt_pit_standalone() -> None:
    """Standalone 'pit' is a menu-zVT; 'pitavastatin' must not trigger it."""
    assert is_menu_zvt("pit")
    assert is_menu_zvt("therapie (pit)")
    assert not is_menu_zvt("pitavastatin")


def test_is_menu_zvt_plain_comparator_is_not_menu() -> None:
    """Regular comparator texts must not be classified as menu."""
    assert not is_menu_zvt("paclitaxel")
    assert not is_menu_zvt("bsc")
    assert not is_menu_zvt("pembrolizumab oder docetaxel")


# ===== Tests for split_zvt_items() =====


def test_split_zvt_items_empty_returns_empty() -> None:
    assert split_zvt_items("") == []
    assert split_zvt_items("   ") == []


def test_split_zvt_items_basic_oder_split() -> None:
    """'Paclitaxel oder Docetaxel' splits into two mono items (no menu markers)."""
    items = split_zvt_items("Paclitaxel oder Docetaxel")
    assert items == ["Paclitaxel", "Docetaxel"]


def test_split_zvt_items_semicolon_split() -> None:
    items = split_zvt_items("Pembrolizumab; Nivolumab")
    assert items == ["Pembrolizumab", "Nivolumab"]


def test_split_zvt_items_slash_split() -> None:
    items = split_zvt_items("Pembrolizumab / Nivolumab")
    assert items == ["Pembrolizumab", "Nivolumab"]


def test_split_zvt_items_menu_no_split() -> None:
    """Menu-zVT with 'oder' inside must NOT be split into atoms."""
    text = "Therapie nach ärztlicher Maßgabe unter Auswahl von X oder Y"
    result = split_zvt_items(text)
    assert result == [text]


def test_split_zvt_items_pit_no_split() -> None:
    """PIT texts must not be split."""
    text = "Patientenindividuelle Therapie (PIT) nach ärztlicher Maßgabe"
    result = split_zvt_items(text)
    assert result == [text]


def test_split_zvt_items_explosion_guard() -> None:
    """More than MAX_ZVT_ITEMS_PER_RECORD fragments → return original text."""
    many = " oder ".join([f"Drug{i}" for i in range(15)])
    result = split_zvt_items(many)
    assert result == [many]


def test_split_zvt_items_fragmentation_guard() -> None:
    """>=6 items AND partial menu marker 'auswahl' → return original text."""
    text = "auswahl: A oder B oder C oder D oder E oder F"
    result = split_zvt_items(text)
    assert result == [text]


def test_split_zvt_items_no_und_split() -> None:
    """'und' must NOT be used as a delimiter."""
    items = split_zvt_items("Capecitabin und Oxaliplatin")
    assert len(items) == 1
    assert items[0] == "Capecitabin und Oxaliplatin"


# ===== Tests for comparator_id() =====


def test_comparator_id_mono() -> None:
    """Plain drug names get 'mono:' prefix."""
    assert comparator_id("Paclitaxel") == "mono:paclitaxel"
    assert comparator_id("Docetaxel") == "mono:docetaxel"


def test_comparator_id_passive_bsc() -> None:
    """BSC variants all map to 'passive:bsc'."""
    assert comparator_id("Best supportive care") == "passive:bsc"
    assert comparator_id("BSC") == "passive:bsc"
    assert comparator_id("B.S.C.") == "passive:bsc"


def test_comparator_id_passive_watchful_waiting() -> None:
    assert comparator_id("watchful waiting") == "passive:watchful_waiting"
    assert comparator_id("Beobachtendes Abwarten") == "passive:watchful_waiting"


def test_comparator_id_menu_pit() -> None:
    """PIT / patientenindividuelle Therapie → 'menu:pit'."""
    assert comparator_id("Patientenindividuelle Therapie nach ärztlicher Maßgabe") == "menu:pit"
    assert comparator_id("PIT") == "menu:pit"


def test_comparator_id_menu_arztliche_massgabe() -> None:
    assert comparator_id("Therapie nach ärztlicher Maßgabe") == "menu:arztliche_massgabe"


def test_comparator_id_menu_auswahl() -> None:
    assert comparator_id("unter Auswahl von Therapie A") == "menu:auswahl"


def test_comparator_id_combo() -> None:
    """Combination therapies get sorted 'combo:' prefix."""
    cid = comparator_id("Pembrolizumab + Chemotherapie")
    assert cid.startswith("combo:")
    parts = cid[len("combo:"):].split("|")
    assert len(parts) == 2
    assert parts == sorted(parts)   # components are alphabetically sorted


def test_comparator_id_oder_list_produces_two_mono_ids() -> None:
    """After split_zvt_items, 'Paclitaxel oder Docetaxel' yields two distinct mono IDs."""
    items = split_zvt_items("Paclitaxel oder Docetaxel")
    ids = [comparator_id(i) for i in items]
    assert ids == ["mono:paclitaxel", "mono:docetaxel"]


# ===== Test candidate-key budget =====


def test_candidate_key_budget(monkeypatch) -> None:
    """Candidate key budget: a small MAX_CANDIDATE_KEYS cap limits aggregated keys.

    We patch MAX_CANDIDATE_KEYS to 3 and supply 20 distinct records.  Without
    the budget guard the aggregated dict would grow to 20 entries; with it,
    only 3 keys are ever created, so shortlist() returns ≤3 candidates.
    """
    import app.shortlist as sl
    monkeypatch.setattr(sl, "MAX_CANDIDATE_KEYS", 3)

    records = tuple(
        PatientGroupRecord(
            patient_group_id=f"pg-{i}",
            decision_id=f"d-{i}",
            product_name="X",
            decision_date="2024-01-01",
            url=f"https://example.org/{i}",
            therapy_area="Onkologie",
            awg_text="query token",
            patient_group_text="query token",
            zvt_text=f"UniqueDrug{i}",
        )
        for i in range(20)
    )
    monkeypatch.setattr("app.shortlist.load_records", lambda: records)
    from app.domain import Setting, ShortlistRequest, TherapyArea, TherapyRole
    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="query token " * 6,
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    candidates, _, _, _ = shortlist(payload)
    # Budget of 3 keys means at most 3 candidates can ever be returned
    assert len(candidates) <= 3


# ===== Tests for new A1 helper functions =====


def test_query_requests_passive_bsc_comparator_type() -> None:
    """'Comparator-Typ: BSC' in query (from build_query) → passive requested."""
    assert _query_requests_passive("nsclc\ncomparator-typ: bsc")


def test_query_requests_passive_explicit_bsc() -> None:
    """Explicit 'bsc' in query → passive requested."""
    assert _query_requests_passive("bsc als vergleich")


def test_query_requests_passive_watchful_waiting() -> None:
    assert _query_requests_passive("watchful waiting vergleich")


def test_query_requests_passive_abwarten() -> None:
    assert _query_requests_passive("abwarten")


def test_query_requests_passive_false_for_active_query() -> None:
    """Active oncology query → passive NOT requested."""
    assert not _query_requests_passive("rezidiviertes mamma-karzinom 2l systemtherapie")


def test_query_implies_active_intent_2l_line() -> None:
    """TherapyLine.L2 implies active intent."""
    assert _query_implies_active_intent("irgendwas", TherapyLine.L2)


def test_query_implies_active_intent_rezidiv_lexical() -> None:
    """'rezidiv' in query implies active intent even without line param."""
    assert _query_implies_active_intent("rezidiviertes mamma-karzinom", None)


def test_query_implies_active_intent_progress_marker() -> None:
    assert _query_implies_active_intent("progress nach vorbehandlung", None)


def test_query_implies_active_intent_therapy_ok_marker() -> None:
    """THERAPY_OK_MARKERS also imply active intent."""
    assert _query_implies_active_intent("systemtherapiefähig, ecog 0", None)


def test_query_implies_active_intent_false_for_passive_query() -> None:
    """Query without active markers and no late line → no active intent."""
    assert not _query_implies_active_intent("nsclc diagnose", None)


def test_query_implies_active_intent_spaeter_no_lexical() -> None:
    """TherapyLine.SPAETER alone does NOT imply active intent (preserves Boost 4)."""
    assert not _query_implies_active_intent("drittlinientherapie", TherapyLine.SPAETER)


# ===== Tests for is_passive_candidate_text() =====


def test_is_passive_candidate_text_bsc() -> None:
    assert is_passive_candidate_text("Best Supportive Care")
    assert is_passive_candidate_text("BSC")
    assert is_passive_candidate_text("B.S.C.")


def test_is_passive_candidate_text_watchful_waiting() -> None:
    assert is_passive_candidate_text("watchful waiting")


def test_is_passive_candidate_text_beobachtendes_abwarten() -> None:
    # normalize_candidate converts "beobachtendes abwarten" → "watchful waiting"
    assert is_passive_candidate_text("Beobachtendes Abwarten")


def test_is_passive_candidate_text_pit() -> None:
    # normalize_candidate converts "patientenindividuelle therapie" → "pit"
    assert is_passive_candidate_text("Patientenindividuelle Therapie")
    assert is_passive_candidate_text("PIT")


def test_is_passive_candidate_text_arztlicher_massgabe() -> None:
    # normalize_candidate normalises ärztlicher → arztlicher
    assert is_passive_candidate_text("nach ärztlicher Maßgabe")


def test_is_passive_candidate_text_false_for_active_drug() -> None:
    assert not is_passive_candidate_text("Paclitaxel")
    assert not is_passive_candidate_text("Pembrolizumab + Chemotherapie")


# ===== Tests for A2: active-intent penalty =====


def test_penalty_passive_when_active_intent_2l_line() -> None:
    """Passive candidate should be penalized for 2L line even without therapy_ok marker."""
    score = 10.0
    adjusted = apply_domain_penalties(
        score,
        query="Mamma HR+/HER2- Rezidiv",
        candidate_text="Beobachtendes Abwarten",
        line=TherapyLine.L2,
    )
    assert adjusted < score  # 0.05 penalty


def test_penalty_passive_when_active_intent_lexical() -> None:
    """Passive candidate should be penalized when query has active-intent lexical markers."""
    score = 10.0
    adjusted = apply_domain_penalties(
        score,
        query="progress nach vorbehandlung",
        candidate_text="watchful waiting",
        line=None,
    )
    assert adjusted < score


def test_no_penalty_passive_for_spaeter_no_lexical_markers() -> None:
    """SPAETER line without active lexical markers must NOT trigger the passive penalty."""
    score = 10.0
    adjusted = apply_domain_penalties(
        score,
        query="Drittlinientherapie",
        candidate_text="Best Supportive Care",
        line=TherapyLine.SPAETER,
    )
    # Boost 4 fires (1.5x); no Penalty 2
    assert adjusted > score


# ===== Tests for A3: PASSIVE_TOP1_MISMATCH red flag =====


def test_red_flag_passive_top1_mismatch_2l_rezidiv() -> None:
    """Active intent (2L line) + passive top candidate → PASSIVE_TOP1_MISMATCH."""
    query = "Mamma HR+/HER2- Rezidiv"
    candidate = _make_domain_candidate("Beobachtendes Abwarten")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "PASSIVE_TOP1_MISMATCH" in flags


def test_red_flag_passive_top1_mismatch_progress_marker() -> None:
    """Active intent (progress lexical) + passive candidate → PASSIVE_TOP1_MISMATCH."""
    query = "progress nach erstlinie"
    candidate = _make_domain_candidate("Best Supportive Care")
    flags = detect_red_flags(query, candidate, None)
    assert "PASSIVE_TOP1_MISMATCH" in flags


def test_no_passive_top1_mismatch_when_passive_requested() -> None:
    """No PASSIVE_TOP1_MISMATCH when BSC is explicitly requested."""
    query = "rezidiv\ncomparator-typ: bsc"
    candidate = _make_domain_candidate("BSC")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "PASSIVE_TOP1_MISMATCH" not in flags


def test_no_passive_top1_mismatch_for_active_candidate() -> None:
    """No PASSIVE_TOP1_MISMATCH when candidate is an active drug."""
    query = "rezidiviertes NSCLC 2L"
    candidate = _make_domain_candidate("Docetaxel")
    flags = detect_red_flags(query, candidate, TherapyLine.L2)
    assert "PASSIVE_TOP1_MISMATCH" not in flags


def test_derive_reliability_passive_top1_mismatch_always_niedrig() -> None:
    """PASSIVE_TOP1_MISMATCH is a hard corridor exit → always 'niedrig'."""
    candidates = [_make_candidate(support_cases=5, confidence="hoch")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=["PASSIVE_TOP1_MISMATCH"],
        notices=[],
    )
    assert rel == "niedrig"
    assert any("passiv" in r.lower() or "BSC" in r or "Abwarten" in r for r in reasons)


def test_derive_reliability_passive_top1_mismatch_reason_text() -> None:
    """PASSIVE_TOP1_MISMATCH produces expected German reason text."""
    candidates = [_make_candidate(support_cases=3, confidence="hoch")]
    rel, reasons = derive_reliability(
        status="ok",
        candidates=candidates,
        ambiguity="niedrig",
        reasons=["PASSIVE_TOP1_MISMATCH"],
        notices=[],
    )
    assert any("passiv" in r.lower() for r in reasons)


# ===== Tests for B1: split_zvt_items fragment guard =====


def test_split_zvt_items_drops_ohne_fragment() -> None:
    """'ohne Prednison' split fragment (starts with 'ohne ', <4 tokens) is dropped."""
    items = split_zvt_items("Docetaxel oder ohne Prednison")
    assert "ohne Prednison" not in items
    assert "Docetaxel" in items


def test_split_zvt_items_keeps_ohne_with_enough_tokens() -> None:
    """'ohne X Y Z W' (4+ tokens) is NOT dropped (might be a valid item)."""
    items = split_zvt_items("Chemotherapie oder ohne Prednison Ersatz Backup Fallback")
    # 'ohne Prednison Ersatz Backup Fallback' has 5 tokens → kept
    assert any("ohne" in it.lower() for it in items)


def test_split_zvt_items_drops_mit_fragment() -> None:
    """'mit BSC' (starts with 'mit ', only 2 tokens) is dropped."""
    items = split_zvt_items("Paclitaxel oder mit BSC")
    assert not any(it.strip().lower() == "mit bsc" for it in items)


# ===== Tests for B2: comparator_id returns "" for modifier-only fragments =====


def test_comparator_id_ohne_fragment_returns_empty() -> None:
    """'ohne Prednison' → '' (not a valid standalone comparator)."""
    assert comparator_id("ohne Prednison") == ""


def test_comparator_id_mit_fragment_returns_empty() -> None:
    """'mit BSC' → '' (modifier-only, < 4 tokens)."""
    assert comparator_id("mit BSC") == ""


def test_comparator_id_unter_fragment_returns_empty() -> None:
    """'unter Auswahl' → '' (only 2 tokens, starts with 'unter ')."""
    assert comparator_id("unter Kortison") == ""


def test_comparator_id_ohne_with_enough_tokens_not_empty() -> None:
    """'ohne Prednison Ersatz Backup Fallback' (5 tokens) → not empty."""
    cid = comparator_id("ohne Prednison Ersatz Backup Fallback")
    assert cid != ""


def test_comparator_id_normal_drug_not_affected() -> None:
    """Regular drug names are unaffected by fragment guard."""
    assert comparator_id("Paclitaxel") == "mono:paclitaxel"
    assert comparator_id("Best supportive care") == "passive:bsc"


# ===== Tests for B3: aggregation skips empty candidate_key =====


def test_aggregation_skips_ohne_fragment(monkeypatch) -> None:
    """Records whose only zVT item is a modifier-only fragment produce no candidate."""
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
            zvt_text="ohne Prednison",
        ),
        PatientGroupRecord(
            patient_group_id="pg-2",
            decision_id="d-2",
            product_name="B",
            decision_date="2025-01-01",
            url="https://example.org/2",
            therapy_area="Onkologie",
            awg_text="query token",
            patient_group_text="query token",
            zvt_text="Paclitaxel",
        ),
    )
    monkeypatch.setattr("app.shortlist.load_records", lambda: records)
    payload = ShortlistRequest(
        therapy_area=TherapyArea.ONKOLOGIE,
        indication_text="query token " * 6,
        setting=Setting.AMBULANT,
        role=TherapyRole.REPLACEMENT,
    )
    candidates, _, _, _ = shortlist(payload)
    # "ohne Prednison" should not appear as a candidate
    texts = [c.candidate_text.lower() for c in candidates]
    assert not any("ohne" in t for t in texts)
    # "Paclitaxel" should still appear
    assert any("paclitaxel" in t for t in texts)
