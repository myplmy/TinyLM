"""Independently join every frozen HOLD ledger position to a new opaque manifest."""
from collections import Counter
from pathlib import Path
import json
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_scan_metadata_v1 as metadata

contract_path = AUDIT/'OPAQUE_HOLD_ROOT28_ROSTER20_CONTRACT_V1.json'
assert inv.file_sha(contract_path) == '3F0E1828F8637C34F0303149D409813F0929F3A848541C5C68BD1646294A7EBA'
contract = inv.cache.read(contract_path)
for name, expected in contract['input_pins'].items(): assert inv.file_sha(ROOT/name) == expected
directory = ROOT/contract['hold_metadata_directory']
inv.verify(directory, contract['hold_metadata_manifest'])
actual = {}
for row in inv.cache.rows(directory, contract['hold_metadata_manifest']):
    assert row['id'] not in actual and row['parent_decision'] == 'HOLD'
    actual[row['id']] = row
hashes = set(contract['hold_hashes'])
assert {row['original_text_sha256'] for row in actual.values()} == hashes
parent_path = inv.PARENT/'built.json'
parent = inv.cache.read(parent_path)
inv.verify(inv.PARENT/'hold', parent['manifests']['hold'])
seen, counts = set(), Counter()
with patch.object(metadata, 'FIELDS', metadata.FIELDS | {'decision'}):
    for shard in parent['manifests']['hold']['shards']:
        with (inv.PARENT/'hold'/shard['path']).open('rb') as stream:
            for line in stream:
                row = metadata.project_metadata(line)
                if row['original_text_sha256'] not in hashes: continue
                assert row['decision'] == 'HOLD' and row['id'] not in seen
                assert row['id'] in actual
                for key in metadata.IDENTITY_FIELDS: assert actual[row['id']][key] == row[key]
                seen.add(row['id']); counts.update(positions=1, input_ids=row['input_ids'])
assert seen == set(actual) and dict(counts) == contract['counts']
assert len(hashes) == 68134 and counts['positions'] == 106236 and counts['input_ids'] == 189933477
guard = inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V4.json')
for ident in ['expanded_train:267902', 'historical_train:267904']:
    assert actual[ident] == guard['trusted_metadata'][ident]
result = dict(status='ALL_CURRENT_HOLD_POSITIONS_INDEPENDENTLY_MATCH_FROZEN_PARENT_HOLD_LEDGER',
    unique_sources=len(hashes), counts=dict(counts), all_individual_files_under_20000000=True,
    new_restricted_alias_positions_opaque_and_still_HOLD=True,
    actual_scan_or_original_payload_files_opened=0, body_fields_decoded=0,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in
        [contract_path, parent_path, AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V4.json',
         AUDIT/'guarded_scan_metadata_v1.py', Path(__file__)]},
    goal_complete=False, training_authorized=False)
output = AUDIT/'OPAQUE_HOLD_ROOT28_ROSTER20_INDEPENDENT_VERIFIED_V1.json'
assert not output.exists(); inv.write_json(output, result)
print(json.dumps(dict(status=result['status'], counts=dict(counts), sha256=inv.file_sha(output))), flush=True)
