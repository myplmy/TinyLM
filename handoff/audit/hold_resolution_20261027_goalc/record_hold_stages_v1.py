"""Reconcile immutable review, admission and actually verified cache stages."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
p = argparse.ArgumentParser()
p.add_argument('--config', required=True)
args = p.parse_args()
config_path = (ROOT/args.config).resolve()
assert config_path.is_relative_to(AUDIT) and not config_path.is_symlink()
pins = {}

def read(path, expected=None):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    if expected is not None:
        assert digest == expected, str(path)
    pins[str(path.relative_to(ROOT))] = digest
    return json.loads(raw)

c = read(config_path)
frozen = AUDIT/'analyze_hold110173_stagnation_v1.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'C462277BDC5BF706789BEA0A8D27D15A8FB0A52476C16447B473F3DDC40DD9FB'
source = raw.decode().split('prior = read(')[0]
before = "VERSIONS = {1:'v20',2:'v16',3:'v14',4:'v14',5:'v12',6:'v15',7:'v15',8:'v13',9:'v7',10:'v1'}"
assert source.count(before) == 1
source = source.replace(before, 'VERSIONS = '+repr({int(k):v for k,v in c['field_versions'].items()}))
source = source.replace('GUARDED_SOURCE_METADATA_CONTRACT_V2', 'GUARDED_SOURCE_METADATA_CONTRACT_V3')
source = source.replace('E0EF117564ED4632D1A2C63F40AB66EB9620D416AE8BF516FD1AE3204286EF8B', '7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306')
env = {'__name__':'hold_stages_metadata_only', '__file__':str(Path(__file__))}
exec(compile(source, str(frozen), 'exec'), env)
pins.update(env['pins'])
prior = read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json')
prior_ids = {r['id'] for r in prior['rows']}
reviewed = env['reviewed']
assert set(reviewed)&prior_ids == {'expanded_train:1046282'}
fresh = {k:v for k,v in reviewed.items() if k not in prior_ids}
fresh_positions = sum(v['source']['occurrences'] for v in fresh.values())
unread_unique = 70192-len(fresh)
unread_positions = 110173-38-fresh_positions
cache = read(ROOT/c['cache_delta_proof'], c['cache_delta_proof_sha256'])
assert cache['current_hold_positions'] == c['official_hold_positions']
previous_cache = read(AUDIT/'CACHE4_PROGRESS_DELTA_INDEPENDENT_VERIFIED_V1.json')
assert previous_cache['previous_hold_positions'] == 110173
assert previous_cache['current_hold_positions'] == cache['previous_hold_positions']
assert cache['previous_hold_positions']-cache['current_hold_positions'] == cache['resolved_positions']
cumulative_reduction = previous_cache['resolved_positions']+cache['resolved_positions']
assert cumulative_reduction == 110173-c['official_hold_positions']
selection = read(ROOT/c['selection'], c['selection_sha256'])
roster_proof = read(ROOT/c['roster_proof'], c['roster_proof_sha256'])
assert roster_proof['expected_cache_HOLD_positions'] == selection['expected_roster_HOLD_positions']
new_rows = selection['rows'][len(prior['rows']):]
assert selection['rows'][:len(prior['rows'])] == prior['rows']
assert {r['id'] for r in new_rows} <= set(fresh)
root_positions = sum(fresh[r['id']]['source']['occurrences'] for r in new_rows)
assert 110173-root_positions == selection['expected_roster_HOLD_positions']
counter = read(ROOT/c['counter_snapshot'], c['counter_snapshot_sha256'])
assert not counter['errors']
built = read(ROOT/c['verified_cache_built'])
outcomes = built['recovery_outcomes']
assert outcomes['documents'] == 460695 and outcomes['input_ids'] == 462874291
assert outcomes['HOLD'] == c['official_hold_positions']
cache_parts = dict(first_unreviewed=unread_positions, first_reviewed_cache_pending=fresh_positions-cumulative_reduction, prior_reviewed_HOLD=38)
root_parts = dict(first_unreviewed=unread_positions, first_reviewed_not_ROOT_admitted=fresh_positions-root_positions, prior_reviewed_HOLD=38)
assert sum(cache_parts.values()) == c['official_hold_positions']
assert sum(root_parts.values()) == selection['expected_roster_HOLD_positions']
initial_average = outcomes['input_ids']/outcomes['documents']
remaining_average = outcomes['HOLD_input_ids']/outcomes['HOLD']
receipt = dict(status='FROZEN_REVIEW_ROOT_AND_VERIFIED_CACHE_STAGES_RECONCILED', recorded_at=datetime.now(timezone.utc).isoformat(),
    coverage=env['coverage'], fresh_first_review_unique=len(fresh), fresh_first_review_positions=fresh_positions,
    still_first_unreviewed_unique=unread_unique, still_first_unreviewed_positions=unread_positions,
    official_verified_cache=c['verified_cache'], official_verified_HOLD_positions=c['official_hold_positions'],
    cumulative_reduction_since_110173=cumulative_reduction, official_remaining_HOLD_decomposition=cache_parts,
    cumulative_new_unique_accepted_documents=previous_cache['new_unique_accepted_documents']+cache['new_unique_accepted_documents'],
    cumulative_additional_duplicate_positions_excluded=previous_cache['additional_duplicate_positions_excluded']+cache['additional_duplicate_positions_excluded'],
    ROOT_selection=c['selection'], ROOT_adopted_unique_since_ROOT11=len(new_rows), ROOT_adopted_positions_since_110173=root_positions,
    ROOT_expected_HOLD_positions=selection['expected_roster_HOLD_positions'], ROOT_remaining_decomposition=root_parts,
    ROOT_cache_pending_positions=c['official_hold_positions']-selection['expected_roster_HOLD_positions'],
    counter_saved=counter['records'], counter_errors=0, counter_new_first_review_credit=0,
    raw_input_composition=dict(initial_positions=outcomes['documents'], initial_raw_input_ids=outcomes['input_ids'], remaining_positions=outcomes['HOLD'], remaining_raw_input_ids=outcomes['HOLD_input_ids'], initial_mean_raw_ids_per_position=initial_average, remaining_mean_raw_ids_per_position=remaining_average, remaining_mean_ratio=remaining_average/initial_average, remaining_position_fraction=outcomes['HOLD']/outcomes['documents'], remaining_raw_input_id_fraction=outcomes['HOLD_input_ids']/outcomes['input_ids'], is_timing_causal_evidence=False),
    direct_cause='Root delayed exact selection, full roster and cache integration while completed reviews and individual unresolved cases accumulated.',
    additional_observed_costs=['Repeated source/candidate/diff reading; existing exact-byte Identity V1 can avoid duplicate candidate printing.', 'Missing formula operands, subjects and conditions require narrow context adjudication.', 'Unnecessary simple-format escalations and metadata mistakes caused avoidable coordination and rework.', 'An observed cache5 full CPU build and independent consumer together cost about 48.94 minutes.'],
    causal_percentages='NOT_ESTABLISHED', hardware_slowdown='NOT_ESTABLISHED', continuous_per_document_slowdown='NOT_ESTABLISHED',
    latest_cache_build_seconds=cache['actual_build_seconds'], latest_cache_consumer_seconds=cache['actual_consumer_seconds'],
    raw_original_or_candidate_TXT_opens=0, goal_complete=False, training_authorized=False,
    limits=['Counts are cache occurrences and SHA-linked canonical sources; raw IDs are original input IDs, not cleaned tokens or training exposure.', 'Reviewed rows and ROOT admission are not verified cache adoption.', 'Exact train/val text overlap is zero; global original-article leakage and model quality remain unverified.'], input_pins=pins)
for path in [frozen, Path(__file__)]:
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
out = AUDIT/c['output_basename']
payload = (json.dumps(receipt, ensure_ascii=False, indent=2)+'\n').encode()
assert len(payload)<20_000_000
with out.open('xb') as f:
    f.write(payload)
print(json.dumps({k:receipt[k] for k in ['status','fresh_first_review_unique','fresh_first_review_positions','still_first_unreviewed_positions','official_verified_HOLD_positions','ROOT_expected_HOLD_positions','counter_saved']}, ensure_ascii=False))
