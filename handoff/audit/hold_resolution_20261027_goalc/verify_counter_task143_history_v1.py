"""Verify that strict TASK membership rejects four historical cross-task rows."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}


def read(path, expected=None):
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    if expected is not None:
        assert digest == expected
    pins[str(path.relative_to(ROOT))] = digest
    return raw


snapshot_path = BASE / 'root12_independent_admission_counter_v1_snapshots/v13/complete.json'
snapshot = json.loads(read(snapshot_path, '64501B995AFFF82B68770DB0F1EFEFE3AA09E1A18DF72DBC0A02E1EA5A15CEF5'))
assert not snapshot['errors'] and not snapshot['unparsed_review_history']
assert snapshot['unreviewed_payload_open_attempts'] == 0
rows = []
for pin in snapshot['shards']:
    rows.extend(json.loads(read(ROOT / pin['path'], pin['sha256'])))
by_id = {row['id']: row for row in rows}
assert len(by_id) == len(rows)
directory = BASE / 'agents/context_latin/root12_independent_admission_counter_v1'
task = directory / 'TASK_143.md'
expected = set(re.findall(r'^## (expanded_train:[0-9]+|validation:[0-9]+)$', read(task).decode(), re.M))
assert expected == {'expanded_train:29006', 'expanded_train:82744', 'expanded_train:285311', 'expanded_train:1341473', 'expanded_train:175957'}
bad = directory / 'review_143.md'
good = directory / 'review_143_v2.md'
previous = directory / 'review_142_v2.md'
read(bad, '6D26C4705AA6FB723D4B6501B24D213376A65E882338C4273F2BFD3F5F73B576')
read(good, '4839845DEDCEC8363B7C0C2170560E275EB1B878E23C978AFAED994BD8A232D8')
read(previous, 'F80CDDF3B763F9F8EC26681B79D63D36370F6EA975A3F4733FC65920DF7C0161')
rejected = [row for row in snapshot['invalid_task_rows'] if row['review']['path'] == str(bad.relative_to(ROOT))]
off_task = {'validation:1730', 'expanded_train:68318', 'expanded_train:52160', 'expanded_train:89121'}
assert len(rejected) == 4 and {row['id'] for row in rejected} == off_task
assert all(row['invalid_as_review_evidence'] is True for row in rejected)
for key in expected:
    assert by_id[key]['review']['path'] == str(good.relative_to(ROOT))
for key in off_task:
    assert by_id[key]['review']['path'] == str(previous.relative_to(ROOT))
prior = read(AUDIT / 'ROOT_AUTHORED_SELECTIONS_V19.json', '0F8DD18A28B5FCF751B80402D1991E1B999A192FD7B0C55260745B1928B313D4')
assert str(bad.relative_to(ROOT)) not in prior.decode('utf-8')
for name in ('collect_root12_counter_v2.py', 'collect_supplemental_candidates_v63.py'):
    read(AUDIT / name)
read(Path(__file__))
result = dict(status='STRICT_TASK143_HISTORY_EXCLUSION_AND_CANONICAL_PRECEDENCE_VERIFIED',
    exact_snapshot='v13', assigned_ids=sorted(expected), rejected_historical_ids=sorted(off_task),
    old_bad_review_preserved=True, corrected_TASK143_rows_selected=5,
    correct_TASK142_rows_preserved=4, historical_bad_rows_selected=0,
    historical_bad_review_previously_admitted_by_ROOT19=False,
    incident_v1_correction='390031 was not assigned to TASK143; no assigned TASK143 row was missing, four TASK142 rows were added.',
    collector_code_changes=0, source_body_opens=0, root_or_cache_new_admissions=0,
    input_pins=pins, goal_complete=False, training_authorized=False)
raw=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
assert len(raw)<20_000_000
out=AUDIT/'ROOT12_COUNTER_REVIEW143_HISTORY_INDEPENDENT_VERIFIED_V1.json'
with out.open('xb') as handle:
    handle.write(raw)
print(json.dumps({'status':result['status'],'sha256':hashlib.sha256(raw).hexdigest().upper()}))
