from __future__ import annotations

import re
import os
import requests
import unicodedata
import logging
from datetime import datetime
from email.message import EmailMessage
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
logger = logging.getLogger(__name__)

LEAD_NOTIFY_TO = os.getenv("LEAD_NOTIFY_TO", "hirsch.hans92@gmail.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM = os.getenv("RESEND_FROM", "onboarding@resend.dev")  # ok for testing

PDF_SCORING_EXPLANATION_LINES = [
    "Support ist die Evidenzstärke aus ähnlichen, aktuellen und passenden G-BA-Beschlüssen.",
    "Höherer Support bedeutet: mehr und/oder passendere Evidenz in vergleichbaren Fällen.",
    "Fälle ist die Zahl unterschiedlicher Entscheidungen (decision_id), die einen Kandidaten stützen.",
    "Confidence (hoch/mittel/niedrig) leitet sich aus Support und Anzahl der Fälle ab.",
    "Ambiguity beschreibt, wie nah die Scores der Top-Kandidaten beieinander liegen.",
    "Hohe Ambiguity bedeutet: mehrere Optionen sind ähnlich plausibel.",
    "Support ist relativ innerhalb dieser Anfrage und keine klinische Empfehlung.",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://amnogtest-546n.vercel.app", "http://localhost:3000"],
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
    correlation_id = str(uuid4())

    if not RESEND_API_KEY:
        logger.error(
            "Lead notification aborted (missing RESEND_API_KEY) corr_id=%s run_id=%s lead_id=%s",
            correlation_id,
            payload.run_id,
            lead_id,
        )
        raise HTTPException(status_code=500, detail="Lead saved, but email failed: RESEND_API_KEY is not configured")

    try:
        send_lead_notification(
            correlation_id=correlation_id,
            run_id=payload.run_id,
            email=str(payload.email),
            company=payload.company,
            lead_id=lead_id,
            saved_at=saved_at,
        )
    except Exception as e:
        logger.exception(
            "Failed to send lead notification corr_id=%s run_id=%s lead_id=%s",
            correlation_id,
            payload.run_id,
            lead_id,
        )
        raise HTTPException(status_code=500, detail=f"Lead saved, but email failed: {e}")

    return LeadResponse(lead_id=lead_id, saved_at=saved_at)


def send_lead_notification(
    *,
    correlation_id: str,
    run_id: str,
    email: str,
    company: str | None,
    lead_id: int,
    saved_at: datetime,
) -> None:
    if not RESEND_FROM or not RESEND_FROM.strip():
        raise ValueError("RESEND_FROM is not configured")
    if not LEAD_NOTIFY_TO or not LEAD_NOTIFY_TO.strip():
        raise ValueError("LEAD_NOTIFY_TO is not configured")

    logger.info(
        "Lead notification config corr_id=%s run_id=%s lead_id=%s has_resend_api_key=%s resend_from=%s lead_notify_to=%s",
        correlation_id,
        run_id,
        lead_id,
        bool(RESEND_API_KEY),
        RESEND_FROM,
        LEAD_NOTIFY_TO,
    )

    subject = f"[zVT Navigator] New lead for run {run_id}"
    text = "\n".join(
        [
            "Ein neuer Lead wurde gespeichert.",
            f"lead_id: {lead_id}",
            f"run_id: {run_id}",
            f"email: {email}",
            f"company: {company or '-'}",
            f"saved_at: {saved_at.isoformat()}",
        ]
    )

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "from": RESEND_FROM,
                "to": [LEAD_NOTIFY_TO],
                "subject": subject,
                "text": text,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Resend request failed: {exc}") from exc

    logger.info(
        "Resend response corr_id=%s run_id=%s lead_id=%s status_code=%s body=%s",
        correlation_id,
        run_id,
        lead_id,
        resp.status_code,
        resp.text[:500],
    )

    if resp.status_code >= 300:
        raise RuntimeError(f"Resend send failed: {resp.status_code} {resp.text}")

    logger.info("Lead notification sent via Resend corr_id=%s lead_id=%s", correlation_id, lead_id)


@app.get("/api/debug/email-config")
def debug_email_config():
    return {
        "has_resend_api_key": bool(RESEND_API_KEY),
        "lead_notify_to": LEAD_NOTIFY_TO,
        "resend_from": RESEND_FROM,
    }

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
        # keep core-font safe (Helvetica)
        return txt.encode("latin-1", errors="replace").decode("latin-1")

    def safe_filename_component(s: str) -> str:
        s = (s or "").strip()
        s = (
            s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
             .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
             .replace("ß", "ss")
        )
        s = safe_text(s)
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"[^A-Za-z0-9._-]+", "", s)
        s = re.sub(r"_+", "_", s).strip("_")
        return s or "Export"

    def url_display(url: str, max_len: int = 72) -> str:
        """
        Display-only (NOT clickable): remove scheme and insert line breaks only at "/"
        so we don't destroy domains like "g-ba.de".
        """
        u = (url or "").strip()
        if not u:
            return ""

        u = re.sub(r"^https?://", "", u)  # avoid the ugly "https:/ /" wrap
        if len(u) <= max_len:
            return u

        out, line = [], ""
        for ch in u:
            line += ch
            if ch == "/" and len(line) >= max_len:
                out.append(line)
                line = ""
        if line:
            # hard wrap remainder if still too long without slashes
            while len(line) > max_len:
                out.append(line[:max_len])
                line = line[max_len:]
            if line:
                out.append(line)
        return "\n".join(out)

    def mc(h: float, text: str, *, font=("Helvetica", "", 10)):
        """multi_cell with x-reset to avoid 'Not enough horizontal space'"""
        pdf.set_x(pdf.l_margin)
        pdf.set_font(*font)
        pdf.multi_cell(0, h, safe_text(text))

    # ---------- PDF setup ----------
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    filename = f"{safe_filename_component(therapy_area)}_zVT_Shortlist.pdf"

    # ---------- Title ----------
    title = f"{therapy_area} - {indication}".strip(" -")
    mc(8, title or "AMNOG Comparator Shortlist", font=("Helvetica", "B", 14))
    pdf.ln(1)

    # ---------- Summary ----------
    mc(6, "Zusammenfassung der Eingaben", font=("Helvetica", "B", 11))

    summary_lines = [
        ("Therapiegebiet", therapy_area),
        ("Anwendungsgebiet", indication),
        ("Population (optional)", request_payload.get("population_text", "")),
        ("Setting", request_payload.get("setting", "")),
        ("Rolle", request_payload.get("role", "")),
        ("Therapielinie", request_payload.get("line", "")),
        ("Comparator-Typ", request_payload.get("comparator_type", "")),
        ("Comparator Text (optional)", request_payload.get("comparator_text", "")),
        ("Projektname", request_payload.get("project_name", "")),
        ("Generiert", response_payload.get("generated_at", "")),
    ]
    for k, v in summary_lines:
        mc(5, f"{k}: {v or ''}", font=("Helvetica", "", 10))

    pdf.ln(2)

    # ---------- Disclaimer (italic) ----------
    mc(
        5,
        "Die genannten Comparatoren sind lediglich eine Näherung und stellen keine Beratung dar "
        "und wurden auf Grundlage bestehender Beschlüsse ermittelt.",
        font=("Helvetica", "I", 9),
    )
    pdf.ln(3)

    # ---------- Result context ----------
    mc(6, "Einordnung der Ergebnisse", font=("Helvetica", "B", 11))
    for line in PDF_SCORING_EXPLANATION_LINES:
        mc(5, f"- {line}", font=("Helvetica", "", 9))
    pdf.ln(2)

    # ---------- Shortlist ----------
    mc(6, "Shortlist", font=("Helvetica", "B", 11))
    pdf.ln(1)

    for candidate in (response_payload.get("candidates") or []):
        # Candidate header
        mc(
            6,
            f"#{candidate.get('rank', '')} {candidate.get('candidate_text', '')}",
            font=("Helvetica", "B", 10),
        )

        # Confidence line (avoid cut-off: multi_cell + x reset)
        conf_line = "Confidence: {c} | Support: {s} | Fälle: {n}".format(
            c=candidate.get("confidence", ""),
            s=candidate.get("support_score", ""),
            n=candidate.get("support_cases", ""),
        )
        mc(5, conf_line, font=("Helvetica", "", 9))

        # References:
        # 1) clickable label line via cell() (reliable)
        # 2) URL below as small, non-clickable display (wrapped only at "/")
        refs = (candidate.get("references") or [])[:3]
        for ref in refs:
            product = ref.get("product_name", "") or ""
            date = ref.get("decision_date", "") or ""
            url = (ref.get("url", "") or "").strip()

            label = safe_text(f"- {product} ({date})")

            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "", 9)

            if url.startswith("http://") or url.startswith("https://"):
                pdf.set_text_color(0, 0, 255)  # blue for "looks like link"
                pdf.cell(0, 5, label, ln=1, link=url)
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.cell(0, 5, label, ln=1)

            if url:
                pdf.set_x(pdf.l_margin)
                pdf.set_font("Helvetica", "", 7)
                pdf.multi_cell(0, 4, safe_text(url_display(url)))
            pdf.ln(0.5)

        pdf.ln(1)

    # ---------- Output ----------
    raw = pdf.output(dest="S")
    out = BytesIO(raw if isinstance(raw, (bytes, bytearray)) else str(raw).encode("latin-1", errors="replace"))

    return StreamingResponse(
        out,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
