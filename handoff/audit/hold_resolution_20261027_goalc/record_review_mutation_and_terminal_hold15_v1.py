"""Preserve one review mutation and adjudicate fifteen fully read nameless bios."""
from pathlib import Path
import importlib.util
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

spec=importlib.util.spec_from_file_location('exact_collector',AUDIT/'collect_exact_cohort_reviews_v1.py')
collector=importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
env=collector.load_reused(AUDIT/'collect_supplemental_candidates_v63.py',dict(re=re,inv=inv))
cohort='remaining_birth_full_counter_v1'
directory=inv.BASE/'agents/context_hangul'/cohort
reason=directory/'review_023_v3_change_reason.md'
canonical=directory/'review_023_v3.md'
old=AUDIT/'exact_cohort_review_archive_v1/0C/0CA0ABF452AF45FB677B9EF6946460F0EF1B44CB1C132FF64FD4B2251B7F9CEF.md'
new=AUDIT/'exact_cohort_review_archive_v1/7D/7D69DAF3F13ED7CFA4B8B163E0220177E8233741A6E57153F2C602C6306A63C4.md'
assert inv.file_sha(old)==old.stem and inv.file_sha(new)==new.stem
assert env['review_entries'](reason.read_bytes())==[]
assert any(env['ident'](e['cells'][0])=='expanded_train:1265328' for e in env['review_entries'](canonical.read_bytes()))
aux=dict(path=str(reason.relative_to(ROOT)),sha256=inv.file_sha(reason),
    canonical_review=str(canonical.relative_to(ROOT)),canonical_review_sha256=inv.file_sha(canonical),
    root_approved=True,original_auxiliary_preserved=True,
    reason='Explicit source-free correction explanation; contains no decision rows and must not be ranked as a review.')
with (AUDIT/'EXACT_COHORT_AUXILIARY_REVIEW_DISPOSITIONS_V1.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(rows=[aux],producer_sha256=inv.file_sha(Path(__file__))),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
mutation=dict(path=str((directory/'review_023_v2.md').relative_to(ROOT)),
    prior_archive=dict(path=str(old.relative_to(ROOT)),sha256=inv.file_sha(old)),
    mutated_archive=dict(path=str(new.relative_to(ROOT)),sha256=inv.file_sha(new)),
    restored_decision_review=dict(path=str(canonical.relative_to(ROOT)),sha256=inv.file_sha(canonical)),
    explanation=aux,root_reviewed=True,
    original_path_was_overwritten=True,prior_bytes_preserved_before_overwrite=True,
    prior_bytes_committed_in='bbf07a3864a99bf31b8f24d58d359dcb7fb4ba6b',
    restored_source_id='expanded_train:1265328',
    limits='Current v2 is the altered file, not the original v2. Original bytes survive only in the pinned archive.')
with (AUDIT/'EXACT_COHORT_REVIEW_MUTATIONS_V1.json').open('x',encoding='utf-8') as stream:
    json.dump(dict(rows=[mutation],goal_complete=False),stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))

numbers={'1252268','1252752','1253479','1253528','1253553','1253619','1254916','1255755',
    '1252724','1252930','1253343','1253409','1253545','1254343','1255209'}
manifest_path=inv.BASE/cohort/'manifest.json'
manifest=inv.cache.read(manifest_path)
snapshot_path=inv.BASE/(cohort+'_snapshots')/'v2/complete.json'
snapshot=inv.cache.read(snapshot_path)
saved={}
for shard in snapshot['shards']:
    assert inv.file_sha(ROOT/shard['path'])==shard['sha256']
    saved.update({r['id']:r for r in inv.cache.read(ROOT/shard['path'])})
contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
rows=[]
for source in manifest['rows']:
    if source['id'].rsplit(':',1)[-1] not in numbers:continue
    assert source['id'] not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    review=saved[source['id']]
    assert review['decision']=='NEEDS_ROOT' and not review.get('body') and not review.get('error')
    assert inv.file_sha(ROOT/source['original']['path'])==source['original']['sha256']
    text=(ROOT/source['original']['path']).read_text(encoding='utf-8')
    assert text.lstrip().startswith('(') and len(text)<6000
    rows.append(dict(id=source['id'],source=source['source'],source_ids=source['source_ids'],
        source_ids_sha256=source['source_ids_sha256'],occurrences=source['occurrences'],input_ids=source['input_ids'],
        original=source['original'],candidate=source['candidate'],
        original_character_range=[0,len(text)],original_characters=len(text),
        decision='HOLD',reviewed=True,root_approved=True,
        reason_code='WHOLE_SOURCE_SUBJECT_IDENTITY_LOST_NO_INDEPENDENT_TRAINING_BODY',
        reason='원문 첫 인명과 본문 주체가 소실됐다. 날짜·팀·학교 분류로 이름을 추정할 수 없고 독립적으로 보존할 동일 대상 본문이 없다.',
        specific_limit=('수상명·연도는 있지만 수상 주체가 없어 독립 수상 기록으로 채택할 수 없다.' if source['id'].endswith(':1255755') else '일반 직업·소속 분류는 소실 인명을 대신하지 못한다.'),
        author_first_review=review['review'],author_reason=review['reason'],
        second_review=dict(reviewer='root',method='지정 원문15건을 한 번에 끝까지 표시해 실제 전문을 재판독',
            full_original_read=True,uses_same_detector_as_meaning_proof=False),
        clean_text_path=None,clean_text_sha256=None,cache_admitted=False,
        status='REVIEWED_TERMINAL_HOLD_FOR_THIS_FROZEN_SOURCE_PENDING_NEW_ROSTER_JOIN',
        raw_source_preserved=True,source_identity_invented=False))
assert len(rows)==15
out=AUDIT/'ROOT_REVIEWED_TERMINAL_HOLD15_V1.json'
result=dict(status='FIFTEEN_INDIVIDUAL_WHOLE_SOURCE_REVIEWED_HOLDS_NOT_UNPROCESSED_RENAMING',rows=rows,
    unique_sources=15,source_positions=sum(r['occurrences'] for r in rows),
    raw_input_ids=sum(r['occurrences']*r['input_ids'] for r in rows),
    original_source_manifest=dict(path=str(manifest_path.relative_to(ROOT)),sha256=inv.file_sha(manifest_path)),
    decision_snapshot=dict(path=str(snapshot_path.relative_to(ROOT)),sha256=inv.file_sha(snapshot_path)),
    producer_sha256=inv.file_sha(Path(__file__)),new_roster_joined=False,
    official_verified_cache_hold_positions_unchanged=115526,
    goal_complete=False,training_authorized=False,
    limits='Available frozen source lacks identity; no global claim that recovery is impossible from every external dump. Official unprocessed counts change only after a new verified join.')
with out.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
report=AUDIT/'ROOT_REVIEWED_TERMINAL_HOLD15_V1.md'
lines=['# 주체 소실 원문15건의 검토 완료 HOLD','',
 'Luna의 개별 전문 판독·NEEDS_ROOT 이후 총괄도 원문15건 전체를 실제 읽었다. 소실 인명을 날짜/학교/구단 분류로 추정해 채우거나, 연도만 지운 익명 소개를 학습 본문으로 채택하지 않는다.',
 '15건 각각의 원문·SHA·전체 문자 구간·원래 위치·1차 리뷰·2차 판독·사유는 같은 이름 JSON에 연결한다. 1255755에는 수상명·연도가 있으나 수상 주체가 없다.',
 '현재 고정 원문에서 독립 본문을 구성할 근거가 없다는 개별 판정이다. 다른 덤프나 원문 전체에서 영구히 복원 불가능하다는 주장은 아니다. 원형과 이전 초안은 모두 보존한다.',
 '이는 미처리115526건을 일괄 종결 HOLD로 바꾸는 작업이 아니다. 이15건의 개별 검토 승인도 아직 새 roster/cache에는 미연결이므로 공식 검증 캐시의 잔여 수치115526은 그대로다.',
 '', '| ID | 원문 문자 수 | 원래 위치 수 |', '|---|---:|---:|']
lines += ['| '+r['id']+' | '+str(r['original_characters'])+' | '+str(r['occurrences'])+' |' for r in rows]
with report.open('x',encoding='utf-8') as stream:stream.write(chr(10).join(lines)+chr(10))
print(json.dumps(dict(terminal_hold_unique=15,positions=result['source_positions'],raw_ids=result['raw_input_ids'],
    official_cache_unchanged=True,review_mutations_recorded=1,auxiliary_files=1),ensure_ascii=False))
