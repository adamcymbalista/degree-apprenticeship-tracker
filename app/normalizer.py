"""Light post-processing shared by every source's output before scoring:
- infer `level` from qualification text if a source didn't set it directly
- infer `degree`/`subject` label from title+qualification for scoring/email use
- fall back status via status.infer_status_from_dates when a source left it UNKNOWN
Sources already avoid inventing data; this only fills fields from data the
vacancy itself already carries (never from guesswork about facts we don't have).
"""
from __future__ import annotations

import re

from app.models import Vacancy
from app.status import infer_status_from_dates

LEVEL_RE = re.compile(r"level\s*(\d)", re.IGNORECASE)
DEGREE_HINTS = ["bsc", "beng", "degree", "bachelor"]


def normalize(v: Vacancy) -> Vacancy:
    if v.level is None:
        haystack = " ".join(filter(None, [v.qualification, v.degree, v.description]))
        m = LEVEL_RE.search(haystack)
        if m:
            v.level = int(m.group(1))

    if v.subject is None:
        v.subject = v.qualification or v.degree

    if v.degree is None and v.qualification:
        haystack = v.qualification.lower()
        if any(h in haystack for h in DEGREE_HINTS) or (v.level and v.level >= 6):
            v.degree = v.qualification

    v.status = infer_status_from_dates(v)
    return v


def normalize_all(vacancies: list[Vacancy]) -> list[Vacancy]:
    return [normalize(v) for v in vacancies]
