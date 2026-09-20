"""Dedup: the same apprenticeship can appear on Find an Apprenticeship, UCAS
and the employer site. We build one canonical_id per real-world vacancy.

Strategy:
1. If a source gives an official reference id, use "source_id:{id}" style keys
   don't work across sources (each source has its own id namespace), so those
   only help within a single source's own re-runs (stability across days).
2. Across sources, fuzzy-match on (employer, title, location, start_date) using
   stdlib difflib - no need for a fuzzy-matching dependency for a few hundred
   rows a day.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.models import Vacancy

TITLE_MATCH_THRESHOLD = 0.82


YEAR_RE = re.compile(r"(20\d{2})")


def _norm(text: str | None) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _year(start_date: str | None) -> str:
    m = YEAR_RE.search(start_date or "")
    return m.group(1) if m else ""


def _norm_key(v: Vacancy) -> str:
    return "|".join([
        _norm(v.employer),
        _norm(v.title),
        _year(v.start_date),
    ])


def make_canonical_id(v: Vacancy) -> str:
    """Deterministic id used as the primary key. Same formula every run so a
    vacancy re-scraped tomorrow maps to the same row (source_id preferred
    when available since it's exact; falls back to a normalised fingerprint).
    """
    if v.source_id:
        return f"{_norm(v.employer)}::{_norm(v.title)}::ref{v.source_id}"
    return _norm_key(v)


def find_duplicate(v: Vacancy, existing: list[Vacancy]) -> Vacancy | None:
    """Fuzzy-match v against already-collected vacancies from *other* sources
    in this run. Returns the existing Vacancy it duplicates, or None.
    """
    v_employer = _norm(v.employer)
    v_title = _norm(v.title)
    v_year = _year(v.start_date)

    for other in existing:
        if _norm(other.employer) != v_employer:
            continue
        other_year = _year(other.start_date)
        if v_year and other_year and v_year != other_year:
            continue
        ratio = SequenceMatcher(None, v_title, _norm(other.title)).ratio()
        if ratio >= TITLE_MATCH_THRESHOLD:
            return other
    return None


def merge_duplicate(primary: Vacancy, duplicate: Vacancy) -> Vacancy:
    """Prefer the primary (first-seen / more authoritative source) but fill
    in any fields it's missing from the duplicate, and keep both source URLs
    referenced via raw_source_data for traceability.
    """
    for f in ("description", "salary", "entry_requirements", "application_deadline",
              "application_open_date", "start_date", "degree", "qualification",
              "level", "subject", "location"):
        if getattr(primary, f) in (None, "") and getattr(duplicate, f) not in (None, ""):
            setattr(primary, f, getattr(duplicate, f))
    primary.raw_source_data.setdefault("also_seen_on", []).append(
        {"source": duplicate.source, "url": duplicate.url}
    )
    return primary


def deduplicate(vacancies: list[Vacancy]) -> list[Vacancy]:
    result: list[Vacancy] = []
    for v in vacancies:
        dup = find_duplicate(v, result)
        if dup is None:
            result.append(v)
        else:
            merge_duplicate(dup, v)
    for v in result:
        v.canonical_id = make_canonical_id(v)
    return result
