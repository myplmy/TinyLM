#!/usr/bin/env python3
"""CPU fixture checks for fact-preserving order intervention; no model loads."""
from collections import Counter
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.p106c_data import make_role
from scripts.p106c_pair_balance import make_plan
from scripts.diag_p106c_order_pair import order_variant,materialize


class OrderPairTests(unittest.TestCase):
    def test_gold_and_target_stay_fixed_when_fact_order_changes(self):
        for role in ('train','rehearsal'):
            rows=make_role(role)
            for i in range(0,len(rows),2):
                original=order_variant(*rows[i:i+2],False)
                reversed_rows=order_variant(*rows[i:i+2],True)
                for old,new in zip(original,reversed_rows):
                    self.assertEqual(old['gold'],new['gold'])
                    self.assertEqual(old['id'],new['id'])
                    self.assertNotEqual(old['question'],new['question'])
                    a,b=old['pair_id']+'a',old['pair_id']+'b'
                    self.assertLess(old['question'].index(a),old['question'].index(b))
                    self.assertLess(new['question'].index(b),new['question'].index(a))

    def test_same_draws_half_reversed_each_language_role(self):
        roles={r:make_role(r) for r in ('train','rehearsal')}
        encode=lambda rows:[([1]*8,[1]*8,2) for _ in rows]
        plan=make_plan(roles['train'],roles['rehearsal'],encode(roles['train']),encode(roles['rehearsal']),[])
        fixed=materialize(plan['baseline'],roles,False)
        mixed=materialize(plan['baseline'],roles,True)
        for left,right in zip(fixed,mixed):
            self.assertEqual([(r['id'],r['gold']) for r in left],[(r['id'],r['gold']) for r in right])
            self.assertEqual(set(r['training_order'] for r in left),{'ab'})
            counts=Counter((r['role'],r['language'],r['training_order']) for r in right)
            self.assertEqual(len(counts),8);self.assertEqual(set(counts.values()),{4})
            colors=Counter((r['role'],r['language'],r['training_order'],r['gold']) for r in right)
            self.assertEqual(set(colors.values()),{1})

    def test_drift_is_rejected_not_guessed(self):
        rows=make_role('train')[:2]
        rows[0]['question']='unknown template'
        with self.assertRaises(ValueError):order_variant(*rows,True)


if __name__=='__main__':unittest.main()
