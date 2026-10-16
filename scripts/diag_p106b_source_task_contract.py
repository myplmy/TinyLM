#!/usr/bin/env python3
"""Original-task preservation and paired old-repair/new-QA teacher diagnostic."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json
import time
from unittest.mock import patch
from urllib.error import HTTPError
from scripts import p106b_source_task_contract as method
from scripts import diag_p106b_repair_role_course as course
from scripts import diag_p106b_source_repair3 as old
from scripts import p106b_gemma_teacher as teacher
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_memory_stream import PersistentMemory,stream_session_scope
from scripts.p106b_gemma_telemetry_resume import RetryingMemoryReader
from scripts.diag_p106b_gemma_ac import count_prompt
from scripts.p106b_http_errors import capture_http_error

TAG='p106b_source_task_contract_v1_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG
CODE=(*old.CODE,'scripts/p106b_source_task_contract.py','scripts/test_p106b_source_task_contract.py',
    'scripts/diag_p106b_source_task_contract.py')
ARMS=('old_repair','new_grounded_qa')


def info():
    return dict(schema='P106B_ORIGINAL_TASK_DIRECTION_PILOT_V1',tag=TAG,
        code_sha256={p:old.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        student_tokenizer_sha256=old.training.data.TOK_SHA,
        source_cohort='previous fixed source8; posthoc development, not unseen test',
        questions_generated_by_teacher=True,source_semantic_verifier=False,
        sampler=teacher.SAMPLER,thinking_budget=256,context=8192,max_output=3072,mtp=True,draft_max=2,
        attempts_per_arm_root=1,quality_regeneration=False,world_truth='NOT_RUN',student_training=False,
        comparison='PARTIAL_CONFOUNDED task-input contract and generated question content differ; same root/seed/runtime',
        original_data_changed=False,deadline_utc=old.original.prior.producer.legacy.source.DEADLINE.isoformat())


def recover(rows,traces):
    """Match original file/ID/reference; generic task_type alone is not direction."""
    import pyarrow.dataset as ds
    import pyarrow.parquet as pq
    by_file=defaultdict(list)
    for r in rows:by_file[(traces[r['meta']['semantic_root_id']]['source_file'],r['meta']['language'])].append(r)
    recovered={}
    for (name,language),selected in by_file.items():
        path=ROOT/name;trace=traces[selected[0]['meta']['semantic_root_id']]
        if old.training.data.digest(path)!=trace['source_sha256']:raise ValueError('exact original source changed')
        cols=['id','inputs','targets','dataset_name','task_type','template_id'];ordinals={}
        if language=='ko':
            wanted={int(r['meta']['source_id'].rsplit(':',1)[1]) for r in selected};n=0
            for batch in pq.ParquetFile(path).iter_batches(columns=cols,batch_size=512):
                for a in batch.to_pylist():
                    if n in wanted:ordinals[n]=a
                    n+=1
                if n>max(wanted):break
            candidates=list(ordinals.values())
        else:
            ids=[int(r['meta']['source_id']) for r in selected]
            candidates=ds.dataset(str(path),format='parquet').scanner(columns=cols,
                filter=ds.field('id').isin(ids)&ds.field('dataset_name').isin(['Flan-Coqa','Flan-Coqa (T)'])).to_table().to_pylist()
        for r in selected:
            m=r['meta'];choices=[ordinals[int(m['source_id'].rsplit(':',1)[1])]] if language=='ko' else [a for a in candidates if str(a['id'])==m['source_id']]
            matches=[]
            for a in choices:
                candidate=method.original_pair(a['inputs'].strip(),a['targets'].strip(),dict(source='p106b_public_direct',selection_family='Flan-Coqa'))
                try:parsed=method.prior.original_three(candidate)
                except ValueError:continue
                if parsed['reference']==m['source_reference']:matches.append(a)
            if len(matches)!=1:raise ValueError('single original source/reference match required')
            a=matches[0];job=method.from_rendered(r)
            job.update(original_inputs=a['inputs'],original_targets=a['targets'],
                original_task_metadata={k:a[k] for k in ('id','dataset_name','task_type','template_id')},
                exact_source_file=name,exact_source_sha256=trace['source_sha256'])
            recovered[m['semantic_root_id']]=job
    return recovered


def freeze():
    from tokenizers import Tokenizer
    from tinylm.train.mtp_sft import encode_record
    if OUTPUT.exists() or EVIDENCE.exists():raise GateNegative('old original-task namespace preserved')
    if old.training.data.digest(old.training.data.TOKENIZER)!=old.training.data.TOK_SHA:raise ValueError('student tokenizer changed')
    reviewed=old.required(course.EVIDENCE/'evaluate/manual_source8_review.json')
    metadata=old.required(course.EVIDENCE/'evaluate/source_task_trace_metadata.json')
    expected={r['root'] for r in reviewed['rows']};traces={r['root']:r for r in metadata['rows']}
    source=old.required(course.CORPUS/'report.json');rows=[r for r in old.training.data.stream_rows(course.CORPUS,source['manifests']['test_source']) if r['meta']['semantic_root_id'] in expected]
    if len(rows)!=8 or Counter(r['meta']['language'] for r in rows)!=dict(ko=4,en=4):raise ValueError('same fixed8 original references required')
    jobs=recover(rows,traces);tok=Tokenizer.from_file(str(old.training.data.TOKENIZER));pairs=[];wire=[]
    for root in sorted(jobs):
        j=jobs[root];route=method.dispatch(j['original_inputs'],j['original_targets'],j['provenance'])
        if route['route']!='ORIGINAL_PAIR':raise ValueError('unknown contract must stay original')
        route['row']['meta'].update(source_split='posthoc_dev',source_cohort='previous_fixed_source8')
        rec=encode_record(route['row'],tok)
        pairs.append(route['row']);wire.append(dict(source_root=root,original_messages=2,x_tokens=rec.x_tokens,
            assistant_targets=rec.targets,fits1024=rec.x_tokens<=1024,no_truncation=True))
    OUTPUT.mkdir(parents=True,exist_ok=False);manifests={}
    for name,values in (('jobs',[jobs[k] for k in sorted(jobs)]),('original_pairs',pairs)):
        w=ShardWriter(OUTPUT,name)
        for v in values:w.append(v)
        manifests[name]=w.close(lineage=info());verify(OUTPUT,manifests[name])
    report=dict(info(),status='ORIGINAL_TASK_PACKET_FROZEN',jobs=8,manifests=manifests,original_pair_wire=wire,
        original_source_metadata=metadata['schema'],source_trace_sha256=old.training.data.digest(course.EVIDENCE/'evaluate/source_task_trace_metadata.json'))
    old.training.write(OUTPUT/'inputs.json',report);old.training.write(EVIDENCE/'inputs.json',report)
    print('[TASK_CONTRACT_INPUTS] '+json.dumps(dict(jobs=8,original_pairs=8,route='ORIGINAL_PAIR',metadata_direction_is_not_trusted=True)),flush=True);return 0


def inputs():
    r=old.required(OUTPUT/'inputs.json')
    if r['code_sha256']!=info()['code_sha256']:raise ValueError('frozen task contract CODE changed')
    if old.training.data.digest(old.training.data.TOKENIZER)!=old.training.data.TOK_SHA:raise ValueError('student tokenizer changed')
    for m in r['manifests'].values():verify(OUTPUT,m)
    return r,list(old.training.data.stream_rows(OUTPUT,r['manifests']['jobs']))


def pilot(a):
    from tokenizers import Tokenizer
    r,jobs=inputs();target=OUTPUT/'pilot'
    if target.exists() or (EVIDENCE/'pilot.json').exists():raise GateNegative('old paired teacher replies preserved')
    idle_before_gpu();target.mkdir(exist_ok=False);raw=ShardWriter(target,'raw');accepted=ShardWriter(target,'candidates')
    tok=Tokenizer.from_file(str(old.training.data.TOKENIZER));began=time.perf_counter();counts={k:Counter() for k in ARMS};results=[];error=None;memory_report={}
    try:
        with wall_limit(a.max_wall_sec),patch.object(teacher,'THINKING',256):
            assets=teacher.assets(True)
            with PersistentMemory() as memory:
                reader=RetryingMemoryReader(memory,emit=lambda line:print(line,flush=True))
                with stream_session_scope(reader),teacher.GemmaSession(True) as session:
                    for i,j in enumerate(jobs):
                        arms=ARMS if i%2==0 else tuple(reversed(ARMS));seed=int(method.prior.sha([TAG,j['root']])[:12],16)%(2**31-1)
                        for arm in arms:
                            session.check();request=(method.prior if arm=='old_repair' else method).payload(j,seed)
                            budget=count_prompt(session,request['messages'],8192,3072);start=time.perf_counter()
                            try:reply=session.request('/v1/chat/completions',request,timeout=180)
                            except HTTPError as exc:
                                raw.append(dict(record_type='HTTP_ERROR',arm=arm,root=j['root'],payload=request,job=j,
                                    error=capture_http_error(exc,session.key)));raise
                            seconds=time.perf_counter()-start
                            native=method.prior.channels(reply);parsed=None;row=None;reason=''
                            try:
                                if native['finish_reason']!='stop':raise ValueError('native final incomplete: '+str(native['finish_reason']))
                                parsed=method.prior.parse_fields(native['final'])
                                if parsed['status']=='THREE_QA_FIELDS_COMPLETE':
                                    row=method.prior.render(j,parsed['pairs'],tok,repaired=True,
                                        record_id=method.prior.sha([TAG,arm,j['root']]),note=parsed['note'])
                                    row['meta'].update(source_split='posthoc_dev',source_cohort='previous_fixed_source8',
                                        original_task_contract=method.VERSION,teacher_task=arm)
                            except ValueError as exc:reason=str(exc)
                            record=dict(arm=arm,root=j['root'],language=j['language'],seed=seed,payload=request,reply=reply,channels=native,
                                parsed=parsed,structural_reason=reason,input_budget=budget,request_sec=seconds,job=j)
                            raw.append(record);c=counts[arm];c.update(requests=1,request_sec=seconds,completion_tokens=int(reply.get('usage',{}).get('completion_tokens') or 0))
                            if row is not None:
                                accepted.append(dict(arm=arm,root=j['root'],row=row));c.update(structural_rows=1,student_x=row['meta']['actual_x_tokens'],assistant_targets=row['meta']['assistant_targets'])
                            results.append(dict(arm=arm,root=j['root'],language=j['language'],accepted=row is not None,structural_reason=reason,
                                declined=bool(parsed and parsed['status']=='PRODUCER_DECLINED')))
                            print('[TASK_CONTRACT_ANSWER] '+json.dumps(dict(arm=arm,root=j['root'],language=j['language'],seconds=seconds,
                                final=native['final'],structural_reason=reason,quality='POSTHOC_ONLY'),ensure_ascii=False),flush=True)
                    memory_report=dict(sampled=session.memory(),telemetry=reader.snapshot(),persistent=memory.snapshot())
    except BaseException as exc:
        import traceback
        traceback.print_exc();error=dict(type=type(exc).__name__,reason=str(exc)[:1200])
    rm=raw.close(lineage=info()) if raw._total_rows else None
    cm=accepted.close(lineage=info()) if accepted._total_rows else None
    for manifest in (rm,cm):
        if manifest:verify(target,manifest)
    report=dict(info(),status='OPERATION_ERROR' if error else 'TEACHER_CONTRACT_PILOT_LOGGED',counts={k:dict(v) for k,v in counts.items()},
        results=results,raw_manifest=rm,candidate_manifest=cm,assets=assets if 'assets' in locals() else None,memory=memory_report,
        input_report_sha256=old.training.data.digest(OUTPUT/'inputs.json'),whole_sec=time.perf_counter()-began,error=error,
        semantic_acceptance='NOT_RUN; parsing/length only',student_checkpoint_created=False)
    old.training.write(EVIDENCE/'pilot.json',report);old.training.write(target/'report.json',report)
    print('[TASK_CONTRACT_FINAL] '+json.dumps(dict(status=report['status'],counts=report['counts'],whole_sec=report['whole_sec'])),flush=True)
    return 9 if error else 0


def readback():
    from tokenizers import Tokenizer
    r=old.required(EVIDENCE/'pilot.json');out=EVIDENCE/'readback.json'
    if out.exists():raise GateNegative('old task contract recount preserved')
    if r['code_sha256']!=info()['code_sha256']:raise ValueError('same frozen CODE required')
    p=OUTPUT/'pilot';verify(p,r['raw_manifest'])
    if r['candidate_manifest']:verify(p,r['candidate_manifest'])
    values=list(old.training.data.stream_rows(p,r['raw_manifest']))
    keys={(x['arm'],x['root']) for x in values}
    if len(values)!=16 or len(keys)!=16 or Counter(v['arm'] for v in values)!=dict(old_repair=8,new_grounded_qa=8):raise ValueError('complete matched8 roots/two contracts required')
    seeds=defaultdict(set);counts={k:Counter() for k in ARMS};tok=Tokenizer.from_file(str(old.training.data.TOKENIZER))
    candidate_rows=list(old.training.data.stream_rows(p,r['candidate_manifest'])) if r['candidate_manifest'] else []
    candidates={(v['arm'],v['root']):v['row'] for v in candidate_rows}
    if len(candidates)!=len(candidate_rows):raise ValueError('unique arm/root candidate required')
    for v in values:
        seeds[v['root']].add(v['seed']);native=method.prior.channels(v['reply'])
        if native!=v['channels']:raise ValueError('raw channel recount differs')
        c=counts[v['arm']];c.update(requests=1,request_sec=v['request_sec'],completion_tokens=int(v['reply'].get('usage',{}).get('completion_tokens') or 0))
        parsed=None;row=None;reason=''
        try:
            if native['finish_reason']!='stop':raise ValueError('native final incomplete: '+str(native['finish_reason']))
            parsed=method.prior.parse_fields(native['final'])
            if parsed['status']=='THREE_QA_FIELDS_COMPLETE':
                row=method.prior.render(v['job'],parsed['pairs'],tok,repaired=True,
                    record_id=method.prior.sha([TAG,v['arm'],v['root']]),note=parsed['note'])
                row['meta'].update(source_split='posthoc_dev',source_cohort='previous_fixed_source8',
                    original_task_contract=method.VERSION,teacher_task=v['arm'])
        except ValueError as exc:reason=str(exc)
        if parsed!=v['parsed'] or reason!=v['structural_reason']:raise ValueError('raw parsing/length recount differs')
        if row!=candidates.get((v['arm'],v['root'])):raise ValueError('candidate canonical content changed')
        if row is not None:c.update(structural_rows=1,student_x=row['meta']['actual_x_tokens'],assistant_targets=row['meta']['assistant_targets'])
    if any(len(s)!=1 for s in seeds.values()):raise ValueError('same root seed required')
    if {k:dict(v) for k,v in counts.items()}!=r['counts']:raise ValueError('full raw counters differ')
    old.training.write(out,dict(info(),status='MATCHED16_RAW_RECOUNTED',requests=16,roots=8,
        counts=r['counts'],pilot_sha256=old.training.data.digest(EVIDENCE/'pilot.json'),semantic_truth='NOT_RUN'))
    print('[TASK_CONTRACT_READBACK] '+json.dumps(dict(requests=16,roots=8,semantic_truth='NOT_RUN')),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','pilot','readback'),required=True);p.add_argument('--max-wall-sec',type=int,default=600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print(json.dumps(info()));return 0
    try:
        old.original.prior.producer.legacy.source.deadline()
        if a.mode=='freeze':return freeze()
        if a.mode=='readback':return readback()
        if a.max_wall_sec!=600:raise ValueError('fixed ten-minute teacher diagnostic only')
        remaining=(old.original.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
        if remaining<3300:raise GateNegative('teacher bound plus45minute closure margin required')
        return pilot(a)
    except GateNegative as exc:print('[TASK_CONTRACT_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[TASK_CONTRACT_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
