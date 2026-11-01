"""Observe value scale of one saved-history replay; original predicates unchanged."""
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_longkv_saved as replay
import torch


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    observer_sha=digest(Path(__file__))
    verifier_sha=digest(Path(replay.__file__))
    output=ROOT/'test_result/evidence/p106b_longkv_value_scale_v1_20261101'
    original=replay.compare_kv
    observations=[]

    def observe(left,right,module):
        result=original(left,right,module)
        values=[]
        for owner in sorted(left,key=str):
            for kind,a,b in zip(('K','V'),left[owner],right[owner]):
                delta=(a-b).double()
                target=b.double()
                rms=float(target.square().mean().sqrt())
                error=float(delta.square().mean().sqrt())
                values.append(dict(owner=str(owner),kind=kind,reference_abs_max=float(target.abs().max()),
                    reference_rms=rms,delta_abs_max=float(delta.abs().max()),delta_rms=error,
                    relative_l2=error/rms if rms else None,
                    violating_elements=int(((a-b).abs()>1e-4+1e-4*b.abs()).sum()),elements=b.numel()))
        observations.append(values)
        return result

    with patch.object(replay,'OUTPUT',output),patch.object(replay,'DOC_IDS',(509,)), \
         patch.object(replay,'POSITIONS',(0,8,255)),patch.object(replay,'compare_kv',observe):
        code=replay.execute()
    report=json.loads((output/'report.json').read_text())
    assert report['final_exit']==code==8 and report['status']=='SAVED_CPU_KV_NEGATIVE'
    assert len(observations)==len(report['cases'][0]['checks'])==3
    assert digest(Path(__file__))==observer_sha and digest(Path(replay.__file__))==verifier_sha
    receipt=dict(schema='P106B_LONGKV_SCALE_OBSERVER_V1',base_verifier_sha256=verifier_sha,
        observer_sha256=observer_sha,base_report_sha256=digest(output/'report.json'),
        original_thresholds_and_decisions_unchanged=True,actual_verifier_exit=code,
        doc_id=509,positions=[0,8,255],observations=observations,
        interpretation='SCALE_OBSERVATION_NOT_A_NEW_PASS_OR_CAUSAL_PROOF',
        new_answers=0,model_training=0,gpu=0)
    with (output/'value_scale.json').open('x') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(dict(actual_verifier_exit=code,scale_receipt_written=True)),flush=True)
    return code


if __name__=='__main__':raise SystemExit(main())
