"""Freeze current owned small evidence; never execute an old checkpoint top level."""
from collections import Counter
from pathlib import Path
import ast
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

frozen=AUDIT/'prepare_exact_followup_checkpoint_v3.py'
assert inv.file_sha(frozen)=='8C3557C1B7D1600EB953B6422C4F65A1792BAD3D12B047CC4ED0853023E83801'
nodes=[node for node in ast.parse(frozen.read_text(encoding='utf-8')).body
    if isinstance(node,ast.FunctionDef) and node.name in {'git','pin','copy'}]
assert len(nodes)==3 and all(not node.decorator_list for node in nodes)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(frozen),'exec'),globals())
archive_source=AUDIT/'prepare_exact_followup_checkpoint_v14.py'
assert inv.file_sha(archive_source)=='87494164DA5F3FF5EBF0A5EFDE7608E143D3D6531616555BF4BDD826842FF098'
nodes=[node for node in ast.parse(archive_source.read_text(encoding='utf-8')).body
    if isinstance(node,ast.FunctionDef) and node.name=='archive_one']
assert len(nodes)==1 and not nodes[0].decorator_list
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(archive_source),'exec'),globals())
head=git('rev-parse','HEAD').decode().strip()
assert head=='4c18dd168f532ed781f4746cdbf905ffcdabf7a7'
branch=git('branch','--show-current').decode().strip()
assert branch and not git('diff','--cached','--name-only','-z')
archive=AUDIT/'exact_followup_progress_archive_v18';assert not archive.exists()
copies,reused,metadata=[],[],[]
previous_path=AUDIT/'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V17.json'
previous=inv.cache.read(previous_path);prior_archives={}
for row in previous['rows']+previous.get('unchanged_prior_guides_reused',[]):
    item=row.get('archive',row);prior_archives[item['sha256']]=item
report_path=AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V2.json';report=inv.cache.read(report_path)
assert report['official_verified_HOLD_positions']==109931 and report['ROOT13_new_positions']==867
assert report['fresh_first_review_unique']==5136 and report['still_first_unreviewed_positions']==100874
snapshot_specs=[(row['cohort'],row['version']) for row in report['first_review_freeze']]
snapshot_specs.append(('root12_independent_admission_counter_v1','v5'))
for cohort,version in snapshot_specs:
    path=inv.BASE/(cohort+'_snapshots')/version/'complete.json';value=inv.cache.read(path)
    assert not value['errors'] and value['root_adopted']==value['cache_admitted']==0
    archive_one(path,archive/cohort/('snapshot_'+version+'_complete.json'))
    for item in value['shards']:
        metadata.append(dict(path=item['path'],sha256=item['sha256'],bytes=(ROOT/item['path']).stat().st_size,
            meaning='IMMUTABLE_SOURCE_LINKED_REVIEW_RECORD_METADATA_NOT_CORPUS_TXT'))

group='root12_independent_admission_counter_v1'
manifest_path=inv.BASE/group/'manifest.json';manifest=inv.cache.read(manifest_path)
assert inv.file_sha(manifest_path)=='A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D'
sources={row['id']:row for row in manifest['rows']}
guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json';guard=inv.cache.read(guard_path)
assert inv.file_sha(guard_path)=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V13.json';selection=inv.cache.read(selection_path)
assert inv.file_sha(selection_path)=='FDA9A45F054A0E1689322EBD69D16863E3C1F13FE2DE4FDF0CE9094C35D81AC9'
sidecars=set()
for row in selection['rows']:
    choice=row['selected']
    if choice['cohort']!=group:continue
    source=sources[row['id']]
    assert row['id'] not in guard['restricted_ids'] and row['original_text_sha256'] not in guard['restricted_hashes']
    directory=inv.BASE/'agents'/source['role']/group
    for name in re.findall(r'hold_[A-Za-z0-9_]+[.]md',choice['reason']):
        path=directory/name
        if path.is_file():sidecars.add(path)
for path in sorted(sidecars):
    archive_one(path,archive/'counter_selected_sidecars'/path.parent.parent.name/path.name)
for role in ['context_controls','context_latin']:
    path=inv.BASE/'agents'/role/group/'START_HERE.md'
    archive_one(path,archive/'counter_role_guides'/role/'START_HERE.md')
history_path=AUDIT/'ROOT12_COUNTER_REVIEW013_HISTORY_DISPOSITION_V1.json';history=inv.cache.read(history_path)
for item in history['rows']:
    for key in ['path','canonical_review']:
        path=ROOT/item[key];archive_one(path,archive/'counter_draft_history'/path.name)
for path in {ROOT/item['review'] for item in history['retractions']}:
    archive_one(path,archive/'counter_draft_history'/path.name)
