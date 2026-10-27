"""Driver admission and source fixture determinism without model/assets."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from scripts import diag_p013_context_curriculum as d


class DriverContract(unittest.TestCase):
    def test_fixture_uses_only_start_rng_and_preserves_target_shift(self):
        source=d.WindowFixture();oracle=np.random.default_rng(1337)
        for _ in range(16):
            x,y=source();oracle.integers(0,2**42,8)
            self.assertEqual(x.shape,(8,1024));self.assertTrue(torch.equal(x[:,1:],y[:,:-1]))
            self.assertTrue(bool((x>=8).all()) and bool((y<32768).all()))
        self.assertEqual(source.calls,16);self.assertEqual(source.rng.bit_generator.state,oracle.bit_generator.state)

    def test_unapproved_profile_rejected_before_native_reference_read(self):
        with patch.object(d.resource,'read_ref',side_effect=AssertionError('asset read forbidden')) as read:
            with self.assertRaises(ValueError):d.validate({'schema':'WRONG'},SimpleNamespace(mode='cost',max_wall_sec=900))
            self.assertFalse(read.called)

    def test_model_phase_requires_full_same_source_cpu_contract(self):
        source=dict(files={},sha256='A'*64);report=dict(exit_code=0,mode='contract',source=source,profile_sha256='B'*64,
            result=dict(original_target_positions_checked=786432,source_calls=96,model_forwards=0))
        d.closed_contract(report,source=source,profile_sha256='B'*64)
        for kind in ('rows','source','profile','forward','exit'):
            other=deepcopy(report)
            if kind=='rows':other['result']['original_target_positions_checked']=131072
            elif kind=='source':other['source']['sha256']='C'*64
            elif kind=='profile':other['profile_sha256']='C'*64
            elif kind=='forward':other['result']['model_forwards']=1
            else:other['exit_code']=9
            with self.subTest(kind=kind),self.assertRaises(ValueError):d.closed_contract(other,source=source,profile_sha256='B'*64)

    def test_gradient_cleanup_failure_does_not_skip_quant_cleanup(self):
        calls=[]
        class Broken:
            def zero_grad(self,**kwargs):calls.append('zero');raise RuntimeError('gradient cleanup failed')
            def clear_quant(self):calls.append('quant')
        report={};errors=d.cleanup_cost_model(Broken(),report)
        self.assertEqual(calls,['zero','quant']);self.assertEqual(errors[0]['stage'],'zero_grad')
        self.assertEqual(report['cost_model_cleanup_errors'],errors)

    def test_each_successful_update_and_peak_survive_later_block_failure(self):
        for fail_index in (1,2):
            report={'blocks':[]}
            def run(index):
                if index==fail_index:raise RuntimeError('injected update failure')
                return dict(seconds=index+1.)
            with self.subTest(index=fail_index),self.assertRaisesRegex(RuntimeError,'injected update failure'):
                d.record_cost_block(0,256,report,run,lambda:None,lambda:dict(peak_allocated_bytes=123))
            row=report['blocks'][0]
            self.assertEqual(row['warmup'],{'seconds':1.})
            self.assertEqual(len(row['measured']),fail_index-1)
            self.assertEqual(row['peak_allocated_bytes'],123)
            self.assertEqual(row['status'],'PARTIAL_BLOCK_ERROR')

    def test_two_cleanup_failures_do_not_replace_primary_cost_error(self):
        calls=[]
        class Broken:
            def zero_grad(self,**kwargs):calls.append('zero');raise RuntimeError('zero failed')
            def clear_quant(self):calls.append('quant');raise RuntimeError('quant failed')
        original={'type':'ValueError','message':'original backward error'}
        report={'primary_cost_error':deepcopy(original)}
        errors=d.cleanup_cost_model(Broken(),report)
        self.assertEqual(calls,['zero','quant']);self.assertEqual([x['stage'] for x in errors],['zero_grad','clear_quant'])
        self.assertEqual(report['primary_cost_error'],original)

    def test_late_exit_timeout_cannot_reclassify_original_compute_error_as_hold(self):
        report=dict(primary_cost_error=dict(type='RuntimeError',message='original backward failure'),primary_cost_error_is_timeout=False)
        self.assertEqual(d.failure_outcome(TimeoutError('later cleanup timeout'),report),('ERROR_NOT_COMPLETE',9))
        self.assertEqual(d.failure_outcome(TimeoutError('real budget only'),{}),('BUDGET_HOLD_NOT_FULL_SUITE',8))
        report['primary_cost_error_is_timeout']=True
        self.assertEqual(d.failure_outcome(RuntimeError('cleanup failed after budget'),report),('ERROR_NOT_COMPLETE',9))


if __name__=='__main__':unittest.main()
