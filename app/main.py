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

    response_payload = run["response_payload"] or {}
    request_payload = run["request_payload"] or {}

    therapy_area = (request_payload.get("therapy_area") or "").strip()
    indication = (request_payload.get("indication_text") or "").strip()

    # ---------- helpers ----------
    def safe_text(txt: str) -> str:
        txt = unescape(txt or "")
        # normalize typography -> latin-1 friendly for core fonts
        txt = txt.replace("\xa0", " ")
        txt = txt.replace("–", "-").replace("—", "-")
        txt = txt.replace("•", "-").replace("\u2022", "-")
        txt = txt.replace("’", "'").replace("“", '"').replace("”", '"')
        txt = unicodedata.normalize("NFKC", txt)
        # ensure Helvetica/core fonts won't crash
        return txt.encode("latin-1", errors="replace").decode("latin-1")

    def sanitize_filename(name: str) -> str:
        # keep it simple + filesystem-safe
        n = (name or "").strip()
        n = (
            n.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
             .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
             .replace("ß", "ss")
        )
        # collapse weird chars
        n = re.sub(r"[^A-Za-z0-9._-]+", "_", n)
        n = re.sub(r"_+", "_", n).strip("_")
        return n or "Export"

    def wrap_url_for_display(url: str, max_len: int = 78) -> str:
        """
        Only for the NON-clickable display line.
        Break long URLs in a readable way without affecting the actual hyperlink.
        """
        url = (url or "").strip()
        if len(url) <= max_len:
            return url

        parts = []
        buf = ""
        for ch in url:
            buf += ch
            # prefer breaking after / or -
            if ch in ["/", "-"] and len(buf) >= max_len:
                parts.append(buf)
                buf = ""
        if buf:
            # hard wrap remaining if still too long
            while len(buf) > max_len:
                parts.append(buf[:max_len])
                buf = buf[max_len:]
            if buf:
                parts.append(buf)

        return "\n".join(parts)

    def label_setting(val: str) -> str:
        return (val or "").strip()

    # ---------- PDF ----------
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=15)

    # consistent margins => avoids "right side cut off"
    pdf.set_margins(left=15, top=15, right=15)
    pdf.add_page()

    effective_w = pdf.w - pdf.l_margin - pdf.r_margin

    # ---- Title (Therapiegebiet – Anwendungsgebiet) ----
    title_left = therapy_area or "AMNOG"
    title_right = indication or ""
    full_title = f"{title_left} - {title_right}".strip(" -")

    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(effective_w, 8, safe_text(full_title))
    pdf.ln(1)

    # ---- Summary of inputs ----
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(effective_w, 6, safe_text("Zusammenfassung der Eingaben"))

    pdf.set_font("Helvetica", size=10)
    summary_lines = [
        ("Therapiegebiet", therapy_area),
        ("Anwendungsgebiet", indication),
        ("Population (optional)", request_payload.get("population_text", "")),
        ("Setting", label_setting(request_payload.get("setting", ""))),
        ("Rolle", label_setting(request_payload.get("role", ""))),
        ("Therapielinie", label_setting(request_payload.get("line", ""))),
        ("Comparator-Typ", label_setting(request_payload.get("comparator_type", ""))),
        ("Comparator Text (optional)", request_payload.get("comparator_text", "")),
        ("Projektname", request_payload.get("project_name", "")),
        ("Generiert", response_payload.get("generated_at", "")),
    ]
    for k, v in summary_lines:
        pdf.multi_cell(effective_w, 5.5, safe_text(f"{k}: {v or ''}"))
    pdf.ln(2)

    # ---- Disclaimer italic ----
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(
        effective_w,
        5,
        safe_text(
            "Die genannten Comparatoren sind lediglich eine Näherung und stellen keine Beratung dar "
            "und wurden auf Grundlage bestehender Beschlüsse ermittelt."
        ),
    )
    pdf.ln(3)

    # ---- Shortlist ----
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(effective_w, 6.5, safe_text("Shortlist"))
    pdf.ln(1)

    for candidate in response_payload.get("candidates", []) or []:
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(
            effective_w,
            5.5,
            safe_text(f"#{candidate.get('rank', '')} {candidate.get('candidate_text', '')}"),
        )

        pdf.set_font("Helvetica", size=9)
        pdf.multi_cell(
            effective_w,
            5,
            safe_text(
                "Confidence: {c} | Support: {s} | Fälle: {n}".format(
                    c=candidate.get("confidence", ""),
                    s=candidate.get("support_score", ""),
                    n=candidate.get("support_cases", ""),
                )
            ),
        )

        # References: clickable title line + non-clickable small URL below
        refs = (candidate.get("references") or [])[:3]
        for ref in refs:
            product = ref.get("product_name", "") or ""
            date = ref.get("decision_date", "") or ""
            url = (ref.get("url", "") or "").strip()

            display_title = f"- {product} ({date})"
            display_url = wrap_url_for_display(url)

            # clickable line
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(0, 0, 255)  # blue (optional, but helps user spot links)
            pdf.cell(effective_w, 5, safe_text(display_title), ln=1, link=url)

            # non-clickable URL shown below (small, gray-ish via default black but smaller)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", size=8)
            if url:
                pdf.multi_cell(effective_w, 4.5, safe_text(display_url))
            else:
                pdf.multi_cell(effective_w, 4.5, safe_text("(keine URL)"))

            pdf.ln(0.5)

        pdf.ln(1)

    # ---------- output ----------
    raw = pdf.output(dest="S")
    if isinstance(raw, (bytes, bytearray)):
        out = BytesIO(raw)
    else:
        out = BytesIO(str(raw).encode("latin-1", errors="replace"))

    filename = f"{sanitize_filename(therapy_area)}_zVT_Shortlist.pdf"
    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )