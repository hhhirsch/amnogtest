from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Optional

from app.domain import CandidateResult, ComparatorType, ReferenceItem, ShortlistRequest, TherapyLine

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent  # .../app
DATA_DIR = BASE_DIR / "data"
PATIENT_GROUPS_PATH = Path(os.getenv("PATIENT_GROUPS_PATH", str(DATA_DIR / "patient_groups_v2.json")))
STATS_PATH = Path(os.getenv("PATIENT_GROUPS_STATS_PATH", str(DATA_DIR / "patient_groups_stats.json")))

ENABLE_ZVT_NOTICES = os.getenv("ENABLE_ZVT_NOTICES", "1") == "1"

# Tokenization / preprocessing
WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9]+")
_BSC_RE = re.compile(r"\bb\s*\.?\s*s\s*\.?\s*c\b", flags=re.IGNORECASE)
_WS_RE = re.compile(r"\s+")
_PAREN_ABBR_RE = re.compile(r"\((?:\s*[A-Za-z]{2,6}\s*)\)")  # used in normalize_candidate only

# Detect combination therapies in zVT text (avoid HER2+ false positives by requiring spaces around "+")
_COMBO_PLUS_RE = re.compile(r"\s\+\s")
_PLUS_WORD_RE = re.compile(r"\bplus\b", flags=re.IGNORECASE)

# ---- Scoring knobs (tweakable via env) ----
# overlap  -> legacy overlap (but with improved tokenization)
# tfidf    -> smoothed TF-IDF sum
# bm25     -> BM25 (recommended)
SCORING_MODE = (os.getenv("SCORING_MODE", "bm25") or "bm25").strip().lower()
if SCORING_MODE not in {"overlap", "tfidf", "bm25"}:
    SCORING_MODE = "bm25"

# If a therapy area has fewer than MIN_PRIMARY_RECORDS, we consider a soft fallback to other areas.
MIN_PRIMARY_RECORDS = int(os.getenv("MIN_PRIMARY_RECORDS", "10"))
OTHER_AREA_PENALTY = float(os.getenv("OTHER_AREA_PENALTY", "0.7"))
RETRIEVE_LIMIT = int(os.getenv("RETRIEVE_LIMIT", "50"))

# Comparator-splitting guards (Risk A + B)
MAX_ZVT_ITEMS_PER_RECORD = 12   # explosion guard: revert to full text if split yields more
MAX_CANDIDATE_KEYS = 60         # hard cap on distinct candidate keys per request
SPLIT_ONLY_TOP_RETRIEVED = 20   # only split the strongest-scoring records

# Field weights for lexical scoring (AWG is primary; population secondary; zVT as boost)
W_AWG = float(os.getenv("W_AWG", "1.0"))
W_POP = float(os.getenv("W_POP", "0.6"))
W_ZVT = float(os.getenv("W_ZVT", "0.3"))

# BM25 parameters
BM25_K1 = float(os.getenv("BM25_K1", "1.2"))
BM25_B = float(os.getenv("BM25_B", "0.75"))

# Stopwords: keep this deliberately small + obvious; TF-IDF/BM25 handle frequent domain terms.
STOPWORDS: set[str] = {
    "mit",
    "und",
    "die",
    "der",
    "des",
    "den",
    "dem",
    "das",
    "in",
    "im",
    "an",
    "auf",
    "bei",
    "von",
    "zu",
    "zur",
    "zum",
    "oder",
    "sowie",
    "als",
    "nach",
    "für",
    "eine",
    "einer",
    "einem",
    "einen",
    "ein",
    "ist",
    "sind",
    "wird",
    "werden",
    "nicht",
    "kein",
    "keine",
    "ohne",
    "über",
    "unter",
    "dass",
    "da",
    "nur",
    "auch",
    "wie",
    "mehr",
    "weniger",
}

# Keep a few short but semantically relevant tokens (otherwise we drop <=2 chars)
KEEP_SHORT_TOKENS = {"1l", "2l", "3l", "4l", "5l", "l1", "l2", "l3", "l4", "l5"}

# Red flag keys for domain-level mismatch detection
RED_FLAG_KEYS = frozenset({
    "SETTING_MISMATCH_PLATIN", "BSC_CONTRADICTION", "LINE_MISMATCH_1L", "PASSIVE_TOP1_MISMATCH",
})

# Single source of truth for passive-care and therapy-eligible markers
PASSIVE_CARE_MARKERS = [
    "bsc", "best supportive care", "supportive care", "symptomatische therapie",
    "watchful waiting", "beobachtendes abwarten", "abwarten", "abwartend", "abwartendes vorgehen",
    "nach arztlicher maßgabe", "arztlicher maßgabe", "patientenindividuelle therapie", "pit",
]

# Markers indicating the user *explicitly* requested passive/supportive care
PASSIVE_REQUEST_MARKERS = [
    "bsc", "best supportive care", "watchful waiting", "beobachtendes abwarten", "abwarten",
    "nach arztlicher maßgabe", "patientenindividuelle therapie", "pit",
]

# Markers implying active treatment intent (cross-indication)
ACTIVE_INTENT_MARKERS = [
    "rezidiv", "rezidivier", "refrakt", "progress", "metastas", "vorbehandelt",
    "nach versagen", "salvage", "second line", "2l", "3l", "4l",
]

THERAPY_OK_MARKERS = [
    "weitere systemtherapie", "weitere systemische therapie",
    "systemtherapie geeignet", "systemtherapiefähig", "systemtherapiefaehig",
    "geeignet für weitere systemische therapie", "geeignet fuer weitere systemische therapie",
    "standardtherapie kommt in frage", "standardtherapie möglich", "standardtherapie moeglich",
    "therapiefähig", "therapiefaehig",
    "geeignet für therapie",
]

# Prefixes that mark modifier-only zVT fragments (e.g. "ohne Prednison")
_FRAG_PREFIXES = ("ohne ", "mit ", "unter ", "für ", "nur ", "inkl ", "inkl. ", "zzgl ", "zzgl. ")


