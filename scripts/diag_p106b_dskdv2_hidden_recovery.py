"""Reuse closed128 hidden cache after exit1; replay only four causal source rows."""
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
import numpy as np
from scripts import diag_p106b_dskdv2_hidden as first
from scripts import p106b_dskdv2_recovery as recovery
from scripts.p106b_shards import ShardWriter,verify as verify_shards

ROOT=first.ROOT;TAG='p106b_dskdv2_hidden_recovery_v2_20261113';BASE=ROOT/'test_result/evidence'/TAG
SOURCES=('scripts/p106b_dskdv2_recovery.py','scripts/test_p106b_dskdv2_recovery.py','scripts/diag_p106b_dskdv2_hidden_recovery.py')


def closed_cache():
    profile,p,rows=first.verify();_,original=first.read_positions();out=first.BASE/'teacher'
    witness=first.exact.read(first.BASE/'ROOT_FINALIZER_FAILURE_v1.json')
    manifest=first.exact.read(out/'positions_shards_manifest.json');verify_shards(out,manifest)
    if (witness['actual_tool_exit']!=1 or witness['positions_manifest_sha256']!=first.exact.digest(out/'positions_shards_manifest.json')
            or manifest['rows']!=128 or manifest['lineage']['profile_sha256']!=first.exact.digest(first.BASE/'profile.json')):
        raise ValueError('original exit1 and closed same-profile128 source positions required')
    cached={}
    for shard in manifest['shards']:
        for line in (out/shard['path']).read_text().splitlines():
            r=json.loads(line)
            if r['row_id']in cached:raise ValueError('duplicate native cache row')
            cached[r['row_id']]=r
    if set(cached)!={r['row_id']for r in rows}:raise ValueError('native cache128 row coverage differs')
    mapping=first.exact.read(first.heads.MAP/'teacher_to_student_anchors.json');modes=first.exact.read(first.heads.MAP/'teacher_mapping_modes.json')
    features=[];accepted=Counter();mode_counts=Counter()
    for row in rows:
        r=cached[row['row_id']];pairs=original[row['row_id']]['exact_gold_candidates']
        if (r['prepared_row_sha256']!=first.data.encoder.object_sha(row)or r['original_ce_targets']!=row['ce_targets']
                or len(r['positions'])!=len(pairs)or not r['original_ce_unchanged']or r['partial_token_fallback']
                or not r['native_head']['head_output_matches_qualified_logits_exact']
                or r['native_head']['actual_body_width']!=1024 or r['native_head']['actual_vocab']!=248320
                or r['native_head']['actual_hidden_width']!=1024 or r['native_head']['native_head_calls']!=1
                or r['native_head']['prefix_tokens']!=len(row['teacher']['ids'])-1):
            raise ValueError('original head/CE/prefix source identity changed')
        path=first.FEATURES/(row['row_id']+'.npy')
        if path.is_symlink()or not path.is_file():raise ValueError('original regular feature file required')
        sha=first.exact.digest(path)
        if sha!=r['feature_sha256']or path.stat().st_size>=20_000_000:raise ValueError('closed original feature bytes changed')
        array=np.load(path,allow_pickle=False);recovery.feature_contract(array,tokens=len(row['teacher']['ids'])-1)
        features.append(dict(row_id=row['row_id'],path=str(path.relative_to(ROOT)),sha256=sha,shape=list(array.shape),bytes=path.stat().st_size));del array
        for pair,pos in zip(pairs,r['positions']):
            if any(pos[k]!=v for k,v in pair.items()):raise ValueError('original exact zero-lookahead target changed')
            if recovery.acceptance_contract(pos,mapping,modes):accepted[row['language']]+=1;mode_counts[str(pos['mapping_mode'])]+=1
    if sum(accepted.values())!=538:raise ValueError('closed native acceptance count differs from original actual progress')
    return profile,p,rows,cached,features,dict(accepted),dict(mode_counts)


