from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import p106b_state_update_aux as code


class StateContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.group=[code.earlier.prior.correct_own_question(r) for r in code.source.binding_rows('test',1)][:4]

    def test_train_and_test_views_balance_new_value_and_format(self):
        for split,n in (('train',32),('dev',32),('test',8)):
            rows=code.state_views(self.group,split);legal=code.approved(rows)
            self.assertEqual(len(rows),n);self.assertEqual(sum(code.label(r,legal) for r in rows),n//2)
            self.assertEqual(sum(r['meta']['final_format']=='json' for r in rows),n//2)
            self.assertEqual(sum(r['meta']['previous_value_copy_correct'] for r in rows),n//4)
            self.assertEqual(sum(r['meta']['old_lookup_ignoring_update_correct'] for r in rows),n//2)

    def test_metadata_and_question_tampering_rejected(self):
        row=code.state_views(self.group,'train')[0];legal=code.approved([row])
        altered=copy.deepcopy(row);altered['meta']['updated_entity']=next(k for k in row['meta']['initial_values'] if k!=row['meta']['updated_entity'])
        with self.assertRaises(ValueError):code.label(altered,legal)
        altered=copy.deepcopy(row);altered['messages'][2]['content'][0]['text']+=' changed'
        with self.assertRaises(ValueError):code.label(altered,legal)

    def test_aux_mask_copy_uses_last_assistant_and_never_changes_word_mask(self):
        import torch
        h=torch.randn(2,8,3,requires_grad=True);y=torch.tensor([[-100,1,2,-100,-100,3,4,-100]]*2)
        original=y.clone();head=code.earlier.new_head(3)
        with torch.no_grad():head.weight.copy_(torch.randn_like(head.weight))
        loss,n,_,events=code.final_auxiliary_sum(head,h,y,[0,1],[[5],[5]])
        expected=torch.nn.functional.cross_entropy(head(h[:,5]),torch.tensor([0,1]),reduction='sum')
        self.assertTrue(torch.equal(y,original));self.assertTrue(torch.allclose(loss,expected));self.assertEqual((n,events),(2,2))
        grad=torch.autograd.grad(loss,h)[0];self.assertEqual(float(grad[:,:5].abs().sum()),0.)
        with self.assertRaises(ValueError):code.final_auxiliary_sum(head,h,y,[0,1],[[1],[5]])

    def test_known_json_contract_only(self):
        import json
        self.assertEqual(json.loads(code.render_value('파랑','json')),dict(answer='파랑'))
        with self.assertRaises(ValueError):code.render_value('파랑','unknown')

    def test_own_department_template_particle(self):
        groups=code.source.binding_rows('test',1)
        department=next(r for r in groups if r['meta']['kind']=='binding_department' and r['meta']['language']=='ko')
        names=list(department['meta']['mapping']);row=code.updated_row(department,names[0],names[1],'json')
        self.assertIn('현재 학과를 answer',row['messages'][2]['content'][0]['text'])

    def test_scoped_callback_does_not_recurse(self):
        import torch
        from unittest.mock import patch
        h=torch.randn(1,8,3,requires_grad=True);y=torch.tensor([[-100,1,2,-100,-100,3,4,-100]])
        head=code.earlier.new_head(3)
        with patch.object(code.earlier,'suffix_auxiliary_sum',code.final_auxiliary_sum):
            loss,n,correct,events=code.earlier.suffix_auxiliary_sum(head,h,y,[1],[[5]])
        self.assertEqual((n,events),(1,1));self.assertTrue(torch.isfinite(loss))


if __name__=='__main__':unittest.main()