for path in [inv.BASE/group/'ROOT_REVIEW_DRAFT_HISTORY_BOUNDARY_V1.md',
    inv.BASE/group/'ROOT_KNOWN_CONTEXT_FINDINGS_V1.md']:
    archive_one(path,archive/'counter_role_guides'/path.name)
metadata += [pin(path) for path in [frozen,archive_source,previous_path,report_path,manifest_path,
    selection_path,guard_path,ROOT/'tmp/COORD_HOLD_01a17740.md']]
inv.write_json(AUDIT/'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V18.json',dict(
    status='FROZEN_SMALL_METADATA_AND_REVIEWS_NO_TRAINING_TXT',rows=copies,
    unchanged_prior_guides_reused=reused,first_review_unique=5136,
    official_verified_HOLD_positions=109931,ROOT13_cache_pending_positions=867,
    source_data_changed=False,goal_complete=False,training_authorized=False))

relative=str(AUDIT.relative_to(ROOT));changed=set()
for args in [('ls-files','--others','--exclude-standard','-z','--',relative),('diff','--name-only','-z','--',relative)]:
    changed.update(value.decode('utf-8') for value in git(*args).split(bytes([0])) if value)
old_large_path=AUDIT/'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V17.json'
old_large=inv.cache.read(old_large_path);old_large_names={row['path'] for row in old_large['rows']}
for name in sorted(changed):
    path=ROOT/name
    if path.parent==AUDIT and path.suffix=='.json' and path.stat().st_size>=500_000 and name not in old_large_names:
        metadata.append(pin(path))
inv.write_json(AUDIT/'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V18.json',dict(
    status='LOCAL_ONLY_IMMUTABLE_LARGE_METADATA_SHA_INDEX',rows=metadata,
    prior_large_index=pin(old_large_path),prior_large_objects_rehashed=False,
    protected_original_or_candidate_TXT_hashed=False,source_bodies_staged=False))
message=AUDIT/'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V18.txt'
text=chr(10).join(['데이터: HOLD 정체 원인을 정리하고 캐시 242위치 감소를 검증한다','',
    '- 신규 1차 검토 5136고유와 실제 미검토 100874위치를 구분한다.',
    '- ROOT12의 123고유/242위치를 새 캐시에 반영하고 별도 consumer 검증을 기록한다.',
    '- 추가 ROOT13의 436고유/867위치 및 전체 원장 297539행 대조를 저장한다.',
    '- 보호 8ID/9SHA/13부모 alias와 독립 대조·조기 리뷰 철회 이력을 보존한다.',
    '- 원형·대량 본문/캐시·타세션 변경·GPU/모델·push/PR은 제외한다.',
    '- 중간 저장 뒤 전량 정제는 계속하며 완료·일시중지·학습 승인으로 바꾸지 않는다.',''])
with message.open('x',encoding='utf-8') as stream:stream.write(text)
changed.update(str(path.relative_to(ROOT)) for path in [
    AUDIT/'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V18.json',message])
explicit=[]
for name in sorted(changed):
    path=ROOT/name
    assert path.resolve().is_relative_to(AUDIT) and not path.is_symlink()
    if not path.is_file() or not 0<path.stat().st_size<20_000_000:continue
    top_small=path.parent==AUDIT and (path.suffix in {'.py','.md'} or
        path.suffix in {'.json','.log'} and path.stat().st_size<500_000)
    exact_closure=path==AUDIT/'ROOT13_COUNTER_BATCH002_CLOSURE_V1.json'
    reviewed=path.is_relative_to(AUDIT/'exact_cohort_review_archive_v1') and path.suffix=='.md'
    if top_small or exact_closure or reviewed or path.is_relative_to(archive) or path==message:explicit.append(pin(path))
# The official WIP CAS/readback already pinned its bytes; do not reread text here.
wip='handoff/WIP_20261027_작업원장.md'
explicit.append(dict(path=wip,sha256='F7951F3192F888636F3168453A8AA2D9BB52043F028F08EBD8D3B93FE536F42E',bytes=(ROOT/wip).stat().st_size))
assert len(explicit)==len({row['path'] for row in explicit})
excluded=inv.cache.read(ROOT/'.agents/project.json')['excludedPaths']
for row in explicit:
    assert all(not row['path'].startswith(value) for value in excluded if not value.startswith('.env'))
manifest=AUDIT/'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V18.json'
inv.write_json(manifest,dict(expected_head=head,branch=branch,rows=explicit,
    excluded_source_data=True,excluded_large_data=True,foreign_dirty_paths_excluded=True,
    goal_complete=False,training_authorized=False))
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)),expected_head=head,branch=branch,
    paths=len(explicit)+1,bytes=sum(row['bytes'] for row in explicit)+manifest.stat().st_size,
    archived_evidence=len(copies),reused_evidence=len(reused),local_hash_rows=len(metadata),
    kinds=dict(Counter(Path(row['path']).suffix for row in explicit)),index_empty=True),ensure_ascii=False))
