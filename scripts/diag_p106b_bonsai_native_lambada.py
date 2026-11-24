"""Evaluate the pinned Bonsai GGUF on official LAMBADA with Prism CAPI logits."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import sysconfig
import time
from unittest.mock import patch

import numpy as np

from scripts import diag_p106b_lambada_default as official
from scripts import diag_p106b_prism_native_raw as prism
from scripts.interactive_research_infer import require_idle_gpu
from scripts.p106b_official_lm_adapter import canonical, prepare_harness
from scripts.p106b_prism_likelihood import PrismLikelihood
from scripts.p106b_shards import ShardWriter


ROOT = prism.ROOT
TAG = 'p106b_bonsai_native_lambada_v1_20261118'
OUT = ROOT / 'test_result/evidence' / TAG
PROFILE = OUT / 'profile.json'
READBACK = prism.AUDIT / 'PRISM_NATIVE_RAW_CLOSED_READBACK_v1.json'
CUTOFF = datetime.fromisoformat('2026-11-18T16:30:00+09:00').timestamp()
HARD_SECONDS = 2400
OUTPUT_CAP = 64_000_000
EOT = 248046
SOURCES = (
    'scripts/diag_p106b_bonsai_native_lambada.py', 'scripts/p106b_prism_likelihood.py',
    'scripts/test_p106b_prism_likelihood.py', 'scripts/diag_p106b_lambada_default.py',
    'scripts/p106b_official_lm_adapter.py', 'scripts/prepare_p106b_official_eval.py',
    'scripts/p106b_shards.py', 'scripts/interactive_research_infer.py',
)


class Hold(ValueError):
    pass


def source_pins():
    return {name:prism.digest(ROOT/name) for name in SOURCES}


def records():
    # The old loader owns the task semantics. Only its parquet cache path changes
    # in this process, to keep existing evaluation namespaces immutable.
    with patch.object(official,'CACHE',OUT/'task_cache'):
        task, definition = official.load_task()
    requests = [official.request_for(task,doc,i) for i,doc in enumerate(task.eval_docs)]
    assert len(requests) == official.ROWS
    sha = hashlib.sha256()
    for request in requests:
        sha.update(canonical(list(request.args))+bytes((10,)))
    return task, definition, requests, sha.hexdigest().upper()


def prepare():
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('CPU preparation requires an empty CUDA device selection')
    import torch
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=False)
    old = prism.verify()
    readback = prism.read(READBACK)
    assert readback['process_exit'] == 0 and readback['same_A_bits_exact']
    assert readback['profile']['sha256'] == prism.digest(prism.PROFILE)
    a0 = ROOT/readback['native_vectors']['A0']['path']
    assert a0 == prism.OUT/'actual/A0_logits_fp32.npy'
    assert prism.digest(a0) == readback['native_vectors']['A0']['sha256']
    data = official.asset_proof()
    task, definition, requests, request_sha = records()
    assert len(task.eval_docs) == len(requests) == data['rows'] == official.ROWS
    assert not torch.cuda.is_initialized()
    pins = source_pins()
    snapshot = OUT/'sources'
    snapshot.mkdir(exist_ok=False)
    for name in SOURCES:
        with (snapshot/Path(name).name).open('xb') as stream:
            stream.write((ROOT/name).read_bytes())
    report = dict(schema='P106B_BONSAI_NATIVE_LAMBADA_PROFILE_V1',tag=TAG,
        source_pins=pins,old_prism_profile_sha256=prism.digest(prism.PROFILE),
        raw_closed_readback_sha256=prism.digest(READBACK),native_A0=readback['native_vectors']['A0'],
        official_definition=definition,official_asset=data,official_request_sha256=request_sha,
        official_rows=official.ROWS,vocab=old['vocab'],prefix_token=EOT,
        time_cutoff_KST='2026-11-18 16:30',internal_seconds=HARD_SECONDS,
        output_cap_bytes=OUTPUT_CAP,minimum_free_bytes=8*1024**3,
        model_gpu_actual_calls=0,installation_or_download=0)
    prism.write(PROFILE,report)
    print('LAMBADA_PREPARED',official.ROWS,request_sha,prism.digest(PROFILE),flush=True)


def verify():
    profile=prism.read(PROFILE)
    if profile['source_pins'] != source_pins():
        raise ValueError('frozen likelihood code differs')
    for name, sha in profile['source_pins'].items():
        if prism.digest(OUT/'sources'/Path(name).name) != sha:
            raise ValueError('frozen likelihood source snapshot differs')
    if (profile['old_prism_profile_sha256'] != prism.digest(prism.PROFILE)
            or profile['raw_closed_readback_sha256'] != prism.digest(READBACK)
            or profile['native_A0']['sha256'] != prism.digest(prism.OUT/'actual/A0_logits_fp32.npy')
            or prism.digest(ROOT/official.DATA_REL) != official.DATA_SHA):
        raise ValueError('frozen Prism or official evaluation asset differs')
    return profile, prism.verify()


def task_plan(plan):
    return dict(original_context_tokens=plan.original_context_tokens,
        kept_context_tokens=plan.kept_context_tokens,truncated_context_tokens=plan.truncated_context_tokens,
        continuation_tokens=len(plan.continuation_ids),input_tokens=len(plan.input_ids),target_start=plan.target_start)


def work(plan):
    return sum(range(plan.target_start+1,len(plan.input_ids)+1))


def numerical_gate(engine, plans):
    reports = []
    for name, plan in plans:
        observed = engine.score([plan])[0]
        expected, logits_hashes, greedy_ids = [], [], []
        for position, target in enumerate(plan.continuation_ids):
            logits = engine.native.logits(engine.prefix(plan,position))
            row = [float(value) for value in logits]
            maximum = max(row)
            lse = maximum + math.log(math.fsum(math.exp(value-maximum) for value in row))
            expected.append(row[target]-lse)
            greedy_ids.append(max(range(len(row)),key=row.__getitem__))
            logits_hashes.append(hashlib.sha256(logits.tobytes()).hexdigest().upper())
        maximum_error = max(abs(a-b) for a,b in zip(expected,observed['position_logprob']))
        if (maximum_error > 1e-10 or greedy_ids != observed['greedy_ids']
                or abs(math.fsum(expected)-observed['response'][0])>1e-10
                or observed['response'][1] != (tuple(greedy_ids)==plan.continuation_ids)):
            raise ValueError('native full-word independent FP64 or greedy oracle negative')
        reports.append(dict(name=name,token_plan=task_plan(plan),continuation_ids=list(plan.continuation_ids),
            maximum_position_error=maximum_error,logits_sha256=logits_hashes,greedy_agreement=True))
    return reports


def actual():
    started=time.monotonic()
    if time.time()+HARD_SECONDS+120>CUTOFF:
        raise Hold('complete declared interval does not fit before cutoff')
    profile, old=verify()
    if os.environ.get('LD_LIBRARY_PATH') != old['bundle']:
        raise ValueError('launch only with the exact frozen Prism library directory')
    if any(key.startswith(('LLAMA_ARG_','GGML_')) for key in os.environ):
        raise ValueError('external Prism environment argument overrides present')
    target=OUT/'actual'
    target.mkdir(exist_ok=False)
    report=dict(schema='P106B_BONSAI_NATIVE_LAMBADA_ACTUAL_V1',tag=TAG,
        started_UTC=datetime.now(timezone.utc).isoformat(),PID=os.getpid(),returncode=1,
        profile_sha256=prism.digest(PROFILE),formal_task=official.TASK,training_steps=0,checkpoint_writes=0)
    writer = None
    model = None
    rows_written = bytes_written = 0

    def check():
        if time.monotonic()-started>HARD_SECONDS or time.time()>CUTOFF-30 or (OUT/'STOP').exists():
            raise Hold('declared time or owned STOP limit')

    def interrupt(_sig, _frame):
        raise Hold('owned signal interruption')

    old_handler=signal.signal(signal.SIGINT,interrupt)
    try:
        report['GPU_entry']=require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
            capture_output=True,text=True,check=True,timeout=10)
        report['free_vram_point_bytes']=int(free.stdout.strip())*1024**2
        if report['free_vram_point_bytes'] < profile['minimum_free_bytes']:
            raise Hold('original free GPU memory admission failed')
        task, definition, requests, request_sha=records()
        if request_sha!=profile['official_request_sha256'] or definition!=profile['official_definition']:
            raise ValueError('official definition or exact ordered request payload differs')
        template,_=prepare_harness(runtime_root=Path(sysconfig.get_paths()['purelib']))
        with prism.native.NativeModel(old['bundle'],ROOT/old['model'],check=check) as model:
            report['model_loaded']=True
            if model.piece(EOT)!=b'<|im_end|>':
                raise ValueError('pinned native EOT piece differs')
            witness=np.load(prism.OUT/'actual/A0_logits_fp32.npy',allow_pickle=False)
            current=model.logits(old['prompts']['A']['native_ids'])
            if not np.array_equal(witness.view(np.uint32),current.view(np.uint32)):
                raise Hold('new process did not reproduce the qualified raw A vector')
            report['qualified_A_raw_bits_reproduced']=True
            del witness,current
            engine=PrismLikelihood(model,template,EOT,check=check)
            plans=[]
            for i,request in enumerate(requests):
                if i%64==0:
                    check()
                try:
                    plans.append(engine.plan(*request.args))
                except ValueError as error:
                    raise Hold(f'original LAMBADA token boundary at item {i}: {error}') from error
            single=next(i for i,p in enumerate(plans) if len(p.continuation_ids)==1)
            multi=next(i for i,p in enumerate(plans) if len(p.continuation_ids)>1)
            largest=max(range(len(plans)),key=lambda i:work(plans[i]))
            report['numerical_oracles']=numerical_gate(engine,[(str(single),plans[single]),
                (str(multi),plans[multi]),(str(largest),plans[largest]),('empty_context',engine.plan('',' standalone'))])
            report['token_budgets']=dict(rows=len(plans),continuation_tokens=sum(len(p.continuation_ids) for p in plans),
                multi_token_rows=sum(len(p.continuation_ids)>1 for p in plans),
                context_truncated_rows=sum(p.truncated_context_tokens>0 for p in plans),
                full_predictor_positions=sum(map(work,plans)),largest_input=len(plans[largest].input_ids))
            indices=sorted({i*(len(plans)-1)//31 for i in range(32)} | {largest})
            tick=time.monotonic()
            cost={i:engine.score([plans[i]])[0] for i in indices}
            cost_seconds=time.monotonic()-tick
            forecast=1.5*cost_seconds*max(len(plans)/len(indices),
                sum(map(work,plans))/sum(work(plans[i]) for i in indices))+120
            remaining=min(HARD_SECONDS-(time.monotonic()-started),CUTOFF-time.time()-30)
            report['cost']=dict(indices=indices,seconds=cost_seconds,forecast_seconds=forecast,remaining_seconds=remaining)
            print('LAMBADA_FORECAST',json.dumps(report['cost']),flush=True)
            if not math.isfinite(forecast) or forecast>remaining:
                raise Hold('measured full evaluation forecast exceeds the sealed budget')
            writer=ShardWriter(target,'samples',limit=10_000_000)
            for i,(request,plan) in enumerate(zip(requests,plans)):
                check()
                score=cost[i] if i in cost else engine.score([plan])[0]
                row=official.record_for(task,task.eval_docs[i],i,request,score['response'],task_plan(plan))
                row['native_token_proof']=dict(input_sha256=hashlib.sha256(canonical(plan.input_ids)).hexdigest().upper(),
                    continuation_ids=list(plan.continuation_ids),greedy_ids=score['greedy_ids'],
                    position_logprob=score['position_logprob'])
                bytes_written += len(canonical(row))+1
                if bytes_written>OUTPUT_CAP:
                    raise Hold('stored evaluation output cap reached')
                writer.append(row)
                rows_written += 1
                if rows_written%256 == 0:
                    print('LAMBADA_PROGRESS',rows_written,len(plans),flush=True)
            manifest=writer.close(lineage=dict(tag=TAG,task=official.TASK,source_sha256=official.DATA_SHA,
                request_sha256=request_sha,evaluation_only=True))
            writer=None
            report['sample_manifest']=manifest
            report['native_calls']=model.calls
            report['native_memory_clears']=model.clears
            report['native_processed_tokens']=model.processed_tokens
        report['native_owned_handles_closed']=not model.model and not model.context and not model.backend
        if not report['native_owned_handles_closed']:
            raise ValueError('Prism model or context remained owned after the run')
        recounted=official.recount_raw(task,target,manifest,official.ROWS)
        report.update(status='OFFICIAL_LAMBADA_FULL_COMPLETE',returncode=0,
            raw_recount=recounted,metrics=recounted['metrics'],complete_evaluation_rows=official.ROWS)
    except BaseException as error:
        report.update(status='HOLD' if isinstance(error,Hold) else 'ERROR',
            returncode=8 if isinstance(error,Hold) else 1,error=dict(type=type(error).__name__,message=str(error)[:1800]))
    finally:
        signal.signal(signal.SIGINT,old_handler)
        if writer is not None:
            if rows_written:
                report['partial_manifest']=writer.close(lineage=dict(tag=TAG,complete=False,evaluation_only=True))
            else:
                writer._finish()
        report['rows_written']=rows_written
        report['wall_seconds']=time.monotonic()-started
        report['process_peak_RSS_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        try:
            verify()
            report['frozen_files_unchanged']=True
        except BaseException as error:
            report.update(status='SOURCE_EXIT_ERROR',returncode=9,source_error=str(error)[:1200])
        prism.write(target/'report.json',report)
    print('LAMBADA_TERMINAL',json.dumps({k:report[k] for k in ('status','returncode','rows_written','wall_seconds','error','metrics') if k in report}),flush=True)
    return report['returncode']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','check','actual'))
    action=parser.parse_args().stage
    if action=='prepare':
        prepare()
    elif action=='check':
        profile, old=verify()
        assert not(OUT/'actual').exists() and time.time()+HARD_SECONDS+120<CUTOFF
        print('LAMBADA_CHECK',json.dumps(dict(profile_sha256=prism.digest(PROFILE),sources=len(profile['source_pins']),
            frozen_previous_assets=len(old['pins']),rows=profile['official_rows'],actual_output_absent=True)),flush=True)
    else:
        return actual()
    return 0


if __name__=='__main__':
    raise SystemExit(main())
