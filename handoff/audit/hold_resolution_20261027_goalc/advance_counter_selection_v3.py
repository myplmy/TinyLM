"""Accept one pinned exclusion history without relaxing any content guard."""
from pathlib import Path
import hashlib
import json

AUDIT = Path(__file__).resolve().parent
adapter = AUDIT / 'advance_counter_selection_v2.py'
raw = adapter.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'E7E36447766CB91028F6B6C253783B9BEC1EB08244BA264DF938F358864A3713'
last = "exec(compile(code,str(adapter),'exec'),environment)"
source = raw.decode('utf-8')
assert source.count(last) == 1
scope = dict(__name__='counter_v3_source_transform', __file__=str(Path(__file__)))
exec(compile(source.split(last)[0], str(adapter), 'exec'), scope)
ROOT = scope['ROOT']
config = scope['config']
environment = scope['environment']
code = scope['code']
history_path = (ROOT / config['strict_task_history_proof']).resolve()
assert history_path.is_relative_to(AUDIT) and not history_path.is_symlink()
history_raw = history_path.read_bytes()
assert hashlib.sha256(history_raw).hexdigest().upper() == config['strict_task_history_proof_sha256']
history = json.loads(history_raw)
assert history['status'] == 'STRICT_TASK143_HISTORY_EXCLUSION_AND_CANONICAL_PRECEDENCE_VERIFIED'
assert history['source_body_opens'] == history['historical_bad_rows_selected'] == 0
assert history['corrected_TASK143_rows_selected'] == 5
assert history['correct_TASK142_rows_preserved'] == 4
assert history['historical_bad_review_previously_admitted_by_ROOT19'] is False
for name, expected in history['input_pins'].items():
    path = ROOT / name
    assert not path.is_symlink()
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == expected, name
snapshot_path = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc/root12_independent_admission_counter_v1_snapshots' / config['snapshot_version'] / 'complete.json'
assert history['input_pins'][str(snapshot_path.relative_to(ROOT))] == config['snapshot_sha256']
snapshot_raw = snapshot_path.read_bytes()
assert hashlib.sha256(snapshot_raw).hexdigest().upper() == config['snapshot_sha256']
snapshot = json.loads(snapshot_raw)
approved_invalid = snapshot['invalid_task_rows']
assert len(approved_invalid) == 4
assert {row['id'] for row in approved_invalid} == set(history['rejected_historical_ids'])
for row in approved_invalid:
    assert row['invalid_as_review_evidence'] is True
    assert row['error'] == 'REVIEW_ROW_IS_NOT_IN_THIS_TASK_SOURCE_LIST'
    assert row['review']['sha256'] == '6D26C4705AA6FB723D4B6501B24D213376A65E882338C4273F2BFD3F5F73B576'
    assert row['review']['path'].endswith('/context_latin/root12_independent_admission_counter_v1/review_143.md')
before = "assert not snapshot['errors'] and not snapshot['invalid_task_rows'] and not snapshot['unparsed_review_history']"
after = "assert not snapshot['errors'] and snapshot['invalid_task_rows']==APPROVED_EXACT_INVALID_HISTORY and not snapshot['unparsed_review_history']"
assert code.count(before) == 1
code = code.replace(before, after, 1)
before = 'input_paths=[EXACT_ORDER_PATH,ADAPTER_V1_PATH,CONFIG_PATH,TEMPLATE_PATH]'
assert code.count(before) == 1
code = code.replace(before, 'input_paths=[HISTORY_PROOF_PATH,ADAPTER_V2_PATH,EXACT_ORDER_PATH,ADAPTER_V1_PATH,CONFIG_PATH,TEMPLATE_PATH]', 1)
before = 'inv.write_json(closure_path,closure)'
assert code.count(before) == 1
code = code.replace(before, "closure.update(explicit_historical_task_rows_excluded=4,historical_task_exclusion_proof=dict(path=str(HISTORY_PROOF_PATH.relative_to(ROOT)),sha256=HISTORY_PROOF_SHA),content_guard_waivers=0)\n" + before, 1)
environment.update(APPROVED_EXACT_INVALID_HISTORY=approved_invalid,
    HISTORY_PROOF_PATH=history_path, HISTORY_PROOF_SHA=config['strict_task_history_proof_sha256'],
    ADAPTER_V2_PATH=adapter)
exec(compile(code, str(adapter), 'exec'), environment)
