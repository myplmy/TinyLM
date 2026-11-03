"""Verify two authored followups, their unchanged bytes and exact review rows."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
DIRECTORY = BASE / 'agents/context_controls/birth_root11_independent_v1'
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser

pins = {}


def read(path):
    assert not path.is_symlink() and (path.resolve().is_relative_to(BASE) or path.resolve().is_relative_to(AUDIT))
    data = path.read_bytes()
    assert 0 < len(data) < 20_000_000
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest().upper()
    return data


contract = json.loads(read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'))
manifest = json.loads(read(BASE / 'birth_root11_independent_v1/manifest.json'))
ids = {'expanded_train:810478', 'expanded_train:95554'}
sources = {row['id']: row for row in manifest['rows'] if row['id'] in ids}
assert set(sources) == ids
for ident, row in sources.items():
    assert ident not in contract['restricted_ids']
    assert row['original']['sha256'] not in contract['restricted_hashes']
texts = {}
for ident, row in sources.items():
    texts[ident] = {}
    for label in ['original', 'candidate']:
        payload = read(ROOT / row[label]['path'])
        assert hashlib.sha256(payload).hexdigest().upper() == row[label]['sha256']
        texts[ident][label] = payload.decode('utf-8')

body810 = read(DIRECTORY / 'expanded_train_810478_reviewed_task232_v1.txt')
assert hashlib.sha256(body810).hexdigest().upper() == '98A7BC345A36A263F7A084A2B09AB98052D58966269724414963596DA2537242'
expected = texts['expanded_train:810478']['candidate']
for old, new in [('미나모토노 요시이에(1039년 ~ 1106년 8월 4일)', '미나모토노 요시이에(1106년 사망)'),
                 ('요시이에는 7월 15일에 68세의 나이로 사망하였다.', '요시이에는 68세의 나이로 사망하였다.')]:
    assert expected.count(old) == 1
    expected = expected.replace(old, new, 1)
assert (expected.rstrip('\n') + '\n').encode('utf-8') == body810
old_hold = read(DIRECTORY / 'hold_810478_task232_v1.md').decode('utf-8')
new_hold = read(DIRECTORY / 'hold_810478_task232_v2.md').decode('utf-8')
for label in ['original', 'candidate']:
    lead = texts['expanded_train:810478'][label].split('。', 1)[0].split('다.', 1)[0] + '다.'
    assert '`' + lead + '`' in new_hold
assert '직전 candidate 리드(원문 인용이 아님)' in new_hold
assert old_hold.split('## 사망 월일', 1)[1] == new_hold.split('## 사망 월일', 1)[1]

old955 = read(DIRECTORY / 'expanded_train_95554_reviewed_v1.txt')
new955 = read(DIRECTORY / 'expanded_train_95554_reviewed_v2.txt')
assert hashlib.sha256(old955).hexdigest().upper() == '8D8C3FDA0A9C8FC4F3269F4BFD708598EE8968A0456B6BD4058E51E5C48DACB1'
assert old955.count('3월 11일 ~ )'.encode('utf-8')) == 1
assert old955.replace('3월 11일 ~ )'.encode('utf-8'), '3월 11일생)'.encode('utf-8'), 1) == new955
read(DIRECTORY / 'hold_95554_v1.md')
resolve, parse, _ = load_parser()
review_results = []
for older, newer, ident, output_name in [
        ('review_232.md', 'review_232_v2.md', 'expanded_train:810478', 'expanded_train_810478_reviewed_task232_v1.txt'),
        ('review_253_v2.md', 'review_253_v3.md', 'expanded_train:95554', 'expanded_train_95554_reviewed_v2.txt')]:
    before = {resolve(row['cells'][0]): row for row in parse(read(DIRECTORY / older))}
    after = {resolve(row['cells'][0]): row for row in parse(read(DIRECTORY / newer))}
    assert len(before) == len(after) == 5 and set(before) == set(after)
    assert all(before[key]['raw'] == after[key]['raw'] for key in before if key != ident)
    assert after[ident]['cells'][1] == 'REVISE_TEXT'
    assert after[ident]['cells'][3] == str(DIRECTORY / output_name)
    review_results.append(dict(id=ident, newer_review=str((DIRECTORY / newer).relative_to(ROOT)),
                               unchanged_other_review_rows=4, body=str((DIRECTORY / output_name).relative_to(ROOT))))
read(Path(__file__).resolve())
result = dict(status='TWO_BIRTH_FOLLOWUP_BYTES_AND_CORRECTED_ORIGINAL_QUOTES_VERIFIED',
              rows=review_results, actual_root_full_new_body_reads=['112b8e', 'bc81f8'],
              actual_root_final_diff_and_sidecar_read='61919d',
              body_810478_unchanged=True, body_95554_only_one_label_closure=True,
              original_vs_previous_candidate_quote_distinguished=True,
              other_review_rows_unchanged=8, input_pins=pins,
              new_root_or_cache_adoptions=0, original_code_executed=False,
              whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'TWO_BIRTH_FOLLOWUPS_810478_95554_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], specific_sources=2, other_review_rows_unchanged=8,
                     new_root_or_cache_adoptions=0), ensure_ascii=False))
