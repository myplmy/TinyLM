"""Check predictor selection against hand-calculated probabilities on CPU."""

from dataclasses import replace
import math
import unittest

import numpy as np

from scripts.p106b_official_lm_adapter import plan_tokens
from scripts.p106b_prism_likelihood import PrismLikelihood


class FakeNative:
    vocab_size = 4
    context_limit = 4

    def __init__(self):
        self.calls = []

    def tokenize(self, text, *, add_special):
        assert add_special is False
        return [int(ch) for ch in text if ch != ' ']

    def logits(self, prefix):
        self.calls.append(tuple(prefix))
        return np.array([0, 2, 2, 0] if prefix[-1] == 0 else [1, 0, 1, 2], dtype=np.float32)


class Template:
    @staticmethod
    def _encode_pair(encoder, context, target):
        left = encoder.tok_encode(context)
        whole = encoder.tok_encode(context+target)
        return left, whole[len(left):]


class PrismLikelihoodTests(unittest.TestCase):
    def setUp(self):
        self.native = FakeNative()
        self.lm = PrismLikelihood(self.native, Template, 0)

    def test_every_subword_uses_its_causal_prefix_and_tie_order(self):
        result = self.lm.score([self.lm.plan('0','13')])[0]
        first = 2-math.log(2+2*math.exp(2))
        second = 2-math.log(1+2*math.e+math.exp(2))
        self.assertEqual(self.native.calls, [(0,), (0,1)])
        self.assertAlmostEqual(result['response'][0],first+second,places=13)
        self.assertTrue(result['response'][1])
        self.assertEqual(result['greedy_ids'],[1,3])

    def test_shared_prefix_and_lower_index_greedy(self):
        first, second = self.lm.score([self.lm.plan('0','1'), self.lm.plan('0','2')])
        self.assertEqual(self.native.calls,[(0,)])
        self.assertEqual(first['response'][0],second['response'][0])
        self.assertEqual((first['response'][1],second['response'][1]),(True,False))
        self.lm.score([self.lm.plan('0','1')])
        self.assertEqual(self.native.calls,[(0,), (0,)])

    def test_empty_context_and_left_context_only_crop(self):
        for target in ('13', '013'):
            plan = self.lm.plan('',target)
            self.assertEqual(plan.input_ids,(0,1))
            self.assertEqual(plan.continuation_ids,(1,3))
        plan=self.lm.plan('22220','13')
        self.assertEqual(plan.input_ids,(2,2,0,1))
        self.assertEqual(plan.continuation_ids,(1,3))
        self.assertEqual(plan.truncated_context_tokens,2)
        with self.assertRaises(ValueError):
            self.lm.plan('0','11111')

    def test_joint_token_boundary_mismatch_fails_before_forward(self):
        original = self.native.tokenize
        self.native.tokenize = lambda text, **kw: [2,3] if text=='01' else original(text,**kw)
        with self.assertRaisesRegex(ValueError,'joint native encoding'):
            self.lm.plan('0','1')
        self.assertEqual(self.native.calls,[])

    def test_validates_every_candidate_before_forward(self):
        plan = self.lm.plan('0','1')
        invalid = plan_tokens([0,1],[2,3],4,4)
        invalid = replace(invalid,input_ids=(9,))
        with self.assertRaises(ValueError):
            self.lm.score([plan,invalid])
        self.assertEqual(self.native.calls,[])


if __name__ == '__main__':
    unittest.main()
