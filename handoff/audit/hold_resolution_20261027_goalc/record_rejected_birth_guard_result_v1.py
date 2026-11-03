"""Check the real negative snapshot and immutable v3 view; never admit rows."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read(path):
    return json.loads(path.read_bytes())


def pin(path):
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))


def records(summary):
    rows = {}
    for entry in summary['shards']:
        data = (ROOT / entry['path']).read_bytes()
        assert sha(data) == entry['sha256']
        for row in json.loads(data):
            assert row['id'] not in rows
            rows[row['id']] = row
    return rows


raw_path = BASE / 'birth_root11_independent_v1_snapshots/v18/complete.json'
view_path = BASE / 'birth_root11_input_delivery_gated_v1/v9/complete.json'
raw, view = read(raw_path), read(view_path)
assert view['raw_snapshot'] == pin(raw_path)
before, after = records(raw), records(view)
assert set(before) == set(after) and len(after) == 2707
rejected = {row['id'] for row in raw['errors']}
assert rejected == {'expanded_train:320336', 'expanded_train:321048'}
for ident, row in after.items():
    if ident in rejected:
        assert row['status'] == 'BLOCKED_BY_RAW_MECHANICAL_REJECTION'
        assert row['input_delivery']['status'] == 'RAW_REVIEW_BINDING_REJECTED_NOT_DELIVERY_APPROVED'
        assert row['root_approved'] is row['cache_admitted'] is False
        assert not ({'body', 'clean_text_sha256', 'author_output', 'body_references'} & set(row))
        assert row['review'] == before[ident]['review']
    else:
        assert row['status'] == before[ident]['status']
        assert row.get('body') == before[ident].get('body')
        assert row.get('clean_text_sha256') == before[ident].get('clean_text_sha256')
assert len(view['failures']) == view['raw_errors'] == 2
assert view['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 358
for event in view['event_shards']:
    assert sha((ROOT / event['path']).read_bytes()) == event['sha256']
tests = AUDIT / 'INPUT_DELIVERY_REJECTED_ROW_CPU_TESTS_20261104_V2.log'
assert 'Ran 28 tests' in tests.read_text() and tests.read_text().rstrip().endswith('OK')
paths = [raw_path, view_path, tests, Path(__file__).resolve(),
         AUDIT / 'quarantine_rejected_birth_row_v1.py',
         AUDIT / 'validate_birth_delivery_snapshot_v3.py',
         AUDIT / 'test_quarantine_rejected_birth_row_v1.py']
result = dict(status='REAL_REJECTED_REVIEW_ROWS_QUARANTINED_WITHOUT_BODY_REFERENCES',
              raw_snapshot=pin(raw_path), view=pin(view_path), verified_rows=2707,
              quarantined_ids=sorted(rejected), original_binding_missing_in_raw=sorted(rejected),
              prospective_delivery_preconditions_satisfied=358,
              rejected_rows_not_counted_as_delivery_approved=True,
              cpu_test_count=28, cpu_test_exit_code=0,
              negative_execution_evidence=[
                  dict(chunk='736b01', command='validator v2, raw v18, output v8',
                       outcome='KeyError original; incomplete v8 directory preserved'),
                  dict(chunk='8e9cc4', command='draft validator v3 --help',
                       outcome='SyntaxError in staged wrapper text before final pin; quote corrected'),
                  dict(chunk='e4ee2c', command='28 CPU tests including actual entry --help', outcome='exit 0'),
                  dict(chunk='22dbce', command='validator v3, raw v18, output v9', outcome='exit 0; two explicit rejections')],
              immutable_event_prefixes_verified=True, protected_body_reads=0,
              root_or_cache_adoptions=0, goal_complete=False, training_authorized=False,
              input_pins={item['path']: item['sha256'] for item in map(pin, paths)})
target = AUDIT / 'BIRTH_REJECTED_ROW_GUARD_RUNTIME_EVIDENCE_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], rows=2707, rejected=2, tests=28,
                     root_or_cache_adoptions=0), ensure_ascii=False))
