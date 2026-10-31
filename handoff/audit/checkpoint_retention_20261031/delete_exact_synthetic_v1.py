"""User102's exact 1120-file cleanup. No folder removal, model load or GPU.

prepare freezes identities and preservation hashes. apply requires that exact
manifest SHA and an unchanged tool. A changed/missing target aborts before any
unlink; later races stop immediately with a partial receipt. Historical logs
and reports are never deletion targets.
"""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
REVIEW=HERE/'review_v3.json'
MANIFEST=HERE/'DELETE_MANIFEST_v1.json'
RECEIPT=HERE/'DELETE_RECEIPT_v1.json'
JOURNAL=HERE/'DELETE_JOURNAL_v1.jsonl'
EXPECTED_COUNT=1120
EXPECTED_BYTES=53_100_048_882
TSV=ROOT/'checkpoints.tsv'

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest().upper()

def write_new(path,data):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2)
        stream.write(chr(10))

def safe_path(raw):
    p=PurePosixPath(raw)
    if p.is_absolute() or '..' in p.parts or str(p)!=raw:
        raise ValueError('noncanonical path')
    full=ROOT/Path(raw)
    if any(q.is_symlink() for q in (full,*full.parents)):
        raise ValueError('symlink path: '+raw)
    if full.resolve(strict=True)!=full:
        raise ValueError('path resolution changed: '+raw)
    return full

def identity(path):
    s=path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:
        raise ValueError('not a single-link regular file: '+str(path))
    return dict(dev=s.st_dev,inode=s.st_ino,bytes=s.st_size,
                mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,
                allocated_bytes=s.st_blocks*512,nlink=s.st_nlink)

def same_identity(path,row):
    current=identity(path)
    for k in ('dev','inode','bytes','mtime_ns','ctime_ns'):
        if current[k]!=row[k]:raise ValueError('file identity changed: '+str(path))
    return current

def tsv():
    out={}
    for line in TSV.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):continue
        c=line.split(chr(9))
        if len(c)==4 and c[0] in ('keep','hold','delete'):
            if c[1] in out:raise ValueError('duplicate TSV name')
            out[c[1]]=c[0]
    return out

