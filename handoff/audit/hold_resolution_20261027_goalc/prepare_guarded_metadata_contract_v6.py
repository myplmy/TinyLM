"""Append one actual filter HOLD using existing metadata only, never its payload."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from active_guard_v5_preflight_v1 import activate, checked_contract, assert_no_protected_opens
from selection_metadata_store_v1 import SelectionStore
from scripts import p106b_hold_resolution_inventory as inv

activate()
old = checked_contract()
pins = {}


def read(path, expected):
    assert not path.is_symlink()
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == expected, str(path)
    pins[str(path.relative_to(ROOT))] = expected
    return json.loads(raw)


old_path = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V5.json'
manifest_path = inv.BASE/'remaining_field_title_page_015_counter_v1/manifest.json'
manifest = read(manifest_path, '1B2525C651B63A639A2825FC5B612BB4084CA8B20A1AB902B9D9C52018183D52')
source, = [row for row in manifest['rows'] if row['id'] == 'expanded_train:360211']
digest = '20361EF8F432B58ACAAEAA04D758AA52BA57C7D1D2C7B499B37B89D7FFA44480'
assert source['original']['sha256'] == source['candidate']['sha256'] == digest
assert source['role'] == 'legacy_review' and source['occurrences'] == 2
opaque_path = AUDIT/'OPAQUE_UNADOPTED_HOLD_ROOT32_ROSTER23_V1.json'
opaque = read(opaque_path, '87EB0550B9F11BC3EC4E6CBF6B75673A8785633B0522762F7E4277849292EFEF')
aliases = {}
for shard in opaque['hold_metadata_manifest']['shards']:
    path = ROOT/opaque['hold_metadata_directory']/shard['path']
    assert not path.is_symlink()
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == shard['sha256']
    pins[str(path.relative_to(ROOT))] = shard['sha256']
    for line in raw.splitlines():
        if digest.encode('ascii') in line:
            row = json.loads(line)
            assert row['original_text_sha256'] == digest and row['parent_decision'] == 'HOLD'
            aliases[row['id']] = row
assert set(aliases) == {'expanded_train:360211', 'historical_train:360215'}
for key in ['source','split','source_ids','source_ids_sha256','input_ids','original_text_sha256']:
    assert aliases[source['id']][key] == source[key]
selection_path = AUDIT/'ROOT_AUTHORED_SELECTIONS_V35.json'
selection_sha = 'DF7AA25488D2F8694588E98F866DCA61FDA66A62E8D8BB0395159B0287559BC3'
selection = SelectionStore(AUDIT).read(selection_path, selection_sha)
assert all(row['original_text_sha256'] != digest for row in selection['rows'])
pins[str(selection_path.relative_to(ROOT))] = selection_sha
entry = dict(id=source['id'], role=source['role'],
    cohort='remaining_field_title_page_015_counter_v1', original=source['original'],
    derived_candidate=source['candidate'], reading_parts=source['reading_parts'],
    occurrences=source['occurrences'], parent_alias_ids=sorted(aliases),
    disposition='ACTUAL_FILTER_METADATA_ONLY_HOLD_NOT_ADMITTED',
    reason='Author reported actual content-filter block; no further payload access or admission.',
    root_additional_payload_reads=0, additional_payload_hashing=0, body_admission_approved=False)
trusted = dict(old['trusted_metadata'], **aliases)
ids = sorted(set(old['restricted_ids']) | set(aliases))
hashes = sorted(set(old['restricted_hashes']) | {digest} |
                {item['sha256'] for item in source['reading_parts']})
assert len(ids) == 13 and len(trusted) == 21 and len(hashes) == 25
pins.update(old['input_pins'])
for path in [old_path, Path(__file__), AUDIT/'EXACT_FILTER_HOLD_360211_F3_F4_V1.md']:
    pins[str(path.relative_to(ROOT))] = inv.file_sha(path)
result = dict(old, status='CUMULATIVE_GUARD_V6_ONE_ACTUAL_FILTER_METADATA_HOLD',
    restricted_ids=ids, restricted_hashes=hashes,
    active_restricted_ids=ids, active_restricted_hashes=hashes,
    trusted_metadata=trusted, counts={'HOLD': len(trusted)},
    exact_source_parent_decisions={key:row['parent_decision'] for key,row in trusted.items()},
    previous_contract=dict(path=str(old_path.relative_to(ROOT)), sha256=inv.file_sha(old_path)),
    actual_filter_metadata_hold=entry, input_pins=pins,
    all_new_payload_reads_require_V6_first=True,
    all_new_global_cache_and_consumer_reads_require_V6=True,
    inherited_guard_flags_are_historical=True,
    root_additional_payload_reads=0, additional_payload_hashing=0,
    goal_complete=False, training_authorized=False)
assert_no_protected_opens()
out = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V6.json'
assert not out.exists() and not out.is_symlink()
inv.write_json(out, result)
print(json.dumps(dict(status=result['status'], sha256=inv.file_sha(out),
    ids=len(ids), hashes=len(hashes), aliases=len(trusted), payload_reads=0)))
