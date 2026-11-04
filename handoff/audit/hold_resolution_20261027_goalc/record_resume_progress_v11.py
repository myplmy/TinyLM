"""Freeze newly bound followups while retaining the official cache boundary."""
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
read(AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V10.json')
versions = {1: 'v14', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v9', 6: 'v11', 7: 'v6', 8: 'v3'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
         for page, version in versions.items()}
assert all(not value['errors'] for value in pages.values())
counts = {page: sum(row['saved'] for row in value['coverage'].values()) for page, value in pages.items()}
assert counts == {1: 398, 2: 307, 3: 309, 4: 310, 5: 307, 6: 270, 7: 112, 8: 50}
assert sum(counts.values()) == 2063
needs = sorted({ident for value in pages.values() for ident in value['needs_root']})
whole = read(AUDIT / 'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V3.json')
assert set(needs) == {row['id'] for row in whole['rows']}
assert whole['unique_sources'] == 4 and whole['source_positions'] == 8
birth = read(BASE / 'birth_root11_independent_v1_snapshots/v29/complete.json')
assert not birth['errors'] and not birth['needs_root']
assert sum(row['saved'] for row in birth['coverage'].values()) == 2707
assert birth['counts'] == {'PINNED_BODY_NOT_ROOT_ADMISSION': 2325, 'MATERIALIZED_BODY_NOT_ROOT_ADMISSION': 382}
delivery = read(BASE / 'birth_root11_input_delivery_gated_v1/v19/complete.json')
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1712
assert delivery['counts']['HISTORICAL_BEFORE_ACTIVATION_NO_RETROSPECTIVE_EMISSION_CLAIM'] == 995
context = read(AUDIT / 'ROOT11_BIRTH_FLAG_CONTEXT_ADJUDICATION_V2.json')
assert context['context_explained_sources'] == 34 and context['source_scoped_followups_pending'] == 0
assert len(context['changed_body_ids']) == 4 and context['unchanged_body_selection_hashes'] == 2703
assert len(context['actual_edited_review_row_ids']) == 6
assert context['unchanged_exact_rows_in_new_review_containers'] == 24
followup = read(AUDIT / 'ROOT11_FIVE_CONTEXT_FOLLOWUPS_VERIFIED_V1.json')
assert len(followup['field_metadata_only_review_repairs']) == 10 and followup['field_new_bodies'] == 0
commit = read(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V14_INDEPENDENT_VERIFIED.json')
assert commit['commit'] == '2883463c1d3f8b15bcfa3d9ee77a52e466ec6b52'
assert commit['paths'] == 803 and commit['index_count'] == 0
data = dict(status='WHOLE_QUEUE_RUNNING_CONTEXT34_CLOSED_NEW_FIELD_REVIEWS_CONTINUE',
            recorded_at=datetime.now(timezone.utc).isoformat(),
            official_original_HOLD_positions=460695, official_processed_original_HOLD_positions=350522,
            official_remaining_HOLD_positions=110173, new_reviews_in_official_HOLD_delta=0,
            literal_first_review_unique=1793, literal_positions=2597,
            literal_candidate_sources=1783, literal_individual_HOLD_sources=10,
            field_expected_unique=18237, field_saved=2063, field_missing=16174,
            field_versions={str(page): version for page, version in versions.items()},
            field_saved_by_page=counts, field_review_binding_errors=0, field_raw_needs_root=needs,
            field_individually_adjudicated_whole_HOLD_unique=4,
            field_individually_adjudicated_whole_HOLD_positions=8,
            other_types_expected_unique=50162, other_types_first_reviews_saved=0,
            first_review_saved_in_literal_and_field_partitions=3856,
            combined_first_review_missing=66336,
            birth_saved=2707, birth_expected=2707, birth_missing=0,
            birth_by_role=birth['coverage'], birth_pinned_candidates=2325,
            birth_materialized_candidates=382, birth_review_link_errors=0,
            prospective_delivery_preconditions_verified=1712,
            historical_delivery_timestamps_not_retrofilled=995,
            birth_diagnostic_source_contexts_explained=34,
            birth_diagnostic_source_context_followups_pending=0,
            latest_followups_changed_body_sources=4, latest_unchanged_body_hashes=2703,
            latest_review_container_hash_changes_cover_records=30,
            latest_edited_review_rows=6, latest_other_review_rows_unchanged=24,
            unrelated_known_format_followups=[dict(id='expanded_train:139681',
                status='ONE_ORPHAN_PIPE_EDIT_DELEGATED_NOT_YET_COLLECTED',
                input='agents/context_latin/birth_root11_independent_v1/reviewed_139681_task086_v2.txt',
                input_sha256='4215154A162E61F687C7E2DD56D90C6A9772ADF0051832E3573C24E5393FC98D',
                original_token='1311년 원 인종 즉위 후| 헌무',
                intended_token='1311년 원 인종 즉위 후 헌무',
                actual_root_full_new_body_read='e68622', non_newline_EOF_to_preserve=True)],
            ordered_flag_linked_record_scopes=464, ordered_flag_unlinked_in_these_scopes=121,
            latest_verified_local_commit=commit['commit'], latest_verified_local_save_paths=803,
            own_git_window='CLOSED', later_work_has_uncommitted_changes=True,
            source_code_and_data_preserved=True, new_cache_admissions=0,
            prior_progress_report='RESUME_PROGRESS_AND_SPEED_20261104_V10.json',
            independent_whole_2707_semantic_pass_claimed=False,
            all_formatting_in_whole_corpus_claimed_clean=False,
            whole_goal_complete=False, training_authorized=False, input_pins=pins)
for path in [reused, Path(__file__).resolve()]:
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V11.json').open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
text = '''# 전체 정제 계속 — 생년34개 문맥 신호 후속 연결 완료

전체작업과다섯역할은RUN이다. 공식cache3은원래H460,695위치중350,522처리/110,173잔여이며새리뷰는감소량에미반영이다. 새리뷰저장과최종ROOT선택·캐시재생성은구분한다.

| 단계 | 동결저장·연결 | 해당단계미저장 |
|---|---:|---:|
| 코드·수식등literal1차 | 1,793고유/2,597위치(후보1,783·개별H10) | 0 |
| 필드·제목1차 | 2,063/18,237고유 | 16,174 |
| 다른유형1차 | 50,162고유의전량입력/큐준비 | 50,162 |
| 생년·사망일독립2차 | 2,707/2,707고유 | 0 |

1차미저장은66,336고유다. 생년독립2차와합산하지않는다. field동결001v14=398/002v8=307/003v6=309/004v12=310/005v9=307/006v11=270/007v6=112/008v3=50이며연결오류0이다. Lreview001/002의총10행은실제TXT/sidecar경로만새리뷰에서교정했고판정·판독범위·사유내용·본문은불변이다. 원형경로거부v12/v13은보존한다. 최신field원시중재4ID는총괄이개별전체HOLD4원문/8위치로각각판독·원형보존근거를닫았다. 새125306은2806자전문에서화해도입/환경설명/Essay·토론·검색스니펫·평점·미완목적어의귀속경계가닫히지않아한원문전체를분리한것이다. 미판독전체를이와같이H로마감하지않는다.

birth29는C1354/L1353전량,연결오류0·미저장0·동결중재0이다. 후보2325/새본문382는검토후보이며최종캐시채택이아니다. gated19는1712행전달선결/실패0이고과거995범위시각은소급하지않는다. 34개보수적진단신호는실제문맥설명29개와반환후속5개를합쳐해당범위미결0으로연결했다. 5개어휘경계신호·상충하는단정연도의보류·출처별설/경·직접의존기간의원형보존을각ID/SHA로기록했다.5후속에서리뷰설명1개·새본문4개를검산했고81208의별도계보삽입494자/1170바이트도원형전체를보존해분리했다.139681의두사망일설/음력표기,355073의실제사망일/음력대응을새달력변환없이보존했다.

28→29에서바뀐본문SHA는정확4개이고나머지2703선택본문SHA는같다. 리뷰한행수정이5행짜리파일전체SHA를바꾸므로,리뷰SHA가바뀐30기록을30개본문변경으로세지않았다. 실제변경리뷰6행/나머지24행의정확원형불변을검산했다. 총괄검증기의처음6개만리뷰SHA가바뀔것이라는가정은결과쓰기전실패원형에남기고이정확행검사로정정했다.34개진단문맥해소는2707본문전량의최종의미통과나전량형식오류0을뜻하지않는다. 전체본문판독중본139681역사산문의고립파이프한위치는별도새v3보완으로위임했고새선택에는아직미반영이다.

한국어로컬커밋2883463c1d3f8b15bcfa3d9ee77a52e466ec6b52는부모861ff714에서정확803경로/11237841바이트를저장했다. 실제전체경로·부모·모든blob·파일SHA/명시저장범위미반영0/index0을독립재검산했고Git창을닫았다. 준비검산의원장읽기+감사쓰기결합과공지의역슬래시개행은보호훅이실행전차단했다. 읽기전용검산과감사쓰기를분리하고공지에는apply_patch를사용해마쳤으며,남은권한막힘은없다. 원형·대량본문/캐시·보호자료·타세션dirtyflag·push/PR은대상밖이다. 그뒤후속/수집은새미커밋작업이다.

속도관측은V6–V10의5시간186.0→155.4건/시간약16.5%감소와별도생년창361.1→432.1행/시간을구분한다. 긴수식/표·결손기호/조건/주체판정,실제잘림·저장/경로누락및총괄전사/준비기/안내/검증가정오류로재작업이있었다. C/L의생년→field전환뒤같은작업자수/문서길이로통제한속도비교가아니며하드웨어저하·원인별기여율은미확인이다. 같은빈병기/빈표제·없는표범례는이미정한경계로역할이자율정리하고새로운귀속·조건문제만중재하도록명확히해불필요한대기를줄인다. 완료한원문을도구표기/기존후속때문에전량재독하지않는다.

구flag소유계보464/585·이범위미연결121은그대로다. 전량큐의남은판독과새본문의미검토,새ROOT/roster·캐시/독립consumer·전체재계측·필요정본·최종핸드오프/한국어로컬저장은남아있다. A–E완료·일시중지·학습승인으로바꾸지않고계속한다.
'''
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V11.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=2063, first_review_missing=66336,
                     binding_errors=0, birth_saved=2707, context34_pending=0,
                     unrelated_format_followups=1, official_HOLD_unchanged=110173,
                     latest_local_commit=commit['commit']), ensure_ascii=False))