def root_guard():
    spec=importlib.util.spec_from_file_location('cleanup_readonly',ROOT/'scripts/cleanup_ckpt.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    import re
    out=dict(mod.PROTECTED);out.update(mod.derived_protection())
    for p in (ROOT/'runs/ckpt').glob('*.pt'):
        for pattern,reason in mod.PROTECTED_RE:
            if re.match(pattern,p.name):out.setdefault(p.name,reason)
    return out

def target_paths(review):
    normal=[dict(r,scope='normal_smoke') for r in review['root_candidates']
            if r['candidate_class']=='REGENERABLE_SMOKE']
    isolated=[dict(r,scope='isolated_smoke') for g in review['isolated_smoke_candidates'] for r in g['files']]
    targets=normal+isolated
    if len(normal)!=64 or len(isolated)!=1056 or len(targets)!=EXPECTED_COUNT:
        raise ValueError('exact target count differs')
    if len({r['path'] for r in targets})!=EXPECTED_COUNT or sum(r['bytes'] for r in targets)!=EXPECTED_BYTES:
        raise ValueError('target uniqueness/bytes differ')
    sessions={g['session'] for g in review['isolated_smoke_candidates']}
    for r in targets:
        p=PurePosixPath(r['path'])
        if r['scope']=='normal_smoke':
            if p.parent!=PurePosixPath('runs/ckpt') or not p.name.startswith('tiny_synthetic_') or '_sm_' not in p.name:
                raise ValueError('normal target outside approved synthetic scope')
        else:
            if len(p.parts)!=7 or p.parts[:3]!=('runs','validation','codex_smoke') or p.parts[3] not in sessions or p.parts[4:6]!=('runs','ckpt') or not p.name.startswith('tiny_synthetic_'):
                raise ValueError('isolated target outside exact runtime scope')
        if p.suffix!='.pt':raise ValueError('only checkpoint .pt targets allowed')
    return targets

def open_files(targets):
    known={str(ROOT/r['path']) for r in targets}
    hits=[];denied=[];readable=0
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:fdpaths=list((proc/'fd').iterdir());readable+=1
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:denied.append(proc.name);continue
        for fd in fdpaths:
            try:p=os.readlink(fd)
            except OSError:continue
            if p in known:hits.append(dict(pid=proc.name,fd=fd.name,path=p))
    if hits or denied:raise ValueError('open targets or inaccessible process scopes: '+str(dict(hits=hits,denied=denied)))
    return dict(open_targets=hits,inaccessible_processes=denied,readable_process_scopes=readable)

def filesystem_free():
    values={}
    for label,path in [('wsl',ROOT),('windows_z',Path('/mnt/z'))]:
        try:
            v=os.statvfs(path)
            values[label]=dict(path=str(path),available_bytes=v.f_bavail*v.f_frsize,
                free_bytes=v.f_bfree*v.f_frsize,total_bytes=v.f_blocks*v.f_frsize,
                device=path.stat().st_dev)
        except OSError as exc:values[label]=dict(path=str(path),error=str(exc))
    return values

def preserved_files(review,targets):
    deleted={r['path'] for r in targets}
    originals=[r for r in review['root_metadata'] if r['path'] not in deleted]
    for r in originals:same_identity(safe_path(r['path']),r)
    research=[r for r in review['root_candidates'] if r['candidate_class']=='CLOSED_RESEARCH_BRANCH']
    if len(research)!=9:raise ValueError('expected nine preserved research models')
    model_hashes=[]
    for i,r in enumerate(research,1):
        p=safe_path(r['path']);before=identity(p);h=digest(p);same_identity(p,before)
        model_hashes.append(dict(path=r['path'],sha256=h,**before))
        print(f'[PRESERVE] research {i}/9 hashed',flush=True)
    reports=set()
    for p in (ROOT/'runs/logs').glob('tiny_synthetic_*.json'):reports.add(p)
    for r in research:
        p=ROOT/'runs/logs'/(Path(r['path']).stem+'.json')
        if p.is_file():reports.add(p)
    for g in review['isolated_smoke_candidates']:
        reports.add(ROOT/g['report']);reports.add(ROOT/g['raw_log'])
        logroot=ROOT/f'runs/validation/codex_smoke/{g["session"]}/runs/logs'
        if logroot.is_dir():reports.update(p for p in logroot.rglob('*') if p.is_file())
        evidence=ROOT/Path(g['report']).parent
        reports.update(p for p in evidence.rglob('*') if p.is_file())
    reports.update(p for p in (ROOT/'test_result').glob('*.md') if p.is_file())
    for r in review['source_file_pins']:
        if r['path'].startswith('test_result/') and r['path'].endswith('.md'):reports.add(ROOT/r['path'])
    immutable=[HERE/n for n in ('review_v1.json','review_v2.json','review_v3.json','VALIDATION_v1.json','VALIDATION_v3.json')]
    reports.update(p for p in immutable if p.is_file())
    records=[]
    for p in sorted(reports):
        raw=str(p.relative_to(ROOT));p=safe_path(raw)
        if raw in deleted:raise ValueError('preservation overlaps deletion')
        before=identity(p);h=digest(p);same_identity(p,before)
        records.append(dict(path=raw,sha256=h,**before))
    return originals,model_hashes,records

def prepare():
    review=json.loads(REVIEW.read_text(encoding='utf-8'))
    targets=target_paths(review);table=tsv();guard=root_guard()
    fixed=[]
    for r in targets:
        current=same_identity(safe_path(r['path']),r)
        if r['scope']=='normal_smoke' and (table.get(Path(r['path']).name)!='delete' or Path(r['path']).name in guard):
            raise ValueError('root verdict/lineage guard blocks target')
        fixed.append(dict(path=r['path'],scope=r['scope'],**current))
    research=[r for r in review['root_candidates'] if r['candidate_class']=='CLOSED_RESEARCH_BRANCH']
    if any(table.get(Path(r['path']).name)!='keep' for r in research):raise ValueError('research must be keep')
    proc=open_files(fixed)
    originals,models,reports=preserved_files(review,fixed)
    for r in fixed:same_identity(safe_path(r['path']),r)
    data=dict(schema='TINYLM_USER102_EXACT_SYNTHETIC_DELETE_V1',created_at=now(),
        authority='사용자102: 재생성 가능한 합성1120개 삭제, 종료 연구9개/원로그/판정 유지, 실측과 목록 갱신 및 한국어 로컬커밋',
        review=str(REVIEW.relative_to(ROOT)),review_sha256=digest(REVIEW),tool_sha256=digest(Path(__file__)),
        registry_sha256=digest(TSV),targets=fixed,count=len(fixed),logical_bytes=sum(r['bytes'] for r in fixed),
        allocated_bytes=sum(r['allocated_bytes'] for r in fixed),
        preserved_root_checkpoints=originals,preserved_research_sha256=models,preserved_log_report_sha256=reports,
        preflight_open_files=proc,preflight_filesystem_free=filesystem_free(),
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        foreign_flag_sha256=digest(ROOT/'scripts/flag_whitelist.tsv'),
        model_loads=0,gpu_runs=0,folder_deletion=False)
    write_new(MANIFEST,data)
    print(json.dumps(dict(status='PREFLIGHT_READY',manifest=str(MANIFEST.relative_to(ROOT)),sha256=digest(MANIFEST),
        count=data['count'],logical_bytes=data['logical_bytes'],allocated_bytes=data['allocated_bytes'],
        preserved_root=len(originals),research_sha256=len(models),log_report_sha256=len(reports)),ensure_ascii=False),flush=True)

def apply(expected_sha):
    if not expected_sha or digest(MANIFEST)!=expected_sha.upper():raise ValueError('explicit manifest SHA required')
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if digest(REVIEW)!=m['review_sha256'] or digest(Path(__file__))!=m['tool_sha256'] or digest(TSV)!=m['registry_sha256']:
        raise ValueError('source/registry/review changed')
    if RECEIPT.exists() or JOURNAL.exists():raise ValueError('previous apply evidence exists; no implicit resume')
    expected=target_paths(json.loads(REVIEW.read_text(encoding='utf-8')))
    if {r['path'] for r in m['targets']}!={r['path'] for r in expected} or m['count']!=EXPECTED_COUNT or m['logical_bytes']!=EXPECTED_BYTES:
        raise ValueError('manifest scope differs')
    table=tsv();guard=root_guard()
    for r in m['targets']:
        same_identity(safe_path(r['path']),r)
        if r['scope']=='normal_smoke' and (table.get(Path(r['path']).name)!='delete' or Path(r['path']).name in guard):raise ValueError('new root protection')
    for r in m['preserved_root_checkpoints']:same_identity(safe_path(r['path']),r)
    for r in m['preserved_research_sha256']+m['preserved_log_report_sha256']:
        p=safe_path(r['path']);same_identity(p,r)
        if digest(p)!=r['sha256']:raise ValueError('preserved file changed before apply')
    proc=open_files(m['targets'])
    before=filesystem_free();started=now();removed=[];error=None;after=None
    try:
        with JOURNAL.open('x',encoding='utf-8') as journal:
            for i,r in enumerate(m['targets'],1):
                p=safe_path(r['path']);same_identity(p,r)
                directory=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:
                    s=os.stat(p.name,dir_fd=directory,follow_symlinks=False)
                    if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(r['dev'],r['inode'],r['bytes'],r['mtime_ns'],r['ctime_ns']):raise ValueError('target changed at unlink boundary')
                    os.unlink(p.name,dir_fd=directory)
                finally:os.close(directory)
                removed.append(r)
                journal.write(json.dumps(dict(path=r['path'],logical_bytes=r['bytes'],allocated_bytes=r['allocated_bytes'],deleted_at=now()),ensure_ascii=False)+chr(10));journal.flush()
                if i%200==0 or i==EXPECTED_COUNT:print(f'[DELETE] {i}/{EXPECTED_COUNT}',flush=True)
        after=filesystem_free()
        if any((ROOT/r['path']).exists() for r in m['targets']):raise ValueError('approved target remains')
        names={str(p.relative_to(ROOT)) for p in (ROOT/'runs/ckpt').glob('*.pt')}
        if names!={r['path'] for r in m['preserved_root_checkpoints']}:raise ValueError('unapproved root checkpoint set changed')
        for r in m['preserved_root_checkpoints']:same_identity(safe_path(r['path']),r)
        for r in m['preserved_research_sha256']+m['preserved_log_report_sha256']:
            p=safe_path(r['path']);same_identity(p,r)
            if digest(p)!=r['sha256']:raise ValueError('preserved file changed after apply')
    except BaseException as exc:
        error=type(exc).__name__+': '+str(exc)
        if after is None:after=filesystem_free()
    deltas={k:after[k]['available_bytes']-before[k]['available_bytes'] for k in before if 'available_bytes' in before[k] and 'available_bytes' in after[k]}
    result=dict(schema='TINYLM_USER102_SYNTHETIC_DELETE_RECEIPT_V1',started_at=started,finished_at=now(),
        manifest=str(MANIFEST.relative_to(ROOT)),manifest_sha256=expected_sha.upper(),status='COMPLETE' if error is None else 'PARTIAL_OR_ERROR',error=error,
        approved_count=EXPECTED_COUNT,deleted_count=len(removed),deleted_logical_bytes=sum(r['bytes'] for r in removed),
        deleted_allocated_bytes=sum(r['allocated_bytes'] for r in removed),
        filesystem_before=before,filesystem_after=after,observed_available_delta_bytes=deltas,
        preserved_root_count=len(m['preserved_root_checkpoints']),preserved_research_count=len(m['preserved_research_sha256']),
        preserved_log_report_count=len(m['preserved_log_report_sha256']),preservation_hashes_verified=error is None,
        open_files_at_apply=proc,model_loads=0,gpu_runs=0,folders_removed=0,logs_removed=0,reports_removed=0,research_models_removed=0,
        host_space_note='WSL 내부 available 차이와 Windows Z available 차이를 따로 기록한다. VHDX 축소/fstrim은 실행하지 않았다.')
    write_new(RECEIPT,result)
    print(json.dumps({k:result[k] for k in ['status','error','deleted_count','deleted_logical_bytes','deleted_allocated_bytes','observed_available_delta_bytes','preserved_research_count','preserved_log_report_count']},ensure_ascii=False),flush=True)
    return 0 if error is None else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','apply'])
    p.add_argument('--manifest-sha256')
    a=p.parse_args()
    if a.mode=='prepare':prepare()
    else:raise SystemExit(apply(a.manifest_sha256))
