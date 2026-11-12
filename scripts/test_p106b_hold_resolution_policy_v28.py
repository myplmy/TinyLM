"""Run all policy27 regressions plus observed declaration variants and holes."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_policy_v28 as policy
from scripts import p106b_hold_resolution_disambiguation_v2 as lists


class ExplicitNameVariantCases(unittest.TestCase):
    def result(self,text,**extra):
        return policy.propose(dict(id='expanded_train:987654321',text=text,complete_eos=True,valid_utf8=True,**extra))

    def test_source_language_name_and_literal_lifespan(self):
        for language in ['이탈리아어권','슬라브어권','스페인어권']:
            raw='실비오()는 '+language+'에서 쓰이는 이름이다.\n\n실비오(, 1913~1996)는 축구 선수이다.\n\n같이 보기\n'
            value=self.result(raw);self.assertEqual(value['decision'],'EDIT')
            self.assertIn('실비오(1913~1996)는',value['text'])

    def test_people_with_name_header(self):
        raw='아웅 투()라는 이름을 가진 사람은 다음과 같다.\n\n아웅 투(1955년~)는 정치인이다.\n'
        value=self.result(raw);self.assertEqual(value['decision'],'EDIT');self.assertIn('1955년~',value['text'])

    def test_name_is_x_people_header(self):
        raw='이름이 조지 쇼인 사람으로는 다음이 있다.\n\n조지 쇼(, 1751~1813)는 식물학자다.\n'
        value=self.result(raw);self.assertEqual(value['decision'],'EDIT');self.assertIn('(1751~1813)',value['text'])

    def test_other_meaning_keeps_populated_see_also(self):
        raw='버밍햄()의 다른 뜻은 다음과 같다.\n\n버밍햄(Birmingham)은 미국의 도시이다.\n\n같이 보기\n버밍엄(Birmingham)은 영국의 도시이다.\n'
        value=self.result(raw);self.assertEqual(value['decision'],'EDIT')
        self.assertIn('같이 보기',value['text']);self.assertIn('버밍엄(Birmingham)',value['text'])

    def test_named_song_with_explicit_colon(self):
        raw='퐁퐁은 다음 등을 가리킨다.\n\n〈퐁퐁〉(): 가수의 곡. 2004년 발표\n'
        value=self.result(raw);self.assertEqual(value['decision'],'EDIT');self.assertIn('2004년',value['text'])

    def test_unbound_river_name_stays_pending(self):
        raw='허강에는 다음 뜻이 있다.\n\n허강시() - 중화인민공화국의 도시\n(, He River) - 중화인민공화국의 강\n'
        self.assertEqual(self.result(raw)['decision'],'PENDING')

    def test_unnamed_people_stay_pending(self):
        raw='사보 졸탄()은 헝가리어 이름으로 다음 사람을 가리킨다.\n\n(1858~1934) - 정치인\n졸탄 사보(, 1972~): 축구 선수\n'
        self.assertEqual(self.result(raw)['decision'],'PENDING')

    def test_extra_closing_parenthesis_not_hidden(self):
        raw='이름이 조지 쇼인 사람으로는 다음이 있다.\n\n조지 쇼(, 1751~1813)는 식물학자다.\n조지 버나드 쇼(), 1856~1950)는 작가다.\n'
        self.assertEqual(lists.source_named_aliases(raw),(raw,[]))
        self.assertEqual(self.result(raw)['decision'],'PENDING')

    def test_formula_or_value_name_not_a_person_list(self):
        for name in ['함수','인구','계수','변수']:
            raw=name+'()의 다른 뜻은 다음과 같다.\n가람(): 예제\n'
            self.assertEqual(lists.source_named_aliases(raw),(raw,[]))

    def test_filled_foreign_name_is_never_erased(self):
        raw='실비오()는 이탈리아어권에서 쓰이는 이름이다.\n실비오(Silvio, 1913년~1996년)는 선수이다.\n'
        value=self.result(raw);self.assertIn('Silvio, 1913년~1996년',value.get('candidate',value['text']))

    def test_complete_code_call_and_empty_tuple_survive(self):
        fence=chr(96)*3
        raw='가람()의 다른 뜻은 다음과 같다.\n'+fence+'python\ndef 가람():\n    return ()\n'+fence+'\n'
        text=self.result(raw);self.assertIn('def 가람():',text.get('candidate',text['text']))
        self.assertIn('return ()',text.get('candidate',text['text']))

    def test_individual_previous_hold_is_not_released(self):
        raw='실비오()는 이탈리아어권에서 쓰이는 이름이다.\n실비오(, 1913~1996)는 선수이다.\n'
        actual=self.result(raw,previous_holds=['actual source hold'])
        self.assertEqual(actual['decision'],'PENDING')


if __name__=='__main__':
    source=ROOT/'scripts/test_p106b_hold_resolution_policy_v27.py'
    code=source.read_text(encoding='utf-8')
    before='from scripts import p106b_hold_resolution_policy_v27 as policy'
    assert code.count(before)==1
    code=code.replace(before,'from scripts import p106b_hold_resolution_policy_v28 as policy')
    before='classes = [DeclaredListSourcePreservation,'
    assert code.count(before)==1
    code=code.replace(before,'classes = [ExplicitNameVariantCases, DeclaredListSourcePreservation,')
    exec(compile(code,str(source),'exec'),dict(__name__='__main__',__file__=str(Path(__file__)),
        ExplicitNameVariantCases=ExplicitNameVariantCases))
