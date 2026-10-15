#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from scripts import diag_p106b_relation_interleaved_evaluate as e


class Evaluation(unittest.TestCase):
    def test_old_test_marked_development_and_new_indices(self):
        r=e.info();self.assertTrue(r['old_TEST_used_as_development']);self.assertEqual(r['natural_source_cases'],32)
        self.assertEqual(e.course.info()['new_test_fiction_indices'],[8192,8447])

    def test_no_auxiliary_generation_or_reserved_test_evaluation(self):
        r=e.info();self.assertFalse(r['auxiliary_used_in_generation']);self.assertFalse(r['future_reserved_role_test_evaluated'])

    def test_fixed_final_checkpoints_not_best_test(self):
        self.assertEqual(e.info()['checkpoint_policy'],'fixed final4rootpasses')
        self.assertEqual(e.info()['endpoints'],['blocked_fact1','interleaved_fact1'])

    def test_same_actual_and_reference_history_counts(self):
        r=e.info();self.assertEqual(r['actual_self_history_answers'],3072);self.assertEqual(r['supplied_error_answers'],512)
        self.assertEqual(r['gold_second_answers'],1536)


if __name__=='__main__':unittest.main()
