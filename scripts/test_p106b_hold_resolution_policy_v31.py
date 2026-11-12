"""Add source-boundary negatives and inherit all earlier policy regressions."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_policy_v31 as policy
from scripts import p106b_hold_resolution_metadata_v4 as metadata
from scripts import test_p106b_hold_resolution_policy_v28 as tests28
from scripts import test_p106b_hold_resolution_policy_v29 as tests29
from scripts import test_p106b_hold_resolution_policy_v30 as tests30


class LiteralCategoryAnchors(unittest.TestCase):
    def source(self):
        return '《가람》은 2015년 일본의 영화이다. 배우와 감독의 실제 이름이 본문에 적혀 있다.\n\n출연\n김가람 - 주인공\n\n각주\n\n외부 링크\n\n일본의 청춘 영화\n일본의 드라마 영화\n'

    def row(self,text=None):
        return dict(id='expanded_train:987654320',text=text or self.source(),complete_eos=True,valid_utf8=True)

    def test_year_free_typed_tail_and_cast_values(self):
        row=self.row();value=policy.propose(row)
        self.assertEqual(value['decision'],'EDIT')
        clean=value.get('candidate',value['text'])
        self.assertIn('김가람 - 주인공',clean)
        self.assertIn('일본의 청춘 영화\n일본의 드라마 영화',clean)
        self.assertNotIn('\n각주\n',clean)

    def test_duplicate_marker_is_not_two_anchors(self):
        text=self.source().replace('일본의 드라마 영화','일본의 청춘 영화')
        self.assertIsNone(metadata.prove(text))

    def test_empty_award_list_is_not_metadata(self):
        text='골든 상은 유럽의 유망주 축구 선수에게 수여되는 상이다.\n\n수상자\n\n각주\n\nU-21 축구\n유럽의 축구상\n'
        self.assertIsNone(metadata.prove(text))

    def test_actual_military_stub_shape_is_deferred(self):
        text='제6군상급사령부는 독일 제국의 야전군급 사령부이다.\n\n전투서열\n\n역대 사령관\n\n독일 제국군의 야전군\n1914년 설립\n1919년 폐지\n'
        self.assertEqual(metadata.empty_content_headings(text),['전투서열','역대 사령관'])

    def test_education_followed_by_next_section_is_empty(self):
        text='소사구는 경기도의 행정 구역이었다.\n\n교육 기관\n\n교통\n\n철도 노선의 실제 정보이다.\n'
        self.assertIn('교육 기관',metadata.empty_content_headings(text))

    def test_filled_education_section_is_not_empty(self):
        self.assertEqual(metadata.empty_content_headings('교육 기관\n\n가람대학교\n\n교통\n\n철도 노선의 실제 정보이다.'),[])

    def test_quotation_cannot_borrow_metadata_proof(self):
        self.assertIsNone(metadata.prove('“'+self.source()+'”'))

    def test_individual_hold_survives(self):
        self.assertEqual(policy.propose(dict(self.row(),previous_holds=['manual hold']))['decision'],'PENDING')


if __name__=='__main__':
    path=ROOT/'scripts/test_p106b_hold_resolution_policy_v27.py'
    code=path.read_text(encoding='utf-8')
    before='from scripts import p106b_hold_resolution_policy_v27 as policy'
    assert code.count(before)==1
    code=code.replace(before,'from scripts import p106b_hold_resolution_policy_v31 as policy')
    before='classes = [DeclaredListSourcePreservation,'
    assert code.count(before)==1
    code=code.replace(before,'classes = [LiteralCategoryAnchors, TerminalBodyContract, EventMetadataBoundary, ExplicitNameVariantCases, DeclaredListSourcePreservation,')
    with ExitStack() as stack:
        for module in [tests28,tests29,tests30]:
            stack.enter_context(patch.object(module,'policy',policy))
        exec(compile(code,str(path),'exec'),dict(__name__='__main__',__file__=str(Path(__file__)),
            LiteralCategoryAnchors=LiteralCategoryAnchors,TerminalBodyContract=tests30.TerminalBodyContract,
            EventMetadataBoundary=tests29.EventMetadataBoundary,ExplicitNameVariantCases=tests28.ExplicitNameVariantCases))
