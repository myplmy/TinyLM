"""Prepare an explicit small-evidence save; keep all corpus bodies local."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

def git(*args):
    return subprocess.check_output(['git','--literal-pathspecs',*args],cwd=ROOT)

def pin(path):
    return dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path),bytes=path.stat().st_size)

def stable_copy(source,target):
    data=source.read_bytes()
    inv.require(data==source.read_bytes() and len(data)<20_000_000,'unstable or oversized checkpoint evidence')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(data)
    return dict(source=pin(source),archive=pin(target))

archive=AUDIT/'verified_cache_followup_archive_v1'
inv.require(not archive.exists(),'new immutable checkpoint archive required')
copies=[]
for cohort in ('repeat_named_roles_counter_v2','remaining_birth_full_counter_v1'):
    source=inv.BASE/(cohort+'_snapshots')/'v1/complete.json'
    copies.append(stable_copy(source,archive/(cohort+'_snapshot_complete.json')))
    for guide in sorted((inv.BASE/cohort).glob('ROOT_*.md')):
        copies.append(stable_copy(guide,archive/cohort/guide.name))
    for role in ('context_controls','context_hangul','context_latin','historical_review','legacy_review'):
        for guide in sorted((inv.BASE/'agents'/role/cohort).glob('ROOT_*.md')):
            copies.append(stable_copy(guide,archive/cohort/role/guide.name))
for name in ('verified.json','recovery_verified.json','partial_resolution_verified.json','restricted_metadata_verified.json'):
    source=inv.BASE/'cache_reviewed_partial_v2'/name
    copies.append(stable_copy(source,archive/'cache_reviewed_partial_v2'/name))
for name in ('path_error_note_v2.md','path_error_note_v4.md','path_error_note_v5.md','path_error_note_v6.md'):
    source=inv.BASE/'agents/context_latin/repeat_named_roles_counter_v2'/name
    if source.is_file():copies.append(stable_copy(source,archive/'latin_incident_current_versions'/name))
archive_map=AUDIT/'VERIFIED_CACHE_FOLLOWUP_ARCHIVE_V1.json'
with archive_map.open('x',encoding='utf-8') as stream:
    json.dump(dict(status='PINNED_SMALL_EVIDENCE_COPIES_NOT_CORPUS_BODIES',rows=copies,
        original_sources_modified=False,goal_complete=False),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))

metadata=[]
for path in sorted(AUDIT.glob('*.json')):
    if path.stat().st_size>=500_000:
        metadata.append(pin(path))
for cohort in ('repeat_named_roles_counter_v2','remaining_birth_full_counter_v1'):
    snapshot=inv.cache.read(inv.BASE/(cohort+'_snapshots')/'v1/complete.json')
    for shard in snapshot['shards']:metadata.append(pin(ROOT/shard['path']))
local_map=AUDIT/'VERIFIED_CACHE_FOLLOWUP_LARGE_LOCAL_V1.json'
with local_map.open('x',encoding='utf-8') as stream:
    json.dump(dict(status='HASH_INDEX_ONLY_LARGE_AUDITS_AND_REVIEW_DATA_REMAIN_LOCAL',rows=metadata,
        staging_source_bodies=False),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))

head=git('rev-parse','HEAD').decode().strip()
branch=git('branch','--show-current').decode().strip()
inv.require(head=='94e59e8daedd25f90332ee1c284b588f49428cbd','shared HEAD changed; prepare a new reviewed window')
inv.require(not git('diff','--cached','--name-only','-z'),'shared index in use')
relative=str(AUDIT.relative_to(ROOT))
changed=set()
for args in [('ls-files','--others','--exclude-standard','-z','--',relative),
             ('diff','--name-only','-z','--',relative)]:
    changed.update(x.decode() for x in git(*args).split(bytes([0])) if x)
explicit=[]
logs={
 'cache_reviewed_partial_v2_build_v1.log','cache_reviewed_partial_v2_verify_v1.log',
 'cache_reviewed_partial_v2_verify_v2.log','remaining_birth_native_v1.log',
 'repeat_named_roles_counter_v2_snapshot_v1.log','remaining_birth_full_counter_v1_snapshot_v1.log',
 'supplemental_candidates_snapshot_v61_execution_v1.log','supplemental_candidates_snapshot_v62_execution_v1.log',
 'supplemental_candidates_snapshot_v63_execution_v1.log'}
for name in sorted(changed):
    path=ROOT/name
    inv.require(path.is_relative_to(AUDIT) and not path.is_symlink(),'unexpected save namespace')
    if not path.is_file() or not (0<path.stat().st_size<20_000_000):continue
    top=path.parent==AUDIT
    small_top=top and (path.suffix in {'.py','.md'} or (path.suffix=='.json' and path.stat().st_size<500_000)
        or path.name in logs)
    reviewed_archive=path.is_relative_to(AUDIT/'exact_cohort_review_archive_v1') and path.suffix=='.md'
    checkpoint_archive=path.is_relative_to(archive)
    if small_top or reviewed_archive or checkpoint_archive:explicit.append(pin(path))
wip=ROOT/'handoff/WIP_20261027_작업원장.md'
explicit.append(pin(wip))
inv.require(len({r['path'] for r in explicit})==len(explicit),'duplicate allowlist path')
message=AUDIT/'VERIFIED_CACHE_FOLLOWUP_COMMIT_MESSAGE_V1.txt'
body='''데이터: 검증된 정제 캐시와 잔여 구간 판독 근거를 저장한다

새 부분 캐시의 실제 생성과 독립 소비자 검산, 재귀 진입 실패와 수정 근거를 보존한다.
반복732건 및 출생충돌2743건의 별도 수집·정확 TASK 결합·본문 진단과 중재를 기록한다.
주체 소실, 출력 오결합, 경로 오류 및 이전 노트 바이트 보존 미확인을 숨기지 않는다.
원문·대량 캐시는 로컬에 유지하고 작은 감사 근거와 코드·진행 원장만 명시 저장한다.
잔여 HOLD 전체 정제는 계속 진행 중이며 학습 재개·모델 품질·전체 완료를 선언하지 않는다.
'''
with message.open('x',encoding='utf-8') as stream:stream.write(body)
manifest=AUDIT/'VERIFIED_CACHE_FOLLOWUP_SAVE_MANIFEST_V1.json'
with manifest.open('x',encoding='utf-8') as stream:
    json.dump(dict(expected_head=head,branch=branch,rows=explicit,
        excluded_source_data=True,excluded_large_data=True,goal_complete=False),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)),expected_head=head,branch=branch,
    paths=len(explicit)+1,bytes=sum(r['bytes'] for r in explicit)+manifest.stat().st_size,
    kinds=dict(Counter(Path(r['path']).suffix for r in explicit)),archived_evidence=len(copies),
    large_local_hash_rows=len(metadata),index_empty=True),ensure_ascii=False))
