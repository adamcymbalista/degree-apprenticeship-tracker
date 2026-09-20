"""Source: UCAS apprenticeship search (https://www.ucas.com/explore/search/apprenticeships).

NOT currently automatable, and this module says so rather than faking data:
UCAS's search results are loaded client-side from a private Algolia index
(the page ships an empty app shell; results only appear after JavaScript
runs - confirmed by fetching the search URL and finding no listings in the
server-rendered HTML). Per spec ("if a website cannot be reliably scraped,
do not fake it" / "if a website blocks automated requests, mark that source
as unavailable and use another source"), we do not scrape this with a
headless browser (that would mean evading their intended delivery
mechanism, which the spec also tells us not to do) - Find an Apprenticeship
already covers the same official vacancies.

If UCAS ever exposes a public API or documents their Algolia search-only
key for third-party use, swap the body of fetch() for a real request - the
Vacancy shape below is what to return.
"""
from __future__ import annotations

import logging

from app.models import Vacancy

logger = logging.getLogger("tracker.sources.ucas")


def fetch(config: dict) -> list[Vacancy]:
    logger.info(
        "ucas: skipped - UCAS apprenticeship search is a client-side JavaScript app "
        "with no public API, so it cannot be reliably scraped with plain HTTP requests. "
        "See app/sources/ucas.py docstring."
    )
    return []
