from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts.p106b_padding_probe import width,close_fp32


class Padding(unittest.TestCase):
    def test_round_up_never_truncates_or_packs(self):
        self.assertEqual(width([1,33,127],True),128)
        self.assertEqual(width([129,700],True),768)
        self.assertEqual(width([1024],True),1024)
        self.assertEqual(width([2],False),1024)
        for values in ([],[0],[1025],[1.5]):
            with self.assertRaises(ValueError):width(values,True)

    def test_valid_tokens_targets_and_segments_are_identical(self):
        from tinylm.train.mtp_sft import Record,pad_records
        import torch
        records=[Record([1,2,3],[-100,4,5],[0,1,1]),Record([7],[8],[1])];before=copy.deepcopy(records)
        a=pad_records(records,0,'cpu',fixed_width=1024,batch_size=8)
        b=pad_records(records,0,'cpu',fixed_width=width([len(r.x) for r in records],True),batch_size=8)
        for left,right in zip(a,b):self.assertTrue(torch.equal(left[:,:128],right))
        self.assertTrue(a[1][:,128:].eq(-100).all());self.assertTrue(a[2][:,128:].eq(0).all())
        self.assertEqual(records,before)

    def test_diagnostic_bound_does_not_become_quality_judgment(self):
        self.assertTrue(close_fp32(1.,1.000001,.000001,.9999999))
        self.assertFalse(close_fp32(1.,1.1,0.,1.))
        self.assertFalse(close_fp32(1.,1.,float('nan'),1.))

    def test_tiny_cpu_model_valid_loss_and_gradients_are_close(self):
        import torch
        from scripts.test_p101a_sft_mtp import tiny
        from tinylm.train.mtp_sft import Record,pad_records,components
        threads=torch.get_num_threads();torch.set_num_threads(1)
        try:
            model,cfg=tiny(False);cfg.grad_checkpoint=True;model.train()
            rows=[Record([1,2,3,4,5],[-100,-100,4,5,6],[0,0,1,1,1]),Record([7,8,9],[-100,9,10],[0,1,1])]
            before={k:v.clone() for k,v in model.state_dict().items()};observed=[]
            for trim in (False,True):
                model.zero_grad(set_to_none=True)
                w=width([len(r.x) for r in rows],trim,alignment=8,ceiling=32)
                x,y,seg=pad_records(rows,0,'cpu',fixed_width=w,batch_size=2)
                hidden=model(x,return_hidden=True);sums,counts=components(model,hidden,y,seg,horizons=())
                loss=sums[1]/counts[1];loss.backward()
                observed.append((float(loss.detach()),{n:p.grad.clone() for n,p in model.named_parameters() if p.grad is not None}))
            self.assertAlmostEqual(observed[0][0],observed[1][0],places=5)
            self.assertEqual(observed[0][1].keys(),observed[1][1].keys())
            for name,value in observed[0][1].items():
                self.assertTrue(torch.allclose(value,observed[1][1][name],atol=1e-5,rtol=1e-5),name)
            for name,value in before.items():self.assertTrue(torch.equal(value,model.state_dict()[name]),name)
        finally:torch.set_num_threads(threads)

    def test_full_gradient_statistics_reject_nonfinite_values(self):
        import torch
        from scripts.diag_p106b_padding_probe import gradient_comparison
        model=torch.nn.Linear(2,1);model(torch.ones(1,2)).sum().backward()
        reference={name:p.grad.clone() for name,p in model.named_parameters()}
        self.assertAlmostEqual(gradient_comparison(model,reference)['cosine'],1.)
        model.weight.grad[0,0]=float('nan')
        with self.assertRaises(ValueError):gradient_comparison(model,reference)


if __name__=='__main__':unittest.main()
