"""Freeze current coverage and scoped followup evidence without cache promotion."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}
reused = AUDIT / 'record_resume_progress_v8.py'
nodes = [node for node in ast.parse(reused.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name == 'read']
assert len(nodes) == 1
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(reused), 'exec'), globals())
versions = {1: 'v18', 2: 'v9', 3: 'v6', 4: 'v13', 5: 'v9', 6: 'v14', 7: 'v9', 8: 'v7'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
         for page, version in versions.items()}
assert all(not value['errors'] for value in pages.values())
counts = {page: sum(row['saved'] for row in value['coverage'].values()) for page, value in pages.items()}
assert counts == {1: 499, 2: 327, 3: 309, 4: 310, 5: 307, 6: 308, 7: 172, 8: 100}
saved = sum(counts.values())
assert saved == 2332
needs = sorted({ident for value in pages.values() for ident in value['needs_root']})
whole = read(AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V3.json')
assert set(needs) == {row['id'] for row in whole['rows']} and len(needs) == 4
three = read(AUDIT / 'ROOT_THREE_FIELD_NARROW_FOLLOWUPS_VERIFIED_V1.json')
two = read(AUDIT / 'ROOT_TWO_FIELD_CODE_FOLLOWUPS_VERIFIED_V1.json')
repairs = three['rows'] + two['records']
assert len(repairs) == len({row['id'] for row in repairs}) == 5
bound = {}
for page in (4, 6):
    for shard in pages[page]['shards']:
        value = read(ROOT / shard['path'])
        rows = value if isinstance(value, list) else value.get('rows', value.get('records'))
        for row in rows:
            if row.get('id') in {item['id'] for item in repairs}:
                bound[row['id']] = row
for repair in repairs:
    row = bound[repair['id']]
    assert row['original'] == repair['original']
    assert row['author_output'] == repair['body']
    assert row['review']['path'] == repair['review']['path']
    assert row['review']['sha256'] == repair['review']['sha256']
    assert not row['root_approved'] and not row['cache_admitted']
styles = read(AUDIT / 'FIELD_FOUR_LITERAL_STYLE_CONTEXT_ADJUDICATIONS_V1.json')
assert len(styles['records']) == 4 and styles['automatic_waivers'] == 0
language = read(AUDIT / 'FIELD_BOUND_HANGUL_ADDITION_SCREEN_OBSERVATION_V1.json')
assert language['frozen_body_pairs_checked'] == 2220
assert language['original_without_hangul_to_body_with_hangul'] == 0
diagnostic = read(AUDIT / 'FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json')
assert diagnostic['saved_review_rows'] == 2224 and diagnostic['body_pairs_checked'] == 2220
numeric = read(AUDIT / 'FIELD_BOUND_NUMERIC_LOCAL_PROOFS_V1.json')
lineage = read(AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_INDEPENDENT_VERIFIED_V4.json')
birth = read(BASE / 'birth_root11_independent_v1_snapshots/v30/complete.json')
delivery = read(BASE / 'birth_root11_input_delivery_gated_v1/v20/complete.json')
assert not birth['errors'] and not birth['needs_root'] and not delivery['failures']
assert sum(row['saved'] for row in birth['coverage'].values()) == 2707
read(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V15_INDEPENDENT_VERIFIED.json')
data = dict(status='WHOLE_QUEUE_RUNNING_2332_FIELD_REVIEWS_FIVE_BOUNDED_REPAIRS_BOUND',
            recorded_at=datetime.now(timezone.utc).isoformat(),
            official_original_HOLD_positions=460695,
            official_processed_original_HOLD_positions=350522,
            official_remaining_HOLD_positions=110173, new_reviews_in_official_HOLD_delta=0,
            literal_first_review_unique=1793, literal_positions=2597,
            field_expected_unique=18237, field_saved=saved, field_missing=18237-saved,
            field_versions=versions, field_saved_by_page=counts,
            field_review_binding_errors=0, field_raw_needs_root=needs,
            individually_adjudicated_field_whole_HOLD_unique=4,
            individually_adjudicated_field_whole_HOLD_positions=8,
            other_types_expected_unique=50162, other_types_first_reviews_saved=0,
            first_review_saved_in_literal_and_field_partitions=1793+saved,
            combined_first_review_missing=18237-saved+50162,
            field_saved_delta_from_v12=169,
            field_saved_delta_from_2224_diagnostic_snapshot=108,
            verified_five_followups_bound_to_current_snapshots=sorted(bound),
            scoped_style_unicode_contexts_adjudicated=4,
            separate_missing_title_and_condition_punctuation_followups_not_closed_here=['653', '11993', '13582', '60130'],
            five_roles_authoring_next_queues=True,
            diagnostics_saved_review_rows=2224, diagnostic_body_pairs=2220,
            diagnostics_are_not_latest_2332_body_semantic_pass=True,
            numeric_local_proof_exact_atoms=13, numeric_context_required_atoms=412,
            generic_guards_changed=False, automatic_waivers=0,
            birth_saved=2707, birth_missing=0, birth_raw_snapshot='v30', birth_delivery_snapshot='v20',
            independent_birth_stage_not_added_to_first_review_unique_count=True,
            prospective_delivery_preconditions_verified=1712,
            historical_delivery_timestamps_not_retrofilled=995,
            ordered_flag_linked_record_scopes=468, ordered_flag_unlinked_in_these_scopes=117,
            root_authored_corpus_bodies=0, new_root_or_cache_admissions=0,
            latest_verified_local_commit='9af1110cb20932e0310d0283430f29bd6b22941e',
            own_git_window='CLOSED', later_work_has_uncommitted_changes=True,
            all_five_roles_and_root='RUN', source_wide_fact_or_semantic_pass=False,
            new_speed_effect_not_measured=True, hardware_slowdown_not_established=True,
            whole_goal_complete=False, training_authorized=False, input_pins=pins)
for path in (reused, Path(__file__).resolve()):
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V13.json').open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
text = '''# 전체 정제 계속과 현재 진행량

전체 정제와 다섯 Luna 역할은 RUN이다. 공식 cache3은 최초 HOLD 460,695개 위치 중 350,522개 처리, 110,173개 잔여다. 새 검토를 공식 감소량에 미리 더하지 않는다.

| 단계 | 고정 저장·원문 연결 | 해당 단계 미저장 |
|---|---:|---:|
| 코드·수식 등 literal 1차 | 1,793고유 / 2,597위치 | 0 |
| 필드·제목 1차 | 2,332 / 18,237고유 | 15,905 |
| 다른 유형 1차 | 전량 입력과 큐 준비 | 50,162 |
| 생년·사망일 독립 2차 | 2,707 / 2,707고유 | 0 |

1차 미저장은 66,067고유다. 생년 독립 2차와 합산하지 않는다. 필드 고정본은 001v18=499, 002v9=327, 003v6=309, 004v13=310, 005v9=307, 006v14=308, 007v9=172, 008v7=100이며 연결 오류는 0이다. V12의 2,163개보다 169개, 본문 진단 당시 2,224개보다 108개 늘었다. 작성 중인 새 파일은 이 수에 포함하지 않았다.

29112의 근거 없는 소수 결합, 33415의 소절 범위 뒤 각주 숫자 결합, 85646의 빠진 목적어에 M-1을 배정한 문장, 47905의 실제 필드값 복구와 혼합 언어 제목, 41069의 실제 할당·호출 보존과 누락 그림 위치 표현을 각 작성 역할이 보완했다. 총괄은 지정된 차이 밖 바이트와 EOF, 나머지 리뷰 행, 실제 원형과 선택된 본문/리뷰 SHA를 검산하고 새 고정본 연결까지 확인했다. 이는 다섯 좁은 보완 범위의 검산이며 코드 실행이나 문서 전체 의미 통과, 자동 캐시 채택이 아니다.

Unicode 한 곳과 스타일 세 곳은 실제 문맥을 확인했다. 비어 있는 U+FFFD 글리프 자리의 구분기호, 내용이 남은 색상 태그, 각 책 바로 아래에 남은 정렬 설명, 값 없는 표의 정렬 구문을 구분했으며 검출기를 완화하지 않았다. 60130의 별도 제목 결손 서지 행은 후속 HOLD를 요청했으므로 스타일 판단으로 승인하지 않는다. 653의 비영 상수 조건, 13582의 질량중심 기준, 11993의 고립 인용부호도 좁은 보완/검산 대상이다. 완료된 원문의 전량 재독을 요구하지 않는다.

기존 본문 진단은 2,224리뷰에 연결된 2,220본문과 본문 없는 개별 전체 HOLD 4건을 대상으로 했다. UTF-8 2,220건 유효, 검수 메모 신호 0, 끝 LF 추가 958건을 실제 바이트로 기록했다. 숫자 79문서/425원자, 코드 3, Unicode 1, 스타일 3, 순서 302 신호는 오류 확정이 아니다. 기존 숫자 국소 증명 13원자와 문맥 필요 412원자를 유지한다. 2,220쌍에서 '원문에 한글이 없는데 새 본문에 한글이 생긴 경우'를 좁게 검사해 0을 관측했지만, 고정 이후 47905 중간 v3는 그 검사 대상 밖이었고 별도 v4에서 보완했다. 이를 2,332개 전체의 의미·언어 통과라고 쓰지 않는다.

속도는 기존 5시간 관측에서 시간당 186.0→155.4건으로 약 16.5% 감소했다. 문서 길이·난도·작업자 수를 통제한 비교가 아니며, 별도 생년 창의 361.1→432.1행/시간과도 구분한다. 긴 수식·표의 빠진 조건/주체 판단, 입력 잘림·경로 혼동·미완 파일 선언, 총괄의 안내·도구·검증 가정 오류로 재작업이 발생했다. 원인별 비중이나 하드웨어 성능 저하는 확인되지 않았다. 채택과 캐시 재생성 전에는 공식 HOLD가 움직이지 않는 집계 지연도 있다. 짧은 기존 reader 호출, 원형 동일 초기 사본, 기존 판단의 반복 적용, 필요한 문맥과 변경분만 재확인하는 방식으로 불필요한 작업을 줄이고 있으나 효과를 아직 계측하지 않았다.

구 진단 계보는 468/585범위 연결, 117범위 미연결이다. 과거 SHA·시각을 소급하지 않고, 재생성 근거와 실제 새 판독을 구분한다. 생년30/gated20, 34개 문맥과 기존 후속, 개별 전체 HOLD 4원문/8위치의 판단은 해당 범위로 유지한다.

최근 검증된 한국어 로컬 커밋은 9af1110c의 599경로다. 이후 산출물은 미커밋이며 새 V16의 명시 목록으로 저장할 예정이다. 전량 판독과 총괄 의미 검토, ROOT/roster, 최종 별도 캐시/독립 consumer, 전체 재계측, 필요한 정본과 최종 핸드오프·저장이 남아 있다. 중간 저장 뒤에도 작업을 계속하며 A–E 완료·일시중지·학습 승인으로 바꾸지 않는다. 원형·기존 캐시·보호 자료·다른 세션의 작업·GPU/모델/학습·push/PR은 변경하지 않았다.
'''
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V13.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=saved,
                     first_review_missing=data['combined_first_review_missing'],
                     binding_errors=0, bounded_repairs_bound=5,
                     official_HOLD_unchanged=110173), ensure_ascii=False))
