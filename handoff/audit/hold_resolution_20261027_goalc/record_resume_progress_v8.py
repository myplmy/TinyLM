"""Freeze post-save progress without treating saved reviews as cache admission."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}


def read(path):
    assert not path.is_symlink()
    assert path.resolve().is_relative_to(AUDIT) or path.resolve().is_relative_to(BASE)
    payload = path.read_bytes()
    assert 0 < len(payload) < 20_000_000
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest().upper()
    return json.loads(payload)


previous = read(AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V7.json')
versions = {1: 'v9', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v9', 6: 'v7', 7: 'v3'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
         for page, version in versions.items()}
page_counts = {page: sum(row['saved'] for row in value['coverage'].values()) for page, value in pages.items()}
assert sum(page_counts.values()) == 1798 and all(not value['errors'] for value in pages.values())
needs = sorted({ident for value in pages.values() for ident in value['needs_root']})
assert set(needs) == {'expanded_train:49092', 'expanded_train:50689', 'expanded_train:56714'}
birth = read(BASE / 'birth_root11_independent_v1_snapshots/v26/complete.json')
assert not birth['errors'] and not birth['needs_root']
assert birth['coverage']['context_controls'] == dict(expected=1354, saved=1354, awaiting_review=0)
assert birth['coverage']['context_latin'] == dict(expected=1353, saved=1235, awaiting_review=118)
delivery = read(BASE / 'birth_root11_input_delivery_gated_v1/v16/complete.json')
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1594
commit = read(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V13.json')
assert commit['commit'] == '861ff714e6a4387876dc4b8c7eb7debe3d020394'
assert commit['expected_paths'] == 1748 and commit['remaining_shared_index_count'] == 0
assert commit['whole_changed_path_set_exact'] and commit['all_committed_bytes_match']
data = dict(previous)
data.update(status='FULL_QUEUE_RUNNING_POST_LOCAL_SAVE_SNAPSHOT',
            recorded_at=datetime.now(timezone.utc).isoformat(),
            field_saved=1798, field_missing=16439, combined_first_review_missing=66601,
            field_versions={str(page): version for page, version in versions.items()},
            field_saved_by_page=page_counts, field_frozen_needs_root=needs,
            field_frozen_followup_rows=[], latest_followup_review_collection_separate=False,
            field_72884_and_111797_latest_saved_selections_bound=True,
            these_two_new_bodies_root_semantic_review_complete=False,
            birth_saved=2589, birth_missing=118, birth_by_role=birth['coverage'],
            birth_pinned_candidates=2227, birth_materialized_candidates=362,
            prospective_delivery_preconditions_verified=1594,
            latest_verified_local_commit=commit['commit'],
            latest_verified_local_save_paths=1748,
            own_git_window='CLOSED', later_work_has_uncommitted_changes=True,
            prior_progress_report='RESUME_PROGRESS_AND_SPEED_20261104_V7.json',
            input_pins=pins)
pins[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V8.json').open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
text = '''# 전체 정제 계속 — 중간 저장 뒤 판독 진척

전체 작업과 다섯 역할은 RUN이다. 공식 cache3은 원래 HOLD 460,695위치 중 350,522처리 / 110,173잔여로 그대로다. 아래 새 리뷰 저장량은 캐시 채택 감소량에 포함하지 않는다.

| 단계 | 실제 저장·연결 | 해당 단계 미저장 |
|---|---:|---:|
| 필드·제목 1차 | 1,798 / 18,237 고유원문 | 16,439 |
| 다른 유형 1차 | 50,162 고유원문의 전체 입력·큐 준비 | 50,162 |
| 생년·사망일 독립 2차 | 2,589 / 2,707 고유원문 | 118 |

1차 미저장은 66,601고유원문이다. 이 수와 독립 2차 118건을 고유원문 수로 합산하지 않는다. 각 단계의 연결 오류는 0이다. field 동결은 001v9=313 / 002v8=307 / 003v6=309 / 004v12=310 / 005v9=307 / 006v7=172 / 007v3=80이다. 생년 snapshot26은 C1354 / L1235이며 C는 배정 완료 뒤 field001로 이동했다. L은 자기 TASK271의 마지막 세 행까지 마치고 field로 간다. H는 field007, historical·legacy는 field006을 이어간다.

72884와111797의 최신 리뷰 선택은 이번 field006v7/007v3에 연결됐고 해당 NEEDS_ROOT 행은 없어졌다. 이는 두 새 본문의 총괄 의미 검토나 캐시 채택 완료를 뜻하지 않는다. 남은 field 원시중재 49092/50689/56714는 이미 개별 전체 HOLD 3원문/6위치 원장에 연결한 사례다. 전량 미판독 자료를 이 사례처럼 일괄 HOLD로 마감하지 않는다.

별도 gated16은 1,594행의 입력 전달 선결/실패0을 확인했다. 과거995범위의 전달 시각은 소급하지 않는다. 전달 출력·저장·해시 일치만으로 이해나 의미 통과를 주장하지 않는다. 기존 명시22보완의 범위 검산은 유지하며 신규 본문은 따로 검토한다.

속도에는 세 가지를 구분해야 한다. 공식 H 수는 새 리뷰를 검토·선택하고 캐시를 재생성하기 전까지 줄지 않는다. 빠른 빈 표제 처리 뒤에 긴 수학·기호 결손 문서가 남았고, 삭제할 최소 단위와 남길 조건·주체를 판정하는 시간이 든다. 입력 ID/경로 혼동, 저장 누락과 잘린 초안, 총괄의 준비기·단계·안내 경로 오류도 실제 재작업을 만들었다. 총괄 측 오류 역시 기록해 바로잡았다.

이전 보고의 5시간 저장률 186.0→155.4건/시간 약16.5%감소와 최근 생년의361.1→432.1행/시간 증가는 서로 다른 창의 관측이다. 이제 생년 작업자가 둘에서 하나로 바뀌었으므로 생년만의 성장률을 팀 전체 속도로 읽을 수 없다. 문서 길이·단계·작업자 수를 통제한 인과 실험이 없으며 하드웨어 저하, 요인별 기여율, 단축 호출의 인과 효과는 확인하지 않았다. 일정 추정에도 같은 한계가 있다.

한국어 로컬 커밋861ff714e6a4387876dc4b8c7eb7debe3d020394은 부모5959b15f에서 명시1,748경로/16,201,097바이트를 저장했다. 전체 변경 경로·부모·모든blob·파일SHA와 저장 범위 미반영0/index0을 독립 재검산했다. Git창은 닫았으며 이후 수집·원장 갱신은 새 미커밋 작업이다. 원형·대량본문/캐시·보호TinyDataset·타세션dirty flag는 저장 목록에서 제외했다. push/PR은0이다.

남은 작업은 전량 판독과 새 본문·보류 sidecar의 의미 보존 검토, 구 flag195의 정확 소유 계보 추적, 새 ROOT/roster와 캐시 재생성·독립consumer·전체 재계측, 필요한 정본·최종 핸드오프·한국어 로컬 저장이다. A–E 전체를 충족하기 전에는 완료·일시중지·학습 승인으로 바꾸지 않는다. GPU·모델·학습·설치·다운로드는 실행하지 않았다.
'''
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V8.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=1798, first_review_missing=66601,
                     birth_saved=2589, birth_missing=118, official_HOLD_unchanged=110173,
                     latest_local_commit=commit['commit']), ensure_ascii=False))
