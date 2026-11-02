"""Archive exact owned review MDs and prepare a selective immutable local save."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

groups=['root_join_conflict_counter_v1','repeat_local_context_counter_v1','nominal_local_alias_counter_v1',
        'post_body_guard_counter_v1','semantic_field_counter_v1','post_semantic_independent_v1','runtime_guard_counter_v1']
restricted={'expanded_train:'+str(n) for n in [14760,756966,15695,1216576,1250821,20624,6030]}
archive=AUDIT/'resume_active_scope_review_archive_v1'
archive.mkdir(exist_ok=True)
review_records=[]
for group in groups:
    manifest=inv.cache.read(inv.BASE/group/'manifest.json')
    inv.require(not ({row['id'] for row in manifest['rows']}&restricted),'current review scope includes a restricted full parent')
    for role in manifest['assignments']:
        directory=inv.BASE/'agents'/role/group
        for source in sorted(directory.glob('*.md')):
            inv.require(not source.is_symlink() and source.resolve().parent==directory.resolve(),'owned review path escapes')
            payload=source.read_bytes()
            inv.require(payload==source.read_bytes() and len(payload)<20_000_000,'review changed or needs splitting')
            digest=hashlib.sha256(payload).hexdigest().upper()
            target=archive/digest[:2]/(digest+'.md')
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                inv.require(target.read_bytes()==payload,'review archive differs')
            else:
                with target.open('xb') as stream:
                    stream.write(payload)
            review_records.append(dict(path=str(source.relative_to(ROOT)),sha256=digest,bytes=len(payload),
                                       archive=str(target.relative_to(ROOT))))
archive_receipt=AUDIT/'RESUME_ACTIVE_SCOPE_REVIEW_ARCHIVE_V1.json'
inv.require(not archive_receipt.exists(),'new immutable archive receipt required')
inv.write_json(archive_receipt,dict(status='EXACT_OWNED_REVIEW_MD_ARCHIVES_PRESERVED',rows=review_records,
    sources=len(review_records),unique_archives=len({row['archive'] for row in review_records}),
    raw_training_txt_staged=False,restricted_parent_bodies_opened=False,goal_complete=False,training_authorized=False))
scripts=['scripts/p106b_hold_resolution_repeat_context_v1.py','scripts/test_p106b_hold_resolution_repeat_context_v1.py']
scope_paths=[str(AUDIT.relative_to(ROOT)),'handoff/WIP_20261027_작업원장.md',*scripts]
raw=subprocess.check_output(['git','--literal-pathspecs','status','--porcelain','-z','--untracked-files=all','--',*scope_paths],cwd=ROOT)
records=[]
omitted=[]
for entry in raw.split(bytes([0])):
    if not entry:
        continue
    name=entry[3:].decode('utf-8')
    path=ROOT/name
    inv.require(path.is_file() and not path.is_symlink(),'checkpoint only owns regular current files')
    size=path.stat().st_size
    parent=path.parent==AUDIT
    selected=(name in scripts or name=='handoff/WIP_20261027_작업원장.md' or
              path.resolve().is_relative_to(archive) or
              (parent and path.suffix in {'.py','.md'}) or
              (parent and path.suffix=='.json' and size<=250_000) or
              (parent and path.name.startswith('resume_active_scope_cpu_check_v1_') and path.suffix=='.log'))
    if selected:
        inv.require(0<size<20_000_000,'selected audit file is empty or oversized')
        records.append(dict(path=name,sha256=inv.file_sha(path),bytes=size))
    elif parent and path.suffix=='.json':
        omitted.append(dict(path=name,sha256=inv.file_sha(path),bytes=size,
                            disposition='LARGE_AUDIT_LOCAL_ONLY_NOT_STAGED'))
large_receipt=AUDIT/'RESUME_ACTIVE_SCOPE_LARGE_LOCAL_AUDITS_V1.json'
inv.write_json(large_receipt,dict(status='LARGE_AUDIT_ARTIFACTS_PRESERVED_LOCALLY_WITH_SHA',rows=omitted,
    excluded_from_git=True,training_authorized=False,goal_complete=False))
records.append(dict(path=str(large_receipt.relative_to(ROOT)),sha256=inv.file_sha(large_receipt),bytes=large_receipt.stat().st_size))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT).decode().strip()
inv.require(subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=ROOT)==b'','shared index is in use')
manifest=AUDIT/'RESUME_ACTIVE_SCOPE_SAVE_MANIFEST_V1.json'
inv.require(not manifest.exists(),'new immutable save manifest required')
inv.write_json(manifest,dict(expected_head=head,branch=branch,rows=sorted(records,key=lambda row:row['path']),
    source_file_count=len(records),bytes=sum(row['bytes'] for row in records),
    large_audits_local_only=len(omitted),archive_receipt=str(archive_receipt.relative_to(ROOT)),
    exact_current_goal_scope=True,goal_complete=False,training_authorized=False))
message=AUDIT/'RESUME_ACTIVE_SCOPE_COMMIT_MESSAGE_V1.txt'
with message.open('x',encoding='utf-8') as stream:
    stream.write('데이터: 잔여 HOLD 전량 연결과 독립 판독 보완을 저장한다'+chr(10)*2+
        '- 원문별4381개 정확 선택과 독립49 판독의 추가수정·실패·미선택 근거를 보존한다.'+chr(10)+
        '- 보호7/동일SHA11위치 본문 미디코딩과 정확쌍/코드 검산 및 관련 CPU 도구를 저장한다.'+chr(10)+
        '- 전량297539고유/460695위치 로스터의115526미결과 새 부분캐시 생성중 상태를 구분한다.'+chr(10)+
        '- 대량 원문·캐시·큰 감사결과는 로컬 SHA목록에 보존하며 전체goal은 계속 진행한다.'+chr(10))
print(json.dumps(dict(status='EXACT_SELECTIVE_LOCAL_CHECKPOINT_PREPARED',paths=len(records)+1,
    bytes=sum(row['bytes'] for row in records),review_mds=len(review_records),
    large_audits_local_only=len(omitted),head=head,branch=branch),ensure_ascii=False))
