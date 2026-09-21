import json
import os
import unittest
from datetime import date, timedelta

from app.models import VacancyStatus
from app.sources.apprentifinder import BASE_URL, _parse_item

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestApprentiFinderParsing(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIXTURES, "apprentifinder_opportunities.json"), encoding="utf-8") as f:
            self.items = json.load(f)

    def test_parses_london_level_6_listing_fully(self):
        v = _parse_item(self.items[0])
        self.assertEqual(v.title, "Software Engineering Degree Apprentice")
        self.assertEqual(v.employer, "Softworks Tech Ltd")
        self.assertEqual(v.location, "London")
        self.assertEqual(v.level, 6)
        self.assertEqual(v.subject, "Software Engineering")
        self.assertEqual(v.degree, "Queen Mary University of London")
        self.assertEqual(v.salary, "£24,000 a year")
        self.assertEqual(v.start_date, "01 September 2027")
        self.assertEqual(v.application_deadline, "30 November 2026")
        self.assertEqual(v.source_id, "aaaaaaaa-0000-0000-0000-000000000001")
        self.assertEqual(v.url, f"{BASE_URL}/browse?selected=aaaaaaaa-0000-0000-0000-000000000001")
        self.assertEqual(v.source, "apprentifinder")

    def test_level_4_listing_parsed_as_level_4_not_invented_as_6(self):
        v = _parse_item(self.items[2])
        self.assertEqual(v.level, 4)

    def test_open_status_has_evidence_from_active_deadline(self):
        v = _parse_item(self.items[0])
        self.assertEqual(v.status, VacancyStatus.OPEN)
        self.assertIsNotNone(v.status_evidence)
        self.assertIn("2026-11-30", v.status_evidence)

    def test_passed_deadline_marks_deadline_passed_not_open(self):
        v = _parse_item(self.items[3])
        self.assertEqual(v.status, VacancyStatus.DEADLINE_PASSED)

    def test_missing_deadline_still_open_from_live_listing_evidence(self):
        v = _parse_item(self.items[4])
        self.assertEqual(v.status, VacancyStatus.OPEN)
        self.assertIn("aaaaaaaa-0000-0000-0000-000000000005", v.status_evidence)

    def test_listing_missing_employer_skipped_not_invented(self):
        v = _parse_item(self.items[5])
        self.assertIsNone(v)

    def test_future_deadline_computed_relative_to_today_not_hardcoded(self):
        # sanity check the date-comparison logic itself, independent of the fixture's dates
        item = dict(self.items[0])
        item["applicationDeadline"] = (date.today() + timedelta(days=1)).isoformat() + "T23:59:59Z"
        v = _parse_item(item)
        self.assertEqual(v.status, VacancyStatus.OPEN)

        item["applicationDeadline"] = (date.today() - timedelta(days=1)).isoformat() + "T23:59:59Z"
        v = _parse_item(item)
        self.assertEqual(v.status, VacancyStatus.DEADLINE_PASSED)


if __name__ == "__main__":
    unittest.main()
