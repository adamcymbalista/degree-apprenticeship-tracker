"""Source: https://www.apprentifinder.co.uk/

A third-party aggregator ("UK's Largest Degree Apprenticeship Database")
that pulls listings from many employer/university sites, so it isn't
limited to whatever an employer chooses to advertise on
findapprenticeship.service.gov.uk - it's the closest thing to "all degree
apprenticeships" this project has a reliable way to reach.

Confirmed live (2026-09-21): its /browse page is a client-rendered Next.js
app (like UCAS, not directly scrapable as HTML), but it calls a plain,
unauthenticated JSON endpoint - api/opportunities - to populate itself.
robots.txt is "Allow: /" for everything, so this is fetched the same
respectful way as every other source (rate-limited, real User-Agent), not
worked around.

That endpoint returns every live opportunity in one response - all levels,
all UK locations, not just degree/Level 6/London/CS ones - so, like
findapprenticeship.py, this module does no filtering itself. scoring.py is
the single place inclusion/exclusion happens.

Fields the endpoint provides map directly onto Vacancy: `field` (e.g.
"Software Engineering", "Cyber Security", "Data Science") is genuinely
structured subject data - more reliable than the free-text guessing
findapprenticeship.py has to do - and `university` is the partner
university/training provider's name (useful for spotting QMUL-partnered
roles specifically; see scoring.py). There's no per-listing "apply" URL in
this feed, so the vacancy's `url` points at ApprentiFinder's own detail
view (`/browse?selected=<id>`), which does show a real "Apply on company
site" link when opened - one extra click, not a dead end.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from app.http_client import get
from app.models import Vacancy, VacancyStatus

logger = logging.getLogger("tracker.sources.apprentifinder")

BASE_URL = "https://www.apprentifinder.co.uk"
API_PATH = "/api/opportunities"


def _parse_iso_date(value: str | None) -> date | None:
    """Endpoint gives ISO datetimes ("2026-09-25T23:59:59Z") or bare ISO
    dates ("2027-09-01") - the date part is always the first 10 characters
    either way, which sidesteps Python-version differences in how
    datetime.fromisoformat handles a trailing "Z".
    """
    if not value or len(value) < 10:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _human_date(value: str | None) -> str | None:
    """Render as "1 September 2027" - matches the format findapprenticeship.py
    produces, which scoring.py's start-year detection depends on (it looks
    for a standalone 4-digit token, which a raw "2027-09-01" string won't
    split out but "1 September 2027" will).
    """
    d = _parse_iso_date(value)
    return d.strftime("%d %B %Y") if d else None


def _parse_item(item: dict) -> Vacancy | None:
    item_id = item.get("id")
    title = item.get("title")
    employer = item.get("employer")
    if not item_id or not title or not employer:
        return None

    deadline_date = _parse_iso_date(item.get("applicationDeadline"))
    if deadline_date:
        if deadline_date >= date.today():
            status = VacancyStatus.OPEN
            evidence = (
                f"Listed as a live opportunity on ApprentiFinder with an active "
                f"closing date of {deadline_date.isoformat()}."
            )
        else:
            status = VacancyStatus.DEADLINE_PASSED
            evidence = f"Closing date {deadline_date.isoformat()} has passed."
    else:
        # No deadline given, but still present in ApprentiFinder's live feed
        # (closed roles are removed from it) - same reasoning findapprenticeship.py
        # uses for a listing with no parseable closing date.
        status = VacancyStatus.OPEN
        evidence = f"Listed as a live opportunity on ApprentiFinder (id {item_id})."

    salary = item.get("salaryText") or (f"£{item['salary']:,}" if item.get("salary") else None)

    return Vacancy(
        title=title,
        employer=employer,
        source="apprentifinder",
        url=f"{BASE_URL}/browse?selected={item_id}",
        location=item.get("location"),
        degree=item.get("university"),
        subject=item.get("field"),
        level=item.get("level"),
        start_date=_human_date(item.get("startDate")),
        application_deadline=_human_date(item.get("applicationDeadline")),
        salary=salary,
        source_id=item_id,
        status=status,
        status_evidence=evidence,
        raw_source_data={"duration": item.get("duration"), "remote": item.get("remote")},
    )


def fetch(config: dict) -> list[Vacancy]:
    rate = config.get("rate_limit", {})
    delay = rate.get("delay_seconds", 2.0)
    timeout = rate.get("timeout_seconds", 20)

    resp = get(BASE_URL + API_PATH, timeout=timeout, delay_seconds=delay)
    if resp is None:
        logger.warning("apprentifinder: request failed, skipping this run")
        return []

    try:
        items = resp.json()
    except ValueError as exc:
        logger.warning("apprentifinder: response was not valid JSON: %s", exc)
        return []

    results: list[Vacancy] = []
    for item in items:
        try:
            vacancy = _parse_item(item)
        except Exception as exc:  # one malformed record must never kill the source
            logger.warning("apprentifinder: failed to parse a listing: %s", exc)
            continue
        if vacancy is not None:
            results.append(vacancy)

    logger.info("apprentifinder: %d results", len(results))
    return results