def _query_requests_passive(query_lower: str, comparator_type_value: str | None = None) -> bool:
    """Return True when the user explicitly requested passive/supportive care as comparator."""
    # Explicit comparator_type BSC
    if comparator_type_value and comparator_type_value.lower() == "bsc":
        return True

    q_norm = _normalize_for_tokens(query_lower)
    return any(x in q_norm for x in PASSIVE_REQUEST_MARKERS)


def _query_implies_active_intent(query_lower: str, line: Optional[TherapyLine] = None) -> bool:
    """Return True when the query/context implies active treatment intent.

    TherapyLine.SPAETER ("später") is intentionally excluded from the line-based
    check so that Boost 4 (BSC appropriate in late-line) operates correctly.
    """
    if line and line.value == "2L":
        return True
    return (
        any(m in query_lower for m in ACTIVE_INTENT_MARKERS)
        or any(m in query_lower for m in THERAPY_OK_MARKERS)
    )


def is_passive_candidate_text(candidate_text: str) -> bool:
    """Return True if the candidate text describes a passive care option.

    Normalizes via normalize_candidate() to handle umlaut variants and abbreviations.
    """
    norm = normalize_candidate(candidate_text)
    return any(m in norm for m in PASSIVE_CARE_MARKERS)


def _normalize_for_tokens(text: str) -> str:
    """Lightweight normalization to improve lexical matching.

    Keep it intentionally conservative (no aggressive stemming) to avoid false positives.
    """
    cleaned = (text or "").strip().lower()
    if not cleaned:
        return ""

    cleaned = _WS_RE.sub(" ", cleaned)

    # Normalize common comparator phrases/abbreviations so query and corpus meet in the middle.
    cleaned = cleaned.replace("best supportive care", "bsc")
    cleaned = cleaned.replace("best supportive-care", "bsc")
    cleaned = _BSC_RE.sub("bsc", cleaned)

    cleaned = cleaned.replace("patientenindividuelle therapie", "pit")
    cleaned = cleaned.replace("beobachtendes abwarten", "watchful waiting")

    cleaned = cleaned.replace("nach ärztlicher maßgabe", "nach arztlicher maßgabe")
    cleaned = cleaned.replace("nach maßgabe des arztes", "nach arztlicher maßgabe")
    cleaned = cleaned.replace("nach maßgabe des arzt", "nach arztlicher maßgabe")
    cleaned = cleaned.replace("ärztlicher maßgabe", "arztlicher maßgabe")

    return cleaned


def tokenize(text: str) -> list[str]:
    raw = [t.lower() for t in WORD_RE.findall(_normalize_for_tokens(text))]
    tokens: list[str] = []
    for tok in raw:
        if tok in STOPWORDS:
            continue
        if len(tok) <= 2 and tok not in KEEP_SHORT_TOKENS:
            continue
        tokens.append(tok)
    return tokens


@dataclass(frozen=True)
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
    procedure_type: str = ""
    has_zvt: bool = True
    ues_be: str = ""
    is_orphan: int = 0
    is_besond: int = 0
    is_ausn: int = 0
    is_atmp: int = 0
    qs_atmp: str = ""

    def __post_init__(self) -> None:
        # Cache tokenized fields once at load time to avoid re-tokenizing on every request.
        # Note: These are stored as private attributes (not dataclass fields) to keep hashing stable.
        awg_tokens = tuple(tokenize(self.awg_text or ""))
        pop_tokens = tuple(tokenize(self.patient_group_text or ""))
        zvt_tokens = tuple(tokenize(self.zvt_text or ""))

        terms = set(awg_tokens)
        terms.update(pop_tokens)
        terms.update(zvt_tokens)

        object.__setattr__(self, "_awg_tokens", awg_tokens)
        object.__setattr__(self, "_pop_tokens", pop_tokens)
        object.__setattr__(self, "_zvt_tokens", zvt_tokens)
        object.__setattr__(self, "_terms", frozenset(terms))


@dataclass(frozen=True)
class BM25Stats:
    idf: dict[str, float]
    avg_len_awg: float
    avg_len_pop: float
    avg_len_zvt: float


