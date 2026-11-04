"""CPU hook, cleanup and moving-competitor oracles, without model loading."""
import unittest
import torch

from scripts import diag_p108_attenuation_gpu as audit


class LocalActualContract(unittest.TestCase):
    def test_patch_only_selected_positions_then_restore(self):
        module=torch.nn.Identity()
        x=torch.arange(12,dtype=torch.float32).reshape(1,4,3)
        before=x.clone()
        with audit.patch_activation(module,[1,3],torch.ones(2,3)):
            y=module(x)
        torch.testing.assert_close(y[0,[1,3]],x[0,[1,3]]+1)
        self.assertTrue(torch.equal(y[0,[0,2]],x[0,[0,2]]))
        self.assertTrue(torch.equal(x,before))
        self.assertTrue(torch.equal(module(x),before))
        self.assertEqual(len(module._forward_hooks),0)

    def test_exception_removes_hook_without_masking_error(self):
        module=torch.nn.Identity()
        with self.assertRaisesRegex(RuntimeError,'original failure'):
            with audit.patch_activation(module,[0],torch.ones(1,2)):
                raise RuntimeError('original failure')
        self.assertEqual(len(module._forward_hooks),0)

    def test_zero_patch_is_byte_preserving_including_signed_zero(self):
        module=torch.nn.Identity();x=torch.tensor([[[-0.,0.]]])
        with audit.patch_activation(module,[0],torch.zeros(1,2)):
            out=module(x)
        self.assertIs(out,x)
        self.assertTrue(torch.equal(out.view(torch.int32),x.view(torch.int32)))

    def test_fixed_and_moving_competitor_are_distinct(self):
        logits=torch.tensor([[2.,1.,3.]])
        value=audit.measure(logits,[0],torch.tensor([1]))['tokens'][0]
        self.assertEqual((value['fixed_margin'],value['actual_margin']),(1.,-1.))
        self.assertEqual((value['fixed_competitor'],value['actual_competitor']),(1,2))

    def test_invalid_positions_values_and_shape_rejected(self):
        module=torch.nn.Identity()
        for positions,values in (([0,0],torch.zeros(2,2)),([-1],torch.zeros(1,2)),([0],torch.tensor([[float('nan'),0.]]))):
            with self.assertRaises(ValueError):
                with audit.patch_activation(module,positions,values):pass
        with self.assertRaises(ValueError):
            with audit.patch_activation(module,[1],torch.zeros(1,2)):module(torch.zeros(1,1,2))
        self.assertEqual(len(module._forward_hooks),0)

    def test_missing_or_second_visit_rejected_and_hook_removed(self):
        module=torch.nn.Identity()
        with self.assertRaises(ValueError):
            with audit.patch_activation(module,[0],torch.zeros(1,2)):pass
        with self.assertRaises(ValueError):
            with audit.patch_activation(module,[0],torch.zeros(1,2)):
                module(torch.zeros(1,1,2));module(torch.zeros(1,1,2))
        self.assertEqual(len(module._forward_hooks),0)

    def test_all_final_audits_run_after_one_failure_and_records_survive(self):
        events=[]
        def failure():
            events.append('cleanup');raise RuntimeError('workspace failure')
        report=dict(records=['actual observation'])
        good=audit.finish_checks(report,[('cleanup',failure),('source',lambda:events.append('source'))])
        self.assertFalse(good)
        self.assertEqual(events,['cleanup','source'])
        self.assertEqual(report['records'],['actual observation'])
        self.assertEqual(report['actual_exit'],9)
        self.assertEqual(report['final_verification_errors'][0]['stage'],'cleanup')


if __name__=='__main__':
    unittest.main()
