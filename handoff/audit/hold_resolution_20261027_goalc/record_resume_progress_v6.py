"""Freeze current counts and actual snapshot growth, without cache adoption."""
from pathlib import Path
import ast
import datetime
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
versions = {1: 'v8', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v8', 6: 'v5', 7: 'v1'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
         for page, version in versions.items()}
assert all(not page['errors'] for page in pages.values())
page_counts = {page: sum(role['saved'] for role in value['coverage'].values()) for page, value in pages.items()}
assert sum(page_counts.values()) == 1638
birth_path = BASE / 'birth_root11_independent_v1_snapshots/v24/complete.json'
birth = read(birth_path)
assert not birth['errors'] and sum(row['saved'] for row in birth['coverage'].values()) == 2190
assert set(birth['needs_root']) == {'expanded_train:841018', 'expanded_train:841818'}
delivery_path = BASE / 'birth_root11_input_delivery_gated_v1/v14/complete.json'
delivery = read(delivery_path)
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1195
holds = read(AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V2.json')
raw_field_needs = sorted({ident for page in pages.values() for ident in page['needs_root']})
assert set(raw_field_needs) == {row['id'] for row in holds['rows']}
followup = read(AUDIT / 'EIGHT_MORE_FOLLOWUPS_BYTE_VERIFIED_V1.json')
assert followup['combined_specific_followups'] == 21
field_short = read(AUDIT / 'FIELD_SHORT_READERS_RUNTIME_VERIFIED_V1.json')
assert len(field_short['positive']) == 3 and len(field_short['negative']) == 5
negative = read(AUDIT / 'ROOT_85646_V1_NONADMISSION_V1.json')
assert negative['v2_review_pending'] is True
prior = read(AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V5.json')
growth = []
for version in (22, 23, 24):
    path = BASE / f'birth_root11_independent_v1_snapshots/v{version}/complete.json'
    value = read(path)
    growth.append(dict(version=version, saved=sum(row['saved'] for row in value['coverage'].values()),
                       snapshot_path=str(path.relative_to(ROOT)), mtime_ns=path.stat().st_mtime_ns,
                       mtime_utc=datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc).isoformat()))
rates = []
for before, after in zip(growth, growth[1:]):
    seconds = (after['mtime_ns'] - before['mtime_ns']) / 1_000_000_000
    assert seconds > 0 and after['saved'] >= before['saved']
    rates.append(dict(from_version=before['version'], to_version=after['version'], seconds=seconds,
                      saved_row_increase=after['saved'] - before['saved'],
                      saved_row_increase_per_hour=(after['saved'] - before['saved']) * 3600 / seconds))
for path in (Path(__file__).resolve(), reused):
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
data = dict(status='FULL_CLEANUP_CONTINUES_WITH_CURRENT_SAVED_COUNTS_AND_EXPLICIT_NEGATIVES',
            field_expected=18237, field_saved=1638, field_missing=16599,
            other_first_review_missing=50162, combined_first_review_missing=66761,
            field_versions={str(key): value for key, value in versions.items()}, field_saved_by_page=page_counts,
            field_connection_errors=0, field_raw_needs_root=raw_field_needs,
            field_whole_hold_sources=3, field_whole_hold_positions=6,
            birth_expected=2707, birth_saved=2190, birth_missing=517, birth_by_role=birth['coverage'],
            birth_connection_errors=0, birth_frozen_needs_root=birth['needs_root'],
            birth_pinned_candidates=1880, birth_materialized_candidates=308,
            birth_frozen_nonadmission_adjudications=2,
            birth_cross_id_report_correction='Root pinned-byte check found correct separate packet frames/diffs; author reread and review240_v3 reported, newer collection still required.',
            prospective_delivery_preconditions_verified=1195,
            historical_sources_without_retrospective_emission_claim=995,
            delivery_precondition_failures=0, input_delivery_is_not_semantic_review=True,
            byte_checked_specific_followups=21, pending_in_these_twenty_one=0,
            large_85646_v1_rejected=True, large_85646_v2_received_v3_narrow_fix_requested=True,
            field_short_reader_regression_tests=19, actual_field_reader_roles=3, actual_field_reader_denials=5,
            ordered_flag_linked_record_scopes=390, ordered_flag_unlinked_in_these_scopes=195,
            birth_snapshot_growth=growth, birth_saved_row_growth_rates=rates,
            growth_rate_limits='Same-cohort snapshot row-count growth only, includes saved NEEDS_ROOT rows; not quality/adoption, whole-project throughput, controlled shortcut effect, or hardware diagnosis.',
            earlier_five_hour_saved_review_window=dict(before_per_hour=186.0, after_per_hour=155.4,
                                                       approximate_change_percent=-16.5),
            observed_rework=['long mathematical missing-condition units and author-output rechecks',
                             'missing TASK207 saved review, now author-reread and saved',
                             '740452 diff deletion/addition misread; pinned inputs were equal and body unchanged',
                             '841018/841818 cross-ID report mixing, not a demonstrated packet mutation',
                             'root supplied the birth guide parent path incorrectly; exact prepared-manifest paths corrected',
                             'earlier root checkpoint planner namespace and same-ID stage mistakes retained'],
            official_cache=3, original_hold_positions=460695,
            official_handled_positions=350522, official_hold_positions_unchanged=110173,
            latest_verified_local_commit=prior['latest_verified_local_commit'],
            own_git_window='CLOSED', later_work_has_uncommitted_changes=True,
            goal_management_status='blocked', actual_work_status='RUN',
            approval_wait_or_external_blocker=False, root_or_cache_adoptions_of_new_reviews=0,
            whole_corpus_semantic_pass=False, goal_complete=False, training_authorized=False, input_pins=pins)
target = AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V6.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
text = f'''# 전체 정제 계속 — 실제 저장 증가와 재작업을 구분

다섯 Luna 역할과 총괄은 RUN이다. 공식 cache3의 원래HOLD460,695위치 중350,522처리/110,173잔여는 유지한다. 새 리뷰의 저장과 본문 검산을 캐시 채택 감소량으로 선반영하지 않는다.

| 단계 | 동결 저장량 | 해당 단계 미저장 |
|---|---|---|
| 필드·제목 1차 |1,638/18,237고유원문, 연결오류0|16,599고유원문|
| 다른유형 1차 |50,162고유원문의 전량 입력·큐 준비|50,162고유원문|
| 생년·사망일 독립2차 |2,190/2,707고유원문, 연결오류0|517고유원문|

1차 리뷰 미저장은66,761고유원문이다. 독립2차517건과 합쳐 고유원문으로 세지 않는다. 보호1건은 별도 계약이다. 필드는page001v8=308/002v8=307/003v6=309/004v12=310/005v8=277/006v5=102/007v1=25로 동결했다. 실제 역할은 이후 TASK도 계속한다. 생년snapshot24는C1,220/L970이고 본문 입력연결1,880/새본문308/중재행2이다.

field 원시중재행49092/50689/56714는 개별전체HOLD3원문/6위치 원장과 연결한다. 85646의 수식 글은 원문52,391자·v1선택32,157자와sidecar를 총괄이 실제 전량 대조했고, 누락 조건을 지운 알고리즘·새 변수귀속·단위/기준 손실을 찾아v1을채택하지않았다. v2의일곱보완을대조한뒤chebwin길이기호와sidecar인용구분만v3로마감하도록전달했다. 큰 문서 전체를 일괄HOLD한 것이 아니다.

새8개625422/56462/511882/367209/58381/82044/83431/740452의 지정 수정과 바깥바이트를 검산했다. 기존13개와합쳐21개 명시 후속 범위의미결0이다. 83431 총괄의본문출력일부는잘렸으므로전문판독이라고쓰지않고실제모든변경/문맥/EOF와바깥바이트검산범위를적었다. 전체새본문 검토/채택 완료를 뜻하지 않는다.

740452의 후보·초기사본·packet candidate는바이트가같았다. 긴diff의삭제행과추가행은문단통째삭제/복구가아니라빈괄호변경이었고리뷰주장을철회했다. 생년TASK207의저장리뷰5행누락은해당입력만실제로재확인하고저장했다. 동결snapshot24에는841018/841818의중재2행이남지만총괄은두ID의원형/후보/packet frame과diff가각각정상임을확인했다. 앞보고가두ID의내용을섞었으며작성자의실제4패킷재확인과review240_v3완료보고를회수했다. 최신선택으로닫는다음수집은별도다.

birth-gated v14는1,195행의정확패킷전달이리뷰저장보다앞섬을확인했고실패0/원시연결오류0이다. 과거995범위에없던전달시각을소급하지않으며전달기록을이해·의미통과로보지않는다. field세역할의짧은호출도기존helper를재사용해CPU19회귀·실제3역할호출·거부5를검증했다. 완료원문을도구때문에재독하지않는다.

속도는 계속 같은 방향으로 변했다고 단정할 수 없다. 이전약5시간창의저장률186.0→155.4건/시간은약16.5%감소였다. 같은생년묶음의최근snapshot22→23은{rates[0]['saved_row_increase_per_hour']:.1f}행/시간,23→24는{rates[1]['saved_row_increase_per_hour']:.1f}행/시간으로저장증가율이회복됐다. 이는수집파일mtime간누적행증가이며중재행을포함한다. 전체프로젝트처리속도·품질·캐시채택률이나짧은호출의인과효과를측정한것이아니다. 남은위치당원본토큰ID평균은원래HOLD의약1.73배였고긴학술문서·조건/주체판단·보완재검토가실제비용을만든다. 경로오타·출력잘림·기록누락·ID혼동과총괄의준비기/단계/안내서경로실수도재작업에포함한다. 원인별기여율과하드웨어저하는확인하지않았다.

한국어로컬5959b15f커밋의692명시경로/10,209,312바이트검산은끝났고Git창은닫혀있다. 그뒤코드·검산·리뷰와현재문서변경은계속진행중이다. 남은전량판독·보완본문총괄검토·새ROOT/roster·캐시재생성·독립consumer·전체재계측·필요정본·최종핸드오프·한국어로컬저장을마칠때까지A–E완료/일시중지/추가300M학습승인으로바꾸지않는다. 보호원형·TinyDataset·타세션전용자료·GPU/모델/학습·설치/다운로드·push/PR은진행하지않았다.
'''
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V6.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=1638, first_review_missing=66761,
                     birth_saved=2190, birth_missing=517, frozen_birth_needs_root=2,
                     recent_birth_row_growth_per_hour=[round(row['saved_row_increase_per_hour'], 1) for row in rates],
                     official_HOLD_unchanged=110173), ensure_ascii=False))
