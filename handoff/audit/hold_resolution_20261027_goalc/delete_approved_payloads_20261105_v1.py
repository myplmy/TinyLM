"""Remove only the user's approved 46 payload trees using exact inode manifests."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import stat
import subprocess

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
STEM='APPROVED_PAYLOAD_CLEANUP_20261105_V1'
MANIFEST=AUDIT/(STEM+'_MANIFEST.json')
RESULT=AUDIT/(STEM+'_RESULT.json')
STARTED=AUDIT/(STEM+'_STARTED.json')
JOURNAL=AUDIT/(STEM+'_EVENTS.jsonl')
TARGETS=tuple([f'{name}/{child}' for name in ['cache_partial_v1']+
    [f'cache_reviewed_partial_v{i}' for i in range(2,11)] for child in ['tokens','text']]+
    [f'cache_reviewed_partial_v{i}/{child}' for i in [12,14] for child in ['tokens','text','ledger','hold']]+
    [f'guarded_partial_proposals_v{i}/ledger' for i in list(range(2,18))+[19,20]])
EXPECTED_FILES=5177
EXPECTED_ALLOCATED_BYTES=101526917120
FLAGS=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC


def require(value,message):
    if not value:raise ValueError(message)


def utc():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_new(path,value):
    payload=(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    require(len(payload)<20_000_000,'audit file exceeds size contract')
    with path.open('xb') as stream:
        stream.write(payload);stream.flush();os.fsync(stream.fileno())


def allowed(path,targets=TARGETS):
    p=PurePosixPath(path)
    require(not p.is_absolute() and '..' not in p.parts and str(p)==path,'noncanonical relative path')
    require(any(path==root or path.startswith(root+'/') for root in targets),'path outside approved payload trees')
    return p


def metadata(s):
    return {key:getattr(s,'st_'+key) for key in ['dev','ino','mode','nlink','size','mtime_ns','blocks']}


def collect(base,targets=TARGETS):
    require(not base.is_symlink() and base.resolve()==base,'base has a symlink')
    require(set(targets)<=set(TARGETS),'unapproved target root')
    device=base.stat().st_dev;files=[];directories=[];seen=set()
    for root in targets:
        allowed(root)
        target=base/root
        require(target.is_dir() and not target.is_symlink(),'target is absent or a symlink')
        for folder,children,names in os.walk(target,followlinks=False):
            children.sort();names.sort();path=Path(folder);s=path.lstat()
            require(stat.S_ISDIR(s.st_mode) and s.st_dev==device,'target directory changed filesystem or type')
            directories.append(dict(path=str(path.relative_to(base)),metadata=metadata(s)))
            for name in children:
                require(not (path/name).is_symlink(),'symlink directory denied')
            for name in names:
                path2=path/name;s=path2.lstat();rel=str(path2.relative_to(base));allowed(rel)
                require(stat.S_ISREG(s.st_mode) and s.st_dev==device and s.st_nlink==1,
                        'nonregular, cross-filesystem or linked payload denied')
                require((s.st_dev,s.st_ino) not in seen,'payload inode is shared')
                seen.add((s.st_dev,s.st_ino));files.append(dict(path=rel,metadata=metadata(s)))
    return files,directories


def retained_snapshot(base,targets=TARGETS):
    digest=hashlib.sha256();count=0
    for folder,children,names in os.walk(base,followlinks=False):
        children[:]=sorted(name for name in children if str((Path(folder)/name).relative_to(base)) not in targets)
        links=[name for name in children if (Path(folder)/name).is_symlink()]
        children[:]=[name for name in children if name not in links]
        names=list(names)+links
        for name in sorted(names):
            p=Path(folder)/name;rel=str(p.relative_to(base));s=p.lstat()
            require(not any(rel==root or rel.startswith(root+'/') for root in targets),'target entered retained snapshot')
            item=dict(path=rel,metadata=metadata(s))
            if stat.S_ISLNK(s.st_mode):item['link']=os.readlink(p)
            digest.update((json.dumps(item,sort_keys=True,separators=(',',':'))+'\n').encode());count+=1
    return dict(files=count,metadata_sha256=digest.hexdigest().upper(),payload_bodies_read=0)


def check_references():
    seeds=[AUDIT/'ROOT_AUTHORED_SELECTIONS_V28.json',AUDIT/'ROOT28_ROSTER_V20_INDEPENDENT_VERIFIED_V1.json',
        AUDIT/'CACHE14_ROOT28_ROSTER20_CONFIG_V1.json',BASE/'cache_reviewed_partial_v11/built.json',
        BASE/'cache_reviewed_partial_v14/started.json',BASE/'roster_reviewed_partial_v20/complete.json',
        BASE/'guarded_partial_proposals_opaque_root28_roster20_v1/complete.json']
    def strings(value):
        if isinstance(value,dict):
            for key,child in value.items():yield key;yield from strings(child)
        elif isinstance(value,list):
            for child in value:yield from strings(child)
        elif isinstance(value,str):yield value
    prefix=str(BASE.relative_to(ROOT))+'/'
    for path in seeds:
        for value in strings(json.loads(path.read_bytes())):
            for target in TARGETS:
                require(prefix+target+'/' not in value and value not in {prefix+target,str(BASE/target)},
                        'current input directly references an approved target')
    return {str(path.relative_to(ROOT)):sha(path) for path in seeds}


def check_holders(files):
    for start in range(0,len(files),200):
        result=subprocess.run(['/usr/bin/fuser',*[str(BASE/row['path']) for row in files[start:start+200]]],
                              capture_output=True,text=True)
        require(result.returncode==1 and not result.stdout.strip() and not result.stderr.strip(),
                'payload is open or scoped holder query failed')


def open_directory(base_fd,relative):
    fd=os.dup(base_fd)
    try:
        for component in PurePosixPath(relative).parts:
            require(component not in {'..','/',''},'invalid directory component')
            child=os.open(component,FLAGS,dir_fd=fd);os.close(fd);fd=child
        return fd
    except BaseException:
        os.close(fd);raise


def unlink_one(base_fd,row,dir_records):
    path=allowed(row['path']);parent=str(path.parent)
    require(parent in dir_records,'file parent was not manifested')
    fd=open_directory(base_fd,parent)
    try:
        s=os.fstat(fd);expected=dir_records[parent]['metadata']
        require((s.st_dev,s.st_ino)==(expected['dev'],expected['ino']),'file parent inode changed')
        require(metadata(os.stat(path.name,dir_fd=fd,follow_symlinks=False))==row['metadata'],'payload changed before unlink')
        os.unlink(path.name,dir_fd=fd)
    finally:os.close(fd)


def prepare():
    require(not MANIFEST.exists(),'immutable cleanup manifest already exists')
    files,dirs=collect(BASE)
    require(len(TARGETS)==46 and len(files)==EXPECTED_FILES,'approved file or root count changed')
    allocated=sum(row['metadata']['blocks']*512 for row in files+dirs)
    require(allocated==EXPECTED_ALLOCATED_BYTES,'approved allocated-byte count changed')
    refs=check_references();keep=retained_snapshot(BASE)
    value=dict(status='EXACT_USER_APPROVED_PAYLOAD_REMOVAL_MANIFEST',utc=utc(),
        approval='현재 사용자: 삭제 가능한 생성물 삭제; 직전46폴더/5177파일/101.53GB표의 범위',
        base=str(BASE),targets=list(TARGETS),files=files,directories=dirs,allocated_bytes=allocated,
        retained_files=keep,current_metadata_pins=refs,source_sha256=sha(Path(__file__)),
        raw_original_or_candidate_payload_reads=0,goal_complete=False,training_authorized=False)
    write_new(MANIFEST,value)
    print(json.dumps(dict(status=value['status'],files=len(files),target_roots=len(TARGETS),allocated_bytes=allocated,
        retained_files=keep['files'],manifest_sha256=sha(MANIFEST))),flush=True)


def delete(expected_sha):
    require(sha(MANIFEST)==expected_sha,'manifest SHA changed')
    plan=json.loads(MANIFEST.read_bytes())
    require(plan['base']==str(BASE) and tuple(plan['targets'])==TARGETS,'manifest authorization scope differs')
    require(sha(Path(__file__))==plan['source_sha256'],'cleanup code changed after manifest')
    require(not any(path.exists() for path in [STARTED,JOURNAL,RESULT]),'cleanup already started; inspect journal instead of rerun')
    files,dirs=collect(BASE)
    require(files==plan['files'] and dirs==plan['directories'],'candidate inode manifest changed')
    require(check_references()==plan['current_metadata_pins'],'current input metadata changed')
    require(retained_snapshot(BASE)==plan['retained_files'],'retained files changed before deletion')
    check_holders(files)
    write_new(STARTED,dict(status='ACTUAL_EXACT_PAYLOAD_REMOVAL_STARTED',utc=utc(),manifest_sha256=expected_sha,
        files=len(files),allocated_bytes=plan['allocated_bytes'],scoped_open_handle_queries_clear=True))
    removed=0;removed_dirs=0;error=None;base_fd=os.open(BASE,FLAGS)
    directory_map={row['path']:row for row in dirs}
    try:
        with JOURNAL.open('x',encoding='utf-8',buffering=1) as stream:
            for index,row in enumerate(files):
                stream.write(json.dumps(dict(intent_file=index))+'\n')
                unlink_one(base_fd,row,directory_map);removed+=1
                stream.write(json.dumps(dict(removed_file=index))+'\n')
                if removed%500==0:
                    stream.flush();os.fsync(stream.fileno());print(json.dumps(dict(removed_files=removed)),flush=True)
            for row in sorted(dirs,key=lambda row:(len(PurePosixPath(row['path']).parts),row['path']),reverse=True):
                p=allowed(row['path']);fd=open_directory(base_fd,str(p.parent))
                try:
                    s=os.stat(p.name,dir_fd=fd,follow_symlinks=False);expected=row['metadata']
                    require(stat.S_ISDIR(s.st_mode) and (s.st_dev,s.st_ino)==(expected['dev'],expected['ino']),
                            'directory identity changed before empty removal')
                    os.rmdir(p.name,dir_fd=fd);removed_dirs+=1
                finally:os.close(fd)
            stream.flush();os.fsync(stream.fileno())
    except BaseException as exc:error=repr(exc)
    finally:os.close(base_fd)
    after=retained_snapshot(BASE);absent=[not (BASE/path).exists() for path in TARGETS]
    success=error is None and removed==len(files) and all(absent) and after==plan['retained_files']
    value=dict(status='EXACT_APPROVED_PAYLOADS_REMOVED_RETAINED_METADATA_UNCHANGED' if success else
        'PARTIAL_OR_FAILED_REMOVAL_INSPECT_EXACT_JOURNAL',utc=utc(),removed_files=removed,
        removed_directories=removed_dirs,approved_target_roots=len(TARGETS),all_target_roots_absent=all(absent),
        retired_allocated_bytes=plan['allocated_bytes'] if success else None,
        retained_metadata_before=plan['retained_files'],retained_metadata_after=after,
        all_other_BASE_file_metadata_unchanged=after==plan['retained_files'],error=error,
        manifest=dict(path=str(MANIFEST.relative_to(ROOT)),sha256=expected_sha),
        journal=dict(path=str(JOURNAL.relative_to(ROOT)),sha256=sha(JOURNAL)),
        original_payload_bodies_read_or_hashed=0,latest_official_cache='cache_reviewed_partial_v11',
        historical_removed_payloads_require_regeneration_for_replay=True,
        goal_complete=False,training_authorized=False)
    write_new(RESULT,value)
    print(json.dumps({key:value[key] for key in ['status','removed_files','removed_directories',
        'retired_allocated_bytes','all_other_BASE_file_metadata_unchanged','error']}),flush=True)
    require(success,'deletion incomplete; do not rerun blindly')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['prepare','delete'])
    parser.add_argument('--expected-manifest-sha');args=parser.parse_args()
    if args.phase=='prepare':prepare()
    else:require(bool(args.expected_manifest_sha),'exact manifest SHA is required');delete(args.expected_manifest_sha)


if __name__=='__main__':main()
