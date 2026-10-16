#!/usr/bin/env python3
"""Read-only fixed-answer/question likelihoods on source-defined QA bundles."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import gc
import json
import math
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import p106b_night_question_scores as method
from scripts import diag_p106b_night_question_bundles_v3 as source
from scripts.p106b_shards import ShardWriter,verify

qa,probe=source.qa,source.probe
TAG='p106b_night_question_scores_v1_s1337'
FROZEN=ROOT/'HF/sft_ready'/TAG/'source'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
ENDPOINTS=('base_qa','unique32k')
COUNTS={'ko':69,'en':41}
CODE=(*source.CODE,'scripts/p106b_night_question_scores.py','scripts/test_p106b_night_question_scores.py',
      'scripts/diag_p106b_night_question_scores.py','scripts/test_p106b_night_question_scores_runtime.py',
      'tinylm/train/mtp_sft.py','tinylm/data/sft.py','tinylm/chat/serialize.py')


def info():
    return dict(schema='P106B_NIGHT_QUESTION_SCORE_RUNTIME_V1',tag=TAG,
        code_sha256={p:qa.data.digest(ROOT/p) for p in sorted(set(CODE))},
        source_bundle_cpu_sha256=qa.data.digest(source.FROZEN/'report.json'),
        source_bundle_readback_sha256=qa.data.digest(source.EVIDENCE/'readback.json'),
        endpoints=list(ENDPOINTS),source_counts=COUNTS,view=0,precision='FP32_MATH',
        first_alias_only=True,teacher_forcing=True,use_cache=False,mtp=False,
        updates=0,checkpoints_written=0,new_teacher_calls=0,source_reselected_from_answers=False,
        semantic_cross_answer_negatives_certified=False,quality_pass_declared=False,
        whole_pretraining_contamination_audited=False,exploratory_previously_observed_cohort=True,
        train_stop_utc=qa.TRAIN_STOP.isoformat(),gpu_time_policy='fresh09 clamp after CPU/idle checks; per-cell training deadline',
        storage_policy='raw source/target scores in ignored <=20MB shards; Git aggregates only')


def safe():
    for target in (FROZEN,EVIDENCE,LOCAL):
        for path in (target,*target.parents):
            if path.is_symlink():raise ValueError('linked question-score namespace')
            if path==ROOT:break


def read_sources():
    frozen,cases,census=source.read_inputs();r=qa.required(source.EVIDENCE/'readback.json')
    if (r.get('status')!='QUESTION_BUNDLE_TEN_RAW_RECOUNTED' or r.get('errors')!=0
            or any(r.get(k)!=v for k,v in source.info().items())
            or r.get('input_report_sha256')!=qa.data.digest(source.FROZEN/'report.json')
            or list(r.get('reports',{}))!=source.old.labels()):
        raise ValueError('complete fixed ten-label question-bundle readback required')
    selected=sorted((b for b in census['bundles'] if b['character_distinct_candidate']),key=lambda b:b['bundle_id'])
    if {l:sum(b['language']==l for b in selected) for l in COUNTS}!=COUNTS:
        raise ValueError('whole original110 candidate bundle population required')
    by_root={c['root']:c for c in cases}
    pairs=[dict(source_bundle_id=b['bundle_id'],source_definition_sha256=qa.data.sha(b),
        source_cases=[by_root[root] for root in b['roots']]) for b in selected]
    return frozen,pairs


def build_wire(pairs,tok):
    wire=[]
    for pair in pairs:
        bundle=method.build_records(pair['source_cases'],tok)
        if bundle['source_bundle_definition_sha256']!=pair['source_definition_sha256']:
            raise ValueError('source bundle definition changed')
        wire.append(dict(source_bundle_id=pair['source_bundle_id'],bundle=bundle))
    if len({x['bundle']['bundle_id'] for x in wire})!=len(wire):raise ValueError('duplicate encoded bundle')
    return wire


def wire_summary(wire):
    cells=[c for b in wire for c in b['bundle']['cells']]
    if not cells:raise ValueError('nonempty full wire required')
    return dict(bundles=len(wire),cells=len(cells),by_language={l:sum(x['bundle']['language']==l for x in wire) for l in COUNTS},
        actual_x_tokens=sum(len(c['x']) for c in cells),content_targets=sum(c['content_token_count'] for c in cells),
        eot_targets=len(cells),max_x=max(len(c['x']) for c in cells),
        source_bundle_ids_sha256=qa.data.sha([x['source_bundle_id'] for x in wire]),
        wire_sha256=qa.data.sha(wire),input_record_sha256=qa.data.sha([c['record_sha256'] for c in cells]))


def save_wire(wire,limit=20_000_000):
    writer=ShardWriter(FROZEN,'wire',limit=limit)
    for row in wire:writer.append(row)
    return writer.close(lineage=dict(wire_sha256=qa.data.sha(wire)))


def restore_wire(manifest):
    if qa.required(FROZEN/'wire_shards_manifest.json')!=manifest:raise ValueError('wire manifest changed')
    verify(FROZEN,manifest);rows=[]
    for spec in manifest['shards']:
        with (FROZEN/spec['path']).open(encoding='utf-8') as stream:rows.extend(json.loads(line) for line in stream)
    if manifest['lineage']!={'wire_sha256':qa.data.sha(rows)}:raise ValueError('wire reconstruction changed')
    return rows


def prepare():
    import torch
    from tokenizers import Tokenizer
    safe();_,pairs=read_sources()
    if FROZEN.exists() or EVIDENCE.exists():raise FileExistsError('old question-score CPU preserved')
    wire=build_wire(pairs,Tokenizer.from_file(str(qa.data.TOKENIZER)))
    if torch.cuda.is_initialized():raise ValueError('CPU source freeze initialized CUDA')
    cost_ids=[]
    for language in COUNTS:
        values=[x for x in wire if x['bundle']['language']==language]
        cost_ids.append(min(values,key=lambda x:qa.data.sha([20261017,'cost-question-scores',x['source_bundle_id']]))['source_bundle_id'])
    manifest=save_wire(wire)
    result=dict(info(),status='QUESTION_SCORE_CPU_FROZEN',cuda_initialized=False,
        wire=wire_summary(wire),manifest=manifest,cost_bundle_ids=sorted(cost_ids))
    qa.write(FROZEN/'report.json',result);qa.write(EVIDENCE/'inputs.json',result)
    print('[QUESTION_SCORE_CPU] '+json.dumps(result['wire']),flush=True)
    return 0


def read_inputs():
    from tokenizers import Tokenizer
    safe();frozen=qa.required(FROZEN/'report.json');_,pairs=read_sources()
    if (frozen.get('status')!='QUESTION_SCORE_CPU_FROZEN' or frozen.get('cuda_initialized') is not False
            or any(frozen.get(k)!=v for k,v in info().items()) or qa.required(EVIDENCE/'inputs.json')!=frozen):
        raise ValueError('whole same-code score CPU proof required')
    wire=restore_wire(frozen['manifest']);rebuilt=build_wire(pairs,Tokenizer.from_file(str(qa.data.TOKENIZER)))
    if wire!=rebuilt or wire_summary(wire)!=frozen['wire']:raise ValueError('complete tokenizer/source wire changed')
    return frozen,wire


def compact(report):return {k:v for k,v in report.items() if k!='outcomes'}


def free_answers(endpoint,wire):
    cp,identity,core,report_hash,raw=probe.full_endpoint(endpoint)
    roots={root for b in wire for root in b['bundle']['roots']}
    free=[r for r in raw if r['view']==0 and r['root'] in roots]
    if len(free)!=len(roots):raise ValueError('same original actual view0 free answers required')
    return cp,identity,core,report_hash,free


def recount(events,wire,free):
    source_ids={x['bundle']['bundle_id']:x['source_bundle_id'] for x in wire}
    cells={c['cell_id']:c for x in wire for c in x['bundle']['cells']}
    for event in events:
        c=cells.get(event.get('cell_id'))
        if (c is None or event.get('source_bundle_id')!=source_ids[c['bundle_id']]
                or event.get('actual_x_tokens')!=len(c['x']) or event.get('forward_precision')!='FP32_MATH'):
            raise ValueError('actual source mapping/input shape/precision changed')
    return method.summarize(events,[x['bundle'] for x in wire],free)


def report_path(endpoint,phase):return EVIDENCE/(phase+'_'+endpoint)/'report.json'


def endpoint_report(endpoint,phase,frozen,wire):
    selected=wire if phase=='full' else [b for b in wire if b['source_bundle_id'] in frozen['cost_bundle_ids']]
    cp,identity,core,full_hash,free=free_answers(endpoint,selected)
    r=qa.required(report_path(endpoint,phase));directory=LOCAL/(phase+'_'+endpoint)
    if (r.get('status')!='QUESTION_SCORES_COMPLETE' or r.get('phase')!=phase or r.get('endpoint')!=endpoint
            or any(r.get(k)!=v for k,v in info().items())
            or r.get('input_report_sha256')!=qa.data.digest(FROZEN/'report.json')
            or r.get('checkpoint')!=str(cp.relative_to(ROOT)) or r.get('checkpoint_sha256')!=identity
            or r.get('initial_core_sha256')!=core or r.get('primary_full_report_sha256')!=full_hash
            or r.get('body_proof')!=probe.e.body_proof(dict(kind='NEW_MODEL_INFERENCE'),core,core)
            or r.get('directory')!=str(directory.relative_to(ROOT))):
        raise ValueError('complete same-code/source/body/checkpoint question scores required')
    verify(directory,r['manifest'])
    if qa.required(directory/'scores_shards_manifest.json')!=r['manifest']:raise ValueError('raw score manifest changed')
    events=list(probe.e.old.stream(directory,r['manifest']))
    if compact(recount(events,selected,free))!=r['summary']:raise ValueError('raw question-score recount differs')
    return r


def forecast(report,total_bundles):
    if (type(report.get('compute_seconds')) not in (int,float) or not math.isfinite(report['compute_seconds'])
            or report['compute_seconds']<=0 or type(report.get('whole_seconds')) not in (int,float)
            or not math.isfinite(report['whole_seconds']) or report['whole_seconds']<report['compute_seconds']
            or type(report.get('measured_bundles')) is not int or report['measured_bundles']!=2
            or report.get('phase')!='cost' or type(total_bundles) is not int or total_bundles<2):
        raise ValueError('actual two-bundle cost required')
    return report['compute_seconds']/2*total_bundles*1.5+max(60.,report['whole_seconds']-report['compute_seconds'])


def check_budget(frozen,wire):
    seconds=0.
    for endpoint in ENDPOINTS:
        cost=endpoint_report(endpoint,'cost',frozen,wire)
        if report_path(endpoint,'full').exists():endpoint_report(endpoint,'full',frozen,wire)
        else:seconds+=forecast(cost,len(wire))
    remaining=(qa.TRAIN_STOP-datetime.now(timezone.utc)).total_seconds()
    if remaining<seconds+600:raise ValueError('pending full scores plus600-second reserve exceed09:00')
    return dict(pending_forecast_seconds=seconds,remaining_before09=remaining,reserve_seconds=600)


def gpu_seconds(cap,now=None):
    if type(cap) is not int or not 1<=cap<=600:raise ValueError('bounded GPU seconds required')
    remaining=(qa.TRAIN_STOP-(now or datetime.now(timezone.utc))).total_seconds()
    if remaining<120:raise ValueError('09:00 GPU stop')
    return min(cap,int(remaining)-1)


def evaluate(endpoint,phase,seconds):
    import torch
    from torch.nn.attention import sdpa_kernel,SDPBackend
    from tinylm.infer.generate import load_model
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    frozen,all_wire=read_inputs()
    if phase=='full':print('[QUESTION_SCORE_BUDGET] '+json.dumps(check_budget(frozen,all_wire)),flush=True)
    wire=all_wire if phase=='full' else [b for b in all_wire if b['source_bundle_id'] in frozen['cost_bundle_ids']]
    cp,identity,expected,full_hash,free=free_answers(endpoint,wire)
    directory=LOCAL/(phase+'_'+endpoint);target=report_path(endpoint,phase)
    if directory.exists() or target.exists():raise FileExistsError('old full/partial score attempt preserved')
    idle_before_gpu();seconds=gpu_seconds(seconds)
    began=time.perf_counter();writer=ShardWriter(directory,'scores');events=[]
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(seconds):
        model,cfg,device=load_model(arch='dense',ckpt_path=str(cp),device='cuda')
        initial=probe.panel.foundation.runtime.state_fingerprint(model)
        if initial!=expected or next(model.parameters()).dtype!=torch.float32:raise ValueError('strict FP32 selected body required')
        torch.cuda.reset_peak_memory_stats();compute=time.perf_counter()
        with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
            for index,bundle in enumerate(wire):
                for cell in bundle['bundle']['cells']:
                    probe.e.train.deadline(training=True)
                    x=torch.tensor([cell['x']],dtype=torch.long,device=device)
                    hidden=model(x,return_hidden=True)[0]
                    event=method.score_hidden(cell,hidden,model._head_logits)
                    event.update(source_bundle_id=bundle['source_bundle_id'],actual_x_tokens=len(cell['x']),forward_precision='FP32_MATH')
                    writer.append(event);events.append(event)
                if (index+1)%20==0:print('[QUESTION_SCORE_PROGRESS] '+json.dumps(dict(endpoint=endpoint,bundles=index+1)),flush=True)
        torch.cuda.synchronize();compute_seconds=time.perf_counter()-compute
        final=probe.panel.foundation.runtime.state_fingerprint(model)
        body=probe.e.body_proof(dict(kind='NEW_MODEL_INFERENCE'),initial,final)
        if qa.data.digest(cp)!=identity:raise ValueError('read-only scoring changed checkpoint file')
        manifest=writer.close(lineage=info());summary=compact(recount(events,wire,free))
        result=dict(info(),status='QUESTION_SCORES_COMPLETE',phase=phase,endpoint=endpoint,
            input_report_sha256=qa.data.digest(FROZEN/'report.json'),primary_full_report_sha256=full_hash,
            checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=identity,initial_core_sha256=initial,
            body_proof=body,directory=str(directory.relative_to(ROOT)),manifest=manifest,summary=summary,
            whole_seconds=time.perf_counter()-began,compute_seconds=compute_seconds,measured_bundles=len(wire),
            peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
        qa.write(target,result);endpoint_report(endpoint,phase,frozen,all_wire)
        print('[QUESTION_SCORE_COMPLETE] '+json.dumps(dict(endpoint=endpoint,phase=phase,seconds=result['whole_seconds'],summary=summary['by_language'])),flush=True)
    del model;gc.collect();torch.cuda.empty_cache()
    return 0


def readback():
    frozen,wire=read_inputs();target=EVIDENCE/'readback.json'
    if target.exists():raise FileExistsError('old likelihood comparison preserved')
    results={endpoint:endpoint_report(endpoint,'full',frozen,wire) for endpoint in ENDPOINTS}
    result=dict(info(),status='TWO_QUESTION_SCORE_RAW_RECOUNTED',errors=0,
        endpoint_report_sha256={x:qa.data.digest(report_path(x,'full')) for x in ENDPOINTS},
        summary={x:r['summary'] for x,r in results.items()},model_loaded=False,new_logits=False)
    qa.write(target,result);print('[QUESTION_SCORE_READBACK] '+json.dumps(result['summary']),flush=True)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','cost','full','readback'),required=True)
    p.add_argument('--endpoint',choices=ENDPOINTS);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit CPU/GPU operation required')
    if a.mode in ('cost','full') and a.endpoint is None:p.error('explicit model endpoint required')
    try:
        if a.mode=='freeze':return prepare()
        if a.mode=='readback':return readback()
        return evaluate(a.endpoint,a.mode,gpu_seconds(600))
    except KeyboardInterrupt:print('[QUESTION_SCORE_INTERRUPTED] partial preserved');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[QUESTION_SCORE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
