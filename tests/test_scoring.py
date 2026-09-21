import unittest

from app.models import MatchCategory, Vacancy, VacancyStatus
from app.scoring import score_vacancy
from tests.fixtures.sample_config import SAMPLE_CONFIG


def make_vacancy(**overrides) -> Vacancy:
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
    return Vacancy(**defaults)


class TestScoring(unittest.TestCase):
    def test_london_scores_higher_than_non_london(self):
        london = score_vacancy(make_vacancy(), SAMPLE_CONFIG)
        outside = score_vacancy(make_vacancy(location="Manchester (M1 1AA)"), SAMPLE_CONFIG)
        self.assertGreater(london.score, outside.score)
        self.assertEqual(outside.match_category, MatchCategory.EXCLUDED)

    def test_level_6_beats_level_4(self):
        l6 = score_vacancy(make_vacancy(), SAMPLE_CONFIG)
        l4 = score_vacancy(make_vacancy(level=4, qualification="IT technician (level 4)"), SAMPLE_CONFIG)
        self.assertGreater(l6.score, l4.score)
        self.assertEqual(l4.match_category, MatchCategory.EXCLUDED)

    def test_2027_beats_2026(self):
        y2027 = score_vacancy(make_vacancy(), SAMPLE_CONFIG)
        y2026 = score_vacancy(make_vacancy(start_date="1 September 2026"), SAMPLE_CONFIG)
        self.assertGreater(y2027.score, y2026.score)

    def test_high_score_cs_london_2027(self):
        v = score_vacancy(make_vacancy(), SAMPLE_CONFIG)
        self.assertGreaterEqual(v.score, 70)
        self.assertIn(v.match_category, {MatchCategory.STRONG_MATCH, MatchCategory.EXCEPTIONAL_MATCH})

    def test_low_score_generic_business_role(self):
        v = score_vacancy(
            make_vacancy(
                title="Business Administration Degree Apprentice",
                qualification="Business administrator (degree) (level 6)",
            ),
            SAMPLE_CONFIG,
        )
        self.assertLess(v.score, 50)

    def test_finance_only_role_excluded_from_high_score(self):
        v = score_vacancy(
            make_vacancy(
                title="Investment Banking Degree Apprentice",
                qualification="Investment operations specialist (degree) (level 6)",
                description="Accounting and audit apprenticeship in our finance team.",
            ),
            SAMPLE_CONFIG,
        )
        self.assertLess(v.score, 50)

    def test_sport_plus_cs_scores_higher_than_cs_alone(self):
        plain = score_vacancy(make_vacancy(), SAMPLE_CONFIG)
        sport = score_vacancy(
            make_vacancy(
                title="Sports Data Engineer Degree Apprentice",
                description="Software engineering role building performance analytics tools for elite athletes.",
            ),
            SAMPLE_CONFIG,
        )
        self.assertGreater(sport.score, plain.score)
        self.assertIn("SPORT", sport.tags)

    def test_sport_mention_without_technical_content_not_tagged(self):
        v = score_vacancy(
            make_vacancy(
                title="Sports Ground Maintenance Apprentice",
                description="Maintaining pitches and sports facilities.",
                qualification="Groundsperson (level 6)",
            ),
            SAMPLE_CONFIG,
        )
        self.assertNotIn("SPORT", v.tags)

    def test_qmul_partner_scores_higher_than_otherwise_identical_role(self):
        plain = score_vacancy(make_vacancy(), SAMPLE_CONFIG)
        qmul = score_vacancy(make_vacancy(degree="Queen Mary University of London"), SAMPLE_CONFIG)
        self.assertGreater(qmul.score, plain.score)
        self.assertIn("QMUL_PARTNER", qmul.tags)

    def test_hard_exclusion_overrides_positive_signals(self):
        v = score_vacancy(
            make_vacancy(
                title="Software Engineering Degree Apprentice",
                location="Manchester (M1 1AA)",
            ),
            SAMPLE_CONFIG,
        )
        self.assertEqual(v.match_category, MatchCategory.EXCLUDED)
        self.assertLess(v.score, 0)


if __name__ == "__main__":
    unittest.main()
