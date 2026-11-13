import unittest
import torch
from scripts.p106b_dskdv2_native import capture_native


class TinyHeadModel(torch.nn.Module):
    def __init__(self):
        super().__init__();self.emb=torch.nn.Embedding(11,3);self.norm=torch.nn.LayerNorm(3)
        self.head=torch.nn.Linear(3,11,bias=False);self.eval()
    def get_output_embeddings(self):return self.head
    def forward(self,ids):return self.head(self.norm(self.emb(ids)))


def fixed_call(model,inputs,*,width,pad_id,vocab,check,stats):
    check();padded=torch.full((1,width),pad_id,dtype=torch.long);padded[:,:inputs.shape[1]]=inputs
    with torch.no_grad():out=model(padded)
    if stats is not None:stats['calls']=stats.get('calls',0)+1
    return out[:,:inputs.shape[1],:].clone()


class NativeContracts(unittest.TestCase):
    def setUp(self):torch.set_num_threads(1);torch.manual_seed(1337)
    def test_full_width_head_and_original_prefix_are_observed_not_recomputed_or_vocab_truncated(self):
        model=TinyHeadModel();ids=torch.tensor([[1,2,3]]);stats={}
        logits,h,proof=capture_native(model,ids,fixed_call=fixed_call,width=8,vocab=11,hidden_width=3,pad_id=0,stats=stats)
        self.assertEqual(logits.shape,(1,3,11));self.assertEqual(h.shape,(3,3));self.assertEqual(stats['calls'],1)
        self.assertTrue(proof['head_output_matches_qualified_logits_exact'])
        self.assertEqual(proof['actual_body_width'],8);self.assertFalse(h.requires_grad)
        self.assertEqual(len(model.head._forward_pre_hooks),0);self.assertEqual(len(model.head._forward_hooks),0)
    def test_modified_returned_logits_are_rejected_and_all_hooks_are_removed(self):
        model=TinyHeadModel()
        def wrong(*args,**kwargs):return fixed_call(*args,**kwargs)+1
        with self.assertRaises(RuntimeError):capture_native(model,torch.tensor([[1,2]]),fixed_call=wrong,width=4,vocab=11,hidden_width=3,pad_id=0)
        self.assertFalse(model.head._forward_pre_hooks);self.assertFalse(model.head._forward_hooks)
    def test_multiple_native_head_calls_are_rejected_and_exception_does_not_leak_hooks(self):
        model=TinyHeadModel()
        def twice(*args,**kwargs):fixed_call(*args,**kwargs);return fixed_call(*args,**kwargs)
        with self.assertRaises(RuntimeError):capture_native(model,torch.tensor([[1,2]]),fixed_call=twice,width=4,vocab=11,hidden_width=3,pad_id=0)
        self.assertFalse(model.head._forward_pre_hooks);self.assertFalse(model.head._forward_hooks)
    def test_wrong_native_hidden_precision_is_rejected_without_implicit_conversion(self):
        model=TinyHeadModel().double()
        with self.assertRaises(ValueError):capture_native(model,torch.tensor([[1,2]]),fixed_call=fixed_call,width=4,vocab=11,hidden_width=3,pad_id=0)
        self.assertFalse(model.head._forward_pre_hooks);self.assertFalse(model.head._forward_hooks)


if __name__=='__main__':unittest.main()
