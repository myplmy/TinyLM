"""Retain all existing safeguards and challenge the new narrow empty leaves."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v24 as policy
from scripts import p106b_hold_resolution_empty_structures_v1 as empty
from scripts import test_p106b_hold_resolution_policy_v22 as inherited


class ObservedSourceHolesAndEmptyLeaves(unittest.TestCase):
    intro = "가람은 대한민국의 배우이다.\n\n"

    def test_missing_actual_coefficient_and_condition_are_not_named_aliases(self):
        text = ("코시-오일러 방정식()은 선형 동차 상미분 방정식이다.\n"
                "여기서 은 주어진 계수들이다.\n여기서 에 따라 미분방정식의 해를 구할 수 있다.\n")
        value = policy.propose(dict(id="expanded_train:987654321", text=text, complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn(policy.ROLE_REASON, value["reasons"])
        self.assertEqual(len(policy.observed_formal_holes(text)), 2)
        self.assertIn("여기서 은 주어진 계수들이다.", value["candidate"])

    def test_actual_symbol_is_not_a_missing_role(self):
        self.assertEqual(policy.observed_formal_holes("여기서 a는 주어진 계수이다.\n여기서 x에 따라 방정식을 푼다.\n"), [])

    def test_quoted_and_code_demonstrations_do_not_lose_their_literals(self):
        fence = chr(96) * 3
        for raw in ["인용 예문은 다음과 같다.\n여기서 은 주어진 계수들이다.\n",
                    fence + "text\n여기서 은 주어진 계수들이다.\n" + fence + "\n"]:
            self.assertEqual(policy.observed_formal_holes(raw), [])
        code = 'import sys\nvalue = "여기서 은 주어진 계수들이다."\n'
        self.assertEqual(policy.observed_formal_holes(code), [])

    def test_empty_plot_has_actual_cast_as_next_sibling(self):
        raw = self.intro + "줄거리\n\n출연진\n홍길동 - 주인공\n"
        clean, changes = empty.clean_empty_structures(raw)
        self.assertEqual(clean, self.intro + "\n출연진\n홍길동 - 주인공\n")
        self.assertEqual([row["original"] for row in changes], ["줄거리\n"])

    def test_actual_plot_and_protected_code_between_headers_are_preserved(self):
        fence = chr(96) * 3
        for middle in ["두 사람이 재회한다.\n", fence + "text\n유효한 본문\n" + fence + "\n"]:
            raw = self.intro + "줄거리\n" + middle + "출연진\n홍길동\n"
            self.assertEqual(empty.clean_empty_structures(raw), (raw, []))

    def test_quoted_heading_and_contents_list_are_preserved(self):
        for prefix in ["인용 예문이다.\n", "목차\n"]:
            raw = self.intro + prefix + "줄거리\n출연진\n홍길동\n"
            self.assertEqual(empty.clean_empty_structures(raw), (raw, []))

    def test_missing_intro_never_proves_a_plot_leaf(self):
        raw = "줄거리\n출연진\n홍길동\n"
        self.assertEqual(empty.clean_empty_structures(raw), (raw, []))

    def test_single_missing_family_value_is_separate_from_real_names(self):
        raw = self.intro + "어머니:\n아버지: 홍길동\n"
        clean, changes = empty.clean_empty_structures(raw)
        self.assertEqual(clean, self.intro + "아버지: 홍길동\n")
        self.assertEqual([row["original"] for row in changes], ["어머니:\n"])

    def test_parent_group_and_hierarchical_children_are_not_empty_person_fields(self):
        for raw in [self.intro + "부모:\n아버지: 홍길동\n",
                    self.intro + "자녀:\n아들: 가람\n",
                    self.intro + "어머니:\n  이름: 누리\n"]:
            self.assertEqual(empty.clean_empty_structures(raw), (raw, []))

    def test_actual_siblings_with_populated_parent_value_survive(self):
        raw = self.intro + "어머니: 누리\n아버지: 홍길동\n"
        self.assertEqual(empty.clean_empty_structures(raw), (raw, []))

    def test_empty_family_title_cannot_cross_actual_html(self):
        raw = self.intro + "어머니:\n<div>실제 이름</div>\n아버지: 홍길동\n"
        self.assertEqual(empty.clean_empty_structures(raw), (raw, []))

    def test_credit_pointer_before_real_list_is_preserved(self):
        raw = self.intro + "참여\n이 목록은 Staff에서 발췌했다.\n홍길동: 작곡\n1998년 음반\n"
        self.assertEqual(empty.clean_empty_structures(raw), (raw, []))



class AliasScopeAndEnglishRoles(unittest.TestCase):
    def test_single_named_definition_retains_its_narrow_release(self):
        raw = "힐베르트 공간()은 완비 내적 공간이다." + chr(10)
        self.assertFalse(policy.unchecked_body_after_named_alias(raw))
        value = policy.propose(dict(id="expanded_train:987654321", text=raw, complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "EDIT")

    def test_a_named_definition_does_not_certify_any_following_formal_prose(self):
        raw = "힐베르트 공간()은 완비 내적 공간이다." + chr(10) + "정의와 증명은 다음과 같다."
        value = policy.propose(dict(id="expanded_train:987654321", text=raw, complete_eos=True, valid_utf8=True))
        self.assertEqual(value["decision"], "PENDING")
        self.assertIn(policy.ALIAS_BODY, value["reasons"])

    def test_complete_following_prose_still_requires_the_scoped_review(self):
        raw = "힐베르트 공간()은 완비 내적 공간이다." + chr(10) + "이는 독립적으로 완결된 설명이다."
        self.assertTrue(policy.unchecked_body_after_named_alias(raw))

    def test_actual_missing_english_data_and_coefficients_are_observed(self):
        raw = "Suppose that the data set consists of the points with ." + chr(10)
        raw += "Suppose it is quadratic, where , and are not yet known."
        self.assertEqual(len([r for r in policy.observed_formal_holes(raw) if r["reason"] == policy.ENGLISH_ROLE]), 2)
        self.assertIn(policy.ENGLISH_ROLE, policy.literal_holes(raw))

    def test_actual_english_symbols_and_protected_source_literals_remain(self):
        self.assertNotIn(policy.ENGLISH_ROLE, policy.literal_holes("The data points with x=3 are given."))
        fence = chr(96) * 3
        self.assertEqual(policy.observed_formal_holes(fence + "text" + chr(10) +
            "points with ." + chr(10) + fence), [])

if __name__ == "__main__":
    modules, pending = [], [inherited]
    while pending:
        module = pending.pop()
        if module in modules:
            continue
        modules.append(module)
        pending.extend(value for name in ["inherited", "local_inherited", "structure_tests", "preservation_tests"]
                       if (value := getattr(module, name, None)) is not None)
    classes = [ObservedSourceHolesAndEmptyLeaves, AliasScopeAndEnglishRoles]
    for module in modules:
        classes += [(inherited.inherited.RetainedStyleInsteadOfRenderedLoss if value.__name__ == "SourceValuePreservation" else value)
                    for value in vars(module).values() if isinstance(value, type)
                    and issubclass(value, unittest.TestCase) and value.__module__ == module.__name__]
    with ExitStack() as stack:
        for module in modules:
            if hasattr(module, "policy"):
                stack.enter_context(patch.object(module, "policy", policy))
        result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in dict.fromkeys(classes)))
    raise SystemExit(0 if result.wasSuccessful() else 1)
