"""User-run CPU tests. Not executed during the read-only A16 audit."""
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tinylm.eval.reference_bench.artifacts import json_write, json_text, finite_json
from tinylm.eval.reference_bench.engine import ContextOverflow, TinyLMEngine, trim_at_stop
from tinylm.eval.reference_bench.korean_bench import classification_metrics, unique_predictions
from tinylm.eval.reference_bench.legacy_compare import paired_summary, source_key


class MetricContractTests(unittest.TestCase):
    def test_array_artifacts_preserve_values_and_unavailable_scores(self):
        import json
        import numpy as np
        self.assertEqual(json.loads(json_text(np.array([1, 2]))), [1, 2])
        self.assertEqual(finite_json(np.array([1.0, np.nan])), [1.0, None])

    def test_accuracy_is_not_macro_f1_for_collapsed_classifier(self):
        score = classification_metrics([0, 0, 0, 1], [0, 0, 0, 0], [0, 1])
        self.assertEqual(score["accuracy"], 0.75)
        self.assertAlmostEqual(score["macro_f1"], 3 / 7)

    def test_reference_label_revision_does_not_break_content_join(self):
        row = {"question": "Which?", "choices": ["a", "b"], "answer": 0}
        revised = {**row, "answer": 1, "correct_answer": "B"}
        self.assertEqual(source_key("mmlu_redux", row), source_key("mmlu_redux", revised))
        self.assertNotEqual(source_key("mmlu_redux", row),
                            source_key("mmlu_redux", {**row, "choices": ["b", "a"]}))

    def test_duplicate_prediction_ids_fail(self):
        with self.assertRaises(ValueError):
            unique_predictions([{"guid": "x", "prediction": 0},
                                {"guid": "x", "prediction": 1}])

    def test_skipped_item_never_shifts_the_pair(self):
        rows = [{"legacy_status": "scored", "legacy_correct": 0, "reference_correct": 1},
                {"legacy_status": "skipped_context", "legacy_correct": None, "reference_correct": 0},
                {"legacy_status": "scored", "legacy_correct": 1, "reference_correct": 0}]
        value = paired_summary(rows)
        self.assertEqual(value["paired_n"], 2)
        self.assertEqual(value["reference_only_correct"], 1)
        self.assertEqual(value["legacy_only_correct"], 1)

    def test_no_implicit_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            json_write(path, {"status": "first"})
            with self.assertRaises(FileExistsError):
                json_write(path, {"status": "second"})

    def test_declared_stop_removed_at_first_occurrence(self):
        self.assertEqual(trim_at_stop("answer\nQuestion: extra STOP", ["STOP", "\nQuestion:"]),
                         "answer")


class LikelihoodContractTests(unittest.TestCase):
    @staticmethod
    def engine():
        import torch
        e = TinyLMEngine.__new__(TinyLMEngine)
        e.torch, e.device, e.dtype_name = torch, torch.device("cpu"), "float32"
        e.eos_id = e.prefix_id = 0
        e.max_length, e.overflow = 4, "error"
        e.stats = {"likelihood_requests": 0, "generation_requests": 0,
                   "truncated_requests": 0, "removed_context_tokens": 0,
                   "max_input_tokens": 0, "generated_tokens": 0}
        # Analytic Markov chain: input 1 -> P(2)=0.6; input 2 -> P(3)=0.8.
        table = torch.tensor([[.7, .1, .1, .1], [.1, .1, .6, .2],
                              [.05, .05, .1, .8], [.7, .1, .1, .1]]).log()
        e.model = lambda x: table[x]
        return e

    def test_answer_sum_and_greedy_flag(self):
        e = self.engine()
        value, correct = e.loglikelihood_tokens([0, 1], [2, 3])
        self.assertAlmostEqual(value, math.log(.6) + math.log(.8), places=6)
        self.assertTrue(correct)
        other, correct = e.loglikelihood_tokens([1], [3])
        self.assertAlmostEqual(other, math.log(.2), places=6)
        self.assertFalse(correct)

    def test_empty_context_uses_eos_prefix(self):
        value, correct = self.engine().loglikelihood_tokens([], [0])
        self.assertAlmostEqual(value, math.log(.7), places=6)
        self.assertTrue(correct)

    def test_window_overflow_is_not_zero_or_silent_skip(self):
        with self.assertRaises(ContextOverflow):
            self.engine().loglikelihood_tokens([1, 1, 1, 1, 1], [2])
        e = self.engine()
        e.overflow = "left"
        e.loglikelihood_tokens([1, 1, 1, 1, 1], [2])
        self.assertEqual(e.stats["truncated_requests"], 1)
        self.assertEqual(e.stats["removed_context_tokens"], 1)

    def test_generation_stops_at_eos(self):
        e = self.engine()
        e.encode = lambda text: [0]
        e.decode = lambda ids: "".join("abc"[x - 1] for x in ids if x != 0)
        result = e.generate("prompt", 2)
        self.assertEqual(result["text"], "")
        self.assertEqual(result["completion_tokens"], 1)
        self.assertEqual(result["finish_reason"], "eos")


if __name__ == "__main__":
    unittest.main()
