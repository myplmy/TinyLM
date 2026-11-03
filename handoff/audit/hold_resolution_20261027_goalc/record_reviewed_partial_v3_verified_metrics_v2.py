"""Record actual verified cache3 quantities and exact exclusion reasons, goal active."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

def pin(path):return dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path))
def total(parts):
    out=Counter()
    for part in parts.values():out.update(part)
    return dict(out)

new_dir=inv.BASE/'cache_reviewed_partial_v3';old_dir=inv.BASE/'cache_reviewed_partial_v2'
new,old=map(inv.cache.read,[new_dir/'built.json',old_dir/'built.json'])
build_path=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_PROCESS_EXIT_V1.json'
verify_path=AUDIT/'CACHE_REVIEWED_PARTIAL_V3_VERIFY_EXIT_V1.json'
build,verify=map(inv.cache.read,[build_path,verify_path])
assert build['process_exit_code']==verify['process_exit_code']==0
assert build['observation_method']==verify['observation_method']=='ACTUAL_SUBPROCESS_WAIT_RETURN_CODE'
assert build['built_receipt']==pin(new_dir/'built.json')
proofs={}
for name in ['verified.json','recovery_verified.json','partial_resolution_verified.json',
        'restricted_metadata_verified.json','baseline_preservation_scope.json']:
    path=new_dir/name;assert verify['proofs'][name]==pin(path);proofs[name]=inv.cache.read(path)
core=proofs['verified.json'];recovery=proofs['recovery_verified.json'];partial=proofs['partial_resolution_verified.json']
restricted=proofs['restricted_metadata_verified.json'];baseline=proofs['baseline_preservation_scope.json']
assert core['every_adopted_document_regenerated'] is True and core['exact_train_val_text_overlap']==0
assert core['files_under_20mb'] is True and all(r['exact_text_duplicates']==0 for r in core['summary'].values())
assert recovery['built_sha256']==pin(new_dir/'built.json')['sha256']
assert recovery['core_verified_sha256']==pin(new_dir/'verified.json')['sha256']
assert partial['core_recovery_verified_sha256']==pin(new_dir/'recovery_verified.json')['sha256']
assert recovery['parent_adopted_documents']==baseline['preserved_baseline_documents']==1145290
assert restricted['restricted_sources']==7 and restricted['alias_positions']==11 and restricted['original_parent_bodies_decoded'] is False
assert partial['checked']==dict(documents=460695,input_ids=462874291)
assert partial['remaining_hold']==110173 and partial['reviewed_hold']==38 and partial['unprocessed']==110135
assert all(value.get('goal_complete') is not True for value in proofs.values())
assert partial['goal_complete'] is False and restricted['goal_complete'] is False and baseline['goal_complete'] is False
assert all(value['training_authorized'] is False for value in proofs.values())
roster_path=inv.BASE/'roster_reviewed_partial_v3/complete.json';roster=inv.cache.read(roster_path)
assert roster['unique_counts']['HOLD']==70230 and partial['roster_sha256']==inv.file_sha(roster_path)
old_partial=inv.cache.read(old_dir/'partial_resolution_verified.json')
accepted=total(new['accepted']);before=total(new['same_adopted_roster_before']['counts'])
assert accepted['documents']==before['documents']==1372548
assert accepted['tokens']-before['tokens']==new['counts']['edited_content_ids_delta']
assert sum(r['ids'] for r in core['summary'].values())==accepted['tokens']
before_signals=total(new['same_adopted_roster_before']['structure_signals'])
after_signals=total(new['accepted_structure_signals'])
signals={k:dict(before=before_signals.get(k,0),after=after_signals.get(k,0),
    reduction=before_signals.get(k,0)-after_signals.get(k,0)) for k in sorted(set(before_signals)|set(after_signals))}
selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'
selection=inv.cache.read(selection_path)
explicit={r['original_text_sha256'] for r in selection['rows'] if r['selected']['decision']=='EXCLUDE'}
boundary={'validation:0','validation:3759','historical_train:709976'}
exclusions=Counter();checked=Counter();outcomes=Counter()
for row in inv.cache.rows(new_dir/'ledger',new['manifests']['ledger']):
    if row.get('resolution_roster_sha256')!=partial['roster_sha256']:continue
    checked.update(documents=1,input_ids=row['input_ids']);outcomes[row['decision']]+=1
    if row['decision']!='EXCLUDE':continue
    if row.get('validation_overlap'):kind='EXACT_TRAIN_VAL_OVERLAP'
    elif row.get('duplicate_of'):kind='EXACT_BODY_DUPLICATE'
    elif row['id'] in boundary:kind='IRREPARABLE_ORIGINAL_SPLIT_BOUNDARY'
    elif row['original_text_sha256'] in explicit:kind='EXPLICIT_SOURCE_CONTEXT_EXCLUSION'
    else:raise AssertionError('unexplained exclusion: '+row['id'])
    exclusions[kind]+=1;exclusions[kind+'_raw_input_ids']+=row['input_ids']
assert dict(checked)==partial['checked'] and dict(outcomes)==partial['outcomes']
assert sum(v for k,v in exclusions.items() if not k.endswith('_raw_input_ids'))==partial['outcomes']['EXCLUDE']
hold=partial['remaining_hold']
paths=[new_dir/'built.json',old_dir/'built.json',old_dir/'partial_resolution_verified.json',
    roster_path,selection_path,build_path,verify_path,Path(__file__)]
result=dict(status='ACTUAL_REVIEWED_PARTIAL_V3_VERIFIED_WHOLE_GOAL_ACTIVE',utc=datetime.now(timezone.utc).isoformat(),
    input_pins=[pin(p) for p in paths]+list(verify['proofs'].values()),
    full_scope=new['counts'],original_hold_scope=partial['checked'],original_hold_outcomes=partial['outcomes'],
    original_hold_raw_input_ids=new['recovery_outcomes'],original_hold_exclusion_reasons=dict(exclusions),
    remaining_hold=hold,reviewed_hold=38,unprocessed=110135,remaining_hold_unique=70230,
    individually_reviewed_hold_unique=38,unprocessed_unique=70192,
    previous_remaining_hold=old_partial['remaining_hold'],hold_reduction_since_previous=old_partial['remaining_hold']-hold,
    hold_reduction_since_original=460695-hold,remaining_hold_percent_original=100*hold/460695,
    resolved_or_individually_reviewed_percent_original=100*(460695-110135)/460695,
    keep_edit_exclude_percent_original=100*(460695-hold)/460695,
    remaining_hold_percent_full_scope=100*hold/new['counts']['documents'],
    accepted_by_split=new['accepted'],accepted_total=accepted,same_adopted_roster_before=before,
    comparable_structure_signal_counts=signals,accepted_documents_with_signal=new['accepted_documents_with_signal'],
    original_documents_with_signal=new['original_documents_with_signal'],
    same_adopted_language_proxy_before=new['same_adopted_roster_before']['language_proxy'],
    accepted_language_proxy_after=new['accepted_language_proxy'],accepted_character_presence_buckets=new['accepted_character_presence_buckets'],
    source_kind=new['source_kind'],mixture_metadata_not_document_labels=new['mixture_metadata_not_document_labels'],
    exact_train_val_text_overlap=0,per_split_exact_text_duplicates=0,all_adopted_documents_regenerated=True,
    files_under_20000000_bytes=True,prior_baseline_documents_preserved=1145290,baseline_preservation_scope=baseline,
    restricted_metadata=restricted,independent_birth_second_reading='NOT_COMPLETED',
    current_literal_bodies_added_in_this_cache=0,
    metric_limits=['Structure signals include valid references/code/quotes and are not confirmed error counts.',
        'Before/after uses this same admitted roster; protected original-parent body metrics remain unavailable.',
        'Original input IDs are not training exposure or unique corpus size.',
        'Character presence is neither language identification nor Wiki/FineWeb attribution.',
        'Exact duplication checks do not close shifted/near/source-URL leakage or full fact verification.',
        'Reviewed nonadmission and unread HOLD are separate; no unread source was renamed reviewed HOLD.'],
    proof_goal_field_presence={name:('EXPLICIT_FALSE' if value.get('goal_complete') is False else 'ABSENT_NOT_A_GOAL_STATUS') for name,value in proofs.items()},
    whole_corpus_cleanup_complete=False,goal_complete=False,training_authorized=False)
out=AUDIT/'REVIEWED_PARTIAL_V3_VERIFIED_METRICS_V1.json'
payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode();assert len(payload)<20_000_000
with out.open('xb') as f:f.write(payload)
lines=['# 잔여 HOLD의 중간 캐시3 실검증과 잔여량','',
    '전체 정제 goal은 계속 진행 중이다. 새 중간 캐시의 실제 생성과 독립 소비자 검산은 각각 종료코드0이다. '
    '이는 전체 정제·전량 사실 검증·학습 재개 승인이 아니다.','',
    '| 원래 HOLD460,695위치의 처리 | 이전 검증v2 | 새 검증v3 |','|---|---:|---:|']
for key in ['KEEP','EDIT','EXCLUDE','HOLD']:
    lines.append(f'| {key} | {old_partial["outcomes"][key]:,} | {partial["outcomes"][key]:,} |')
lines.extend(['',f'잔여는 이전보다{old_partial["remaining_hold"]-hold:,}위치 줄어{hold:,}위치다. '
    f'처음 HOLD 대비{result["remaining_hold_percent_original"]:.4f}%, 전체2,154,912위치 대비{result["remaining_hold_percent_full_scope"]:.4f}%다. '
    '이 중38위치는 개별 원문 검토 후 비채택한 HOLD이며110,135위치는 아직 내용을 판독하지 않은 미처리다. '
    '고유 원문으로는 각각38/70,192이며 합계70,230이다. 미처리를 종결 HOLD로 바꾸지 않았다.','',
    f'채택은{accepted["documents"]:,}문서, EOS 포함{accepted["tokens"]:,}IDs, 본문{accepted["content_ids"]:,}IDs다. '
    '기준 캐시의1,145,290본문은 보존했다. v2 추가 후보 전체가 불변이라는 뜻은 아니며, 수량 복구와 오채택 철회가 있다.','',
    '| 원래 HOLD 안의 실제 제외 이유 | 위치 수 |','|---|---:|'])
for key,value in exclusions.items():
    if not key.endswith('_raw_input_ids'):lines.append(f'| {key} | {value:,} |')
lines.extend(['','정확 중복은 보존되는 동일 본문을 가리키며 내용 불량 확정이 아니다. 확인된 train/val 정확 교집합은 분할 누설을 막기 위한 제외다. '
    '원형 경계 결손과 개별 문맥 비채택은 별도 이유다. 모든 연결은 새 ledger에 남아 있다.','',
    '| 동일 새 채택 목록의 구조 신호 | 정제 전 | 정제 후 |','|---|---:|---:|'])
for key,value in signals.items():lines.append(f'| {key} | {value["before"]:,} | {value["after"]:,} |')
lines.extend(['','구조 신호는 오류 확정 수가 아니다. 정상 참고문헌·코드·표제·인용도 포함한다. 비교는 같은 새 채택 목록이며 '
    '보호 부모 원문의 before 본문 지표는 미확인이다. 과거 학습 창26.8%/4.3%와 분모를 섞지 않는다. '
    '문서별 출처는 UNKNOWN_MIXED_NATIVE_CACHE를 유지하며 문자 포함률을 출처·언어 비중으로 바꾸지 않는다.','',
    '독립 소비자는 채택 전량 재생성, 문서경계/EOS·직렬화, 각 파일20,000,000바이트 미만, 정확 본문중복0 및 '
    'train/val 정확 본문 교집합0을 확인했다. 보호7원문/동일SHA11위치는 metadata와 승인된 safe view만 검증했고 부모 본문 디코딩0이다. '
    '근접·이동 구간·URL 원문서 누설은 미확인이며 출생 전량의 별도2차 전문 판독은 미완이다.','',
    'literal1793의 진행 본문은 이번 캐시에 선반영하지 않았다. 전체 잔여 판독·다른 유형·정본 연쇄·최종 핸드오프와 로컬 저장을 계속한다. '
    '중간 캐시 검증은 goal 정지/일시중지 사유가 아니다.','',
    '수치 정본: [실검증 및 계측](REVIEWED_PARTIAL_V3_VERIFIED_METRICS_V1.json).',''])
report=AUDIT/'HOLD_STATUS_AND_EXCLUSION_RATIONALE_20261103_V2.md'
with report.open('x',encoding='utf-8') as f:f.write(chr(10).join(lines))
print(json.dumps(dict(accepted=accepted,remaining_hold=hold,reviewed_hold=38,unprocessed=110135,
    exclusion_reasons=dict(exclusions),signals=signals,goal_complete=False),ensure_ascii=False))
