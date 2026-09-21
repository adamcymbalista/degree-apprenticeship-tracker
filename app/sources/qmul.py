"""Source: Queen Mary University of London degree apprenticeship pages.

QMUL's own pages are marketing/programme-info pages, not a JSON-LD vacancy
feed, so this reuses the same generic JobPosting scraper as employers.py -
if QMUL (or another university you add below) ever publishes structured
vacancy data, it'll be picked up automatically; otherwise it's logged as
"no structured data" rather than inventing a vacancy from prose.

Checked live (2026-09-21): the original QMUL URL here was simply wrong -
it 404s even in a real browser, and gov/enterprise-style bot protection
turned that into a 403 for plain HTTP requests, which is what showed up in
the logs. The correct page (qmul.ac.uk/degreeapprenticeships/, below) is
genuinely just prose about the programme - no application dates, no
JobPosting data, nothing this source could turn into a Vacancy even with a
working URL. QMUL doesn't publish vacancies itself; its partner employers
do, on their own sites or Find an Apprenticeship, with QMUL named only as
the training provider - which findapprenticeship.service.gov.uk's search
results don't expose (a "queen mary" search there returns 0 results; the
site indexes job titles/employers, not training-provider names). The
practical way to surface QMUL-partnered roles is apprentifinder.py, whose
feed includes a `university` field per listing - see the QMUL-partner
check in scoring.py.

Update `UNIVERSITY_PAGES` with any university degree-apprenticeship pages
you want tracked - add more universities the same way.
"""
from __future__ import annotations

from app.models import Vacancy
from app.sources.employers import fetch_from_page

UNIVERSITY_PAGES = [
    {"name": "Queen Mary University of London", "careers_url": "https://www.qmul.ac.uk/degreeapprenticeships/"},
    {"name": "University of Greenwich", "careers_url": "https://www.gre.ac.uk/degree-apprenticeships"},
    {"name": "Open University", "careers_url": "https://www.open.ac.uk/business/apprenticeships"},
]


def fetch(config: dict) -> list[Vacancy]:
    results: list[Vacancy] = []
    for page in UNIVERSITY_PAGES:
        results.extend(fetch_from_page(page["name"], page["careers_url"], config))
    return results
