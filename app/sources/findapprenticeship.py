"""Source: https://www.findapprenticeship.service.gov.uk/

This is the primary, most reliable source (official DfE site, GOV.UK design
system, stable HTML). No public search API is available without registering
an employer/training-provider account (see README "Known limitations"), so
we do a polite HTML scrape of the public search results pages.

Resilience strategy (per spec: "robust against websites changing HTML
structure"):
  - We do NOT depend on CSS class names, which GOV.UK/DfE change more often
    than the page layout. Instead we anchor on the one thing that's part of
    the site's URL contract: result links matching
    /apprenticeship/reference/<digits>. Everything else is extracted by
    regex over the surrounding block's *text*, matching the field labels
    ("Training course:", "Wage:", "Closes"/"Closing date", "Start date",
    "Posted") that the service displays to end users - those change far less
    often than markup, and a label rename just means one listing fails to
    parse (logged) rather than the whole source crashing.
  - Any listing we can't confidently parse a field from is left as None /
    UNKNOWN rather than guessed.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.http_client import get
from app.models import Vacancy, VacancyStatus

logger = logging.getLogger("tracker.sources.findapprenticeship")

BASE_URL = "https://www.findapprenticeship.service.gov.uk"
SEARCH_PATH = "/apprenticeships"
REFERENCE_RE = re.compile(r"/apprenticeship/reference/(\d+)")

LEVEL_RE = re.compile(r"level\s*(\d)", re.IGNORECASE)
WAGE_RE = re.compile(r"£[\d,]+(?:\.\d+)?\s*(?:a year|per year|an hour|per hour|a week)?", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{1,2}\s+\w+\s+\d{4})")
TRAINING_COURSE_RE = re.compile(r"training course:?\s*(.+)$", re.IGNORECASE)
LOCATION_LINE_RE = re.compile(r"^[A-Za-z .'-]+\([A-Za-z0-9 ]+\)$")
LABEL_PREFIXES = ("distance", "start date", "training course", "wage", "clos", "posted")
MAX_PAGES = 15  # safety cap so a malformed "results found" count can't loop forever


def _date_on_line_starting(lines: list[str], prefix: str) -> str | None:
    """First dd Month yyyy date found on the line that starts with `prefix`
    (case-insensitive) - dates are often wrapped in "in N days (...)" or a
    day-of-week, so we search the whole line rather than anchoring right
    after the label.
    """
    for line in lines:
        if line.lower().startswith(prefix):
            m = DATE_RE.search(line)
            if m:
                return m.group(1)
    return None


def _parse_uk_date(text: str | None) -> date | None:
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%d %B %Y").date()
    except ValueError:
        try:
            return datetime.strptime(text.strip(), "%d %b %Y").date()
        except ValueError:
            return None


def _block_lines(anchor) -> list[str]:
    """Walk up from the reference link to the smallest ancestor block that
    contains this result's field labels, so we don't pull in neighbouring
    listings' text, then return its text as one line per child element
    (using "\n" as the get_text separator keeps <p>/<li> boundaries intact,
    which is what lets us tell "employer" and "location" apart positionally).
    """
    node = anchor
    for _ in range(6):
        if node.parent is None:
            break
        node = node.parent
        text = node.get_text("\n", strip=True)
        if "Distance" in text or "Wage" in text or "Training course" in text:
            return [line.strip() for line in text.split("\n") if line.strip()]
    return [line.strip() for line in node.get_text("\n", strip=True).split("\n") if line.strip()]


def _parse_listing(anchor, base_url: str) -> Vacancy | None:
    href = anchor.get("href", "")
    match = REFERENCE_RE.search(href)
    if not match:
        return None
    reference_id = match.group(1)
    title = anchor.get_text(strip=True)
    if not title:
        return None

    url = href if href.startswith("http") else base_url + href
    lines = _block_lines(anchor)
    block_text = " ".join(lines)

    # Employer/location: these are the free-text lines that come after the
    # title and before the first labelled field ("Distance:", "Wage:", ...).
    # GOV.UK's own listings render employer then location in that order, and
    # a location line always ends in "(POSTCODE)" - we use that shape to
    # split the two rather than assuming fixed line positions.
    free_lines = []
    started = False
    for line in lines:
        if not started:
            if line == title:
                started = True
            continue
        if line.lower().startswith(LABEL_PREFIXES):
            break
        free_lines.append(line)

    employer = None
    location = None
    for line in free_lines:
        if LOCATION_LINE_RE.match(line):
            location = line
        elif employer is None:
            employer = line
    if employer is None and free_lines:
        employer = free_lines[0]

    level_match = LEVEL_RE.search(block_text)
    level = int(level_match.group(1)) if level_match else None

    qualification = None
    for line in lines:
        course_match = TRAINING_COURSE_RE.match(line)
        if course_match:
            qualification = course_match.group(1).strip(" -–")
            break

    wage_match = WAGE_RE.search(block_text)
    start_date = _date_on_line_starting(lines, "start date")
    closing_date_text = _date_on_line_starting(lines, "clos")
    posted_date = _date_on_line_starting(lines, "posted")

    deadline_date = _parse_uk_date(closing_date_text) if closing_date_text else None
    status = VacancyStatus.UNKNOWN
    evidence = None
    if deadline_date:
        if deadline_date >= date.today():
            status = VacancyStatus.OPEN
            evidence = (
                f"Listed as a live vacancy on Find an Apprenticeship "
                f"(reference {reference_id}) with an active closing date of {deadline_date.isoformat()}."
            )
        else:
            status = VacancyStatus.DEADLINE_PASSED
            evidence = f"Closing date {deadline_date.isoformat()} has passed."
    else:
        # No parseable closing date, but the vacancy is still listed on the
        # live public search (closed adverts are removed from this search by
        # the service) - treat that listing itself as evidence of OPEN.
        status = VacancyStatus.OPEN
        evidence = f"Listed as an active vacancy on Find an Apprenticeship (reference {reference_id})."

    return Vacancy(
        title=title,
        employer=employer or "Unknown employer",
        source="findapprenticeship",
        url=url,
        location=location,
        qualification=qualification,
        level=level,
        start_date=start_date,
        application_deadline=closing_date_text,
        salary=wage_match.group(0) if wage_match else None,
        source_id=reference_id,
        status=status,
        status_evidence=evidence,
        raw_source_data={"posted": posted_date, "block_text": block_text[:500]},
    )


def fetch(config: dict, *, keywords: list[str] | None = None, max_pages: int = 5) -> list[Vacancy]:
    """Search findapprenticeship.service.gov.uk once per keyword in `keywords`
    (default: the configured subject list), London + "commutable" distance,
    and return every parsed listing. Duplicate reference ids across keyword
    searches are dropped.
    """
    rate = config.get("rate_limit", {})
    delay = rate.get("delay_seconds", 2.0)
    timeout = rate.get("timeout_seconds", 20)

    terms = keywords or config.get("subjects", ["software engineering", "computer science"])
    seen_refs: set[str] = set()
    results: list[Vacancy] = []

    for term in terms:
        for page in range(1, max_pages + 1):
            params = {
                "searchTerm": term,
                "location": "London",
                "distance": "all",
                "sort": "AgeDesc",
                "pageNumber": page,
            }
            resp = get(BASE_URL + SEARCH_PATH, params=params, timeout=timeout, delay_seconds=delay)
            if resp is None:
                logger.warning("findapprenticeship: request failed for term=%r page=%d, stopping this term", term, page)
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            anchors = [a for a in soup.find_all("a", href=True) if REFERENCE_RE.search(a["href"])]
            if not anchors:
                break

            page_new = 0
            for anchor in anchors:
                ref_match = REFERENCE_RE.search(anchor["href"])
                ref_id = ref_match.group(1)
                if ref_id in seen_refs:
                    continue
                try:
                    vacancy = _parse_listing(anchor, BASE_URL)
                except Exception as exc:  # a single malformed listing must never kill the source
                    logger.warning("findapprenticeship: failed to parse a listing: %s", exc)
                    continue
                if vacancy is None:
                    continue
                seen_refs.add(ref_id)
                results.append(vacancy)
                page_new += 1

            if page_new == 0 or page >= MAX_PAGES:
                break

    logger.info("findapprenticeship: %d results", len(results))
    return results
