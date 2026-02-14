from __future__ import annotations

from datetime import datetime
from io import BytesIO
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fpdf import FPDF

from app.models import (
    CandidateResult,
    LeadRequest,
    LeadResponse,
    RunResponse,
    ShortlistRequest,
    ShortlistResponse,
)
from app.shortlist import shortlist
from app.store import get_run, init_db, save_lead, save_run

app = FastAPI(title="AMNOG Comparator Shortlist MVP", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.post("/api/shortlist", response_model=ShortlistResponse)
def create_shortlist(payload: ShortlistRequest) -> ShortlistResponse:
    domain_req = payload.to_domain()
    domain_candidates, ambiguity = shortlist(domain_req)
    run_id = str(uuid4())
    generated_at = datetime.utcnow()

    # Convert Domain -> Pydantic response models
    candidates = [CandidateResult.from_domain(c) for c in domain_candidates]
    response_payload = {
        "run_id": run_id,
        "candidates": [c.model_dump() for c in candidates],
        "ambiguity": ambiguity,
        "generated_at": generated_at.isoformat(),
    }
    save_run(run_id, payload.model_dump(), response_payload)
    return ShortlistResponse(**response_payload)


@app.get("/api/run/{run_id}", response_model=RunResponse)
def read_run(run_id: str) -> RunResponse:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id not found")
    return RunResponse(**run)


@app.post("/api/leads", response_model=LeadResponse)
def create_lead(payload: LeadRequest) -> LeadResponse:
    if not payload.consent:
        raise HTTPException(status_code=400, detail="consent is required")
    if not get_run(payload.run_id):
        raise HTTPException(status_code=404, detail="run_id not found")
    lead_id, saved_at = save_lead(payload.run_id, payload.email, payload.company, payload.consent)
    return LeadResponse(lead_id=lead_id, saved_at=saved_at)


@app.post("/api/export/pdf")
def export_pdf(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id not found")

    response_payload = run["response_payload"]
    request_payload = run["request_payload"]

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "AMNOG Comparator Shortlist (MVP)")
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, f"Therapiegebiet: {request_payload['therapy_area']}")
    pdf.multi_cell(0, 6, f"Generiert: {response_payload['generated_at']}")
    pdf.ln(2)

    for candidate in response_payload["candidates"]:
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 6, f"#{candidate['rank']} {candidate['candidate_text']}")
        pdf.set_font("Helvetica", size=9)
        pdf.multi_cell(
            0,
            5,
            f"Confidence: {candidate['confidence']} | Support: {candidate['support_score']} | Fälle: {candidate['support_cases']}",
        )
        for ref in candidate["references"][:3]:
            pdf.multi_cell(0, 5, f"- {ref['product_name']} ({ref['decision_date']}): {ref['url']}")
        pdf.ln(1)

    pdf.multi_cell(0, 5, "Disclaimer: Plausible Kandidaten-Shortlist, keine verbindliche ZVT-Festlegung.")
    out = BytesIO(pdf.output(dest="S").encode("latin-1"))

    return StreamingResponse(out, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=shortlist.pdf"})
