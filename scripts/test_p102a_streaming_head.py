#!/usr/bin/env python3
"""CPU-only synthetic checks. No models, assets, tokenizers or CUDA calls."""
from pathlib import Path
import sys
import unittest
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tinylm.train.streaming_head import target_nll, vocab_nll
from tinylm.train.alm import target_nll as reference_nll


class TiedToy(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.emb = torch.nn.Embedding(19, 5)
        self.emb_up = torch.nn.Linear(5, 7, bias=False)

    def _emb_w(self):
        return self.emb.weight

    def _emb_up_w(self):
        return self.emb_up.weight

    def _head_logits(self, hidden):
        return F.linear(F.linear(hidden, self._emb_up_w().t()), self._emb_w())

    def hidden(self, x):
        return torch.tanh(F.linear(self.emb(x), self._emb_up_w()))


class StreamingTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(20261023)
        torch.set_num_threads(1)

    def pair(self, *, dtype=torch.float32, tile=4, weighted=True, nonlinear=False):
        p = torch.randn(9, 5, dtype=dtype) * .3
        e = torch.randn(19, 5, dtype=dtype) * .3
        y = torch.tensor([0, 18, 4, 7, 7, 2, 17, 16, 8])
        outer = torch.linspace(-1.1, 1.3, 9, dtype=dtype) if weighted else torch.ones(9, dtype=dtype)
        records = []
        for variant in (False, True):
            h, w = p.clone().requires_grad_(), e.clone().requires_grad_()
            loss = vocab_nll(h, w, y, tile=tile) if variant else F.cross_entropy(F.linear(h, w), y, reduction='none')
            total = ((loss.square() * .07 + loss.sin()) * outer).sum() if nonlinear else (loss * outer).sum()
            records.append((loss.detach(), *torch.autograd.grad(total, (h, w))))
        for a, b in zip(*records):
            torch.testing.assert_close(a, b, atol=2e-6, rtol=1e-5)

    def test_fp32_signed_outer(self): self.pair()
    def test_fp32_ce_sum(self): self.pair(weighted=False)
    def test_fp32_nonlinear_outer(self): self.pair(nonlinear=True)
    def test_fp64(self): self.pair(dtype=torch.float64)
    def test_one_vocabulary_tile(self): self.pair(tile=32)
    def test_one_column_tile(self): self.pair(tile=1)

    def test_gradcheck(self):
        h = (torch.randn(3, 2, dtype=torch.float64) * .1).requires_grad_()
        e = (torch.randn(7, 2, dtype=torch.float64) * .1).requires_grad_()
        self.assertTrue(torch.autograd.gradcheck(lambda h, e: vocab_nll(h, e, torch.tensor([0, 6, 2]), tile=3), (h, e)))

    def test_frozen_table(self):
        h = torch.randn(3, 2, requires_grad=True); e = torch.randn(7, 2)
        vocab_nll(h, e, torch.tensor([1, 3, 0]), tile=3).sum().backward()
        self.assertIsNotNone(h.grad)

    def test_tied_input_output_and_projection(self):
        self.tied(False)

    def test_tied_bf16_autocast(self):
        self.tied(True)

    def tied(self, amp):
        model = TiedToy(); initial = {k: v.clone() for k, v in model.state_dict().items()}
        x = torch.tensor([[1, 4, 7, 9], [3, 8, 2, 1]])
        y = torch.tensor([[2, -100, 7, 18], [-100, 4, 8, -100]])
        records = []
        for variant in (False, True):
            model.load_state_dict(initial); model.zero_grad(set_to_none=True)
            with torch.autocast('cpu', dtype=torch.bfloat16, enabled=amp):
                hidden = model.hidden(x); hidden.retain_grad()
                nll, mask = (target_nll(model, hidden, y, chunk=3, tile=4) if variant else reference_nll(model, hidden, y, chunk=3, checkpoint_head=False))
                outer = torch.tensor([[.3, -2., -1.1, .8], [1., .4, 1.2, -3.]])
                loss = ((nll * .1).sin() * outer).sum()
            loss.backward()
            self.assertTrue(torch.equal(nll.detach()[~mask], torch.zeros_like(nll[~mask])))
            self.assertTrue(torch.equal(hidden.grad[~mask], torch.zeros_like(hidden.grad[~mask])))
            records.append((nll.detach(), *(p.grad.clone() for p in model.parameters())))
        for a, b in zip(*records):
            # BF16 CPU is a mathematical wiring fixture, not a GPU update ruler.
            torch.testing.assert_close(a, b, atol=.02 if amp else 2e-6, rtol=.02 if amp else 1e-5)

    def test_empty_mask(self):
        model = TiedToy(); h = torch.randn(2, 3, 7, requires_grad=True)
        nll, valid = target_nll(model, h, torch.full((2, 3), -100))
        self.assertFalse(bool(valid.any())); nll.sum().backward()
        self.assertTrue(torch.equal(h.grad, torch.zeros_like(h)))

    def test_reject_invalid(self):
        h, e = torch.zeros(2, 3), torch.zeros(7, 3)
        for y, tile in ((torch.tensor([-100, 2]), 3), (torch.tensor([0, 7]), 3), (torch.tensor([0, 2]), 0), (torch.tensor([0, 2]), True)):
            with self.subTest(y=y, tile=tile), self.assertRaises(ValueError):
                vocab_nll(h, e, y, tile=tile)

    def test_zero_rows(self):
        h, e = torch.zeros(0, 3, requires_grad=True), torch.zeros(7, 3, requires_grad=True)
        nll = vocab_nll(h, e, torch.zeros(0, dtype=torch.long), tile=3)
        self.assertEqual(tuple(nll.shape), (0,)); nll.sum().backward()
        self.assertEqual(tuple(h.grad.shape), (0, 3))

    def test_optimizer_group_reference_scope(self):
        import gc
        import weakref
        from scripts.diag_p102a_streaming_head import fresh_optimizers
        class Engine:
            @staticmethod
            def optimizers(model):
                params=list(model.parameters())
                return torch.optim.SGD(params[:1],lr=.1), torch.optim.SGD(params[1:],lr=.2)
        model=TiedToy();refs=[weakref.ref(p) for p in model.parameters()]
        opts=fresh_optimizers(Engine,model)
        self.assertEqual(opts[0].param_groups[0]['lr'],5e-5)
        self.assertEqual(opts[1].param_groups[0]['lr'],2e-4)
        del opts,model
        gc.collect()
        self.assertTrue(all(ref() is None for ref in refs))

    def test_expired_guard_never_admits_cuda(self):
        from scripts.diag_p102a_streaming_head import checked_cuda
        class Model:
            calls=0
            def cuda(self):
                self.calls+=1
                raise AssertionError('expired model must not enter CUDA')
        class Expired:
            def check(self,stage): raise TimeoutError(stage)
        model=Model()
        with self.assertRaises(TimeoutError): checked_cuda(model,Expired())
        self.assertEqual(model.calls,0)

    def test_large_common_offset(self):
        p=torch.ones(3,1,requires_grad=True)
        e=(torch.arange(19).float().reshape(-1,1)*.125+100000).requires_grad_()
        labels=torch.tensor([0,18,8])
        a=F.cross_entropy(F.linear(p,e),labels,reduction='none')
        b=vocab_nll(p,e,labels,tile=4)
        torch.testing.assert_close(a,b,atol=2e-6,rtol=1e-5)
        ga=torch.autograd.grad((a*torch.tensor([.3,-.7,1.1])).sum(),(p,e),retain_graph=True)
        gb=torch.autograd.grad((b*torch.tensor([.3,-.7,1.1])).sum(),(p,e))
        # Shared-offset cancellation makes input VJP ill-conditioned; compare
        # the well-conditioned table VJP without disguising that limitation.
        torch.testing.assert_close(ga[1],gb[1],atol=2e-6,rtol=1e-5)

    def test_noncontiguous_inputs(self):
        h=torch.randn(8,6)[:,::2].requires_grad_()
        e=torch.randn(19,6)[:,::2].requires_grad_()
        labels=torch.arange(8)
        a=F.cross_entropy(F.linear(h,e),labels,reduction='none')
        b=vocab_nll(h,e,labels,tile=4)
        torch.testing.assert_close(a,b,atol=2e-6,rtol=1e-5)

    def test_actual_alm_nonlinear_vjp(self):
        from tinylm.train import alm
        model=TiedToy();initial={k:v.clone() for k,v in model.state_dict().items()}
        x=torch.tensor([[1,4,7,9],[3,8,2,1]])
        y=torch.tensor([[2,-100,7,18],[-100,4,8,-100]])
        chunks=[dict(row=0,positions=[0],teacher_logprob=-4.3),
                dict(row=0,positions=[2,3],teacher_logprob=-2.1),
                dict(row=1,positions=[1,2],teacher_logprob=-8.)]
        results=[]
        for candidate in (False,True):
            model.load_state_dict(initial);model.zero_grad(set_to_none=True)
            hidden=model.hidden(x)
            nll,mask=(target_nll(model,hidden,y,chunk=3,tile=4) if candidate else reference_nll(model,hidden,y,chunk=3))
            kl,count=alm.chunk_kl(nll,mask,chunks,temperature=100.)
            loss=alm.normalized_loss(nll.sum(),int(mask.sum()),kl,count,weight=17.)
            loss.backward()
            results.append((loss.detach(),*(p.grad.clone() for p in model.parameters())))
        for a,b in zip(*results): torch.testing.assert_close(a,b,atol=2e-6,rtol=1e-5)


if __name__ == '__main__':
    unittest.main()
