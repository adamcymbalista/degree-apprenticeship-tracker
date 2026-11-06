import os
import unittest

from bs4 import BeautifulSoup

from app.models import VacancyStatus
from app.sources.employers import fetch_from_page
from app.sources.findapprenticeship import BASE_URL, REFERENCE_RE, _parse_listing

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestFindApprenticeshipParsing(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIXTURES, "findapprenticeship_search.html"), encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        self.anchors = [a for a in soup.find_all("a", href=True) if REFERENCE_RE.search(a["href"])]

    def test_finds_all_listings(self):
        self.assertEqual(len(self.anchors), 3)

    def test_parses_degree_level_6_listing_fully(self):
        v = _parse_listing(self.anchors[0], BASE_URL)
        self.assertEqual(v.title, "Software Engineering Degree Apprentice")
        self.assertEqual(v.employer, "Softworks Tech Ltd")
        self.assertEqual(v.location, "London (EC2A 4NE)")
        self.assertEqual(v.level, 6)
        self.assertEqual(v.salary, "£24,000 a year")
        self.assertEqual(v.start_date, "1 September 2027")
        self.assertEqual(v.application_deadline, "19 October 2099")
        self.assertEqual(v.source_id, "VAC2000099001")
        self.assertEqual(v.url, f"{BASE_URL}/apprenticeship/VAC2000099001")

    def test_parses_level_3_listing_as_level_3_not_invented_as_6(self):
        v = _parse_listing(self.anchors[1], BASE_URL)
        self.assertEqual(v.level, 3)

    def test_location_with_commas_and_building_name_still_parsed(self):
        # real-world address format confirmed against the live site's HTML
        v = _parse_listing(self.anchors[1], BASE_URL)
        self.assertEqual(v.location, "e-Innovation Centre, University of Wolverhampton, Telford (TF2 9FT)")
        self.assertEqual(v.employer, "Countyshire Council")

    def test_sport_data_listing_location_outside_central_london_still_captured(self):
        v = _parse_listing(self.anchors[2], BASE_URL)
        self.assertIn("Greater London", v.location)
        self.assertEqual(v.employer, "Elite Sports Data Ltd")

    def test_open_status_has_evidence_not_guessed(self):
        v = _parse_listing(self.anchors[0], BASE_URL)
        self.assertEqual(v.status, VacancyStatus.OPEN)
        self.assertIsNotNone(v.status_evidence)
        self.assertIn("VAC2000099001", v.status_evidence)

    def test_malformed_anchor_without_reference_id_ignored(self):
        soup = BeautifulSoup('<a href="/apprenticeships?pageNumber=2">Next</a>', "html.parser")
        anchor = soup.find("a")
        self.assertIsNone(REFERENCE_RE.search(anchor["href"]))


class TestEmployerJsonLdParsing(unittest.TestCase):
    def test_extracts_apprenticeship_job_posting_and_skips_non_apprenticeship(self):
        with open(os.path.join(FIXTURES, "employer_careers_page.html"), encoding="utf-8") as f:
            html = f.read()

        class FakeResponse:
            text = html

        from unittest import mock
        with mock.patch("app.sources.employers.get", return_value=FakeResponse()):
            results = fetch_from_page("SecureGov Ltd", "https://securegov.example/careers", {"rate_limit": {}})

        self.assertEqual(len(results), 1)  # the warehouse posting must be filtered out
        v = results[0]
        self.assertEqual(v.title, "Cyber Security Degree Apprentice")
        self.assertEqual(v.employer, "SecureGov Ltd")
        self.assertIn("London", v.location)
        self.assertEqual(v.application_deadline, "2099-01-15")
        self.assertEqual(v.status, VacancyStatus.OPEN)
        self.assertNotIn("<p>", v.description)  # HTML stripped from JSON-LD description


if __name__ == "__main__":
    unittest.main()
