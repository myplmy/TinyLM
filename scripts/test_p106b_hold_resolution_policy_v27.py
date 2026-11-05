"""Reuse the original policy regressions and challenge declared-list proofs."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v27 as policy
from scripts import p106b_hold_resolution_disambiguation_v1 as lists
from scripts import test_p106b_hold_resolution_policy_v26 as inherited26


class DeclaredListSourcePreservation(unittest.TestCase):
    def result(self, text, **extra):
        return policy.propose(dict(id='expanded_train:987654321', text=text,
            complete_eos=True, valid_utf8=True, **extra))

    def test_real_named_people_header_and_filled_dates(self):
        raw = '페랭()은 다음 사람을 가리킨다.\n\n가람(, 1870년 ~ 1942년)은 프랑스의 물리학자이다.\n\n같이 보기\n'
        prepared, proof = lists.source_named_aliases(raw)
        self.assertEqual(prepared, raw.replace('페랭()', '페랭').replace('(, 1870년', '(1870년'))
        self.assertTrue(proof)
        value = self.result(raw)
        self.assertEqual(value['decision'], 'EDIT')
        self.assertIn('가람(1870년 ~ 1942년)', value['text'])
        self.assertTrue(policy.ordered_deletion(raw, value['text']))

    def test_bare_lifespan_keeps_endpoint_and_unknown_death(self):
        raw = '마이어는 다음 뜻으로 쓰인다.\n\n인명\n가람(, 1904~2005): 독일의 물리학자\n누리(, 1954~): 미국의 제작자\n상표\n가람(): 미국의 슈퍼마켓 체인\n'
        clean, proof = lists.source_named_aliases(raw)
        self.assertIn('가람(1904~2005):', clean)
        self.assertIn('누리(1954~):', clean)
        self.assertIn('가람: 미국의 슈퍼마켓', clean)
        self.assertTrue(any(row['reason'] == 'DECLARED_NAME_LIST_EMPTY_ALIAS_BEFORE_LITERAL_LIFESPAN' for row in proof))
        value = self.result(raw)
        self.assertEqual(value['decision'], 'EDIT')
        self.assertNotIn('2026', value['text'])

    def test_filled_foreign_names_are_literal(self):
        raw = '페랭은 다음 사람을 가리킨다.\n\n가람(Jean Perrin, 1870년 ~ 1942년)은 물리학자이다.\n'
        self.assertEqual(lists.source_named_aliases(raw), (raw, []))

    def test_no_declaration_and_regular_university_article_stay_outside_extension(self):
        for raw in ['가람(, 1904~2005): 물리학자\n',
                    '가람 대학()은 일본의 사립 대학이다.\n가람(): 분교\n']:
            self.assertEqual(lists.source_named_aliases(raw), (raw, []))

    def test_formula_function_and_value_subject_are_not_name_list_proofs(self):
        for name in ['함수', '기호', '인구', '계수', '연산자']:
            raw = name + '()는 다음 뜻으로 쓰인다.\n가람(): 예시\n'
            self.assertEqual(lists.source_named_aliases(raw), (raw, []))

    def test_actual_numeric_tuple_missing_birth_and_measured_value_are_not_filled(self):
        raw = '마이어는 다음 뜻으로 쓰인다.\n\n가람(, ~2005): 물리학자\n인구(): 도시의 인구\n좌표(, 3): 수치 예제\n'
        clean, _ = lists.source_named_aliases(raw)
        for literal in ['가람(, ~2005)', '인구()', '좌표(, 3)']:
            self.assertIn(literal, clean)
        self.assertEqual(self.result(raw)['decision'], 'PENDING')

    def test_complete_source_code_and_quoted_literals_survive(self):
        fence = chr(96) * 3
        for body in [fence + 'python\ndef 가람():\n    return ()\n' + fence + '\n',
                     '> 가람(): 빈 괄호의 예시\n',
                     '가람(): 함수 호출의 예시\n']:
            raw = '마이어는 다음 뜻으로 쓰인다.\n\n' + body
            self.assertEqual(lists.source_named_aliases(raw), (raw, []))

    def test_quoted_teaching_context_is_not_nominal_cleanup(self):
        raw = '마이어는 다음 뜻으로 쓰인다.\n\n인용 예문이다.\n가람(): 사람\n'
        self.assertEqual(lists.source_named_aliases(raw), (raw, []))

    def test_unclosed_parenthesis_or_fence_is_not_repaired_by_guessing(self):
        fence = chr(96) * 3
        for body in ['가람(, 1904~2005: 사람\n', fence + 'text\n가람(): 사람\n']:
            raw = '마이어는 다음 뜻으로 쓰인다.\n\n' + body
            self.assertEqual(lists.source_named_aliases(raw), (raw, []))

    def test_bare_unbound_list_name_does_not_get_a_new_value(self):
        raw = '상호는 다음을 가리킨다.\n\n우에토()\n조고 (동음이의)()\n'
        self.assertEqual(lists.source_named_aliases(raw), (raw, []))

    def test_individual_holds_and_incomplete_eos_keep_original_boundary(self):
        raw = '마이어는 다음 뜻으로 쓰인다.\n\n가람(): 미국의 슈퍼마켓 체인\n'
        for row, individual in [(dict(id='expanded_train:987654321',text=raw,complete_eos=True,valid_utf8=True),True),
                                (dict(id='expanded_train:987654321',text=raw,complete_eos=False,valid_utf8=True),False),
                                (dict(id='expanded_train:987654321',text=raw,complete_eos=True,valid_utf8=True,previous_holds=['actual prior hold']),False)]:
            actual = policy.propose(row, individual)
            expected = policy.previous.propose(row, individual)
            self.assertEqual({k:v for k,v in actual.items() if k!='rules'}, {k:v for k,v in expected.items() if k!='rules'})


if __name__ == '__main__':
    modules, pending = [], [inherited26.inherited]
    while pending:
        module = pending.pop()
        if module in modules:
            continue
        modules.append(module)
        pending.extend(value for name in ['inherited','local_inherited','structure_tests','preservation_tests']
                       if (value := getattr(module,name,None)) is not None)
    classes = [DeclaredListSourcePreservation, inherited26.ObservedSourceHolesAndEmptyLeaves,
               inherited26.AliasScopeAndEnglishRoles, inherited26.EntireMissingContentAxis,
               inherited26.metadata_tests.TypedOrdinalMetadata]
    for module in modules:
        classes += [(inherited26.inherited.inherited.RetainedStyleInsteadOfRenderedLoss
                     if value.__name__ == 'SourceValuePreservation' else value)
                    for value in vars(module).values() if isinstance(value,type)
                    and issubclass(value,unittest.TestCase) and value.__module__==module.__name__]
    with ExitStack() as stack:
        for module in [inherited26,*modules]:
            if hasattr(module,'policy'):
                stack.enter_context(patch.object(module,'policy',policy))
        result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(
            unittest.defaultTestLoader.loadTestsFromTestCase(value) for value in dict.fromkeys(classes)))
    raise SystemExit(0 if result.wasSuccessful() else 1)
