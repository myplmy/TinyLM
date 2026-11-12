"""Independent metadata reconstruction and fresh body pins for one selected batch."""
from pathlib import Path
from collections import Counter
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
assert config_path.parent == AUDIT
c = json.loads(config_path.read_bytes())
guard.activate()
store = SelectionStore(AUDIT)
prior = store.read(ROOT/c['prior_selection']['path'], c['prior_selection']['sha256'])
path = AUDIT/('ROOT_AUTHORED_SELECTIONS_V'+str(c['next_selection'])+'.json')
sha = guard.inv.file_sha(path)
current = store.read(path, sha)
assert current['rows'][:len(prior['rows'])] == prior['rows']
readiness_path = ROOT/c['readiness_proof']['path']
assert guard.inv.file_sha(readiness_path) == c['readiness_proof']['sha256']
readiness = json.loads(readiness_path.read_bytes())
by_id = {row['id']:row for row in readiness['checks']}
closure_path = AUDIT/(c['closure_stem']+'.json')
closure = json.loads(closure_path.read_bytes())
assert closure['root_approved'] is True and closure['automatic_guard_waivers'] == 0
assert closure['protected_payload_open_attempts'] == 0
closure_by_id = {row['id']:row for row in closure['checks']}
added = current['rows'][len(prior['rows']):]
assert {row['id'] for row in added} == set(by_id) == set(closure_by_id)
assert len(added) == c['expected_added_unique']
positions = 0
for row in added:
    expected = by_id[row['id']]
    proof = closure_by_id[row['id']]
    choice = row['selected']
    guard.require_payload_context(dict(source_id=row['id'], original=expected['original'], candidate=expected['body']))
    assert row['original_text_sha256'] == expected['original']['sha256']
    assert choice['original'] == expected['original'] and choice['decision'] == expected['decision']
    assert choice['body'] == expected['body']['path']
    assert choice['clean_text_sha256'] == expected['body']['sha256']
    assert guard.inv.file_sha(ROOT/choice['body']) == choice['clean_text_sha256']
    assert choice['review'] == expected['primary_review']
    assert guard.inv.file_sha(ROOT/choice['review']['path']) == choice['review']['sha256']
    assert proof['body'] == expected['body'] and all(proof['guards'].values())
    assert choice['additional_human_full_text_read_claimed'] is False
    assert choice['root_full_text_read_of_every_selected_source_claimed'] is False
    assert choice['approval_mode'] != 'SOURCE_CLASS_RULE_WITH_ALL_ROW_LITERAL_PROOFS'
    positions += proof['occurrences']
assert positions == c['expected_added_positions']
assert current['counts'] == dict(Counter(row['selected']['decision'] for row in current['rows']))
assert current['expected_roster_HOLD_unique'] == prior['expected_roster_HOLD_unique'] - len(added)
assert current['expected_roster_HOLD_positions'] == prior['expected_roster_HOLD_positions'] - positions
assert current['goal_complete'] is False and current['cache_admitted'] is False
guard.assert_no_protected_opens()
result = dict(status='PRIOR_PREFIX_AND_AUTHORED_LITERAL_BATCH_INDEPENDENTLY_VERIFIED',
    prior_unchanged_sources=len(prior['rows']), added_sources=len(added), added_positions=positions,
    selected_sources=len(current['rows']), expected_HOLD_unique=current['expected_roster_HOLD_unique'],
    expected_HOLD_positions=current['expected_roster_HOLD_positions'],
    actual_cache_built=False, payload_copies_written=0, protected_payload_open_attempts=0,
    input_pins={str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in
        [config_path, Path(__file__), readiness_path, closure_path, path, guard.CONTRACT]},
    goal_complete=False, training_authorized=False)
out = AUDIT/('ROOT'+str(c['next_selection'])+'_AUTHORED_LITERAL_SELECTION_INDEPENDENT_VERIFIED_V1.json')
assert not out.exists()
guard.inv.write_json(out, result)
print(json.dumps({k:v for k,v in result.items() if k!='input_pins'}))
