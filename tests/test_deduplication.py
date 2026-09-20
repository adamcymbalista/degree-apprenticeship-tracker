import unittest

from app.models import Vacancy
from app.deduplication import deduplicate, make_canonical_id


def make(**overrides) -> Vacancy:
    defaults = dict(
        title="Software Engineering Degree Apprentice",
        employer="ExampleCorp",
        source="findapprenticeship",
        url="https://findapprenticeship.example/1",
        start_date="1 September 2027",
    )
    defaults.update(overrides)
    return Vacancy(**defaults)


class TestDeduplication(unittest.TestCase):
    def test_same_vacancy_from_two_sources_merges_to_one(self):
        v1 = make(source="findapprenticeship", url="https://findapprenticeship.example/1", salary=None)
        v2 = make(source="employer:ExampleCorp", url="https://examplecorp.example/careers/1", salary="£24,000 a year")
        result = deduplicate([v1, v2])
        self.assertEqual(len(result), 1)
        # merge should have backfilled the missing field from the duplicate
        self.assertEqual(result[0].salary, "£24,000 a year")

    def test_distinct_vacancies_stay_distinct(self):
        v1 = make(title="Software Engineering Degree Apprentice")
        v2 = make(title="Cyber Security Degree Apprentice", employer="OtherCorp")
        result = deduplicate([v1, v2])
        self.assertEqual(len(result), 2)

    def test_same_employer_different_start_year_not_merged(self):
        v1 = make(start_date="1 September 2027")
        v2 = make(start_date="1 September 2026")
        result = deduplicate([v1, v2])
        self.assertEqual(len(result), 2)

    def test_canonical_id_prefers_source_id_when_available(self):
        v = make(source_id="2000012345")
        cid = make_canonical_id(v)
        self.assertIn("ref2000012345", cid)

    def test_canonical_id_stable_across_runs(self):
        v1 = make()
        v2 = make()
        self.assertEqual(make_canonical_id(v1), make_canonical_id(v2))

    def test_slightly_different_title_wording_still_matches(self):
        v1 = make(title="Software Engineer Degree Apprenticeship")
        v2 = make(title="Software Engineer  Degree  Apprenticeship ")
        result = deduplicate([v1, v2])
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
