"""Inherit policy28 regressions; exercise positive event pairs and rejected boundaries."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_policy_v29 as policy
from scripts import p106b_hold_resolution_metadata_v3 as metadata


class EventMetadataBoundary(unittest.TestCase):
    def source(self, suffix='대한민국의 정당\n1945년 설립\n1945년 폐지', before='각주'):
        return '가람단체(가람회)는 1945년에 설립된 정치 단체이다. 독립된 설명을 원문대로 보존한다.\n\n'+before+'\n\n'+suffix

    def result(self, source, **extra):
        return policy.propose(dict(id='expanded_train:987654321', text=source,
                                   complete_eos=True, valid_utf8=True, **extra))

    def test_same_year_start_end_and_all_literal_values_survive(self):
        source=self.source()
        proof=metadata.prove(source)
        self.assertIsNotNone(proof)
        self.assertIn('1945년 설립\n1945년 폐지',proof['candidate'])
        self.assertNotIn('각주',proof['candidate'])
        self.assertEqual(self.result(source)['decision'],'EDIT')

    def test_installation_and_abolition_pair(self):
        source=self.source('가람군\n1413년 설치\n1914년 폐지\n1914년 설치')
        self.assertIsNotNone(metadata.prove(source))

    def test_populated_reference_and_attribution_are_not_removed(self):
        before='참고자료\n 이철순, 제목 (2005.9.1) 제552호 (300~311쪽)\n\n각주'
        source=self.source(before=before)
        proof=metadata.prove(source)
        self.assertIsNotNone(proof)
        self.assertIn('참고자료\n 이철순, 제목 (2005.9.1) 제552호 (300~311쪽)',proof['candidate'])

    def test_one_event_without_complement_does_not_release(self):
        self.assertIsNone(metadata.prove(self.source('가람단체\n1945년 설립\n대한민국의 단체')))

    def test_reversed_event_dates_remain_pending(self):
        self.assertIsNone(metadata.prove(self.source('가람단체\n1987년 설립\n1945년 폐지')))

    def test_quoted_or_punctuated_suffix_is_not_metadata(self):
        for suffix in ['가람단체\n1945년 설립\n1945년 폐지.', '가람단체\n1945년 설립\n“1945년 폐지”']:
            self.assertIsNone(metadata.prove(self.source(suffix)))

    def test_missing_name_is_not_reconstructed(self):
        source=self.source().replace('가람단체(가람회)는','는',1)
        self.assertIsNone(metadata.prove(source))

    def test_populated_footer_is_not_an_empty_heading(self):
        source=self.source(before='외부 링크\n Official web site')
        self.assertIsNone(metadata.prove(source))

    def test_no_new_edit_does_not_release_unchanged_body(self):
        source=self.source(before='관계 있는 단체에 대한 완결된 설명이다.')
        self.assertIsNone(metadata.prove(source))

    def test_individual_hold_is_not_automatically_released(self):
        source=self.source()
        self.assertEqual(self.result(source,previous_holds=['actual source hold'])['decision'],'PENDING')

    def test_missing_math_still_requires_context(self):
        source=self.source(before='정의\n함수 는 다음 식으로 정의된다.\n\n각주')
        self.assertEqual(self.result(source)['decision'],'PENDING')

    def test_missing_content_list_is_not_an_empty_footer(self):
        source=self.source(before='수상자\n\n각주')
        self.assertIsNone(metadata.prove(source))

    def test_paired_program_bytes_are_preserved(self):
        fence=chr(96)*3
        source=self.source(before=fence+'python\ndef f():\n    return ()\n'+fence+'\n\n각주')
        value=self.result(source)
        self.assertIn('def f():\n    return ()',value.get('candidate',value['text']))


if __name__=='__main__':
    # Reuse the earlier all-policy runner; inject only this new policy/class.
    from scripts.test_p106b_hold_resolution_policy_v28 import ExplicitNameVariantCases
    path=ROOT/'scripts/test_p106b_hold_resolution_policy_v27.py'
    code=path.read_text(encoding='utf-8')
    before='from scripts import p106b_hold_resolution_policy_v27 as policy'
    assert code.count(before)==1
    code=code.replace(before,'from scripts import p106b_hold_resolution_policy_v29 as policy')
    before='classes = [DeclaredListSourcePreservation,'
    assert code.count(before)==1
    code=code.replace(before,'classes = [EventMetadataBoundary, ExplicitNameVariantCases, DeclaredListSourcePreservation,')
    exec(compile(code,str(path),'exec'),dict(__name__='__main__',__file__=str(Path(__file__)),
        EventMetadataBoundary=EventMetadataBoundary, ExplicitNameVariantCases=ExplicitNameVariantCases))
