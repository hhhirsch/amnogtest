from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from html import unescape
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
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    page_w = max(60, pdf.w - pdf.l_margin - pdf.r_margin)

    url_pattern = re.compile(r"https?://\S+")

    def _soft_break_url(url: str) -> str:
        # Keep output latin-1 compatible for core FPDF fonts.
        return url.replace("/", "/\n").replace("-", "-\n")

    def to_latin1_safe(s: str) -> str:
        s = unescape(s or "")
        # Normalize common typography variants before fallback replacement.
        s = s.replace("\xa0", " ")
        s = s.replace("–", "-").replace("—", "-")
        s = s.replace("•", "-").replace("\u2022", "-")
        s = s.replace("’", "'").replace("“", '"').replace("”", '"')
        s = unicodedata.normalize("NFKC", s)
        # Guarantee FPDF core-font compatibility.
        return s.encode("latin-1", errors="replace").decode("latin-1")

    def wrap(txt: str) -> str:
        txt = to_latin1_safe(txt)
        # URL soft breaks (latin-1 safe)
        return url_pattern.sub(lambda m: _soft_break_url(m.group(0)), txt)

    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(page_w, 8, wrap("AMNOG Comparator Shortlist (MVP)"))

    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(page_w, 6, wrap(f"Therapiegebiet: {request_payload.get('therapy_area', '')}"))
    pdf.multi_cell(page_w, 6, wrap(f"Generiert: {response_payload.get('generated_at', '')}"))
    pdf.ln(2)

    for candidate in response_payload.get("candidates", []):
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(
            page_w,
            6,
            wrap(f"#{candidate.get('rank')} {candidate.get('candidate_text', '')}"),
        )

        pdf.set_font("Helvetica", size=9)
        pdf.multi_cell(
            page_w,
            5,
            wrap(
                "Confidence: {c} | Support: {s} | Fälle: {n}".format(
                    c=candidate.get("confidence", ""),
                    s=candidate.get("support_score", ""),
                    n=candidate.get("support_cases", ""),
                )
            ),
        )

        for ref in (candidate.get("references") or [])[:3]:
            pdf.multi_cell(
                page_w,
                5,
                wrap(
                    f"- {ref.get('product_name','')} ({ref.get('decision_date','')}): {ref.get('url','')}"
                ),
            )
        pdf.ln(1)

    pdf.multi_cell(
        page_w,
        5,
        wrap("Disclaimer: Plausible Kandidaten-Shortlist, keine verbindliche ZVT-Festlegung."),
    )

    out = BytesIO(pdf.output(dest="S").encode("latin-1", errors="replace"))
    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=shortlist.pdf"},
    )
