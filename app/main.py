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

@app.post("/api/export/pdf")
def export_pdf(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id not found")

    response_payload = run.get("response_payload") or {}
    request_payload = run.get("request_payload") or {}

    # ----------------------------
    # helpers
    # ----------------------------
    url_pattern = re.compile(r"https?://\S+")

    def _soft_break_url(url: str) -> str:
        # display-only line breaks for long URLs (readability)
        return url.replace("/", "/\n").replace("-", "-\n")

    def safe_text(txt: str) -> str:
        txt = unescape(txt or "")

        # normalize common typography -> latin-1 friendly
        txt = txt.replace("\xa0", " ")
        txt = txt.replace("–", "-").replace("—", "-")
        txt = txt.replace("•", "-").replace("\u2022", "-")
        txt = txt.replace("’", "'").replace("“", '"').replace("”", '"')

        txt = unicodedata.normalize("NFKC", txt)

        # only break URLs, not normal text
        txt = url_pattern.sub(lambda m: _soft_break_url(m.group(0)), txt)

        # hard guarantee core-font compatibility (Helvetica)
        return txt.encode("latin-1", errors="replace").decode("latin-1")

    def filename_safe(txt: str) -> str:
        # therapy_area -> safe filename chunk
        txt = unicodedata.normalize("NFKD", (txt or ""))
        txt = txt.encode("ascii", errors="ignore").decode("ascii")
        txt = txt.strip().replace(" ", "_")
        txt = re.sub(r"[^A-Za-z0-9_\-]+", "", txt)
        txt = re.sub(r"_+", "_", txt)
        return txt or "Therapiegebiet"

    def v(key: str) -> str:
        return safe_text(str(request_payload.get(key, "") or ""))

    # ----------------------------
    # titles / filename
    # ----------------------------
    therapy_area = (request_payload.get("therapy_area") or "").strip()
    indication_text = (request_payload.get("indication_text") or "").strip()

    # PDF title inside the document
    doc_title = " – ".join([t for t in [therapy_area, indication_text] if t]).strip()
    if not doc_title:
        doc_title = "AMNOG Comparator Shortlist"

    # Download filename
    dl_name = f"{filename_safe(therapy_area)}_zVT_Shortlist.pdf"

    # ----------------------------
    # PDF setup (fix margins / right cut-off)
    # ----------------------------
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # explicit margins to avoid right-side cut-off
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_top_margin(15)

    pdf.add_page()

    page_w = pdf.w - pdf.l_margin - pdf.r_margin  # usable width

    # ----------------------------
    # header (title)
    # ----------------------------
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(page_w, 8, safe_text(doc_title))
    pdf.ln(2)

    # ----------------------------
    # summary of user inputs
    # ----------------------------
    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(page_w, 6, safe_text("Zusammenfassung der Eingaben"))
    pdf.set_font("Helvetica", "", 10)

    summary_lines = [
        ("Therapiegebiet", v("therapy_area")),
        ("Anwendungsgebiet", v("indication_text")),
        ("Population (optional)", v("population_text")),
        ("Setting", v("setting")),
        ("Rolle", v("role")),
        ("Therapielinie", v("line")),
        ("Comparator-Typ", v("comparator_type")),
        ("Comparator Text (optional)", v("comparator_text")),
        ("Projektname", v("project_name")),
    ]

    for label, value in summary_lines:
        if value.strip():
            pdf.multi_cell(page_w, 5, safe_text(f"{label}: {value}"))

    generated_at = response_payload.get("generated_at", "")
    if generated_at:
        pdf.ln(1)
        pdf.multi_cell(page_w, 5, safe_text(f"Generiert: {generated_at}"))

    pdf.ln(3)

    # disclaimer (italic, as requested)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        page_w,
        5,
        safe_text(
            "Disclaimer: Die genannten Comparatoren sind lediglich eine Näherung und stellen keine Beratung dar "
            "und wurden auf Grundlage bestehender Beschlüsse ermittelt."
        ),
    )
    pdf.ln(4)

    # ----------------------------
    # results
    # ----------------------------
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(page_w, 6, safe_text("Shortlist"))
    pdf.ln(1)

    candidates = response_payload.get("candidates", []) or []
    for candidate in candidates:
        rank = candidate.get("rank", "")
        cand_txt = candidate.get("candidate_text", "")
        conf = candidate.get("confidence", "")
        support = candidate.get("support_score", "")
        cases = candidate.get("support_cases", "")

        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(page_w, 6, safe_text(f"#{rank} {cand_txt}".strip()))

        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(
            page_w,
            5,
            safe_text(f"Confidence: {conf} | Support: {support} | Fälle: {cases}"),
        )

        # References (display-only, NOT clickable)
        refs = (candidate.get("references") or [])[:3]
        for ref in refs:
            prod = ref.get("product_name", "") or ""
            date = ref.get("decision_date", "") or ""
            url = ref.get("url", "") or ""

            # line 1: "Vabysmo (2022-10-15) -> verlinkt auf ..."
            pdf.set_font("Helvetica", "", 9)
            if url:
                pdf.multi_cell(page_w, 5, safe_text(f"- {prod} ({date}) -> verlinkt auf"))
            else:
                pdf.multi_cell(page_w, 5, safe_text(f"- {prod} ({date})"))

            # line 2: URL small below (wrapped)
            if url:
                pdf.set_font("Helvetica", "", 8)
                pdf.multi_cell(page_w, 4, safe_text(f"  {url}"))

        pdf.ln(2)

    # output
    raw = pdf.output(dest="S")
    if isinstance(raw, (bytes, bytearray)):
        out = BytesIO(raw)
    else:
        out = BytesIO(str(raw).encode("latin-1", errors="replace"))

    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{dl_name}"'},
    )
