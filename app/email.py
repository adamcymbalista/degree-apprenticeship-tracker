"""SMTP sending + HTML email rendering. stdlib smtplib/email only - no
templating engine needed for a handful of card-shaped emails.

Credentials come from environment variables only (never config.yaml, never
hardcoded): EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD,
EMAIL_FROM, EMAIL_TO. Works with Gmail SMTP (smtp.gmail.com:587) out of the
box; any STARTTLS SMTP provider works by changing EMAIL_HOST/EMAIL_PORT.
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.models import MatchCategory, Vacancy
from app.scoring import explain_match

logger = logging.getLogger("tracker.email")

CARD_STYLE = "border:1px solid #d9d9d9;border-radius:8px;padding:16px;margin-bottom:14px;background:#ffffff;"
CATEGORY_COLORS = {
    MatchCategory.EXCEPTIONAL_MATCH: "#1a7f37",
    MatchCategory.STRONG_MATCH: "#2563eb",
    MatchCategory.GOOD_MATCH: "#6b7280",
    MatchCategory.POSSIBLE_MATCH: "#9ca3af",
    MatchCategory.LOW_MATCH: "#9ca3af",
    MatchCategory.EXCLUDED: "#9ca3af",
}


class EmailConfigError(RuntimeError):
    pass


def _get_smtp_settings() -> dict:
    required = ["EMAIL_HOST", "EMAIL_PORT", "EMAIL_USERNAME", "EMAIL_PASSWORD", "EMAIL_FROM", "EMAIL_TO"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise EmailConfigError(f"Missing required environment variables: {', '.join(missing)}")
    return {k: os.environ[k] for k in required}


def send_email(subject: str, html_body: str) -> None:
    settings = _get_smtp_settings()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings["EMAIL_FROM"]
    msg["To"] = settings["EMAIL_TO"]
    msg.attach(MIMEText("This email requires HTML support to view.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    host, port = settings["EMAIL_HOST"], int(settings["EMAIL_PORT"])
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(settings["EMAIL_USERNAME"], settings["EMAIL_PASSWORD"])
        server.sendmail(settings["EMAIL_FROM"], settings["EMAIL_TO"].split(","), msg.as_string())
    logger.info("email sent: %s", subject)


def _vacancy_card(v: Vacancy, *, show_why: bool = True) -> str:
    color = CATEGORY_COLORS.get(v.match_category, "#6b7280")
    tags_html = " ".join(
        f'<span style="background:#eef2ff;color:#3730a3;border-radius:12px;padding:2px 8px;'
        f'font-size:12px;margin-right:4px;">{t}</span>' for t in v.tags
    )
    why = f'<p style="margin:8px 0 0;font-style:italic;color:#374151;">{explain_match(v)}</p>' if show_why else ""
    rows = [
        ("Employer", v.employer),
        ("Role", v.title),
        ("Degree", v.degree or v.qualification or "Unknown"),
        ("Location", v.location or "Unknown"),
        ("Start date", v.start_date or "Unknown"),
        ("Deadline", v.application_deadline or "Unknown"),
    ]
    if v.salary:
        rows.append(("Salary", v.salary))
    rows.append(("Source", v.source))

    rows_html = "".join(
        f'<tr><td style="padding:2px 8px 2px 0;color:#6b7280;font-size:13px;white-space:nowrap;">{label}</td>'
        f'<td style="padding:2px 0;font-size:13px;">{value}</td></tr>'
        for label, value in rows
    )

    return f"""
    <div style="{CARD_STYLE}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="color:{color};font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.04em;">
          {v.match_category.value.replace('_', ' ')} &middot; score {v.score}
        </span>
      </div>
      <table style="border-collapse:collapse;width:100%;">{rows_html}</table>
      <div style="margin-top:8px;">{tags_html}</div>
      {why}
      <p style="margin:10px 0 0;">
        <a href="{v.url}" style="color:#2563eb;font-weight:600;text-decoration:none;">View application &rarr;</a>
      </p>
    </div>
    """


def _wrap(title: str, intro: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#111827;">
  <div style="max-width:640px;margin:0 auto;padding:24px 16px;">
    <h1 style="font-size:20px;margin:0 0 4px;">{title}</h1>
    <p style="color:#4b5563;margin:0 0 20px;">{intro}</p>
    {body}
    <p style="color:#9ca3af;font-size:12px;margin-top:24px;">
      Degree Apprenticeship Tracker &middot; scores are computed by a transparent rule-based
      system (see app/scoring.py) - no data here is invented; anything the source didn't
      confirm is shown as "Unknown".
    </p>
  </div>
</body></html>"""


def render_weekly_email(sections: dict[str, list[Vacancy]], date_label: str) -> tuple[str, str]:
    subject = f"Degree Apprenticeship Weekly Update — {date_label}"
    body_parts = []
    any_content = False
    for section_name, vacancies in sections.items():
        if not vacancies:
            continue
        any_content = True
        cards = "".join(_vacancy_card(v) for v in vacancies)
        body_parts.append(
            f'<h2 style="font-size:15px;margin:24px 0 8px;border-bottom:2px solid #e5e7eb;padding-bottom:4px;">'
            f'{section_name} ({len(vacancies)})</h2>{cards}'
        )
    if not any_content:
        body_parts.append('<p style="color:#6b7280;">No relevant opportunities to report this week.</p>')
    body = "".join(body_parts)
    html = _wrap(
        f"Degree Apprenticeship Weekly Update — {date_label}",
        "A summary of London Level 6 degree apprenticeships matching your interests, covering the last 7 days.",
        body,
    )
    return subject, html


def render_emergency_email(vacancies: list[Vacancy]) -> tuple[str, str]:
    if len(vacancies) == 1:
        v = vacancies[0]
        subject = f"\U0001f6a8 NEW DEGREE APPRENTICESHIP OPEN — {v.employer} — {v.title}"
    else:
        subject = f"\U0001f6a8 {len(vacancies)} NEW DEGREE APPRENTICESHIPS OPEN TODAY"
    cards = "".join(_vacancy_card(v) for v in vacancies)
    body = f'<p style="font-weight:700;color:#b91c1c;">Opened today</p>{cards}'
    html = _wrap(subject, "One or more high-match London degree apprenticeships opened applications today.", body)
    return subject, html


def render_test_email() -> tuple[str, str]:
    subject = "Degree Apprenticeship Tracker — test email"
    html = _wrap(
        "Test email",
        "If you're reading this, SMTP is configured correctly for the Degree Apprenticeship Tracker.",
        '<p style="color:#374151;">No vacancy data was fetched - this is a connectivity check only.</p>',
    )
    return subject, html
