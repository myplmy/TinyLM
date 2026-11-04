"""Bind the next bounded repairs to frozen review rows; record no cache admission."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}
reused = AUDIT / 'record_resume_progress_v8.py'
nodes = [node for node in ast.parse(reused.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name == 'read']
assert len(nodes) == 1
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(reused), 'exec'), globals())
prior = read(AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V13.json')
assert prior['field_saved'] == 2332
versions = {1: 'v19', 2: 'v10', 3: 'v6', 4: 'v13', 5: 'v10', 6: 'v14', 7: 'v9', 8: 'v7'}
pages = {page: read(BASE / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
         for page, version in versions.items()}
assert all(not page['errors'] for page in pages.values())
counts = {page: sum(row['saved'] for row in value['coverage'].values()) for page, value in pages.items()}
assert counts == {1: 504, 2: 357, 3: 309, 4: 310, 5: 307, 6: 308, 7: 172, 8: 100}
saved = sum(counts.values())
assert saved == 2367
repair = read(AUDIT / 'ROOT_FIELD_CONDITIONS_AND_SLOTS_VERIFIED_V1.json')
requested = {row['id']: row for row in repair['records']}
assert len(requested) == 5
bound = {}
for page in (1, 2, 5):
    for shard in pages[page]['shards']:
        value = read(ROOT / shard['path'])
        rows = value if isinstance(value, list) else value.get('records', value.get('rows'))
        for row in rows:
            if row['id'] in requested:
                expected = requested[row['id']]
                assert row['original'] == expected['original'] and row['author_output'] == expected['body']
                assert row['review']['path'] == expected['review']['path']
                assert row['review']['sha256'] == expected['review']['sha256']
                assert not row['root_approved'] and not row['cache_admitted']
                bound[row['id']] = dict(body=row['author_output'], review=row['review'])
assert set(bound) == set(requested)
commit = read(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LOCAL_COMMIT_V16_INDEPENDENT_VERIFIED.json')
assert commit['commit'] == 'b9259eaba7de799086bec65df12302e5e133deb3'
assert commit['verified_paths'] == 322 and commit['shared_index_count'] == 0
data = dict(status='POST_V13_FIVE_CONDITION_SLOT_SCOPES_BOUND_TO_NEW_SNAPSHOTS',
            field_versions=versions, field_saved_by_page=counts, field_saved_frozen=saved,
            delta_from_v13=saved-prior['field_saved'], field_review_binding_errors=0,
            field_missing=18237-saved, combined_first_review_missing=18237-saved+50162,
            official_HOLD_positions_unchanged=110173, independent_birth_unique_not_added=2707,
            verified_specific_scopes_bound=bound,
            latest_verified_local_commit=commit['commit'], own_git_window='CLOSED',
            later_changes_uncommitted=True, all_five_roles_and_root='RUN',
            current_scopes_not_whole_document_semantic_pass=True,
            new_root_or_cache_admissions=0, input_pins=pins,
            whole_goal_complete=False, training_authorized=False)
for path in (reused, Path(__file__).resolve()):
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
with (AUDIT / 'POST_V13_SCOPE_DELTA_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=data['status'], field_saved=saved,
                     first_review_missing=data['combined_first_review_missing'],
                     newly_bound_scopes=5, official_HOLD_positions=110173)))
