"""SQLite persistence layer. Plain sqlite3 + hand-written SQL - the schema is
small and stable enough that an ORM would be pure overhead (ponytail rung 3:
stdlib does it).

Tables: vacancies, employers, sources, alerts, runs.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

from app.models import MatchCategory, Vacancy, VacancyStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS employers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    last_run_at TEXT,
    last_success_at TEXT,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS vacancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_id TEXT UNIQUE NOT NULL,   -- dedup key, stable across sources
    title TEXT NOT NULL,
    employer TEXT NOT NULL,
    description TEXT,
    location TEXT,
    degree TEXT,
    qualification TEXT,
    level INTEGER,
    subject TEXT,
    start_date TEXT,
    application_open_date TEXT,
    application_deadline TEXT,
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT,
    salary TEXT,
    entry_requirements TEXT,
    keywords TEXT,              -- JSON list
    raw_source_data TEXT,       -- JSON blob, most-recently-seen source payload
    status TEXT NOT NULL DEFAULT 'UNKNOWN',
    status_evidence TEXT,
    status_changed_at TEXT,     -- when `status` last actually changed (drives weekly "newly opened" section)
    score INTEGER NOT NULL DEFAULT 0,
    match_category TEXT NOT NULL DEFAULT 'LOW_MATCH',
    score_reasons TEXT,         -- JSON list
    tags TEXT,                  -- JSON list
    discovered_at TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    emergency_alert_sent_at TEXT,
    included_in_weekly_at TEXT,
    baseline BOOLEAN NOT NULL DEFAULT 0   -- true if seen during the very first run
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vacancy_canonical_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,   -- EMERGENCY | WEEKLY
    sent_at TEXT NOT NULL,
    status_at_send TEXT,
    FOREIGN KEY (vacancy_canonical_id) REFERENCES vacancies(canonical_id)
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_type TEXT NOT NULL,   -- daily | weekly | dry-run | test-email
    started_at TEXT NOT NULL,
    finished_at TEXT,
    new_vacancies INTEGER DEFAULT 0,
    newly_opened INTEGER DEFAULT 0,
    emergency_alerts INTEGER DEFAULT 0,
    errors TEXT   -- JSON list of {source, error}
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def get_connection(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def is_first_run(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) AS n FROM vacancies").fetchone()
    return row["n"] == 0


def upsert_vacancy(conn: sqlite3.Connection, v: Vacancy, baseline: bool = False) -> tuple[Optional[sqlite3.Row], bool]:
    """Insert or update a vacancy keyed on canonical_id.

    Returns (previous_row_or_None, is_new).
    """
    existing = conn.execute(
        "SELECT * FROM vacancies WHERE canonical_id = ?", (v.canonical_id,)
    ).fetchone()

    status_val = v.status.value if isinstance(v.status, VacancyStatus) else v.status
    category_val = v.match_category.value if isinstance(v.match_category, MatchCategory) else v.match_category

    if existing is None:
        conn.execute(
            """INSERT INTO vacancies (
                canonical_id, title, employer, description, location, degree,
                qualification, level, subject, start_date, application_open_date,
                application_deadline, url, source, source_id, salary,
                entry_requirements, keywords, raw_source_data, status,
                status_evidence, status_changed_at, score, match_category, score_reasons, tags,
                discovered_at, last_seen, baseline
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                v.canonical_id, v.title, v.employer, v.description, v.location, v.degree,
                v.qualification, v.level, v.subject, v.start_date, v.application_open_date,
                v.application_deadline, v.url, v.source, v.source_id, v.salary,
                v.entry_requirements, json.dumps(v.keywords), json.dumps(v.raw_source_data),
                status_val, v.status_evidence, v.discovered_at, v.score, category_val,
                json.dumps(v.score_reasons), json.dumps(v.tags),
                v.discovered_at, v.last_seen, baseline,
            ),
        )
        return None, True

    status_changed = existing["status"] != status_val
    conn.execute(
        """UPDATE vacancies SET
            title=?, employer=?, description=?, location=?, degree=?, qualification=?,
            level=?, subject=?, start_date=?, application_open_date=?, application_deadline=?,
            url=?, source=?, source_id=?, salary=?, entry_requirements=?, keywords=?,
            raw_source_data=?, status=?, status_evidence=?,
            status_changed_at=CASE WHEN ? THEN ? ELSE status_changed_at END,
            score=?, match_category=?,
            score_reasons=?, tags=?, last_seen=?
        WHERE canonical_id=?""",
        (
            v.title, v.employer, v.description, v.location, v.degree, v.qualification,
            v.level, v.subject, v.start_date, v.application_open_date, v.application_deadline,
            v.url, v.source, v.source_id, v.salary, v.entry_requirements, json.dumps(v.keywords),
            json.dumps(v.raw_source_data), status_val, v.status_evidence,
            status_changed, v.last_seen,
            v.score, category_val,
            json.dumps(v.score_reasons), json.dumps(v.tags), v.last_seen,
            v.canonical_id,
        ),
    )
    return existing, False


