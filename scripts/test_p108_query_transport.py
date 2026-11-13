import unittest
from types import SimpleNamespace
from unittest.mock import patch
import torch
from scripts import diag_p108_query_transport as d
from scripts import p108_value_edit as value


class QueryTransportContracts(unittest.TestCase):
    def test_capture_reuses_bytecode_with_private_last_position_adapter(self):
        self.assertIs(d.CAPTURE.__code__,d.old_transport.capture.__code__)
        self.assertIsNot(d.CAPTURE.__globals__,d.old_transport.capture.__globals__)
        self.assertIs(d.CAPTURE.__globals__['prior'],d.query)
        self.assertIsNot(d.old_transport.capture.__globals__['prior'],d.query)

    def test_observation_does_not_consume_the_generation_injection(self):
        layer=torch.nn.Linear(2,2,bias=False)
        with torch.no_grad():layer.weight.copy_(torch.eye(2))
        x=torch.zeros(1,3,2);delta=torch.tensor([1.,2.]);counts=[]
        from contextlib import contextmanager
        @contextmanager
        def oracle(*args):
            with value.inject(layer,2,delta):yield
        def observed(*args):counts.append(layer(x)[0,2].detach().clone());return {'logits':torch.tensor([0.,2.])}
        def generated(*args):counts.append(layer(x)[0,2].detach().clone());return {'generation':{'generated_ids':[1,4]}}
        fake=SimpleNamespace(oracle=oracle,prior=SimpleNamespace(generated=generated))
        with patch.object(d,'query',fake),patch.object(d,'capture',observed):
            d.local_answer({},layer,{},delta,None,'test')
        self.assertEqual(len(counts),2)
        for a in counts:torch.testing.assert_close(a,delta)
        torch.testing.assert_close(layer(x),x)

    def test_first_token_parity_fails_closed(self):
        d.first_token_parity(torch.tensor([0.,1.]),{'generation':{'generated_ids':[1,4]}})
        for ids in [[],[0,4]]:
            with self.assertRaises(RuntimeError):d.first_token_parity(torch.tensor([0.,1.]),{'generation':{'generated_ids':ids}})

    def test_logits_comparison_preserves_vocab_and_actual_difference(self):
        a=torch.tensor([1.,3.]);b=torch.tensor([2.,3.5]);r=d.compare_logits(a,b)
        self.assertEqual(r['max_abs'],1.);self.assertTrue(r['argmax_equal'])
        with self.assertRaises(ValueError):d.compare_logits(a,torch.zeros(3))


if __name__=='__main__':unittest.main()
