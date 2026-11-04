"""Independently hash every committed blob and the exact frozen working files."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import subprocess
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--version',required=True);args=parser.parse_args()
assert args.version.isdigit() and 1<=int(args.version)<=9999
prefix='EXACT_FOLLOWUP_PROGRESS_';suffix='_V'+args.version+'.json'
manifest_path=AUDIT/(prefix+'SAVE_MANIFEST'+suffix)
receipt_path=AUDIT/(prefix+'LOCAL_COMMIT'+suffix)
out=AUDIT/(prefix+'LOCAL_COMMIT_V'+args.version+'_INDEPENDENT_VERIFIED.json')
assert not out.exists()
manifest=json.loads(manifest_path.read_bytes());receipt=json.loads(receipt_path.read_bytes())
assert receipt['status']=='ACTUAL_LOCAL_COMMIT_WHOLE_MEMBERSHIP_AND_BYTES_VERIFIED'
commit=receipt['commit'];expected={r['path']:r for r in manifest['rows']}
relative=str(manifest_path.relative_to(ROOT));raw=manifest_path.read_bytes()
expected[relative]=dict(path=relative,sha256=hashlib.sha256(raw).hexdigest().upper(),bytes=len(raw))
assert len(expected)==len(manifest['rows'])+1


def git(*values,data=None):
    return subprocess.check_output(['git','--literal-pathspecs',*values],input=data,cwd=ROOT)


actual={value.decode('utf-8') for value in git('diff-tree','--no-commit-id','--name-only','-z','-r',commit).split(bytes([0])) if value}
assert actual==set(expected)
assert git('show','-s','--format=%P',commit).decode().strip()==manifest['expected_head']==receipt['parent']
assert git('rev-parse','HEAD').decode().strip()==commit
ordered=sorted(expected)
batch=io.BytesIO(git('cat-file','--batch',data=(''.join(commit+':'+p+chr(10) for p in ordered)).encode('utf-8')))
total=0
for name in ordered:
    row=expected[name];path=ROOT/name
    assert name=='handoff/WIP_20261027_작업원장.md' or path.resolve().is_relative_to(AUDIT)
    header=batch.readline().split();assert len(header)==3 and header[1]==b'blob'
    size=int(header[2]);assert size==row['bytes'] and size<20_000_000
    payload=batch.read(size);assert batch.read(1)==bytes([10])
    assert hashlib.sha256(payload).hexdigest().upper()==row['sha256']
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper()==row['sha256']
    total+=size
assert not batch.read() and not git('diff','--name-only',commit,'--',*ordered)
assert not git('diff','--cached','--name-only','-z')
value=dict(status='INDEPENDENT_WHOLE_COMMIT_MEMBERSHIP_AND_EVERY_BLOB_VERIFIED',commit=commit,
    parent=receipt['parent'],paths=len(ordered),bytes=total,all_blob_SHA256_match=True,
    all_working_SHA256_match=True,own_saved_scope_dirty=0,index_count=0,
    manifest_sha256=hashlib.sha256(raw).hexdigest().upper(),
    title=git('show','-s','--format=%s',commit).decode('utf-8').strip(),
    verified_at=datetime.now(timezone.utc).isoformat(),foreign_tracked_dirty_paths_excluded=True,
    goal_complete=False,training_authorized=False)
with out.open('x',encoding='utf-8') as stream:
    json.dump(value,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
print(json.dumps({k:value[k] for k in ['status','commit','paths','bytes','own_saved_scope_dirty','index_count']},ensure_ascii=False))
