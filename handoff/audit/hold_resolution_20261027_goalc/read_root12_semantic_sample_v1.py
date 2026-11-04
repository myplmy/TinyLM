"""Read selected exact source/body pairs after the cumulative metadata gate."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
parser=argparse.ArgumentParser()
parser.add_argument('ids',nargs='+')
parser.add_argument('--identical-source-only',action='store_true')
args=parser.parse_args()
assert 1 <= len(args.ids) <= 4
sha=lambda value:hashlib.sha256(value).hexdigest().upper()
guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
raw=guard_path.read_bytes()
assert sha(raw)=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
guard=json.loads(raw)
summary=json.loads((BASE/'root12_guard_clear_preflight_v1/complete.json').read_bytes())
records=ROOT/summary['records']['path']
raw=records.read_bytes()
assert sha(raw)==summary['records']['sha256']
rows={row['id']:row for row in json.loads(raw)}
for number in args.ids:
    assert number.isdigit()
    key='expanded_train:'+number
    row=rows[key]
    assert key not in guard['restricted_ids']
    assert all(row[label]['sha256'] not in guard['restricted_hashes']
               for label in ('original','candidate','body'))
    print('EXACT_SOURCE_BODY',key,'role',row['role'],'cohort',row['cohort'])
    original_bytes=None
    for label in ('original','body'):
        pin=row[label]
        path=ROOT/pin['path']
        assert path.resolve().is_relative_to(BASE) and not path.is_symlink()
        value=path.read_bytes()
        assert sha(value)==pin['sha256']
        if label=='original': original_bytes=value
        if args.identical_source_only and label=='body':
            assert value==original_bytes,'identity-only mode cannot skip changed text'
            print('BODY_BYTE_IDENTICAL_TO_FULLY_PRINTED_ORIGINAL',key,len(value))
            continue
        text=value.decode('utf-8')
        assert len(text)<=12000,'split an explicit long read rather than truncating'
        print(label.upper(),'BEGIN',len(text),pin['sha256'])
        print(text)
        print(label.upper(),'END_AND_EOF',key)
