"""Real frozen metadata boundary checks; no training TXT is created by root."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
HELPER = AUDIT / 'copy_exact_root12_candidate_v1.py'
ast.parse(HELPER.read_text(encoding='utf-8'))
folder = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_controls/root12_independent_admission_counter_v1'
existing = 'expanded_train_915159_root12_working_task182_v3.txt'
assert (folder / existing).is_file()
cases = [
    ('valid_C', 'c', ['182', 'expanded_train:915159', 'expanded_train_915159_root12_working_task182_v987654.txt'], 0),
    ('valid_L', 'l', ['166', 'expanded_train:111357', '111357_counter_working_v987654.txt'], 0),
    ('wrong_role', 'l', ['182', 'expanded_train:915159', '915159_counter_working_v987654.txt'], 2),
    ('wrong_task', 'c', ['181', 'expanded_train:915159', 'expanded_train_915159_root12_working_task181_v987654.txt'], 2),
    ('existing_output', 'c', ['182', 'expanded_train:915159', existing], 2),
    ('path_escape', 'c', ['182', 'expanded_train:915159', '../915159.txt'], 2),
    ('restricted_id', 'c', ['182', 'expanded_train:1250821', 'expanded_train_1250821_root12_working_task182_v987654.txt'], 2),
    ('wrong_basename_id', 'c', ['182', 'expanded_train:915159', 'expanded_train_64616_root12_working_task182_v987654.txt'], 2),
]
results = []
for label, role, args, expected in cases:
    run = subprocess.run(['bash', str(ROOT / f'tmp/hold-{role}-root12-copy-v1'), *args, '--check-only'],
                         capture_output=True, text=True)
    row = dict(case=label, returncode=run.returncode, expected=expected,
               output=run.stdout.strip() or run.stderr.strip(), passed=run.returncode == expected)
    results.append(row)
    if not row['passed']:
        print(json.dumps(row, ensure_ascii=False))
        raise SystemExit('test failed; no PASS receipt written')
assert not (folder / 'expanded_train_915159_root12_working_task182_v987654.txt').exists()
assert not (ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_latin/root12_independent_admission_counter_v1/111357_counter_working_v987654.txt').exists()
pins = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest().upper()
        for path in (HELPER, Path(__file__).resolve(), ROOT / 'tmp/hold-c-root12-copy-v1', ROOT / 'tmp/hold-l-root12-copy-v1')}
receipt = dict(status='METADATA_BOUNDARY_TESTS_PASS_COPY_RUNTIME_NOT_RUN_BY_ROOT', cases=results,
               input_pins=pins, root_txt_creations=0, root_original_or_candidate_payload_opens=0,
               static_ast_utf8='PASS', runtime_copy_not_run_reason='TXT creation belongs to assigned agents; root ran check-only.',
               goal_complete=False, training_authorized=False)
data = (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
assert len(data) < 20_000_000
target = AUDIT / 'EXACT_ROOT12_CANDIDATE_COPY_BOUNDARY_TESTS_V1.json'
with target.open('xb') as output:
    output.write(data)
print(json.dumps(dict(status=receipt['status'], passed=len(results), failed=0,
                      receipt=str(target.relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest().upper(),
                      pins=pins), ensure_ascii=False))