def prepare():
    first.data.guard()
    if BASE.exists():raise FileExistsError('fresh recovery namespace required')
    profile,p,rows,cached,features,accepted,modes=closed_cache()
    paths=[first.BASE/'profile.json',first.BASE/'ROOT_FINALIZER_FAILURE_v1.json',first.BASE/'teacher/positions_shards_manifest.json']
    manifest=first.exact.read(paths[-1]);paths.extend(first.BASE/'teacher'/s['path']for s in manifest['shards']);paths.extend(ROOT/s for s in SOURCES)
    first.exact.write(BASE/'features_manifest.json',dict(original_namespace=str(first.BASE.relative_to(ROOT)),rows=128,features=features))
    first.exact.write(BASE/'profile.json',dict(tag=TAG,authority_directive=115,deadline=first.data.DEADLINE.isoformat(),
        sources={str(x.relative_to(ROOT)):first.exact.digest(x)for x in paths},features_manifest_sha256=first.exact.digest(BASE/'features_manifest.json'),
        original_exit1_not_relabelled=True,reuse='CLOSED_POSITION_AND_FEATURE_SUBARTIFACT_ONLY',
        original_profile_sha256=first.exact.digest(first.BASE/'profile.json'),canaries=profile['canaries'],
        source_rows=128,exact_candidates=557,accepted_positions=538,accepted_by_language=accepted,accepted_mapping_modes=modes,
        original_ce_targets=772,original_ce_preserved=True,corpus_admitted=False,
        new_gpu_source_rows=4,new_fixed_forward_calls=8,optimizer_updates=0,checkpoint_writes=0,quality_claim=False))
    print('[DSKDV2_CACHE_RECOVERY_PREPARED] '+json.dumps(dict(rows=128,accepted=538,new_gpu_source_rows=4,model_load=False,gpu=False)),flush=True)


