#!/usr/bin/env python3
"""Strict RNG execution of the unchanged, byte-verified v1 QA corpus.

The v1 producer/code/reports stay immutable. A process-local adapter records
the new execution contract explicitly; it never relabels old JSON as current.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from contextlib import contextmanager,ExitStack
import copy
from datetime import datetime,timezone
import json
from unittest.mock import patch
from scripts import diag_p106b_grounded_span as source
from scripts.p106b_gate_runtime import GateNegative
TAG='p106b_grounded_span_exec_v2_s1337'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
CODE=(*source.CODE,'scripts/diag_p106b_grounded_span_execution.py','scripts/test_p106b_grounded_span_execution.py',
      'scripts/p106b_education_followup.py','scripts/diag_p101a_mtp_parity.py',
      'tinylm/chat/canonical.py','tinylm/chat/serialize.py','tinylm/data/sft.py',
      'tinylm/train/muon.py','tinylm/train/optimizer_audit.py')


def strict_head(dim,device='cpu',rank=64):
    import torch
    cpu_before=torch.random.get_rng_state().clone()
    cuda_before=torch.cuda.get_rng_state().clone() if torch.cuda.is_initialized() else None
    with torch.random.fork_rng(devices=[]):
        # torch.manual_seed also seeds CUDA even inside a CPU-only fork.
        # Seed only the CPU generator used by these CPU Linear constructors.
        torch.random.default_generator.manual_seed(20261016)
        head=torch.nn.ModuleDict({k:torch.nn.Linear(dim,rank,bias=False) for k in ('qs','ks','qe','ke')})
    head=head.to(device)
    if not torch.equal(cpu_before,torch.random.get_rng_state()):raise ValueError('CPU head RNG changed')
    if cuda_before is not None and not torch.equal(cuda_before,torch.cuda.get_rng_state()):
        raise ValueError('active CUDA head RNG changed')
    return head


def metadata(producer):
    value=source.info()
    value.update(tag=TAG,code_sha256={p:source.public.digest(ROOT/p) for p in sorted(set(CODE))},
        source_producer_tag=source.TAG,source_producer_report=str((source.CORPUS/'report.json').relative_to(ROOT)),
        source_producer_report_sha256=source.public.digest(source.CORPUS/'report.json'),
        source_producer_code_sha256=producer['code_sha256'],source_data_changed=False,
        seed_preservation='CPU_GENERATOR_FORK_AND_ACTIVE_CUDA_STATE_ASSERTED',
        source_and_execution_contracts_separate=True)
    return value


def adapted(producer,metadata):
    value=copy.deepcopy(producer)
    value.update(tag=TAG,code_sha256=metadata['code_sha256'],source_producer_report_sha256=metadata['source_producer_report_sha256'],
        source_producer_code_sha256=producer['code_sha256'],source_data_changed=False)
    return value


@contextmanager
def runtime(producer,rows,labels,run_info):
    contract=adapted(producer,run_info)
    with ExitStack() as stack:
        for name,value in dict(TAG=TAG,EVIDENCE=EVIDENCE,LOCAL=LOCAL,
                info=lambda:copy.deepcopy(run_info),read_course=lambda:(contract,rows,labels)).items():
            stack.enter_context(patch.object(source,name,value))
        stack.enter_context(patch.object(source.method,'new_head',strict_head))
        yield


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','cost','train','evaluate'),required=True)
    p.add_argument('--arm',choices=tuple(source.method.ARMS),default='span0');p.add_argument('--max-wall-sec',type=int,default=7200)
    group=p.add_mutually_exclusive_group(required=True);group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=21600:p.error('wall range60..21600')
    try:
        producer,rows,labels=source.read_course();run_info=metadata(producer)
        if a.check_only:print('[STRICT_SPAN_CHECK_ONLY] '+json.dumps(run_info));return 0
        source.deadline();a.max_wall_sec=min(a.max_wall_sec,int((source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-(2700 if a.mode=='train' else 600))
        if a.max_wall_sec<60:raise GateNegative('authorized closing margin')
        contract_path=EVIDENCE/'source_contract.json'
        if a.mode=='freeze':
            if EVIDENCE.exists():raise GateNegative('preserve old strict execution evidence')
            source.training.write(contract_path,dict(status='UNCHANGED_SOURCE_STRICT_RNG_EXECUTION_FROZEN',run_metadata=run_info,
                counts=producer['counts'],expected_updates=producer['expected_updates'],models_loaded=0,source_data_not_copied=True))
            print('[STRICT_SPAN_SOURCE] '+json.dumps(dict(tag=TAG,source_sha256=run_info['source_producer_report_sha256'],counts=producer['counts'],updates=producer['expected_updates'])),flush=True);return 0
        frozen=source.required(contract_path)
        if frozen['run_metadata']!=run_info:raise ValueError('strict execution code/source changed after freeze')
        with runtime(producer,rows,labels,run_info):
            return source.evaluate(a) if a.mode=='evaluate' else source.train(a,cost=a.mode=='cost')
    except GateNegative as exc:print('[STRICT_SPAN_HOLD] '+str(exc),flush=True);return 8
    except KeyboardInterrupt:print('[STRICT_SPAN_INTERRUPTED] raw new output retained',flush=True);return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[STRICT_SPAN_ERROR] '+type(exc).__name__+': '+str(exc),flush=True);return 9


if __name__=='__main__':raise SystemExit(main())
