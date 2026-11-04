"""Read exact current counter pairs; never use an older primary body as a proxy."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
parser = argparse.ArgumentParser()
parser.add_argument('--version', required=True)
parser.add_argument('--snapshot-sha256', required=True)
parser.add_argument('ids', nargs='+')
args = parser.parse_args()
assert re.fullmatch(r'v[1-9][0-9]*', args.version)
assert 1 <= len(args.ids) <= 4 and len(set(args.ids)) == len(args.ids)


def read_pin(path, expected):
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    value = path.read_bytes()
    assert hashlib.sha256(value).hexdigest().upper() == expected
    return value


guard = json.loads(read_pin(
    AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V3.json',
    '7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'))
snapshot_path = BASE / 'root12_independent_admission_counter_v1_snapshots' / args.version / 'complete.json'
snapshot = json.loads(read_pin(snapshot_path, args.snapshot_sha256))
assert not snapshot['errors'] and snapshot['unreviewed_payload_open_attempts'] == 0
rows = []
for pin in snapshot['shards']:
    rows.extend(json.loads(read_pin(ROOT / pin['path'], pin['sha256'])))
by_id = {row['id']: row for row in rows}
assert len(by_id) == len(rows)
for number in args.ids:
    assert number.isdigit()
    key = 'expanded_train:' + number
    assert key not in guard['restricted_ids']
    row = by_id[key]
    assert row.get('body')
    pins = [row['original'], dict(path=row['body'], sha256=row['clean_text_sha256'])]
    assert all(pin['sha256'] not in guard['restricted_hashes'] for pin in pins)
    texts = []
    for pin in pins:
        path = ROOT / pin['path']
        assert path.resolve().is_relative_to(BASE)
        texts.append(read_pin(path, pin['sha256']).decode('utf-8'))
    assert all(len(value) <= 12000 for value in texts), 'explicitly split long reads; never truncate'
    print('CURRENT_COUNTER_PAIR', key, 'SNAPSHOT', args.version, 'REVIEW', row['review']['path'])
    for label, value, pin in zip(('ORIGINAL', 'CURRENT_BODY'), texts, pins):
        print(label, 'BEGIN', len(value), pin['sha256'])
        print(value)
        print(label, 'END_AND_EOF', key)
    print('FULL_DIFF_BEGIN', key)
    print(''.join(difflib.unified_diff(texts[0].splitlines(keepends=True), texts[1].splitlines(keepends=True), fromfile='original', tofile='current_body')), end='')
    print('\nFULL_DIFF_END_AND_EOF', key)