@lru_cache(maxsize=1)
def load_records() -> tuple[PatientGroupRecord, ...]:
    if not PATIENT_GROUPS_PATH.exists():
        raise RuntimeError(f"Patient groups data file not found: {PATIENT_GROUPS_PATH}")
    rows = json.loads(PATIENT_GROUPS_PATH.read_text(encoding="utf-8"))
    known_fields = {f.name for f in PatientGroupRecord.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    records = tuple(PatientGroupRecord(**{k: v for k, v in row.items() if k in known_fields}) for row in rows)
    logger.info("Loaded patient_groups from %s (%d records)", PATIENT_GROUPS_PATH, len(records))
    return records


@lru_cache(maxsize=32)
def load_records_for_area(area_value: str) -> tuple[PatientGroupRecord, ...]:
    return tuple(r for r in load_records() if r.therapy_area == area_value)


@lru_cache(maxsize=1)
def load_area_stats() -> dict:
    try:
        if not STATS_PATH.exists():
            return {}
        return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


# -----------------------------
# Scoring: overlap / TF-IDF / BM25
# -----------------------------


def overlap_score(query: str, document: str) -> float:
    """Legacy overlap score (kept for SCORING_MODE=overlap)."""
    q_tokens = set(tokenize(query))
    return overlap_score_from_tokens(q_tokens, document)


def overlap_score_from_tokens(query_tokens: set[str], document: str) -> float:
    # Backwards-compatible helper (string document). Prefer overlap_score_from_record for runtime.
    d_tokens = tokenize(document)
    if not query_tokens or not d_tokens:
        return 0.0
    hit_count = sum(1 for token in d_tokens if token in query_tokens)
    return hit_count / math.sqrt(len(d_tokens))


def overlap_score_from_record(query_tokens: set[str], record: PatientGroupRecord) -> float:
    if not query_tokens:
        return 0.0

    dl = len(record._awg_tokens) + len(record._pop_tokens)
    if dl <= 0:
        return 0.0

    hit_count = 0
    for token in record._awg_tokens:
        if token in query_tokens:
            hit_count += 1
    for token in record._pop_tokens:
        if token in query_tokens:
            hit_count += 1

    return hit_count / math.sqrt(dl)


def build_idf(records: tuple[PatientGroupRecord, ...]) -> dict[str, float]:
    """Compute smoothed IDF for TF-IDF.

    We keep IDF non-negative via log((N+1)/(df+1)).
    """
    N = len(records)
    if N == 0:
        return {}

    df: dict[str, int] = defaultdict(int)
    for r in records:
        for tok in r._terms:
            df[tok] += 1

    return {tok: math.log((N + 1) / (count + 1)) for tok, count in df.items()}


@lru_cache(maxsize=1)
def get_global_idf() -> dict[str, float]:
    return build_idf(load_records())


@lru_cache(maxsize=32)
def get_idf_for_area(area_value: str) -> dict[str, float]:
    records = load_records_for_area(area_value)
    if len(records) < MIN_PRIMARY_RECORDS:
        return get_global_idf()
    return build_idf(records)


def tfidf_score_from_doc_tokens(
    query_tokens: set[str], doc_tokens: tuple[str, ...], idf: Mapping[str, float]
) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0

    counts = Counter(doc_tokens)
    doc_len = len(doc_tokens)

    score = 0.0
    for tok in query_tokens:
        tf = counts.get(tok, 0) / doc_len
        if tf:
            score += tf * idf.get(tok, 0.0)
    return score


def build_bm25_stats(records: tuple[PatientGroupRecord, ...]) -> BM25Stats:
    """Compute BM25 stats (idf + average field lengths)."""
    N = len(records)
    if N == 0:
        return BM25Stats(idf={}, avg_len_awg=1.0, avg_len_pop=1.0, avg_len_zvt=1.0)

    df: dict[str, int] = defaultdict(int)
    sum_awg = 0
    sum_pop = 0
    sum_zvt = 0

    for r in records:
        sum_awg += len(r._awg_tokens)
        sum_pop += len(r._pop_tokens)
        sum_zvt += len(r._zvt_tokens)

        # Document frequency is tracked per *record* (union of all fields).
        for tok in r._terms:
            df[tok] += 1

    # BM25 idf (non-negative): log(1 + (N - df + 0.5)/(df + 0.5))
    idf = {tok: math.log(1.0 + (N - dfi + 0.5) / (dfi + 0.5)) for tok, dfi in df.items()}

    avg_len_awg = (sum_awg / N) if N else 1.0
    avg_len_pop = (sum_pop / N) if N else 1.0
    avg_len_zvt = (sum_zvt / N) if N else 1.0

    # Avoid division-by-zero downstream
    return BM25Stats(
        idf=idf,
        avg_len_awg=max(avg_len_awg, 1.0),
        avg_len_pop=max(avg_len_pop, 1.0),
        avg_len_zvt=max(avg_len_zvt, 1.0),
    )


@lru_cache(maxsize=1)
def get_global_bm25_stats() -> BM25Stats:
    return build_bm25_stats(load_records())


@lru_cache(maxsize=32)
def get_bm25_stats_for_area(area_value: str) -> BM25Stats:
    records = load_records_for_area(area_value)
    if len(records) < MIN_PRIMARY_RECORDS:
        return get_global_bm25_stats()
    return build_bm25_stats(records)


def bm25_score_from_doc_tokens(
    query_tokens: set[str], doc_tokens: tuple[str, ...], idf: Mapping[str, float], avgdl: float
) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0

    counts = Counter(doc_tokens)
    dl = len(doc_tokens)
    avgdl = avgdl if avgdl > 0 else 1.0

    # BM25 length normalisation
    denom_const = BM25_K1 * (1.0 - BM25_B + BM25_B * (dl / avgdl))

    score = 0.0
    for tok in query_tokens:
        tf = counts.get(tok, 0)
        if not tf:
            continue
        tok_idf = idf.get(tok, 0.0)
        score += tok_idf * (tf * (BM25_K1 + 1.0)) / (tf + denom_const)
    return score


def score_record_tfidf(query_tokens: set[str], record: PatientGroupRecord, idf: Mapping[str, float]) -> float:
    awg = tfidf_score_from_doc_tokens(query_tokens, record._awg_tokens, idf)
    pop = tfidf_score_from_doc_tokens(query_tokens, record._pop_tokens, idf)
    zvt = tfidf_score_from_doc_tokens(query_tokens, record._zvt_tokens, idf)
    return awg * W_AWG + pop * W_POP + zvt * W_ZVT


def score_record_bm25(query_tokens: set[str], record: PatientGroupRecord, stats: BM25Stats) -> float:
    awg = bm25_score_from_doc_tokens(query_tokens, record._awg_tokens, stats.idf, stats.avg_len_awg)
    pop = bm25_score_from_doc_tokens(query_tokens, record._pop_tokens, stats.idf, stats.avg_len_pop)
    zvt = bm25_score_from_doc_tokens(query_tokens, record._zvt_tokens, stats.idf, stats.avg_len_zvt)
    return awg * W_AWG + pop * W_POP + zvt * W_ZVT


# -----------------------------
# Business logic helpers
# -----------------------------


def recency_weight(decision_date: str) -> float:
    try:
        decision = datetime.strptime(decision_date, "%Y-%m-%d").date()
    except Exception:
        return 0.8
    years = (date.today() - decision).days / 365.25
    if years < 2:
        return 1.0
    if years <= 4:
        return 0.8
    return 0.6


def decision_quality_weight(record: PatientGroupRecord) -> float:
    """Return evidence weight based on decision type.

    Special procedures (Orphan/ATMP/Ausnahme/Besondere) are less generalizable
    to standard indications, so we downweight them while still including them
    as supporting evidence.

    Returns:
        1.0 for clean standard procedures
        0.4-0.7 for special procedures (graduated by type)
        0.0 if has_zvt is False
    """
    if not record.has_zvt:
        return 0.0

    # Graduated penalties by special procedure type
    # (Orphan decisions often still have valid zVT logic for small populations)
    if record.is_orphan:
        return 0.6

    # ATMP/Ausnahme typically still follow standard zVT principles
    if record.is_atmp or record.is_ausn:
        return 0.7

    # "Besondere" procedures least transferable
    if record.is_besond:
        return 0.4

    return 1.0  # Clean standard procedure


def normalize_candidate(text: str) -> str:
    cleaned = (text or "").strip().lower()
    cleaned = _WS_RE.sub(" ", cleaned)

    cleaned = cleaned.replace("best supportive care", "bsc")
    cleaned = cleaned.replace("best supportive-care", "bsc")
    cleaned = _BSC_RE.sub("bsc", cleaned)

    cleaned = cleaned.replace("beobachtendes abwarten", "watchful waiting")

    cleaned = cleaned.replace("patientenindividuelle therapie", "pit")
    cleaned = cleaned.replace("nach ärztlicher maßgabe", "nach arztlicher maßgabe")
    cleaned = cleaned.replace("nach maßgabe des arztes", "nach arztlicher maßgabe")
    cleaned = cleaned.replace("ärztlicher maßgabe", "arztlicher maßgabe")

    cleaned = _PAREN_ABBR_RE.sub("", cleaned)
    cleaned = _WS_RE.sub(" ", cleaned).strip(" ;,.")
    return cleaned


_MENU_MARKERS = [
    "nach ärztlicher maßgabe",
    "nach arztlicher maßgabe",   # normalized form (ä → a)
    "patientenindividuelle therapie",
    "unter auswahl von",
    "auswahl aus",
    "unter berücksichtigung von",
    "unter beruecksichtigung von",
]
_PIT_RE = re.compile(r"\bpit\b", re.IGNORECASE)


def is_menu_zvt(text_lower: str) -> bool:
    """Return True if zVT text indicates a menu/physician-choice concept.

    Conservative markers include physician's-discretion phrases and
    explicit choice-lists ("unter Auswahl von", "Auswahl aus", PIT).
    When True, the text must NOT be split into atomic comparators.
    """
    if _PIT_RE.search(text_lower):   # "PIT" = patientenindividuelle Therapie
        return True
    return any(m in text_lower for m in _MENU_MARKERS)


def split_zvt_items(zvt_text: str) -> list[str]:
    """Split a zVT text string into atomic comparator items.

    Rules:
    - Empty input → [].
    - Menu-zVT (physician's choice / PIT) → [zvt_text] (no splitting).
    - Otherwise split on: line-breaks, semicolons, " oder ", " / ".
    - DO NOT split on "und".
    - Explosion guard: >MAX_ZVT_ITEMS_PER_RECORD items → [zvt_text].
    - Fragmentation guard: >=6 items AND partial menu markers → [zvt_text].

    Inline comment tests:
    # split_zvt_items("Paclitaxel oder Docetaxel") == ["Paclitaxel", "Docetaxel"]
    # split_zvt_items("Therapie nach ärztlicher Maßgabe unter Auswahl von X oder Y") == [<original>]
    """
    if not zvt_text or not zvt_text.strip():
        return []

    zvt_lower = _WS_RE.sub(" ", zvt_text).strip().lower()

    # Risk A: menu-zVT → keep as single node
    if is_menu_zvt(zvt_lower):
        return [zvt_text]

    text = _WS_RE.sub(" ", zvt_text).strip()

    # Split on newlines, semicolons, " oder " (case-insensitive), " / "
    items: list[str] = [text]
    for pattern in (r"\n", r";", r"(?i)\s+oder\s+", r"\s+/\s+"):
        expanded: list[str] = []
        for it in items:
            expanded.extend(re.split(pattern, it))
        items = expanded

    cleaned = [it.strip().strip(";,. ") for it in items]
    cleaned = [it for it in cleaned if it]

    if not cleaned:
        return []

    # Fragment guard B1: drop modifier-only items (e.g., "ohne Prednison" as standalone)
    filtered = []
    for it in cleaned:
        it_lower = it.lower()
        if any(it_lower.startswith(pfx) for pfx in _FRAG_PREFIXES) and len(WORD_RE.findall(it)) < 4:
            continue
        filtered.append(it)
    cleaned = filtered

    if not cleaned:
        return []

    # Explosion guard: too many fragments → treat as single unstructured text
    if len(cleaned) > MAX_ZVT_ITEMS_PER_RECORD:
        return [zvt_text]

    # Fragmentation guard: "almost menu" constructs (>=6 items + partial menu markers)
    _frag_markers = ["auswahl", "maßgabe"]
    if len(cleaned) >= 6 and (
        any(m in zvt_lower for m in _frag_markers) or bool(_PIT_RE.search(zvt_lower))
    ):
        return [zvt_text]

    return cleaned


# Validation test cases (inline comments):
# 1. Menu detection:
#    "Therapie nach ärztlicher Maßgabe unter Auswahl von X oder Y"
#    -> split_zvt_items returns: ["Therapie nach ärztlicher Maßgabe ..."] (no split)
#    -> comparator_id returns: "menu:arztliche_massgabe"
#
# 2. Real alternatives:
#    "Pembrolizumab oder Nivolumab"
#    -> split_zvt_items returns: ["Pembrolizumab", "Nivolumab"] (split)
#    -> comparator_id("Pembrolizumab") returns: "mono:pembrolizumab"
#    -> comparator_id("Nivolumab") returns: "mono:nivolumab"
#
# 3. Combination therapy:
#    "Paclitaxel + Carboplatin" == "Carboplatin + Paclitaxel"
#    -> comparator_id returns: "combo:carboplatin|paclitaxel" (canonical)
#
# 4. Fragment filtering:
#    "Paclitaxel ohne Prednison oder Docetaxel"
#    -> split_zvt_items returns: ["Paclitaxel", "Docetaxel"] ("ohne Prednison" filtered)
#
# 5. Passive care:
#    "Best Supportive Care (BSC)"
#    -> comparator_id returns: "passive:bsc"
#
# 6. Active intent penalty:
#    Query: "Rezidiviertes NSCLC nach Platin (2L), therapiefähig"
#    Top candidate: "Best Supportive Care"
#    -> Penalty 0.15 applied (strong downweight)
#    -> Red flag: PASSIVE_TOP1_MISMATCH
#    -> Reliability: niedrig


def comparator_id(item: str) -> str:
    """Return a canonical comparator ID for a single zVT item.

    Prefixes:
      "menu:"    – physician's-choice / PIT nodes (never counted as passive)
      "passive:" – BSC / watchful waiting
      "combo:"   – combination regimens (sorted components)
      "mono:"    – all other single agents / regimens

    Inline comment tests:
    # comparator_id("Paclitaxel") == "mono:paclitaxel"
    # comparator_id("Docetaxel") == "mono:docetaxel"
    # comparator_id("Best supportive care") == "passive:bsc"
    # comparator_id("Patientenindividuelle Therapie nach ärztlicher Maßgabe") == "menu:pit"
    # comparator_id("Pembrolizumab + Chemotherapie") starts with "combo:"
    """
    norm = normalize_candidate(item)
    norm_lower = norm.lower()

    # B2: Modifier-only fragments (e.g., "ohne Prednison") are not standalone comparators
    if any(norm_lower.startswith(pfx) for pfx in _FRAG_PREFIXES) and len(WORD_RE.findall(norm_lower)) < 4:
        return ""

    # Menu / physician's-choice nodes (checked BEFORE passive to avoid misclassifying
    # "BSC nach ärztlicher Maßgabe" as passive)
    if is_menu_zvt(norm_lower):
        if "pit" in norm_lower or "patientenindividuelle" in norm_lower:
            return "menu:pit"
        elif "arztlicher maßgabe" in norm_lower:
            return "menu:arztliche_massgabe"
        elif "unter auswahl von" in norm_lower or "auswahl aus" in norm_lower:
            return "menu:auswahl"
        else:
            return "menu:unspecified"

    # Passive comparators
    if "bsc" in norm_lower:
        return "passive:bsc"
    if "watchful waiting" in norm_lower or "beobachtendes abwarten" in norm_lower:
        return "passive:watchful_waiting"

    # Combination regimens
    if _is_combination_therapy_zvt(norm_lower):
        parts = re.split(r"\s\+\s|\bplus\b|zusammen mit", norm_lower, flags=re.IGNORECASE)
        components = sorted(
            {normalize_candidate(p) for p in parts if normalize_candidate(p)}
        )
        if len(components) >= 2:
            return "combo:" + "|".join(components)
        # Fallthrough to mono if split did not yield >=2 components

    return "mono:" + norm_lower


def detect_red_flags(
    query: str,
    top_candidate: CandidateResult,
    line: Optional[TherapyLine],
    comparator_type: Optional["ComparatorType"] = None,
) -> list[str]:
    """Detect obvious mismatches between query and top result.

    These are domain-level logic checks that catch clinically implausible
    matches regardless of BM25 score.
    """
    flags: list[str] = []
    query_lower = query.lower()
    candidate_text = top_candidate.candidate_text.lower()
    comparator_type_value = comparator_type.value if comparator_type else None

    # Rule 1: Post-platinum progression → platinum rechallenge unlikely
    post_platin_markers = [
        "progress nach platin", "post-platin", "platinrefraktär",
        "nach platinbasierter", "platinum-refractory",
    ]
    platin_drugs = ["cisplatin", "carboplatin", "oxaliplatin"]

    if any(m in query_lower for m in post_platin_markers):
        if any(d in candidate_text for d in platin_drugs):
            flags.append("SETTING_MISMATCH_PLATIN")

    # Rule 2: Systemic therapy suitable → BSC / watchful waiting unlikely top choice
    if any(m in query_lower for m in THERAPY_OK_MARKERS):
        if is_passive_candidate_text(candidate_text):
            if not _query_requests_passive(query_lower, comparator_type_value):
                flags.append("BSC_CONTRADICTION")

    # Rule 3: First-line → no post-progression options
    if line and line.value == "1L":
        post_prog_markers = ["nach versagen", "nach progress", "vorbehandelt"]
        if any(m in candidate_text for m in post_prog_markers):
            flags.append("LINE_MISMATCH_1L")

    # Rule 4: Active treatment intent → passive top comparator is suspicious
    if _query_implies_active_intent(query_lower, line):
        if not _query_requests_passive(query_lower, comparator_type_value):
            if is_passive_candidate_text(candidate_text):
                flags.append("PASSIVE_TOP1_MISMATCH")

    return flags


def apply_domain_penalties(
    score: float,
    query: str,
    candidate_text: str,
    line: Optional[TherapyLine],
    comparator_type: Optional["ComparatorType"] = None,
) -> float:
    """Apply soft penalties for clinically implausible matches.

    These are NOT hard filters — they adjust ranking to make better
    candidates rise to top.
    """
    penalty = 1.0
    query_lower = query.lower()
    candidate_lower = candidate_text.lower()

    # Penalty 1: Post-platinum progression + platinum comparator
    post_platin = any(x in query_lower for x in [
        "progress nach platin", "post-platin", "platinrefraktär",
        "nach platinbasierter", "platinum-refractory",
    ])
    has_platin = any(x in candidate_lower for x in [
        "cisplatin", "carboplatin", "oxaliplatin",
    ])
    if post_platin and has_platin:
        penalty *= 0.3

    # Penalty 2: Passive comparator in an active-intent context
    comparator_type_value = comparator_type.value if comparator_type else None
    line_value = line.value if line else None
    is_passive = is_passive_candidate_text(candidate_text)
    passive_requested = _query_requests_passive(query_lower, comparator_type_value)
    active_intent = _query_implies_active_intent(query_lower, line)

    if active_intent and not passive_requested and is_passive:
        # Late-line (3L+): passive is more legitimate despite active intent
        if line_value and line_value in ("3L", "4L+", "später"):
            penalty *= 0.5  # Moderate downweight
        else:
            penalty *= 0.15  # Strong downweight (not eliminative)

    # Penalty 3: First-line + post-progression options
    if line and line.value == "1L":
        is_post_prog = any(x in candidate_lower for x in [
            "nach versagen", "nach progress", "vorbehandelt",
        ])
        if is_post_prog:
            penalty *= 0.5

    # Boost 4: Late-line + BSC (BSC becomes more likely in 3L+)
    if line and line.value == "später":
        if is_passive or "ärztliche maßgabe" in candidate_lower:
            penalty *= 1.5

    return score * penalty


def _is_combination_therapy_zvt(zvt_lower: str) -> bool:
    """Heuristic: does the zVT text describe a combination/add-on regimen?

    We avoid treating biomarker notation like 'HER2+' as combination by requiring spaces around '+'.
    """
    t = zvt_lower or ""
    if not t:
        return False

    if "kombination" in t or "kombiniert" in t:
        return True
    if "zusätzlich" in t or "zusaetzlich" in t:
        return True
    if "add-on" in t:
        return True
    if "zusammen mit" in t:
        return True
    if _COMBO_PLUS_RE.search(t):
        return True
    if _PLUS_WORD_RE.search(t):
        return True
    return False

def confidence_label(score: float, top_score: float, support_cases: int) -> str:
    """Confidence is relative to the best candidate in *this* request."""
    if top_score <= 0:
        return "niedrig"

    relative = score / top_score
    if relative >= 0.80 and support_cases >= 3:
        return "hoch"
    if relative >= 0.50 and support_cases >= 2:
        return "mittel"
    return "niedrig"


def ambiguity_label(sorted_scores: list[float]) -> str:
    if len(sorted_scores) < 2 or sorted_scores[0] <= 0:
        return "niedrig"
    ratio = sorted_scores[min(4, len(sorted_scores) - 1)] / sorted_scores[0]
    if ratio > 0.75:
        return "hoch"
    if ratio > 0.45:
        return "mittel"
    return "niedrig"


def build_query(payload: ShortlistRequest) -> str:
    parts = [payload.indication_text]
    if payload.population_text:
        parts.append(payload.population_text)
    if payload.line:
        parts.append(f"Therapielinie: {payload.line.value}")
    if payload.comparator_type:
        parts.append(f"Comparator-Typ: {payload.comparator_type.value}")
    if payload.comparator_text:
        parts.append(payload.comparator_text)
    return "\n".join(parts)


def aggregate_score(best_by_decision: dict[str, float]) -> float:
    """Aggregate per-decision evidence into a candidate-level support score.

    - We avoid double-counting within a decision by using the best hit per decision.
    - We lightly reward breadth (more distinct decisions) via a log bonus.
    """
    if not best_by_decision:
        return 0.0

    best_scores = list(best_by_decision.values())
    base = sum(best_scores)

    coverage_bonus = math.log(1 + len(best_scores)) * 0.15
    return base * (1 + coverage_bonus)


def derive_reliability(
    status: str,
    candidates: list[CandidateResult],
    ambiguity: str,
    reasons: list[str] | None,
    notices: list[str] | None,
) -> tuple[str, list[str]]:
    """Derive reliability assessment from existing signals.
    
    Args:
        status: "ok" | "needs_clarification" | "no_result"
        candidates: ranked list of candidates
        ambiguity: "hoch" | "mittel" | "niedrig"
        reasons: Quality-Gate reasons
        notices: hints/notices
        
    Returns:
        tuple of (reliability, reliability_reasons)
        reliability: "hoch" | "mittel" | "niedrig"
        reliability_reasons: list of max 3 prioritized, actionable reasons
    """
    # Hard guard: kein Ergebnis => nicht belastbar
    if status == "no_result" or not candidates:
        return "niedrig", ["Kein belastbares Ergebnis gefunden."]
    
    top = candidates[0]
    cases = top.support_cases_clean or top.support_cases or 0
    conf = top.confidence  # "hoch"|"mittel"|"niedrig"
    
    # signals
    # More robust fallback detection: check for specific substrings that indicate fallback/analog scenarios
    has_fallback = ("AREA_FALLBACK" in (reasons or [])) or any(
        ("Analogfällen" in n or "andere Therapiegebiete berücksichtigt" in n) for n in (notices or [])
    )
    high_amb = (ambiguity == "hoch")
    low_conf = (conf == "niedrig")

    # Detect red flags from reasons
    red_flags = [r for r in (reasons or []) if r in RED_FLAG_KEYS]
    
    # Evidence tiers (realistisch für Datenbestand)
    strong_evid = cases >= 3
    med_evid = cases == 2
    weak_evid = cases <= 1
    
    # ── Reliability decision ──
    # NIEDRIG: BSC_CONTRADICTION or PASSIVE_TOP1_MISMATCH are hard corridor exits (always unreliable)
    if "BSC_CONTRADICTION" in red_flags or "PASSIVE_TOP1_MISMATCH" in red_flags:
        rel = "niedrig"
    # NIEDRIG: Red flags + low evidence → critically unreliable
    elif red_flags and cases <= 2:
        rel = "niedrig"
    # NIEDRIG: Blocker / kritisch
    elif "TOO_GENERIC" in (reasons or []):
        rel = "niedrig"
    elif weak_evid and (low_conf or high_amb):
        rel = "niedrig"
    
    # HOCH: ODER-Gate (zwei Wege) – only without red flags
    elif strong_evid and conf == "hoch" and not high_amb and not red_flags:
        rel = "hoch"
    elif strong_evid and ambiguity == "niedrig" and not has_fallback and not red_flags:
        rel = "hoch"
    
    # MITTEL: alles dazwischen
    else:
        rel = "mittel"
    
    # ── Reasons: priorisiert (max 3) ──
    reason_priority: list[tuple[str, int]] = []

    # (0) Red flags: highest priority
    if "SETTING_MISMATCH_PLATIN" in red_flags:
        reason_priority.append(("Therapiesequenz-Matching unsicher (Platin-Rechallenge nach Progress).", 0))
    if "BSC_CONTRADICTION" in red_flags:
        reason_priority.append(("Best Supportive Care unwahrscheinlich bei therapiefähigen Patienten.", 0))
    if "LINE_MISMATCH_1L" in red_flags:
        reason_priority.append(("Therapielinie stimmt möglicherweise nicht überein.", 0))
    if "PASSIVE_TOP1_MISMATCH" in red_flags:
        reason_priority.append(("Top-Comparator wirkt passiv (BSC/Abwarten) trotz aktiven Behandlungskontexts.", 0))
    
    # (1) Blocker: zuerst, weil actionable
    if "TOO_GENERIC" in (reasons or []):
        reason_priority.append(("Eingabe ist zu allgemein – bitte präzisieren.", 1))
    if weak_evid:
        reason_priority.append(("Sehr wenige ähnliche Entscheidungen vorhanden.", 1))
    
    # (2) Warnings
    if has_fallback:
        reason_priority.append(("Wenig Daten im Therapiegebiet – Ergebnis basiert auf Analogfällen.", 2))
    if high_amb:
        reason_priority.append(("Mehrere Comparatoren sind ähnlich plausibel.", 2))
    
    # (3) Info
    if low_conf:
        reason_priority.append(("Die Übereinstimmung ist nur schwach.", 3))
    
    reason_priority.sort(key=lambda x: x[1])
    texts = [t for t, _ in reason_priority[:3]]
    if not texts:
        if rel == "hoch":
            pos: list[str] = []
            if cases >= 3:
                pos.append(f"{cases} vergleichbare Entscheidungen stützen die Top-Option.")
            if ambiguity == "niedrig":
                pos.append("Klare Trennschärfe zwischen Top-Option und Alternativen.")
            if conf == "hoch":
                pos.append("Hohe Modellsicherheit des Matchings.")
            texts = pos[:2]
        elif rel == "mittel":
            lim: list[str] = []
            if cases == 2:
                lim.append("Nur 2 ähnliche Entscheidungen vorhanden.")
            if ambiguity == "hoch":
                lim.append("Mehrere Comparatoren sind ähnlich plausibel.")
            elif ambiguity == "mittel":
                lim.append("Trennschärfe ist nur mittel – mehrere Optionen bleiben möglich.")
            if conf == "niedrig":
                lim.append("Die Übereinstimmung ist nur schwach.")
            if has_fallback:
                lim.append("Wenig Daten im Therapiegebiet – Ergebnis basiert auf Analogfällen.")
            texts = lim[:2]
        else:
            texts = ["Kein belastbares Ergebnis gefunden."]

    return rel, texts


def shortlist(payload: ShortlistRequest) -> tuple[list[CandidateResult], str, list[str], list[str]]:
    query = build_query(payload)
    query_tokens = set(tokenize(query))

    # Phase 0: Input fidelity logging
    logger.info(
        "shortlist input indication_len=%d population_len=%d population_preview=%.80s",
        len(payload.indication_text or ""),
        len(payload.population_text or ""),
        (payload.population_text or "")[:80],
    )

    area_value = payload.therapy_area.value
    primary_records = load_records_for_area(area_value)

    # Therapy-area selection (strict by default; soft fallback if the area corpus is tiny)
    if len(primary_records) >= MIN_PRIMARY_RECORDS:
        records_with_penalty = [(r, 1.0) for r in primary_records]
        use_area_corpus = True
    else:
        records_with_penalty = [
            (r, 1.0 if r.therapy_area == area_value else OTHER_AREA_PENALTY) for r in load_records()
        ]
        use_area_corpus = False

    # --- IMPORTANT FIX ---
    # Only build/consult the caches required for the active SCORING_MODE
    idf: Optional[Mapping[str, float]] = None
    bm25_stats: Optional[BM25Stats] = None

    if SCORING_MODE == "tfidf":
        idf = get_idf_for_area(area_value) if use_area_corpus else get_global_idf()
    elif SCORING_MODE == "bm25":
        bm25_stats = get_bm25_stats_for_area(area_value) if use_area_corpus else get_global_bm25_stats()

    # Fail fast: if these are None, we have a logic bug (don't silently return empty results).
    if SCORING_MODE == "tfidf" and idf is None:
        raise RuntimeError("idf wurde nicht initialisiert – das sollte nicht passieren")
    if SCORING_MODE == "bm25" and bm25_stats is None:
        raise RuntimeError("bm25_stats wurde nicht initialisiert – das sollte nicht passieren")

    retrieved: list[tuple[PatientGroupRecord, float, float]] = []
    for record, area_penalty in records_with_penalty:
        if SCORING_MODE == "overlap":
            base_score = overlap_score_from_record(query_tokens, record)
        elif SCORING_MODE == "tfidf":
            base_score = score_record_tfidf(query_tokens, record, idf)  # type: ignore[arg-type]
        else:  # bm25 (default)
            base_score = score_record_bm25(query_tokens, record, bm25_stats)  # type: ignore[arg-type]

        # Apply area penalty already for retrieval ordering in fallback mode.
        retrieval_score = base_score * area_penalty
        if retrieval_score > 0:
            retrieved.append((record, base_score, area_penalty))

    retrieved.sort(key=lambda item: item[1] * item[2], reverse=True)
    top_retrieved = retrieved[:RETRIEVE_LIMIT]

    aggregated: dict[str, dict] = defaultdict(
        lambda: {
            "text": "",
            "score": 0.0,
            "refs": [],
            "best_by_decision": {},
            "best_by_decision_clean": {},
            "best_by_decision_special": {},
            "best_display_score": -1.0,
        }
    )

    # Risk B: track created keys to enforce MAX_CANDIDATE_KEYS budget per request
    created_keys: set[str] = set()

    for idx, (record, base_score, area_penalty) in enumerate(top_retrieved):
        if not record.zvt_text:
            continue

        # Contextual nudges (small)
        adj = 1.0
        zvt_lower = (record.zvt_text or "").lower()
        is_combo = _is_combination_therapy_zvt(zvt_lower)

        # Role-based hinting
        if payload.role.value == "add-on" and is_combo:
            adj += 0.1
        if payload.role.value == "monotherapy":
            # Monotherapy should prefer non-combination comparators, and down-rank clear combination regimens.
            adj += 0.05 if not is_combo else -0.1

        # Setting hinting
        if payload.setting.value == "stationär" and any(x in zvt_lower for x in ["infusion", "stationär"]):
            adj += 0.1

        # Uncertainty penalties
        if payload.setting.value == "unklar":
            adj -= 0.1
        if payload.role.value == "unklar":
            adj -= 0.1

        weighted = base_score * recency_weight(record.decision_date) * adj * area_penalty
        weighted *= decision_quality_weight(record)

        is_special = bool(record.is_orphan or record.is_besond or record.is_ausn or record.is_atmp)

        # Risk B: only split for the top SPLIT_ONLY_TOP_RETRIEVED records
        if idx < SPLIT_ONLY_TOP_RETRIEVED:
            items = split_zvt_items(record.zvt_text)
        else:
            items = [record.zvt_text]

        for item in items:
            candidate_key = comparator_id(item)

            # B3: Skip modifier-only fragments (comparator_id returns "" for them)
            if not candidate_key:
                continue

            # Candidate key budget guard (Risk B):
            # New keys beyond MAX_CANDIDATE_KEYS are silently dropped;
            # existing keys continue to accumulate evidence.
            is_new_key = candidate_key not in aggregated
            if is_new_key and len(created_keys) >= MAX_CANDIDATE_KEYS:
                continue
            if is_new_key:
                created_keys.add(candidate_key)

            entry = aggregated[candidate_key]

            # Use the strongest supporting wording as the display text for this candidate.
            if weighted > entry["best_display_score"]:
                entry["text"] = item
                entry["best_display_score"] = weighted

            entry["refs"].append(
                ReferenceItem(
                    decision_id=record.decision_id,
                    product_name=record.product_name,
                    decision_date=record.decision_date,
                    url=record.url,
                    snippet=(record.patient_group_text or "")[:260],
                    score=round(weighted, 4),
                )
            )

            prev = entry["best_by_decision"].get(record.decision_id)
            if prev is None or weighted > prev:
                entry["best_by_decision"][record.decision_id] = weighted

            bucket = "best_by_decision_special" if is_special else "best_by_decision_clean"
            prev_bucket = entry[bucket].get(record.decision_id)
            if prev_bucket is None or weighted > prev_bucket:
                entry[bucket][record.decision_id] = weighted

    for entry in aggregated.values():
        entry["score"] = aggregate_score(entry["best_by_decision"])

    # Apply domain penalties to aggregated candidate scores
    for entry in aggregated.values():
        entry["score"] = apply_domain_penalties(
            entry["score"],
            query=query,
            candidate_text=entry["text"],
            line=payload.line,
        )

    ranked = sorted(aggregated.values(), key=lambda e: e["score"], reverse=True)[:5]
    top_score = ranked[0]["score"] if ranked else 0.0

    candidates: list[CandidateResult] = []
    for idx, row in enumerate(ranked, start=1):
        refs = sorted(row["refs"], key=lambda r: r.score, reverse=True)[:5]
        support_cases = len(row["best_by_decision"])
        support_cases_clean = len(row["best_by_decision_clean"])
        support_cases_special = len(row["best_by_decision_special"])
        score = float(row["score"])
        # Use clean cases for confidence label when available (fall back to total)
        cases_for_conf = support_cases_clean or support_cases
        candidates.append(
            CandidateResult(
                rank=idx,
                candidate_text=row["text"],
                support_score=round(score, 4),
                confidence=confidence_label(score, top_score, cases_for_conf),
                support_cases=support_cases,
                support_cases_clean=support_cases_clean,
                support_cases_special=support_cases_special,
                references=refs,
            )
        )

    ambiguity = ambiguity_label([c.support_score for c in candidates])

    notices: list[str] = []
    if ENABLE_ZVT_NOTICES:
        area_stats = load_area_stats().get(area_value)
        if area_stats:
            total = area_stats.get("total_rows", 0)
            has_zvt = area_stats.get("has_zvt_rows", 0)
            orphan_missing = area_stats.get("orphan_missing_zvt_rows", 0)
            orphan_missing_ratio = orphan_missing / total if total else 0
            if has_zvt < 15 or orphan_missing_ratio >= 0.50:
                notices.append(
                    "Für dieses Therapiegebiet liegen viele Orphan-/Sonderverfahren ohne festgelegte zVT vor. "
                    "Ergebnisse basieren auf Analogfällen und können fachfremd sein."
                )
            special_rows = area_stats.get("special_rows", 0)
            special_ratio = special_rows / total if total else 0
            if special_ratio >= 0.30 and not any("Sonderverfahren" in n for n in notices):
                notices.append(
                    "Hinweis: Hoher Sonderverfahren-Anteil in diesem Therapiegebiet – "
                    "Ergebnisse basieren teilweise auf Orphan- oder ATMP-Entscheidungen."
                )
        if not use_area_corpus:
            notices.append(
                "Hinweis: Es wurden ergänzend andere Therapiegebiete berücksichtigt (mit Abschlag), "
                "weil im gewählten Gebiet zu wenige passende Präzedenzfälle vorlagen."
            )

    # Red flag detection on top candidate
    reasons: list[str] = []
    if candidates:
        red_flags = detect_red_flags(
            query=query,
            top_candidate=candidates[0],
            line=payload.line,
            comparator_type=payload.comparator_type,
        )
        reasons.extend(red_flags)

    return candidates, ambiguity, notices, reasons

