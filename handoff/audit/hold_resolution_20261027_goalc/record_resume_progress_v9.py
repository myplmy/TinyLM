"""Freeze continued queue progress and verified provenance, keeping admission separate."""
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
definitions = [node for node in ast.parse(reused.read_text(encoding='utf-8')).body
               if isinstance(node, ast.FunctionDef) and node.name == 'read']
assert len(definitions) == 1
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(reused), 'exec'), globals())
prior = read(AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V8.json')
versions = {1: 'v10', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v9', 6: 'v8', 7: 'v4'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
         for page, version in versions.items()}
counts = {page: sum(row['saved'] for row in value['coverage'].values()) for page, value in pages.items()}
assert sum(counts.values()) == 1855 and all(not value['errors'] for value in pages.values())
needs = sorted({ident for value in pages.values() for ident in value['needs_root']})
assert set(needs) == {'expanded_train:49092', 'expanded_train:50689', 'expanded_train:56714'}
birth = read(BASE / 'birth_root11_independent_v1_snapshots/v27/complete.json')
assert not birth['errors'] and not birth['needs_root']
assert sum(row['saved'] for row in birth['coverage'].values()) == 2644
delivery = read(BASE / 'birth_root11_input_delivery_gated_v1/v17/complete.json')
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1649
chain = read(AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_INDEPENDENT_VERIFIED_V3.json')
assert chain['actual_additional_saved_chain_links'] == 74 and chain['combined_linked_sources'] == 464
assert chain['remaining_unlinked_sources'] == 121 and chain['automatic_flag_waivers'] == 0
followups = read(AUDIT / 'TWO_BIRTH_FOLLOWUPS_810478_95554_VERIFIED_V1.json')
assert followups['other_review_rows_unchanged'] == 8 and followups['new_root_or_cache_adoptions'] == 0
header = read(AUDIT / 'COMPLETE_PACKET_HEADER_SCOPE_VERIFIED_V1.json')
assert header['actual_root_probe_calls'] == 3 and not header['old_reader_or_config_changed']
copies = read(AUDIT / 'FIELD_LATIN_INITIAL_COPIES_INDEPENDENT_VERIFIED_V1.json')
assert copies['sources'] == 3749 and copies['new_cleaned_bodies'] == copies['new_reviews'] == 0
data = dict(prior)
data.update(status='FULL_QUEUE_RUNNING_PROVENANCE_AND_READER_CONFUSIONS_VERIFIED',
            recorded_at=datetime.now(timezone.utc).isoformat(),
            field_saved=1855, field_missing=16382, combined_first_review_missing=66544,
            field_versions={str(page): version for page, version in versions.items()},
            field_saved_by_page=counts, field_frozen_needs_root=needs,
            birth_saved=2644, birth_missing=63, birth_by_role=birth['coverage'],
            birth_pinned_candidates=2263, birth_materialized_candidates=381,
            prospective_delivery_preconditions_verified=1649,
            birth_snapshot_does_not_yet_select_post_freeze_two_followups=True,
            two_post_freeze_birth_followups_byte_checked=True,
            ordered_flag_linked_record_scopes=464, ordered_flag_unlinked_in_these_scopes=121,
            new_ordered_flag_ownership_links_not_semantic_passes=74,
            new_ownership_independent_binding_checks=74,
            ownership_adapter_positive_cases=2, ownership_adapter_negative_rejections=5,
            latin_new_initial_copies_not_reviews=3749,
            hangul_field007_own_assignment_saved=102,
            hangul_next_phase='remaining_field_title_page_008_counter_v1',
            reader_header_full_pinned_packet_probes=3,
            old_reader_or_config_changed=False,
            prior_progress_report='RESUME_PROGRESS_AND_SPEED_20261104_V8.json', input_pins=pins)
for path in [reused, Path(__file__).resolve()]:
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V9.json').open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
text = '''# 전체 정제 계속 — 최신 판독과 중복 재판독 방지

다섯 역할과 총괄은 RUN이며 A–E는 미완이다. 공식 cache3의 원래H460,695위치 중350,522처리/110,173잔여는 그대로다. 이후 저장 리뷰를 캐시 감소량에 미리 더하지 않는다.

| 단계 | 실제 동결 저장·연결 | 해당 단계 미저장 |
|---|---:|---:|
| 필드·제목1차 | 1,855/18,237 고유원문 | 16,382 |
| 다른 유형1차 | 50,162고유원문의 전량 입력·큐 준비 | 50,162 |
| 생년·사망일 독립2차 | 2,644/2,707 고유원문 | 63 |

1차 미저장은66,544고유원문이다. 독립2차63건과합쳐고유수로세지않는다. field는001v10=323/002v8=307/003v6=309/004v12=310/005v9=307/006v8=197/007v4=102이다. 연결오류0이고 남은원시중재3ID는기존개별전체HOLD3원문/6위치에연결했다. H는field007자기배정102건저장을마치고기존전량큐대로008로간다. C는001, historical·legacy는006을계속한다.

birth27은C1354/L1290이며누락63·오류0·동결중재0이다. gated17은1649행전달선결/실패0을확인하고과거995범위의전달시각은소급하지않는다. 동결후810478의원형/직전후보인용구별sidecar와95554의월일출생역할닫기를새리뷰로회수했다. 새본문전문/전차이·EOF·sidecar를실제로읽고810478본문불변/95554단일변경밖바이트불변/나머지8리뷰행불변을검산했다. 이둘의최신선택수집은다음생년스냅샷에서하며이번27에소급하지않는다.

구순서flag는기존390개에정확74개소유계보를추가해464/585연결,이범위미연결121개다. 새74개의이전/현재리뷰행·출력SHA·서로다른명명역할과집합을독립검사했다. 본문참조정상2/잘못된참조거부5도확인했다. 이는새의미판독·이해·과거전달시각·자동flag면제가아니다. 남은경우를현재파일해시나부분ID로임의연결하거나자동중복재독하지않는다. 원시실패와구형recipe/출력양식은각V1–V3결과에보존했다.

판독지연의실제사례도좁게조치했다.1895의삭제표시가패킷경계에서-각/주로나뉜것과995586의개행없는EOF가diff의마지막삭제/추가를붙인것은원형/후보바이트로확인했다. 입력변경이나분류손실로계산하지않는다. birth complete-reader는실제전체packet을출력하면서마지막내부조각의piece/characters를헤더에복사했다. root3프로브에서전체packetSHA/바이트를확인하고기존도구/설정/완료자료는변경하지않았다. L은정확다음packet까지읽어TASK251을마쳤다. 실제잘림과이표시한계는구분한다.

L의생년마지막TASK271/3행뒤field전환을위해자기36페이지의동일candidate초기사본3749개를미리생성·독립SHA검산했다. 사본을정제/판독/채택으로세지않는다. 자기사본→없는자기새TXT의noclobber복사와자기TXT/MD읽기·비교만추가설명했으며원형/초기사본덮기·보호자료·다른역할접근·임의코드권한은없다. 생년작업은그대로계속한다.

속도근거는V6–V8의서로다른관측창에연결한다. 긴문서·수식/주체/조건의결손판정과보완검토,실제입력혼동·저장누락·잘림및총괄의전사/준비기/경로실수는재작업을만들었다. 이번총괄코드의누락import·잘못전사한contract SHA·추측한의존파일명도숨기지않고실패단계와정정근거를기록했다. 단계/작업자수/문서길이를통제하지않았으므로하드웨어저하·원인별기여율·짧은호출의인과효과를주장하지않는다. 새리뷰가모여도공식H는검토선택·캐시재생성전까지그대로보이는집계지연도있다.

마지막한국어로컬커밋은861ff714(명시1748경로/16201097바이트)이며그뒤작업은새미커밋변경이다. 전량판독·새보완의미검토·새ROOT/roster·캐시/독립consumer·전체재계측·필요정본·최종핸드오프·로컬저장은남는다. 전체작업을완료/일시중지/추가300M승인으로바꾸지않는다. 원형·보호TinyDataset·타세션dirty flag·GPU/모델/학습·설치/다운로드·push/PR경계는유지한다.
'''
with (AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V9.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=data['status'], field_saved=1855, first_review_missing=66544,
                     birth_saved=2644, birth_missing=63, linked_flag_sources=464,
                     unlinked_flag_sources=121, official_HOLD_unchanged=110173), ensure_ascii=False))
