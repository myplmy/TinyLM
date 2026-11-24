"""CPU toy hook/cached-prompt contracts, not TinyLM quality evidence."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import torch
from scripts import p108c_runtime as r


class Block(torch.nn.Module):
    def __init__(self, factor):
        super().__init__()
        self.down = torch.nn.Linear(2, 2, bias=False)
        with torch.no_grad():
            self.down.weight.copy_(torch.tensor([[factor, 0.], [0., factor]]))

    def forward(self, x):
        return x + self.down(x)


class RuntimeContracts(unittest.TestCase):
    def test_current_question_offsets_exclude_previous_identical_question(self):
        text = "Hi! old reply. Hi! assistant"
        offsets = [(i, i+1) for i in range(len(text))]
        found = r.question_indices(text, "Hi!", offsets)
        self.assertEqual(found, [15, 16, 17])

    def test_missing_span_and_incomplete_unicode_coverage_rejected(self):
        with self.assertRaises(ValueError):
            r.question_indices("abc", "other", [(0, 3)])
        with self.assertRaises(ValueError):
            r.question_indices("질문", "질문", [(0, 1)])

    def test_whitespace_need_not_have_own_token(self):
        self.assertEqual(r.question_indices("a b", "a b", [(0, 1), (2, 3)]), [0, 1])

    def test_layer_features_match_independent_toy_forward(self):
        layers = {0:Block(2.), 1:Block(3.)}
        modules = {i:l.down for i,l in layers.items()}
        x = torch.tensor([[[1., 2.], [3., 4.], [5., 6.]]])
        def forward():
            return layers[1](layers[0](x))
        actual = r.capture_features(layers, modules, [1, 2, 3], [0, 1], forward)
        np.testing.assert_array_equal(actual["key_last"], [[5, 6], [15, 18]])
        np.testing.assert_array_equal(actual["key_question_mean"], [[2, 3], [6, 9]])
        np.testing.assert_array_equal(actual["residual_last"], [[15, 18], [60, 72]])
        np.testing.assert_array_equal(actual["residual_question_mean"], [[6, 9], [24, 36]])
        self.assertTrue(all(not m._forward_hooks for m in modules.values()))
        self.assertTrue(all(not m._forward_hooks for m in layers.values()))

    def test_failure_also_removes_all_feature_hooks(self):
        layer = Block(2.)
        def broken():
            layer(torch.ones(1, 2, 2))
            raise RuntimeError("injected failure")
        with self.assertRaises(RuntimeError):
            r.capture_features({0:layer}, {0:layer.down}, [1, 2], [0], broken)
        self.assertFalse(layer._forward_hooks)
        self.assertFalse(layer.down._forward_hooks)

    def test_alias_and_invalid_position_fail_before_forward(self):
        layer = Block(2.)
        with self.assertRaises(ValueError):
            r.capture_features({0:layer, 1:layer}, {0:layer.down, 1:layer.down},
                               [1], [0], lambda: self.fail("must not execute"))
        with self.assertRaises(ValueError):
            r.capture_features({0:layer}, {0:layer.down}, [1], [1],
                               lambda: self.fail("must not execute"))

    def test_feature_view_decision_has_no_answer_or_family_dependency(self):
        gate = r.RoutedEdit.__new__(r.RoutedEdit)
        gate.feature_view = "key_last"; gate.feature_layer = 1; gate.threshold = .5
        gate.router = dict(kind="ridge", center=np.zeros(2), scale=np.ones(2),
                           coefficient=np.array([1., 0.]))
        obs = dict(features={"key_last":np.array([[0., 1.], [1., 0.]])},
                   expected="unused", family="unused")
        self.assertEqual(gate.decide(obs), (True, 1.))
        obs["expected"] = "different"; obs["family"] = "different"
        self.assertEqual(gate.decide(obs), (True, 1.))

    def test_cached_actual_history_mismatch_rejected_before_emit(self):
        gate = r.RoutedEdit.__new__(r.RoutedEdit)
        gate.prompt = lambda *args: ("new prompt", [2], [0])
        with self.assertRaises(ValueError):
            gate.emit("question", observation=dict(ids=[1], prompt_sha256="old"))


if __name__ == "__main__":
    unittest.main()
