"""Record new frozen review coverage, preserving rejected intermediate states."""
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
prior = read(AUDIT / 'POST_V11_SCOPE_DELTA_V1.json')
versions = {1: 'v16', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v9', 6: 'v12', 7: 'v7', 8: 'v5'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
         for page, version in versions.items()}
assert all(not value['errors'] for value in pages.values())
counts = {page: sum(row['saved'] for row in value['coverage'].values()) for page, value in pages.items()}
assert counts == {1: 453, 2: 307, 3: 309, 4: 310, 5: 307, 6: 285, 7: 127, 8: 65}
saved = sum(counts.values())
assert saved == 2163 and saved - prior['field_saved_frozen'] == 90
missing = 18237 - saved + 50162
assert missing == 66236
needs = sorted({ident for value in pages.values() for ident in value['needs_root']})
whole = read(AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V3.json')
assert set(needs) == {row['id'] for row in whole['rows']} and len(needs) == 4
negative = read(BASE / 'remaining_field_title_page_001_counter_v1_snapshots/v15/complete.json')
assert len(negative['errors']) == 2
assert {row['id'] for row in negative['errors']} == {'expanded_train:5274', 'expanded_train:5292'}
read(AUDIT / 'FIELD001_V15_MISSING_OUTPUT_OBSERVATION_V1.json')
lf = read(AUDIT / 'ROOT_TWO_FIELD_TERMINAL_LF_VERIFIED_V1.json')
assert lf['specific_followup_pending'] == 0 and len(lf['records']) == 2
assert all(row['terminal_lf_added'] == 1 and row['all_other_body_bytes_unchanged'] for row in lf['records'])
birth = read(BASE / 'birth_root11_independent_v1_snapshots/v30/complete.json')
assert not birth['errors'] and not birth['needs_root']
assert sum(row['saved'] for row in birth['coverage'].values()) == 2707
delivery = read(BASE / 'birth_root11_input_delivery_gated_v1/v20/complete.json')
assert not delivery['failures'] and delivery['raw_errors'] == 0
data = dict(status='WHOLE_QUEUE_RUNNING_NEW_FIELD_COVERAGE_AND_TERMINAL_LF_SCOPES_VERIFIED',
            recorded_at=datetime.now(timezone.utc).isoformat(),
            official_original_HOLD_positions=460695, official_processed_original_HOLD_positions=350522,
            official_remaining_HOLD_positions=110173, new_reviews_in_official_HOLD_delta=0,
            literal_first_review_unique=1793, literal_positions=2597,
            literal_candidate_sources=1783, literal_individual_HOLD_sources=10,
            field_expected_unique=18237, field_saved=saved, field_missing=18237-saved,
            field_versions=versions, field_saved_by_page=counts,
            field_review_binding_errors=0, field_raw_needs_root=needs,
            field_individually_adjudicated_whole_HOLD_unique=4,
            field_individually_adjudicated_whole_HOLD_positions=8,
            other_types_expected_unique=50162, other_types_first_reviews_saved=0,
            first_review_saved_in_literal_and_field_partitions=1793+saved,
            combined_first_review_missing=missing,
            field_saved_delta_from_post_v11=90,
            historical_field001_v15_missing_file_rejections_preserved=2,
            later_v16_binding_errors=0, terminal_lf_followups_closed=2,
            terminal_lf_changes_not_byte_identical_eof_claimed=True,
            birth_saved=2707, birth_missing=0, birth_raw_snapshot='v30', birth_delivery_snapshot='v20',
            birth_body_shards_not_rehashed_again_for_this_progress_report=True,
            prospective_delivery_preconditions_verified=1712, historical_delivery_timestamps_not_retrofilled=995,
            ordered_flag_linked_record_scopes=464, ordered_flag_unlinked_in_these_scopes=121,
            all_role_initial_copies_prepared=18237, working_copy_creation_is_not_new_review=True,
            latest_verified_local_commit='2883463c1d3f8b15bcfa3d9ee77a52e466ec6b52',
            own_git_window='CLOSED', later_work_has_uncommitted_changes=True,
            independent_whole_body_semantic_pass_claimed=False,
            all_formatting_in_whole_corpus_claimed_clean=False,
            new_root_or_cache_admissions=0, all_five_roles_and_root='RUN',
            whole_goal_complete=False, training_authorized=False, input_pins=pins)
for path in (reused, Path(__file__).resolve()):
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V12.json').open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
text = '''# 전체 정제 계속과 본문 검토 저장 2163개

전체 정제와 다섯 역할의 전량 큐는 RUN이다. 공식 cache3은 원래 HOLD460695개 위치 중350522개 처리/110173개 잔여이며 새 리뷰를 이 감소량에 미리 반영하지 않는다.

| 단계 | 동결 저장·연결 | 해당 단계 미저장 |
|---|---:|---:|
| 코드·수식 등 literal 1차 | 1793고유/2597위치, 후보1783·개별H10 | 0 |
| 필드·제목 1차 | 2163/18237고유 | 16074 |
| 다른 유형 1차 | 전량 입력과 큐 준비 | 50162 |
| 생년·사망일 독립 2차 | 2707/2707고유 | 0 |

1차 미저장은66236고유다. 생년 독립 2차와 합산하지 않는다. field001v16=453/002v8=307/003v6=309/004v12=310/005v9=307/006v12=285/007v7=127/008v5=65이며 연결 오류0이다. POST_V11 동결의2073에서90개 늘었고, 아직 작성 중인 결과는 제외했다. 원시 중재4ID/8위치는 이미 개별 전체H로 판단한 범위이며 미판독 자료 전체를 같은 이유로 H마감하지 않는다.

field001 v15에서는 review010에 선언한5274/5292의 실제TXT가 아직 없던 상태를 거부2로 보존했다. 역할이 선언된 정확 경로에 본문을 저장한 후 별도v16을 수집해 연결 오류0을 확인했다. 과거 거부와 관측 시각을 지우거나 최초부터 파일이 존재했다고 소급하지 않는다. 5090/5100의 과거 다른TASK에 들어간 무효행도 원형 보존되며 현재 유효 선택과 혼합하지 않는다.

5171/5181 두 원형·새본문 전문/전체diff/sidecar·EOF를 읽고 정확 편집식과 SHA를 검산했다. 빈 병기·내용 없는 구획과 앞 빈줄1개를 정리한 차이 외에는 본문이 불변이고, 두 새TXT에는 끝LF1개가 추가됐다. 마지막 혜공왕/선덕왕 한자와 괄호는 온전하며 UTF8이 유효하다. 비개행EOF 불변이라고 쓰지 않으며, 말미 바이트를 잘라 맞추거나 두 새본문을 다시 작성하지 않는다. 이 특정 범위 미결0은 자동 ROOT/캐시 채택이나 전체 의미 통과가 아니다.

birth30/gated20과 기존34개 문맥 진단·5후속,139681 최종v5 고립파이프,134299의 소실조건식 직접의존 단락H,72884/111797/810478/95554 및 기존22후속 검산은 유지한다. 진행 보고를 위해2707본문을 다시 전량 해시/재독하지 않았다. 전달선결1712행과 과거995시각 한계도 유지한다.

새 중재107244에서는 등급 아이콘이나 공식코드가 비었더라도 실제 연령·부정·보호자 동반 조건과 나라별 목록 문맥이 완전한 설명을 보존하도록 했다. 홍콩의 채워진1/2A/2B/3/예전2등급은 빈 표식만 정리하고, 브라질·아르헨티나·헝가리에 빠진 공식 코드를 순서로 생성하지 않는다. 9794의11939년10월은 오기/각주결합으로 확정할 근거가 없어 시간구를 원형H에 보존하고, 독립적으로 완결한 더블린 거처 관계는 유지하도록 했다. 이는 원문 문맥 중재이며 현재 법령·역사 사실의 외부 검증이나 새 날짜 복원은 아니다. 실제 새 저장물은 후속 검토 전까지 통과로 세지 않는다.

속도 관측은 기존5시간186.0→155.4건/시간, 약16.5% 감소다. 별도 생년창361.1→432.1행/시간과 구분하며 문서길이·작업자수를 통제한 비교가 아니다. 긴 수식/표의 결손 기호·조건·주체 판독, 잘림·입력/경로 혼동과 미완 저장, 총괄의 안내·준비기·검증 가정 오류가 재작업을 만들었다. 원인별 기여율이나 하드웨어 저하는 미확인이다. 공식H는 채택/캐시 재생성 전까지 그대로인 집계 지연도 있다. 재독을 요구하지 않는 좁은 경로 보완, 기존 판단의 역할 자율 적용, 전18237배정 원형동일 초기사본으로 재입력 부담을 줄이고 있으나 속도 효과를 아직 측정하지 않았다.

마지막 검증 로컬 커밋2883463c 이후의 후속·수집·코드·원장은 미커밋이다. 다음 명시 한국어 로컬 저장 후에도 정제와 검증을 계속한다. 구flag계보464/585·미연결121, 전량 큐와 새본문의 총괄 의미 검토, ROOT/roster·별도캐시/독립consumer·전체재계측·필요정본·최종핸드오프/저장이 남는다. 보호자료·원형/기존캐시·타세션dirtyflag·GPU/모델/학습·설치/다운로드·push/PR은 변경하지 않았다. A–E완료·일시중지·학습승인으로 바꾸지 않는다.
'''
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V12.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=saved, first_review_missing=missing,
                     binding_errors=0, old_rejections_preserved=2, terminal_lf_scopes_closed=2,
                     official_HOLD_unchanged=110173), ensure_ascii=False))
