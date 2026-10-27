"""Native generation protocol invariants; no backend/model initialization."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_gguf_resources as g

class GenerationContracts(unittest.TestCase):
    def test_actual_eos_and_fixed_eos_disabled_are_distinct(self):
        self.assertEqual(g.accept_generation([7,50256],4,True,1,10,10,[]),'EOS')
        self.assertEqual(g.accept_generation([7,50256],2,False,0,10,10,[]),'MAX_NEW_EOS_DISABLED')
        for values,cap,natural,reason,pos in [([7],4,False,0,9),([7],4,True,1,9),([50256],4,True,1,8),([50257],1,False,0,9)]:
            with self.assertRaises(ValueError):g.accept_generation(values,cap,natural,reason,pos,10,[])

    def test_observer_stream_requires_every_id_position_and_clock(self):
        event=[dict(index=0,token_id=3,native_seconds=.1,wall_seconds=.11),dict(index=1,token_id=4,native_seconds=.2,wall_seconds=.21)]
        g.accept_generation([3,4],2,False,0,10,10,event)
        for kind in ('missing','id','index','clock'):
            bad=deepcopy(event)
            if kind=='missing':bad.pop()
            elif kind=='id':bad[0]['token_id']=8
            elif kind=='index':bad[1]['index']=0
            else:bad[1]['wall_seconds']=.01
            with self.assertRaises(ValueError):g.accept_generation([3,4],2,False,0,10,10,bad)

    def test_timing_improvement_cannot_hide_changed_answer_or_cache(self):
        a=dict(generated_ids=[2,3],finish_reason='MAX_NEW_EOS_DISABLED',final_kv_position=10)
        self.assertTrue(g.same_generation(a,deepcopy(a)))
        for key,value in [('generated_ids',[2,4]),('finish_reason','EOS'),('final_kv_position',11)]:
            b=deepcopy(a);b[key]=value
            with self.assertRaises(ValueError):g.same_generation(a,b)

if __name__=='__main__':unittest.main()
