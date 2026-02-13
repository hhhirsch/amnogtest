from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


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
    indication_text: str = Field(min_length=50, max_length=6000)
    population_text: Optional[str] = None
    setting: Setting
    role: TherapyRole
    line: Optional[TherapyLine] = None
    comparator_type: Optional[ComparatorType] = None
    comparator_text: Optional[str] = None
    project_name: Optional[str] = None


class ReferenceItem(BaseModel):
    decision_id: str
    product_name: str
    decision_date: str
    url: str
    snippet: str
    score: float


class CandidateResult(BaseModel):
    rank: int
    candidate_text: str
    support_score: float
    confidence: str
    support_cases: int
    references: list[ReferenceItem]


class ShortlistResponse(BaseModel):
    run_id: str
    candidates: list[CandidateResult]
    ambiguity: str
    generated_at: datetime


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
