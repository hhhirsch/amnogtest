# From repo root:
# python scripts/excel_to_patient_groups_json.py "/mnt/data/GBA Beschlüsse_2026.xlsx" "app/data/patient_groups_v2.json"

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
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

# Optional columns — converter falls back gracefully when absent
COL_REG_NB = "BE.REG_NB.Attribute:value"
COL_UES_ZVT_ZN = "BE.PAT_GR_INFO_COLLECTION.ID_PAT_GR.UES_ZVT_ZN.Attribute:value"
COL_ORPHAN = "BE.ZUL.SOND_ZUL_ORPHAN.Attribute:value"
COL_UES_BE = "BE.UES_BE.Attribute:value"
COL_BESOND = "BE.ZUL.SOND_ZUL_BESOND.Attribute:value"
COL_AUSN = "BE.ZUL.SOND_ZUL_AUSN.Attribute:value"
COL_ATMP = "BE.ZUL.SOND_ZUL_ATMP.Attribute:value"
COL_QS_ATMP = "BE.ZUL.QS_ATMP.Attribute:value"

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

def parse_bool_flag(x: Any) -> int:
    """Return 1 if x represents a truthy flag value, else 0."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return 0
    return 1 if str(x).strip().lower() in {"1", "true", "ja", "yes"} else 0

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

    has_ues_col = COL_UES_ZVT_ZN in df.columns
    has_reg_nb_col = COL_REG_NB in df.columns
    has_orphan_col = COL_ORPHAN in df.columns
    has_ues_be_col = COL_UES_BE in df.columns
    has_besond_col = COL_BESOND in df.columns
    has_ausn_col = COL_AUSN in df.columns
    has_atmp_col = COL_ATMP in df.columns
    has_qs_atmp_col = COL_QS_ATMP in df.columns

    records: List[Dict[str, Any]] = []
    stats: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"total_rows": 0, "has_zvt_rows": 0, "orphan_rows": 0, "orphan_missing_zvt_rows": 0, "special_rows": 0, "special_has_zvt_rows": 0}
    )

    for _, row in df.iterrows():
        awg_text = clean_text(row.get(COL_AWG))
        pg_text = clean_text(row.get(COL_PG_TEXT))
        awg_beschluss = clean_text(row.get(COL_AWG_BESCHLUSS)) if COL_AWG_BESCHLUSS in df.columns else ""
        therapy_area = infer_therapy_area(awg_text, pg_text, awg_beschluss)

        zvt_text = clean_text(row.get(COL_ZVT))

        if has_ues_col:
            ues = clean_text(row.get(COL_UES_ZVT_ZN))
            has_zvt = (ues == "Zusatznutzen und zweckmäßige Vergleichstherapie") and bool(zvt_text)
        else:
            has_zvt = bool(zvt_text)

        procedure_type = clean_text(row.get(COL_REG_NB)) if has_reg_nb_col else ""

        raw_orphan = row.get(COL_ORPHAN) if has_orphan_col else None
        try:
            is_orphan = 0 if (
                raw_orphan is None
                or (isinstance(raw_orphan, float) and pd.isna(raw_orphan))
            ) else (1 if str(raw_orphan).strip() == "1" else 0)
        except Exception:
            is_orphan = 0

        is_besond = parse_bool_flag(row.get(COL_BESOND)) if has_besond_col else 0
        is_ausn   = parse_bool_flag(row.get(COL_AUSN))   if has_ausn_col   else 0
        is_atmp   = parse_bool_flag(row.get(COL_ATMP))   if has_atmp_col   else 0
        qs_atmp   = clean_text(row.get(COL_QS_ATMP))     if has_qs_atmp_col else ""
        ues_be    = clean_text(row.get(COL_UES_BE))       if has_ues_be_col  else ""

        is_special = int(bool(is_orphan or is_besond or is_ausn or is_atmp))

        # Stats are collected for ALL rows (before the strict filter below)
        stats[therapy_area]["total_rows"] += 1
        stats[therapy_area]["has_zvt_rows"] += int(has_zvt)
        stats[therapy_area]["orphan_rows"] += int(is_orphan)
        stats[therapy_area]["orphan_missing_zvt_rows"] += int(is_orphan and not has_zvt)
        stats[therapy_area]["special_rows"] += is_special
        stats[therapy_area]["special_has_zvt_rows"] += int(is_special and has_zvt)

        if not has_zvt:
            continue

        rec = {
            "patient_group_id": str(row.get(COL_PG_ID)),
            "decision_id": str(row.get(COL_DECISION_ID)),
            "product_name": clean_text(row.get(COL_PRODUCT)),
            "decision_date": parse_decision_date(row.get(COL_AKZ)),
            "url": clean_text(row.get(COL_URL)),
            "therapy_area": therapy_area,
            "awg_text": awg_text,
            "patient_group_text": pg_text,
            "zvt_text": zvt_text,
            "procedure_type": procedure_type,
            "has_zvt": has_zvt,
            "ues_be": ues_be,
            "is_orphan": is_orphan,
            "is_besond": is_besond,
            "is_ausn": is_ausn,
            "is_atmp": is_atmp,
            "qs_atmp": qs_atmp,
        }
        records.append(rec)

    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    stats_json = str(Path(out_json).parent / "patient_groups_stats.json")
    Path(stats_json).write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    # Statistik
    counts: Dict[str, int] = {}
    for r in records:
        counts[r["therapy_area"]] = counts.get(r["therapy_area"], 0) + 1
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"Wrote {len(records)} records -> {out_json}")
    print("Top therapy areas:", top)
    top_stats = sorted(stats.items(), key=lambda x: x[1]["total_rows"], reverse=True)[:5]
    print("Stats summary (top areas by total_rows):", [(a, dict(s)) for a, s in top_stats])
    print(f"Stats written -> {stats_json}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/excel_to_patient_groups_json.py <input.xlsx> <output.json>")
        raise SystemExit(2)
    main(sys.argv[1], sys.argv[2])
