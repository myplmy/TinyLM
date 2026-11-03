"""Freeze the completed controls birth assignment and continued field queue."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}
reused = AUDIT / 'record_resume_progress_v5.py'
nodes = [node for node in ast.parse(reused.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name == 'read']
assert len(nodes) == 1 and not nodes[0].decorator_list
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(reused), 'exec'), globals())
versions = {1: 'v8', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v9', 6: 'v6', 7: 'v2'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
         for page, version in versions.items()}
page_counts = {page: sum(role['saved'] for role in value['coverage'].values()) for page, value in pages.items()}
assert sum(page_counts.values()) == 1758 and all(not value['errors'] for value in pages.values())
field_needs = sorted({ident for page in pages.values() for ident in page['needs_root']})
assert set(field_needs) == {'expanded_train:49092', 'expanded_train:50689', 'expanded_train:56714',
                            'expanded_train:72884', 'expanded_train:111797'}
birth = read(BASE / 'birth_root11_independent_v1_snapshots/v25/complete.json')
assert birth['coverage']['context_controls'] == dict(expected=1354, saved=1354, awaiting_review=0)
assert sum(row['saved'] for row in birth['coverage'].values()) == 2529
assert not birth['errors'] and not birth['needs_root']
delivery = read(BASE / 'birth_root11_input_delivery_gated_v1/v15/complete.json')
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1534
extra = read(AUDIT / 'ROOT_85646_V3_FOLLOWUP_VERIFIED_V1.json')
assert extra['combined_specific_followups'] == 22 and extra['known_pending_in_this_case'] == 0
entry = read(AUDIT / 'FIELD_BIRTH_ROLES_SHORT_READERS_RUNTIME_VERIFIED_V1.json')
assert len(entry['positive']) == 2 and len(entry['negative']) == 5
copies = read(AUDIT / 'FIELD_CONTROLS_INITIAL_COPIES_COMPLETE_V1.json')
assert copies['sources'] == 3248 and copies['root_authored_cleaned_bodies'] == 0
prior = read(AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V6.json')
data = dict(status='CONTROLS_BIRTH_ASSIGNMENT_SAVED_AND_FIELD_REVIEW_CONTINUES',
            field_expected=18237, field_saved=1758, field_missing=16479,
            other_first_review_missing=50162, combined_first_review_missing=66641,
            field_versions={str(key): value for key, value in versions.items()}, field_saved_by_page=page_counts,
            field_connection_errors=0, field_frozen_needs_root=field_needs,
            field_three_whole_hold_sources=['expanded_train:49092', 'expanded_train:50689', 'expanded_train:56714'],
            field_frozen_followup_rows=['expanded_train:72884', 'expanded_train:111797'],
            field_followup_root_instructions_delivered=True, latest_followup_review_collection_separate=True,
            birth_expected=2707, birth_saved=2529, birth_missing=178, birth_by_role=birth['coverage'],
            birth_connection_errors=0, birth_frozen_needs_root=0, birth_pinned_candidates=2179,
            birth_materialized_candidates=350, controls_birth_assignment_saved=1354,
            controls_next_phase='remaining_field_title_page_001_counter_v1',
            controls_new_initial_copies_not_reviews=3248,
            new_birth_roles_field_runtime_positive=2, new_birth_roles_field_runtime_denials=5,
            existing_field_helper_and_entry_changed=False,
            prospective_delivery_preconditions_verified=1534,
            historical_sources_without_retrospective_emission_claim=995,
            delivery_precondition_failures=0, input_delivery_is_not_semantic_review=True,
            byte_checked_specific_followups=22, pending_in_these_specific_followups=0,
            ordered_flag_linked_record_scopes=390, ordered_flag_unlinked_in_these_scopes=195,
            earlier_speed_evidence='RESUME_PROGRESS_AND_SPEED_20261104_V6.json',
            birth_stage_active_role_count_changed_from_two_to_one=True,
            speed_caveat='Controls moved to first field review; future birth-only row growth cannot be compared as unchanged team throughput.',
            official_cache=3, original_hold_positions=460695,
            official_handled_positions=350522, official_hold_positions_unchanged=110173,
            latest_verified_local_commit=prior['latest_verified_local_commit'],
            own_git_window='CLOSED', later_work_has_uncommitted_changes=True,
            goal_management_status='blocked', actual_work_status='RUN',
            approval_wait_or_external_blocker=False, root_or_cache_adoptions_of_new_reviews=0,
            whole_corpus_semantic_pass=False, goal_complete=False, training_authorized=False,
            input_pins=pins)
for path in (reused, Path(__file__).resolve()):
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V7.json').open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
text = '''# 전체 정제 계속 — 한 역할의 생년 배정 종료와 field 전환

다섯 역할과 총괄은 RUN이다. 공식cache3의 원래HOLD460,695위치 중350,522처리/110,173잔여는 그대로이며 새 리뷰를 채택 감소량으로 세지 않는다.

| 단계 | 동결 저장량 | 해당 단계 미저장 |
|---|---|---|
| 필드·제목 1차 |1,758/18,237고유원문, 연결오류0|16,479고유원문|
| 다른유형 1차 |50,162고유원문의 전량 입력·큐 준비|50,162고유원문|
| 생년·사망일 독립2차 |2,529/2,707고유원문, 연결오류/동결중재0|178고유원문|

1차미저장은66,641고유원문이다. 독립2차178건과합쳐고유원문으로세지않는다. field는001v8=308/002v8=307/003v6=309/004v12=310/005v9=307/006v6=147/007v2=70이다. 생년snapshot25는C1354/L1175이며C의자기배정1354건저장·연결이모두끝났다. 다른역할의178건과전체goal은남아있다.

C는기존field001자기TASK001부터36페이지와그뒤other98페이지전량으로전환했다. L은자기생년미착수를끝낸뒤같은기존전량큐로간다. 세다른역할은Hfield007/historical006/legacy006을진행한다. 새두역할field진입점은기존entry/helper바이트를바꾸지않고명단metadata만확장해실제2역할호출/거부5를확인했다. 기존19회귀의재실행이아니며같은검증된동작을재사용했다. 한exec한조각/고정ID·페이지·패킷·모든논리END/EOF는유지한다.

C가편집에쓸candidate작업용초기사본3248개를원문ID/원형SHA보호검사뒤고정candidate와동일바이트로만복사하고전부SHA검산했다. 새정제·판독·채택은0이다. 원형/candidate/초기사본은덮지않고Luna가자기새TXT/MD만작성한다. 완료원문을도구때문에재독하지않는다.

field 원시중재49092/50689/56714는개별전체HOLD3원문/6위치원장에연결한다. 동결006/007의72884/111797은그뒤의좁은후속원문행이며중재기준을전달했다. 111797은실제다간원문/후보/패킷에와인링크가없음을핀검산했고작성자가25개지정패킷을실제로다시읽어잘못된ID내용보고를정정했다. 새리뷰선택으로닫는다음수집은별도다. 원문불일치/변형원인이나의도는추정하지않는다.

생년동결24에남았던841018/841818은실제재판독·review240_v3로연결돼25에서미결0이다. 별도gated15는1534행의정확입력전달선결/실패0을확인하며과거995범위의전달시각을소급하지않는다. 출력은이해·의미통과가아니다.

85646v3는원문52,391자/v1선택전문판독과v1→v2의7개보완·v2→v3의단일수정,그밖바이트불변과실제원문인용/나머지네리뷰행불변을확인했다. 구v1음성판정도보존한다. 기존21개와합쳐22개명시후속범위미결0이나전체새본문/기술사실검증/캐시채택완료는아니다.

속도근거는v6에연결한다. 이전5시간창저장률186.0→155.4건/시간감소와최근같은생년묶음361.1→432.1행/시간증가를구분한다. 이제C가field로옮겼으므로향후생년저장률만으로팀전체속도를비교하지않는다. 문서길이·결손조건/주체판단과보완재검토,경로/ID혼동·저장누락·출력잘림·총괄의단계/준비기/안내서실수는실제재작업으로기록했고기여율·하드웨어저하·짧은호출의인과효과는확인하지않았다.

마지막검증한국어커밋은5959b15f이며그뒤변경의중간저장을준비한다. 남은전량판독과독립의미검토·새ROOT/roster·캐시재생성·독립consumer·전체재계측·필요정본·최종핸드오프·한국어로컬저장은미완이다. A–E전체전에는완료/일시중지/추가300M학습승인으로바꾸지않는다. 보호원형·TinyDataset·타세션전용자료·GPU/모델/학습·설치/다운로드·push/PR은진행하지않았다.
'''
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V7.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=1758, first_review_missing=66641,
                     birth_saved=2529, birth_missing=178, controls_birth_missing=0,
                     official_HOLD_unchanged=110173), ensure_ascii=False))
