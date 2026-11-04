"""Read one exact field source only after cumulative ID/SHA metadata gates."""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
parser=argparse.ArgumentParser();parser.add_argument('--page',type=int,required=True)
parser.add_argument('--part',type=int);parser.add_argument('id');args=parser.parse_args()
assert 1<=args.page<=36 and re.fullmatch(r'expanded_train:[0-9]+',args.id)
raw=(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json').read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
guard=json.loads(raw);assert args.id not in guard['restricted_ids']
index=json.loads((BASE/'remaining_field_title_readers_v1/complete.json').read_bytes())
page=next(row for row in index['pages'] if row['page']==args.page)
raw=(ROOT/page['path']).read_bytes();assert hashlib.sha256(raw).hexdigest().upper()==page['sha256']
source=next(row for row in json.loads(raw)['rows'] if row['id']==args.id)
pin=source['original'];assert pin['sha256'] not in guard['restricted_hashes']
path=ROOT/pin['path'];assert path.resolve().is_relative_to(BASE) and not path.is_symlink()
raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest().upper()==pin['sha256']
text=raw.decode('utf-8');limit=6000;parts=max(1,(len(text)+limit-1)//limit)
assert args.part is not None or parts==1,'long source requires explicit part numbers'
part=args.part or 1;assert 1<=part<=parts
lo=(part-1)*limit;hi=min(len(text),part*limit)
print(json.dumps(dict(id=args.id,original=pin,part=part,parts=parts,range=[lo,hi],original_chars=len(text))))
print('ORIGINAL_CONTEXT_BEGIN');print(text[lo:hi]);print('ORIGINAL_CONTEXT_PART_END')
if part==parts:print('ORIGINAL_SOURCE_EOF',args.id)
