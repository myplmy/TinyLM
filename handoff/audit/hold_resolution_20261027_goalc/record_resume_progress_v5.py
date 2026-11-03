"""Freeze newer review counts and the real missing-input repair; no admission."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}


def read(path):
    data = path.read_bytes()
    assert len(data) < 20_000_000
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest().upper()
    return json.loads(data)


versions = {1: 'v8', 2: 'v8', 3: 'v6', 4: 'v11', 5: 'v6', 6: 'v4'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' /
                    version / 'complete.json') for page, version in versions.items()}
assert all(not page['errors'] for page in pages.values())
page_counts = {page: sum(role['saved'] for role in snapshot['coverage'].values())
               for page, snapshot in pages.items()}
assert sum(page_counts.values()) == 1496
birth_path = BASE / 'birth_root11_independent_v1_snapshots/v22/complete.json'
birth = read(birth_path)
assert not birth['errors'] and not birth['needs_root']
assert sum(role['saved'] for role in birth['coverage'].values()) == 1790
delivery_path = BASE / 'birth_root11_input_delivery_gated_v1/v12/complete.json'
delivery = read(delivery_path)
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 795
holds = read(AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V2.json')
raw_field_needs = {ident for page in pages.values() for ident in page['needs_root']}
assert raw_field_needs == {row['id'] for row in holds['rows']} and len(raw_field_needs) == 3
repair = read(AUDIT / 'DELIVERY_MISSING_449324_REPAIR_VERIFIED_V1.json')
assert repair['other_four_review_rows_unchanged']
assert repair['unchanged_assigned_candidate_bytes_outside_one_date_role_edit_and_final_LF']
assert repair['original_bytes_outside_two_field_edits_empty_heading_and_final_LF_verified']
shortcut = read(AUDIT / 'BIRTH_READER_SHORTCUTS_RUNTIME_VERIFIED_V1.json')
assert shortcut['regression_tests']['count'] == 35 and shortcut['regression_tests']['failures'] == 0
prior = read(AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V4.json')
assert repair['id'] not in prior['explicit_root_followup_ids']
receipt = read(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V12.json')
assert receipt['commit'] == '5959b15f42d9db35817ddf78f1296622e08c5940'
assert receipt['actual_changed_paths'] == 692 and receipt['all_committed_bytes_match']
data = dict(status='WHOLE_CLEANUP_CONTINUES_WITH_MORE_REVIEWS_AND_A_REAL_NEGATIVE_REPAIR',
            field_expected=18237, field_saved=1496, field_missing=16741,
            other_first_review_missing=50162, combined_first_review_missing=66903,
            field_versions={str(k): v for k, v in versions.items()}, field_saved_by_page=page_counts,
            field_connection_errors=0, field_raw_needs_root=sorted(raw_field_needs),
            field_raw_needs_root_individually_adjudicated=True, field_whole_holds=3,
            field_whole_hold_positions=holds['source_positions'],
            birth_expected=2707, birth_saved=1790, birth_missing=917,
            birth_by_role=birth['coverage'], birth_connection_errors=0, birth_needs_root=0,
            birth_pinned_candidates=1549, birth_materialized_candidates=241,
            prospective_delivery_preconditions_verified=795,
            historical_sources_without_retrospective_emission_claim=995,
            delivery_precondition_failures_in_new_frozen_view=0,
            earlier_missing_delivery_and_wrong_review_preserved=True,
            independently_byte_checked_explicit_followups=13,
            known_pending_in_these_thirteen=0,
            ordered_flag_linked_record_scopes=390, ordered_flag_unlinked_in_these_scopes=195,
            cpu_shortcut_and_delivery_regression_tests=35,
            official_cache=3, official_hold_positions_unchanged=110173,
            original_hold_positions=460695, official_handled_positions=350522,
            latest_verified_local_commit=receipt['commit'], latest_commit_paths=692,
            latest_commit_bytes=10209312, new_following_changes_still_in_progress=True,
            goal_management_status='blocked', actual_work_status='RUN',
            approval_wait_or_external_blocker=False, root_or_cache_adoptions_of_new_reviews=0,
            whole_corpus_semantic_pass=False, goal_complete=False, training_authorized=False,
            input_pins=pins)
target = AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V5.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
text = '''# 전체 정제 계속 — 최신 검토와 전달 누락 교정

다섯 Luna 역할의 전량 큐와 총괄 검토는 계속RUN이다. 한국어 로컬 커밋 `5959b15f42d9db35817ddf78f1296622e08c5940`에 692명시 경로/10,209,312바이트를 저장했고 부모2f811836·전체경로·모든blob·명시저장범위미반영0·공유index0을 검산했다. 그 뒤 추가 작업은 진행 중이다. 이 저장은 목표 완료나 일시중지가 아니다.

| 단계 | 고정 집계 | 해당 단계 미저장 |
|---|---|---|
| 필드·제목 1차 |1,496/18,237고유원문, 연결오류0|16,741고유원문|
| 다른유형 1차 |50,162고유원문의 전량 입력·큐 준비|50,162고유원문|
| 생년·사망일 묶음 독립2차 |1,790/2,707고유원문, 연결오류/동결중재대기0|917고유원문|

1차 리뷰 미저장은66,903고유원문이다. 독립2차917건과 단계를 합쳐 고유원문 수로 세지 않는다. 보호1건은 별도 계약이다. 필드는page001v8=308/002v8=307/003v6=309/004v11=310/005v6=177/006v4=85로 동결했다. 생년snapshot22는controls1000/Latin790이고 입력 연결1,549/새본문241이다. 역할들은 이 동결본 이후 TASK도 계속한다.

코드·수식1차는 기존1,793고유원문/2,597위치의 본문후보1,783·개별HOLD10 연결을 유지한다. 필드 원시NEEDS_ROOT 세 행49092/50689/56714는 개별 전체HOLD 원장v2로 연결했고 세 원문은6위치다. 원문 손상이 확정된 것과 귀속을 복원 못해 보류한 것을 구분하며, 후보 채택이나 공식HOLD감소로 계산하지 않는다.

새 전달검증에서는449324의 packet1 이력이 없던 실제 음성 사례를 찾았다. 구 review162는1946/1954출생·8월25일·음반을 근거로 썼으나 실제393자 원문은1909년 출생 공무원 최문경의 경력과1982년8월31일/몰년미상 표기를 담았다. 미전달은 곧 미판독이라는 일반 결론이 아니지만, 이 건은 원문과 리뷰 내용의 불일치도 직접 확인됐다. 구 리뷰·당시 차단 뷰·새 재판독과 수정 이력을 모두 보존했다. 이 한 사례를 전량 오류율로 환산하지 않는다.

449324만 고정 reader로 실제 재판독한 뒤 새 review162_v3/본문v2를 만들었다. 1982년 단정과 몰년미상은 함께보류하고1909출생·연도없는8월31일 사망 역할과 경력은 보존했다. 총괄은 지정 원문/후보/선택 전문·모든차이·EOF·sidecar·구/신리뷰행과 나머지네행 불변을 확인했다. 후보 대비 날짜역할 한곳과 최종개행 외 바이트가 모두 같고, 원문 대비 허용한 두 필드/빈표제/개행 외 바이트도 같음을 검산했다. 총괄이 먼저 다른 단계의 같은ID후보를 대조한 시도는 assertion으로 멈췄으며, 현재manifest의 정확path/SHA로 바로잡은 근거만 사용했다.

birth-gated뷰v11의 미전달1건은 당시 음성 근거로 보존한다. 교정 뒤 snapshot22에 대한gated뷰v12는795행의 정확 패킷 전달이 리뷰저장보다 앞섬을 확인했고 전달실패0/원시연결오류0이다. 과거995범위에는 없던 시각 증거를 소급하지 않는다. 출력기록은 이해·인증·의미 검토 통과가 아니다. 기존12개와 이번1개의 명시 후속보완은 각 범위의 바깥바이트까지 검산했지만 전체 새본문 검토 완료를 뜻하지 않는다.

긴경로 입력오기를 줄이기 위해 controls/Latin의 짧은 실행진입점 두개를 만들었다. 기존v2의SHA를 확인한 뒤 같은v2/guard/config/registry/journal을 그대로 실행한다. CPU35회귀, 실제root전용probe2개와 거부2개를 확인했고 공식리뷰입력으로root시험을 기록하지 않았다. 새 진입점 때문에 완료된 원문을 다시 읽지 않는다. 필드 세역할의 경로/출력잘림 부담은 기존scoped helper 추가재사용을 검토할 다음 항목이다.

속도에 관한 기존 관측은 약5시간 연속창의 리뷰 저장률186.0→155.4건/시간(약16.5%감소)이다. 남은위치당원본토큰ID평균은 원래HOLD의약1.73배였으며 긴학술문서·결손수식·주체/날짜역할판단, 중재와 수정재검토, 경로/단계혼동·잘린출력·이미끝난요청의재등장이 실제재작업을 만들었다. 총괄의준비기이름충돌·잘못된단계후보대조도 교정비용에 포함한다. 원인별기여율·하드웨어저하·짧은호출도입뒤속도개선율은 측정하지 않았다.

공식cache3의원래HOLD460,695위치중350,522처리/110,173잔여는 그대로다. 새리뷰·13개보완·세필드HOLD와경고390/585경로연결을 새채택·의미PASS·HOLD감소로 선반영하지 않는다. 기존경고 미연결195건은 정확기존증거부터 추적하며 자동중복재판독으로 돌리지 않는다.

잔여1차판독66,903건 및 해당독립2차917건, 새본문총괄검토 뒤 새ROOT/roster·전체캐시재생성·독립consumer·전체재계측·정본문서연쇄·최종핸드오프·한국어로컬저장이 남는다. A–E전체전에는 완료/일시중지/추가300M학습승인으로 바꾸지 않는다. 관리goal API의blocked표시와 실제RUN을 구분하며 현재승인대기/외부막힘은없다. 원형·보호TinyDataset·타세션전용자료·GPU/모델/학습·설치/다운로드·push/PR은 변경/실행하지 않았다.

정확 경로/SHA는 같은이름v5 JSON, 개별사례는DELIVERY_MISSING_449324_REPAIR_VERIFIED_V1.json 및 CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V2.json에 연결했다.
'''
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V5.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=1496, first_review_missing=66903,
                     birth_saved=1790, birth_missing=917, input_preconditions=795,
                     current_delivery_failures=0, official_HOLD_unchanged=110173), ensure_ascii=False))
