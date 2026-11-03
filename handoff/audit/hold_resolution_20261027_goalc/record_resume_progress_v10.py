"""Freeze completed birth coverage and the ongoing whole-corpus field queue."""
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
read(AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V9.json')
versions = {1: 'v12', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v9', 6: 'v10', 7: 'v5', 8: 'v2'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
         for page, version in versions.items()}
errors = [dict(page=page, **row) for page, value in pages.items() for row in value['errors']]
assert len(errors) == 5 and {row['error'] for row in errors} == {'NO_EXACT_BODY_OUTPUT_PATH'}
assert all(row['page'] == 1 and row['role'] == 'context_latin' for row in errors)
counts = {page: sum(row['saved'] for row in value['coverage'].values()) - len(value['errors'])
          for page, value in pages.items()}
assert sum(counts.values()) == 1965
assert counts == {1: 343, 2: 307, 3: 309, 4: 310, 5: 307, 6: 257, 7: 102, 8: 30}
needs = sorted({ident for value in pages.values() for ident in value['needs_root']})
assert set(needs) == {'expanded_train:49092', 'expanded_train:50689', 'expanded_train:56714'}
birth = read(BASE / 'birth_root11_independent_v1_snapshots/v28/complete.json')
assert not birth['errors'] and not birth['needs_root']
assert sum(row['saved'] for row in birth['coverage'].values()) == 2707
assert birth['coverage']['context_controls']['saved'] == 1354
assert birth['coverage']['context_latin']['saved'] == 1353
delivery = read(BASE / 'birth_root11_input_delivery_gated_v1/v18/complete.json')
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1712
chain = read(AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_INDEPENDENT_VERIFIED_V3.json')
assert chain['actual_additional_saved_chain_links'] == 74
assert chain['combined_linked_sources'] == 464 and chain['remaining_unlinked_sources'] == 121
context = read(AUDIT / 'ROOT11_BIRTH_FLAG_CONTEXT_ADJUDICATION_V1.json')
assert context['diagnostic_sources'] == 34 and context['source_scoped_followups_pending'] == 5
assert context['context_explained_without_followup'] == 29
followup72884 = read(AUDIT / 'ROOT_72884_V2_FOLLOWUP_VERIFIED_V1.json')
followup111797 = read(AUDIT / 'ROOT_111797_V3_FOLLOWUP_VERIFIED_V1.json')
assert followup72884['new_root_or_cache_adoptions'] == 0
assert followup111797['new_root_or_cache_adoptions'] == 0
data = dict(status='WHOLE_QUEUE_RUNNING_BIRTH_COVERAGE_COMPLETE_CONTEXT_FOLLOWUPS_OPEN',
            recorded_at=datetime.now(timezone.utc).isoformat(),
            official_cache='data_cache/p106b_hold_resolution_v1_20261027_goalc/cache_reviewed_partial_v3',
            official_original_HOLD_positions=460695, official_processed_original_HOLD_positions=350522,
            official_remaining_HOLD_positions=110173, new_reviews_in_official_HOLD_delta=0,
            field_expected_unique=18237, field_saved=1965, field_missing=16272,
            field_versions={str(page): version for page, version in versions.items()},
            field_saved_by_page=counts, field_review_path_rejections_not_counted=5,
            field_review_path_rejections=errors, field_frozen_needs_root=needs,
            field_three_frozen_needs_root_already_individual_HOLD_sources=3,
            field_three_frozen_needs_root_original_positions=6,
            other_types_expected_unique=50162, other_types_first_reviews_saved=0,
            combined_first_review_missing=66434,
            birth_saved=2707, birth_expected=2707, birth_missing=0,
            birth_by_role=birth['coverage'], birth_pinned_candidates=2326,
            birth_materialized_candidates=381, birth_review_link_errors=0,
            birth_frozen_needs_root=0, prospective_delivery_preconditions_verified=1712,
            historical_delivery_timestamps_not_retrofilled=995,
            birth_snapshot_selects_two_prior_followups=True,
            new_birth_diagnostic_sources=34, new_birth_context_explained_sources=29,
            new_birth_context_followups_pending=context['pending_ids'],
            root_72884_and_111797_specific_followups_verified=True,
            ordered_flag_linked_record_scopes=464, ordered_flag_unlinked_in_these_scopes=121,
            new_ordered_flag_ownership_links_not_semantic_passes=74,
            latest_verified_local_commit='861ff714e6a4387876dc4b8c7eb7debe3d020394',
            own_git_window='CLOSED', later_work_has_uncommitted_changes=True,
            prior_progress_report='RESUME_PROGRESS_AND_SPEED_20261104_V9.json',
            independent_whole_2707_semantic_pass_claimed=False,
            original_or_existing_cache_overwritten=False, new_cache_admissions=0,
            whole_goal_complete=False, training_authorized=False, input_pins=pins)
for path in [reused, Path(__file__).resolve()]:
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V10.json').open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
text = '''# 전체 정제 계속 — 생년 독립 판독 전량 저장과 의미 검토

다섯 역할과 총괄은 RUN이며 A–E는 미완이다. 공식 cache3은 원래 HOLD460,695위치 중350,522처리/110,173잔여로 그대로다. 새 리뷰를 이 감소량에 미리 포함하지 않는다.

| 단계 | 동결 저장·연결 | 해당 단계 미저장 |
|---|---:|---:|
| 필드·제목1차 | 1,965/18,237고유원문 | 16,272 |
| 다른 유형1차 | 50,162고유원문의 전량 입력·큐 준비 | 50,162 |
| 생년·사망일 독립2차 | 2,707/2,707고유원문 | 0 |

1차 미저장은66,434고유원문이다. 독립2차와 합산하지 않는다. field001v12의유효343/002v8=307/003v6=309/004v12=310/005v9=307/006v10=257/007v5=102/008v2=30을 동결했다. 001v12의리뷰주장348중L의bare filename5건은정확TXT경로연결에서거부되어위저장량에포함하지않았다. 본문불량확정은아니며원형거부를보존하고L에새리뷰경로만교정하도록요청했다. 다른페이지연결오류0이다. 기존field원시중재3ID는개별전체HOLD3원문/6위치원장에연결했고008의두보완은이번새리뷰에연결되어원시중재가없다. 전량미판독자료를일괄HOLD로마감하지않는다.

birth28은C1354/L1353전량저장,미저장0·연결오류0·동결중재0이다. 후보2326/새본문381은검토후보수이며최종캐시채택이아니다. 기존810478/95554의최신보완도선택했다. gated18은1712행의실제전달선결/실패0을확인하고과거995범위의전달시각은소급하지않는다. 전달·저장·SHA일치는이해·의미완료를뜻하지않는다.

2707선택본문에기존독립수량/역할탐지기를적용해34고유신호를얻고총괄이각신호의전차이·출생/수량문맥과실제리뷰행을읽었다.5개는전라북도·전라남도·전남·전기의자·전쟁의첫글자를기간의'전'으로인식한어휘경계신호였다. 상충하는무조건연도를보류하고원문설·출처·경을남긴사례도있다. 현재29개문맥설명완료/정확5개후속보완대기이며34개를모두오류로계산하지않는다.341392의실제발화가없다는sidecar서술은발화는있고닫는인용부호가없다는한문장으로교정하고본문·원형인용·다른4리뷰행불변을검산했다.5개대기는121135의본문과다른리뷰설명,79984/81208/139681의날짜역할·빈포장,355073의생년보류와함께빠진명시사망날짜대응이다. 이네본문/한메타데이터교정은작성역할에좁게반환했다.범위밖의전량의미통과를주장하지않는다.

72884의새본문전문·전차이·sidecar및8개명명영토항목의날짜·일부·반환관계를확인했다. 두후속교정밖바이트와다른4리뷰행은불변이다.111797도빈곡명뒤열린괄호한위치의새v3와기존v2밖바이트·원형인용·리뷰연결검산을마쳤다.둘은이번006/007스냅샷에연결됐으며새캐시채택은0이다. 자료의현행사실검증으로확대해석하지않는다.

구순서flag의정확소유계보는464/585연결,이범위미연결121을유지한다. 새74개연결은이전/현재명명역할·리뷰·본문SHA의추적증거이며새판독·이해·자동면제가아니다. 현재해시로과거없는리뷰SHA를소급하지않는다.

속도는기존5시간관측의186.0→155.4건/시간(약16.5%감소)과최근생년스냅샷의361.1→432.1행/시간을다른관측창으로구분한다. 긴수식·표문서의주체·조건·기호결손판독과보완,실제입력혼동/잘린초안/저장누락,총괄의전사·준비기·경로안내실수가재작업을만들었다. 이번bare filename과리뷰설명오류도숨기지않고좁게교정한다. 원인별기여율·하드웨어저하·문서길이/작업자수를통제한인과효과는측정하지않았다. 공식H가리뷰뒤즉시줄지않는집계지연도구분한다. C/L은생년배정을마치고field001을이어가며H는008,역사/legacy는자기전량페이지큐를계속한다.

마지막검증로컬커밋은861ff714다. 이후작은감사/리뷰·코드·WIP를다음명시한국어로컬저장으로잇고전량판독을계속한다. 새ROOT/roster·캐시/독립consumer·전체재계측·필요정본·최종핸드오프는남아있다. 완료·일시중지·학습승인으로바꾸지않는다. 원형·기존캐시·보호TinyDataset·타세션dirty flag·GPU/모델/학습·설치/다운로드·push/PR경계를유지한다.
'''
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V10.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=1965, field_path_errors_excluded=5,
                     first_review_missing=66434, birth_saved=2707, birth_missing=0,
                     birth_context_followups=5, official_HOLD_unchanged=110173), ensure_ascii=False))
