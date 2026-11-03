"""Save only new semantic/review progress with the already verified copy helpers."""
from pathlib import Path
from collections import Counter
import ast
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
reuse=AUDIT/'prepare_exact_followup_checkpoint_v3.py'
tree=ast.parse(reuse.read_text(encoding='utf-8'))
definitions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {'git','pin','copy'}]
assert {node.name for node in definitions}=={'git','pin','copy'}
exec(compile(ast.Module(body=definitions,type_ignores=[]),str(reuse),'exec'),globals())
head=git('rev-parse','HEAD').decode().strip()
assert head=='9d536a9ea3b4f480eb3cfa64c043c70952115d71'
branch=git('branch','--show-current').decode().strip()
assert not git('diff','--cached','--name-only','-z')
archive=AUDIT/'exact_followup_progress_archive_v6';assert not archive.exists()
copies=[];metadata=[];reused=[]
for group,version in [('remaining_literal_full_counter_v1','v11'),
                       ('remaining_field_title_page_001_counter_v1','v2'),
                       ('remaining_field_title_page_002_counter_v1','v1')]:
    path=inv.BASE/(group+'_snapshots')/version/'complete.json'
    copies.append(copy(path,archive/group/('snapshot_'+version+'_complete.json')))
    for shard in inv.cache.read(path)['shards']:metadata.append(pin(ROOT/shard['path']))
roles=('context_controls','context_hangul','context_latin','historical_review','legacy_review')
cohort='remaining_literal_full_counter_v1'
for role in roles:
    for guide in sorted((inv.BASE/'agents'/role/cohort).glob('ROOT_*.md')):
        previous=AUDIT/'exact_followup_progress_archive_v5'/cohort/role/guide.name
        if previous.is_file() and inv.file_sha(previous)==inv.file_sha(guide):reused.append(pin(previous))
        else:copies.append(copy(guide,archive/cohort/role/guide.name))
    path=inv.BASE/'agents'/role/'ROOT_OTHER_TYPES_PHASE_AUTHORIZATION_V1.md'
    copies.append(copy(path,archive/'phase_authorizations'/role/path.name))
path=inv.BASE/'agents/context_hangul/remaining_field_title_page_001_counter_v1/ROOT_PAGE001_PENDING_AND_NEXT_V1.md'
copies.append(copy(path,archive/'field_resumption/context_hangul'/path.name))
for role in roles:
    for group in ('root11_ordered_corrections_v1','root11_ordered_additional_corrections_v1',
                  'root11_birth_1031233_correction_v1','root11_birth_1052119_correction_v1'):
        directory=inv.BASE/'agents'/role/group
        if not directory.is_dir():continue
        for path in sorted(directory.glob('*.md')):copies.append(copy(path,archive/group/role/path.name))
        for path in sorted(directory.glob('*.txt')):metadata.append(pin(path))
for name in ('ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V4.json',
             'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V1.json','WORKING_COPY_HISTORY_INCIDENT_RECONCILIATION_V1.json',
             'FIELD_HANGUL_PAGE001_EXACT_RESUME_PATHS_V1.json','OTHER_TYPES_PHASE_EXACT_AUTHORIZATION_V1.json'):
    metadata.append(pin(AUDIT/name))
inv.write_json(AUDIT/'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V6.json',{
    'status':'SMALL_NEW_SEMANTIC_AND_REVIEW_PROGRESS_NOT_CORPUS_BODIES','rows':copies,
    'unchanged_prior_guides_reused':reused,'goal_complete':False,'source_data_changed':False})
inv.write_json(AUDIT/'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V6.json',{
    'status':'HASH_INDEX_ONLY_DERIVED_LOCAL_BODIES_AND_REVIEW_SHARDS','rows':metadata,
    'prior_large_index':pin(AUDIT/'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V5.json'),
    'prior_large_objects_rehashed':False,'source_bodies_staged':False,'reused_copy_helpers':pin(reuse)})
relative=str(AUDIT.relative_to(ROOT));changed=set()
for args in [('ls-files','--others','--exclude-standard','-z','--',relative),('diff','--name-only','-z','--',relative)]:
    changed.update(value.decode() for value in git(*args).split(bytes([0])) if value)
explicit=[]
for name in sorted(changed):
    path=ROOT/name;assert path.is_relative_to(AUDIT) and not path.is_symlink()
    if not path.is_file() or not 0<path.stat().st_size<20_000_000:continue
    top=path.parent==AUDIT
    small=top and (path.suffix in {'.py','.md'} or path.suffix=='.json' and path.stat().st_size<500_000)
    reviewed=path.is_relative_to(AUDIT/'exact_cohort_review_archive_v1') and path.suffix=='.md'
    if small or reviewed or path.is_relative_to(archive):explicit.append(pin(path))
explicit.append(pin(ROOT/'handoff/WIP_20261027_작업원장.md'))
assert len({row['path'] for row in explicit})==len(explicit)
message=AUDIT/'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V6.txt'
body=chr(10).join(['데이터: 독립 의미 검토와 잔여 판독 보완을 저장한다','',
    '- literal1793의1546저장/247미저장 및field page1의85저장/427미저장을채택과구분한다.',
    '- 잘못배치한TASK006두행을보존하고정확ID4934/4939의새전문판독/리뷰로연결한다.',
    '- ROOT11의585flag중9원문/본문/전체diff를독립검토해발견한5수정대상과재검토한3수정본을기록한다.',
    '- 남은출생프로필2보완과576flag미판독,출생독립2차전량검토미완을명시한다.',
    '- 개별전문판독HOLD7,원형API/수식/코드줄경계와오삭제복원,파생사본이력의미확인도보존한다.',
    '- 대량본문/캐시는로컬SHA색인만연결하고기존캐시/보호자료/타세션자료를staging하지않는다.',
    '- 전체정제goal은계속active이며부분저장을완료/일시중지/학습승인으로바꾸지않는다.',''])
with message.open('x',encoding='utf-8') as stream:stream.write(body)
manifest=AUDIT/'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V6.json'
inv.write_json(manifest,{'expected_head':head,'branch':branch,'rows':explicit,
    'excluded_source_data':True,'excluded_large_data':True,'goal_complete':False})
print(json.dumps({'manifest':str(manifest.relative_to(ROOT)),'expected_head':head,'branch':branch,
    'paths':len(explicit)+1,'bytes':sum(row['bytes'] for row in explicit)+manifest.stat().st_size,
    'archived_evidence':len(copies),'reused_prior_guides':len(reused),'local_hash_rows':len(metadata),
    'kinds':dict(Counter(Path(row['path']).suffix for row in explicit)),'index_empty':True},ensure_ascii=False))
