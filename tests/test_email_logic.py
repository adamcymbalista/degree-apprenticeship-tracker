import os
import unittest
from unittest import mock

from app.alerts import select_emergency_candidates, group_weekly
from app.email import EmailConfigError, render_emergency_email, render_weekly_email, send_email
from app.models import MatchCategory, Vacancy, VacancyStatus
from app.scoring import score_vacancy
from tests.fixtures.sample_config import SAMPLE_CONFIG


def make_scored(**overrides) -> Vacancy:
    defaults = dict(
        title="Software Engineering Degree Apprentice",
        employer="ExampleCorp",
        source="findapprenticeship",
        url="https://example.com/1",
        location="London (EC1A 1AA)",
        qualification="Software engineer (degree) (level 6)",
        level=6,
        start_date="1 September 2027",
        status=VacancyStatus.OPEN,
    )
    defaults.update(overrides)
    v = Vacancy(**defaults)
    return score_vacancy(v, SAMPLE_CONFIG)


class TestEmergencySelection(unittest.TestCase):
    def test_newly_opened_high_score_selected(self):
        v = make_scored()
        selected = select_emergency_candidates([(v, VacancyStatus.CLOSED.value)], SAMPLE_CONFIG)
        self.assertEqual(selected, [v])

    def test_brand_new_and_open_selected(self):
        v = make_scored()
        selected = select_emergency_candidates([(v, None)], SAMPLE_CONFIG)
        self.assertEqual(selected, [v])

    def test_already_open_not_reselected_no_duplicate_alert(self):
        v = make_scored()
        selected = select_emergency_candidates([(v, VacancyStatus.OPEN.value)], SAMPLE_CONFIG)
        self.assertEqual(selected, [])

    def test_low_score_not_selected_even_if_newly_opened(self):
        v = make_scored(title="Business Administration Apprentice", qualification="Business admin (degree) (level 6)")
        selected = select_emergency_candidates([(v, VacancyStatus.CLOSED.value)], SAMPLE_CONFIG)
        self.assertEqual(selected, [])

    def test_reopened_after_closing_is_selected_again(self):
        v = make_scored()
        # simulates: opened -> alerted -> closed -> reopened
        selected = select_emergency_candidates([(v, VacancyStatus.CLOSED.value)], SAMPLE_CONFIG)
        self.assertEqual(selected, [v])

    def test_multiple_openings_same_day_combine_into_one_email(self):
        v1 = make_scored(employer="CorpA", url="https://example.com/a")
        v2 = make_scored(employer="CorpB", url="https://example.com/b")
        selected = select_emergency_candidates([(v1, None), (v2, None)], SAMPLE_CONFIG)
        self.assertEqual(len(selected), 2)
        subject, html = render_emergency_email(selected)
        self.assertIn("2", subject)
        self.assertIn("CorpA", html)
        self.assertIn("CorpB", html)


class TestWeeklyGrouping(unittest.TestCase):
    def test_high_match_open_goes_in_still_open_section(self):
        v = make_scored()
        sections = group_weekly([v], SAMPLE_CONFIG)
        self.assertIn(v, sections["STILL OPEN — HIGH MATCH"])

    def test_excluded_vacancy_appears_nowhere(self):
        v = make_scored(location="Manchester (M1 1AA)")
        sections = group_weekly([v], SAMPLE_CONFIG)
        self.assertTrue(all(v not in vs for vs in sections.values()))

    def test_2026_vacancy_not_mixed_into_high_match_sections(self):
        v = make_scored(start_date="1 September 2026")
        sections = group_weekly([v], SAMPLE_CONFIG)
        self.assertNotIn(v, sections["NEW HIGH-MATCH OPPORTUNITIES"])
        self.assertNotIn(v, sections["STILL OPEN — HIGH MATCH"])


class TestSmtpConfig(unittest.TestCase):
    def test_send_email_raises_clear_error_without_env_vars(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(EmailConfigError):
                send_email("subject", "<p>body</p>")


if __name__ == "__main__":
    unittest.main()
