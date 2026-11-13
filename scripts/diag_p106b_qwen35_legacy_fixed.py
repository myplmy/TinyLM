"""Exact original canary after the owned full evaluation; no training or edits."""
import argparse
from datetime import datetime,timezone
import gc
import json
import subprocess
import time
import traceback
import weakref
from pathlib import Path
from scripts import diag_p106b_qwen35_fixedshape as original
from scripts import p106b_qwen35_legacy_fixed as legacy

q=original.q;ROOT=original.ROOT
TAG='p106b_qwen35_legacy_fixed_v1_20261113'
BASE=ROOT/'test_result/evidence'/TAG
SOURCES=('scripts/p106b_qwen35_legacy_fixed.py','scripts/test_p106b_qwen35_legacy_fixed.py',
    'scripts/diag_p106b_qwen35_legacy_fixed.py')


def prepare():
    original.phase_budget('canary');p=original.verify()
    if BASE.exists():raise FileExistsError('fresh legacy confirmation namespace required')
    original.prerequisite('canary',q.digest(original.BASE/'profile.json'))
    BASE.mkdir(parents=True)
    original.write_new(BASE/'profile.json',dict(tag=TAG,authority_directive=115,deadline=original.DEADLINE.isoformat(),
        original_profile_sha256=q.digest(original.BASE/'profile.json'),sources={n:q.digest(ROOT/n) for n in SOURCES},
        original_sources=p['sources'],exact_function='scripts.diag_p106b_qwen35_text_core6.hybrid_canary',
        no_new_prefix_strings=True,width=1024,pad_id=248044,vocab=248320,training=False,checkpoint_writes=0))
    print('[LEGACY_FIXED_PREPARED]',flush=True)


def verify():
    original.verify();p=q.read_json(BASE/'profile.json')
    if p['deadline']!=original.DEADLINE.isoformat() or p['original_profile_sha256']!=q.digest(original.BASE/'profile.json'):
        raise ValueError('qualified fixedshape lineage changed')
    q.verify_pins(p['sources']);q.verify_pins(p['original_sources']);return p


def run():
    cap=min(1200,original.phase_budget('canary'));p=verify();start=time.perf_counter()
    full=original.prerequisite('full',p['original_profile_sha256'])
    if full.get('actual_counts')!=q.official.expected_counts('full') or full.get('actual_rows')!=19965:
        raise ValueError('closed full evaluation must precede this confirmation')
    directory=BASE/'actual'
    if directory.exists():raise FileExistsError('confirmation already attempted')
    directory.mkdir()
    report=dict(tag=TAG,status='RUNNING',returncode=9,profile_sha256=q.digest(BASE/'profile.json'),
        full_report_sha256=q.digest(original.BASE/'full/report.json'),training=False,optimizer_updates=0,
        checkpoint_writes=0,quality_claim=False,started_at=datetime.now(timezone.utc).isoformat())
    lm=writer=ref=torch=None;failure=None;pins={}
    def check():
        if time.perf_counter()-start>cap-120 or (original.DEADLINE-datetime.now(timezone.utc)).total_seconds()<900:
            raise TimeoutError('legacy confirmation time/authority reserve')
    try:
        with q.wall_limit(cap-120):
            import os
            for n,v in q.official.OFFLINE.items():os.environ[n]=v
            from scripts.interactive_research_infer import require_idle_gpu
            report['entry_gpu_point']=require_idle_gpu()
            free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],check=True,
                capture_output=True,text=True,timeout=10).stdout.strip()
            if not free.isdigit() or int(free)<12288:raise MemoryError('12288MiB free point required')
            import torch
            from torch.nn.attention import sdpa_kernel,SDPBackend
            from scripts.p106b_shards import ShardWriter
            torch.set_num_threads(4);torch.manual_seed(1337)
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            torch.cuda.reset_peak_memory_stats();assets=q.read_json(original.BASE/'profile.json')
            writer=ShardWriter(directory,'token_lengths',limit=3_000_000);proof=report['model_proof']={}
            with torch.no_grad(),sdpa_kernel(SDPBackend.MATH):
                with q.model_runtime(torch,assets['assets'],writer,check,proof,assets['source_identity']) as lm:
                    ref=weakref.ref(lm.model)
                    report['exact_legacy_fixed']=legacy.exact_legacy_canary(lm,torch,check=check)
            lm=None;gc.collect();report['owned_model_alive_after_release']=ref()is not None
            if report['owned_model_alive_after_release']:raise RuntimeError('owned model still alive')
            report.update(status='EXACT_LEGACY_FIXED_COMPLETE',returncode=0)
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
        if writer is not None:
            try:
                manifest=writer.close(lineage=dict(tag=TAG,phase='exact_legacy_fixed'))
                q.pin_manifest(directory,'token_lengths',manifest,pins);report['length_manifest']=manifest
            except BaseException as exc:
                report.update(status='ERROR',returncode=9,writer_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try:verify();q.verify_pins(pins);report['sources_assets_unchanged']=True
        except BaseException as exc:
            report.update(status='ERROR',returncode=9,source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        report.update(wall_seconds=time.perf_counter()-start,finished_at=datetime.now(timezone.utc).isoformat())
        original.write_new(directory/'report.json',report)
    if failure is not None:raise failure
    print('[EXACT_LEGACY_FIXED_FINAL] '+json.dumps({k:report[k] for k in ['status','returncode','wall_seconds']}),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','actual']);args=p.parse_args()
    (prepare if args.phase=='prepare' else run)()


if __name__=='__main__':main()
