"""Core data model for a normalised apprenticeship vacancy.

Every source module (app/sources/*) must return a list of Vacancy objects.
Fields we cannot determine from a source are left as None/UNKNOWN rather than
guessed - see status.py and normalizer.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class VacancyStatus(str, Enum):
    NOT_YET_OPEN = "NOT_YET_OPEN"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    DEADLINE_PASSED = "DEADLINE_PASSED"
    UNKNOWN = "UNKNOWN"


class MatchCategory(str, Enum):
    EXCEPTIONAL_MATCH = "EXCEPTIONAL_MATCH"
    STRONG_MATCH = "STRONG_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    LOW_MATCH = "LOW_MATCH"
    EXCLUDED = "EXCLUDED"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Vacancy:
    title: str
    employer: str
    source: str  # e.g. "findapprenticeship", "ucas", "employer:bt"
    url: str

    description: Optional[str] = None
    location: Optional[str] = None
    degree: Optional[str] = None
    qualification: Optional[str] = None
    level: Optional[int] = None  # apprenticeship level, e.g. 6
    subject: Optional[str] = None
    start_date: Optional[str] = None  # free text or ISO date, best effort
    application_open_date: Optional[str] = None
    application_deadline: Optional[str] = None
    salary: Optional[str] = None
    entry_requirements: Optional[str] = None
    source_id: Optional[str] = None  # official vacancy ref if the source has one
    keywords: list[str] = field(default_factory=list)
    raw_source_data: dict = field(default_factory=dict)

    status: VacancyStatus = VacancyStatus.UNKNOWN
    status_evidence: Optional[str] = None  # what told us the status (see status.py)

    discovered_at: str = field(default_factory=utcnow_iso)
    last_seen: str = field(default_factory=utcnow_iso)

    # populated later by scoring.py
    score: int = 0
    match_category: MatchCategory = MatchCategory.LOW_MATCH
    score_reasons: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # populated by deduplication.py / database.py
    canonical_id: Optional[str] = None
    dedup_key: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, VacancyStatus) else self.status
        d["match_category"] = (
            self.match_category.value if isinstance(self.match_category, MatchCategory) else self.match_category
        )
        return d
