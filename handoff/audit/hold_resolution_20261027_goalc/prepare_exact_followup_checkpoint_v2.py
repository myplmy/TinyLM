"""Freeze only owned small evidence and explicit WIP bytes for a local commit."""
from pathlib import Path
from collections import Counter
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

def copy(source,target):
    data=source.read_bytes()
    inv.require(data==source.read_bytes() and len(data)<20_000_000,'unstable/oversized evidence')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(data)
    return dict(source=pin(source),archive=pin(target))

head=git('rev-parse','HEAD').decode().strip()
branch=git('branch','--show-current').decode().strip()
inv.require(head=='623c2587809e5147b0cc36d3249fbe69d8ecc401','shared HEAD changed')
inv.require(not git('diff','--cached','--name-only','-z'),'shared index in use')
archive=AUDIT/'exact_followup_progress_archive_v2'
inv.require(not archive.exists(),'new immutable archive required')
copies=[]
metadata=[]
for cohort,version in [('repeat_named_roles_counter_v2','v12'),('remaining_birth_full_counter_v1','v12'),('repeat_named_full_independent_v1','v12'),('root10_quantity_recheck_v1','v2'),('remaining_literal_full_counter_v1','v2')]:
    source=inv.BASE/(cohort+'_snapshots')/version/'complete.json'
    copies.append(copy(source,archive/cohort/'snapshot_v12_complete.json'))
    snapshot=inv.cache.read(source)
    for shard in snapshot['shards']:metadata.append(pin(ROOT/shard['path']))
    for guide in sorted((inv.BASE/cohort).glob('ROOT_*.md')):
        copies.append(copy(guide,archive/cohort/guide.name))
    for role in ('context_controls','context_hangul','context_latin','historical_review','legacy_review'):
        for guide in sorted((inv.BASE/'agents'/role/cohort).glob('ROOT_*.md')):
            copies.append(copy(guide,archive/cohort/role/guide.name))
with (AUDIT/'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V2.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(status='IMMUTABLE_SMALL_EVIDENCE_COPIES_NOT_CORPUS_BODIES',rows=copies,
        goal_complete=False,source_data_changed=False),stream,ensure_ascii=False,indent=2);stream.write(chr(10))
for name in ('EXACT_COHORT_BODY_DIAGNOSTICS_V4.json','EXACT_COHORT_BODY_DIAGNOSTICS_V5.json'):
    metadata.append(pin(AUDIT/name))
for name in ('remaining_literal_full_sources_v1/complete.json','remaining_literal_native_proofs_v1/complete.json','remaining_literal_full_counter_v1/manifest.json','root10_quantity_recheck_v1/manifest.json'):
    metadata.append(pin(inv.BASE/name))
prior=AUDIT/'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V1.json'
with (AUDIT/'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V2.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(status='HASH_INDEX_ONLY_ALL_CORPUS_TEXTS_REMAIN_LOCAL',rows=metadata,
        prior_large_index=pin(prior),prior_large_objects_rehashed=False,staging_source_bodies=False),
        stream,ensure_ascii=False,indent=2);stream.write(chr(10))
relative=str(AUDIT.relative_to(ROOT));changed=set()
for args in [('ls-files','--others','--exclude-standard','-z','--',relative),('diff','--name-only','-z','--',relative)]:
    changed.update(x.decode() for x in git(*args).split(bytes([0])) if x)
explicit=[]
for name in sorted(changed):
    path=ROOT/name
    inv.require(path.is_relative_to(AUDIT) and not path.is_symlink(),'unexpected save namespace')
    if not path.is_file() or not 0<path.stat().st_size<20_000_000:continue
    top=path.parent==AUDIT
    small=top and (path.suffix in {'.py','.md'} or path.suffix=='.json' and path.stat().st_size<500_000
        or path.suffix=='.log' and ('_snapshot_v' in path.name or path.name=='NUMERIC_LOCAL_ATOM_TEST_V2.log'))
    reviewed=path.is_relative_to(AUDIT/'exact_cohort_review_archive_v1') and path.suffix=='.md'
    if small or reviewed or path.is_relative_to(archive):explicit.append(pin(path))
explicit.append(pin(ROOT/'handoff/WIP_20261027_작업원장.md'))
inv.require(len({r['path'] for r in explicit})==len(explicit),'duplicate allowlist')
message=AUDIT/'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V2.txt'
body='''데이터: 후속 전량 판독과 원문 복원 검증을 저장한다

반복732의 교차 독립판독과 출생2743의 계속 판독을 실제 저장 근거에 연결한다.
발행처 정의와 일치한 용어집 표제182 복원, 원문 수량26 재판독과 선택 철회를 기록한다.
다음 프로그램 문맥1793의 전량 원문 재생성과 지정 입력을 준비하고 판독을 계속한다.
누락본문·출력열·경로·오판정·시험 실패를 보존하고 정확 수치 원자/단위의 국소 증명을 추가한다.
원문과 캐시는 로컬에 두고 소유 코드·작은 감사 근거·진행 원장만 명시 저장한다.
전체 잔여 HOLD와 새 캐시 반영은 진행 중이며 완료·일시중지·학습 승인을 선언하지 않는다.
'''
with message.open('x',encoding='utf-8') as stream:stream.write(body)
manifest=AUDIT/'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V2.json'
with manifest.open('x',encoding='utf-8') as stream:
    json.dump(dict(expected_head=head,branch=branch,rows=explicit,excluded_source_data=True,
        excluded_large_data=True,goal_complete=False),stream,ensure_ascii=False,indent=2);stream.write(chr(10))
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)),expected_head=head,branch=branch,
    paths=len(explicit)+1,bytes=sum(r['bytes'] for r in explicit)+manifest.stat().st_size,
    kinds=dict(Counter(Path(r['path']).suffix for r in explicit)),archived_evidence=len(copies),
    local_hash_rows=len(metadata),index_empty=True),ensure_ascii=False))
