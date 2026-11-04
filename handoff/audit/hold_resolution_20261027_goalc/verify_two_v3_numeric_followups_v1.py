"""Verify two exact numeric-context followups; never edit corpus bodies."""
from pathlib import Path
import hashlib
import json
import re

A = Path(__file__).resolve().parent
ROOT = A.parents[2]
B = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
guard_path = A / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
guard_bytes = guard_path.read_bytes()
assert hashlib.sha256(guard_bytes).hexdigest().upper() == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
guard = json.loads(guard_bytes)

def pin(path):
    return dict(path=str(path.relative_to(ROOT)),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper())

def review_rows(path):
    rows = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.match(r'^\|\s*((?:expanded_train|validation):\d+)\s*\|', line)
        if match:
            rows[match[1]] = line
    return rows

specs = [
    ('13111', 'context_latin', 2, 'reviewed_expanded_train_13111_v1.txt',
     'reviewed_expanded_train_13111_flattened_powers_followup_20261104_v1.txt',
     'review_004_v2.md', 'review_004_v4.md',
     '9A43BB5309882F39B6642E01C1F1182AD26C321C989EFA39F1BA36118E7BD3F2'),
    ('149559', 'context_hangul', 9, 'expanded_train_149559_task001_v1.txt',
     'expanded_train_149559_snell_context_followup_20261104_v1.txt',
     'review_001_v2.md', 'review_001_v3.md',
     '495B7115BDE8B05324CD9D34A8B84DC5199598FA042A9710F08307AF05EAD4A9'),
]
records = []
for number, role, page, oldname, newname, oldreview, newreview, oldsha in specs:
    identity = 'expanded_train:' + number
    manifest = json.loads((B / f'remaining_field_title_page_{page:03}_counter_v1/manifest.json').read_text())
    source = next(row for row in manifest['rows'] if row['id'] == identity)
    assert identity not in guard['restricted_ids'] and source['original']['sha256'] not in guard['restricted_hashes']
    folder = B / 'agents' / role / f'remaining_field_title_page_{page:03}_counter_v1'
    oldpath, newpath = folder / oldname, folder / newname
    oldraw, newraw = oldpath.read_bytes(), newpath.read_bytes()
    assert hashlib.sha256(oldraw).hexdigest().upper() == oldsha
    old, new = oldraw.decode('utf-8'), newraw.decode('utf-8')
    if number == '13111':
        edits = [
            (' 예를 들어서 1524라는 숫자는 (1×103) + (5×102) + (2×101) + (4×100)로 표현되며, 이 표기법에서 등급화된 수 10은 100, 101, 102, 103 등의 형태로 찾을 수 있다.', ''),
            ('위에서 든 예인 1524는', '예를 들어 1524는')]
        sidecar = folder / 'hold_13111_flattened_powers_followup_20261104_v1.md'
    else:
        edits = [("오일러 라그랑주 공식은 x<0 또는 x>0인 구간에서 성립하며 굴절률이 상수이므로 경로는 일직선이 된다. x=0에서 f가 연속이어야 하지만 f' 는 불연속일 수도 있다.", '')]
        sidecar = folder / 'hold_149559_snell_context_followup_20261104_v1.md'
    expected = old
    for before, after in edits:
        assert expected.count(before) == 1, (identity, 'edit multiplicity')
        expected = expected.replace(before, after, 1)
    assert expected == new, (identity, 'outside declared edits')
    assert oldraw.endswith(bytes([10])) == newraw.endswith(bytes([10]))
    before, after = review_rows(folder / oldreview), review_rows(folder / newreview)
    assert len(before) == len(after) == 5 and set(before) == set(after)
    assert all(before[key] == after[key] for key in before if key != identity)
    assert newname in after[identity]
    records.append(dict(id=identity, original=source['original'], old_body=pin(oldpath),
                        new_body=pin(newpath), review=pin(folder / newreview), sidecar=pin(sidecar),
                        exact_edits=edits, outside_edits_unchanged=True, UTF8_valid=True,
                        EOF_unchanged=True, other_four_review_rows_unchanged=True,
                        root_authored_training_body=False))
result = dict(status='TWO_V3_NUMERIC_CONTEXT_FOLLOWUPS_EXACTLY_VERIFIED', records=records,
              root_actual_read_results=['304b19', '3d6d99'],
              literal_integer_observation_13111=dict(expression='1*103+5*102+2*101+4*100',
                  value=1*103+5*102+2*101+4*100, named_example=1524, equal=False,
                  lost_exponent_reconstructed=False),
              source_13111_adjacent_separator_removed=True,
              source_149559_adjacent_separator_retained=True, new_root_or_cache_admissions=0,
              whole_document_fact_pass=False, whole_goal_complete=False, training_authorized=False)
target = A / 'ROOT_TWO_V3_NUMERIC_FOLLOWUPS_VERIFIED_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(path=str(target.relative_to(ROOT)),
                     sha256=hashlib.sha256(target.read_bytes()).hexdigest().upper(),
                     records=len(records)), ensure_ascii=False))

