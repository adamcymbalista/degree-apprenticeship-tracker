"""Source: Queen Mary University of London degree apprenticeship pages.

QMUL's own pages are marketing/programme-info pages, not a JSON-LD vacancy
feed, so this reuses the same generic JobPosting scraper as employers.py -
if QMUL (or another university you add below) ever publishes structured
vacancy data, it'll be picked up automatically; otherwise it's logged as
"no structured data" rather than inventing a vacancy from prose.

Update `UNIVERSITY_PAGES` with any university degree-apprenticeship pages
you want tracked - add more universities the same way.
"""
from __future__ import annotations

from app.models import Vacancy
from app.sources.employers import fetch_from_page

UNIVERSITY_PAGES = [
    {"name": "Queen Mary University of London", "careers_url": "https://www.qmul.ac.uk/undergraduate/courses/degree-apprenticeships/"},
    {"name": "University of Greenwich", "careers_url": "https://www.gre.ac.uk/degree-apprenticeships"},
    {"name": "Open University", "careers_url": "https://www.open.ac.uk/business/apprenticeships"},
]


def fetch(config: dict) -> list[Vacancy]:
    results: list[Vacancy] = []
    for page in UNIVERSITY_PAGES:
        results.extend(fetch_from_page(page["name"], page["careers_url"], config))
    return results
