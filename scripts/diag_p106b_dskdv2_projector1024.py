"""Reuse the immutable projector-only kernel on closed TRAIN1024 features."""
import argparse
import gc
import json
from pathlib import Path
from types import FunctionType,SimpleNamespace
import numpy as np
from scripts import diag_p106b_dskdv2_projector_warmup as old
from scripts import diag_p106b_dskdv2_calibration1024 as expanded
from scripts.p106b_shards import verify as verify_shards

ROOT=old.ROOT;BASE=ROOT/'test_result/evidence/p106b_dskdv2_projector1024_v1_20261113'
SOURCES=('scripts/diag_p106b_dskdv2_projector1024.py','scripts/test_p106b_dskdv2_projector1024.py')


def closed():
    p,rows=expanded.verify();path=expanded.BASE/'teacher/report.json';r=old.native.exact.read(path)
    root=old.native.exact.read(expanded.BASE/'ROOT_ACTUAL_EXIT_v1.json')
    if r.get('returncode')!=0 or root.get('actual_tool_exit')!=0 or root.get('report_sha256')!=old.native.exact.digest(path):raise ValueError('closed actual native1024 proof required')
    if (r['rows_completed'],r['reused_rows'],r['new_body_calls'],r['new_causal_calls'],r['accepted_positions'])!=(1024,128,896,2,4113):raise ValueError('exact actual native1024 inventory required')
    if r['final_cuda_cleanup']['allocated_bytes']or r['final_cuda_cleanup']['reserved_bytes']or r['owned_teacher_alive_after_release']:raise ValueError('released original teacher required')
    directory=path.parent;verify_shards(directory,r['positions_manifest']);cached={}
    for s in r['positions_manifest']['shards']:
        for line in (directory/s['path']).read_text().splitlines():
            q=json.loads(line)
            if q['row_id']in cached:raise ValueError('duplicate expanded position row')
            cached[q['row_id']]=q
    if set(cached)!={q['row_id']for q in rows}:raise ValueError('all original TRAIN1024 rows required')
    mapping=old.native.exact.read(old.native.heads.MAP/'teacher_to_student_anchors.json');modes=old.native.exact.read(old.native.heads.MAP/'teacher_mapping_modes.json')
    for row in rows:
        q=cached[row['row_id']]
        for key in ['semantic_root_id','source_row_sha256','record_sha256','language']:
            if q[key]!=row[key]:raise ValueError('same original source identity required')
        if q['ce_targets']!=row['ce_targets']or len(q['positions'])!=len(row['exact_gold_candidates']):raise ValueError('original CE/exact counts changed')
        for actual,pair in zip(q['positions'],row['exact_gold_candidates']):
            if any(actual[k]!=v for k,v in pair.items()):raise ValueError('native original exact/zero-lookahead target changed')
            old.native.recovered.recovery.acceptance_contract(actual,mapping,modes)
        path=ROOT/q['feature_path']
        if path.is_symlink()or old.native.exact.digest(path)!=q['feature_sha256']:raise ValueError('same closed feature bytes required')
        h=np.load(path,allow_pickle=False);old.native.recovered.recovery.feature_contract(h,tokens=len(row['teacher']['ids'])-1);del h
    return p,rows,cached


def selected(rows,cached):
    result=[]
    for row in rows:
        positions=[p for p in cached[row['row_id']]['positions']if p['accepted']]
        if positions:result.append((row,positions,np.load(ROOT/cached[row['row_id']]['feature_path'],allow_pickle=False)))
    if sum(len(p)for _,p,_ in result)!=4113:raise ValueError('same full native4113 positions required')
    return result


def build_inner(destination=BASE,selector=selected):
    destination=Path(destination)
    if destination==old.BASE or not destination.is_relative_to(ROOT/'test_result/evidence'):raise ValueError('fresh owned output only')
    proxy=SimpleNamespace(**dict(vars(old.native),selected=selector))
    return FunctionType(old.actual_inner.__code__,dict(old.actual_inner.__globals__,native=proxy,BASE=destination),old.actual_inner.__name__,old.actual_inner.__defaults__)


def prepare():
    if BASE.exists():raise FileExistsError('fresh expanded projector namespace required')
    _p,rows,cached=closed();split=old.split_by_root(rows)
    split['original128_dev']=[r['row_id']for r in rows if r['reuse_original_row_id']and r['row_id']in split['dev']]
    counts={k:sum(sum(p['accepted']for p in cached[r['row_id']]['positions'])for r in rows if r['row_id']in ids)for k,ids in split.items()}
    if counts['train']+counts['dev']!=4113 or counts['original128_dev']!=136:raise ValueError('same old136 held positions must remain held')
    paths=[ROOT/s for s in SOURCES]+[expanded.BASE/'profile.json',expanded.BASE/'teacher/report.json',expanded.BASE/'ROOT_ACTUAL_EXIT_v1.json',
        old.BASE/'profile.json',old.BASE/'report.json',old.BASE/'ROOT_ACTUAL_EXIT_v1.json',ROOT/'scripts/diag_p106b_dskdv2_projector_warmup.py']
    old.native.exact.write(BASE/'profile.json',dict(tag=BASE.name,authority_directive=115,deadline=old.native.data.DEADLINE.isoformat(),
        sources={str(p.relative_to(ROOT)):old.native.exact.digest(p)for p in paths},split=split,positions=counts,updates=100,lr=.001,
        betas=[.9,.999],eps=1e-8,weight_decay=0.,clip_norm=1.,seed=1337,measurements=[0,25,50,75,100],
        early_stopping=False,student_updates=0,checkpoint_writes=0,quality_claim=False,original_kernel_reused=True,
        old_held136_remains_held=True,change='Only calibration source coverage128 to1024; fixed full-batch gradient step exposes more positions.'))
    print('[PROJECTOR1024_PREPARED] '+json.dumps(dict(positions=counts,source_rows=1024,old_held_remains_held=True,model_loads=0,gpu_calls=0)),flush=True)


def verify():
    old.native.data.guard();old.native.verify();p=old.native.exact.read(BASE/'profile.json')
    if p['authority_directive']!=115 or p['deadline']!=old.native.data.DEADLINE.isoformat():raise ValueError('expanded projector authority changed')
    for name,sha in p['sources'].items():
        if old.native.exact.digest(ROOT/name)!=sha:raise ValueError('expanded projector source changed')
    return p


def inputs():
    p,rows,cached=closed();return p,None,rows,cached,None,None,None


def actual():
    proxy=SimpleNamespace(**dict(vars(old.native),inputs=inputs))
    runner=FunctionType(old.actual.__code__,dict(old.actual.__globals__,BASE=BASE,verify=verify,native=proxy,actual_inner=build_inner()),old.actual.__name__,old.actual.__defaults__)
    runner()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','actual']);a=parser.parse_args();(prepare if a.phase=='prepare'else actual)()
