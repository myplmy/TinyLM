"""Connect later source-scoped fixes and working-copy evidence without admission."""
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
prior = read(AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V11.json')
pipe = read(AUDIT / 'ROOT_139681_ORPHAN_PIPE_VERIFIED_V1.json')
condition = read(AUDIT / 'ROOT_134299_CONDITION_FOLLOWUP_VERIFIED_V1.json')
copies = read(AUDIT / 'FIELD_THREE_ROLE_INITIAL_COPIES_INDEPENDENT_VERIFIED_V1.json')
controls = read(AUDIT / 'FIELD_CONTROLS_INITIAL_COPIES_COMPLETE_V1.json')
latin = read(AUDIT / 'FIELD_LATIN_INITIAL_COPIES_COMPLETE_V1.json')
assert pipe['specific_followup_pending'] == condition['specific_followup_pending'] == 0
assert copies['sources'] == 11240 and copies['actual_copy_bytes'] == 63132341
assert copies['new_cleaned_bodies'] == copies['new_reviews'] == copies['cache_admitted'] == 0
assert controls['sources'] == 3248 and latin['sources'] == 3749
assert controls['sources'] + latin['sources'] + copies['sources'] == 18237
snapshots = {}
for version in ('v29', 'v30'):
    value = read(BASE / 'birth_root11_independent_v1_snapshots' / version / 'complete.json')
    assert not value['errors'] and not value['needs_root']
    records = []
    for shard in value['shards']:
        path = ROOT / shard['path']
        payload = path.read_bytes()
        assert hashlib.sha256(payload).hexdigest().upper() == shard['sha256']
        records += json.loads(payload)
        pins[str(path.relative_to(ROOT))] = shard['sha256']
    assert len(records) == len({row['id'] for row in records}) == 2707
    snapshots[version] = {row['id']: row for row in records}
older, latest = snapshots['v29'], snapshots['v30']
assert set(older) == set(latest)
changed = [ident for ident in older if older[ident]['clean_text_sha256'] != latest[ident]['clean_text_sha256']]
assert changed == ['expanded_train:139681']
assert latest[changed[0]]['clean_text_sha256'] == pipe['body']['sha256']
assert latest[changed[0]]['review']['sha256'] == pipe['review']['sha256']
delivery = read(BASE / 'birth_root11_input_delivery_gated_v1/v20/complete.json')
assert delivery['raw_errors'] == 0 and not delivery['failures']
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1712
assert delivery['counts']['HISTORICAL_BEFORE_ACTIVATION_NO_RETROSPECTIVE_EMISSION_CLAIM'] == 995
page8 = read(BASE / 'remaining_field_title_page_008_counter_v1_snapshots/v4/complete.json')
assert not page8['errors']
assert sum(row['saved'] for row in page8['coverage'].values()) == 60
bound = []
for shard in page8['shards']:
    payload = (ROOT / shard['path']).read_bytes()
    assert hashlib.sha256(payload).hexdigest().upper() == shard['sha256']
    bound.extend(row for row in json.loads(payload) if row['id'] == 'expanded_train:134299')
assert len(bound) == 1
assert bound[0]['clean_text_sha256'] == condition['body']['sha256']
assert bound[0]['review']['sha256'] == condition['review']['sha256']
for path in (reused, Path(__file__).resolve()):
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
result = dict(status='POST_V11_TWO_FOLLOWUPS_BOUND_AND_THREE_ROLE_INITIAL_COPIES_VERIFIED_RUNNING',
              recorded_at=datetime.now(timezone.utc).isoformat(),
              field_saved_frozen=2073, field_missing_frozen=16164,
              combined_first_review_missing_frozen=66326,
              field_versions=dict(prior['field_versions'], **{'8': 'v4'}),
              field_review_binding_errors=0, birth_saved=2707, birth_missing=0,
              birth_raw_snapshot='birth_root11_independent_v1_snapshots/v30',
              birth_delivery_snapshot='birth_root11_input_delivery_gated_v1/v20',
              prospective_delivery_preconditions_verified=1712, historical_timestamps_not_retrofilled=995,
              birth29_to_30_changed_body_ids=changed, birth29_to_30_unchanged_body_hashes=2706,
              scoped_139681_pipe_pending=0, scoped_134299_condition_pending=0,
              new_three_role_initial_copies=11240, new_copy_bytes=63132341,
              new_copy_largest_file_bytes=copies['largest_copy_bytes'],
              existing_controls_initial_copies=3248, existing_latin_initial_copies=3749,
              all_role_initial_copies_prepared=18237, new_copy_reviews=0, new_copy_cleaned_bodies=0,
              no_new_reading_or_admission_from_initial_copies=True,
              old_controls_and_latin_creation_receipts_reused_not_whole_rehashed=True,
              role_scope_announced=['context_hangul', 'historical_review', 'legacy_review'],
              role_scope='Exact own listed initial TXT to absent own new TXT via noclobber; own TXT/MD read/compare only. Reader and raw/initial overwrite prohibitions remain.',
              actual_new_copy_verifier_output='0a6b0e',
              official_original_HOLD_positions=460695, official_processed_original_HOLD_positions=350522,
              official_remaining_HOLD_positions=110173, new_reviews_in_official_HOLD_delta=0,
              latest_verified_local_commit=prior['latest_verified_local_commit'],
              own_git_window='CLOSED', later_work_has_uncommitted_changes=True,
              all_five_roles_and_root='RUN', protected_or_foreign_data_changed=False,
              new_root_or_cache_adoptions=0, input_pins=pins,
              whole_goal_complete=False, training_authorized=False)
assert result['field_saved_frozen'] == prior['field_saved'] + 10
with (AUDIT / 'POST_V11_SCOPE_DELTA_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
text = '''# V11 뒤의 좁은 보완과 재입력 부담 경감

전체 정제와 다섯 역할은 RUN이다. 공식 cache3의 원래H460695 중350522처리/H110173위치는 그대로이며 새리뷰를 감소량에 선반영하지 않는다. V11의 다른 동결은 유지하고 field008만v4의60행으로 갱신해 field2073/18237·연결오류0, 1차미저장66326고유다. 실시간으로 작성중인 후속은 이 동결에 미포함이다.

139681의역사산문고립파이프는최종v5의정확한ASCII한문자만제거했고다른바이트·비개행EOF·다른4리뷰행은불변이다. 초기v3의끝LF와v4의UTF-8결손은미선택원형으로보존하고두SHA/실제바이트·UTF8여부를기록했다. birth30은2707전량·오류0/미저장0이며29에서본문SHA가바뀐것은이한ID뿐이다. gated20은1712행전달선결/실패0·과거995시각소급0이다. 기존34진단문맥범위와5후속검산은유지한다.

134299는원형1223자와새369자본문전문/전차이·sidecar를읽고,조건식이소실된운동상수단락을직접의존단위로원형보류했다. 빠진공식/조건/반례를새로쓰지않았다. 도입·연산자역할/이름·참고문헌은남겼고밖바이트는불변이다. 한행정정review012v2와원래5행review012를함께사용해유효5행을확인했으며새field008v4에정확히연결됐다.이두특정후속미결은0이며전체자료의의미통과는아니다.

재입력부담을줄이기위해C/L에서검산한동일바이트초기사본생성기를H3724/역사3757/legacy3759의자기36페이지에그대로재사용했다.108역할/페이지·11240사본·63132341바이트를독립검산했고최대파일337939바이트다. 각ID/원형SHA보호는본문읽기·해시전에확인했으며보호대상일치0·다른역할혼입0·원형/기존파일덮기0이다. 기존C3248/L3749의생성근거와합쳐field18237자기배정사본이준비됐지만새판독/정제/캐시채택은0이다. 이번새3역할만전량재검산했고기존두역할의사본을불필요하게다시읽지는않았다.

역할에자기정확초기사본에서없는자기새TXT로noclobber복사·자기TXT/MD읽기·비교만허용했다. 원형판독은고정reader/identity지침그대로이며원형·candidate·초기사본덮기/다른역할/코드·해시·시험·웹·Git·모델권한은없다. 진행중/완료자료를재시작하지않고다음새본문부터활용한다. 반복된UTF-8말미손상에대해서는EOF를맞추려고마지막바이트를잘라내지말고추가LF차이는총괄검산에그대로회수하도록정정했다. 속도효과는아직측정하지않았고절약률·품질향상을주장하지않는다.

마지막검증로컬커밋은2883463c이며이후후속·코드·가이드·수집·원장변경은새미커밋작업이다. Git창은닫혀있고원형/기존캐시·보호자료·타세션dirtyflag·GPU/모델/학습·설치/다운로드·push/PR은변경하지않는다. 전량큐·새ROOT/roster·별도캐시/독립consumer·전체재계측·필요정본/최종핸드오프·로컬저장은계속남아있다. A–E완료나일시중지/학습승인으로바꾸지않는다.
'''
with (AUDIT / 'POST_V11_SCOPE_DELTA_V1.md').open('x', encoding='utf-8') as stream:
    stream.write(text)
print(json.dumps(dict(status=result['status'], field_saved_frozen=2073,
                     first_review_missing=66326, birth_saved=2707, scoped_pending=0,
                     unchanged_working_copies=11240, new_copy_reviews=0,
                     official_HOLD_unchanged=110173), ensure_ascii=False))
