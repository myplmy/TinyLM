"""Preserve the first plan and refresh it after the other session's commit."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
assert subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT) == b''
old = json.loads((AUDIT/'BOUNDED_LOCAL_COMMIT_ALLOWLIST_V1.json').read_text(encoding='utf-8'))
for row in old['rows']:
    assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest().upper() == row['sha256'],row['path']
for origin,destination,replacements in [
    ('prepare_bounded_local_commit_v1.py','prepare_bounded_local_commit_v2.py',[
        ('BOUNDED_LOCAL_COMMIT_ALLOWLIST_V1.json','BOUNDED_LOCAL_COMMIT_ALLOWLIST_V2.json'),
        ('_20261101_v1.paths','_20261101_v2.paths'),('_20261101_v1.message','_20261101_v2.message')]),
    ('verify_bounded_commit_index_v1.py','verify_bounded_commit_index_v2.py',[
        ('BOUNDED_LOCAL_COMMIT_ALLOWLIST_V1.json','BOUNDED_LOCAL_COMMIT_ALLOWLIST_V2.json'),
        ('_20261101_v1.paths','_20261101_v2.paths'),('_20261101_post.paths','_20261101_post_v2.paths')]),
    ('finalize_bounded_local_commit_v1.py','finalize_bounded_local_commit_v2.py',[
        ('BOUNDED_LOCAL_COMMIT_ALLOWLIST_V1.json','BOUNDED_LOCAL_COMMIT_ALLOWLIST_V2.json'),
        ('_20261101_post.paths','_20261101_post_v2.paths'),('_20261101_post.message','_20261101_post_v2.message')])
]:
    source = (AUDIT/origin).read_text(encoding='utf-8')
    for before,after in replacements:
        assert source.count(before) == 1,before
        source = source.replace(before,after)
    target = AUDIT/destination
    compile(source,str(target),'exec')
    with target.open('x',encoding='utf-8') as stream:
        stream.write(source)
head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
record = dict(status='SHARED_INDEX_LEFT_UNTOUCHED_AND_OWN_PLAN_REFRESHED',
    failed_coordination_guard=dict(chunk_id='d31f91',exit_code=1,git_writes=0),
    observed_foreign_index=dict(chunk_id='2de794',other_paths=97,our_paths=0,
        foreign_file_contents_opened=False,foreign_pathnames_printed=False),
    observed_empty_after_other_commit=dict(chunk_id='07acc4',index_paths=0,head=head),
    previous_expected_head=old['expected_head'],previous_owned_file_pins_unchanged=len(old['rows']),
    previous_allowlist_preserved=True,foreign_index_modified=False,
    observed_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat())
with (AUDIT/'SHARED_INDEX_COORDINATION_V1.json').open('x',encoding='utf-8') as stream:
    json.dump(record,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(dict(head=head,old_owned_pins_unchanged=len(old['rows']),prepared_new_helpers=3),ensure_ascii=False))
