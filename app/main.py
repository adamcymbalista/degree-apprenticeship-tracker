"""CLI entrypoint. Run with:

    python -m app.main --daily        # normal scan: detect changes, send emergency email if warranted
    python -m app.main --weekly       # force-send the weekly digest now
    python -m app.main --dry-run      # fetch + score, print results, touch nothing
    python -m app.main --test-email   # send a test email to check SMTP config
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timezone

from app import alerts, database as db, deduplication, email as email_mod, normalizer, scoring
from app.config import load_config
from app.models import MatchCategory, VacancyStatus
from app.sources import employers, findapprenticeship, qmul, ucas
from app.status import just_opened

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M",
)
logger = logging.getLogger("tracker.main")

DB_PATH = os.environ.get("TRACKER_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tracker.db"))

SOURCE_MODULES = [
    ("findapprenticeship", findapprenticeship.fetch),
    ("ucas", ucas.fetch),
    ("employers", employers.fetch),
    ("qmul", qmul.fetch),
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_all_sources(config: dict) -> tuple[list, list[dict]]:
    """Runs every source module; one source failing never aborts the others."""
    all_vacancies = []
    errors: list[dict] = []
    for name, fetch_fn in SOURCE_MODULES:
        try:
            results = fetch_fn(config)
            logger.info("%s: %d results", name, len(results))
            all_vacancies.extend(results)
        except Exception as exc:  # a source crashing must never crash the whole run
            logger.error("%s: source failed: %s", name, exc)
            errors.append({"source": name, "error": str(exc)})
    return all_vacancies, errors


def process(config: dict, raw_vacancies: list) -> list:
    """Normalise -> dedupe -> score. Shared by --dry-run and --daily so
    "what dry-run shows" and "what daily actually stores" can never drift apart.
    """
    normalised = normalizer.normalize_all(raw_vacancies)
    deduped = deduplication.deduplicate(normalised)
    for v in deduped:
        scoring.score_vacancy(v, config)
    return deduped


def cmd_dry_run(config: dict) -> None:
    raw, errors = fetch_all_sources(config)
    vacancies = process(config, raw)

    print(f"\nFetched {len(raw)} raw listings, {len(vacancies)} after deduplication.")
    if errors:
        print(f"{len(errors)} source(s) failed: {[e['source'] for e in errors]}")

    excluded = sum(1 for v in vacancies if v.match_category == MatchCategory.EXCLUDED)
    print(f"Excluded (non-London / below Level 6): {excluded}")
    print(f"Remaining candidates: {len(vacancies) - excluded}")

    ranked = sorted(
        [v for v in vacancies if v.match_category != MatchCategory.EXCLUDED],
        key=lambda v: v.score, reverse=True,
    )
    print("\nTop matches:")
    for i, v in enumerate(ranked[:20], 1):
        print(f"{i:2}. [{v.score:4}] {v.match_category.value:20} {v.employer} — {v.title} ({v.location})")
        print(f"     {v.url}")

    print("\nDry run complete - no data was written to the database and no emails were sent.")


def cmd_test_email() -> int:
    subject, html = email_mod.render_test_email()
    try:
        email_mod.send_email(subject, html)
    except email_mod.EmailConfigError as exc:
        print(f"Cannot send test email: {exc}")
        print("Set EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM, EMAIL_TO and try again.")
        return 1
    print(f"Test email sent: {subject}")
    return 0


def _mark_opened_this_week(conn, row) -> bool:
    if row["status"] != VacancyStatus.OPEN.value or not row["status_changed_at"]:
        return False
    try:
        changed = datetime.fromisoformat(row["status_changed_at"])
    except ValueError:
        return False
    now = datetime.now(changed.tzinfo) if changed.tzinfo else datetime.now()
    return (now - changed).days <= 7


def send_weekly(conn, config: dict) -> None:
    rows = conn.execute("SELECT * FROM vacancies").fetchall()
    vacancies = []
    for row in rows:
        v = db.row_to_vacancy(row)
        if _mark_opened_this_week(conn, row):
            v.raw_source_data["_opened_this_week"] = True
        vacancies.append(v)

    sections = alerts.group_weekly(vacancies, config)
    subject, html = email_mod.render_weekly_email(sections, date.today().strftime("%d %B %Y"))
    try:
        email_mod.send_email(subject, html)
    except email_mod.EmailConfigError as exc:
        logger.warning("Weekly email not sent: %s", exc)
        return
    for section_vacancies in sections.values():
        for v in section_vacancies:
            db.mark_weekly_included(conn, v.canonical_id)
    started = _utcnow()
    db.record_run(conn, "weekly", started, _utcnow(), 0, 0, 0, [])
    logger.info("Weekly email sent")


def maybe_send_weekly(conn, config: dict, *, force: bool) -> None:
    if not force:
        weekly_day = config.get("email", {}).get("weekly_day", "Monday")
        if date.today().strftime("%A") != weekly_day:
            logger.info("Weekly email not due")
            return
        last = db.last_weekly_run(conn)
        if last:
            last_date = datetime.fromisoformat(last).date()
            if (date.today() - last_date).days < 6:
                logger.info("Weekly email already sent this week")
                return
    send_weekly(conn, config)


def cmd_weekly(config: dict) -> None:
    with db.get_connection(DB_PATH) as conn:
        maybe_send_weekly(conn, config, force=True)


def cmd_daily(config: dict) -> None:
    started_at = _utcnow()
    logger.info("Starting scan")

    raw, errors = fetch_all_sources(config)
    vacancies = process(config, raw)
    logger.info("Total after dedup: %d", len(vacancies))

    with db.get_connection(DB_PATH) as conn:
        first_run = db.is_first_run(conn)
        scanned: list[tuple] = []
        new_count = 0
        opened_count = 0

        for v in vacancies:
            existing = conn.execute(
                "SELECT status FROM vacancies WHERE canonical_id = ?", (v.canonical_id,)
            ).fetchone()
            prev_status = existing["status"] if existing else None
            db.upsert_vacancy(conn, v, baseline=first_run)
            scanned.append((v, prev_status))
            if existing is None:
                new_count += 1
            if just_opened(prev_status, v.status):
                opened_count += 1

        logger.info("New vacancies: %d", new_count)
        logger.info("Newly opened: %d", opened_count)

        emergency_sent = 0
        if first_run:
            logger.info("First run: baseline of %d vacancies stored, no emergency emails sent.", len(vacancies))
        else:
            candidates = alerts.select_emergency_candidates(scanned, config)
            logger.info("High-priority alerts: %d", len(candidates))
            if candidates:
                subject, html = email_mod.render_emergency_email(candidates)
                try:
                    email_mod.send_email(subject, html)
                    for v in candidates:
                        db.mark_emergency_sent(conn, v.canonical_id)
                    emergency_sent = len(candidates)
                except email_mod.EmailConfigError as exc:
                    logger.warning("Emergency email not sent: %s", exc)

        db.record_run(conn, "daily", started_at, _utcnow(), new_count, opened_count, emergency_sent, errors)
        maybe_send_weekly(conn, config, force=False)

    logger.info("Scan complete")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Degree Apprenticeship Tracker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--daily", action="store_true", help="Run the normal daily scan")
    group.add_argument("--weekly", action="store_true", help="Force-send the weekly digest now")
    group.add_argument("--dry-run", action="store_true", help="Fetch + score, print results, write nothing")
    group.add_argument("--test-email", action="store_true", help="Send a test email to verify SMTP config")
    args = parser.parse_args(argv)

    config = load_config()

    if args.dry_run:
        cmd_dry_run(config)
    elif args.test_email:
        return cmd_test_email()
    elif args.weekly:
        cmd_weekly(config)
    elif args.daily:
        cmd_daily(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
