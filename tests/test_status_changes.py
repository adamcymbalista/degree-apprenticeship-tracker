import unittest
from datetime import date, timedelta

from app.models import Vacancy, VacancyStatus
from app.status import detect_transition, infer_status_from_dates, just_opened, parse_date


class TestStatusTransitions(unittest.TestCase):
    def test_closed_to_open_detected(self):
        label = detect_transition(VacancyStatus.CLOSED.value, VacancyStatus.OPEN)
        self.assertEqual(label, "CLOSED -> OPEN")

    def test_not_yet_open_to_open_detected(self):
        label = detect_transition(VacancyStatus.NOT_YET_OPEN.value, VacancyStatus.OPEN)
        self.assertEqual(label, "NOT_YET_OPEN -> OPEN")

    def test_open_to_closed_detected(self):
        label = detect_transition(VacancyStatus.OPEN.value, VacancyStatus.CLOSED)
        self.assertEqual(label, "OPEN -> CLOSED")

    def test_no_change_returns_none(self):
        self.assertIsNone(detect_transition(VacancyStatus.OPEN.value, VacancyStatus.OPEN))

    def test_brand_new_vacancy_has_no_transition(self):
        self.assertIsNone(detect_transition(None, VacancyStatus.OPEN))

    def test_just_opened_true_for_brand_new_open_vacancy(self):
        self.assertTrue(just_opened(None, VacancyStatus.OPEN))

    def test_just_opened_true_for_closed_to_open(self):
        self.assertTrue(just_opened(VacancyStatus.CLOSED.value, VacancyStatus.OPEN))

    def test_just_opened_false_if_already_open(self):
        self.assertFalse(just_opened(VacancyStatus.OPEN.value, VacancyStatus.OPEN))

    def test_just_opened_false_if_still_closed(self):
        self.assertFalse(just_opened(VacancyStatus.CLOSED.value, VacancyStatus.CLOSED))

    def test_infer_status_deadline_passed(self):
        v = Vacancy(
            title="t", employer="e", source="s", url="u",
            application_deadline=(date.today() - timedelta(days=1)).strftime("%d %B %Y"),
        )
        self.assertEqual(infer_status_from_dates(v), VacancyStatus.DEADLINE_PASSED)

    def test_infer_status_not_yet_open(self):
        v = Vacancy(
            title="t", employer="e", source="s", url="u",
            application_open_date=(date.today() + timedelta(days=10)).strftime("%d %B %Y"),
        )
        self.assertEqual(infer_status_from_dates(v), VacancyStatus.NOT_YET_OPEN)

    def test_infer_status_stays_unknown_without_evidence(self):
        v = Vacancy(title="t", employer="e", source="s", url="u")
        self.assertEqual(infer_status_from_dates(v), VacancyStatus.UNKNOWN)

    def test_source_provided_status_is_not_overridden(self):
        v = Vacancy(title="t", employer="e", source="s", url="u", status=VacancyStatus.OPEN)
        self.assertEqual(infer_status_from_dates(v), VacancyStatus.OPEN)

    def test_parse_date_handles_multiple_formats(self):
        self.assertEqual(parse_date("19 October 2026"), date(2026, 10, 19))
        self.assertEqual(parse_date("2026-10-19"), date(2026, 10, 19))
        self.assertIsNone(parse_date(None))
        self.assertIsNone(parse_date("not a date"))


if __name__ == "__main__":
    unittest.main()
