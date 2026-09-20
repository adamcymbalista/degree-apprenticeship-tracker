"""Generic source for employer/university careers pages.

Most large employer ATSs (Workday, SuccessFactors, Greenhouse, and most
custom-built careers sites) embed schema.org JobPosting structured data as
<script type="application/ld+json"> - this is far more robust than scraping
each employer's bespoke HTML/CSS, and it's the "official" machine-readable
source per page (prefer structured data over brittle selectors).

We only trust that structured data. If a page has none, we log it and move
on rather than guessing a vacancy out of page prose - per spec: "If a source
doesn't provide enough information, mark the relevant fields unknown" /
"never invent apprenticeship information".

Covers both PROJECT_INSTRUCTIONS.sources.employer_generic and .qmul (QMUL
just supplies its own URL list via app/sources/qmul.py).
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.http_client import get
from app.models import Vacancy, VacancyStatus

logger = logging.getLogger("tracker.sources.employers")

APPRENTICESHIP_TERMS = ("apprentice", "apprenticeship")


def _iter_job_postings(ld_json_obj):
    """A page's JSON-LD can be a single object, a list, or a @graph list."""
    if isinstance(ld_json_obj, list):
        for item in ld_json_obj:
            yield from _iter_job_postings(item)
        return
    if not isinstance(ld_json_obj, dict):
        return
    types = ld_json_obj.get("@type")
    types = [types] if isinstance(types, str) else (types or [])
    if "JobPosting" in types:
        yield ld_json_obj
    if "@graph" in ld_json_obj:
        yield from _iter_job_postings(ld_json_obj["@graph"])


def _text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("name") or value.get("@id")
    if isinstance(value, list):
        return ", ".join(str(_text(v)) for v in value if v)
    return str(value).strip() or None


def _location_text(job: dict) -> str | None:
    loc = job.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if not isinstance(loc, dict):
        return _text(loc)
    address = loc.get("address", {})
    if isinstance(address, dict):
        parts = [address.get("addressLocality"), address.get("addressRegion"), address.get("postalCode")]
        return ", ".join(p for p in parts if p) or None
    return _text(address)


def _iso_date(text: str | None) -> str | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return text


def _parse_job_posting(job: dict, employer_name: str, page_url: str) -> Vacancy | None:
    title = _text(job.get("title"))
    if not title:
        return None

    description = _text(job.get("description"))
    if description:
        # JSON-LD descriptions are often raw HTML
        description = BeautifulSoup(description, "html.parser").get_text(" ", strip=True)

    org = job.get("hiringOrganization")
    employer = _text(org) if org else employer_name
    valid_through = _iso_date(job.get("validThrough"))
    date_posted = _iso_date(job.get("datePosted"))

    status = VacancyStatus.OPEN
    evidence = f"JobPosting structured data (schema.org) published on {employer_name}'s own careers page."
    deadline_date = None
    if valid_through:
        try:
            deadline_date = date.fromisoformat(valid_through)
        except ValueError:
            deadline_date = None
    if deadline_date and deadline_date < date.today():
        status = VacancyStatus.DEADLINE_PASSED
        evidence = f"JobPosting validThrough ({valid_through}) has passed."

    url = _text(job.get("url")) or page_url

    return Vacancy(
        title=title,
        employer=employer or employer_name,
        source=f"employer:{employer_name}",
        url=url,
        description=description,
        location=_location_text(job),
        qualification=_text(job.get("qualifications")) or _text(job.get("educationRequirements")),
        salary=_text(job.get("baseSalary")),
        entry_requirements=_text(job.get("qualifications")),
        application_deadline=valid_through,
        status=status,
        status_evidence=evidence,
        raw_source_data={"date_posted": date_posted, "employment_type": _text(job.get("employmentType"))},
    )


def fetch_from_page(name: str, url: str, config: dict) -> list[Vacancy]:
    rate = config.get("rate_limit", {})
    resp = get(url, timeout=rate.get("timeout_seconds", 20), delay_seconds=rate.get("delay_seconds", 2.0))
    if resp is None:
        logger.warning("employers: could not fetch %s (%s) - source unavailable this run", name, url)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")
    postings: list[Vacancy] = []
    for script in scripts:
        try:
            data = json.loads(script.string or "{}")
        except (json.JSONDecodeError, TypeError):
            continue
        for job in _iter_job_postings(data):
            v = _parse_job_posting(job, name, url)
            if v is None:
                continue
            # Match on the title only, not the full description: description
            # text can mention "apprenticeship" in passing (or in the
            # negative) without the posting actually being one.
            if any(t in v.title.lower() for t in APPRENTICESHIP_TERMS):
                postings.append(v)

    if not postings:
        logger.info(
            "employers: no JobPosting structured data (or no apprenticeship postings) found on %s (%s). "
            "This source only trusts machine-readable schema.org data, so nothing was invented from page text.",
            name, url,
        )
    return postings


def fetch(config: dict) -> list[Vacancy]:
    results: list[Vacancy] = []
    for employer in config.get("employers_seed", []):
        results.extend(fetch_from_page(employer["name"], employer["careers_url"], config))
    logger.info("employers: %d results across %d configured career pages", len(results), len(config.get("employers_seed", [])))
    return results
