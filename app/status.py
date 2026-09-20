"""Vacancy status detection and transition tracking.

We only ever claim OPEN when the source gave positive evidence (see each
source module - status_evidence is set there). No page-exists-so-it's-open
guessing anywhere in this file.
"""
from __future__ import annotations

from datetime import date, datetime

from app.models import Vacancy, VacancyStatus


def parse_date(text: str | None) -> date | None:
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def infer_status_from_dates(v: Vacancy, today: date | None = None) -> VacancyStatus:
    """Fallback used only when a source could not give an explicit status
    (status stayed UNKNOWN). Infers from open/deadline dates when present;
    otherwise stays UNKNOWN rather than guessing.
    """
    today = today or date.today()
    if v.status != VacancyStatus.UNKNOWN:
        return v.status

    deadline = parse_date(v.application_deadline)
    if deadline and deadline < today:
        return VacancyStatus.DEADLINE_PASSED

    open_date = parse_date(v.application_open_date)
    if open_date and open_date > today:
        return VacancyStatus.NOT_YET_OPEN

    return VacancyStatus.UNKNOWN


TRANSITION_LABELS = {
    (VacancyStatus.CLOSED, VacancyStatus.OPEN): "CLOSED -> OPEN",
    (VacancyStatus.NOT_YET_OPEN, VacancyStatus.OPEN): "NOT_YET_OPEN -> OPEN",
    (VacancyStatus.OPEN, VacancyStatus.CLOSED): "OPEN -> CLOSED",
    (VacancyStatus.UNKNOWN, VacancyStatus.OPEN): "UNKNOWN -> OPEN",
}


def detect_transition(previous_status: str | None, new_status: VacancyStatus) -> str | None:
    """Returns a human-readable transition label, or None if nothing notable
    changed. previous_status is the raw DB string (or None for a brand-new row).
    """
    if previous_status is None:
        return None
    try:
        prev = VacancyStatus(previous_status)
    except ValueError:
        prev = VacancyStatus.UNKNOWN
    if prev == new_status:
        return None
    return TRANSITION_LABELS.get((prev, new_status), f"{prev.value} -> {new_status.value}")


def deadline_changed(previous_deadline: str | None, new_deadline: str | None) -> bool:
    return bool(previous_deadline) and bool(new_deadline) and previous_deadline != new_deadline


def just_opened(previous_status: str | None, new_status: VacancyStatus) -> bool:
    """True if this vacancy's status became OPEN as of this run (covers both
    a genuine CLOSED/NOT_YET_OPEN -> OPEN transition, and a brand new vacancy
    discovered already OPEN)."""
    if new_status != VacancyStatus.OPEN:
        return False
    if previous_status is None:
        return True
    return previous_status != VacancyStatus.OPEN.value
