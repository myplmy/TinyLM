"""Typed repeated records: positive roles and loss/copy/identity negatives."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_policy_v32 as policy
from scripts import p106b_hold_resolution_repeat_context_v2 as proof


class TypedRepeatedRecords(unittest.TestCase):
    def quiz(self):
        return ('Take this road safety quiz to check the written rules.\n'
            '1. Why should a driver reduce speed in heavy rain?\n'
            '- There is more time to react\n- The vehicle may skid less\n- It reduces some risks\n- All of the above\n'
            '2. When should a parked vehicle be checked for damage?\n'
            '- While moving through traffic\n- Before entering a junction\n- After reaching a safe place\n- All of the above\n'
            'Answers: 1. D 2. C')

    def metadata(self):
        return ('가람(Garam, 1990년 ~ )은 대한민국의 축구 선수이다. 가람 FC에서 수비수로 활동했다.\n\n'
                '1990년 출생\n살아있는 사람\n대한민국의 축구 선수\n가람 FC의 축구 선수\n대한민국의 축구 선수\n')

    def row(self,text):
        return dict(id='expanded_train:987654320',text=text,complete_eos=True,valid_utf8=True)

    def test_choices_in_different_questions_remain_identical(self):
        text=self.quiz();result=proof.prove(text)
        self.assertEqual(result['candidate'],text)
        value=policy.propose(self.row(text))
        self.assertEqual(value['decision'],'KEEP')
        self.assertEqual(value['text'].count('- All of the above'),2)

    def test_duplicate_within_one_question_is_not_released(self):
        text=self.quiz().replace('- There is more time to react','- All of the above')
        self.assertIsNone(proof.prove(text))

    def test_duplicate_question_body_is_not_released(self):
        text=self.quiz().replace('When should a parked vehicle be checked for damage?',
                                  'Why should a driver reduce speed in heavy rain?')
        self.assertIsNone(proof.prove(text))

    def test_blank_choice_is_not_released(self):
        self.assertIsNone(proof.prove(self.quiz().replace('- The vehicle may skid less','- ')))

    def test_missing_answer_key_is_not_released(self):
        self.assertIsNone(proof.prove(self.quiz().replace(' 2. C','')))

    def test_answer_keys_must_keep_question_order(self):
        self.assertIsNone(proof.prove(self.quiz().replace('1. D 2. C','2. C 1. D')))

    def test_other_repeated_body_is_not_borrowing_choice_role(self):
        text='Repeated prose statement.\nRepeated prose statement.\n'+self.quiz()
        self.assertIsNone(proof.prove(text))

    def test_only_redundant_nonnumeric_metadata_tag_is_removed(self):
        text=self.metadata();result=proof.prove(text)
        self.assertIsNotNone(result)
        self.assertEqual(result['candidate'].count('대한민국의 축구 선수'),2)
        self.assertEqual(result['proof']['removed'],['대한민국의 축구 선수'])
        value=policy.propose(self.row(text))
        self.assertEqual(value['decision'],'EDIT')
        self.assertEqual(value['text'].count('1990'),2)
        self.assertIn('가람 FC의 축구 선수',value['text'])

    def test_duplicate_year_tag_is_deferred(self):
        self.assertIsNone(proof.prove(self.metadata()+'1990년 출생\n'))

    def test_body_repetition_is_not_metadata_repetition(self):
        text=self.metadata().replace('가람 FC에서 수비수로 활동했다.',
            '가람 FC에서 수비수로 활동했다.\n\n대한민국의 축구 선수')
        self.assertIsNone(proof.prove(text))

    def test_missing_formal_symbol_is_deferred(self):
        self.assertIsNone(proof.prove(self.metadata().replace('가람 FC에서 수비수로 활동했다.',
            '함수 는 정의역이 없는 기호이다.')))

    def test_empty_content_heading_remains_deferred(self):
        self.assertIsNone(proof.prove(self.metadata().replace('\n\n1990년','\n\n방송 일자\n\n1990년')))

    def test_individual_hold_is_preserved(self):
        self.assertEqual(policy.propose(self.row(self.quiz()),individual_hold=True)['decision'],'PENDING')


if __name__=='__main__':
    path=ROOT/'scripts/test_p106b_hold_resolution_policy_v31.py'
    code=path.read_text(encoding='utf-8')
    for before,after,expected in [
        ('from scripts import p106b_hold_resolution_policy_v31 as policy',
         'from scripts import p106b_hold_resolution_policy_v32 as policy',2),
        ('classes = [LiteralCategoryAnchors, TerminalBodyContract,',
         'classes = [TypedRepeatedRecords, LiteralCategoryAnchors, TerminalBodyContract,',1),
        ('LiteralCategoryAnchors=LiteralCategoryAnchors,TerminalBodyContract=',
         'TypedRepeatedRecords=TypedRepeatedRecords,LiteralCategoryAnchors=LiteralCategoryAnchors,TerminalBodyContract=',1)]:
        assert code.count(before)==expected,before
        code=code.replace(before,after)
    exec(compile(code,str(path),'exec'),dict(__name__='__main__',__file__=str(Path(__file__)),
        TypedRepeatedRecords=TypedRepeatedRecords))
