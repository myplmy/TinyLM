"""Reject absent/partial/unclean HOLD or a forecast that misses the new cap."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gguf_cpu_resume as d

def hold():
    return dict(mode='resources',device='cpu',exit_code=8,status='BUDGET_HOLD_NOT_FULL_SUITE',workloads=[],answers=[],
        numeric_canary=[dict(allclose=True,argmax_equal=True) for _ in range(16)],
        proof=dict(worker_returncode=0,worker_cleanup_complete=True,cleanup_diagnostics=[],telemetry_errors=[]),
        cost_admission=dict(conservative_seconds=3802.18))

class ExplicitBudget(unittest.TestCase):
    def test_separate_old_and_new_caps_with_closed_cpu_antecedent(self):
        r=d.budget_admission(hold());self.assertEqual((r['prior_execution_cap_seconds'],r['new_execution_cap_seconds']),(1800,5400))
        self.assertAlmostEqual(r['predicted_total_seconds'],4402.18)

    def test_no_cap_forgery_or_partial_or_unclean_execution(self):
        for kind in ('not_hold','partial','numeric','cleanup','too_slow','nan'):
            r=deepcopy(hold())
            if kind=='not_hold':r['exit_code']=0
            elif kind=='partial':r['workloads']=[{}]
            elif kind=='numeric':r['numeric_canary'][0]['allclose']=False
            elif kind=='cleanup':r['proof']['worker_returncode']=9
            elif kind=='too_slow':r['cost_admission']['conservative_seconds']=4900
            else:r['cost_admission']['conservative_seconds']=float('nan')
            with self.assertRaises(ValueError):d.budget_admission(r)

if __name__=='__main__':unittest.main()
