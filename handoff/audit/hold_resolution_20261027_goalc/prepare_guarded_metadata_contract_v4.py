"""Extend the opaque contract using metadata only, never classified payloads."""
from pathlib import Path
from collections import Counter
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

previous_path = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
assert inv.file_sha(previous_path) == '7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
previous = inv.cache.read(previous_path)
projector_path = AUDIT/'guarded_scan_metadata_v1.py'
assert inv.file_sha(projector_path) == previous['input_pins'][str(projector_path.relative_to(ROOT))]
spec = importlib.util.spec_from_file_location('frozen_text_free_guard_projector_v4', projector_path)
metadata_reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata_reader)
metadata_reader.FIELDS = set(metadata_reader.FIELDS) | {'decision'}

manifest_path = inv.BASE/'remaining_field_title_page_012_counter_v1/manifest.json'
assert inv.file_sha(manifest_path) == '400854324612FC862A9A96F497AAD8BA62591A5B7B002EBB21E8F72A20D7F08A'
manifest = inv.cache.read(manifest_path)
new_id = 'expanded_train:267902'
source = next(row for row in manifest['rows'] if row['id'] == new_id)
new_sha = 'F933C7533EF3E4A0CC889C91CBEF329AC09DD8025492A84A025BDF4699F1909A'
assert source['original']['sha256'] == source['candidate']['sha256'] == new_sha
assert source['role'] == 'historical_review'
assert new_id not in previous['restricted_ids'] and new_sha not in previous['restricted_hashes']

report_path = inv.PARENT/'built.json'
assert inv.file_sha(report_path) == '47F117C11261581E82A1594DC4E2F4706400CF868FBB2F39521B47C917EDA7DE'
report = inv.cache.read(report_path)
directory = inv.PARENT/'ledger'
inv.verify(directory, report['manifests']['ledger'])
fields = ['id', 'source', 'split', 'source_ids', 'source_ids_sha256',
          'original_text_sha256', 'input_ids']
aliases = {}
needle = new_sha.encode('ascii')
for shard in report['manifests']['ledger']['shards']:
    with (directory/shard['path']).open('rb') as stream:
        for line in stream:
            if needle not in line:
                continue
            row = metadata_reader.project_metadata(line)
            if row.get('original_text_sha256') != new_sha:
                continue
            assert row['id'] not in aliases
            assert row['decision'] in {'HOLD', 'EXCLUDE'}, 'admitted parent needs explicit mediation'
            aliases[row['id']] = {key: row[key] for key in fields}
            aliases[row['id']]['parent_decision'] = row['decision']
assert len(aliases) == source['occurrences']
expected = {key: source[key] for key in fields}
assert {key: aliases[new_id][key] for key in fields} == expected
trusted = dict(previous['trusted_metadata'])
for key, value in aliases.items():
    assert key not in trusted or trusted[key] == value
    trusted[key] = value
assert all(trusted[key] == value for key, value in previous['trusted_metadata'].items())

result = dict(previous)
restricted_ids = list(previous['restricted_ids']) + [new_id]
restricted_hashes = list(previous['restricted_hashes']) + [new_sha]
result.update(status='METADATA_ONLY_CUMULATIVE_GUARD_V4_WITH_COMPLETE_NEW_SOURCE_ALIASES',
    restricted_ids=restricted_ids, restricted_hashes=restricted_hashes,
    active_restricted_ids=restricted_ids, active_restricted_hashes=restricted_hashes,
    trusted_metadata=trusted, counts=dict(Counter(r['parent_decision'] for r in trusted.values())),
    previous_contract=dict(path=str(previous_path.relative_to(ROOT)), sha256=inv.file_sha(previous_path)),
    new_restricted_entry=dict(id=new_id, original=source['original'],
        derived_candidate=source['candidate'], occurrences=source['occurrences'],
        decision='HOLD_NOT_REWRITTEN_OR_ADMITTED',
        reason='Operational controlled-substance procedure identified by assigned author; retain metadata without reproducing procedural content.',
        author_initial_read_preceded_new_restriction=True,
        root_new_original_or_candidate_file_reads=0,
        technical_detail_quoted_in_new_artifacts=False, parent_alias_ids=sorted(aliases)),
    new_source_parent_alias_count=len(aliases), new_parent_alias_payload_decodes=0,
    all_new_payload_reads_require_V4_first=True,
    all_new_global_cache_and_consumer_reads_require_V4=True,
    V3_frozen_disjoint_scope_reproduction_requires_active_V4_preflight=True,
    inherited_requirement_flags_are_frozen_provenance_not_current_authorization=True,
    original_or_candidate_bodies_opened=0, goal_complete=False, training_authorized=False)
result['exact_source_parent_decisions'] = dict(previous['exact_source_parent_decisions'],
    **{key: value['parent_decision'] for key, value in aliases.items()})
result['input_pins'] = dict(previous['input_pins'], **{
    str(path.relative_to(ROOT)): inv.file_sha(path)
    for path in [previous_path, manifest_path, report_path, projector_path, Path(__file__)]})
result['parent_ledger_manifest_is_embedded_in_built_receipt'] = True
result['parent_ledger_shard_pins'] = {
    str((directory/shard['path']).relative_to(ROOT)): shard['sha256']
    for shard in report['manifests']['ledger']['shards']}
assert len(result['restricted_ids']) == 9 and len(result['restricted_hashes']) == 10
out = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V4.json'
assert not out.exists()
inv.write_json(out, result)
print(json.dumps(dict(status=result['status'], canonical_restricted_sources=9,
    restricted_hashes=10, trusted_alias_positions=len(trusted), new_alias_ids=sorted(aliases),
    new_alias_parent_decisions={k: v['parent_decision'] for k, v in aliases.items()},
    source_body_opens=0, sha256=inv.file_sha(out))))
