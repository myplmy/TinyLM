from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from collections import defaultdict
from scripts import diag_p106b_binding_scale as code


class Contracts(unittest.TestCase):
    def test_names_disjoint_and_fictional_four_views_balanced(self):
        rows={s:code.binding_rows(s,2) for s in ('train','dev','test')};code.validate_splits(rows)
        self.assertEqual(len(code.names('train','ko')),96)
        for split,values in rows.items():
            self.assertEqual(len(values),32);roots=defaultdict(list)
            legal=code.trusted(values)
            for row in values:
                roots[row['meta']['semantic_root_id']].append(code.method.binding_bit(row,legal))
                self.assertIn('FICTIONAL',row['meta']['named_entities'])
            self.assertTrue(all(len(v)==4 and sum(v)==2 for v in roots.values()))

    def test_scoped_factory_restores_original_names(self):
        original=copy.deepcopy(code.method.prior.source.NAMES);code.binding_rows('train',1)
        self.assertEqual(original,code.method.prior.source.NAMES)

    def test_choice_uses_dev_only_and_tie_priority(self):
        def scale_fixture_report(root,exact,ce):return dict(history=[dict(dev=dict(all4_exact_roots=root,
            counts={'ko:binding_color':dict(exact=exact),'en:arithmetic':dict(exact=99)}),native=dict(ce=ce))],
            fresh_test='MUST_NOT_BE_READ')
        reports={a:scale_fixture_report(0,3,3.5) for a in ('aux0',*code.CANDIDATES)}
        self.assertEqual(code.select_candidate(reports),('auxdense100',False))
        reports['aux03']=scale_fixture_report(1,4,3.6);reports['aux100']=scale_fixture_report(1,4,3.6)
        self.assertEqual(code.select_candidate(reports),('aux03',True))
        reports['aux100']=scale_fixture_report(1,4,3.4)
        self.assertEqual(code.select_candidate(reports),('aux100',True))

    def test_budget_uses_nearest_rank_and_excludes_completed(self):
        reports={a:dict(step_seconds=[100,1,2,3,4,5,6,7]) for a in ('aux0','aux100')}
        a=code.forecast(reports,40000);self.assertEqual(a['arms']['aux0']['steady_p95'],7)
        self.assertEqual(a['needed_sec'],2*(7*2096+600)+4500);self.assertTrue(a['fits'])
        b=code.forecast(reports,20000,('aux0',));self.assertTrue(b['fits'])
        self.assertLess(b['needed_sec'],a['needed_sec'])
        self.assertFalse(code.forecast(reports,100)['fits'])

    def test_budget_rejects_partial_and_nonfinite_cost(self):
        with self.assertRaises(ValueError):code.forecast({'a':dict(step_seconds=[1,2,3])},100)
        with self.assertRaises(ValueError):code.forecast({'a':dict(step_seconds=[1]*7+[float('nan')])},100)


if __name__=='__main__':unittest.main()
