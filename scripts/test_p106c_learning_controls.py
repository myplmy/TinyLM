#!/usr/bin/env python3
"""Pure contracts for three Stage8 controls; no real checkpoint/model/GPU."""
import ast
from collections import Counter
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.p106c_data import make_role
from scripts.p106c_pair_balance import make_plan
from scripts.diag_p106c_order_pair import materialize,prompt_grid
from scripts.diag_p106c_learning_controls import extend_draws,familiar,construct_random_model


class LearningControlTests(unittest.TestCase):
    def test_extension_preserves_prefix_balance_and_cap(self):
        roles={r:make_role(r) for r in ('train','rehearsal')}
        e=lambda vs:[([1]*8,[1]*8,2) for _ in vs]
        prefix=make_plan(roles['train'],roles['rehearsal'],e(roles['train']),e(roles['rehearsal']),[])['baseline']
        extended,caps=extend_draws(prefix,roles)
        self.assertEqual(extended[:32],prefix);self.assertEqual(len(extended),128)
        self.assertLessEqual(max(caps.values()),16)
        for batch in materialize(extended,roles,True):
            counts=Counter((r['role'],r['language'],r['gold'],r['training_order']) for r in batch)
            self.assertEqual(set(counts.values()),{1})

    def test_familiar_keeps_gold_and_requested_target(self):
        rows=make_role('train')[:2]
        a,b=map(familiar,rows)
        self.assertIn('민수의 색은?',a['question']);self.assertIn('지수의 색은?',b['question'])
        self.assertEqual([a['gold'],b['gold']],[r['gold'] for r in rows])
        grid=prompt_grid(make_role('sealed'))
        for row in grid:
            row=dict(row,pair_id=f"{row['pair_id']}_{row['family']}_{int(row['reversed'])}")
            self.assertEqual(familiar(row)['gold'],row['gold'])

    def test_unknown_entity_does_not_get_broadly_replaced(self):
        row=make_role('train')[0];row['question']='A and B'
        with self.assertRaises(ValueError):familiar(row)

    def test_scratch_constructor_never_accepts_parent_parameters(self):
        with patch('tinylm.model.TiedMLPTransformer') as ctor:
            cfg=object();model=construct_random_model(cfg)
            ctor.assert_called_once_with(cfg);model.load_state_dict.assert_not_called()
        tree=ast.parse((ROOT/'scripts/diag_p106c_learning_controls.py').read_text())
        fn=next(v for v in tree.body if isinstance(v,ast.FunctionDef) and v.name=='scratch_student')
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='load_state_dict' for n in ast.walk(fn)))


if __name__=='__main__':unittest.main()
