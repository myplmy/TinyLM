"""Upstream adapter boundary tests, CPU only; user execution is required."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import tinylm
from lm_eval.api.instance import Instance
from tokenizers import Tokenizer, models, pre_tokenizers
from tinylm.eval.reference_bench.lm_adapter import TinyLMHarness


class RecordingEngine:
    def __init__(self):
        self.tokenizer = Tokenizer(models.WordLevel(
            {"<eos>": 0, "<unk>": 1, "a": 2, "b": 3, "c": 4}, unk_token="<unk>"))
        self.tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
        self.eos_id = self.prefix_id = 0
        self.max_length = 3
        self.overflow = "error"
        self.device = "cpu"
        self.identity = {"tokenizer_sha256": "fixture"}
        self.encoded, self.scored = [], []

    def encode(self, text):
        self.encoded.append(text)
        return self.tokenizer.encode(text, add_special_tokens=False).ids

    def decode(self, ids):
        return self.tokenizer.decode(ids)

    def loglikelihood_tokens(self, context, continuation):
        self.scored.append((context, continuation))
        return -float(len(continuation)), True


class HarnessContractTests(unittest.TestCase):
    def test_joint_tokenization_transfers_trailing_context_space(self):
        e = RecordingEngine()
        adapter = TinyLMHarness(e)
        context, continuation = adapter._encode_pair("a ", "b")
        self.assertEqual(context, [2])
        self.assertEqual(continuation, [3])
        self.assertIn("a b", e.encoded)
        self.assertIn("a", e.encoded)
        self.assertNotIn("b", e.encoded)

    def test_rolling_window_scores_each_token_once(self):
        e = RecordingEngine()
        adapter = TinyLMHarness(e)
        request = Instance(request_type="loglikelihood_rolling", doc={},
                           arguments=("a b c a b c a",), idx=0)
        values = adapter.loglikelihood_rolling([request])
        self.assertEqual(values, [-7.0])
        targets = [token for _, continuation in e.scored for token in continuation]
        self.assertEqual(targets, [2, 3, 4, 2, 3, 4, 2])
        self.assertTrue(all(len(context) + len(cont) - 1 <= 3 for context, cont in e.scored))

    def test_unsupported_generation_kwarg_is_not_ignored(self):
        adapter = TinyLMHarness(RecordingEngine())
        request = Instance(request_type="generate_until", doc={},
                           arguments=("a", {"max_gen_toks": 1, "unknown_knob": True}), idx=0)
        with self.assertRaisesRegex(ValueError, "unknown_knob"):
            adapter.generate_until([request])


if __name__ == "__main__":
    unittest.main()
