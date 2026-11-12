"""Exercise the actual consumer getter and inherit every earlier regression."""
from contextlib import ExitStack
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_policy_v30 as policy
from scripts import test_p106b_hold_resolution_policy_v28 as tests28
from scripts import test_p106b_hold_resolution_policy_v29 as tests29


class TerminalBodyContract(unittest.TestCase):
    def row(self):
        source=tests29.EventMetadataBoundary().source()
        return dict(id='expanded_train:987654321',text=source,complete_eos=True,valid_utf8=True)

    def test_actual_consumer_selects_the_finished_body(self):
        row=self.row()
        value=policy.propose(row)
        self.assertEqual(value['decision'],'EDIT')
        consumed=value.get('candidate',value['text'])
        self.assertNotIn('\n각주\n',consumed)
        self.assertEqual(consumed,value['text'])
        self.assertNotEqual(consumed,row['text'])
        self.assertIn('대한민국의 정당\n1945년 설립\n1945년 폐지',consumed)

    def test_individual_pending_candidate_contract_is_unchanged(self):
        row=dict(self.row(),previous_holds=['actual individual hold'])
        before=policy.previous.propose(row)
        after=policy.propose(row)
        self.assertEqual(after['decision'],'PENDING')
        self.assertEqual({k:v for k,v in before.items() if k!='rules'},
                         {k:v for k,v in after.items() if k!='rules'})

    def test_unrelated_terminal_rows_are_unchanged(self):
        row=dict(self.row(),text='가람()은 다음 사람을 가리킨다.\n\n가람(, 1904~2005)은 작가이다.\n')
        before=policy.previous.propose(row)
        after=policy.propose(row)
        self.assertEqual({k:v for k,v in before.items() if k!='rules'},
                         {k:v for k,v in after.items() if k!='rules'})


if __name__=='__main__':
    path=ROOT/'scripts/test_p106b_hold_resolution_policy_v27.py'
    code=path.read_text(encoding='utf-8')
    before='from scripts import p106b_hold_resolution_policy_v27 as policy'
    assert code.count(before)==1
    code=code.replace(before,'from scripts import p106b_hold_resolution_policy_v30 as policy')
    before='classes = [DeclaredListSourcePreservation,'
    assert code.count(before)==1
    code=code.replace(before,'classes = [TerminalBodyContract, EventMetadataBoundary, ExplicitNameVariantCases, DeclaredListSourcePreservation,')
    with ExitStack() as stack:
        for module in [tests28,tests29]:
            stack.enter_context(patch.object(module,'policy',policy))
        exec(compile(code,str(path),'exec'),dict(__name__='__main__',__file__=str(Path(__file__)),
            TerminalBodyContract=TerminalBodyContract,EventMetadataBoundary=tests29.EventMetadataBoundary,
            ExplicitNameVariantCases=tests28.ExplicitNameVariantCases))
