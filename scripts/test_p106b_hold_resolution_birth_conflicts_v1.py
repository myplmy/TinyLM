"""Semantic counterexamples for source-only birth-field quarantine."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import p106b_hold_resolution_birth_conflicts_v1 as policy


def biography(life="1977년 3월 19일 ~ ", category="1978년 출생", middle="출연작은 2001년에 발표되었다."):
    return ("홍길동(" + life + ")은 대한민국의 배우이다." + chr(10) * 2 + middle + chr(10) * 2
            + category + chr(10) + "살아있는 사람" + chr(10) + "대한민국의 배우" + chr(10))


class BirthFieldTests(unittest.TestCase):
    def test_conflicting_years_are_both_quarantined(self):
        source = biography()
        result = policy.prove(source)
        self.assertIsNotNone(result)
        self.assertIn("홍길동(3월 19일 ~ )", result["candidate"])
        self.assertIn("2001년에", result["candidate"])
        self.assertNotIn("1977년", result["candidate"])
        self.assertNotIn("1978년", result["candidate"])
        self.assertEqual(result["proof"]["birth_year_selected"], None)
        self.assertFalse(result["proof"]["age_recomputed"])

    def test_coordinate_proof_reconstructs_input_without_guessing(self):
        source = biography()
        result = policy.prove(source)
        clean = source
        for change in reversed(result["changes"]):
            lo, hi = change["prepared_candidate_characters"]
            self.assertEqual(source[lo:hi], change["original"])
            clean = clean[:lo] + clean[hi:]
        self.assertEqual(clean, result["candidate"])

    def test_full_death_date_and_career_numbers_are_unchanged(self):
        source = biography("1900년 1월 2일 ~ 1980년 4월 5일", "1901년 출생", "1980년에 작품 12개를 발표했다.")
        result = policy.prove(source)
        self.assertIsNotNone(result)
        self.assertIn("1월 2일 ~ 1980년 4월 5일", result["candidate"])
        self.assertIn("1980년에 작품 12개", result["candidate"])

    def test_matching_years_are_never_deleted(self):
        self.assertIsNone(policy.prove(biography(category="1977년 출생")))

    def test_birth_year_only_cannot_borrow_full_death_date(self):
        self.assertIsNone(policy.prove(biography("1900년 ~ 1980년 4월 5일", "1901년 출생")))

    def test_tenure_date_is_not_a_birth(self):
        self.assertIsNone(policy.prove(biography("재임: 1977년 3월 19일 ~ 1980년 4월 5일")))

    def test_multiple_categories_do_not_choose_one(self):
        self.assertIsNone(policy.prove(biography(category="1978년 출생" + chr(10) + "1979년 출생")))

    def test_uncertainty_and_calendar_are_not_erased(self):
        for value in ["1977년 3월 19일경 ~ ", "양력, 1977년 3월 19일 ~ ", "1977년 3월 19일 또는 20일 ~ "]:
            with self.subTest(value=value):
                self.assertIsNone(policy.prove(biography(value)))

    def test_birth_discussion_or_age_arithmetic_needs_reading(self):
        for middle in ["출생 연도는 1977년으로도 기록된다.", "그는 2000년에 23세가 되었다.", "그의 생일은 3월 19일이다."]:
            with self.subTest(middle=middle):
                self.assertIsNone(policy.prove(biography(middle=middle)))

    def test_unrelated_person_birth_claim_needs_reading(self):
        self.assertIsNone(policy.prove(biography(middle="아버지는 1950년에 태어났다.")))

    def test_code_and_quotation_remain_literal(self):
        source = biography()
        for value in ["> " + source, '"' + source, "```text" + chr(10) + source + "```"]:
            with self.subTest(value=value[:8]):
                self.assertIsNone(policy.prove(value))

    def test_invalid_or_multiple_dates_are_not_repaired(self):
        for life in ["1977년 13월 19일 ~ ", "1977년 2월 30일 ~ ", "1977년 3월 19일, 1978년 4월 1일 ~ "]:
            with self.subTest(life=life):
                self.assertIsNone(policy.prove(biography(life)))

    def test_category_without_metadata_boundary_is_not_enough(self):
        source = biography().replace(chr(10) * 2 + "1978년 출생", chr(10) + "1978년 출생")
        self.assertIsNone(policy.prove(source))


if __name__ == "__main__":
    unittest.main()
