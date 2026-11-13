"""Native fixed-width Qwen normalized features and exact-token alignment coverage."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc
import json
import os
from pathlib import Path
import subprocess
import time
import traceback
import weakref
from scripts import diag_p106b_actd_topk as data
from scripts import diag_p106b_dskdv2_contract as exact
from scripts import diag_p106b_dskdv2_heads as heads
from scripts.p106b_shards import ShardWriter,verify as verify_shards

ROOT=data.ROOT;TAG='p106b_dskdv2_hidden_v1_20261113';BASE=ROOT/'test_result/evidence'/TAG
FEATURES=ROOT/'data_cache'/TAG
SOURCES=('scripts/diag_p106b_dskdv2_hidden.py','scripts/p106b_dskdv2_native.py','scripts/test_p106b_dskdv2_native.py')


def read_positions():
    path=exact.BASE/'positions_shards_manifest.json';manifest=exact.read(path);verify_shards(exact.BASE,manifest);result={}
    for shard in manifest['shards']:
        for line in (exact.BASE/shard['path']).read_text().splitlines():
            row=json.loads(line)
            if row['row_id']in result:raise ValueError('duplicate exact-position row')
            result[row['row_id']]=row
    if len(result)!=128 or sum(len(r['exact_gold_candidates'])for r in result.values())!=557:
        raise ValueError('original exact557/128 inventory required')
    return manifest,result


def prepare():
    data.guard();p,rows=data.verify();data.legacy_prerequisite()
    if BASE.exists()or FEATURES.exists():raise FileExistsError('fresh hidden/feature namespace required')
    manifest,positions=read_positions();report=exact.read(heads.BASE/'report.json');receipt=exact.read(heads.BASE/'ROOT_CPU_EXIT_v1.json')
    if (report['status']!='CPU_NATIVE_HEAD_VJP_AND_INITIALIZATION_COMPLETE'
            or receipt.get('actual_process_exit_code')!=0 or receipt['report_sha256']!=exact.digest(heads.BASE/'report.json')):
        raise ValueError('actual native CPU head/VJP and initial projector audit required')
    canaries={};seen=set()
    for row in rows:
        pairs=positions[row['row_id']]['exact_gold_candidates']
        if row['language']not in seen:
            canaries[row['row_id']]=[min(x['teacher_predictor_raw_index']for x in pairs)];seen.add(row['language'])
    for key,index in [('alm_000034',535),('alm_000050',383)]:
        if index not in {x['teacher_predictor_raw_index']for x in positions[key]['exact_gold_candidates']}:
            raise ValueError('original two exact shared UTF8-fragment predictors changed')
        canaries.setdefault(key,[]).append(index)
    refs=[exact.BASE/'profile.json',exact.BASE/'report.json',exact.BASE/'ROOT_CPU_EXIT_v1.json',exact.BASE/'positions_shards_manifest.json',
        heads.BASE/'profile.json',heads.BASE/'report.json',heads.BASE/'ROOT_CPU_EXIT_v1.json',
        data.BASE/'profile.json',data.BASE/'teacher/report.json',data.BASE/'ROOT_TEACHER_EXIT_v1.json']
    refs.extend(exact.BASE/s['path']for s in manifest['shards'])
    refs.extend(ROOT/s for s in SOURCES)
    map_base=heads.MAP
    refs.extend(map_base/name for name in ['teacher_to_student_anchors.json','teacher_mapping_modes.json'])
    sources={str(x.relative_to(ROOT)):exact.digest(x)for x in refs}
    exact.write(BASE/'profile.json',dict(tag=TAG,authority_directive=115,deadline=data.DEADLINE.isoformat(),
        sources=sources,original_teacher_profile_sha256=exact.digest(data.BASE/'profile.json'),
        original_exact_candidates=557,original_ce_targets=772,original_x_tokens=32216,original_rows=128,
        corpus_admitted=False,exact_utf8_fragment_fallback=False,future_alignment=False,
        teacher='Qwen3.5-0.8B-Base',precision='FP32_MATH_TF32_OFF',body_width=1024,
        teacher_vocab=248320,teacher_hidden=1024,cache=False,canaries=canaries,
        feature_cache=str(FEATURES.relative_to(ROOT)),full_vocab_argmax=True,
        optimizer_updates=0,checkpoint_writes=0,quality_claim=False))
    print('[DSKDV2_HIDDEN_PREPARED] '+json.dumps(dict(tag=TAG,rows=128,exact_candidates=557,canaries=canaries,model_load=False,gpu=False)),flush=True)


def verify():
    data.guard();p,rows=data.verify();data.legacy_prerequisite();profile=exact.read(BASE/'profile.json')
    if profile['authority_directive']!=115 or profile['deadline']!=data.DEADLINE.isoformat():raise ValueError('hidden authority changed')
    for name,sha in profile['sources'].items():
        if exact.digest(ROOT/name)!=sha:raise ValueError('sealed hidden source changed: '+name)
    return profile,p,rows


def teacher():
    profile,p,rows=verify();_,positions=read_positions();start=time.perf_counter();out=BASE/'teacher'
    if out.exists()or FEATURES.exists():raise FileExistsError('hidden actual/cache already attempted')
    out.mkdir();FEATURES.mkdir();trace=writer=None;torch=lm=None;failure=None
    report=dict(tag=TAG,status='RUNNING',returncode=9,profile_sha256=exact.digest(BASE/'profile.json'),
        training=False,optimizer_updates=0,checkpoint_writes=0,quality_claim=False,corpus_admitted=False,
        rows_completed=0,features=[],prefix_checks=[],accepted_by_language={},mapping_holds={},accepted_positions=0,
        exact_candidates=557,original_ce_targets=772,original_ce_preserved=True,zero_lookahead=True,
        started_at=datetime.now(timezone.utc).isoformat())
    def check():data.guard(start,1680)
    try:
        for name,value in data.qualified.q.official.OFFLINE.items():os.environ[name]=value
        from scripts.interactive_research_infer import require_idle_gpu
        report['entry_gpu_point']=require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
        if not free.isdigit()or int(free)<12288:raise MemoryError('native teacher hidden12288MiB free point required')
        import numpy as np
        import torch
        from torch.nn.attention import sdpa_kernel,SDPBackend
        from scripts import p106b_qwen35_fixedshape as fixed
        from scripts.p106b_dskdv2_native import capture_native
        torch.set_num_threads(4);torch.manual_seed(1337)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch.cuda.reset_peak_memory_stats();qp=data.qualified.verify();proof=report['model_proof']={};stats=report['fixed_calls']={}
        mapping=exact.read(heads.MAP/'teacher_to_student_anchors.json');modes=exact.read(heads.MAP/'teacher_mapping_modes.json')
        writer=ShardWriter(out,'positions',limit=3_000_000);trace=ShardWriter(out,'calls',limit=3_000_000)
        accepted=Counter();held=Counter();mode_counts=Counter()
        with data.qualified.q.wall_limit(1680),torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
            with data.qualified.q.model_runtime(torch,qp['assets'],trace,check,proof,qp['source_identity'])as lm:
                ref=weakref.ref(lm.model)
                for row in rows:
                    check();ids=torch.tensor([row['teacher']['ids'][:-1]],dtype=torch.long,device='cuda')
                    logits,features,observed=capture_native(lm.model,ids,fixed_call=fixed.logits,width=1024,vocab=248320,
                        hidden_width=1024,pad_id=248044,check=check,stats=stats)
                    for index in profile['canaries'].get(row['row_id'],[]):
                        prefix,short,short_proof=capture_native(lm.model,ids[:,:index+1],fixed_call=fixed.logits,width=1024,
                            vocab=248320,hidden_width=1024,pad_id=248044,check=check,stats=stats)
                        result=fixed.compare_prefix(logits[:,:index+1],prefix,atol=data.qualified.q.official.ATOL,rtol=data.qualified.q.official.RTOL)
                        hclose=bool(torch.allclose(features[:index+1],short,atol=data.qualified.q.official.ATOL,rtol=data.qualified.q.official.RTOL))
                        report['prefix_checks'].append(dict(row_id=row['row_id'],predictor=index,hidden_close=hclose,
                            hidden_max_abs=float((features[:index+1]-short).abs().max()),native_short_head=short_proof,**result))
                        del prefix,short
                        if not result['close']or not hclose:raise ValueError('new exact native prefix/future check failed')
                    feature_path=FEATURES/(row['row_id']+'.npy')
                    if features.device.type!='cpu'or features.dtype!=torch.float32 or features.shape!=(ids.shape[1],1024):
                        raise ValueError('unaltered normalized CPU FP32 native feature matrix required')
                    with feature_path.open('xb')as stream:np.save(stream,features.numpy(),allow_pickle=False)
                    report['features'].append(dict(row_id=row['row_id'],path=str(feature_path.relative_to(ROOT)),
                        sha256=exact.digest(feature_path),shape=list(features.shape),dtype='float32',bytes=feature_path.stat().st_size))
                    pairs=positions[row['row_id']]['exact_gold_candidates'];selected=[]
                    for pair in pairs:
                        index=pair['teacher_predictor_raw_index'];native=logits[0,index]
                        token=int(native.argmax());mode=modes[token];student_id=mapping[token]
                        good=mode in (1,3)and type(student_id)is int and 0<=student_id<32768
                        entry=dict(pair,teacher_native_argmax=token,teacher_native_argmax_logit=float(native[token]),
                            teacher_native_logsumexp=float(torch.logsumexp(native,dim=-1)),mapping_mode=mode,
                            mapped_student_argmax=student_id if good else None,accepted=good,
                            hold_reason=None if good else 'NATIVE_TOP1_HAS_NO_EXACT_COMPLETE_STUDENT_TOKEN')
                        selected.append(entry)
                        if good:accepted[row['language']]+=1;mode_counts[str(mode)]+=1
                        else:held[entry['hold_reason']]+=1
                    writer.append(dict(row_id=row['row_id'],language=row['language'],prepared_row_sha256=data.encoder.object_sha(row),
                        native_head=observed,feature_sha256=report['features'][-1]['sha256'],positions=selected,
                        original_ce_targets=row['ce_targets'],original_ce_unchanged=True,partial_token_fallback=False))
                    del ids,logits,features,native;report['rows_completed']+=1
                    if report['rows_completed']%16==0:print('[DSKDV2_HIDDEN_PROGRESS] '+json.dumps(dict(rows=report['rows_completed'],accepted=sum(accepted.values()))),flush=True)
                report.update(accepted_by_language=dict(accepted),accepted_positions=sum(accepted.values()),
                    accepted_mapping_modes=dict(mode_counts),mapping_holds=dict(held),held_positions=772-sum(accepted.values()),
                    exact_candidates_held=557-sum(accepted.values()),nonexact_original_holds=215)
            lm=None;gc.collect();report['owned_model_alive_after_release']=ref()is not None
            if report['owned_model_alive_after_release']:raise RuntimeError('native hidden collector retained teacher model')
        if report['rows_completed']!=128 or len(report['prefix_checks'])!=4:raise ValueError('complete128 and all4 causal canaries required')
        report.update(status='DSKDV2_NATIVE_HIDDEN_AND_TOP1_COMPLETE',returncode=0)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',returncode=9,error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        lm=None;gc.collect()
        if torch is not None:
            report['peak_allocated_bytes']=torch.cuda.max_memory_allocated();report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            try:
                from scripts.diag_p107_hybrid_mntp import close_owned_cuda
                close_owned_cuda(torch,report)
            except BaseException as exc:report.update(status='ERROR',cleanup_error=repr(exc),returncode=9);failure=failure or RuntimeError(repr(exc))
        for obj,key in [(writer,'positions_manifest'),(trace,'calls_manifest')]:
            if obj is not None:report[key]=obj.close(lineage=dict(tag=TAG,profile_sha256=exact.digest(BASE/'profile.json')))
        try:verify();report['sources_assets_unchanged']=True
        except BaseException as exc:report.update(status='ERROR',source_error=repr(exc),returncode=9);failure=failure or RuntimeError(repr(exc))
        report.update(seconds=time.perf_counter()-start,finished_at=datetime.now(timezone.utc).isoformat(),
            student_model_calls=0,projection_agreement_status='NOT_RUN',full_dskdv2_training_ready=False)
        exact.write(out/'report.json',report)
    if failure is not None:raise failure
    print('[DSKDV2_HIDDEN_FINAL] '+json.dumps({k:report[k]for k in ['status','seconds','rows_completed','accepted_positions','held_positions']}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','teacher']);args=parser.parse_args()
    (prepare if args.phase=='prepare'else teacher)()


if __name__=='__main__':main()
