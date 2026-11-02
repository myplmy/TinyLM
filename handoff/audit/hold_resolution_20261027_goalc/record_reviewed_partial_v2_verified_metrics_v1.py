"""Record observed cache verification and comparable metrics without closing HOLDs."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
OUT = AUDIT / 'REVIEWED_PARTIAL_V2_VERIFIED_METRICS_V1.json'
REPORT = AUDIT / 'HOLD_STATUS_AND_EXCLUSION_RATIONALE_20261103_V1.md'
assert not OUT.exists() and not REPORT.exists()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def pin(path):
    return dict(path=str(path.relative_to(ROOT)),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper())


def total(by_split):
    value = Counter()
    for part in by_split.values():
        value.update(part)
    return dict(value)


new_dir = BASE / 'cache_reviewed_partial_v2'
old_dir = BASE / 'cache_partial_v1'
new = read(new_dir / 'built.json')
old = read(old_dir / 'built.json')
old_partial = read(old_dir / 'partial_resolution_verified.json')
build_path = AUDIT / 'CACHE_REVIEWED_PARTIAL_V2_PROCESS_EXIT_V1.json'
verify_path = AUDIT / 'CACHE_REVIEWED_PARTIAL_V2_VERIFY_EXIT_V2.json'
failed_path = AUDIT / 'CACHE_REVIEWED_PARTIAL_V2_VERIFY_EXIT_V1.json'
build, verify, failed = map(read, [build_path, verify_path, failed_path])
assert build['process_exit_code'] == verify['process_exit_code'] == 0
assert failed['process_exit_code'] != 0 and failed['proofs'] == {}
assert build['observation_method'] == verify['observation_method'] == 'ACTUAL_SUBPROCESS_WAIT_RETURN_CODE'
assert build['built_receipt'] == pin(new_dir / 'built.json')
proofs = {}
for name in ['verified.json', 'recovery_verified.json', 'partial_resolution_verified.json',
             'restricted_metadata_verified.json']:
    path = new_dir / name
    assert verify['proofs'][name] == pin(path)
    proofs[name] = read(path)
core, recovery, partial, restricted = [proofs[name] for name in proofs]
assert recovery['built_sha256'] == pin(new_dir / 'built.json')['sha256']
assert recovery['core_verified_sha256'] == pin(new_dir / 'verified.json')['sha256']
assert partial['core_recovery_verified_sha256'] == pin(new_dir / 'recovery_verified.json')['sha256']
assert core['every_adopted_document_regenerated'] is True
assert core['exact_train_val_text_overlap'] == 0 and core['files_under_20mb'] is True
assert all(row['exact_text_duplicates'] == 0 for row in core['summary'].values())
assert recovery['parent_adopted_documents'] == 1145290
assert recovery['all_previous_adopted_text_preserved'] is True
assert restricted['restricted_sources'] == 7 and restricted['alias_positions'] == 11
assert restricted['original_parent_bodies_decoded'] is False
assert partial['checked'] == old_partial['checked'] == dict(documents=460695, input_ids=462874291)
assert partial['remaining_hold'] == partial['unprocessed'] == 115526
assert partial['goal_complete'] is False
assert all(part['training_authorized'] is False for part in proofs.values())
assert all(sum(value[key] for key in ['KEEP','EDIT','EXCLUDE','HOLD']) == value['documents']
           for value in [new['counts'],old['counts'],new['recovery_outcomes']])
assert {key:new['counts'][key] for key in core['decisions']} == core['decisions']
join_path = BASE / 'resolution_join_plan_v4/complete.json'
join = read(join_path)
assert join['counts']['HOLD'] == 73668 and join['remaining_hold'] == 115526

accepted = total(new['accepted'])
before = total(new['same_adopted_roster_before']['counts'])
assert accepted['documents'] == before['documents'] == 1369110
assert accepted['tokens'] - before['tokens'] == new['counts']['edited_content_ids_delta']
assert sum(part['ids'] for part in core['summary'].values()) == accepted['tokens']
assert sum(part['documents'] for part in core['summary'].values()) == accepted['documents']
signals_before = total(new['same_adopted_roster_before']['structure_signals'])
signals_after = total(new['accepted_structure_signals'])
signal_changes = {key:dict(before=signals_before.get(key,0),after=signals_after.get(key,0),
    reduction=signals_before.get(key,0)-signals_after.get(key,0))
    for key in sorted(set(signals_before)|set(signals_after))}
hold = partial['remaining_hold']
result = dict(status='ACTUAL_REVIEWED_PARTIAL_V2_VERIFIED_FULL_GOAL_STILL_ACTIVE',
    utc=datetime.now(timezone.utc).isoformat(),
    input_pins=[pin(path) for path in [new_dir/'built.json',old_dir/'built.json',
        old_dir/'partial_resolution_verified.json',build_path,verify_path,failed_path,join_path,Path(__file__)]]
        + list(verify['proofs'].values()),
    full_scope=new['counts'], original_hold_scope=partial['checked'],
    original_hold_outcomes=partial['outcomes'],original_hold_raw_input_ids=new['recovery_outcomes'],
    previous_hold=old_partial['remaining_hold'],remaining_hold=hold,
    hold_reduction_since_previous=old_partial['remaining_hold']-hold,
    hold_reduction_since_original=460695-hold,
    remaining_hold_percent_original_hold=100*hold/460695,
    resolved_percent_original_hold=100*(460695-hold)/460695,
    remaining_hold_percent_full_scope=100*hold/new['counts']['documents'],
    unresolved_unique_sources=73668,
    prior_baseline_documents_preserved=1145290,
    accepted_by_split=new['accepted'],accepted_total=accepted,
    same_adopted_roster_before=before,
    comparable_structure_signal_counts=signal_changes,
    accepted_documents_with_signal=new['accepted_documents_with_signal'],
    original_documents_with_signal=new['original_documents_with_signal'],
    same_adopted_language_proxy_before=new['same_adopted_roster_before']['language_proxy'],
    accepted_language_proxy_after=new['accepted_language_proxy'],
    accepted_character_presence_buckets=new['accepted_character_presence_buckets'],
    source_kind=new['source_kind'],mixture_metadata_not_document_labels=new['mixture_metadata_not_document_labels'],
    exact_train_val_text_overlap=0,per_split_exact_text_duplicates=0,
    all_accepted_documents_regenerated=True,files_under_20000000_bytes=True,
    restricted_metadata=restricted,
    metric_limits=[
        'Structural signals count syntax candidates, not demonstrated errors.',
        'Protected parent bodies remain opaque; corresponding original-body language/structure metrics are unavailable.',
        'Character presence is not a language or document-origin label.',
        'Comparison uses this same admitted roster, not training windows or previous differently sized admitted sets.',
        'Exact and aligned window checks do not establish shifted/near/source-identity leakage absence.',
        'Original raw input IDs are neither training exposure nor unique corpus size.',
        'full_target_processed means enumerated; explicit unprocessed HOLD still equals115526.'
    ],
    independent_semantic_review='SOURCE_LINKED_STRATIFIED_REVIEW_AND_MEDIATION_NOT_ALL_FACT_VERIFICATION',
    current732_reading_not_in_this_cache=True,goal_complete=False,training_authorized=False)
payload=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert len(payload)<20000000
with OUT.open('xb') as stream:
    stream.write(payload)

lines=['# 잔여 HOLD 정제의 새 부분 캐시 검증과 실제 잔여량','',
    '전체 goal은 진행 중이다. 새 부분 캐시 생성과 독립 소비자 검증은 모두 실제 종료 코드0이다. '
    '처음 CLI 검산은 데이터 검사 전 재귀 진입 오류로 종료1이었고, 실패 로그/영수증/동결 코드를 보존했다. '
    '별도 직접 라이브러리 진입점의3개 반례 시험 후 새 실행에서 전량 검산을 마쳤다. 이전 실패를 성공으로 덮지 않는다.','',
    '| 원래 HOLD460,695위치의 결과 | 이전 검증 캐시 | 새 검증 캐시 |','|---|---:|---:|']
labels={'KEEP':'원문 유지','EDIT':'수정 본문','EXCLUDE':'채택 제외','HOLD':'미처리/미결'}
for key in ['KEEP','EDIT','EXCLUDE','HOLD']:
    lines.append(f'| {labels[key]} | {old_partial["outcomes"][key]:,} | {partial["outcomes"][key]:,} |')
lines += ['',f'이전보다 잔여 HOLD가44,693위치 줄었다. 최초 HOLD 중{460695-hold:,}위치'
    f'({result["resolved_percent_original_hold"]:.4f}%)가 유지·수정·제외로 처리됐고, '
    f'{hold:,}위치({result["remaining_hold_percent_original_hold"]:.4f}%)는 아직 미결이다. '
    f'전체2,154,912위치 대비 잔여 비중은{result["remaining_hold_percent_full_scope"]:.4f}%다. '
    '미결은73,668개 고유 원문이며 모두 불량 확정이나 복구 불가 판정을 받은 것은 아니다.','',
    '전체 새 캐시는 KEEP1,024,642 / EDIT344,468 / EXCLUDE670,276 / HOLD115,526위치다. '
    f'채택은{accepted["documents"]:,}문서 위치, EOS 포함{accepted["tokens"]:,}IDs이며 '
    f'본문 IDs는{accepted["content_ids"]:,}다. 원래 HOLD 원문 IDs462,874,291 중 '
    '미결 원문 IDs197,074,818은 학습 노출량이나 고유 코퍼스 크기와 다르다.','',
    '제외는 정확 중복·확인된 train/val 교집합·원형 경계 결손·개별 문맥 판정의 서로 다른 이유를 가진다. '
    '보존 가능한 동일 본문 한 개를 남기는 중복 제외와, 내용의 참/거짓 또는 유용성 판정은 구별한다. '
    '이번 총 제외121,349를 모두 의미 불량 문서로 세지 않는다. 정확 이유와 원문 연결은 새 캐시 ledger에 남아 있다.','',
    '기존 기준 채택1,145,290본문은 검증상 보존됐다. 이전 부분 캐시의 추가 후보까지 모두 글자 단위로 '
    '불변이라는 뜻은 아니다. 그 후보의 재검토·수정 내역은 ROOT10과 이전 선택/실패 기록에 남긴다.','',
    '| 동일 새 채택 목록의 구조 신호(발생 수) | 정제 전 | 정제 후 |','|---|---:|---:|']
for key, value in signal_changes.items():
    lines.append(f'| {key} | {value["before"]:,} | {value["after"]:,} |')
lines += ['',
    '이 표는 새 채택 목록에서 계측 가능한 원문과 수정 본문을 같은 분모로 비교한다. 보호 부모 본문은 '
    '의도적으로 읽지 않았으므로 해당 원문의 구조·언어 값은 before의 미확인 한계로 남는다. HTML·표제·URL·반복 '
    '신호에는 실제 코드, 참고문헌, 정상 문서 구조와 인용이 포함된다. 수치를 오류 확정 수로 읽거나 '
    '과거 학습 창26.8%/4.3%와 직접 비교하지 않는다.','',
    '한글 음절/ASCII 문자 및 포함 문서 수를 전후 JSON에 기록했다. 혼합 원천의 문서별 출처·언어 라벨은 '
    '복원하지 않았으며 UNKNOWN_MIXED_NATIVE_CACHE를 유지한다. FineWeb/위키 비중을 문자 포함률로 만들지 않는다.','',
    '독립 소비자는 채택 전량 재생성·EOS/경계·토큰 직렬화·20,000,000바이트 미만 분할·정확 문서 중복0·'
    'train/val 정확 본문 교집합0을 확인했다. 보호7원문/동일SHA11위치는 메타데이터만 검증했고 부모 본문 디코딩0이다. '
    '근접 중복·임의 이동 구간·원문서 URL/ID 기준 누설과 전량 사실 검증은 확정하지 않았다.','',
    '732개 후속 원문 판독은 이 캐시에 선반영하지 않았다. 미상 수식·표 대상·저자 귀속을 추정하지 않고 '
    '실제 독립 본문·수치·인용을 보존하는 검토와 다른 잔여 유형 처리를 계속한다. 미처리 명부의 HOLD를 '
    '종결 판정으로 개명해 전체 완료하지 않는다. 추가300M과 모델/GPU 학습 실행은 승인되지 않았다.','',
    '수치 정본: [검증·재계측 영수증](REVIEWED_PARTIAL_V2_VERIFIED_METRICS_V1.json). '
    '캐시: `data_cache/p106b_hold_resolution_v1_20261027_goalc/cache_reviewed_partial_v2/`.','']
text='\n'.join(lines)
assert '\u6b8b' not in text and len(text.encode('utf-8'))<20000000
with REPORT.open('x',encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=result['status'],remaining_hold=hold,
    remaining_percent=result['remaining_hold_percent_original_hold'],accepted=accepted,
    signals=signal_changes,goal_complete=False),ensure_ascii=False))
