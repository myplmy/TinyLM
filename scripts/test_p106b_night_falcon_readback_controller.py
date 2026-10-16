"""Common eligible source-ID comparison; no source/tokenizer/model/GPU reads."""
from pathlib import Path
import sys
import copy
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_night_falcon_readback as d


def examples():
    ref = []; tiny = []
    for task in d.falcon.TASKS[:3]:
        for i in range(2):
            gold = i; pred = 0
            ref.append(dict(id=task + '#' + str(i), task=task, gold=gold, pred=pred,
                correct=int(pred == gold), char_norm_pred=pred, char_norm_correct=int(pred == gold)))
            tiny.append(dict(id=task + '#' + str(i), task=task, gold=gold,
                pred_harness=1, pred_harness_norm=1, skipped=False))
    return ref, tiny


class ReferenceControllerTests(unittest.TestCase):
    def test_symmetric_disagreement_and_real_denominators(self):
        ref, tiny = examples(); result = d.common_comparison(ref, tiny)
        for v in result.values():
            self.assertEqual(v['n_common'], 2); self.assertEqual(v['falcon_correct'], 1)
            self.assertEqual(v['tiny_correct'], 1); self.assertEqual(v['tiny_minus_falcon'], 0.)
            self.assertEqual((v['discordant_falcon_only'], v['discordant_tiny_only']), (1, 1))

    def test_different_eligibility_uses_intersection_not_implicit_zero(self):
        ref, tiny = examples(); tiny[0]['skipped'] = True
        result = d.common_comparison(ref, tiny)
        self.assertEqual(result['piqa']['n_common'], 1)
        self.assertEqual(result['piqa']['falcon_eligible'], 2)
        self.assertEqual(result['piqa']['tiny_eligible'], 1)
        self.assertEqual(result['piqa']['tiny_correct'], 1)

    def test_original_gold_mismatch_is_not_comparable(self):
        ref, tiny = examples(); tiny[0]['gold'] = 1
        with self.assertRaises(ValueError): d.common_comparison(ref, tiny)

    def test_duplicate_and_empty_task_cannot_silently_pass(self):
        ref, tiny = examples()
        with self.assertRaises(ValueError): d.common_comparison(ref + [ref[0]], tiny)
        with self.assertRaises(ValueError): d.common_comparison(ref, tiny + [tiny[0]])
        with self.assertRaises(ValueError): d.common_comparison(ref, [r for r in tiny if r['task'] != 'piqa'])

    def test_declared_endpoint_labels_are_unique(self):
        labels = [p.__name__.rsplit('_', 1)[-1] + '.' + e for p, endpoints in d.PROVIDERS for e in endpoints]
        self.assertEqual(len(labels), 17); self.assertEqual(len(set(labels)), 17)


if __name__ == '__main__': unittest.main()
