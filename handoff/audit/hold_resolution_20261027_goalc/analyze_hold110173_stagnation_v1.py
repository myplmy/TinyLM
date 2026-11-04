"""Reconcile fixed cache HOLD positions with newer review-only snapshots."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
VERSIONS = {1:'v20',2:'v16',3:'v14',4:'v14',5:'v12',6:'v15',7:'v15',8:'v13',9:'v7',10:'v1'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


pins = {}


def read(path):
    value = path.read_bytes()
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(value).hexdigest().upper()
    return json.loads(value)


guard_path = AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V2.json'
assert sha(guard_path) == 'E0EF117564ED4632D1A2C63F40AB66EB9620D416AE8BF516FD1AE3204286EF8B'
read(guard_path)
reviewed = {}
coverage = []
cohorts = [('remaining_field_title_page_'+str(page).zfill(3)+'_counter_v1',version)
           for page,version in VERSIONS.items()]
cohorts += [('remaining_literal_full_counter_v1','v21')]
for cohort, version in cohorts:
    snapshot = read(BASE/(cohort+'_snapshots')/version/'complete.json')
    manifest = read(BASE/cohort/'manifest.json')
    sources = {row['id']:row for row in manifest['rows']}
    assert not snapshot['errors'] and snapshot['root_adopted'] == snapshot['cache_admitted'] == 0
    records = []
    for pin in snapshot['shards']:
        path = ROOT/pin['path']
        assert sha(path) == pin['sha256']
        records.extend(read(path))
    saved = [row for row in records if row['status'] != 'NO_SAVED_REVIEW_ROW']
    assert len(saved) == sum(row['saved'] for row in snapshot['coverage'].values())
    for row in saved:
        assert row['id'] not in reviewed
        reviewed[row['id']] = dict(source=sources[row['id']], record=row, cohort=cohort)
    coverage.append(dict(cohort=cohort,version=version,saved=len(saved),
        positions=sum(sources[row['id']]['occurrences'] for row in saved)))
prior = read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json')
prior_ids = {row['id'] for row in prior['rows']}
overlap = set(reviewed)&prior_ids
assert overlap == {'expanded_train:1046282'}
fresh = {key:row for key,row in reviewed.items() if key not in prior_ids}
fresh_positions = sum(row['source']['occurrences'] for row in fresh.values())
cache = read(BASE/'cache_reviewed_partial_v3/built.json')
assert cache['recovery_outcomes']['HOLD'] == cache['counts']['HOLD'] == 110173
assert cache['recovery_outcomes']['documents'] == 460695
baseline = read(AUDIT/'REVIEW_COHORT_DENOMINATOR_CORRECTION_V1.json')
assert baseline['initial_official_unprocessed_unique'] == 70192
assert baseline['initial_prior_reviewed_HOLD_unique'] == 38
assert len(fresh) == 4977 and fresh_positions == 8943
unread_unique = 70192-len(fresh)
unread_positions = 110173-38-fresh_positions
assert unread_unique == 65215 and unread_positions == 101192
assert 38+fresh_positions+unread_positions == 110173
next_paths = [AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json',
              BASE/'roster_reviewed_partial_v4/complete.json',
              BASE/'cache_reviewed_partial_v4/built.json']
next_states = {str(path.relative_to(ROOT)):path.exists() for path in next_paths}
assert not any(next_states.values())
start = read(AUDIT/'CACHE_REVIEWED_PARTIAL_V3_PROCESS_STARTED_V1.json')
exit_receipt = read(AUDIT/'CACHE_REVIEWED_PARTIAL_V3_PROCESS_EXIT_V1.json')
assert exit_receipt['process_exit_code'] == 0
receipt = dict(status='OFFICIAL_CACHE_HOLD_STAGNATION_EXPLAINED_WITH_FRESH_REVIEW_PROGRESS',
    recorded_at=datetime.now(timezone.utc).isoformat(),
    official_cache='cache_reviewed_partial_v3', official_hold_positions=110173,
    reviewed_terminal_hold_positions_already_in_cache=38,
    fresh_first_review_unique=len(fresh),fresh_first_review_positions=fresh_positions,
    still_first_unreviewed_unique=unread_unique,still_first_unreviewed_positions=unread_positions,
    initial_unprocessed_unique=70192,fresh_review_percent_of_initial_unique=100*len(fresh)/70192,
    fresh_review_percent_of_official_HOLD_positions=100*fresh_positions/110173,
    coverage=coverage, prior_reviewed_source_repeated_in_literal=sorted(overlap),
    fresh_bodyless_review_rows=sum(row['record'].get('decision')=='NEEDS_ROOT' for row in fresh.values()),
    newer_selection_roster_cache_existence=next_states,
    latest_cache_actual_build_start_utc=start['utc'],
    latest_cache_actual_build_process_seconds=exit_receipt['seconds'],
    direct_observation='New review records explicitly remain NOT_ROOT_ADMISSION with zero cache admissions; cache3 predates these cohorts. No new ROOT12, roster4 or cache4 exists at this check.',
    cause_analysis=[
        'The majority is still genuinely unread; the new first-review throughput has covered only 7.09 percent of initial unprocessed unique sources.',
        'Root has accumulated review, diagnostics and corrections without completing the next selection, roster and cache integration batch. This workflow scheduling is the direct cause of the unchanged official number.',
        'Long sources and repeated original/candidate/diff reading, followed by sequential root ambiguity decisions and per-body safeguards, increase cost. No causal percentage is established for each factor.',
        'Finished reviews and unresolved numeric/code/order warnings have waited together; unresolved cases must instead stay separate from an independently cleared adoption batch.',
        'Source-restricted metadata-only guards are necessary for new collection and cache consumers; this recent technical gate does not explain the entire earlier delay.'
    ],
    root_ownership='Chief integration and status-reporting delay is root responsibility; first reviews alone must not be presented as adopted cache progress.',
    remedies=['Continue delegated reading while root closes a frozen cleared subset.',
        'Keep unclear or restricted cases individually held without delaying independent cleared cases.',
        'Produce exact ROOT selection and full roster, then a new immutable cache and independent consumer verification.',
        'Report first-review, root-cleared, cache-adopted and reviewed-HOLD counts separately.'],
    cache_build_is_not_forbidden_by_current_user_authorization=True,
    official_hold_count_reduced_in_this_analysis=False,
    new_original_or_candidate_TXT_opens=0,root_adopted=0,cache_admitted=0,
    goal_complete=False,training_authorized=False,input_pins=dict(pins,**{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}))
out = AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V1.json'
with out.open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,ensure_ascii=False,indent=2)
    stream.write(chr(10))
print(json.dumps({key:receipt[key] for key in ('status','fresh_first_review_unique',
    'fresh_first_review_positions','still_first_unreviewed_unique',
    'still_first_unreviewed_positions','official_hold_count_reduced_in_this_analysis')},ensure_ascii=False))
print('RECEIPT',str(out.relative_to(ROOT)),sha(out))
