import unittest
from tinylm.eval.paired_records import mc_metrics, summarize_paired, paired_rows, cluster_bootstrap
from support_report import paired_record


class PairedTests(unittest.TestCase):
    def test_skip_alignment_uses_id(self):
        left = [paired_record("a", 1), paired_record("b", None, status="skipped"),
                paired_record("c", 0)]
        right = [paired_record("b", 1), paired_record("c", 1)]
        result = summarize_paired(left, right, "correct")
        self.assertEqual(result["coverage"]["common"], 1)
        self.assertEqual(result["mean"], -1)
        self.assertIsNone(result["se"])

    def test_mean_margin_can_hide_wrong_best_choice(self):
        score = mc_metrics([1, 0, 100, 100], 0)
        self.assertGreater(score["mean_wrong_margin"], 0)
        self.assertLess(score["best_wrong_margin"], 0)
        self.assertEqual(score["correct"], 0)
        self.assertAlmostEqual(sum(score["choice_probabilities"]), 1)

    def test_duplicate_and_missing_provenance_fail(self):
        a = paired_record("a", 1)
        with self.assertRaises(ValueError):
            paired_rows([a, a], [a], "correct")
        b = dict(a)
        del b["item_sha256"]
        with self.assertRaises(ValueError):
            paired_rows([a], [b], "correct")

    def test_cross_tokenizer_ce_fails(self):
        a, b = paired_record("a", 1.0, metric="gold_ce"), paired_record("a", 1.1, metric="gold_ce")
        b["model_provenance"] = {"tokenizer_sha256": "different"}
        with self.assertRaises(ValueError):
            paired_rows([a], [b], "gold_ce")

    def test_mcnemar_and_family_bootstrap(self):
        left = [paired_record(str(i), 1, family=str(i // 2)) for i in range(4)]
        right = [paired_record(str(i), 0, family=str(i // 2)) for i in range(4)]
        result = summarize_paired(left, right, "correct")
        self.assertEqual(result["mcnemar_discordant"], [4, 0])
        self.assertAlmostEqual(result["mcnemar_exact_p"], 0.125)
        boot = cluster_bootstrap(left, right, "correct", draws=100, seed=2)
        self.assertIsInstance(boot, dict)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            mc_metrics([0, float("nan")], 0)
