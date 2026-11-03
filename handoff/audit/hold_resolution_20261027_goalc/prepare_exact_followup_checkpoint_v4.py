"""Save actual cache3 proof and the next full queues using the prior copy guards."""
from pathlib import Path
from collections import Counter
import ast
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

# Reuse only the three verified helper definitions; do not execute the old save.
reuse_path=AUDIT/'prepare_exact_followup_checkpoint_v3.py'
tree=ast.parse(reuse_path.read_text(encoding='utf-8'))
definitions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {'git','pin','copy'}]
assert {node.name for node in definitions}=={'git','pin','copy'}
import subprocess
exec(compile(ast.Module(body=definitions,type_ignores=[]),str(reuse_path),'exec'),globals())
head=git('rev-parse','HEAD').decode().strip()
branch=git('branch','--show-current').decode().strip()
assert head=='a1bc5a4cb59a0865b20ce028e7da742427b7a0bb'
assert not git('diff','--cached','--name-only','-z')
archive=AUDIT/'exact_followup_progress_archive_v4'
assert not archive.exists()
copies=[]
metadata=[]
cohorts=[('repeat_named_roles_counter_v2','v16'),('remaining_birth_full_counter_v1','v17'),
    ('repeat_named_full_independent_v1','v16'),('root10_quantity_recheck_v1','v6'),
    ('remaining_literal_full_counter_v1','v8')]
for cohort,version in cohorts:
    source=inv.BASE/(cohort+'_snapshots')/version/'complete.json'
    copies.append(copy(source,archive/cohort/('snapshot_'+version+'_complete.json')))
    snapshot=inv.cache.read(source)
    for shard in snapshot['shards']:metadata.append(pin(ROOT/shard['path']))
    for guide in sorted((inv.BASE/cohort).glob('ROOT_*.md')):
        copies.append(copy(guide,archive/cohort/guide.name))
    for role in ('context_controls','context_hangul','context_latin','historical_review','legacy_review'):
        for guide in sorted((inv.BASE/'agents'/role/cohort).glob('ROOT_*.md')):
            copies.append(copy(guide,archive/cohort/role/guide.name))
field_path=inv.BASE/'remaining_field_title_readers_v1/complete.json'
field=inv.cache.read(field_path)
for page in field['pages']:
    metadata.append(pin(ROOT/page['path']))
    for role in page['assignments']:
        directory=inv.BASE/'agents'/role/page['group']
        for name in ['START_HERE.md','ROOT_IDENTITY_TASK_001_V1.md']+(['ROOT_SCOPED_INPUT_READER_V1.md'] if role=='context_controls' else []):
            copies.append(copy(directory/name,archive/page['group']/role/name))
for role in ('context_controls','context_hangul','context_latin','historical_review','legacy_review'):
    guide=inv.BASE/'agents'/role/'REMAINING_FIELD_TITLE_QUEUE_V1.md'
    copies.append(copy(guide,archive/'field_queues'/role/guide.name))
inv.write_json(AUDIT/'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V4.json',dict(
    status='IMMUTABLE_SMALL_REVIEW_AND_QUEUE_EVIDENCE_NOT_SOURCE_BODIES',rows=copies,
    goal_complete=False,source_data_changed=False))
for name in ['ROOT_AUTHORED_SELECTIONS_V11.json','ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json',
    'ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1.json','EXACT_COHORT_BODY_DIAGNOSTICS_V6.json',
    'EXACT_SELECTION_RUNTIME_GUARDS_V10.json','IDENTICAL_LITERAL_INPUT_READING_PROOFS_V2.json']:
    metadata.append(pin(AUDIT/name))
for name in ['remaining_unassigned_all_sources_v1/complete.json','remaining_field_title_full_sources_v1/complete.json',
    'remaining_field_title_native_proofs_v1/complete.json','remaining_field_title_readers_v1/complete.json',
    'roster_reviewed_partial_v3/complete.json','cache_reviewed_partial_v3/built.json',
    'cache_reviewed_partial_v3/verified.json','cache_reviewed_partial_v3/recovery_verified.json',
    'cache_reviewed_partial_v3/partial_resolution_verified.json','cache_reviewed_partial_v3/restricted_metadata_verified.json',
    'cache_reviewed_partial_v3/baseline_preservation_scope.json']:
    metadata.append(pin(inv.BASE/name))
inv.write_json(AUDIT/'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V4.json',dict(
    status='HASH_INDEX_ONLY_LARGE_LOCAL_INPUTS_AND_SELECTIONS',rows=metadata,
    prior_large_index=pin(AUDIT/'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V3.json'),
    prior_large_objects_rehashed=False,source_bodies_staged=False,reused_copy_helpers=pin(reuse_path)))
relative=str(AUDIT.relative_to(ROOT))
changed=set()
for args in [('ls-files','--others','--exclude-standard','-z','--',relative),('diff','--name-only','-z','--',relative)]:
    changed.update(value.decode() for value in git(*args).split(bytes([0])) if value)
explicit=[]
for name in sorted(changed):
    path=ROOT/name
    assert path.is_relative_to(AUDIT) and not path.is_symlink()
    if not path.is_file() or not 0<path.stat().st_size<20_000_000:continue
    top=path.parent==AUDIT
    small=top and (path.suffix in {'.py','.md'} or path.suffix=='.json' and path.stat().st_size<500_000
        or path.suffix=='.log' and ('_snapshot_v' in path.name or 'cache_reviewed_partial_v3_' in path.name))
    reviewed=path.is_relative_to(AUDIT/'exact_cohort_review_archive_v1') and path.suffix=='.md'
    if small or reviewed or path.is_relative_to(archive):explicit.append(pin(path))
explicit.append(pin(ROOT/'handoff/WIP_20261027_작업원장.md'))
assert len({row['path'] for row in explicit})==len(explicit)
body=chr(10).join([
    '데이터: 중간 캐시3 실검증과 전량 후속 판독을 저장한다','',
    'cache3 실제 생성0/독립소비자0과 전체 재계측 및 제외 이유를 저장한다.',
    '원래H460695 중 잔여110173위치와 개별검토38/미처리110135를 구분한다.',
    '출생 전량 후속 복구와 ROOT11 검산, literal의 계속 판독 및 실패·정정 이력을 보존한다.',
    '미배정 전체 census와 필드/제목18237의 전량 원문 복원·36페이지 판독 입력 및 제한 reader 검산을 기록한다.',
    '대량 원문·정제TXT·토큰캐시는 로컬에 두고 코드·작은 감사 근거·진행원장만 명시 저장한다.',
    '전체 잔여 정제와 독립 의미 검토·정본 연쇄는 미완이며 완료/일시중지/학습 승인을 선언하지 않는다.',''])
message=AUDIT/'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V4.txt'
with message.open('x',encoding='utf-8') as stream:stream.write(body)
manifest=AUDIT/'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V4.json'
inv.write_json(manifest,dict(expected_head=head,branch=branch,rows=explicit,
    excluded_source_data=True,excluded_large_data=True,goal_complete=False))
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)),expected_head=head,branch=branch,
    paths=len(explicit)+1,bytes=sum(row['bytes'] for row in explicit)+manifest.stat().st_size,
    kinds=dict(Counter(Path(row['path']).suffix for row in explicit)),archived_evidence=len(copies),
    local_hash_rows=len(metadata),index_empty=True),ensure_ascii=False))
