"""Complete the new restriction's aliases from immutable text-free ledger."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_scan_metadata_v1 as metadata_reader

# Add only a disposition enum to the existing text-free projection, in memory.
metadata_reader.FIELDS = set(metadata_reader.FIELDS) | {'decision'}
project_metadata = metadata_reader.project_metadata

previous_path = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V2.json'
assert inv.file_sha(previous_path) == 'E0EF117564ED4632D1A2C63F40AB66EB9620D416AE8BF516FD1AE3204286EF8B'
previous = inv.cache.read(previous_path)
report_path = inv.PARENT/'built.json'
assert inv.file_sha(report_path) == '47F117C11261581E82A1594DC4E2F4706400CF868FBB2F39521B47C917EDA7DE'
report = inv.cache.read(report_path)
directory = inv.PARENT/'ledger'
inv.verify(directory,report['manifests']['ledger'])
new_id = previous['new_restricted_entry']['id']
new_sha = previous['new_restricted_entry']['original']['sha256']
fields = ['id','source','split','source_ids','source_ids_sha256','original_text_sha256','input_ids']
aliases = {}
for shard in report['manifests']['ledger']['shards']:
    with (directory/shard['path']).open('rb') as stream:
        for line in stream:
            # These are metadata ledger records, never raw native scan bodies.
            if new_sha.encode('ascii') not in line:
                continue
            row = project_metadata(line)
            if row.get('original_text_sha256') != new_sha:
                continue
            assert row['id'] not in aliases
            aliases[row['id']] = {key:row[key] for key in fields}
            assert row['decision'] in {'HOLD','EXCLUDE'}
            aliases[row['id']]['parent_decision'] = row['decision']
assert len(aliases) == previous['new_restricted_entry']['occurrences'] == 2
assert aliases[new_id] == previous['trusted_metadata'][new_id]
metadata = dict(previous['trusted_metadata'])
for key,value in aliases.items():
    assert key not in metadata or metadata[key] == value
    metadata[key] = value
result = dict(previous)
result.update(status='METADATA_ONLY_CUMULATIVE_GUARD_V3_WITH_COMPLETE_NEW_SOURCE_ALIASES',
    trusted_metadata=metadata,counts=dict(Counter(row['parent_decision'] for row in metadata.values())),
    previous_contract=dict(path=str(previous_path.relative_to(ROOT)),sha256=inv.file_sha(previous_path)),
    new_restricted_entry=dict(previous['new_restricted_entry'],parent_alias_ids=sorted(aliases)),
    new_source_parent_alias_count=len(aliases),new_parent_alias_payload_decodes=0,
    all_new_global_cache_and_consumer_reads_require_V3=True,
    V2_exact_frozen_cohort_collection_remains_reproducible=True)
result['input_pins'] = dict(previous['input_pins'],**{
    str(path.relative_to(ROOT)):inv.file_sha(path)
    for path in (previous_path,report_path,Path(__file__),AUDIT/'guarded_scan_metadata_v1.py')})
result['parent_ledger_manifest_is_embedded_in_built_receipt'] = True
result['parent_ledger_shard_pins'] = {
    str((directory/shard['path']).relative_to(ROOT)):shard['sha256']
    for shard in report['manifests']['ledger']['shards']}
output = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
assert not output.exists()
inv.write_json(output,result)
print(json.dumps(dict(status=result['status'],new_alias_ids=sorted(aliases),
    trusted_alias_positions=len(metadata),restricted_ids=len(result['restricted_ids']),
    restricted_hashes=len(result['restricted_hashes']),sha256=inv.file_sha(output))))
