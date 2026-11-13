"""Expand only a closed TRAIN1024 snapshot; reuse all128 old native features."""
import argparse
from collections import Counter
import gc
import json
import os
import time
import traceback
import weakref
import numpy as np
from scripts import diag_p106b_dskdv2_bridge as native
from scripts.p106b_dskdv2_reuse import reusable
from scripts.p106b_shards import ShardWriter,verify as verify_shards

ROOT=native.ROOT;BASE=ROOT/'test_result/evidence/p106b_dskdv2_calibration1024_v1_20261113';FEATURES=ROOT/'data_cache'/BASE.name
data=native.data;exact=native.exact
SOURCES=('scripts/p106b_dskdv2_reuse.py','scripts/test_p106b_dskdv2_reuse.py','scripts/diag_p106b_dskdv2_calibration1024.py')


def prepare():
    native.verify();_a,_p,oldrows,cached,_f,_ac,_m=native.inputs();data.guard();start=time.perf_counter()
    if BASE.exists()or FEATURES.exists():raise FileExistsError('fresh expanded calibration namespace required')
    from scripts import diag_p106b_gsq_objective as original
    from scripts.p101a_sft_mtp_data import stream_rows
    from tokenizers import Tokenizer
    source=original.TRAIN;report=exact.read(source/'report.json');manifest=report['manifest'];verify_shards(source,manifest)
    frozen=list(stream_rows(source,manifest))
    if report.get('status')!='ALM_TRAIN_PREPARED'or len(frozen)!=1024 or len({r['semantic_root_id']for r in frozen})!=1024:
        raise ValueError('closed original TRAIN1024 source only')
    for r in frozen:
        if data.encoder.object_sha(r['source_row'])!=r['source_row_sha256']or data.encoder.object_sha(r['record'])!=r['record_sha256']:
            raise ValueError('frozen source/one-shift original changed')
    qp=data.qualified.verify();raw=data.qualified.q.read_json(qp['assets']['files']['tokenizer.json']['resolved_path'])
    metadata=data.qualified.q.read_json(qp['assets']['files']['tokenizer_config.json']['resolved_path'])
    tok,_proof=data.qualified.q.build_tokenizer(raw,metadata);native_added=json.loads(tok.backend_tokenizer.to_str())['added_tokens']
    student=Tokenizer.from_file(str(data.inventory.TOKENIZER));sr=exact.read(data.inventory.TOKENIZER)
    specials={r['id']:r['content']for r in sr['added_tokens']if r['special']};oldbyroot={r['semantic_root_id']:r for r in oldrows}
    paths=[ROOT/x for x in SOURCES]+[source/'report.json',native.BASE/'profile.json',native.BASE/'student/report.json',native.BASE/'ROOT_STUDENT_EXIT_v1.json',native.recovered.BASE/'features_manifest.json']
    paths.extend(source/s['path']for s in manifest['shards']);pins={str(p.relative_to(ROOT)):exact.digest(p)for p in paths}
    writer=ShardWriter(BASE,'prepared',limit=3_000_000);counts=Counter();languages=Counter();canaries={};root_order=data.encoder.object_sha([r['semantic_root_id']for r in frozen])
    for i,r in enumerate(frozen):
        data.guard(start,600);row=data.prepared_row(r,i,root_order,student,tok,raw,specials,added_declarations=native_added);row['row_id']='cal1024_'+f'{i:06d}'
        pairs,held=native.bridge.reference.exact_pairs(row['packed']['text'],row['packed']['student']['byte_spans'],row['teacher']['byte_spans'])
        if len(pairs)+len(held)!=row['ce_targets']:raise ValueError('original CE exact/HOLD accounting changed')
        row.update(exact_gold_candidates=pairs,exact_holds=held,reuse_original_row_id=None)
        if r['semantic_root_id']in oldbyroot:
            old=oldbyroot[r['semantic_root_id']]
            if not reusable(row,old):raise ValueError('original128 identity cannot be reused')
            row['reuse_original_row_id']=old['row_id'];counts['reused_rows']+=1
        elif not row['teacher_oversized']and pairs and row['language']not in canaries:
            canaries[row['language']]=dict(row_id=row['row_id'],predictor=min(p['teacher_predictor_raw_index']for p in pairs))
        counts.update(rows=1,actual_x=len(row['packed']['student']['ids'])-1,ce_targets=row['ce_targets'],exact_candidates=len(pairs),holds=len(held),oversized_rows=int(row['teacher_oversized']))
        languages[row['language']]+=1;writer.append(row)
    m=writer.close(lineage=dict(tag=BASE.name,source_sha256=exact.digest(source/'report.json'),train_only=True))
    if counts['rows']!=1024 or counts['reused_rows']!=128 or languages!={'ko':512,'en':512}or set(canaries)!={'ko','en'}:raise ValueError('exact TRAIN1024/reused128/new896 inventory required')
    exact.write(BASE/'profile.json',dict(tag=BASE.name,authority_directive=115,deadline=data.DEADLINE.isoformat(),sources=pins,prepared_manifest=m,
        counts=dict(counts),languages=dict(languages),canaries=canaries,new_feature_cache=str(FEATURES.relative_to(ROOT)),
        teacher='QUALIFIED_FIXED_FP32_MATH_B1_1024',student_body_calls=0,optimizer_updates=0,checkpoint_writes=0,corpus_admitted=False,quality_claim=False))
    print('[CAL1024_PREPARED] '+json.dumps(dict(counts=dict(counts),canaries=canaries,seconds=time.perf_counter()-start,model_loads=0,gpu_calls=0)),flush=True)


