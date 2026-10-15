#!/usr/bin/env python3
"""Actual selected parent and known code contract on CPU only; no forward."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
import json
import time
from unittest.mock import patch
from scripts import diag_p106b_dualqa_curriculum as course
from scripts.p106b_gate_runtime import GateNegative
TAG='p106b_dualqa_parent_wire_v1_s1337'
OUTPUT=ROOT/'test_result/evidence'/TAG


def run():
    import torch
    course.producer.legacy.source.deadline()
    if OUTPUT.exists():raise GateNegative('old CPU wire preserved')
    started=time.perf_counter()
    if torch.cuda.is_initialized():raise ValueError('fresh CPU-only process required')
    with patch.object(torch.nn.Module,'cuda',side_effect=AssertionError('CPU-only parent wire')),patch.object(torch.Tensor,'cuda',side_effect=AssertionError('CPU-only parent wire')):
        torch,model,cfg,tok,initial=course.load_parent()
        if {p.device.type for p in model.parameters()}!={'cpu'}:raise ValueError('all parent parameters must stay CPU')
        old,rows=course.old_code.read_course();chosen=course.data.code_rows(rows,course.TAG)
        known=course.data.known_contract(chosen,tok,course.data.binding.approved_questions())
        if len(chosen)!=4096 or len(known)!=3072:raise ValueError('actual verified code counts differ')
        if course.training.state_fingerprint(model)!=initial:raise ValueError('read-only CPU wire changed parent')
        if torch.cuda.is_initialized():raise ValueError('CPU wire initialized CUDA')
        value=dict(schema='P106B_DUALQA_PARENT_CPU_WIRE_V1',tag=TAG,status='ACTUAL_PARENT_AND_CODE_CPU_WIRED',
            source0_parent_sha256=course.producer.PARENT_SHA,core_before_after_sha256=initial,
            code_sha256={**course.info()['code_sha256'],'scripts/diag_p106b_dualqa_parent_wire.py':course.training.data.digest(Path(__file__))},
            actual_geometry=dict(layers=cfg.n_layers,dim=cfg.dim,ffn_dim=cfg.ffn_dim,vocab=cfg.vocab_size,
                max_seq=cfg.max_seq_len,tie_mlp=cfg.tie_mlp,mtp_aux=cfg.mtp_aux,visits=list(model.visit_schedule())),
            actual_code_rows=len(chosen),known_binding_labels=len(known),
            code_counts=dict(Counter(r['meta']['kind']+':'+r['meta']['language'] for r in chosen)),
            causal_suffix_events=sum(len(v['positions']) for v in known.values()),
            known_label_counts=dict(Counter(v['bit'] for v in known.values())),
            cuda_initialized=False,model_forwards=0,optimizer_updates=0,new_checkpoints=0,
            whole_sec=time.perf_counter()-started,source_student_course_frozen=False,
            scope='actual CPU geometry/metadata wiring only; not GPU, learning, semantic quality or completed teacher quotas')
    course.training.write(OUTPUT/'report.json',value)
    print('[DUALQA_PARENT_CPU_WIRE] '+json.dumps({k:v for k,v in value.items() if k!='code_sha256'}),flush=True)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit CPU execution required')
    try:return run()
    except GateNegative as exc:print('[DUALQA_PARENT_CPU_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[DUALQA_PARENT_CPU_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
