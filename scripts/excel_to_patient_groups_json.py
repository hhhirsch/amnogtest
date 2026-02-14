from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

SHEET = "2026-02-01_12-47-28_Export_Besc"

COL_DECISION_ID = "BE.ID_BE.Attribute:value"
COL_AKZ = "BE.ID_BE_AKZ.Attribute:value"
COL_PRODUCT = "BE.ZUL.NAME_HN.Attribute:value"
COL_URL = "BE.URL.Attribute:value"
COL_AWG = "BE.ZUL.AWG"

COL_PG_ID = "BE.PAT_GR_INFO_COLLECTION.ID_PAT_GR.Attribute:value"
COL_PG_TEXT = "BE.PAT_GR_INFO_COLLECTION.ID_PAT_GR.NAME_PAT_GR"
COL_AWG_BESCHLUSS = "BE.PAT_GR_INFO_COLLECTION.ID_PAT_GR.AWG_BESCHLUSS.Attribute:value"
COL_ZVT = "BE.PAT_GR_INFO_COLLECTION.ID_PAT_GR.ZVT_BEST.NAME_ZVT_BEST.Attribute:value"

HTML_TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")

# Therapiegebiet aus AWG/Patientengruppe ableiten (V1: regelbasiert)
THERAPY_RULES = [
    ("Onkologie", ["karzinom", "tumor", "metastas", "adenokarzin", "lymphom", "leukäm", "myelom", "neoplas"]),
    ("Nervensystem", ["multiple sklerose", "parkinson", "epilep", "alzheimer", "migräne", "schlaganfall", "neuropath"]),
    ("Herz-Kreislauf", ["herzinsuff", "koronar", "hyperton", "infarkt", "vorhofflimm", "kardiovask"]),
    ("Atmung", ["asthma", "copd", "lungen", "bronch", "pulmonal"]),
    ("Infektionen", ["infektion", "antibiot", "hiv", "hepatitis", "influenza", "covid", "sepsis"]),
    ("Stoffwechsel", ["diabetes", "adipos", "hyperchol", "lipid", "stoffwechsel"]),
    ("Verdauung", ["colitis", "morbus crohn", "ulzer", "hepat", "leber", "darm", "gastro"]),
    ("Urogenital", ["renal", "niere", "dialyse", "urolog", "prostata", "blase", "ovar", "endometr"]),
    ("Haut", ["psoriasis", "dermat", "atop", "urtikaria", "ekzem"]),
    ("Augenerkrankungen", ["makula", "retina", "glaukom", "okular", "uveitis"]),
    ("Muskel-Skelett", ["arthritis", "rheuma", "osteopor", "spondyl", "gicht"]),
    ("Blut/Blutbildend", ["hämophil", "anäm", "thrombozyt", "gerinnung"]),
    ("Psychische", ["depress", "schizophren", "bipolar", "adhs", "angststörung"]),
]

def clean_text(x: Any) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).replace("_x000D_", " ")
    s = HTML_TAG_RE.sub(" ", s)
    s = WS_RE.sub(" ", s).strip()
    return s

def parse_decision_date(akz: Any) -> str:
    # Aktenzeichen beginnt oft mit YYYY-MM-DD-...
    if akz is None or (isinstance(akz, float) and pd.isna(akz)):
        return ""
    s = str(akz)
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else ""

def infer_therapy_area(awg_text: str, pg_text: str, awg_beschluss: str) -> str:
    t = f"{awg_text}\n{pg_text}\n{awg_beschluss}".lower()
    for area, kws in THERAPY_RULES:
        if any(k in t for k in kws):
            return area
    return "Sonstiges"

def main(xlsx_path: str, out_json: str) -> None:
    df = pd.read_excel(xlsx_path, sheet_name=SHEET)

    needed = [COL_DECISION_ID, COL_AKZ, COL_PRODUCT, COL_URL, COL_AWG, COL_PG_ID, COL_PG_TEXT, COL_ZVT]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing columns: {missing}")

    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        zvt = row.get(COL_ZVT)
        if zvt is None or (isinstance(zvt, float) and pd.isna(zvt)):
            continue

        awg_text = clean_text(row.get(COL_AWG))
        pg_text = clean_text(row.get(COL_PG_TEXT))
        awg_beschluss = clean_text(row.get(COL_AWG_BESCHLUSS)) if COL_AWG_BESCHLUSS in df.columns else ""

        rec = {
            "patient_group_id": str(row.get(COL_PG_ID)),
            "decision_id": str(row.get(COL_DECISION_ID)),
            "product_name": clean_text(row.get(COL_PRODUCT)),
            "decision_date": parse_decision_date(row.get(COL_AKZ)),
            "url": clean_text(row.get(COL_URL)),
            "therapy_area": infer_therapy_area(awg_text, pg_text, awg_beschluss),
            "awg_text": awg_text,
            "patient_group_text": pg_text,
            "zvt_text": clean_text(zvt),
        }
        records.append(rec)

    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    # kleine Statistik
    counts = {}
    for r in records:
        counts[r["therapy_area"]] = counts.get(r["therapy_area"], 0) + 1
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"Wrote {len(records)} records -> {out_json}")
    print("Top therapy areas:", top)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/excel_to_patient_groups_json.py <input.xlsx> <output.json>")
        raise SystemExit(2)
    main(sys.argv[1], sys.argv[2])