def verify():
    native.verify();data.guard();p=exact.read(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=data.DEADLINE.isoformat():raise ValueError('expanded calibration authority changed')
    for name,sha in p['sources'].items():
        if exact.digest(ROOT/name)!=sha:raise ValueError('expanded calibration pinned source changed')
    verify_shards(BASE,p['prepared_manifest']);rows=[]
    for s in p['prepared_manifest']['shards']:rows.extend(json.loads(line)for line in (BASE/s['path']).read_text().splitlines())
    if len(rows)!=1024:raise ValueError('expanded prepared inventory differs')
    return p,rows


def actual():
    p,rows=verify();_a,_op,_oldrows,oldcached,_f,_ac,_m=native.inputs();start=time.perf_counter();out=BASE/'teacher'
    if out.exists()or FEATURES.exists():raise FileExistsError('expanded calibration actual/cache already attempted')
    out.mkdir();FEATURES.mkdir();positions_writer=trace=None;torch=lm=None;failure=None
    report=dict(tag=BASE.name,status='RUNNING',returncode=9,profile_sha256=exact.digest(BASE/'profile.json'),rows_completed=0,
        reused_rows=0,new_body_calls=0,new_causal_calls=0,accepted_positions=0,ce_targets=0,features=[],training=False,optimizer_updates=0,checkpoint_writes=0,corpus_admitted=False,quality_claim=False)
    try:
        from scripts.interactive_research_infer import require_idle_gpu
        report['entry_gpu_point']=require_idle_gpu()
        import subprocess
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],check=True,capture_output=True,text=True,timeout=10).stdout.strip()
        if not free.isdigit()or int(free)<12288:raise MemoryError('expanded native teacher requires12288MiB free point')
        for k,v in data.qualified.q.official.OFFLINE.items():os.environ[k]=v
        import torch
        from torch.nn.attention import sdpa_kernel,SDPBackend
        from scripts.p106b_dskdv2_native import capture_native
        from scripts import p106b_qwen35_fixedshape as fixed
        torch.set_num_threads(4);torch.manual_seed(1337);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.cuda.reset_peak_memory_stats()
        qp=data.qualified.verify();proof=report['model_proof']={};stats=report['fixed_calls']={};canaries={v['row_id']:v['predictor']for v in p['canaries'].values()}
        mapping=exact.read(native.heads.MAP/'teacher_to_student_anchors.json');modes=exact.read(native.heads.MAP/'teacher_mapping_modes.json')
        positions_writer=ShardWriter(out,'positions',limit=3_000_000);trace=ShardWriter(out,'calls',limit=3_000_000)
        with data.qualified.q.wall_limit(1680),torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
            with data.qualified.q.model_runtime(torch,qp['assets'],trace,lambda:data.guard(start,1680),proof,qp['source_identity'])as lm:
                ref=weakref.ref(lm.model)
                for row in rows:
                    data.guard(start,1680);alias=row['reuse_original_row_id'];ce=row['ce_targets'];record=dict(row_id=row['row_id'],semantic_root_id=row['semantic_root_id'],language=row['language'],source_row_sha256=row['source_row_sha256'],record_sha256=row['record_sha256'],positions=[],ce_targets=ce)
                    if alias:
                        old=oldcached[alias];path=native.first.FEATURES/(alias+'.npy');record.update(positions=old['positions'],feature_path=str(path.relative_to(ROOT)),feature_sha256=old['feature_sha256'],reused_original_row_id=alias,native_head=old['native_head']);report['reused_rows']+=1
                    elif row['teacher_oversized']:
                        record.update(hold_reason='TEACHER_FULL_SEQUENCE_OVER1024',feature_path=None,feature_sha256=None)
                    else:
                        ids=torch.tensor([row['teacher']['ids'][:-1]],device='cuda',dtype=torch.long)
                        full,feature,proofrow=capture_native(lm.model,ids,fixed_call=fixed.logits,width=1024,vocab=248320,hidden_width=1024,pad_id=248044,check=lambda:data.guard(start,1680),stats=stats)
                        trace.append(dict(row_id=row['row_id'],kind='NEW_NATIVE_FULL_SOURCE',proof=proofrow));report['new_body_calls']+=1
                        path=FEATURES/(row['row_id']+'.npy')
                        with path.open('xb')as stream:np.save(stream,feature.numpy(),allow_pickle=False)
                        record.update(feature_path=str(path.relative_to(ROOT)),feature_sha256=exact.digest(path),native_head=proofrow)
                        for pair in row['exact_gold_candidates']:
                            v=full[0,pair['teacher_predictor_raw_index']];top=int(v.argmax());mode=modes[top];good=mode in(1,3)and type(mapping[top])is int and 0<=mapping[top]<32768
                            record['positions'].append(dict(pair,teacher_native_argmax=top,teacher_native_argmax_logit=float(v[top]),teacher_native_logsumexp=float(v.logsumexp(-1)),mapping_mode=mode,accepted=good,mapped_student_argmax=mapping[top]if good else None))
                        if row['row_id']in canaries:
                            j=canaries[row['row_id']];short,hidden,shortproof=capture_native(lm.model,ids[:,:j+1],fixed_call=fixed.logits,width=1024,vocab=248320,hidden_width=1024,pad_id=248044,check=lambda:data.guard(start,1680),stats=stats)
                            check=fixed.compare_prefix(full[:,:j+1],short,atol=1e-5,rtol=1e-4);hclose=torch.allclose(feature[:j+1],hidden,atol=1e-5,rtol=1e-4)
                            trace.append(dict(row_id=row['row_id'],kind='NEW_CAUSAL_PREFIX',proof=shortproof,check=check,hidden_close=hclose));report['new_causal_calls']+=1
                            if not check['close']or not check['argmax_equal']or not hclose:raise ValueError('expanded new source causal gate failed')
                            del short,hidden
                        full=feature=ids=v=None
                    if record['feature_path']is not None:report['features'].append(dict(row_id=row['row_id'],path=record['feature_path'],sha256=record['feature_sha256']))
                    for q in record['positions']:native.recovered.recovery.acceptance_contract(q,mapping,modes)
                    accepted=sum(q['accepted']for q in record['positions']);report['accepted_positions']+=accepted;report['ce_targets']+=ce;report['rows_completed']+=1
                    positions_writer.append(record)
                    if report['rows_completed']%64==0:print('[CAL1024_PROGRESS] '+json.dumps({k:report[k]for k in ['rows_completed','reused_rows','new_body_calls','accepted_positions']}),flush=True)
            lm=None;gc.collect();report['owned_teacher_alive_after_release']=ref()is not None
            if report['owned_teacher_alive_after_release']:raise ValueError('expanded cache retained teacher')
        if report['rows_completed']!=1024 or report['reused_rows']!=128 or report['ce_targets']!=p['counts']['ce_targets']or report['new_causal_calls']!=2:raise ValueError('expanded actual source count incomplete')
        report.update(status='CLOSED_NATIVE_CALIBRATION1024_TEACHER_FEATURES',returncode=0)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        lm=full=feature=ids=v=short=hidden=None;gc.collect()
        if torch is not None and torch.cuda.is_initialized():
            report['peak_allocated_bytes']=torch.cuda.max_memory_allocated();report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            try:
                from scripts.diag_p107_hybrid_mntp import close_owned_cuda
                close_owned_cuda(torch,report)
            except BaseException as exc:report.update(status='ERROR',returncode=9,cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        manifests,errors=native.recovered.recovery.close_outputs([('positions_manifest',positions_writer),('calls_manifest',trace)],lineage=dict(tag=BASE.name,profile_sha256=exact.digest(BASE/'profile.json')));report.update(manifests)
        if errors:report.update(status='ERROR',returncode=9,finalizer_errors=errors);failure=failure or RuntimeError(repr(errors))
        try:verify();native.inputs();report['original_sources_assets_and_cache_unchanged']=True
        except BaseException as exc:report.update(status='ERROR',returncode=9,source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report['seconds']=time.perf_counter()-start;exact.write(out/'report.json',report)
    if failure:raise failure
    print('[CAL1024_FINAL] '+json.dumps({k:report[k]for k in ['status','seconds','rows_completed','reused_rows','new_body_calls','accepted_positions']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','actual']);a=parser.parse_args();(prepare if a.phase=='prepare'else actual)()
