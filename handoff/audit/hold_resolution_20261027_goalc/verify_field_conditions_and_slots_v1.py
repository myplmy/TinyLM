"""Check authored condition, punctuation and missing-title edits against exact sources."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}


def read(path):
    payload = path.read_bytes()
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest().upper()
    return payload


guard_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
guard = json.loads(read(guard_path))
assert pins[str(guard_path.relative_to(ROOT))] == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser
resolve, parse, _ = load_parser()
records = []
for page, role, number, before_name, after_name, note_name, old_review_name, new_review_name, expected_sha in [
    (1, 'context_latin', '653', 'reviewed_expanded_train_653_v1.txt', 'reviewed_expanded_train_653_v3.txt',
     'hold_expanded_train_653_v3.md', 'review_015.md', 'review_015_v4.md',
     'FDE849343014DA91254F6C8B93AA3109D6035140AC75F1A2448D955E0E246CA3'),
    (2, 'context_controls', '11993', 'expanded_train_11993_reviewed_task002_v2.txt',
     'expanded_train_11993_reviewed_task002_v3.txt', 'hold_11993_task002_v3.md',
     'review_002_v2.md', 'review_002_v3.md', 'E0813F90FD55C645A553B0BAE5E441F83E3E453D22C7B3564F11F507D772FB03'),
    (2, 'context_controls', '13067', None, 'expanded_train_13067_reviewed_task003_v3.txt',
     'hold_13067_task003_v1.md', 'review_003.md', 'review_003_v2.md',
     '6F1002BC4E4066AD443241920BE1D641536EA55EFA9DA9EFACE61F554C98BB2B'),
    (2, 'context_controls', '13582', 'expanded_train_13582_reviewed_task004_v2.txt',
     'expanded_train_13582_reviewed_task004_v3.txt', 'hold_13582_task004_v3.md',
     'review_004_v2.md', 'review_004_v3.md', '04D49F3BC0BE23B3F57FF04DFA52B5C8A87EFEAF1B4C78E905A401E2D59826C4'),
    (5, 'legacy_review', '60130', 'expanded_train_60130_revised_task011_v1.txt',
     'expanded_train_60130_revised_task011_v2.txt', 'hold_60130_task011_v2.md',
     'review_011.md', 'review_011_v2.md', 'D971BCAC826386F392B83DB809CB8212E20271F348EEFAAB60861D5BA47BC349'),
]:
    ident = 'expanded_train:' + number
    manifest_path = BASE / f'remaining_field_title_page_{page:03}_counter_v1/manifest.json'
    source = next(row for row in json.loads(read(manifest_path))['rows'] if row['id'] == ident)
    assert ident not in guard['restricted_ids'] and source['original']['sha256'] not in guard['restricted_hashes']
    original = read(ROOT / source['original']['path'])
    assert hashlib.sha256(original).hexdigest().upper() == source['original']['sha256']
    source_text = original.decode('utf-8')
    directory = BASE / 'agents' / role / f'remaining_field_title_page_{page:03}_counter_v1'
    path = directory / after_name
    after = read(path)
    assert hashlib.sha256(after).hexdigest().upper() == expected_sha
    text = after.decode('utf-8')
    before = read(directory / before_name) if before_name else None
    note_path = directory / note_name
    note = read(note_path).decode('utf-8')
    if number == '653':
        old = '행의 상수곱의 역연산은, 그 행에 그 상수 대신 역수를 곱하는 것이다.'.encode()
        new = '행의 상수곱의 역연산은, 0이 아닌 상수의 역수를 그 행에 곱하는 것이다.'.encode()
        assert before.count(old) == 1 and before.replace(old, new, 1) == after
        assert '(행의 상수곱) 번째 행을 0이 아닌 임의의 상수 으로 곱한다.' in source_text
        wrong_direction = '행에 상수곱을 하면, 행렬식은 그 상수의 역수배가 된다.'
        assert wrong_direction in source_text and wrong_direction in note and wrong_direction not in text
        assert text.count('해가 존재하는 경우') == 2 and '체의 표수가 0이라면' in text
        read(AUDIT / 'ROOT_653_DETERMINANT_DIRECTION_COUNTEREXAMPLE_V1.json')
        detail = dict(scope='One inverse-operation sentence retains the source nonzero-scalar condition',
                      determinant_direction_sentence_remains_held=True,
                      existence_and_characteristic_zero_qualifiers_retained=True,
                      preexisting_v2_not_overwritten_and_final_v3_used=True)
    elif number == '11993':
        changes = [('그리고 선택받은 자(elect)"라고', '그리고 선택받은 자(elect)라고'),
                   ('소리를 봄 또는 인지함"으로', '소리를 봄 또는 인지함으로')]
        expected = before
        for old, new in changes:
            assert expected.count(old.encode()) == 1
            expected = expected.replace(old.encode(), new.encode(), 1)
        assert expected == after
        initial = read(directory / 'expanded_train_11993_reviewed_task002_v1.txt')
        expected_v2 = initial
        for old, new in [
            ('문자 그대로는  아버지(The Father of Greatness, 우주의 아버지)"라고',
             '문자 그대로는 아버지(The Father of Greatness, 우주의 아버지)라고'),
            ('Seal of the Prophets: 문자 그대로는  , 책이 완료되어',
             'Seal of the Prophets: 책이 완료되어'),
            ('그리고  또는 선택받은 자(elect)"라고', '그리고 선택받은 자(elect)"라고'),
        ]:
            assert expected_v2.count(old.encode()) == 1
            expected_v2 = expected_v2.replace(old.encode(), new.encode(), 1)
        assert expected_v2 == before
        raw_chinese_rows = [line for block in re.findall(r'```text\n(.*?)\n```', note, re.S)
                            for line in block.splitlines() if '; 중국어:' in line]
        assert len(raw_chinese_rows) == 6 and len(set(raw_chinese_rows)) == 6
        assert all(line in source_text and line.split('; 중국어:', 1)[0] in text for line in raw_chinese_rows)
        for phrase in ('번역되었을 수도 있고', '번역되었을 수도 있다', '기반으로 한 것으로 보인다'):
            assert phrase in source_text and phrase in text
        assert re.search(r'c\.\s*216~276', text)
        detail = dict(scope='Three bounded gloss/alternative edits plus two orphan closing quotes',
                      six_empty_chinese_cells_have_exact_source_rows=True,
                      filled_multilingual_names_and_glosses_preserved=True,
                      translation_uncertainty_approximate_dates_and_attribution_not_reassigned=True)
    elif number == '13067':
        raw_marker = '인 정수  (즉, 제곱 인수가 없는 정수가 아닌 수)은 다음과 같다.\n'
        assert source_text.count(raw_marker) == 1
        values = source_text.split(raw_marker, 1)[1].splitlines()[0]
        marker = '정수 중 제곱 인수가 없는 정수가 아닌 수는 다음과 같다.\n'
        assert marker + values in text
        detail = dict(scope='The filled integer domain, double negation and literal ordered list only',
                      original_integer_list_exactly_retained=True,
                      missing_function_symbol_or_formula_generated=False,
                      byte_identity_outside_initial_authored_cleaning_not_claimed=True)
    elif number == '13582':
        old = '회전 조건에서 언급되는 물리량은 각속도 ω (오메가), 병진 속력 v, 물체의 반지름 r이다.'.encode()
        new = '회전 조건에서 언급되는 물리량은 물체의 질량중심을 기준으로 한 물체의 각속도 ω (오메가), 물체의 병진 속력 v, 물체의 반지름 r이다.'.encode()
        assert before.count(old) == 1 and before.replace(old, new, 1) == after
        assert '물체의 질량중심을 기준으로 물체의 각속도 ω (오메가)' in source_text
        assert '일정한 조건(그 조건은 수식으로 표현되는데, 자세한 설명은 생략)' in text
        assert '최대 정지 마찰력의 크기는 수직 항력의 크기와 정지 마찰 계수의 곱' in text
        assert '(구름 마찰력의 크기)=(구름 마찰계수)*(수직항력)' in text
        blocks = re.findall(r'```text\n(.*?)\n```', note, re.S)
        assert len(blocks) == 5 and all(block in source_text for block in blocks)
        detail = dict(scope='One named-variable sentence retains centre-of-mass reference and object ownership',
                      missing_rotation_relation_stays_held=True,
                      five_exact_held_source_blocks_verified=True,
                      actual_product_relations_and_explicit_rigid_body_qualification_retained=True)
    else:
        removed = ' 브느와 페터스 (1984), Magic-Strip.\n'.encode()
        assert before.count(removed) == 1 and before.replace(removed, b'', 1) == after
        assert '브느와 페터스 (1984) . Magic-Strip.' in source_text
        assert '브느와 페터스 (1984) . Magic-Strip.' in note
        assert '브느와 페터스 (1984), Magic-Strip.' in note
        for title, comment in [
            ("24. 땡땡과 알파아트(Tintin et l'Alph-art) (1986, 2004)", '에르제 사후에 미완성 유고작으로 출간됨'),
            ('25. 땡땡과 상어 호수 (Tintin et le lac aux requins) (1972)', '극장판 애니메이션을 원작으로 만들어짐'),
        ]:
            assert title + '\n   ' + comment in text
        detail = dict(scope='Only the bibliographic row with its missing title and attached year/publisher',
                      missing_title_not_generated_or_reassigned=True,
                      other_named_bibliography_and_book_note_relations_unchanged=True)
    old_review = {resolve(row['cells'][0]): row for row in parse(read(directory / old_review_name))}
    review_path = directory / new_review_name
    new_review = {resolve(row['cells'][0]): row for row in parse(read(review_path))}
    effective = dict(old_review, **new_review)
    assert len(old_review) == len(effective) == 5 and ident in new_review
    assert all(effective[key]['raw'] == old_review[key]['raw'] for key in old_review if key != ident)
    assert path.name in new_review[ident]['raw'] and note_path.name in new_review[ident]['raw']
    if before is not None:
        assert before.endswith(b'\n') == after.endswith(b'\n')
    records.append(dict(id=ident, original=source['original'],
                        body=dict(path=str(path.relative_to(ROOT)), sha256=expected_sha),
                        review=dict(path=str(review_path.relative_to(ROOT)), sha256=pins[str(review_path.relative_to(ROOT))]),
                        sidecar=dict(path=str(note_path.relative_to(ROOT)), sha256=pins[str(note_path.relative_to(ROOT))]),
                        details=detail, unchanged_other_review_rows=4,
                        unchanged_bytes_outside_requested_followup=(before is not None),
                        whole_document_semantic_or_fact_pass=False))
read(Path(__file__).resolve())
result = dict(status='FOUR_BOUNDED_EDITS_AND_ONE_INTEGER_LIST_SCOPE_VERIFIED', records=records,
              actual_root_reads=['1327b1', '02c9d1', 'b4a151', '7a6439'],
              root_authored_corpus_bodies=0, new_root_or_cache_admissions=0,
              earlier_failures_and_authored_versions_preserved=True,
              generic_guards_changed=False, input_pins=pins,
              whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'ROOT_FIELD_CONDITIONS_AND_SLOTS_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], exact_source_scopes=5,
                     bounded_followup_edits=4, unchanged_other_review_rows=20,
                     root_or_cache_admissions=0)))
