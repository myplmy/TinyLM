"""Replay arithmetic and rollback contracts without loading any checkpoint."""
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
import torch
from scripts import p108b_replay as api


class ReplayTests(unittest.TestCase):
    def fixture(self):
        model=torch.nn.Linear(2,2,bias=False)
        with torch.no_grad():model.weight.copy_(torch.tensor([[1.,2.],[3.,4.]]))
        @contextmanager
        def edit(layer,delta):
            self.assertEqual(layer,0);before=model.weight.detach().clone()
            try:
                with torch.no_grad():model.weight.add_(delta)
                yield None
            finally:
                with torch.no_grad():model.weight.copy_(before)
        adapter=SimpleNamespace(model=model,modules={0:model},edit=edit)
        origin=dict(core_sha256=api.manual.state_fingerprint(model));values=[];references=[]
        before=model.weight.detach().clone()
        for j,delta in enumerate([torch.tensor([[.5,0.],[0.,-.25]]),torch.tensor([[-.125,0.],[0.,.5]])]):
            after=before+delta;values.append(dict(requested=delta,after=after))
            references.append(dict(layer=0,path=str(j),before_weight_sha256=api.metrics.tensor_sha(before),after_weight_sha256=api.metrics.tensor_sha(after)))
            before=after
        with torch.no_grad():model.weight.copy_(before)
        edited=api.manual.state_fingerprint(model)
        with torch.no_grad():model.weight.copy_(values[0]['after']-values[0]['requested'])
        arm=dict(name='repeat',origin=origin,packets=references,core_sha256=edited)
        return adapter,arm,values

    def test_ordered_repeat_is_exact_and_restores_after_success(self):
        adapter,arm,values=self.fixture()
        with api.install(adapter,arm,packets_loader=lambda r:values[int(r['path'])])as proof:
            self.assertTrue(torch.equal(adapter.model.weight,values[-1]['after']))
            self.assertEqual(len(proof['packet_receipts']),2)
        self.assertTrue(proof['original_core_restored'])

    def test_late_packet_failure_rolls_back_earlier_accepted_step(self):
        adapter,arm,values=self.fixture();values[1]['after']=values[1]['after']+1
        with self.assertRaises(ValueError):
            with api.install(adapter,arm,packets_loader=lambda r:values[int(r['path'])]):pass
        self.assertEqual(api.manual.state_fingerprint(adapter.model),arm['origin']['core_sha256'])

    def test_evaluation_exception_also_rolls_back(self):
        adapter,arm,values=self.fixture()
        with self.assertRaisesRegex(RuntimeError,'intentional'):
            with api.install(adapter,arm,packets_loader=lambda r:values[int(r['path'])]):raise RuntimeError('intentional')
        self.assertEqual(api.manual.state_fingerprint(adapter.model),arm['origin']['core_sha256'])

    def test_sparse_escape_and_reordered_predecessor_are_rejected(self):
        adapter,arm,values=self.fixture();values[0]['mask']=torch.zeros(2,2,dtype=torch.bool)
        with self.assertRaises(ValueError):api.validate_physical(arm['packets'][0],values[0],adapter.model.weight)
        with self.assertRaises(ValueError):api.validate_physical(arm['packets'][1],values[1],adapter.model.weight)


if __name__=='__main__':unittest.main()
