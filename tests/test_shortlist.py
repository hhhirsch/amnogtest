import pytest
from app.domain import Setting, ShortlistRequest, TherapyArea, TherapyRole
from app.shortlist import (
    PatientGroupRecord,
    normalize_candidate,
    recency_weight,
    shortlist,
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

    candidates, _ = shortlist(payload)

    assert len(candidates) == 1
    assert candidates[0].support_cases == 1
    assert candidates[0].support_score == pytest.approx(
        max(ref.score for ref in candidates[0].references), rel=1e-4
    )


def test_recency_weight_invalid_date_fallback() -> None:
    assert recency_weight("invalid") == 0.8
