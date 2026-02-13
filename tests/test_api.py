from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_shortlist_and_run_lookup() -> None:
    payload = {
        "therapy_area": "Onkologie",
        "indication_text": "Erwachsene mit metastasiertem NSCLC nach Progress unter Erstlinientherapie und hoher Tumorlast.",
        "population_text": "ECOG 0-1, vorbehandelt in 2L mit platinhaltiger Therapie.",
        "setting": "ambulant",
        "role": "add-on",
        "line": "2L",
        "comparator_type": "aktiv",
    }
    response = client.post("/api/shortlist", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["candidates"]) > 0
    assert len(body["candidates"]) <= 5
    assert body["candidates"][0]["references"]

    run_response = client.get(f"/api/run/{body['run_id']}")
    assert run_response.status_code == 200
    assert run_response.json()["run_id"] == body["run_id"]


def test_lead_requires_consent() -> None:
    payload = {
        "therapy_area": "Onkologie",
        "indication_text": "Erwachsene mit metastasiertem NSCLC nach Progress unter Erstlinientherapie und hoher Tumorlast.",
        "setting": "unklar",
        "role": "unklar",
    }
    run_response = client.post("/api/shortlist", json=payload)
    run_id = run_response.json()["run_id"]

    lead_response = client.post(
        "/api/leads",
        json={"run_id": run_id, "email": "user@example.com", "consent": False},
    )
    assert lead_response.status_code == 400
