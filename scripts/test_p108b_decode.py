"""Decoder contracts without GPU/model loading or sample-loop duplication."""
import unittest
import torch
from scripts import p108b_decode as d
from tinylm.infer.generate import _pick


class DecodeTests(unittest.TestCase):
    def test_sign_aware_penalty_changes_repetition_but_does_not_mutate_logits(self):
        logits=torch.tensor([[10.,9.5,-20.,-30.,-40.]])
        original=logits.clone();picker=d.GeneratedTokenPenalty(_pick,1.2)
        self.assertEqual(int(picker(logits,0.,1)),0)
        self.assertEqual(int(picker(logits,0.,1)),1)
        self.assertTrue(torch.equal(logits,original))
        negative=torch.tensor([[-1.,-1.1,-20.,-30.,-40.]])
        picker=d.GeneratedTokenPenalty(_pick,1.2)
        self.assertEqual(int(picker(negative,0.,1)),0)
        self.assertEqual(int(picker(negative,0.,1)),1)

    def test_terminal_tokens_are_not_suppressed(self):
        picker=d.GeneratedTokenPenalty(_pick,2.)
        logits=torch.tensor([[-10.,-10.,10.,-10.,-10.]])
        self.assertEqual(int(picker(logits,0.,1)),2)
        self.assertEqual(int(picker(logits,0.,1)),2)

    def test_disabled_penalty_is_bit_identical_to_canonical_picker(self):
        picker=d.GeneratedTokenPenalty(_pick,1.)
        logits=torch.tensor([[1.,2.,3.,4.,5.]])
        for seed in (17,29,43):
            torch.manual_seed(seed);expected=_pick(logits,.7,3)
            torch.manual_seed(seed);actual=picker(logits,.7,3)
            self.assertTrue(torch.equal(expected,actual))
        self.assertEqual(picker.modified_slots,0)

    def test_private_function_does_not_mutate_owner_globals(self):
        def owner(x):return _pick(x,0.,1)
        altered=d.private_function(owner,_pick=lambda *_:torch.tensor([[0]]))
        x=torch.tensor([[0.,1.]])
        self.assertEqual(int(owner(x)),1)
        self.assertEqual(int(altered(x)),0)
        self.assertIs(owner.__globals__['_pick'],_pick)

    def test_settings_invalid_values_fail_before_generation(self):
        for kw in (dict(temperature=float('nan')),dict(top_k=-1),dict(repetition_penalty=.5)):
            with self.assertRaises(ValueError):d.Decoder('invalid',**kw)
        self.assertEqual(len(d.registered()),6)


if __name__=='__main__':unittest.main()
