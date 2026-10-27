"""Only complete singleton controls can admit the separate resource suite."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gguf_prefill_control as d

def report():
    controls=[]
    for tile in d.TILES:
        controls.append(dict(prefill_chunk=tile,failed_workloads=[] if tile==1 else ['ko128'],numeric=[
            dict(workload=work,step=step,allclose=tile==1,argmax_equal=True) for work in ('ko128','en128','ko512','en512') for step in range(4)]))
    return dict(schema=d.SCHEMA,mode='diagnose',status='CONTROLLED_PREFILL_COMPLETE_NOT_ADOPTED',exit_code=0,
        controls=controls,proof=dict(worker_returncode=0,worker_cleanup_complete=True,cleanup_diagnostics=[],telemetry_errors=[]))

class SingletonAdmission(unittest.TestCase):
    def test_other_shape_negatives_are_preserved_not_waived(self):
        r=report();self.assertEqual(d.admit_singleton(r)['prefill_chunk'],1)
        self.assertFalse(r['controls'][2]['numeric'][0]['allclose'])

    def test_no_partial_or_top1_only_or_unclean_admission(self):
        for change in ('coverage','argmax','numeric','failed','duplicate','cleanup','exit'):
            r=deepcopy(report())
            if change=='coverage':r['controls'][0]['numeric'].pop()
            elif change=='argmax':r['controls'][0]['numeric'][0]['argmax_equal']=False
            elif change=='numeric':r['controls'][0]['numeric'][0]['allclose']=False
            elif change=='failed':r['controls'][0]['failed_workloads']=['ko128']
            elif change=='duplicate':r['controls'][2]['prefill_chunk']=1
            elif change=='cleanup':r['proof']['cleanup_diagnostics']=['Error']
            else:r['exit_code']=9
            with self.assertRaises(ValueError):d.admit_singleton(r)

if __name__=='__main__':unittest.main()
