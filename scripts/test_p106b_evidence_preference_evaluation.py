#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import inspect
import unittest
from scripts import diag_p106b_evidence_preference_evaluate as e


class Evaluation(unittest.TestCase):
    def test_parent_replay_uses_actual_previous_metric_names(self):
        src=inspect.getsource(e.parent_replay)
        self.assertIn("('role_retention','role_retention')",src)
        self.assertIn("('source_posthoc_dev','source_posthoc_dev')",src)

    def test_same_new_runtime_and_final64(self):
        self.assertEqual(e.course.TAG,'p106b_evidence_preference_v1_s1337')
        self.assertIs(e.course.producer,e.course.upstream.producer)
        self.assertIs(e.course.prior,e.course.upstream.prior)
        self.assertIn('style3',e.info()['new_test'])
        src=inspect.getsource(e.run);self.assertIn("saved['evidence_preference']",src)
        self.assertIn('updates=64',src);self.assertIn('old_parent_exact_replay',src)

    def test_actual_gold_and_free_clarification_separate(self):
        src=inspect.getsource(e.readback)
        self.assertIn('ASK_FOR_MISSING_FACT',src);self.assertIn('ANSWER',src)
        self.assertEqual(e.info()['precision'],'FP32_MATH')


if __name__=='__main__':unittest.main()
