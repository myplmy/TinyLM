"""Reconcile ten individually reviewed HOLDs without admitting any new body."""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

snapshot_path = inv.BASE / 'remaining_literal_full_counter_v1_snapshots/v20/complete.json'
manifest_path = inv.BASE / 'remaining_literal_full_counter_v1/manifest.json'
new_hold_path = AUDIT / 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V3.json'
prior_hold_path = AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD37_V1.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
snapshot = inv.cache.read(snapshot_path)
sources = {r['id']: r for r in inv.cache.read(manifest_path)['rows']}
contract = inv.cache.read(contract_path)
assert len(sources) == 1793 and not snapshot['errors']
assert all(r['saved'] == r['expected'] and not r['awaiting_review'] for r in snapshot['coverage'].values())
assert not (set(sources) & set(contract['restricted_ids']))
assert not ({r['original']['sha256'] for r in sources.values()} & set(contract['restricted_hashes']))
new_holds = {r['id']: r for r in inv.cache.read(new_hold_path)['rows']}
old_hold = next(r for r in inv.cache.read(prior_hold_path)['rows'] if r['id'] == 'expanded_train:1046282')
assert len(new_holds) == 9 and old_hold['second_review']['full_original_read']
holds = dict(new_holds, **{old_hold['id']: old_hold})
records = []
for pin in snapshot['shards']:
    assert inv.file_sha(ROOT / pin['path']) == pin['sha256']
    records.extend(inv.cache.read(ROOT / pin['path']))
assert len(records) == 1793 and {r['id'] for r in records} == set(sources)
body_ids, reviewed_holds = [], []
for row in records:
    source = sources[row['id']]
    if row['status'] == 'TEXT_ADJUDICATION_NOT_ADMISSION':
        proof = holds[row['id']]
        assert proof['original'] == source['original']
        assert proof['decision'] == 'HOLD'
        assert proof.get('root_approved_nonadmission', proof.get('root_approved'))
        assert proof.get('full_original_actually_read', proof.get('second_review', {}).get('full_original_read'))
        reviewed_holds.append({'id': row['id'], 'original': source['original'],
            'source_ids': source['source_ids'], 'source_ids_sha256': source['source_ids_sha256'],
            'occurrences': source['occurrences'], 'reviewed_disposition': 'ROOT_INDIVIDUALLY_REVIEWED_HOLD',
            'proof': str((prior_hold_path if row['id'] == old_hold['id'] else new_hold_path).relative_to(ROOT)),
            'author_review': row['review'], 'not_waiting_for_user_approval': True})
    else:
        assert row['status'] in {'PINNED_BODY_NOT_ROOT_ADMISSION', 'MATERIALIZED_BODY_NOT_ROOT_ADMISSION'}
        assert row['body'] and row['clean_text_sha256'] and row['review']
        body_ids.append(row['id'])
assert set(holds) == {r['id'] for r in reviewed_holds}
result = {'status': 'ALL_LITERAL_FIRST_REVIEW_ROWS_RECONCILED_NOT_FINAL_SEMANTIC_OR_CACHE_ADMISSION',
    'unique_source_ids': 1793, 'source_positions': sum(r['occurrences'] for r in sources.values()),
    'saved_body_candidates': len(body_ids), 'body_candidate_positions': sum(sources[i]['occurrences'] for i in body_ids),
    'individually_reviewed_hold_sources': len(reviewed_holds),
    'individually_reviewed_hold_positions': sum(r['occurrences'] for r in reviewed_holds),
    'new_reviewed_hold_sources': 9, 'new_reviewed_hold_positions': sum(r['occurrences'] for r in new_holds.values()),
    'already_officially_reviewed_source_not_counted_as_new': old_hold['id'],
    'unresolved_root_boundary_decisions': 0, 'missing_review_rows': 0, 'binding_errors': 0,
    'holds': reviewed_holds, 'body_records_remain_in_pinned_snapshot_shards': snapshot['shards'],
    'input_pins': {str(p.relative_to(ROOT)): inv.file_sha(p) for p in
        (snapshot_path, manifest_path, new_hold_path, prior_hold_path, contract_path, Path(__file__).resolve())},
    'new_roster_or_cache_adoptions': 0, 'whole_corpus_semantic_completion': False,
    'goal_complete': False, 'training_authorized': False}
out = AUDIT / 'LITERAL_FULL_FIRST_READING_RECONCILIATION_V1.json'
inv.write_json(out, result)
print(json.dumps({k: v for k, v in result.items() if isinstance(v, (int, bool))}))
