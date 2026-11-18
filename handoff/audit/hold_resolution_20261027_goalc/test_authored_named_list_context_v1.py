from pathlib import Path
import sys
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[3])]
from authored_named_list_context_v1 import classify_block, context_deferrals, PROSE


RELATED = '같이 보기\n ReBirth RB-338 - 윈도우와 매킨토시에서 작동되는 TB-303, TR-808, TR-909의 신디사이저 소프트웨어'
DEFINITIONS = '컴퓨터 과학\n 클래스: 객체 지향 프로그래밍의 중요한 개념\n class 속성: HTML 속성의 하나\n 클래스 파일: 자바의 이진 실행 파일 형식\n 네트워크 클래스: IPv4에서 IP 주소의 첫 번째 구조 변화'
ROSTER = '필리프 2세 휘하 원수 2명, 1180~1223\n 알베릭 클레망 (? ~1191), 1185년 프랑스 원수 임명\n 기욤 드 라투르넬, 1220년 프랑스 원수 임명'


class NamedListContextTests(unittest.TestCase):
    def test_related_item_retains_actual_title_and_models(self):
        reasons, proof = context_deferrals(RELATED, RELATED)
        self.assertNotIn(PROSE, reasons)
        self.assertTrue(proof['discharged'])

    def test_definition_rows_are_not_forced_to_finite_prose(self):
        reasons, proof = context_deferrals(DEFINITIONS, DEFINITIONS)
        self.assertNotIn(PROSE, reasons)
        self.assertTrue(proof['discharged'])

    def test_sparse_roster_keeps_unknown_birth_date_and_count(self):
        role = classify_block(ROSTER)
        self.assertEqual(role['records'], 2)
        self.assertTrue(role['uniform_birth_fields_not_required'])

    def test_mismatched_declared_count_is_not_released(self):
        self.assertIsNone(classify_block(ROSTER.replace('2명', '3명')))

    def test_unfilled_definition_stays_unresolved(self):
        self.assertIsNone(classify_block('정의\n 첫 항목: 값\n 둘째 항목: '))

    def test_dangling_predicate_in_definition_is_not_a_value(self):
        self.assertIsNone(classify_block('정의\n 첫 항목: 실제 값\n 둘째 항목: 조건을 충족하는 경우'))

    def test_arbitrary_dash_without_related_heading_is_not_list_proof(self):
        self.assertIsNone(classify_block(RELATED.replace('같이 보기', '서술 문단')))

    def test_body_cannot_invent_definition_colons(self):
        source = DEFINITIONS.replace(':', '')
        reasons, proof = context_deferrals(source, DEFINITIONS)
        self.assertIn(PROSE, reasons)
        self.assertFalse(proof['discharged'])

    def test_filled_record_value_changes_fail_source_anchor(self):
        reasons, proof = context_deferrals(DEFINITIONS, DEFINITIONS.replace('IPv4', 'IPv6'))
        self.assertIn(PROSE, reasons)
        self.assertFalse(proof['discharged'])

    def test_reordered_record_values_fail_source_anchor(self):
        values = DEFINITIONS.splitlines()
        body = '\n'.join([values[0], values[2], values[1], *values[3:]])
        reasons, proof = context_deferrals(DEFINITIONS, body)
        self.assertIn(PROSE, reasons)
        self.assertFalse(proof['discharged'])

    def test_one_valid_list_does_not_release_unfinished_other_block(self):
        text = RELATED + '\n\n' + '그는 중요한 조건을 설명한 다음 새로운 절차를 시작하기 위하여 여러 실제 자료와 과거 기록을 함께 검토하면서 마지막으로 그 결과를'
        reasons, proof = context_deferrals(text, text)
        self.assertIn(PROSE, reasons)
        self.assertFalse(proof['discharged'])

    def test_typographic_quote_flag_is_not_waived(self):
        text = RELATED + '\n\n“'
        reasons, proof = context_deferrals(text, text)
        self.assertIn('UNBALANCED_CURLY_DOUBLE_QUOTES_NEED_CONTEXT', reasons)

    def test_nominal_narrative_without_listing_remains_context(self):
        text = '이 인물은 작품 속에서 여러 사람과 관계를 맺고 오랫동안 함께 생활하며 이야기의 사건에 계속 등장한다. 세바스찬이라는 이름은 세리카가 지어준 이름'
        reasons, proof = context_deferrals(text, text)
        self.assertIn(PROSE, reasons)
        self.assertFalse(proof['discharged'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
