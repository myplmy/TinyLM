"""Verify seven declared edits without rereading unchanged dictionary prose."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read_pin(pin):
    path = ROOT / pin['path']
    assert path.resolve().is_relative_to(BASE) or path.resolve().is_relative_to(AUDIT)
    data = path.read_bytes()
    assert len(data) < 20_000_000 and sha(data) == pin['sha256']
    return data


manifest_path = BASE / 'remaining_field_title_page_004_counter_v1/manifest.json'
snapshot_path = BASE / 'remaining_field_title_page_004_counter_v1_snapshots/v4/complete.json'
source = next(r for r in json.loads(manifest_path.read_text())['rows'] if r['id'] == 'expanded_train:46845')
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
assert source['id'] not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']
snapshot = json.loads(snapshot_path.read_text())
assert not snapshot['errors']
records = []
for pin in snapshot['shards']:
    records.extend(json.loads(read_pin(pin)))
record = next(r for r in records if r['id'] == source['id'])
assert record['role'] == 'context_hangul' and record['status'] == 'MATERIALIZED_BODY_NOT_ROOT_ADMISSION'
original, candidate = read_pin(source['original']), read_pin(source['candidate'])
assert original == candidate and len(original.decode('utf-8')) == 109206
body_pin = {'path': record['body'], 'sha256': record['clean_text_sha256']}
body = read_pin(body_pin)
lines = candidate.decode('utf-8').splitlines(keepends=True)
edits = {
    82: ('Metropolitan (if applicable):\n', ''),
    110: ('>Area>: 9,992 km² (mi²) ().\n', 'Area: 9,992 km².\n'),
    111: ('>Number of Provinces>: 2 (Potenza; Matera).\n', 'Number of Provinces: 2 (Potenza; Matera).\n'),
    112: ('>Number of Communes (Municipalities)>: 131.\n', 'Number of Communes (Municipalities): 131.\n'),
    113: ('>Population>: 591,338 (2007)\n', 'Population: 591,338 (2007)\n'),
    122: ('Area: 9,970 km²/ mi²\n', 'Area: 9,970 km²\n'),
    270: ('Bianchi (CS): A commune in the province of Cosenza. Population: (2006e).\n',
          'Bianchi (CS): A commune in the province of Cosenza.\n'),
}
for line_number, (before, after) in edits.items():
    assert lines[line_number - 1] == before, line_number
    lines[line_number - 1] = after
assert ''.join(lines).encode('utf-8') == body
review = record['review']
review_bytes = read_pin({'path': review['archive'], 'sha256': review['sha256']})
assert source['id'] in review_bytes.decode('utf-8')
result = {
    'status': 'SEVEN_EXACT_SOURCE_BOUND_LINE_EDITS_AND_ALL_OTHER_BYTES_VERIFIED_NOT_ADOPTED',
    'id': source['id'], 'original': source['original'], 'assigned_candidate': source['candidate'],
    'current_body': body_pin, 'review': review, 'original_characters': 109206,
    'original_and_assigned_candidate_exactly_equal': True,
    'source_line_edits': [{'line': n, 'before': pair[0], 'after': pair[1]} for n, pair in edits.items()],
    'all_other_bytes_unchanged': True,
    'full_original_reader_role': 'context_hangul',
    'root_read_method': 'FOUR_COMPLETE_INITIAL_CHANGE_HUNKS_AND_EXACT_THREE_FOLLOWUP_LABEL_CHANGES_NOT_FULL_DICTIONARY_READING',
    'initial_change_hunks_root_tool_chunk': '9fd89a',
    'root_full_original_read_claimed': False, 'whole_dictionary_errors_eliminated_claimed': False,
    'new_root_or_cache_adoptions': 0, 'protected_body_reads': 0, 'goal_complete': False,
    'input_pins': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
                   (manifest_path, snapshot_path, Path(__file__).resolve())},
}
out = AUDIT / 'FIELD_46845_EXACT_LOCAL_EDITS_VERIFIED_V1.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'original_characters': 109206, 'exact_changed_source_lines': 7,
                  'all_other_bytes_unchanged': True, 'new_cache_adoptions': 0}))
