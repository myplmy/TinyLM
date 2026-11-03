"""Join saved distinct-reader evidence without granting semantic/cache closure."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

root_path = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V10.json'
guard_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
manifest_path = inv.BASE / 'birth_root11_independent_v1/manifest.json'
snapshot_path = inv.BASE / 'birth_root11_independent_v1_snapshots/v3/complete.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
root = inv.cache.read(root_path)
guards = {r['id']: r for r in inv.cache.read(guard_path)['records'] if r.get('ordered_source_deletion') is False}
assert len(guards) == 585
sources = {r['id']: r for r in inv.cache.read(manifest_path)['rows']}
snapshot = inv.cache.read(snapshot_path)
contract = inv.cache.read(contract_path)
root_ids = {r['id'] for r in root['rows']}
assert len(root_ids) == 21 and root_ids <= set(guards)
corrections = {r['id']: r['body'] for r in root['new_reviewed_birth_corrections'] +
               root['new_reviewed_followup_corrections']}
records = []
for pin in snapshot['shards']:
    assert inv.file_sha(ROOT / pin['path']) == pin['sha256']
    records.extend(inv.cache.read(ROOT / pin['path']))
assert len(records) == len(sources) == 2707
saved = []
for row in records:
    if row['status'] == 'NO_SAVED_REVIEW_ROW':
        continue
    source = sources[row['id']]
    assert row['id'] not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    assert row['role'] == source['role'] != source['previous_editor_role']
    assert row['role'] != source.get('correction_author_role')
    assert row['status'] in {'PINNED_BODY_NOT_ROOT_ADMISSION', 'MATERIALIZED_BODY_NOT_ROOT_ADMISSION'}
    assert row['review'] and row['read_scope'] and row.get('body')
    flagged = guards.get(row['id'])
    binding = 'NOT_IN_ORDERED_FLAG_SET'
    if flagged:
        assert source['original']['sha256'] == flagged['original_text_sha256']
        if source['candidate']['sha256'] == flagged['clean_text_sha256']:
            binding = 'EXACT_OLD_ROOT11_FLAGGED_BODY'
        else:
            assert source['candidate']['sha256'] == corrections[row['id']]['sha256']
            assert row['id'] in root_ids
            binding = 'ROOT_REVIEWED_REPLACEMENT_FOR_SAME_FLAGGED_SOURCE'
    saved.append({'id': row['id'], 'reviewer_role': row['role'],
        'previous_editor_role': source['previous_editor_role'], 'original': source['original'],
        'independent_input_candidate': source['candidate'], 'old_flag_binding': binding,
        'review': row['review'], 'declared_actual_read_scope': row['read_scope'],
        'saved_body': {'path': row['body'], 'sha256': row['clean_text_sha256']},
        'new_body_differs_from_independent_input': row['clean_text_sha256'] != source['candidate']['sha256'],
        'root_adoption': False, 'semantic_closure_automatically_granted': False})
saved_ids = {r['id'] for r in saved}
flag_saved_ids = saved_ids & set(guards)
overlap = root_ids & flag_saved_ids
union = root_ids | flag_saved_ids
pins = {str(p.relative_to(ROOT)): inv.file_sha(p) for p in
        (root_path, guard_path, manifest_path, snapshot_path, contract_path, Path(__file__).resolve())}
result = {'status': 'SAVED_DISTINCT_REVIEW_EVIDENCE_COVERAGE_NOT_FINAL_QUALITY_OR_CACHE_CLOSURE',
    'ordered_flag_sources': 585, 'root_direct_full_read_annotations': len(root_ids),
    'birth_second_saved_review_sources': len(saved_ids),
    'birth_saved_sources_in_ordered_flag_set': len(flag_saved_ids),
    'overlapping_root_and_birth_saved_flag_sources': len(overlap),
    'flag_sources_with_either_actual_root_read_or_saved_distinct_review_record': len(union),
    'flag_sources_without_either_record_at_frozen_versions': 585 - len(union),
    'root_ledger_without_direct_root_annotation': 585 - len(root_ids),
    'birth_new_authored_bodies_still_requiring_root_review': sum(r['new_body_differs_from_independent_input'] for r in saved),
    'rows': saved, 'input_pins': pins, 'root_or_cache_adoptions': 0,
    'automatic_flag_waivers': 0, 'protected_body_reads': 0, 'goal_complete': False,
    'limits': 'The two review scopes overlap. Saved read-scope statements and exact inputs are linked here; new corrections and final admission still require root judgment. This is not proof that an unchanged candidate has passed all quality checks.'}
out = AUDIT / 'ROOT11_AND_BIRTH_SAVED_REVIEW_COVERAGE_BRIDGE_V1.json'
inv.write_json(out, result)
print(json.dumps({k: v for k, v in result.items() if isinstance(v, (int, bool))}))
