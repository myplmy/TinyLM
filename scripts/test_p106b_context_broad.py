"""CPU source-case/domain/grouping/restore and dialogue rubric fixtures."""
import unittest
from collections import Counter
from scripts import p106b_context_broad as data

class BroadTests(unittest.TestCase):
    def test_distinct_balanced_actual_topic_cases(self):
        rows=data.build();allrows=[r for part in rows.values() for r in part]
        self.assertEqual([len(rows[k]) for k in ('train','val')],[8192,1024])
        self.assertEqual(len({r['meta']['semantic_root_id'] for r in allrows}),9216)
        self.assertEqual(len({data.sha(r['messages']) for r in allrows}),9216)
        self.assertEqual(set(Counter(r['meta']['kind'] for r in rows['train']).values()),{1024})
    def test_correct_and_missing_conditions_in_each_context_domain(self):
        for kind in data.KINDS[:6]:
            conditions={data.make(kind,'ko',i)['meta']['source_condition'] for i in range(100)}
            self.assertEqual(conditions,{'SUFFICIENT','MISSING','AMBIGUOUS'})
    def test_original_scope_restores_after_failure(self):
        from scripts import diag_p106b_context_broad as gate
        from scripts import diag_p106b_context_quality as old
        original=(old.TAG,old.CORPUS,old.data)
        with self.assertRaises(RuntimeError):
            with gate.scope():
                self.assertEqual(old.info()['expected_updates'],256);raise RuntimeError('fixture')
        self.assertEqual((old.TAG,old.CORPUS,old.data),original)
    def test_every_turn_has_a_declared_rubric(self):
        for kind in data.KINDS:
            for seed in range(20):
                r=data.make(kind,'en',seed)
                self.assertEqual(len(r['meta']['turn_rubrics']),len(r['messages'])//2)

if __name__=='__main__':unittest.main(verbosity=2)
