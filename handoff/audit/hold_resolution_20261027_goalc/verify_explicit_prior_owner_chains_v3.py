"""Independently check link unions, role paths, exact reviews and byte pins."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser
from scripts.p106b_hold_resolution_author_output_bindings_v1 import declared_txt_basename as original_declared_txt_basename

pins = {}


def read(path):
    assert not path.is_symlink() and path.resolve().is_relative_to(AUDIT)
    data = path.read_bytes()
    assert 0 < len(data) < 20_000_000
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest().upper()
    return json.loads(data)


def checked(pin, archive=False):
    path = ROOT / (pin.get('archive', pin['path']) if archive else pin['path'])
    assert not path.is_symlink() and (path.resolve().is_relative_to(BASE) or path.resolve().is_relative_to(AUDIT))
    data = path.read_bytes()
    assert 0 < len(data) < 20_000_000
    assert hashlib.sha256(data).hexdigest().upper() == pin['sha256']
    return data


def role_of(review):
    marker = BASE.relative_to(ROOT).parts + ('agents',)
    parts = Path(review['path']).parts
    assert parts[:len(marker)] == marker
    return parts[len(marker)]


contract = read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
flags = read(AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json')
flag_ids = {row['id'] for row in flags['records'] if row.get('ordered_source_deletion') is False}
assert len(flag_ids) == 585
known = set(read(AUDIT / 'RUNTIME_PRIOR_REVIEW_OUTPUT_CHAIN_V1.json')['combined_record_scopes'])
assert len(known) == 390
resolve, parse, _ = load_parser()
successes = []
for version, expected_added in [(1, 52), (2, 14), (3, 8)]:
    value = read(AUDIT / f'EXPLICIT_PRIOR_OWNER_CHAINS_V{version}.json')
    successful = [row for row in value['rows'] if row['status'] == 'EXACT_PRIOR_AND_CURRENT_REVIEW_OUTPUT_CHAIN_VERIFIED']
    ids = {row['id'] for row in successful}
    assert len(ids) == expected_added and not (known & ids)
    assert ids <= flag_ids
    for row in successful:
        ident = row['id']
        # Apply both protection gates before review/body hashes.
        assert ident not in contract['restricted_ids']
        assert row['original']['sha256'] not in contract['restricted_hashes']
        checked(row['original'])
        checked(row['candidate'])
        assert row['prior']['output']['sha256'] == row['candidate']['sha256']
        for label in ['prior', 'current']:
            proof = row[label]
            review = checked(proof['review'], archive=True)
            assert role_of(proof['review']) == proof['role']
            entry = exact_entry(review, ident, flag_ids, resolve, lambda data: parse(data, allow_sections=True))
            assert entry['raw'] == proof['exact_review_row']
            checked(proof['output'])
        assert row['prior']['role'] != row['current']['role'] and row['distinct_named_roles']
        assert row['automatic_flag_waiver'] is False
        assert row['independent_semantic_pass_granted'] is False
        successes.append(ident)
    known |= ids
    assert known == set(value['combined_record_scopes'])
assert len(successes) == 74 and len(known) == 464 and len(flag_ids-known) == 121

# Exercise the new token adapter without opening any source or authored body.
adapter_path = AUDIT / 'trace_explicit_prior_owner_chains_v3.py'
definitions = [node for node in ast.parse(adapter_path.read_text(encoding='utf-8')).body
               if isinstance(node, ast.FunctionDef) and node.name in {'link_targets', 'declared_txt_basename'}]
assert len(definitions) == 2 and all(not node.decorator_list for node in definitions)
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(adapter_path), 'exec'), globals())
directory = BASE / 'agents/context_latin/root_join_conflict_counter_v1'
ident = 'expanded_train:10465'
paths = {label: {'path': str(BASE / 'root_join_conflict_counter_v1/inputs' / f'expanded_train_10465_{label}.txt')}
         for label in ['original', 'candidate']}
for cell in ['expanded_train_10465_v1.txt`; `hold_10465.md',
             '[expanded_train_10465_v1.txt](expanded_train_10465_v1.txt); [hold.md](hold.md)']:
    assert declared_txt_basename(cell, ident, directory, paths, 'EDIT_TEXT') == 'expanded_train_10465_v1.txt'
negative = [
    ('본문 없음', 'EDIT_TEXT'),
    ('expanded_train_10465_v1.txt; expanded_train_10465_v2.txt', 'EDIT_TEXT'),
    ('expanded_train_999999_v1.txt', 'EDIT_TEXT'),
    (str(BASE / 'agents/context_hangul/root_join_conflict_counter_v1/expanded_train_10465_v1.txt'), 'EDIT_TEXT'),
    ('expanded_train_10465_v1.txt', 'ADOPT_CANDIDATE'),
]
for cell, status in negative:
    try:
        declared_txt_basename(cell, ident, directory, paths, status)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid or ambiguous body reference accepted')
for path in [adapter_path, Path(__file__)]:
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
result = dict(status='INDEPENDENT_74_CHAIN_BYTES_ROLES_ROWS_AND_ADAPTER_REJECTIONS_VERIFIED',
              actual_additional_saved_chain_links=74, combined_linked_sources=464, remaining_unlinked_sources=121,
              adapter_positive_cases=2, adapter_negative_rejections=5, input_pins=pins,
              new_source_semantic_reads=0, automatic_flag_waivers=0, cache_adoptions=0,
              historical_input_delivery_proven=False, whole_goal_complete=False)
with (AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_INDEPENDENT_VERIFIED_V3.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({key: result[key] for key in ['status', 'actual_additional_saved_chain_links',
                 'combined_linked_sources', 'remaining_unlinked_sources', 'adapter_positive_cases',
                 'adapter_negative_rejections']}, ensure_ascii=False))
