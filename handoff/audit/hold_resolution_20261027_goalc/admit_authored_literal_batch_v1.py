"""Append a validated authored batch; preserve prior choices and reuse all bodies."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from selection_metadata_store_v1 import SelectionStore

parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
args = parser.parse_args()
config_path = Path(args.config).resolve()
assert config_path.parent == AUDIT and not config_path.is_symlink()
guard.activate()
config = json.loads(config_path.read_bytes())
store = SelectionStore(AUDIT)
prior_path = ROOT/config['prior_selection']['path']
prior = store.read(prior_path, config['prior_selection']['sha256'])
pins = {}


def read(pin):
    path = ROOT/pin['path']
    assert path.parent == AUDIT and not path.is_symlink()
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == pin['sha256']
    pins[pin['path']] = pin['sha256']
    return json.loads(raw)


proof = read(config['readiness_proof'])
context_path = ROOT/config['context_audit']['path']
assert guard.inv.file_sha(context_path) == config['context_audit']['sha256']
assert proof['root_approved'] is False and proof['cache_admitted'] is False
assert proof['cumulative_guard_sha256'] == guard.EXPECTED
assert proof['protected_payload_open_attempts'] == proof['corpus_payload_copies_written'] == 0
assert proof['verified'] == len(proof['checks']) == config['expected_added_unique']
assert proof['verified_positions'] == config['expected_added_positions']
for name, sha in proof['input_pins'].items():
    assert guard.inv.file_sha(ROOT/name) == sha, name
    pins[name] = sha
prior_ids = {row['id'] for row in prior['rows']}
prior_hashes = {row['original_text_sha256'] for row in prior['rows']}
new_rows, closure_checks = [], []
for row in proof['checks']:
    assert row['id'] not in prior_ids and row['original_text_sha256'] not in prior_hashes
    guard.require_payload_context(dict(source_id=row['id'], original=row['original'], candidate=row['body']))
    assert row['full_source_read_by_primary_author_claimed'] is True
    assert row['additional_human_full_text_read_claimed'] is False
    assert row['decision'] in {'KEEP', 'EDIT'}
    assert all(row['fresh_preservation_proof']['guards'].values())
    assert all(row['additional_readiness_guards'].values())
    assert guard.inv.file_sha(ROOT/row['body']['path']) == row['body']['sha256']
    assert guard.inv.file_sha(ROOT/row['primary_review']['path']) == row['primary_review']['sha256']
    choice = dict(cohort=row['primary_source_cohort'], decision=row['decision'],
        body=row['body']['path'], clean_text_sha256=row['body']['sha256'],
        original=row['original'], review=row['primary_review'], reason=row['reason'],
        author_output=None, compare_source=None, root_approved=True,
        primary_review=row['primary_review'], primary_source_cohort=row['primary_source_cohort'],
        approval_mode='EXISTING_PRIMARY_FULL_READ_ALL_ROW_LITERAL_PROOFS_ROOT_STRATIFIED_CONTEXT',
        individual_human_full_text_read_claimed=True,
        additional_human_full_text_read_claimed=False,
        root_full_text_read_of_every_selected_source_claimed=False,
        saved_review_pins=row['all_saved_reviews'])
    new_rows.append(dict(id=row['id'], original_text_sha256=row['original_text_sha256'],
        selected=choice, original_paths=[row['original']], root_approved=True,
        cache_admitted=False, status='ROOT_APPROVED_EXISTING_AUTHORED_LITERAL_ONLY_RESULT',
        guard_closure_id=config['closure_stem']))
    closure_checks.append(dict(id=row['id'], original=row['original'], body=row['body'],
        occurrences=row['occurrences'], primary_review=row['primary_review'],
        guards=dict(row['fresh_preservation_proof']['guards'], **row['additional_readiness_guards'])))
assert len({row['id'] for row in new_rows}) == len(new_rows)
assert len({row['original_text_sha256'] for row in new_rows}) == len(new_rows)
for path in [config_path, Path(__file__), context_path, guard.CONTRACT,
        AUDIT/'active_guard_v6_preflight_v1.py', AUDIT/'selection_metadata_store_v1.py']:
    pins[str(path.relative_to(ROOT))] = guard.inv.file_sha(path)
pins[config['prior_selection']['path']] = config['prior_selection']['sha256']
closure = dict(status='ROOT_CLOSED_AUTHORED_LITERAL_BATCH_WITH_EXPLICIT_CONTEXT_DEFERRALS',
    checks=closure_checks, sources=len(new_rows), positions=sum(r['occurrences'] for r in closure_checks),
    root_approved=True, automatic_guard_waivers=0, protected_payload_open_attempts=0,
    context_audit=config['context_audit'], input_pins=pins,
    additional_human_full_text_reads_claimed=0, payload_copies_written=0,
    whole_corpus_semantic_completion=False, goal_complete=False, training_authorized=False)
closure_path = AUDIT/(config['closure_stem']+'.json')
assert not closure_path.exists()
guard.inv.write_json(closure_path, closure)
rows = prior['rows'] + new_rows
deferred_ids = [key for key in prior.get('deferred_literal_ids', []) if key not in {r['id'] for r in new_rows}]
document = dict(prior, rows=rows, source_ids=len(rows), selected_sources=len(rows),
    counts=dict(Counter(row['selected']['decision'] for row in rows)),
    selection_scope='PRIOR_VERIFIED_SELECTION_UNCHANGED_PLUS_PINNED_AUTHORED_LITERAL_BATCH',
    prior_selection=config['prior_selection'], prior_selected_rows_preserved_exactly=len(prior['rows']),
    new_approved_sources=len(new_rows), new_approved_positions=closure['positions'],
    deferred_literal_ids=deferred_ids, deferred_literal_sources=len(deferred_ids),
    closure=dict(path=str(closure_path.relative_to(ROOT)), sha256=guard.inv.file_sha(closure_path)),
    expected_roster_HOLD_unique=prior['expected_roster_HOLD_unique']-len(new_rows),
    expected_roster_HOLD_positions=prior['expected_roster_HOLD_positions']-closure['positions'],
    adopted_existing_authored_sources=len(new_rows), new_human_first_read_credit=0,
    restricted_parent_full_bodies_opened=0, whole_corpus_semantic_completion=False,
    cache_admitted=False, goal_complete=False, training_authorized=False)
document['input_pins'] = dict(prior['input_pins'], **pins,
    **{str(closure_path.relative_to(ROOT)):guard.inv.file_sha(closure_path)})
out = AUDIT/('ROOT_AUTHORED_SELECTIONS_V'+str(config['next_selection'])+'.json')
assert not out.exists()
receipt = store.write(out, document, force_sharded=True)
storage_path = AUDIT/('ROOT'+str(config['next_selection'])+'_SELECTION_STORAGE_V1.json')
assert not storage_path.exists()
guard.inv.write_json(storage_path, receipt)
guard.assert_no_protected_opens()
print(json.dumps(dict(status='AUTHORED_BATCH_SELECTED_NOT_CACHE_ADMITTED',
    selected_sources=len(rows), added_unique=len(new_rows), added_positions=closure['positions'],
    selection_sha256=guard.inv.file_sha(out), expected_HOLD_unique=document['expected_roster_HOLD_unique'],
    expected_HOLD_positions=document['expected_roster_HOLD_positions'], payload_copies=0)))
