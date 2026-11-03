"""Reuse complete pair/frame export for a different author's second reading."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

GROUP = 'birth_root11_independent_v1'
selection_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json'
original_manifest_path = inv.BASE / 'remaining_birth_full_counter_v1/manifest.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
corrections_path = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json'
holds_path = AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD37_V1.json'
flags_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
selection = inv.cache.read(selection_path)
original_manifest = inv.cache.read(original_manifest_path)
contract = inv.cache.read(contract_path)
corrections = inv.cache.read(corrections_path)
holds = inv.cache.read(holds_path)
selected = {r['id']: r for r in selection['rows']}
assert len(selected) == len(selection['rows'])
originals = {r['id']: r for r in original_manifest['rows']}
assert len(originals) == len(original_manifest['rows']) == 2743
blocked_ids, blocked_hashes = set(contract['restricted_ids']), set(contract['restricted_hashes'])
# Both metadata gates precede any source body hashing or decoding.
assert not (set(originals) & blocked_ids)
assert not ({r['original']['sha256'] for r in originals.values()} & blocked_hashes)
flags = {r['id'] for r in inv.cache.read(flags_path)['records']
         if r.get('ordered_source_deletion') is False}
assert len(flags) == 585
all_replacements = {r['id']: r for r in corrections['new_reviewed_birth_corrections'] +
                corrections['new_reviewed_followup_corrections']}
assert len(all_replacements) == 7
replacements = {ident: row for ident, row in all_replacements.items() if ident in originals}
assert len(replacements) == 6 and set(all_replacements) - set(originals) == {'expanded_train:106989'}
assert corrections['corrected_semantic_reviewed_sources'] == 10
assert corrections['corrections_still_pending'] == 0
hold_rows = {r['id']: r for r in holds['rows']}
source_path = inv.BASE / 'birth_root11_independent_source_v1.json'
assert not source_path.exists() and not (inv.BASE / GROUP).exists()
rows, reused_nonadmissions = [], []
for ident, source in originals.items():
    choice = selected[ident]['selected']
    if choice['decision'] == 'HOLD':
        prior = hold_rows[ident]
        assert choice.get('body') is None and prior['original'] == source['original']
        assert prior['root_approved'] and prior['second_review']['reviewer'] == 'root'
        assert prior['second_review']['full_original_read']
        reused_nonadmissions.append({'id': ident, 'original': source['original'],
            'decision': 'HOLD', 'already_individually_read_by_distinct_root_reviewer': True,
            'proof': str(holds_path.relative_to(ROOT))})
        continue
    assert choice['decision'] in {'KEEP', 'EDIT'}
    assert choice['cohort'] == 'remaining_birth_full_counter_v1'
    assert choice['original'] == source['original']
    review = choice['review']
    assert review and '/agents/' in review['path']
    first_editor = review['path'].split('/agents/', 1)[1].split('/', 1)[0]
    assert first_editor == source['role']
    body = {'path': choice['body'], 'sha256': choice['clean_text_sha256']}
    replacement = replacements.get(ident)
    correction_author = None
    if replacement:
        assert replacement['original'] == source['original']
        assert not replacement['in_new_root_selection'] and not replacement['in_cache3']
        body = replacement['body']
        assert '/agents/' in body['path']
        correction_author = body['path'].split('/agents/', 1)[1].split('/', 1)[0]
    for pin in (source['original'], body):
        path = ROOT / pin['path']
        assert not path.is_symlink() and path.resolve().is_relative_to(inv.BASE.resolve())
        assert inv.file_sha(path) == pin['sha256']
        assert 0 < path.stat().st_size < 20_000_000
    row = {k: v for k, v in source.items()
           if k not in {'candidate', 'reading_parts', 'proof', 'guards'}}
    row.update(candidate=body, previous_editor_role=first_editor,
        previous_editor_review=review, correction_author_role=correction_author,
        candidate_is_reviewed_correction_not_yet_adopted=bool(replacement),
        old_root11_body={'path': choice['body'], 'sha256': choice['clean_text_sha256']},
        ordered_change_flag=ident in flags, root_approved=False, cache_admitted=False,
        named_review_strata=[*source['named_review_strata'], 'WHOLE_BIRTH_DISTINCT_AUTHOR_SECOND_READING'])
    rows.append(row)
assert len(rows) == 2707 and len(reused_nonadmissions) == 36
assert {r['id'] for r in rows} | {r['id'] for r in reused_nonadmissions} == set(originals)
pins = {str(p.relative_to(ROOT)): inv.file_sha(p) for p in
    (selection_path, original_manifest_path, contract_path, corrections_path, holds_path,
     flags_path, Path(__file__).resolve())}
inv.write_json(source_path, {'status': 'EXACT_BIRTH_FINAL_BODY_INPUTS_NOT_SECOND_REVIEW_COMPLETION',
    'rows': rows, 'counts': {'pinned_source_body_pairs_verified': 2707},
    'source_code_pins': original_manifest['source_code_pins'], 'input_pins': pins,
    'separately_root_reviewed_nonadmissions': reused_nonadmissions,
    'cleaned_prose_authored_by_root': 0, 'cache_admitted': 0, 'goal_complete': False})

template_path = AUDIT / 'prepare_remaining_birth_readers_v1.py'
text = template_path.read_text(encoding='utf-8')
replacements_in_code = [
    ('2743', '2707'),
    ('remaining_birth_full_counter_v1', GROUP),
    ('remaining_birth_native_proofs_v1/complete.json', 'birth_root11_independent_source_v1.json'),
    ('fresh_regeneration_and_proof_match', 'pinned_source_body_pairs_verified'),
    ('native regeneration must agree', 'all exact original/final body pins must agree'),
    ('roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]',
     'roles = ["context_controls", "context_latin"]'),
    ('role = min(roles, key=lambda value:',
     'role = min([r for r in roles if r != item["row"]["previous_editor_role"] and r != item["row"].get("correction_author_role")], key=lambda value:'),
    ('    ids.sort()', '    ids.sort(key=lambda value: (not by_id[value]["ordered_change_flag"], value))'),
    ('range(0, len(framed), 6000)', 'range(0, len(framed), 4000)'),
    ('framed[offset:offset + 6000]', 'framed[offset:offset + 4000]'),
    ('offset // 6000', 'offset // 4000'),
    ('6000문자', '4000문자'),
    ('출생연도 충돌의 전량 원문 판독', '출생2707 최종본문의 독립2차 판독'),
    ('BIRTH_YEAR_CONFLICT_REQUIRES_INDEPENDENT_SOURCE_READING', 'FINAL_BIRTH_BODY_REQUIRES_DISTINCT_AUTHOR_SECOND_READING'),
    ('ALL2707_NATIVE_SOURCE_CANDIDATE_FULL_READING_REQUIRED_NOT_ADMISSION',
     'ALL2707_ROOT11_FINAL_BODY_DISTINCT_AUTHOR_SECOND_READING_NOT_ADMISSION'),
    ('[source_path, Path(__file__)]', '[source_path, Path(__file__), template_path]'),
]
for before, after in replacements_in_code:
    assert text.count(before) >= 1, before
    text = text.replace(before, after)
lo = text.index('    start.extend([')
hi = text.index('    save(directory / "START_HERE.md"', lo)
protocol = '''    start.extend([
        "현재literal의옛중재를정확리뷰에반영한뒤이새독립검토를시작한다.검수메모는한국어로쓴다.",
        "이전편집자와다른두역할의실제독립검토다.원문전체/최종선택문전체/전체diff를읽고자동가드나이전결론으로대체하지않는다.",
        "원문ID와후보SHA는고정됐다.6개후보는이미총괄이검토했으나아직채택되지않은새보완본문이며기존ROOT11캐시수정은아니다.",
        "원문과선택문을먼저비교하고명명주체/한자명/영문명/생몰월일/출생지/살아있음/직함/경력/작품/서지/수치/단위/조건/부정/불확실성의오삭제를확인한다.",
        "한인물의상충출생연도는양쪽필드와직접의존만국소보류하고다른위치에같은생년이남지않았는지확인한다.다른사람/사건/사망/추정기간은지우지않는다.",
        "원형에서값이없는항목은추정해채우지않는다.출처실제제목/저자/연도와채워진목록관계는보존하고빈표제/소실주체/검수메모/파손구문잔존도확인한다.",
        "후보가정상이면정확candidatebasename의ACCEPT_CANDIDATE,실제보완이면새전체TXT/원형sidecar와REVISE_TEXT다.같은TXT를복제해수정으로세지않는다.",
        "기존편집자agents폴더나과거리뷰는열지않는다.입력은이새그룹의지정고정사본/패킷과자기TASK/가이드뿐이다.",
        "코드/시험/통계/해시/설치/웹/Git/모델/GPU는금지다.controls는총괄의고정reader안내가나오기전에는원문패킷을직접읽지않는다.",
        "과거field작업은보류중이다.이배정의모든TASK를마치고총괄이정확남은flag배정또는field복귀커서를알려준다.중간저장이나페이지끝을전체완료로세지않는다.",
        "빈필드/독립완결설명은기존기준으로판단하고실제새충돌만좁은원문문구와함께묶어중재요청한다.그동안독립TASK를계속한다."])
'''
text = text[:lo] + protocol + text[hi:]
scope = {'__file__': __file__, '__name__': 'birth_final_reader_reuse', 'template_path': template_path}
exec(compile(text, str(template_path) + ':birth_final_second_reading', 'exec'), scope)
manifest_path = inv.BASE / GROUP / 'manifest.json'
manifest = inv.cache.read(manifest_path)
assert len(manifest['rows']) == 2707
assert all(r['role'] != r['previous_editor_role'] and r['role'] != r.get('correction_author_role')
           for r in manifest['rows'])
assert {r['id'] for r in manifest['rows']} == {r['id'] for r in rows}
assert sum(len(ids) for ids in manifest['assignments'].values()) == 2707
inv.write_json(AUDIT / 'BIRTH_ROOT11_SECOND_READING_PREPARATION_V1.json', {
    'status': 'ACTUAL_PAIR_EXPORT_AND_DISTINCT_AUTHOR_ASSIGNMENT_NOT_SEMANTIC_COMPLETION',
    'manifest': {'path': str(manifest_path.relative_to(ROOT)), 'sha256': inv.file_sha(manifest_path)},
    'source': {'path': str(source_path.relative_to(ROOT)), 'sha256': inv.file_sha(source_path)},
    'sources_requiring_actual_second_reading': 2707, 'separately_root_reviewed_hold_sources': 36,
    'ordered_change_flags_in_body_cohort': sum(r['ordered_change_flag'] for r in rows),
    'assignments': {role: len(ids) for role, ids in manifest['assignments'].items()},
    'packet_parts': sum(len(r['reading_parts']) for r in manifest['rows']),
    'previous_editor_equals_reviewer': 0, 'latest_correction_author_equals_reviewer': 0,
    'cleaned_prose_authored_by_root': 0, 'new_cache_admitted': 0,
    'input_pins': pins, 'goal_complete': False, 'training_authorized': False})
print(json.dumps({'sources': 2707, 'separate_reviewed_hold': 36,
    'assignments': {role: len(ids) for role, ids in manifest['assignments'].items()},
    'previous_editor_equals_reviewer': 0, 'adopted': 0}))
