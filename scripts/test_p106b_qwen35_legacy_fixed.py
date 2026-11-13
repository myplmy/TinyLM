from types import SimpleNamespace
import unittest
import torch
from scripts import p106b_qwen35_legacy_fixed as legacy
from scripts import diag_p106b_qwen35_text_core6 as q


class LegacyFixedContracts(unittest.TestCase):
    def toy(self,noncausal=False):
        calls=[];encoded=[]
        class Body:
            config=SimpleNamespace(vocab_size=19)
            def __call__(self,**kw):
                x=kw['input_ids'];mask=kw['attention_mask'];calls.append(tuple(x.shape))
                if tuple(x.shape)!=(1,128):raise AssertionError('fixed body required')
                if kw['use_cache'] or kw['past_key_values']is not None:raise AssertionError('state')
                h=(x.float()*mask).sum(1,keepdim=True).expand_as(x) if noncausal else x.float().cumsum(1)
                return SimpleNamespace(logits=h[:,:,None]*torch.arange(19).float()[None,None,:],past_key_values=None)
        class LM:
            device=torch.device('cpu')
            model=Body()
            def tok_encode(self,text,**kw):
                encoded.append(text);return [ord(c)%18 for c in text]
            def _model_call(self,x):return 'original'
            def loglikelihood(self,requests,**kw):
                answers=[]
                for r in requests:
                    a,b=r.args;x=self.tok_encode(a+b) or [1]
                    value=self._model_call(torch.tensor([x],dtype=torch.long))
                    answers.append((-abs(float(value.sum())),False))
                return answers
        return LM(),calls,encoded

    def test_exact_original_strings_and_bytecode_with_causal_toy(self):
        lm,calls,encoded=self.toy();body=lm.model;code=q.hybrid_canary.__code__
        r=legacy.exact_legacy_canary(lm,torch,width=128,pad_id=18)
        self.assertTrue(r['legacy_result']['passed']);self.assertIs(lm.model,body)
        self.assertIs(q.hybrid_canary.__code__,code);self.assertNotIn('_model_call',lm.__dict__)
        for text in ['Prefix for a causal state check',' one future',' another different future']:
            self.assertIn(text,encoded)
        self.assertTrue(all(shape==(1,128) for shape in calls))
        self.assertEqual(r['direct_body_stats']['serial_batch1_calls'],3)

    def test_future_dependent_toy_is_rejected_and_instance_restored(self):
        lm,_,_=self.toy(True);body=lm.model
        with self.assertRaisesRegex(ValueError,'prefix numerical oracle negative'):
            legacy.exact_legacy_canary(lm,torch,width=128,pad_id=18)
        self.assertIs(lm.model,body);self.assertNotIn('_model_call',lm.__dict__)

    def test_nonstateless_direct_calls_fail_closed(self):
        lm,_,_=self.toy();view=legacy.LegacyLMView(lm,width=128,pad_id=18)
        x=torch.ones(1,2,dtype=torch.long)
        for kw in [dict(use_cache=True),dict(past_key_values=object()),dict(logits_to_keep=1)]:
            with self.assertRaises(ValueError):view.model(input_ids=x,**kw)


if __name__=='__main__':unittest.main()
