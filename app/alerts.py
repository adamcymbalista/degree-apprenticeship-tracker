"""Decides which vacancies get an emergency email today, and how the weekly
digest is grouped into its six sections. Pure functions over already-scored
Vacancy objects plus a bit of DB state - no I/O here, so these are trivial
to unit test.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from app.models import MatchCategory, Vacancy, VacancyStatus
from app.status import just_opened, parse_date

YEAR_RE = re.compile(r"(20\d{2})")


def _wrong_entry_year(v: Vacancy, config: dict) -> bool:
    """True only if the vacancy's start date is a *confirmed* year that
    isn't the primary one - spec: "do not mix 2026 programmes into the main
    results". Unknown/unparseable years are not penalised here (that's a
    missing-data case, not a wrong-year one).
    """
    m = YEAR_RE.search(v.start_date or "")
    if not m:
        return False
    primary = config.get("entry_year", {}).get("primary", 2027)
    return int(m.group(1)) != primary


def select_emergency_candidates(
    scanned: list[tuple[Vacancy, str | None]], config: dict
) -> list[Vacancy]:
    """scanned: (vacancy, previous_status_value_or_None) for everything seen
    in *today's* scan. Returns vacancies that should trigger an emergency
    email: opened today (brand new-and-open, or transitioned to OPEN) and
    score >= minimum_score_for_emergency.
    """
    min_score = config.get("minimum_score_for_emergency", 75)
    out = []
    for v, prev_status in scanned:
        if v.match_category == MatchCategory.EXCLUDED:
            continue
        if v.score < min_score:
            continue
        if just_opened(prev_status, v.status):
            out.append(v)
    return out


def _days_ago(iso_text: str | None) -> float | None:
    if not iso_text:
        return None
    try:
        dt = datetime.fromisoformat(iso_text)
    except ValueError:
        return None
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    return (now - dt).total_seconds() / 86400


def _deadline_within_days(deadline_text: str | None, days: int) -> bool:
    if not deadline_text:
        return False
    d = parse_date(deadline_text)
    if not d:
        return False
    return date.today() <= d <= date.today() + timedelta(days=days)


def group_weekly(vacancies: list[Vacancy], config: dict, window_days: int = 7) -> dict[str, list[Vacancy]]:
    """Buckets vacancies into the six weekly-email sections. A vacancy can
    appear in more than one section (e.g. new AND high match).
    """
    relevant = [v for v in vacancies if v.match_category != MatchCategory.EXCLUDED]

    sections: dict[str, list[Vacancy]] = {
        "NEW HIGH-MATCH OPPORTUNITIES": [],
        "NEWLY OPENED APPLICATIONS": [],
        "STILL OPEN — HIGH MATCH": [],
        "DEADLINES COMING UP": [],
        "NEWLY DISCOVERED BUT NOT YET OPEN": [],
        "INTERESTING SPORT / CRIME / SECURITY / TRAVEL OPTIONS": [],
    }
    high_match = {MatchCategory.EXCEPTIONAL_MATCH, MatchCategory.STRONG_MATCH}
    interest_tags = {"SPORT", "SPORTS_ANALYTICS", "CRIME", "SECURITY", "INTELLIGENCE",
                      "TRANSPORT", "TRAVEL", "AVIATION", "GOVERNMENT"}

    for v in relevant:
        discovered_days = _days_ago(v.discovered_at)
        is_new_this_week = discovered_days is not None and discovered_days <= window_days

        wrong_year = _wrong_entry_year(v, config)

        if is_new_this_week and v.match_category in high_match and not wrong_year:
            sections["NEW HIGH-MATCH OPPORTUNITIES"].append(v)

        if v.status == VacancyStatus.OPEN:
            # We don't have a separate "opened_at" timestamp on the dataclass;
            # main.py passes vacancies whose DB row's status_changed_at is
            # recent as already-flagged via v.raw_source_data["_opened_this_week"].
            if v.raw_source_data.get("_opened_this_week"):
                sections["NEWLY OPENED APPLICATIONS"].append(v)
            elif v.match_category in high_match and not wrong_year:
                sections["STILL OPEN — HIGH MATCH"].append(v)

        if v.status == VacancyStatus.OPEN and _deadline_within_days(v.application_deadline, 14):
            sections["DEADLINES COMING UP"].append(v)

        if is_new_this_week and v.status == VacancyStatus.NOT_YET_OPEN:
            sections["NEWLY DISCOVERED BUT NOT YET OPEN"].append(v)

        if set(v.tags) & interest_tags and v not in sections["NEW HIGH-MATCH OPPORTUNITIES"]:
            sections["INTERESTING SPORT / CRIME / SECURITY / TRAVEL OPTIONS"].append(v)

    return sections