def verify():
    first.verify();p=first.exact.read(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=first.data.DEADLINE.isoformat():raise ValueError('recovery authority changed')
    for name,sha in p['sources'].items():
        if first.exact.digest(ROOT/name)!=sha:raise ValueError('sealed recovery reference changed: '+name)
    if first.exact.digest(BASE/'features_manifest.json')!=p['features_manifest_sha256']:raise ValueError('feature manifest changed')
    return p


def run():
    p=verify();_profile,_old,rows,cached,_features,_accepted,_modes=closed_cache();start=time.perf_counter();out=BASE/'actual'
    if out.exists():raise FileExistsError('recovery actual already attempted')
    out.mkdir();torch=lm=trace=None;failure=None
    report=dict(tag=TAG,status='RUNNING',returncode=9,profile_sha256=first.exact.digest(BASE/'profile.json'),
        source_rows_reused=128,accepted_positions=538,accepted_by_language=p['accepted_by_language'],accepted_mapping_modes=p['accepted_mapping_modes'],
        original_ce_targets=772,exact_candidates=557,held_positions=234,corpus_admitted=False,
        original_exit1_not_relabelled=True,training=False,optimizer_updates=0,checkpoint_writes=0,quality_claim=False,checks=[])
    def check():first.data.guard(start,1680)
    try:
        for name,value in first.data.qualified.q.official.OFFLINE.items():os.environ[name]=value
        from scripts.interactive_research_infer import require_idle_gpu
        report['entry_gpu_point']=require_idle_gpu()
        free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
        if not free.isdigit()or int(free)<12288:raise MemoryError('recovery teacher12288MiB free point required')
        import torch
        from torch.nn.attention import sdpa_kernel,SDPBackend
        from scripts import p106b_qwen35_fixedshape as fixed
        from scripts.p106b_dskdv2_native import capture_native
        torch.set_num_threads(4);torch.manual_seed(1337);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        torch.cuda.reset_peak_memory_stats();qp=first.data.qualified.verify();proof=report['model_proof']={};stats=report['fixed_calls']={}
        trace=ShardWriter(out,'calls',limit=3_000_000)
        with first.data.qualified.q.wall_limit(1680),torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
            with first.data.qualified.q.model_runtime(torch,qp['assets'],trace,check,proof,qp['source_identity'])as lm:
                ref=weakref.ref(lm.model)
                for row in rows:
                    if row['row_id']not in p['canaries']:continue
                    check();ids=torch.tensor([row['teacher']['ids'][:-1]],device='cuda',dtype=torch.long)
                    full,features,native=capture_native(lm.model,ids,fixed_call=fixed.logits,width=1024,vocab=248320,hidden_width=1024,pad_id=248044,check=check,stats=stats)
                    trace.append(dict(row_id=row['row_id'],kind='ORIGINAL_CACHE_FULL_SOURCE_REPLAY',native=native))
                    original=torch.from_numpy(np.load(first.FEATURES/(row['row_id']+'.npy'),allow_pickle=False))
                    feature_match=bool(torch.allclose(features,original,atol=1e-5,rtol=1e-4));max_abs=float((features-original).abs().max())
                    if not feature_match:raise ValueError('original cached normalized hidden differs from native replay')
                    for pos in cached[row['row_id']]['positions']:
                        logits=full[0,pos['teacher_predictor_raw_index']]
                        if int(logits.argmax())!=pos['teacher_native_argmax']:raise ValueError('cached original native top1 differs')
                        z=float(torch.logsumexp(logits,dim=-1));expected=pos['teacher_native_logsumexp']
                        if abs(z-expected)>1e-5+1e-4*abs(expected):raise ValueError('cached full-vocabulary normalization differs')
                    for index in p['canaries'][row['row_id']]:
                        short,hidden,short_native=capture_native(lm.model,ids[:,:index+1],fixed_call=fixed.logits,width=1024,vocab=248320,hidden_width=1024,pad_id=248044,check=check,stats=stats)
                        trace.append(dict(row_id=row['row_id'],kind='PREFIX_CAUSAL',predictor=index,native=short_native))
                        match=fixed.compare_prefix(full[:,:index+1],short,atol=1e-5,rtol=1e-4)
                        hclose=bool(torch.allclose(features[:index+1],hidden,atol=1e-5,rtol=1e-4))
                        report['checks'].append(dict(row_id=row['row_id'],predictor=index,cached_hidden_close=feature_match,
                            cached_hidden_max_abs=max_abs,cached_hidden_exact=torch.equal(features,original),prefix_hidden_close=hclose,
                            prefix_hidden_max_abs=float((features[:index+1]-hidden).abs().max()),**match))
                        del short,hidden
                        if not match['close']or not hclose:raise ValueError('recovered exact prefix/future numerical gate failed')
                    del full,features,original,ids,logits
            lm=None;gc.collect();report['owned_model_alive_after_release']=ref()is not None
            if report['owned_model_alive_after_release']:raise RuntimeError('recovery retained teacher model')
        if len(report['checks'])!=4 or stats['serial_batch1_calls']!=8:raise ValueError('only four source/eight fixed forwards required')
        report.update(status='CLOSED_NATIVE128_CACHE_RECOVERED_WITH_FOUR_ACTUAL_CAUSAL_REPLAYS',returncode=0)
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',returncode=9,error=repr(exc));failure=RuntimeError(repr(exc))
    finally:
        lm=None;gc.collect()
        if torch is not None:
            report['peak_allocated_bytes']=torch.cuda.max_memory_allocated();report['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            try:
                from scripts.diag_p107_hybrid_mntp import close_owned_cuda
                close_owned_cuda(torch,report)
            except BaseException as exc:report.update(status='ERROR',returncode=9,cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        manifests,errors=recovery.close_outputs([('calls_manifest',trace)],lineage=dict(tag=TAG,profile_sha256=first.exact.digest(BASE/'profile.json')))
        report.update(manifests)
        if errors:report.update(status='ERROR',returncode=9,finalizer_errors=errors);failure=failure or RuntimeError(repr(errors))
        try:verify();closed_cache();report['sources_features_and_assets_unchanged']=True
        except BaseException as exc:report.update(status='ERROR',returncode=9,source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report.update(seconds=time.perf_counter()-start,full_dskdv2_training_ready=False,projection_agreement_status='NOT_RUN')
        first.exact.write(out/'report.json',report)
    if failure is not None:raise failure
    print('[DSKDV2_RECOVERY_FINAL] '+json.dumps({k:report[k]for k in ['status','seconds','source_rows_reused','accepted_positions']}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','actual']);args=parser.parse_args()
    (prepare if args.phase=='prepare'else run)()


if __name__=='__main__':main()
