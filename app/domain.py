from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


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


@dataclass(frozen=True)
class ShortlistRequest:
    therapy_area: TherapyArea
    indication_text: str
    population_text: Optional[str] = None
    setting: Setting = Setting.UNKLAR
    role: TherapyRole = TherapyRole.UNKLAR
    line: Optional[TherapyLine] = None
    comparator_type: Optional[ComparatorType] = None
    comparator_text: Optional[str] = None
    project_name: Optional[str] = None


@dataclass(frozen=True)
class ReferenceItem:
    decision_id: str
    product_name: str
    decision_date: str
    url: str
    snippet: str
    score: float


@dataclass(frozen=True)
class CandidateResult:
    rank: int
    candidate_text: str
    support_score: float
    confidence: str
    support_cases: int
    references: list[ReferenceItem]
    support_cases_clean: int = 0
    support_cases_special: int = 0

