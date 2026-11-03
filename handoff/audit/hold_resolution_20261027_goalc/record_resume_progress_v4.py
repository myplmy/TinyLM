"""Freeze stage counts and honest remaining work without changing corpus state."""
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


def saved(snapshot):
    return sum(role['saved'] for role in snapshot['coverage'].values())


versions = {1: 'v8', 2: 'v8', 3: 'v6', 4: 'v10', 5: 'v5', 6: 'v3'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' /
                    version / 'complete.json') for page, version in versions.items()}
assert all(not page['errors'] for page in pages.values())
field_saved = sum(map(saved, pages.values()))
assert field_saved == 1382
field_missing = 18237 - field_saved
other_missing = 50162
literal = read(BASE / 'remaining_literal_full_counter_v1_snapshots/v20/complete.json')
literal_holds = read(AUDIT / 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V3.json')
prior_terminal_holds = read(AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD37_V1.json')
assert literal['expected'] == saved(literal) == 1793 and not literal['errors']
prior_literal_hold = {row['id'] for row in prior_terminal_holds['rows'] if row['id'] == 'expanded_train:1046282'}
assert prior_literal_hold == {'expanded_train:1046282'}
assert set(literal['needs_root']) == {row['id'] for row in literal_holds['rows']} | prior_literal_hold
assert len(literal['needs_root']) == 10
birth = read(BASE / 'birth_root11_independent_v1_snapshots/v20/complete.json')
assert saved(birth) == 1440 and not birth['errors'] and not birth['needs_root']
delivery = read(BASE / 'birth_root11_input_delivery_gated_v1/v10/complete.json')
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 445
field_holds = read(AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V1.json')
raw_field_needs = {ident for page in pages.values() for ident in page['needs_root']}
assert raw_field_needs == {row['id'] for row in field_holds['rows']}
followups = [read(AUDIT / name) for name in (
    'CURRENT_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json',
    'ADDITIONAL_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json',
    'CURRENT_FIELD_AND_BIRTH_FOLLOWUP_ADJUDICATIONS_V1.json')]
followup_ids = [row['id'] for result in followups for row in result['rows']]
assert len(followup_ids) == len(set(followup_ids)) == 12
assert all(row['unchanged_bytes_outside_allowed_edits_verified'] for result in followups for row in result['rows'])
chain = read(AUDIT / 'RUNTIME_PRIOR_REVIEW_OUTPUT_CHAIN_V1.json')
assert chain['linked_flag_sources_in_these_scopes'] == 390 and chain['not_linked_in_these_scopes'] == 195
guard = read(AUDIT / 'BIRTH_REJECTED_ROW_GUARD_RUNTIME_EVIDENCE_V1.json')
assert guard['cpu_test_count'] == 28 and guard['cpu_test_exit_code'] == 0
pins[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
data = dict(status='CONTINUING_WHOLE_CLEANUP_NOT_A_COMPLETION_OR_PAUSE',
            official_cache_version=3, original_hold_positions=460695,
            official_handled_positions=350522, official_remaining_hold_positions=110173,
            official_hold_reduction_percent=round(350522 / 460695 * 100, 2),
            literal_first_review_saved=1793, literal_body_candidates=1783,
            literal_individually_adjudicated_whole_holds=10,
            field_first_review_saved=field_saved, field_first_review_expected=18237,
            field_first_review_missing=field_missing, other_first_review_missing=other_missing,
            combined_first_review_missing=field_missing + other_missing,
            field_snapshot_versions={str(page): version for page, version in versions.items()},
            field_saved_by_page={str(page): saved(snapshot) for page, snapshot in pages.items()},
            field_raw_needs_root=sorted(raw_field_needs),
            field_raw_needs_root_individually_adjudicated=sorted(raw_field_needs),
            birth_independent_second_saved=1440, birth_independent_second_expected=2707,
            birth_independent_second_missing=1267, birth_saved_by_role=birth['coverage'],
            birth_materialized_candidates=194, birth_pinned_candidates=1246,
            prospective_delivery_precondition_verified_rows=445,
            historical_rows_without_retrospective_emission_claim=995,
            birth_connection_errors=0, birth_snapshot_needs_root=0,
            explicit_root_followup_ids=followup_ids, explicit_known_followups_pending=0,
            ordered_flag_linked_record_scopes=390, ordered_flag_not_linked_in_these_scopes=195,
            cpu_guard_regression_test_count=28, cpu_guard_regression_test_failures=0,
            latest_verified_local_commit='2f811836774ababf680c5d64a0f6c8825280935c',
            latest_commit_paths=1097, latest_commit_bytes=9363142,
            following_changes_are_in_progress_and_not_all_committed=True,
            goal_management_status_observed='blocked', actual_work_status='RUN',
            approval_wait_or_external_blocker=False, root_or_cache_adoptions_of_new_reviews=0,
            whole_corpus_semantic_review_complete=False, goal_complete=False,
            training_authorized=False, input_pins=pins)
target = AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V4.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
text = f'''# 전체 정제 진행과 속도 관측 — 2026-11-04 v4

전체 정제는 다섯 역할과 계속 수행 중이다. 중간 저장이나 이 보고를 완료·일시중지로 처리하지 않는다. 최신 검산된 로컬 커밋은 `2f811836774ababf680c5d64a0f6c8825280935c`(1,097명시 경로, 9,363,142바이트)이며 그 뒤 새 판독·보완·검증은 진행 중이다.

공식 cache3에서 원래 HOLD 460,695위치 중 350,522위치를 처리했고 110,173위치가 남는다. 76.09% 감소는 보존·수정·제외를 합친 처리량이며 품질 합격률이 아니다. 아래 새 리뷰를 아직 새 ROOT·roster·전체 캐시에 채택하지 않았으므로 공식 HOLD가 그만큼 더 줄었다고 말하지 않는다.

| 단계 | 이번 고정 집계 | 같은 단계의 잔여 |
|---|---|---|
| 코드·수식 1차 | 1,793고유원문/2,597위치: 본문후보 1,783, 개별 판독 HOLD 10 | 이 단계 연결 오류·미처리 중재 0; 최종 채택 별도 |
| 필드·제목 1차 | 1,382/18,237고유원문, 연결 오류 0 | 16,855고유원문의 리뷰 미저장 |
| 다른 유형 1차 | 50,162고유원문의 입력·전량 큐 준비 | 전량 리뷰 미저장 |
| 생년·사망일 묶음 독립 2차 | 1,440/2,707고유원문, 연결 오류·동결 중재 대기 0 | 1,267고유원문의 리뷰 미저장 |

1차 리뷰 미저장은 16,855+50,162=67,017고유원문이며, 보호 1건은 별도 메타데이터 계약이다. 독립 2차 1,267건을 이 1차 잔여와 고유원문 수로 더하지 않는다. 필드 고정본은 page001v8=308, 002v8=307, 003v6=309, 004v10=306, 005v5=112, 006v3=40이다. 생년 묶음 snapshot20은 controls800/Latin640, 입력 연결1,246/새 본문194다. 역할들은 이 동결본 뒤의 정확 다음 TASK도 계속 수행한다.

필드의 원시 리뷰에는 49092/50689 두 NEEDS_ROOT 행이 남아 있으나, `CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V1.json`에서 개별 HOLD 판정을 연결했다. 49092는 이종 항목의 광범위한 혼입, 50689는 핵심 글리프와 남은 필드의 귀속 소실 때문이다. 두 고유원문은 4위치에 해당하며 아직 새 roster에 합류하지 않았다. 49092의 총괄 판독은 대표 연속 구간과 노트 전문이며 원문 전량 판독을 주장하지 않는다. Luna의 전량 판독과 구분한다. `carrying/current/infinite`의 패킷 분할은 원문 손상 근거에서 철회했다.

기존 8개와 새 4개(35700/292732/47644/48362)의 알려진 보완은 새 본문·변경 문맥·EOF·sidecar와 허용 변경 밖 바이트까지 대조해 마감했다. 12개 ID는 서로 겹치지 않는다. 47644는 단위가 없는 질량값/직접 비교와 누락 수식에 매인 BE 조건을 보류하고, 실제 단위가 있는 범위·독립 천체명·가설/미확인 표현을 보존했다. 48362는 실제 모델 변수/조건부 결과를 복원해 유지하고 빈 수식·지시 대상·상충 임계절·다운로드 UI만 분리했다. 문서 전체의 과학적 사실 검증이나 새 ROOT 채택을 뜻하지 않는다.

입력 전달의 별도 gated뷰v10은 리뷰 저장 전에 지정 패킷이 모두 출력된 445행을 확인했고 실패0이다. 과거995개 범위에는 없던 시각 증거를 소급하지 않는다. 전달 기록은 이해·인증·의미 검토 통과가 아니다. 원시 snapshot18의 잘못된 출력 경로2건을 기존 검증기가 읽다 멈춘 문제는 새 v3 진입점에서 격리하도록 고쳤다. 실제 음성 스냅샷의 두 행에는 본문 참조가 남지 않고, 경로를 바로잡은 snapshot20은 원시 오류0/전달 실패0이다. CPU 회귀28건을 통과했으며, 초기 CLI 구문 오류와 그 정정도 별도 근거에 남겼다.

585개 순서 변경 경고에 대한 기존 경로 연결은 385개에서390개로 늘었다. runtime manifest가 봉인한 이전 preview에서 정확 작성자리뷰와 출력SHA 5개를 찾아, 총괄 결정노트를 작성자리뷰로 오인하지 않고 이전/현재 두 역할의 연결을 검산했다. 이번 기록 범위 미연결은195개다. 이 수는 새 의미 검토 통과·경고 면제·HOLD 감소가 아니다. 남은 경로는 기존 정확 증거부터 추적하며 자동 중복 재판독으로 돌리지 않는다.

속도 저하의 수치 근거는 이전 연속 약5시간창의 새 리뷰 저장률 186.0→155.4건/시간(약16.5% 감소)이다. 문서 길이와 난도를 통제한 생산성 측정은 아니다. 남은 원형 위치당 토큰ID 평균은 원래 HOLD 평균의 약1.73배였고, 현재 큐에는 긴 문서와 수식·조건·주체 결손이 많다. 중재 집중, 같은 규칙 재문의, 경로/리뷰번호 오기, 잘린 출력 재독과 수정본 반복 확인도 실제 재작업을 만들었다. 압축 뒤 이미 완료한 요청이 다시 등장한 35700은 완료 근거를 확인해 재작업하지 않도록 했다. 각 원인의 지연 기여율·하드웨어 저하·조치 이후 개선율은 측정하지 않았다.

잔여 67,017건의 1차 판독과 1,267건의 해당 독립2차, 새 보완 결과의 총괄 검토가 끝나야 다음 채택 범위를 확정할 수 있다. 이후 새 ROOT·roster, 전체 캐시 재생성, 독립 consumer, 전체 재계측, 정본 문서 연쇄·최종 핸드오프·한국어 로컬 저장이 남는다. 문서 난도 차이가 커 현재 리뷰 저장률만으로 완료 시각을 확정할 수 없다. A–E 전체가 충족되기 전에는 목표 완료나 추가300M 학습 승인으로 바꾸지 않는다.

관리 goal API의 blocked 표시는 남아 있으나 실제 작업은RUN이며 승인 대기/외부 막힘은 없다. GPU·모델·학습·설치/다운로드·보호 TinyDataset·타 세션 전용자료·원형 덮기/삭제·push/PR은 수행하지 않았다. 정확 snapshot·감사 근거의 경로와 SHA는 같은 이름의 v4 JSON에 연결했다.
'''
report_path = AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V4.md'
with report_path.open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=field_saved,
                     first_review_missing=field_missing + other_missing, birth_saved=1440,
                     birth_missing=1267, known_followups_pending=0,
                     official_hold_unchanged=110173), ensure_ascii=False))
