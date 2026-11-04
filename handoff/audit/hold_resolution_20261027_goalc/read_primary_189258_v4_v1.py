"""Bounded exact reads of the repaired paper and complete character changes."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
p = argparse.ArgumentParser()
g = p.add_mutually_exclusive_group(required=True)
g.add_argument('--part', type=int)
g.add_argument('--diff', action='store_true')
args = p.parse_args()


def read(path, expected):
    assert not path.is_symlink() and path.resolve().is_relative_to(ROOT)
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == expected
    return raw


guard = json.loads(read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V3.json', '7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'))
assert 'expanded_train:189258' not in guard['restricted_ids']
snap = json.loads(read(BASE / 'remaining_field_title_page_010_counter_v1_snapshots/v11/complete.json', 'D0DC8ED566680E7997588D8D5A761367E9375582506123ABF8D650D8907968F2'))
assert not snap['errors']
rows = []
for pin in snap['shards']:
    rows.extend(json.loads(read(ROOT / pin['path'], pin['sha256'])))
row = next(row for row in rows if row['id'] == 'expanded_train:189258')
assert row['clean_text_sha256'] == 'F5AEBCD220AAB5F530337846439EB03992AC7EFA3A4344E9CD3CE14FBAABB50E'
pins = [dict(path=row['body'],sha256=row['clean_text_sha256']), dict(path=str((BASE / 'exact_cohort_rendered_v1/BB/BB87351E3DF882E9089EADF383FFB335FD8F97ECA652692AD27D97B96A35223E.txt').relative_to(ROOT)),sha256='BB87351E3DF882E9089EADF383FFB335FD8F97ECA652692AD27D97B96A35223E')]
assert all(pin['sha256'] not in guard['restricted_hashes'] for pin in pins)
texts = []
for pin in pins:
    path = ROOT / pin['path']
    assert path.resolve().is_relative_to(BASE)
    texts.append(read(path, pin['sha256']).decode('utf-8'))
after, before = texts
if args.diff:
    print('COMPLETE_CHARACTER_DIFF_BEGIN', 'expanded_train:189258', 'v3_to_v4')
    changes = 0
    for tag, a, b, c, d in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        if tag != 'equal':
            print(json.dumps(dict(tag=tag,v3=[a,b],v4=[c,d],removed=before[a:b],added=after[c:d]),ensure_ascii=False))
            changes += 1
    print('COMPLETE_CHARACTER_DIFF_END_AND_EOF', changes)
else:
    parts = math.ceil(len(after)/12000)
    assert 1 <= args.part <= parts
    lo = (args.part-1)*12000
    hi = min(lo+12000,len(after))
    print(json.dumps(dict(id=row['id'],part=args.part,parts=parts,range=[lo,hi],characters=len(after),sha256=row['clean_text_sha256'])))
    print('CURRENT_V4_BODY_PART_BEGIN')
    print(after[lo:hi])
    print('CURRENT_V4_BODY_END_AND_EOF' if hi == len(after) else 'CURRENT_V4_BODY_PART_END')
