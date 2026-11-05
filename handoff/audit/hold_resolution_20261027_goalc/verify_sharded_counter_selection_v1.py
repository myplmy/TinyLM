"""Independently reconstruct and recount a versioned counter selection.

Does not import the storage writer/loader or open corpus TXT.  Verifies physical
manifest/shard pins, native logical bytes, unchanged prior rows and new closure.
"""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import re

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def compact(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                       allow_nan=False) + chr(10)).encode('utf-8')


def read(path, expected=None):
    path = Path(path)
    assert (path.resolve().is_relative_to(AUDIT) or path.resolve().is_relative_to(BASE)
            or path.resolve() == ROOT/'scripts/p106b_hold_resolution_policy_v26.py')
    assert not path.is_symlink() and path.suffix != '.txt'
    raw = path.read_bytes()
    assert 0 < len(raw) < 20_000_000
    actual = sha(raw)
    assert expected is None or actual == expected, str(path)
    pins[str(path.relative_to(ROOT))] = actual
    return raw


def native(path, expected):
    raw = read(path, expected)
    value = json.loads(raw)
    if 'selection_storage_schema' not in value:
        assert value['source_ids'] == len(value['rows'])
        return value, dict(physical_bytes=len(raw), sharded=False)
    assert value['selection_storage_schema'] == 'TINYLM_SELECTION_ROWS_V1'
    assert value['logical_name'] == path.name
    assert value['canonical_encoding'] == 'UTF8_COMPACT_JSON_PLUS_LF_V1'
    assert len(value['native_key_order']) == len(set(value['native_key_order']))
    assert value['native_key_order'].count('rows') == 1
    assert set(value['native_metadata']) == set(value['native_key_order']) - {'rows'}
    rows, shard_bytes = [], 0
    for pin in value['row_shards']:
        assert re.fullmatch(r'[0-9A-F]{64}', pin['sha256'])
        assert pin['path'] == 'selection_metadata_row_shards_v1/' + pin['sha256'] + '.json'
        part = AUDIT / pin['path']
        assert not part.parent.is_symlink()
        part_raw = read(part, pin['sha256'])
        assert len(part_raw) == pin['bytes'] <= 4_000_000
        group = json.loads(part_raw)
        assert isinstance(group, list) and 0 < len(group) == pin['rows'] <= 512
        assert compact(group) == part_raw
        rows.extend(group)
        shard_bytes += len(part_raw)
    result = {key: rows if key == 'rows' else value['native_metadata'][key]
              for key in value['native_key_order']}
    logical = compact(result)
    assert len(logical) == value['logical_json_bytes']
    assert sha(logical) == value['logical_json_sha256']
    assert len(rows) == value['source_ids'] == result['source_ids']
    assert len({r['id'] for r in rows}) == len(rows)
    return result, dict(physical_bytes=len(raw), sharded=True,
        row_shards=len(value['row_shards']), total_shard_bytes=shard_bytes,
        logical_json_bytes=len(logical), logical_json_sha256=sha(logical))


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', type=int, required=True)
parser.add_argument('--expected-sha', required=True)
args = parser.parse_args()
path = AUDIT / ('ROOT_AUTHORED_SELECTIONS_V' + str(args.version) + '.json')
selection, storage = native(path, args.expected_sha)
prior_pin = selection['prior_selection']
previous, _ = native(ROOT / prior_pin['path'], prior_pin['sha256'])
previous_rows = previous['rows']
assert selection['rows'][:len(previous_rows)] == previous_rows
new_rows = selection['rows'][len(previous_rows):]
assert len(new_rows) == selection['new_approved_sources']
closure_pin = selection['closure']
closure = json.loads(read(ROOT / closure_pin['path'], closure_pin['sha256']))
assert closure['root_training_TXT_authored'] == closure['guard_failures_waived'] == 0
assert closure['protected_payload_open_attempts'] == 0
assert closure['active_guard_sha256'] == '01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338'
assert closure['root_approved_new_sources'] == len(new_rows)
assert closure['root_approved_new_positions'] == selection['new_approved_positions']
assert previous['expected_roster_HOLD_unique'] - len(new_rows) == selection['expected_roster_HOLD_unique']
assert previous['expected_roster_HOLD_positions'] - selection['new_approved_positions'] == selection['expected_roster_HOLD_positions']
assert Counter(row['selected']['decision'] for row in selection['rows']) == selection['counts']
checks = {item['id']: item for item in closure['checks']}
assert len(checks) == len(closure['checks'])
new_ids = {row['id'] for row in new_rows}
assert {key for key, item in checks.items() if all(item['guards'].values())} == new_ids
deferred_ids = {item['id'] for item in closure['individual_deferred']}
assert set(checks) - new_ids <= deferred_ids
source_manifest = json.loads(read(BASE/'root12_independent_admission_counter_v1/manifest.json',
    'A71B3109889F32F5969298287C7ADA9B1C223130A8603D87B80D2D910A57527D'))
sources = {row['id']: row for row in source_manifest['rows']}
assert len(sources) == len(source_manifest['rows']) == 3688
assert sum(sources[key]['occurrences'] for key in new_ids) == selection['new_approved_positions']
for row in new_rows:
    check = checks[row['id']]
    source = sources[row['id']]
    assert row['root_approved'] is True and row['cache_admitted'] is False
    assert all(check['guards'].values())
    assert row['selected']['body'] == check['body']['path']
    assert row['selected']['clean_text_sha256'] == check['body']['sha256']
    assert row['original_text_sha256'] == check['original']['sha256']
    assert check['primary_review'] != check['counter_review']
    assert check['primary_review'] == source['prior_review']
    assert source['primary_author_role'] != source['role']
    assert '/agents/' + source['role'] + '/' in check['counter_review']['path']
guard = json.loads(read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V5.json', closure['active_guard_sha256']))
assert not {r['id'] for r in new_rows} & set(guard['restricted_ids'])
for name, expected in closure['input_pins'].items():
    target = ROOT / name
    assert target.suffix != '.txt', 'this verifier is metadata-only'
    read(target, expected)
pins[str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__).read_bytes())
receipt = dict(status='SHARDED_COUNTER_SELECTION_INDEPENDENTLY_RECONSTRUCTED_AND_RECOUNTED',
    selection=dict(path=str(path.relative_to(ROOT)), sha256=args.expected_sha),
    source_ids=len(selection['rows']), preserved_prior_rows=len(previous_rows),
    new_sources=len(new_rows), new_positions=selection['new_approved_positions'],
    expected_HOLD_positions=selection['expected_roster_HOLD_positions'],
    expected_HOLD_unique=selection['expected_roster_HOLD_unique'],
    storage=storage, all_new_guards_closed=True, source_or_candidate_payload_opened=0,
    input_pins=pins, cache_admitted=False, goal_complete=False, training_authorized=False)
out = AUDIT / ('ROOT' + str(args.version) + '_SHARDED_SELECTION_INDEPENDENT_VERIFIED_V1.json')
raw = (json.dumps(receipt, ensure_ascii=False, indent=2) + chr(10)).encode('utf-8')
assert len(raw) < 20_000_000
with out.open('xb') as stream:
    stream.write(raw)
print(json.dumps(dict(verified=True, source_ids=receipt['source_ids'],
    new_sources=receipt['new_sources'], new_positions=receipt['new_positions'],
    storage=storage, receipt_sha256=sha(raw)), ensure_ascii=False))
