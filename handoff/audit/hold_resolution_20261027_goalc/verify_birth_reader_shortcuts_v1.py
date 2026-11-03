"""Verify actual shortcuts with root-only probes and exact metadata denials."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from snapshot_birth_delivery_events_v1 import archive_event_prefixes

module = AUDIT / 'birth_input_delivery_guard_v1.py'
spec = importlib.util.spec_from_file_location('unchanged_delivery_guard', module)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
prepared_path = AUDIT / 'BIRTH_READER_SHORTCUTS_PREPARED_V1.json'
prepared = json.loads(prepared_path.read_bytes())
activation_path = AUDIT / 'BIRTH_INPUT_DELIVERY_ACTIVATION_V1.json'
activation = json.loads(activation_path.read_bytes())
config, contract, sources = guard.load_config(ROOT, activation['config'], activation['module']['sha256'])


def pin(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=guard.sha(data), bytes=len(data))


def probes(role):
    directory = ROOT / config['roles'][role]['event_directory'] / 'root_probes'
    rows, pins = [], []
    for path in sorted(directory.glob('events_*.jsonl')):
        pins.append(pin(path))
        for line in path.read_bytes().splitlines():
            row = json.loads(line)
            claimed = row.pop('event_sha256')
            assert guard.event_hash(row) == claimed
            assert row['purpose'] == 'ROOT_VERIFICATION_PROBE' and row['role'] == role
            rows.append(dict(row, event_sha256=claimed))
    return rows, pins


cases = {'context_controls': 'expanded_train:625422', 'context_latin': 'expanded_train:292732'}
positive, negative, event_pins = [], [], []
for row in prepared['rows']:
    role, ident = row['role'], cases[row['role']]
    guard.read_pin(ROOT, row['reader'])
    guard.read_pin(ROOT, row['shortcut'])
    before, _ = probes(role)
    result = subprocess.run(['bash', str(ROOT / row['shortcut']['path']), ident, '1', '--probe'],
                            cwd=ROOT, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode('utf-8')
    expected = guard.expected_event(config, contract, sources, role, ident, 1,
                                   activation['config']['sha256'], activation['module']['sha256'])
    guard.checked_packet_output(result.stdout, expected, sources[ident]['reading_parts'][0])
    after, pins = probes(role)
    new = [event for event in after if event['event_sha256'] not in {event['event_sha256'] for event in before}]
    assert len(new) == 1 and new[0]['source_id'] == ident and new[0]['packet'] == 1
    event_pins += pins
    positive.append(dict(role=role, source_id=ident, packet=1, exit_code=0,
                         stdout_sha256=guard.sha(result.stdout), complete_envelope_verified=True,
                         event=new[0], official_review_input_emission=False))
control = next(row for row in prepared['rows'] if row['role'] == 'context_controls')
before, _ = probes('context_controls')
for ident, reason in [('expanded_train:292732', 'other assigned role'),
                      ('expanded_train:756966', 'restricted ID')]:
    result = subprocess.run(['bash', str(ROOT / control['shortcut']['path']), ident, '1', '--probe'],
                            cwd=ROOT, capture_output=True, timeout=30)
    assert result.returncode != 0 and result.stdout == b''
    negative.append(dict(source_id=ident, reason=reason, exit_code=result.returncode,
                         stdout_bytes=0, stderr_last_line=result.stderr.decode('utf-8').splitlines()[-1]))
after, _ = probes('context_controls')
assert {event['event_sha256'] for event in before} == {event['event_sha256'] for event in after}
target = AUDIT / 'birth_reader_shortcuts_probe_evidence_v1'
target.mkdir(exist_ok=False)
archived = archive_event_prefixes(ROOT, target, event_pins, guard)
for item in archived:
    guard.read_pin(ROOT, item)
paths = [prepared_path, activation_path, module, Path(__file__).resolve(),
         AUDIT / 'prepare_birth_reader_shortcuts_v1.py', AUDIT / 'test_birth_reader_shortcuts_v1.py']
result = dict(status='EXISTING_V2_SHORTCUTS_ACTUAL_ROOT_PROBES_AND_DENIALS_VERIFIED',
              positive=positive, negative=negative, immutable_probe_event_prefixes=archived,
              regression_tests=dict(tool_chunk='c26725', count=35, failures=0, exit_code=0),
              input_pins=[pin(path) for path in paths], unchanged_existing_readers=prepared['rows'],
              protected_body_reads=0, corpus_or_review_writes=0,
              semantic_review_inferred_from_probe=False, historical_review_emissions_created=False,
              root_or_cache_adoptions=0, goal_complete=False, training_authorized=False)
output = AUDIT / 'BIRTH_READER_SHORTCUTS_RUNTIME_VERIFIED_V1.json'
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], root_probes=len(positive), denials=len(negative),
                     official_review_input_emissions=0, tests=35), ensure_ascii=False))
