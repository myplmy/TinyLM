"""Metadata-only partition of the entire unresolved literal-context type."""
from collections import Counter
from pathlib import Path
import json
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
import guarded_scan_metadata_v1 as metadata

REASON = 'GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL'
OUT = inv.BASE / 'remaining_literal_full_sources_v1'
inv.require(not OUT.exists(), 'new immutable literal census namespace required')
join_path = inv.BASE / 'resolution_join_plan_v4/complete.json'
ownership_paths = [inv.BASE / name / 'manifest.json' for name in
                   ('repeat_named_roles_counter_v2', 'remaining_birth_full_counter_v1')]
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
join, contract = map(inv.cache.read, (join_path, contract_path))
inv.require(join['full_restricted_original_bodies_opened'] is False, 'guarded join required')
assigned = {}
for path in ownership_paths:
    for row in inv.cache.read(path)['rows']:
        key = row['original_text_sha256']
        inv.require(key not in assigned, 'existing review ownership must be disjoint')
        assigned[key] = dict(id=row['id'], role=row['role'], cohort=path.parent.name)
blocked_ids, blocked_shas = set(contract['restricted_ids']), set(contract['restricted_hashes'])
directory = join_path.parent / join['records_directory']
inv.verify(directory, join['manifest'])
writer = inv.ShardWriter(OUT / 'rows', 'pending_literal_sources', limit=19_999_999)
counts, overlap, restricted = Counter(), [], []
fields = metadata.FIELDS | {'decision', 'reason', 'occurrences', 'language_bucket', 'review_status'}
with patch.object(metadata, 'FIELDS', fields):
    for shard in join['manifest']['shards']:
        with (directory / shard['path']).open('rb') as stream:
            for line in stream:
                row = metadata.project_metadata(line)
                if row['decision'] != 'HOLD' or REASON not in row['reason'].split(','):
                    continue
                counts.update(whole_type_unique=1, whole_type_positions=row['occurrences'])
                key = row['original_text_sha256']
                if row['id'] in blocked_ids or key in blocked_shas:
                    restricted.append(dict(id=row['id'], original_text_sha256=key,
                                           occurrences=row['occurrences']))
                    counts.update(restricted_unique=1, restricted_positions=row['occurrences'])
                    continue
                if key in assigned:
                    overlap.append(dict(**assigned[key], original_text_sha256=key,
                                        occurrences=row['occurrences']))
                    counts.update(current_owned_unique=1, current_owned_positions=row['occurrences'])
                    continue
                record = {name: row[name] for name in ('id', 'source', 'split', 'source_ids',
                    'source_ids_sha256', 'original_text_sha256', 'input_ids', 'language_bucket', 'occurrences')}
                record.update(previous_reasons=row['reason'].split(','),
                    named_review_strata=['ENTIRE_REMAINING_LITERAL_PROGRAM_CONTEXT_TYPE'],
                    root_approved=False, cache_admitted=False)
                writer.append(record)
                counts.update(queued_unique=1, queued_positions=row['occurrences'])
inv.require(counts['whole_type_unique'] == join['pending_reasons_unique'][REASON] == 1793,
            'entire pending literal type must be conserved')
for unit in ('unique', 'positions'):
    inv.require(counts['whole_type_' + unit] == sum(counts[name + '_' + unit] for name in
        ('queued', 'current_owned', 'restricted')), 'ownership partition differs')
paths = [join_path, *ownership_paths, contract_path,
         AUDIT / 'REMAINING_LITERAL_FULL_SOURCE_SCOPE_V1.md',
         AUDIT / 'guarded_scan_metadata_v1.py', Path(__file__)]
pins = {str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths}
manifest = writer.close(lineage=dict(input_pins=pins))
result = dict(status='ENTIRE_LITERAL_TYPE_METADATA_PARTITION_NOT_REVIEW_OR_ADMISSION',
    counts=dict(counts), rows=manifest, current_owned=overlap, restricted_metadata_only=restricted,
    input_pins=pins, original_bodies_decoded=False, body_changed=0, cache_admitted=0,
    goal_complete=False, training_authorized=False)
inv.write_json(OUT / 'complete.json', result)
print(json.dumps(dict(status=result['status'], counts=dict(counts)), ensure_ascii=False))