def mark_emergency_sent(conn: sqlite3.Connection, canonical_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        "UPDATE vacancies SET emergency_alert_sent_at=? WHERE canonical_id=?",
        (now, canonical_id),
    )
    conn.execute(
        "INSERT INTO alerts (vacancy_canonical_id, alert_type, sent_at, status_at_send) "
        "VALUES (?, 'EMERGENCY', ?, (SELECT status FROM vacancies WHERE canonical_id=?))",
        (canonical_id, now, canonical_id),
    )


def mark_weekly_included(conn: sqlite3.Connection, canonical_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        "UPDATE vacancies SET included_in_weekly_at=? WHERE canonical_id=?",
        (now, canonical_id),
    )
    conn.execute(
        "INSERT INTO alerts (vacancy_canonical_id, alert_type, sent_at, status_at_send) "
        "VALUES (?, 'WEEKLY', ?, (SELECT status FROM vacancies WHERE canonical_id=?))",
        (canonical_id, now, canonical_id),
    )


def record_run(conn: sqlite3.Connection, run_type: str, started_at: str, finished_at: str,
                new_vacancies: int, newly_opened: int, emergency_alerts: int,
                errors: list[dict]) -> None:
    conn.execute(
        """INSERT INTO runs (run_type, started_at, finished_at, new_vacancies,
            newly_opened, emergency_alerts, errors) VALUES (?,?,?,?,?,?,?)""",
        (run_type, started_at, finished_at, new_vacancies, newly_opened,
         emergency_alerts, json.dumps(errors)),
    )


def record_source_result(conn: sqlite3.Connection, source_name: str, success: bool, error: Optional[str] = None) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute("INSERT OR IGNORE INTO sources (name) VALUES (?)", (source_name,))
    if success:
        conn.execute(
            "UPDATE sources SET last_run_at=?, last_success_at=?, last_error=NULL WHERE name=?",
            (now, now, source_name),
        )
    else:
        conn.execute(
            "UPDATE sources SET last_run_at=?, last_error=? WHERE name=?",
            (now, error, source_name),
        )


def last_weekly_run(conn: sqlite3.Connection) -> Optional[str]:
    row = conn.execute(
        "SELECT finished_at FROM runs WHERE run_type='weekly' ORDER BY finished_at DESC LIMIT 1"
    ).fetchone()
    return row["finished_at"] if row else None


def row_to_vacancy(row: sqlite3.Row) -> Vacancy:
    return Vacancy(
        title=row["title"], employer=row["employer"], source=row["source"], url=row["url"],
        description=row["description"], location=row["location"], degree=row["degree"],
        qualification=row["qualification"], level=row["level"], subject=row["subject"],
        start_date=row["start_date"], application_open_date=row["application_open_date"],
        application_deadline=row["application_deadline"], salary=row["salary"],
        entry_requirements=row["entry_requirements"], source_id=row["source_id"],
        keywords=json.loads(row["keywords"] or "[]"), raw_source_data=json.loads(row["raw_source_data"] or "{}"),
        status=VacancyStatus(row["status"]), status_evidence=row["status_evidence"],
        discovered_at=row["discovered_at"], last_seen=row["last_seen"],
        score=row["score"], match_category=MatchCategory(row["match_category"]),
        score_reasons=json.loads(row["score_reasons"] or "[]"), tags=json.loads(row["tags"] or "[]"),
        canonical_id=row["canonical_id"], dedup_key=row["canonical_id"],
    )
