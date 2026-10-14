from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import diag_p106b_prefix_probe as probe


class Contracts(unittest.TestCase):
    def test_prompt_does_not_append_gold(self):
        row=probe.course.method.source.binding_rows('train',1)[0]
        changed=copy.deepcopy(row)
        changed['messages'][-1]['content'][0]['text']='ANSWER_ONLY_SENTINEL_7'
        self.assertEqual(probe.prompt(row),probe.prompt(changed))
        self.assertNotIn('ANSWER_ONLY_SENTINEL_7',probe.prompt(changed))

    def test_reject_wrong_producer_label(self):
        row=probe.course.method.source.binding_rows('train',1)[0]
        row['messages'][-1]['content'][0]['text']='not_the_registered_answer'
        with self.assertRaises(ValueError):probe.groups([row])

    def test_four_view_not_independent_roots(self):
        meta=[dict(root='a',label=0),dict(root='a',label=1),dict(root='a',label=1),dict(root='a',label=0)]
        r=probe.summarize_predictions(meta,[0,1,1,1])
        self.assertEqual((r['exact'],r['roots'],r['all4_exact_roots']),(3,1,0))
        with self.assertRaises(ValueError):probe.summarize_predictions(meta[:3],[0,1,1])

    def test_normalization_never_uses_dev_test(self):
        import torch
        train=torch.tensor([[0.,0.],[2.,0.]])
        transformed,others,mean,scale=probe.standardize(train,[torch.tensor([[100.,3.]])])
        self.assertTrue(torch.equal(mean,torch.tensor([1.,0.])))
        self.assertAlmostEqual(float(scale[1]),.01,places=6)
        self.assertTrue(torch.allclose(transformed[:,0],torch.tensor([-1.,1.])))
        self.assertAlmostEqual(float(others[0][0,0]),99.)

    def test_decode_hidden_flag_preserves_logits_and_backbone(self):
        import torch
        from scripts.test_p101a_sft_mtp import tiny
        model,cfg=tiny(False);model.eval();torch.set_num_threads(1)
        before=probe.course.base.training.state_fingerprint(model)
        ids=torch.tensor([[1,2,3]])
        with torch.no_grad():
            plain,kv=model(ids,use_cache=True,logits_last_only=True)
            observed,hidden,other=model(ids,use_cache=True,logits_last_only=True,return_mtp_hidden=True)
        self.assertTrue(torch.equal(plain,observed))
        self.assertEqual(tuple(hidden.shape),(1,1,cfg.dim))
        self.assertEqual(set(kv),set(other))
        self.assertEqual(before,probe.course.base.training.state_fingerprint(model))

    def test_sparse_layer_observer_is_removed_and_does_not_change_logits(self):
        import torch
        from scripts.test_p101a_sft_mtp import tiny
        model,cfg=tiny(False);model.eval();torch.set_num_threads(1)
        ids=torch.tensor([[1,2,3]])
        with torch.no_grad():
            before,_=model(ids,use_cache=True,logits_last_only=True)
            with probe.LayerCapture(model,(0,2)) as recorder:
                observed,_=model(ids,use_cache=True,logits_last_only=True)
                self.assertEqual(set(recorder.take()),{0,2})
                with self.assertRaises(ValueError):recorder.take()
            after,_=model(ids,use_cache=True,logits_last_only=True)
        self.assertTrue(torch.equal(before,observed))
        self.assertTrue(torch.equal(before,after))
        self.assertFalse(model.layers[0]._forward_hooks)

    def test_device_migration_precedes_transient_cache_freeze(self):
        from types import SimpleNamespace
        class Model:
            def __init__(self):self.device='cpu';self.calls=[];self._tlinear_cache=[]
            def clear_quant(self):self.calls.append('clear');self._tlinear_cache=[]
            def eval(self):self.calls.append('eval')
            def requires_grad_(self,value):self.calls.append(('grad',value))
            def cuda(self):self.calls.append('cuda');self.device='cuda:0';return self
            def freeze_quant(self):
                self.calls.append('freeze')
                self._tlinear_cache=[SimpleNamespace(_wq=SimpleNamespace(device=self.device))]
            def parameters(self):return iter([SimpleNamespace(device=self.device)])
        model=Model();self.assertIs(probe.prepare_model(model),model)
        self.assertEqual(model.calls,['clear','eval',('grad',False),'cuda','freeze'])
        self.assertEqual(model._tlinear_cache[0]._wq.device,'cuda:0')


if __name__=='__main__':unittest.main()
