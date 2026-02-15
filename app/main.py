from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from html import unescape
from io import BytesIO
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://amnogtest-546n.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True, "service": "amnogtest", "docs": "/docs"}

@app.get("/health")
def health():
    return {"ok": True}

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

@app.get("/api/export/pdf")
def export_pdf(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id not found")

    response_payload = run.get("response_payload") or {}
    request_payload = run.get("request_payload") or {}

    therapy_area = (request_payload.get("therapy_area") or "").strip()
    indication = (request_payload.get("indication_text") or "").strip()

    # ---------- helpers ----------
    def safe_text(txt: str) -> str:
        txt = unescape(txt or "")
        txt = txt.replace("\xa0", " ")
        txt = txt.replace("–", "-").replace("—", "-")
        txt = txt.replace("•", "-").replace("\u2022", "-")
        txt = txt.replace("’", "'").replace("“", '"').replace("”", '"')
        txt = unicodedata.normalize("NFKC", txt)
        return txt.encode("latin-1", errors="replace").decode("latin-1")

    def safe_filename_component(s: str) -> str:
        s = (s or "").strip()
        # de-umlaut for nicer filenames
        s = (
            s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
             .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
             .replace("ß", "ss")
        )
        s = safe_text(s)
        s = s.replace(" ", "_")
        s = re.sub(r"[^A-Za-z0-9_\-]+", "", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s or "Export"

    def soft_break_url_display(url: str) -> str:
        # Nur fürs Anzeigen (nicht klickbar): weiche Umbrüche
        return (url or "").replace("/", "/\n").replace("-", "-\n")

    # ---------- PDF setup ----------
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Dateiname: Therapiegebiet_zVT_Shortlist.pdf
    filename = f"{safe_filename_component(therapy_area)}_zVT_Shortlist.pdf"

    # ---------- Header / Title ----------
    pdf.set_font("Helvetica", "B", 14)
    title = f"{therapy_area} - {indication}".strip(" -")
    pdf.multi_cell(0, 8, safe_text(title or "AMNOG Comparator Shortlist"))
    pdf.ln(1)

    # ---------- Summary ----------
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6, safe_text("Zusammenfassung der Eingaben"))

    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 5, safe_text(f"Therapiegebiet: {therapy_area}"))
    pdf.multi_cell(0, 5, safe_text(f"Anwendungsgebiet: {indication}"))
    pdf.multi_cell(0, 5, safe_text(f"Population (optional): {request_payload.get('population_text', '')}"))
    pdf.multi_cell(0, 5, safe_text(f"Setting: {request_payload.get('setting', '')}"))
    pdf.multi_cell(0, 5, safe_text(f"Rolle: {request_payload.get('role', '')}"))
    pdf.multi_cell(0, 5, safe_text(f"Therapielinie: {request_payload.get('line', '')}"))
    pdf.multi_cell(0, 5, safe_text(f"Comparator-Typ: {request_payload.get('comparator_type', '')}"))
    pdf.multi_cell(0, 5, safe_text(f"Comparator Text (optional): {request_payload.get('comparator_text', '')}"))
    pdf.multi_cell(0, 5, safe_text(f"Projektname: {request_payload.get('project_name', '')}"))
    pdf.multi_cell(0, 5, safe_text(f"Generiert: {response_payload.get('generated_at', '')}"))

    pdf.ln(2)

    # ---------- Disclaimer (italic) ----------
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        0,
        5,
        safe_text(
            "Die genannten Comparatoren sind lediglich eine Näherung und stellen keine Beratung dar "
            "und wurden auf Grundlage bestehender Beschlüsse ermittelt."
        ),
    )

    pdf.ln(3)

    # ---------- Shortlist ----------
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6, safe_text("Shortlist"))
    pdf.ln(1)

    for candidate in (response_payload.get("candidates") or []):
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(
            0,
            6,
            safe_text(f"#{candidate.get('rank', '')} {candidate.get('candidate_text', '')}"),
        )

        pdf.set_font("Helvetica", size=9)
        conf_line = "Confidence: {c} | Support: {s} | Fälle: {n}".format(
            c=candidate.get("confidence", ""),
            s=candidate.get("support_score", ""),
            n=candidate.get("support_cases", ""),
        )
        pdf.multi_cell(0, 5, safe_text(conf_line))

        # References:
        # 1) klickbarer kurzer Text: "- Produkt (Datum)" -> Link
        # 2) URL darunter klein als Anzeige (nicht klickbar), darf umbrechen
        for ref in (candidate.get("references") or [])[:3]:
            product = ref.get("product_name", "") or ""
            date = ref.get("decision_date", "") or ""
            url = (ref.get("url", "") or "").strip()

            clickable_label = safe_text(f"- {product} ({date})")

            pdf.set_font("Helvetica", size=9)
            if url.startswith("http://") or url.startswith("https://"):
                pdf.multi_cell(0, 5, clickable_label, link=url)
            else:
                pdf.multi_cell(0, 5, clickable_label)

            if url:
                pdf.set_font("Helvetica", size=7)
                pdf.multi_cell(0, 4, safe_text(soft_break_url_display(url)))

        pdf.ln(1)

    # ---------- Output ----------
    raw = pdf.output(dest="S")
    out = BytesIO(raw if isinstance(raw, (bytes, bytearray)) else str(raw).encode("latin-1", errors="replace"))

    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )