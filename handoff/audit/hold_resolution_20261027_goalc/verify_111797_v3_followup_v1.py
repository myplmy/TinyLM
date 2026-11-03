"""Bind the corrected source identity and four exact edits without new admission."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
COHORT = 'remaining_field_title_page_007_counter_v1'
DIRECTORY = BASE / 'agents/context_hangul' / COHORT
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser

pins = {}


def read(path):
    assert not path.is_symlink() and (path.resolve().is_relative_to(BASE) or path.resolve().is_relative_to(AUDIT))
    payload = path.read_bytes()
    assert 0 < len(payload) < 20_000_000
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest().upper()
    return payload


contract = json.loads(read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'))
manifest = json.loads(read(BASE / COHORT / 'manifest.json'))
ident = 'expanded_train:111797'
source = next(row for row in manifest['rows'] if row['id'] == ident)
assert ident not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']
texts = {}
for label in ['original', 'candidate']:
    payload = read(ROOT / source[label]['path'])
    assert hashlib.sha256(payload).hexdigest().upper() == source[label]['sha256']
    texts[label] = payload.decode('utf-8')
v2 = read(DIRECTORY / 'expanded_train_111797_task011_v2.txt')
assert hashlib.sha256(v2).hexdigest().upper() == '64953EA77E84E4A2CB046418BD6A023BCFE869126EF43E8A84B13CB7A3A2231B'
missing_comparison = '레이디 핑키의 이름은 ""로 표기되고, 영어 레이디(lady)의 표기는 뒷부분의 장음을 포함하여 ""이기 때문에 엄밀히는 "레이디"가 아니지만, 의도는 어느 정도 부합한다고 할 수 있다.'
expected = texts['candidate']
for old, new in [(missing_comparison + '\n', ''),
                 ('《전설의 용자 ~ 마음은 하나 ~》 ()', '《전설의 용자 ~ 마음은 하나 ~》'),
                 ('외부 링크 \n', '')]:
    assert expected.count(old) == 1
    expected = expected.replace(old, new, 1)
assert expected.encode('utf-8') == v2
v3 = read(DIRECTORY / 'expanded_train_111797_task011_v3.txt')
assert v2.count('《바람의 미래로》 ('.encode('utf-8')) == 1
assert v2.replace('《바람의 미래로》 ('.encode('utf-8'), '《바람의 미래로》'.encode('utf-8'), 1) == v3
assert hashlib.sha256(v3).hexdigest().upper() == 'BCFE8F8B849D6F334904E84707BDB628B7AFE06CE4BC1502F791AE3780631BE8'
old_hold = read(DIRECTORY / 'hold_111797_task011_v2.md')
new_hold = read(DIRECTORY / 'hold_111797_task011_v3.md')
assert new_hold.startswith(old_hold)
assert missing_comparison in texts['original'] and missing_comparison in new_hold.decode('utf-8')
assert '《바람의 미래로》 (\n' in texts['original']
assert '`《바람의 미래로》 (`' in new_hold.decode('utf-8')
read(DIRECTORY / 'note_111797_recheck_v1.md')
resolve, parse, _ = load_parser()
review = read(DIRECTORY / 'review_011_v4.md')
entry = exact_entry(review, ident, {row['id'] for row in manifest['rows']}, resolve, parse)
assert entry['cells'][1] == 'REVISE_TEXT' and entry['cells'][3] == 'expanded_train_111797_task011_v3.txt'
assert 'hold_111797_task011_v3.md' in entry['raw']
read(Path(__file__).resolve())
result = dict(status='111797_FOUR_SCOPED_EDITS_AND_ORIGINAL_HOLD_QUOTES_VERIFIED', id=ident,
              source_original=source['original'], candidate=source['candidate'],
              selected_body=dict(path=str((DIRECTORY / 'expanded_train_111797_task011_v3.txt').relative_to(ROOT)),
                                 sha256=hashlib.sha256(v3).hexdigest().upper()),
              candidate_to_v2_exact_edits=3, v2_to_v3_exact_edits=1, other_body_bytes_unchanged=True,
              hold_v2_preserved_as_prefix=True, raw_missing_comparison_preserved=True,
              actual_root_all_diffs_and_changed_context_reads=['074c24', '6952fc', 'f58151'],
              root_new_full_original_read_claim=False, known_pending_in_this_case=0,
              input_pins=pins, new_root_or_cache_adoptions=0, whole_goal_complete=False,
              training_authorized=False)
with (AUDIT / 'ROOT_111797_V3_FOLLOWUP_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], candidate_to_v2_edits=3, v2_to_v3_edits=1,
                     other_body_bytes_unchanged=True, pending_in_this_case=0), ensure_ascii=False))
