from types import SimpleNamespace
import unittest
import torch
from scripts import p106b_qwen35_fixedshape as f


class FixedShapeContracts(unittest.TestCase):
    def test_real_eos_is_not_confused_with_right_padding(self):
        x=torch.tensor([[2,7,3],[4,5,6]])
        p,m=f.padded_inputs(x,width=8,pad_id=7,vocab=9)
        torch.testing.assert_close(p[:,:3],x)
        self.assertTrue(bool((p[:,3:]==7).all()));self.assertEqual(m[0,1],1)
        self.assertTrue(bool((m[:,:3]==1).all()));self.assertTrue(bool((m[:,3:]==0).all()))

    def test_invalid_lengths_ids_and_types_fail_closed(self):
        for x in [torch.empty(1,0,dtype=torch.long),torch.zeros(1,9,dtype=torch.long),
                  torch.tensor([[-1]]),torch.tensor([[9]]),torch.ones(1,3),torch.tensor([1,2])]:
            with self.assertRaises(ValueError):f.padded_inputs(x,width=8,pad_id=7,vocab=9)

    def model(self,noncausal=False):
        calls=[]
        class Tiny:
            config=SimpleNamespace(vocab_size=5)
            def __call__(self,**kw):
                ids=kw['input_ids'];calls.append((ids.clone(),kw['attention_mask'].clone()))
                if tuple(ids.shape)!=(1,8):raise AssertionError('body shape changed')
                if kw['use_cache'] or kw['past_key_values']is not None or kw['logits_to_keep']!=0:raise AssertionError('state/head')
                h=ids.float().sum(1,keepdim=True).expand_as(ids) if noncausal else ids.float().cumsum(1)
                return SimpleNamespace(logits=h[:,:,None]*torch.arange(5).float()[None,None,:],past_key_values=None)
        return Tiny(),calls

    def test_full_head_shape_and_serial_batch1_are_observed(self):
        model,calls=self.model();x=torch.tensor([[1,2,3],[2,3,1]]);stats={}
        out=f.logits(model,x,width=8,pad_id=4,vocab=5,stats=stats)
        self.assertEqual(tuple(out.shape),(2,3,5));self.assertEqual(len(calls),2)
        self.assertEqual(stats,dict(serial_batch1_calls=2,real_input_slots=6,fixed_input_slots=16))
        self.assertEqual(out.untyped_storage().nbytes(),out.numel()*out.element_size())

    def test_causal_and_deliberately_future_dependent_toys_are_distinguished(self):
        for noncausal in [False,True]:
            model,_=self.model(noncausal)
            a=f.logits(model,torch.tensor([[1,2]]),width=8,pad_id=4,vocab=5)
            b=f.logits(model,torch.tensor([[1,2,3]]),width=8,pad_id=4,vocab=5)
            r=f.compare_prefix(a,b,atol=1e-5,rtol=1e-4,chunk_positions=1)
            self.assertEqual(r['close'],not noncausal)

    def test_instance_adapter_restores_class_and_instance_overrides_on_exception(self):
        model,_=self.model()
        class LM:
            def _model_call(self,*args,**kw):return 'original'
        for with_override in [False,True]:
            lm=LM();lm.model=model
            if with_override:lm._model_call=lambda *a:'custom'
            expected=lm._model_call(None)
            with self.assertRaisesRegex(RuntimeError,'abort'):
                with f.fixed_calls(lm,width=8,pad_id=4):
                    self.assertEqual(lm._model_call(torch.tensor([[1,2]])).shape,(1,2,5))
                    raise RuntimeError('abort')
            self.assertEqual(lm._model_call(None),expected)
            self.assertEqual('_model_call'in lm.__dict__,with_override)

    def test_external_masks_and_loss_labels_still_rejected(self):
        model,_=self.model();lm=SimpleNamespace(model=model)
        with f.fixed_calls(lm,width=8,pad_id=4):
            for key in ['attn_mask','labels']:
                with self.assertRaises(ValueError):lm._model_call(torch.tensor([[1]]),**{key:torch.ones(1,1)})

    def test_chunk_comparison_matches_direct_torch_tolerance(self):
        a=torch.arange(48,dtype=torch.float32).reshape(1,12,4);b=a.clone();b[0,9,2]+=.01
        r=f.compare_prefix(a,b,atol=1e-5,rtol=1e-4,chunk_positions=3)
        self.assertEqual(r['close'],bool(torch.allclose(a,b,atol=1e-5,rtol=1e-4)))
        self.assertEqual(r['outside_tolerance'],int((~torch.isclose(a,b,atol=1e-5,rtol=1e-4)).sum()))
        self.assertAlmostEqual(r['max_abs'],float((a-b).abs().max()))
        with self.assertRaises(ValueError):f.compare_prefix(a,b[:,:,:2],atol=1e-5,rtol=1e-4)


if __name__=='__main__':unittest.main()
