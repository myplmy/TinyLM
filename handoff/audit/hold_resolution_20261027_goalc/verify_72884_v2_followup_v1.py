"""Verify the authored narrow followup and retained named territorial entries."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
DIRECTORY = BASE / 'agents/legacy_review/remaining_field_title_page_006_counter_v1'
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser

pins = {}


def read(path):
    assert not path.is_symlink()
    assert path.resolve().is_relative_to(BASE) or path.resolve().is_relative_to(AUDIT)
    payload = path.read_bytes()
    assert 0 < len(payload) < 20_000_000
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest().upper()
    return payload


contract = json.loads(read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'))
assert pins[str((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').relative_to(ROOT))] == (
    'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF')
manifest = json.loads(read(BASE / 'remaining_field_title_page_006_counter_v1/manifest.json'))
source = next(row for row in manifest['rows'] if row['id'] == 'expanded_train:72884')
assert source['id'] not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']
original_bytes = read(ROOT / source['original']['path'])
assert hashlib.sha256(original_bytes).hexdigest().upper() == source['original']['sha256']
original = original_bytes.decode('utf-8')
before = read(DIRECTORY / 'expanded_train_72884_revised_task002_v1.txt')
after = read(DIRECTORY / 'expanded_train_72884_revised_task002_v2.txt')
assert hashlib.sha256(after).hexdigest().upper() == '378ABB2DE229DB20974B81CD0B46155B59413884D65DB2C5D1B5A0B46359FFCC'
expected = before
edits = [('미국 제국주의(美國帝國主義)는, 줄여서', '미국 제국주의(美國帝國主義), 줄여서'),
         ('령 동플로리다와 서플로리다 (1815년 - )', '동플로리다와 서플로리다 (1815년 - )')]
for old, new in edits:
    assert expected.count(old.encode('utf-8')) == 1
    expected = expected.replace(old.encode('utf-8'), new.encode('utf-8'), 1)
assert expected == after
text = after.decode('utf-8')
named_entries = [
    '미국 동부 영토 (1776년 - ) (기존에 거주하던 아메리카 토착민들을 무력으로 쫓아내고 획득)',
    '워싱턴 D.C.',
    '루이지애나 (1803년 - ) (나폴레옹에게 헐값에 인수함)',
    '동플로리다와 서플로리다 (1815년 - ) (현재는 미국의 주)',
    '텍사스 공화국 (1836년 - ) (현재는 미국의 주)',
    '영국령 브리티시컬럼비아주의 일부분 (1846년 - ) (현재는 미국의 주)',
    '파나마운하 지대 (1903년 - 1999년) (현재는 파나마에 반환)',
    '태평양의 신탁통치령 제도 (1944년 - 1990년)',
]
assert all(entry in original and entry in text for entry in named_entries)
assert [text.index(entry) for entry in named_entries] == sorted(text.index(entry) for entry in named_entries)
hold = read(DIRECTORY / 'hold_72884_task002_v2.md').decode('utf-8')
quotes = [line[2:].strip() for line in hold.splitlines() if line.startswith('> ')]
assert quotes and all(quote in original for quote in quotes)
assert 'PNAC의 원칙(PNAC\'s principles)에서는 아래와 같이 기술되어 있다.' in hold
assert 'PNAC의 원칙(PNAC\'s principles)에서는 아래와 같이 기술되어 있다.' not in text
assert '령 루이지애나' in hold and '령 동플로리다와 서플로리다' in hold
assert '1898년 - 1946년' in hold and '1916년 - 1922년' in hold
assert '중 리오그란데강의 서부' in hold and '의 영토 일부분 (1848년 - )' in hold

resolve, parse, _ = load_parser()
older = {resolve(row['cells'][0]): row for row in parse(read(DIRECTORY / 'review_002_v2.md'))}
newer = {resolve(row['cells'][0]): row for row in parse(read(DIRECTORY / 'review_002_v3.md'))}
assert len(older) == len(newer) == 5 and set(older) == set(newer)
assert all(older[key]['raw'] == newer[key]['raw'] for key in older if key != source['id'])
output = newer[source['id']]['cells'][3]
assert output in {str(DIRECTORY / 'expanded_train_72884_revised_task002_v2.txt'),
                  'expanded_train_72884_revised_task002_v2.txt'}
read(Path(__file__).resolve())
result = dict(status='ROOT_72884_NEW_BODY_CONTEXT_AND_NARROW_FOLLOWUP_VERIFIED',
              id=source['id'], original=source['original'],
              body=dict(path=str((DIRECTORY / 'expanded_train_72884_revised_task002_v2.txt').relative_to(ROOT)),
                        sha256=hashlib.sha256(after).hexdigest().upper()),
              actual_root_full_new_body_diff_and_sidecar_read='d43dc3',
              actual_root_original_candidate_and_followup_full_diffs='f55788',
              allowed_followup_edits=2, outside_followup_bytes_unchanged=True,
              named_entry_relations_preserved=8, actual_original_sidecar_quotes=len(quotes),
              other_review_rows_unchanged=4, source_facts_independently_verified=False,
              current_geopolitical_status_claimed=False, input_pins=pins,
              new_root_or_cache_adoptions=0, whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'ROOT_72884_V2_FOLLOWUP_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], retained_named_entries=8,
                     followup_edits=2, other_review_rows_unchanged=4, root_adopted=0), ensure_ascii=False))
