"""Frozen TRAIN128 exact byte/position preparation and native teacher top128."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback
import weakref
from scripts import diag_p106b_actd_anchor as inventory
from scripts import diag_p106b_alm_cache as encoder
from scripts import diag_p106b_qwen35_fixedshape as qualified
from scripts import diag_p106b_qwen35_legacy_fixed as legacy
from scripts import p106b_actd_anchor as actd
from scripts import p106b_actd_cache as cache
from scripts.p106b_alm_bytes import SpecialToken,build_teacher_stream,student_piece_bytes

ROOT=inventory.ROOT;TAG='p106b_actd_top128_v1_20261113';BASE=ROOT/'test_result/evidence'/TAG
DEADLINE=qualified.DEADLINE;K=128
SOURCES=('scripts/p106b_actd_cache.py','scripts/test_p106b_actd_cache.py',
 'scripts/diag_p106b_actd_topk.py','scripts/test_p106b_actd_topk.py',
 'scripts/p106b_actd_consumer.py','scripts/test_p106b_actd_consumer.py',
 'scripts/diag_p106b_actd_consumer.py','scripts/p106b_actd_anchor.py',
 'scripts/diag_p106b_actd_anchor.py','scripts/diag_p106b_alm_cache.py','scripts/p106b_alm_bytes.py',
 'tinylm/train/mtp_sft.py','tinylm/data/sft.py','tinylm/chat/serialize.py','tinylm/chat/canonical.py',
 'scripts/p106b_shards.py','scripts/diag_p106b_gsq_objective.py','scripts/p106b_weight_route.py',
 'scripts/interactive_research_infer.py','tinylm/model/transformer.py','tinylm/model/modules.py',
 'tinylm/model/ternary.py','tinylm/config.py')


def guard(start=None,cap=600):
    if (DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
        raise TimeoutError('User115 ACTD authority cleanup reserve')
    if start is not None and time.perf_counter()-start>cap:
        raise TimeoutError('ACTD phase time budget')


def write_new(path,obj):
    return inventory.write_new(path,obj)


def teacher_stream(packed,tokenizer,raw,*,added_declarations=None):
    text=packed['text'];out=tokenizer(text,add_special_tokens=False,return_offsets_mapping=True)
    ids=list(out['input_ids']);offsets=[list(p) for p in out['offset_mapping']]
    if len(ids)!=len(offsets) or not ids:raise ValueError('untruncated complete native teacher token offsets required')
    keep,owners=encoder.owners_for_offsets(offsets,packed['student']['loss_spans_chars'])
    declared=raw['added_tokens'] if added_declarations is None else added_declarations
    added={r['id']:r for r in declared};ordinary={i:s for s,i in raw['model']['vocab'].items()}
    pieces=[];specials=[]
    for index,token_id in enumerate(ids):
        if token_id in added:
            meta=added[token_id];piece=meta['content'].encode('utf-8',errors='strict')
            if meta['special']is True:specials.append(SpecialToken(index,token_id,meta['content'],piece))
        elif token_id in ordinary:piece=student_piece_bytes(ordinary[token_id])
        else:raise ValueError('teacher encoded an undeclared native ID')
        pieces.append(list(piece))
    stream=build_teacher_stream(text,ids,pieces,supervised=keep,turn_ids=owners,specials=specials)
    return stream,dict(ids=ids,char_offsets=offsets,supervised=keep,turn_ids=owners,
        byte_spans=encoder.stream_summary(stream),ids_sha256=encoder.object_sha(ids))


def prepared_row(frozen,index,root_order_sha,tok,teacher_tokenizer,teacher_raw,special_ids,*,added_declarations=None):
    if encoder.object_sha(frozen['source_row'])!=frozen['source_row_sha256']:
        raise ValueError('frozen original source row changed')
    from tinylm.train.mtp_sft import encode_record
    from tinylm.data.sft import encode_conversation
    from tinylm.chat.serialize import loss_spans
    spec=dict(row=frozen['source_row'],row_sha256=frozen['source_row_sha256'],
        x_tokens=len(frozen['record']['x']),ce_targets=frozen['ce_targets'],source_index=None,
        root=frozen['semantic_root_id'],language=frozen['language'],root_order_sha256=root_order_sha)
    packed=encoder.pack_student(spec,tok,encode_record,encode_conversation,loss_spans,special_ids)
    record=dict(x=packed['student']['ids'][:-1],y=packed['student']['labels'][1:],segments=packed['student']['turn_ids'][1:])
    if record!=frozen['record'] or encoder.object_sha(record)!=frozen['record_sha256']:
        raise ValueError('original encoder no longer reproduces the frozen one-shift record')
    student=encoder.rebuild_student(packed);teacher,native=teacher_stream(packed,teacher_tokenizer,teacher_raw,added_declarations=added_declarations)
    s,sh=cache.prefix_candidates(student);t,th=cache.prefix_candidates(teacher)
    aligns={};holds={}
    oversized=len(native['ids'])>1024
    for policy in cache.POLICIES:
        if oversized:
            aligns[policy]=[];holds[policy]=[dict(student_target_raw_index=r['target_raw_index'],reason='TEACHER_FULL_SEQUENCE_OVER1024',policy=policy) for r in s]
        else:aligns[policy],holds[policy]=cache.align_positions(s,t,policy=policy)
        if len(aligns[policy])+len(holds[policy])+len(sh)!=frozen['ce_targets']:
            raise ValueError('every original CE target must have aligned/HOLD accounting')
    union=sorted({r['teacher_prefix_raw_index'] for values in aligns.values() for r in values})
    if any(i<0 or i>=len(native['ids'])-1 for i in union):raise ValueError('predictor must precede its native next target')
    return dict(schema='P106B_ACTD_PREPARED_ROW_V1',row_id=frozen['row_id'],frozen_index=index,
        source_train_index=None,source_train_index_status='ORIGINAL_CORPUS_INDEX_NOT_EXPORTED',
        semantic_root_id=frozen['semantic_root_id'],language=frozen['language'],
        source_row_sha256=frozen['source_row_sha256'],record_sha256=frozen['record_sha256'],
        packed=packed,teacher=native,teacher_oversized=oversized,ce_targets=frozen['ce_targets'],
        student_boundary_holds=sh,teacher_boundary_holds=th,alignments=aligns,alignment_holds=holds,
        teacher_prefix_union=union,original_ce_unchanged=True)


def prepare():
    import os
    for key,value in qualified.q.official.OFFLINE.items():os.environ[key]=value
    start=time.perf_counter();guard();qp=qualified.verify();legacy.verify()
    if BASE.exists():raise FileExistsError('fresh ACTD top128 namespace required')
    ip=json.loads((inventory.BASE/'profile.json').read_text());inv=json.loads((inventory.BASE/'report.json').read_text())
    for name,sha in ip['sources'].items():
        if inventory.digest(ROOT/name)!=sha:raise ValueError('closed vocabulary inventory source changed')
    references=[inventory.ROWS,inventory.GSQ_PROFILE,inventory.BASE/'profile.json',inventory.BASE/'report.json',
        inventory.BASE/'teacher_to_student_anchors.json',inventory.BASE/'teacher_mapping_modes.json',
        qualified.BASE/'profile.json',qualified.BASE/'canary/report.json',qualified.BASE/'ROOT_CANARY_EXIT_v1.json',legacy.BASE/'profile.json',inventory.TOKENIZER]
    old=json.loads(inventory.GSQ_PROFILE.read_text())
    if inventory.digest(inventory.ROWS)!=old['references'][str(inventory.ROWS.relative_to(ROOT))]:raise ValueError('same frozen TRAIN128 pin required')
    source_rows=json.loads(inventory.ROWS.read_text())['rows']
    if inv['cache_inventory']!=inventory.inventory(source_rows):raise ValueError('same immutable TRAIN export inventory required')
    teacher_raw=qualified.q.read_json(qp['assets']['files']['tokenizer.json']['resolved_path'])
    teacher_metadata=qualified.q.read_json(qp['assets']['files']['tokenizer_config.json']['resolved_path'])
    tokenizer,tokenizer_proof=qualified.q.build_tokenizer(teacher_raw,teacher_metadata)
    declarations=qualified.q.tokenizer_declarations(teacher_raw,teacher_metadata)
    qualified.q.validate_tokenizer(tokenizer,teacher_raw,teacher_metadata,declarations)
    # Same already-validated raw22 + config33 composition used by the actual HF frontend.
    # This metadata view is only for byte/mapping declarations, never a tokenizer rewrite.
    native_added=[dict(value,id=key) for key,value in sorted(declarations['decoder'].items())]
    from tokenizers import Tokenizer
    student=Tokenizer.from_file(str(inventory.TOKENIZER));student_raw=json.loads(inventory.TOKENIZER.read_text())
    special_ids={r['id']:r['content'] for r in student_raw['added_tokens'] if r['special']}
    ordinary={i:student_piece_bytes(s) for s,i in student_raw['model']['vocab'].items() if i not in special_ids}
    special_true={r['id'] for r in native_added if r['special']is True}
    explicit={int(k):v for k,v in ip['teacher_special_map'].items()}
    mapper=actd.AnchorMapper(ordinary,32768,lambda text:student.encode(text,add_special_tokens=False).ids,
        teacher_special_ids=special_true,special_map=explicit)
    anchors=json.loads((inventory.BASE/'teacher_to_student_anchors.json').read_text())
    overrides=cache.literal_added_overrides(dict(added_tokens=native_added),lambda i:tokenizer.decode([i],skip_special_tokens=False),mapper,anchors)
    if len(overrides)!=12 or len(special_true)!=21:raise ValueError('inspected added False12/True21 contract changed')
    for r in overrides:anchors[r['teacher_id']]=r['anchor_id']
    root_order=encoder.object_sha([r['semantic_root_id'] for r in source_rows]);rows=[]
    for i,row in enumerate(source_rows):
        guard(start);rows.append(prepared_row(row,i,root_order,student,tokenizer,teacher_raw,special_ids,added_declarations=native_added))
    BASE.mkdir(parents=True)
    from scripts.p106b_shards import ShardWriter
    writer=ShardWriter(BASE,'prepared',limit=3_000_000)
    for row in rows:writer.append(row)
    manifest=writer.close(lineage=dict(tag=TAG,source=inventory.digest(inventory.ROWS),split='TRAIN_ONLY'))
    write_new(BASE/'anchor_lookup.json',anchors);write_new(BASE/'added_literal_overrides.json',overrides)
    sources={n:inventory.digest(ROOT/n) for n in SOURCES}
    refs={str(p.relative_to(ROOT)):inventory.digest(p) for p in references}
    counts=dict(rows=len(rows),languages=dict(Counter(r['language'] for r in rows)),
        actual_x_tokens=sum(len(r['packed']['student']['ids'])-1 for r in rows),ce_targets=sum(r['ce_targets'] for r in rows),
        teacher_full_tokens=sum(len(r['teacher']['ids']) for r in rows),teacher_prefix_union=sum(len(r['teacher_prefix_union']) for r in rows),
        teacher_oversized_rows=sum(r['teacher_oversized'] for r in rows),student_boundary_holds=sum(len(r['student_boundary_holds']) for r in rows),
        aligned={p:sum(len(r['alignments'][p]) for r in rows) for p in cache.POLICIES},
        alignment_holds={p:sum(len(r['alignment_holds'][p]) for r in rows) for p in cache.POLICIES},
        lookahead={p:sum(x['lookahead_characters']>0 for r in rows for x in r['alignments'][p]) for p in cache.POLICIES})
    if (counts['rows'],counts['languages'],counts['actual_x_tokens'],counts['ce_targets'])!=(128,{'ko':64,'en':64},32216,772):
        raise ValueError('frozen exact bilingual data/CE counts changed')
    profile=dict(schema='P106B_ACTD_TOP128_PROFILE_V1',tag=TAG,authority_directive=115,deadline=DEADLINE.isoformat(),
        sources=sources,references=refs,qualified_profile_sha256=inventory.digest(qualified.BASE/'profile.json'),
        legacy_profile_sha256=inventory.digest(legacy.BASE/'profile.json'),k=128,teacher_vocab=248320,student_vocab=32768,
        temperature=1.,residual_weight=1.,primary_policy='nearest_monotonic',secondary_policy='causal_left_variant',
        mapping_policy='EXPLICIT_HF_SPECIAL_TRUE_AND_FALSE_LITERAL_FIRST_SUBTOKEN_V1',
        root_order_sha256=root_order,student_pad_id=student.token_to_id('<pad>'),
        student_model=old['entry'],student_checkpoint=old['checkpoint'],
        manual_manifest_sha256=old['manual_manifest_sha256'],prepared_manifest=manifest,
        anchor_lookup_sha256=inventory.digest(BASE/'anchor_lookup.json'),added_override_sha256=inventory.digest(BASE/'added_literal_overrides.json'),
        counts=counts,teacher_tokenizer_proof=tokenizer_proof,corpus_admitted=False,
        training=False,optimizer_updates=0,checkpoint_writes=0,quality_claim=False)
    write_new(BASE/'profile.json',profile)
    for name,sha in dict(sources,**refs).items():
        if inventory.digest(ROOT/name)!=sha:raise ValueError('preparation source changed: '+name)
    import torch
    if torch.cuda.is_initialized():raise RuntimeError('CPU preparation initialized CUDA')
    report=dict(status='ACTD_TOP128_POSITIONS_PREPARED_NOT_TEACHER_CACHE',returncode=0,counts=counts,
        profile_sha256=inventory.digest(BASE/'profile.json'),seconds=time.perf_counter()-start,cuda_initialized=False,
        sources_unchanged=True,training_ready=False,quality_claim=False)
    write_new(BASE/'prepare_report.json',report);print('[ACTD_POSITIONS_PREPARED] '+json.dumps(report),flush=True)


def verify():
    guard();qualified.verify();legacy.verify();p=json.loads((BASE/'profile.json').read_text())
    if p['deadline']!=DEADLINE.isoformat() or p['authority_directive']!=115 or p['k']!=128:
        raise ValueError('ACTD current authority/top128 contract changed')
    for name,sha in dict(p['sources'],**p['references']).items():
        if inventory.digest(ROOT/name)!=sha:raise ValueError('frozen source/reference changed: '+name)
    if inventory.digest(BASE/'anchor_lookup.json')!=p['anchor_lookup_sha256'] or inventory.digest(BASE/'added_literal_overrides.json')!=p['added_override_sha256']:
        raise ValueError('frozen anchor mapping changed')
    from scripts.p106b_shards import verify as verify_shards
    verify_shards(BASE,p['prepared_manifest'])
    rows=[]
    for shard in p['prepared_manifest']['shards']:
        for line in (BASE/shard['path']).read_text().splitlines():rows.append(json.loads(line))
    if len(rows)!=128 or len({r['row_id'] for r in rows})!=128:raise ValueError('all original128 rows required')
    return p,rows


def legacy_prerequisite():
    r=json.loads((legacy.BASE/'actual/report.json').read_text());w=json.loads((legacy.BASE/'ROOT_ACTUAL_EXIT_v1.json').read_text())
    if (r.get('status')!='EXACT_LEGACY_FIXED_COMPLETE' or r.get('returncode')!=0
            or not r.get('sources_assets_unchanged') or not r.get('exact_legacy_fixed',{}).get('legacy_result',{}).get('passed')
            or r.get('final_cuda_cleanup',{}).get('allocated_bytes')!=0 or r.get('final_cuda_cleanup',{}).get('reserved_bytes')!=0
            or w.get('actual_process_exit_code')!=0 or w.get('report_sha256')!=inventory.digest(legacy.BASE/'actual/report.json')):
        raise ValueError('same exact legacy prefix numerical proof and root actual exit0 required')
    return inventory.digest(legacy.BASE/'actual/report.json')


def teacher():
    p,rows=verify();legacy_sha=legacy_prerequisite();start=time.perf_counter();cap=1800;guard(start,cap)
    out=BASE/'teacher'
    if out.exists():raise FileExistsError('teacher attempt already exists; preserve partial raw')
    out.mkdir();report=dict(tag=TAG,status='RUNNING',returncode=9,profile_sha256=inventory.digest(BASE/'profile.json'),
        legacy_report_sha256=legacy_sha,training=False,optimizer_updates=0,checkpoint_writes=0,quality_claim=False,
        started_at=datetime.now(timezone.utc).isoformat(),rows_completed=0,accepted_positions={p:0 for p in cache.POLICIES},
        held_positions={p:0 for p in cache.POLICIES},real_prefix_checks=[])
    torch=lm=ref=writer=trace=None;failure=None
    check=lambda:guard(start,cap-120)
    try:
        import os
        for name,value in qualified.q.official.OFFLINE.items():os.environ[name]=value
        from scripts.interactive_research_infer import require_idle_gpu
        report['entry_gpu_point']=require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],check=True,capture_output=True,text=True,timeout=10).stdout.strip()
        if not free.isdigit() or int(free)<12288:raise MemoryError('teacher requires12288MiB free point')
        import torch
        from torch.nn.attention import sdpa_kernel,SDPBackend
        from scripts import p106b_qwen35_fixedshape as fixed
        from scripts.p106b_shards import ShardWriter
        torch.set_num_threads(4);torch.manual_seed(1337)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch.cuda.reset_peak_memory_stats();qp=qualified.verify();proof=report['model_proof']={}
        anchors=json.loads((BASE/'anchor_lookup.json').read_text());stats=report['fixed_calls']={}
        trace=ShardWriter(out,'calls',limit=3_000_000);writer=ShardWriter(out,'top128',limit=3_000_000);seen_lang=set()
        with qualified.q.wall_limit(cap-120),torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
            with qualified.q.model_runtime(torch,qp['assets'],trace,check,proof,qp['source_identity']) as lm:
                ref=weakref.ref(lm.model)
                for row in rows:
                    check();positions=row['teacher_prefix_union'];distributions={}
                    if positions:
                        ids=torch.tensor([row['teacher']['ids'][:-1]],dtype=torch.long,device='cuda')
                        logits=fixed.logits(lm.model,ids,width=1024,pad_id=248044,vocab=248320,check=check,stats=stats)
                        if row['language']not in seen_lang:
                            for index in sorted({positions[0],positions[-1]}):
                                prefix=fixed.logits(lm.model,ids[:,:index+1],width=1024,pad_id=248044,vocab=248320,check=check,stats=stats)
                                r=fixed.compare_prefix(logits[:,:index+1],prefix,atol=qualified.q.official.ATOL,rtol=qualified.q.official.RTOL)
                                report['real_prefix_checks'].append(dict(row_id=row['row_id'],language=row['language'],predictor=index,**r));del prefix
                                if not r['close']:raise ValueError('actual TRAIN prefix/full future numerical mismatch')
                            seen_lang.add(row['language'])
                        for offset in range(0,len(positions),32):
                            indices=positions[offset:offset+32]
                            selected=logits[0].index_select(0,torch.tensor(indices,device='cuda'))
                            top_ids,top_scores,logz=cache.native_topk(selected,k=128)
                            a,b,z=top_ids.cpu().tolist(),top_scores.cpu().tolist(),logz.cpu().tolist()
                            for i,teacher_ids,scores,normalizer in zip(indices,a,b,z):
                                distributions[i]=cache.distribution(teacher_ids,scores,normalizer,anchor_lookup=anchors,student_vocab=32768,k=128)
                            del selected,top_ids,top_scores,logz
                        del ids,logits
                    acceptance={}
                    for policy in cache.POLICIES:
                        good,held=cache.accepted_positions(row,distributions,policy=policy,k=128,anchor_lookup=anchors,student_vocab=32768)
                        acceptance[policy]=dict(accepted=len(good),held=len(held));report['accepted_positions'][policy]+=len(good);report['held_positions'][policy]+=len(held)
                    writer.append(dict(schema='P106B_ACTD_NATIVE_TOP128_ROW_V1',row_id=row['row_id'],prepared_row_sha256=encoder.object_sha(row),
                        distributions={str(i):v for i,v in distributions.items()},acceptance=acceptance))
                    trace.append(dict(row_id=row['row_id'],teacher_full_tokens=len(row['teacher']['ids']),predictor_positions=positions,
                        actual_body_width=1024,processed=bool(positions)))
                    report['rows_completed']+=1
                    if report['rows_completed']%16==0:print('[ACTD_TEACHER_PROGRESS] '+json.dumps({k:report[k] for k in ['rows_completed','accepted_positions','held_positions']}),flush=True)
            lm=None;gc.collect();report['owned_model_alive_after_release']=ref()is not None
            if report['owned_model_alive_after_release']:raise RuntimeError('owned teacher body still alive')
        report.update(status='ACTD_NATIVE_TOP128_COMPLETE',returncode=0)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',returncode=9,error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        lm=None;gc.collect()
        if torch is not None:
            report['peak_allocated_bytes']=torch.cuda.max_memory_allocated();report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            try:
                from scripts.diag_p107_hybrid_mntp import close_owned_cuda
                close_owned_cuda(torch,report)
            except BaseException as exc:
                report.update(status='ERROR',returncode=9,cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        for obj,key in [(writer,'cache_manifest'),(trace,'call_manifest')]:
            if obj is not None:
                try:report[key]=obj.close(lineage=dict(tag=TAG,phase='teacher',quality_claim=False))
                except BaseException as exc:
                    report.update(status='ERROR',returncode=9,writer_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:verify();legacy_prerequisite();report['sources_and_inputs_unchanged']=True
        except BaseException as exc:
            report.update(status='ERROR',returncode=9,source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report.update(seconds=time.perf_counter()-start,finished_at=datetime.now(timezone.utc).isoformat())
        write_new(out/'report.json',report)
    if failure is not None:raise failure
    print('[ACTD_TEACHER_FINAL] '+json.dumps({k:report[k] for k in ['status','returncode','seconds','rows_completed','accepted_positions','held_positions']}),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','teacher']);args=p.parse_args()
    (prepare if args.phase=='prepare' else teacher)()


if __name__=='__main__':main()
