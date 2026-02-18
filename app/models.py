from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

from app import domain as d


class TherapyArea(str, Enum):
    AUGEN = "Augenerkrankungen"
    HAUT = "Haut"
    HERZ = "Herz-Kreislauf"
    INFEKTIONEN = "Infektionen"
    ATMUNG = "Atmung"
    BLUT = "Blut/Blutbildend"
    MUSKEL = "Muskel-Skelett"
    NERVENSYSTEM = "Nervensystem"
    UROGENITAL = "Urogenital"
    VERDAUUNG = "Verdauung"
    ONKOLOGIE = "Onkologie"
    PSYCHISCHE = "Psychische"
    STOFFWECHSEL = "Stoffwechsel"
    SONSTIGES = "Sonstiges"


class Setting(str, Enum):
    AMBULANT = "ambulant"
    STATIONAER = "stationär"
    BEIDES = "beides"
    UNKLAR = "unklar"


class TherapyRole(str, Enum):
    REPLACEMENT = "replacement"
    ADD_ON = "add-on"
    MONOTHERAPY = "monotherapy"
    UNKLAR = "unklar"

class TherapyLine(str, Enum):
    L1 = "1L"
    L2 = "2L"
    SPAETER = "später"
    SWITCH = "switch"
    UNKLAR = "unklar"


class ComparatorType(str, Enum):
    AKTIV = "aktiv"
    PLACEBO = "placebo"
    BSC = "BSC"
    PHYSICIAN_CHOICE = "physician's choice"
    UNKLAR = "unklar"


class ShortlistRequest(BaseModel):
    therapy_area: TherapyArea
    indication_text: str = Field(max_length=6000)
    population_text: Optional[str] = None
    setting: Setting
    role: TherapyRole
    line: Optional[TherapyLine] = None
    comparator_type: Optional[ComparatorType] = None
    comparator_text: Optional[str] = None
    project_name: Optional[str] = None

    def to_domain(self) -> d.ShortlistRequest:
        return d.ShortlistRequest(
            therapy_area=d.TherapyArea(self.therapy_area.value),
            indication_text=self.indication_text,
            population_text=self.population_text,
            setting=d.Setting(self.setting.value),
            role=d.TherapyRole(self.role.value),
            line=d.TherapyLine(self.line.value) if self.line else None,
            comparator_type=d.ComparatorType(self.comparator_type.value)
            if self.comparator_type
            else None,
            comparator_text=self.comparator_text,
            project_name=self.project_name,
        )


class ReferenceItem(BaseModel):
    decision_id: str
    product_name: str
    decision_date: str
    url: str
    snippet: str
    score: float

    @staticmethod
    def from_domain(x: d.ReferenceItem) -> "ReferenceItem":
        return ReferenceItem(
            decision_id=x.decision_id,
            product_name=x.product_name,
            decision_date=x.decision_date,
            url=x.url,
            snippet=x.snippet,
            score=x.score,
        )


class CandidateResult(BaseModel):
    rank: int
    candidate_text: str
    support_score: float
    confidence: str
    support_cases: int
    references: list[ReferenceItem]

    @staticmethod
    def from_domain(x: d.CandidateResult) -> "CandidateResult":
        return CandidateResult(
            rank=x.rank,
            candidate_text=x.candidate_text,
            support_score=x.support_score,
            confidence=x.confidence,
            support_cases=x.support_cases,
            references=[ReferenceItem.from_domain(r) for r in x.references],
        )


class ShortlistResponse(BaseModel):
    run_id: str
    candidates: list[CandidateResult]
    ambiguity: str
    generated_at: datetime
    notices: list[str] = []
    reliability: Literal["hoch", "mittel", "niedrig"] = "mittel"
    reliability_reasons: list[str] = []

    @staticmethod
    def from_domain(
        run_id: str, candidates: list[d.CandidateResult], ambiguity: str, generated_at: datetime,
        notices: list[str] | None = None,
    ) -> "ShortlistResponse":
        return ShortlistResponse(
            run_id=run_id,
            candidates=[CandidateResult.from_domain(c) for c in candidates],
            ambiguity=ambiguity,
            generated_at=generated_at,
            notices=notices or [],
        )


class LeadRequest(BaseModel):
    run_id: str
    email: EmailStr
    company: Optional[str] = None
    consent: bool


class LeadResponse(BaseModel):
    lead_id: int
    saved_at: datetime


class RunResponse(BaseModel):
    run_id: str
    request_payload: dict
    response_payload: dict
    created_at: datetime
