#!/usr/bin/env python3
"""기존 strict Falcon/HFLM을 공식 MMLU0/5shot에 연결한다. 새 학습은 없다."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import importlib
import json
import math
import os
from pathlib import Path
import sys
import sysconfig
import time
from types import MethodType, SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from scripts import p106b_official_mmlu as data
from scripts import diag_p106b_official_mmlu as prior
from scripts import diag_p106b_official_core6 as old
from scripts import diag_p106b_resource_matrix as resource
from scripts.p106b_official_archive import verify_files
from scripts.p106b_nvml_probe import watcher_class
from scripts.diag_p106b_mmlu_nvml_recovery import verify_probe
from scripts.diag_p107_adaptive_training import ResourceHold
from scripts.diag_p107_hybrid_mntp import close_owned_cuda, independent_final_checks
from scripts.p106b_shards import ShardWriter, verify as verify_shards

PROFILE=ROOT/'data_cache/p106b_falcon_mmlu_v1_20261101/profile.json'
OUTPUT=ROOT/'test_result/evidence/p106b_falcon_mmlu_v1_20261101'
SUBJECT_PROOF=ROOT/'test_result/evidence/p106b_mmlu_subject_originals_v2_20261101/report.json'
OWN=('scripts/diag_p106b_falcon_mmlu.py','scripts/test_p106b_falcon_mmlu.py',
     'scripts/p106b_official_archive.py','scripts/test_p106b_official_archive.py',
     'scripts/p106b_nvml_probe.py','scripts/test_p106b_nvml_probe.py','scripts/diag_p106b_nvml_probe.py',
     'scripts/diag_p106b_mmlu_nvml_recovery.py','scripts/test_p106b_mmlu_nvml_recovery.py')
HF_FILES=['lm_eval/models/huggingface.py','lm_eval/models/utils_hf.py','lm_eval/api/model.py']
ARMS={'falcon0':0,'falcon5':5}


def identity():
    files=dict(prior.identity()['files'])
    files.update({name:data.digest(ROOT/name) for name in OWN})
    return dict(files=files,sha256=resource.sha(files))


def model_assets():
    resource.need(data.digest(old.FALCON_REFERENCE)==old.FALCON_REFERENCE_SHA,'기존 strict Falcon CPU 영수증 변형')
    reference=json.loads(old.FALCON_REFERENCE.read_text())['asset_sha256']
    resource.need({name:data.digest(old.FALCON/name) for name in reference}==reference,'기존 Falcon 원형 변형')
    return dict(model='falcon90m',revision=old.FALCON.name,path=str(old.FALCON.relative_to(ROOT)),
                reference_sha256=old.FALCON_REFERENCE_SHA,files=reference)


def runtime_proof():
    from scripts.p106b_official_lm_adapter import SOURCE, MANIFEST, prepare_harness
    _,framework=prepare_harness(runtime_root=Path(sysconfig.get_paths()['purelib']))
    archive=Path(json.loads(MANIFEST.read_text())['archive_path'])
    official=verify_files(HF_FILES,archive=archive,source=SOURCE,runtime=Path(sysconfig.get_paths()['purelib']))
    import transformers, torch
    implementation=importlib.import_module('transformers.models.falcon_h1.modeling_falcon_h1')
    return dict(framework=framework,official_hf_files=official,transformers_version=transformers.__version__,
        torch_version=torch.__version__,model_implementation_path=implementation.__file__,
        model_implementation_sha256=data.digest(implementation.__file__))


def tokenizer_only(tokenizer):
    from lm_eval.api.model import TemplateLM
    from lm_eval.models.huggingface import HFLM
    prefix=tokenizer.bos_token_id if tokenizer.bos_token_id is not None else tokenizer.eos_token_id
    proxy=SimpleNamespace(backend='causal',tokenizer=tokenizer,add_bos_token=False,prefix_token_id=prefix)
    proxy.tok_encode=MethodType(HFLM.tok_encode,proxy)
    proxy._encode_pair=MethodType(TemplateLM._encode_pair,proxy)
    return proxy


def prepare_contract():
    from unittest.mock import patch
    from transformers import AutoTokenizer,AutoConfig,AutoModelForCausalLM
    from scripts.p106b_official_lm_adapter import plan_tokens
    monitor,model,framework=verify_probe(),model_assets(),runtime_proof()
    data.verify_assets()
    proof=json.loads(SUBJECT_PROOF.read_text())
    resource.need(proof['status']=='ALL_57_SUBJECT_TEST_DEV_ORDER_EXACT' and not proof['errors'],'과제별 공식 원문/5예시 순서 검산 필요')
    resource.need(not OUTPUT.exists() and not PROFILE.exists(),'새 Falcon 평가 namespace 필요')
    OUTPUT.mkdir(parents=True)
    writer=ShardWriter(OUTPUT/'contract/lengths','requests',limit=4_000_000)
    with patch.object(AutoModelForCausalLM,'from_pretrained',side_effect=RuntimeError('CPU 계약 가중치 로딩 금지')):
        tokenizer=AutoTokenizer.from_pretrained(str(old.FALCON),local_files_only=True,trust_remote_code=False)
        meta=AutoConfig.from_pretrained(str(old.FALCON),local_files_only=True,trust_remote_code=False)
        resource.need(meta.model_type=='falcon_h1','고정 모델 구조 필요')
        proxy=tokenizer_only(tokenizer)
        totals={}
        for shots in (0,5):
            tasks,_,_=data.load_tasks(shots)
            total=dict(rows=0,requests=0,input_positions=0,truncated_requests=0,removed_context_tokens=0,
                maximum_original_input=0,maximum_actual_input=0)
            for name,task in tasks.items():
                for index,doc in enumerate(task.eval_docs):
                    choices=[]
                    for request in data.requests(task,doc,shots,index):
                        context,continuation=proxy._encode_pair(*request.args)
                        plan=plan_tokens(context,continuation,meta.vocab_size,1024)
                        choices.append(dict(context_tokens=len(context),continuation_tokens=len(continuation),
                            input_tokens=len(plan.input_ids),removed_context_tokens=plan.truncated_context_tokens))
                    total['rows']+=1;total['requests']+=4
                    for row in choices:
                        total['input_positions']+=row['input_tokens']
                        total['truncated_requests']+=row['removed_context_tokens']>0
                        total['removed_context_tokens']+=row['removed_context_tokens']
                        total['maximum_original_input']=max(total['maximum_original_input'],row['context_tokens']+row['continuation_tokens']-1)
                        total['maximum_actual_input']=max(total['maximum_actual_input'],row['input_tokens'])
                    writer.append(dict(task=name,doc_id=index,shots=shots,choices=choices))
                print(json.dumps(dict(event='FALCON_CPU_TASK',task=name,shots=shots,rows=len(task.eval_docs))),flush=True)
            resource.need(total['rows']==14042 and total['requests']==56168,'전량 분모 필요')
            totals[str(shots)]=total
    lengths=writer.close(lineage=dict(purpose='EVALUATION_ONLY',model='falcon90m',shots=[0,5]))
    controls=[('Question: one plus one? Answer:',' A'),('Question: apple color? Answer:',' B')]
    result=dict(schema='FALCON_OFFICIAL_MMLU_PROFILE_V1',status='CPU_CONTRACT_COMPLETE',
        created_at=datetime.now(timezone.utc).isoformat(),source=identity(),models=model,runtime=framework,
        monitor=monitor,subject_equivalence_sha256=data.digest(SUBJECT_PROOF),
        assets_sha256=data.digest(data.CACHE/'assets.json'),shots=totals,
        policies={str(n):prior.policy(n) for n in (0,5)},cpu_lengths=lengths,
        token_controls=[dict(arguments=list(pair),encoded=proxy._encode_pair(*pair)) for pair in controls],
        vocab_size=meta.vocab_size,authority_directive=104,deadline=prior.DEADLINE.isoformat(),
        model_loads=0,gpu_runs=0,training=0,checkpoint_writes=0)
    PROFILE.parent.mkdir(parents=True)
    resource.write_new(PROFILE,result);resource.write_new(OUTPUT/'contract/report.json',result)
    print(json.dumps(dict(status=result['status'],profile_sha256=data.digest(PROFILE),source=result['source']['sha256'],shots=totals)))
    return 0


def read_profile(path,sha):
    resource.need(path==str(PROFILE.relative_to(ROOT)) and data.digest(PROFILE)==sha,'동결 profile 경로/SHA 필요')
    value=json.loads(PROFILE.read_text())
    resource.need(value['source']==identity() and value['models']==model_assets() and value['runtime']==runtime_proof(),'소스/모델/runtime 변형')
    resource.need(value['monitor']==verify_probe() and data.digest(SUBJECT_PROOF)==value['subject_equivalence_sha256'],'감시/공식원형 검산 변형')
    resource.need(value['assets_sha256']==data.digest(data.CACHE/'assets.json'),'평가자료 manifest 변형')
    data.verify_assets()
    return value


def admit_full(cost,profile_sha,shots,positions,now):
    if (cost.get('final_exit')!=0 or cost.get('status')!='LIMITED_COST_DIAGNOSTIC' or cost.get('model')!='falcon90m'
            or cost.get('shots')!=shots or cost.get('actual_rows')!=114 or cost.get('profile_sha256')!=profile_sha
            or cost.get('source')!=identity() or cost.get('policy')!=prior.policy(shots) or len(cost.get('audits',{}))!=57):
        raise ValueError('동일 source/profile/57과제114행 비용 필요')
    seconds,measured=cost.get('scorer_seconds'),cost.get('scored_input_positions')
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in (seconds,measured,positions)):
        raise ValueError('실제 양수 시간/입력량 필요')
    estimate=seconds*positions/measured*1.8+300
    if estimate>5400 or now+estimate+120>=prior.DEADLINE.timestamp():
        raise ResourceHold('전량 예상이90분/11시 예비를 초과')
    return dict(forecast_seconds=estimate,hard_cap_seconds=min(5400,int(prior.DEADLINE.timestamp()-now-120)))


@contextmanager
def observe_backend(lm,torch,report):
    original,forward=lm._loglikelihood_tokens,lm._model_call
    def call(inputs,*args,**kwargs):
        value=forward(inputs,*args,**kwargs)
        report['completed_forward_batches']+=1
        report['completed_forward_padded_positions']+=inputs.numel()
        return value
    def run(requests,**kwargs):
        torch.cuda.synchronize();tick=time.monotonic()
        try:return original(requests,**kwargs)
        finally:report['scorer_seconds']+=time.monotonic()-tick
    lm._loglikelihood_tokens,lm._model_call=run,call
    try:yield
    finally:
        lm._loglikelihood_tokens,lm._model_call=original,forward
        report['peak_allocated_bytes']=torch.cuda.max_memory_allocated()
        report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()


def evaluate(args):
    profile=read_profile(args.profile,args.profile_sha256);shots=ARMS[args.arm]
    cost=OUTPUT/('shot'+str(shots))/'cost/report.json'
    try:
        admission=admit_full(json.loads(cost.read_text()),args.profile_sha256,shots,profile['shots'][str(shots)]['input_positions'],time.time()) if args.mode=='full' else dict(hard_cap_seconds=600)
    except ResourceHold as exc:
        print(json.dumps(dict(status='NOT_RUN_RESOURCE_HOLD',model_loads=0,reason=str(exc))));return 8
    resource.need(time.time()+admission['hard_cap_seconds']+120<=prior.DEADLINE.timestamp(),'마감 예비 필요')
    if args.check_only:
        print(json.dumps(dict(status='READY_GPU_NOT_RUN',arm=args.arm,admission=admission)));return 0
    folder=OUTPUT/('shot'+str(shots))/args.mode
    resource.need(not folder.exists(),'이전/부분 출력 보존')
    folder.mkdir(parents=True)
    report=dict(schema='FALCON_OFFICIAL_MMLU_RUN_V1',status='STARTED',model='falcon90m',shots=shots,
        source=identity(),policy=prior.policy(shots),profile_sha256=args.profile_sha256,model_metadata=profile['models'],
        admission=admission,actual_rows=0,audits={},samples={},official_results={},scorer_seconds=0.,
        completed_forward_batches=0,completed_forward_padded_positions=0,training=0,checkpoint_writes=0,
        resource_limit_bytes=8_000_000_000,torch_allocator_cap_bytes=6*2**30)
    code,watch,writer,started=9,None,None,time.monotonic()
    try:
        tasks,_,framework=data.load_tasks(shots)
        from lm_eval.evaluator import simple_evaluate
        from lm_eval.tasks import TaskManager
        from lm_eval.api.metrics import aggregate_subtask_metrics
        from scripts import interactive_research_infer as manual
        import torch
        from torch.nn.attention import sdpa_kernel,SDPBackend
        torch.set_num_threads(4);torch.manual_seed(1337)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        report['gpu_admission']=manual.require_idle_gpu()
        watch=watcher_class()();watch.start()
        torch.cuda.set_per_process_memory_fraction(6*2**30/torch.cuda.get_device_properties(0).total_memory)
        writer=ShardWriter(folder/'lengths','requests',limit=4_000_000)
        with resource.wall(admission['hard_cap_seconds']),sdpa_kernel(SDPBackend.MATH),torch.no_grad():
            with old.model_runtime('falcon90m',torch) as (lm,proof):
                lm.batch_size_per_gpu=4
                resource.need(lm.batch_size==4 and lm.max_length==1024 and not lm.model.config.use_cache,'고정 batch/context/cache 필요')
                resource.need(proof['model_source_sha256']==profile['runtime']['model_implementation_sha256'],'실제 모델 코드 변형')
                for row in profile['token_controls']:
                    resource.need([list(x) for x in lm._encode_pair(*row['arguments'])]==row['encoded'],'실제/CPU tokenizer 계약 불일치')
                report['model_proof']=proof
                report['numerical_canary']=old.numerical_canary(lm,torch)
                torch.cuda.reset_peak_memory_stats()
                with old.length_observer(lm,writer) as lengths,observe_backend(lm,torch,report):
                    result=simple_evaluate(model=lm,tasks=list(tasks.values()),num_fewshot=shots,
                        task_manager=TaskManager(),batch_size=4,device='cuda',use_cache=None,cache_requests=False,
                        limit=2 if args.mode=='cost' else None,bootstrap_iters=100000,log_samples=True,
                        apply_chat_template=False,fewshot_as_multiturn=False,random_seed=1337,
                        numpy_random_seed=1337,torch_random_seed=1337,fewshot_random_seed=1337)
                report['length_summary']=lengths
                resource.need(set(result['samples'])==set(tasks),'전체57과제 필요')
                vals,sizes=[],[]
                for name,task in tasks.items():
                    rows=old.plain(result['samples'][name]);expected=2 if args.mode=='cost' else len(task.eval_docs)
                    audit=data.independent_scores(rows,expected)
                    resource.need(math.isclose(audit['accuracy'],result['results'][name]['acc,none'],abs_tol=1e-12),'공식/독립 집계 불일치')
                    shard=ShardWriter(folder/'samples'/name,'responses',limit=4_000_000)
                    for row in rows:shard.append(row)
                    report['samples'][name]=shard.close(lineage=dict(model='falcon90m',task=name,shots=shots,evaluation_only=True))
                    report['audits'][name]=audit;report['official_results'][name]=old.plain(result['results'][name])
                    report['actual_rows']+=expected;vals.append(audit['accuracy']);sizes.append(expected)
                report['weighted_accuracy']=aggregate_subtask_metrics(vals,sizes,weight_by_size=True)
                resource.need(math.isclose(report['weighted_accuracy'],sum(a['correct'] for a in report['audits'].values())/sum(sizes),abs_tol=1e-12),'공식 크기가중 집계 불일치')
                report['framework']=framework
            resource.need(proof['initial_core_sha256']==proof['final_core_sha256'] and proof['source_assets_unchanged'],'원모델/파일 변형')
        resource.need(report['actual_rows']==(114 if args.mode=='cost' else 14042),'전량 분모 필요')
        report['status'],code=('LIMITED_COST_DIAGNOSTIC' if args.mode=='cost' else 'OFFICIAL_MMLU_FULL_COMPLETE'),0
    except (TimeoutError,ResourceHold) as exc:
        report.update(status='HOLD',error_type=type(exc).__name__,error=str(exc)[:1500]);code=8
    except Exception as exc:
        report.update(status='ERROR',error_type=type(exc).__name__,error=str(exc)[:1500]);code=9
    finally:
        def lengths():
            if writer is not None and writer._total_rows:
                report['lengths_manifest']=writer.close(lineage=dict(model='falcon90m',shots=shots,partial=code!=0))
                verify_shards(folder/'lengths',report['lengths_manifest'])
                report['scored_input_positions']=sum(row['context_tokens']+row['continuation_tokens']-1-row['truncated_context_tokens']
                    for part in report['lengths_manifest']['shards'] for row in map(json.loads,(folder/'lengths'/part['path']).read_text().splitlines()))
                report['position_count_scope']='SUBMITTED_REQUESTS; NOT_COMPLETED_WHEN_INTERRUPTED'
        def stop():
            if watch is not None:report['vram_watch']=watch.stop()
        def cuda():
            if 'torch' in sys.modules:close_owned_cuda(sys.modules['torch'],report)
        def source():
            report['source_unchanged']=profile['source']==identity()
            report['assets_unchanged']=profile['models']==model_assets()
            resource.need(report['source_unchanged'] and report['assets_unchanged'] and profile['runtime']==runtime_proof(),'소스/원형/runtime 변형')
        gc.collect()
        good=independent_final_checks(report,[('watch',stop),('lengths',lengths),('cuda',cuda),('source',source)])
        if not good:report['status'],code='ERROR',9
        elif report.get('vram_watch',{}).get('reason') is not None and code!=9:report['status'],code='HOLD',8
        report.update(final_exit=code,wall_seconds=time.monotonic()-started)
        resource.write_new(folder/'report.json',report)
        print(json.dumps({k:report[k] for k in ('status','shots','actual_rows','final_exit','wall_seconds')}),flush=True)
    return code


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('contract','cost','full'),required=True)
    parser.add_argument('--arm',choices=tuple(ARMS))
    parser.add_argument('--profile');parser.add_argument('--profile-sha256')
    parser.add_argument('--execute',action='store_true');parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if args.execute==args.check_only:parser.error('실행 또는 읽기전용 하나만 명시')
    resource.need(time.time()+120<prior.DEADLINE.timestamp(),'11시 마감 예비')
    for key,value in prior.OFFLINE.items():os.environ[key]=value
    if args.mode=='contract':
        if args.check_only:print(json.dumps(dict(status='CPU_CONTRACT_NOT_RUN')));return 0
        return prepare_contract()
    if not args.arm or not args.profile or not args.profile_sha256:parser.error('동결 arm/profile/SHA 필요')
    return evaluate(args)


if __name__=='__main__':
    raise SystemExit(main())
