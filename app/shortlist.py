from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.models import CandidateResult, ReferenceItem, ShortlistRequest

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "patient_groups.json"
WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9]+")


@dataclass
class PatientGroupRecord:
    patient_group_id: str
    decision_id: str
    product_name: str
    decision_date: str
    url: str
    therapy_area: str
    awg_text: str
    patient_group_text: str
    zvt_text: str


def load_records() -> list[PatientGroupRecord]:
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [PatientGroupRecord(**row) for row in rows]


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(text)]


def overlap_score(query: str, document: str) -> float:
    q_tokens = set(tokenize(query))
    d_tokens = tokenize(document)
    if not q_tokens or not d_tokens:
        return 0.0
    hit_count = sum(1 for token in d_tokens if token in q_tokens)
    return hit_count / math.sqrt(len(d_tokens))


def recency_weight(decision_date: str) -> float:
    decision = datetime.strptime(decision_date, "%Y-%m-%d").date()
    years = (date.today() - decision).days / 365.25
    if years < 2:
        return 1.0
    if years <= 4:
        return 0.8
    return 0.6


def normalize_candidate(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    cleaned = cleaned.replace("best supportive care", "bsc")
    cleaned = cleaned.replace("beobachtendes abwarten", "watchful waiting")
    return cleaned


def confidence_label(score: float, support_cases: int) -> str:
    if score >= 2.5 and support_cases >= 3:
        return "hoch"
    if score >= 1.2 and support_cases >= 2:
        return "mittel"
    return "niedrig"


def ambiguity_label(sorted_scores: list[float]) -> str:
    if len(sorted_scores) < 2:
        return "niedrig"
    gap = sorted_scores[0] - sorted_scores[min(4, len(sorted_scores) - 1)]
    if gap < 0.4:
        return "hoch"
    if gap < 1.0:
        return "mittel"
    return "niedrig"


def build_query(payload: ShortlistRequest) -> str:
    parts = [payload.indication_text]
    if payload.population_text:
        parts.append(payload.population_text)
    if payload.comparator_text:
        parts.append(payload.comparator_text)
    return "\n".join(parts)


def shortlist(payload: ShortlistRequest) -> tuple[list[CandidateResult], str]:
    query = build_query(payload)
    records = [r for r in load_records() if r.therapy_area == payload.therapy_area.value]

    retrieved: list[tuple[PatientGroupRecord, float]] = []
    for record in records:
        document = f"{record.awg_text}\n{record.patient_group_text}"
        score = overlap_score(query, document)
        if score > 0:
            retrieved.append((record, score))

    retrieved.sort(key=lambda item: item[1], reverse=True)
    top_retrieved = retrieved[:30]

    aggregated: dict[str, dict] = defaultdict(lambda: {"text": "", "score": 0.0, "refs": []})

    for record, sim_score in top_retrieved:
        candidate_key = normalize_candidate(record.zvt_text)
        adj = 1.0
        zvt_lower = record.zvt_text.lower()
        if payload.role.value == "add-on" and "kombination" in zvt_lower:
            adj += 0.1
        if payload.setting.value == "stationär" and any(x in zvt_lower for x in ["infusion", "stationär"]):
            adj += 0.1
        if payload.setting.value == "unklar":
            adj -= 0.1
        if payload.role.value == "unklar":
            adj -= 0.1

        weighted = sim_score * recency_weight(record.decision_date) * adj
        entry = aggregated[candidate_key]
        entry["text"] = record.zvt_text
        entry["score"] += weighted
        entry["refs"].append(
            ReferenceItem(
                decision_id=record.decision_id,
                product_name=record.product_name,
                decision_date=record.decision_date,
                url=record.url,
                snippet=record.patient_group_text[:260],
                score=round(weighted, 4),
            )
        )

    ranked = sorted(aggregated.values(), key=lambda e: e["score"], reverse=True)[:5]
    candidates: list[CandidateResult] = []
    for idx, row in enumerate(ranked, start=1):
        refs = sorted(row["refs"], key=lambda r: r.score, reverse=True)[:5]
        support_cases = len({ref.decision_id for ref in refs})
        score = round(row["score"], 4)
        candidates.append(
            CandidateResult(
                rank=idx,
                candidate_text=row["text"],
                support_score=score,
                confidence=confidence_label(score, support_cases),
                support_cases=support_cases,
                references=refs,
            )
        )

    ambiguity = ambiguity_label([c.support_score for c in candidates])
    return candidates, ambiguity
