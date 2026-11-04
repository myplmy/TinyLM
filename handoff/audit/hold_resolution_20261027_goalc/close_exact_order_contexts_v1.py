"""Verify only source/body pairs and exact grammatical closures approved by root."""
from pathlib import Path
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_policy_v26 as policy
from scripts import p106b_hold_resolution_inventory as inv
from numeric_atom_integrity_v1 import numeric_atom_changes
p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args()
pins={}
def read(path,expected=None):
    assert not path.is_symlink()
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest().upper()
    if expected is not None:assert digest==expected,str(path)
    pins[str(path.relative_to(ROOT))]=digest
    return raw
config_path=(ROOT/args.config).resolve();assert config_path.is_relative_to(AUDIT)
c=json.loads(read(config_path))
guard=json.loads(read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json','7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'))
snapshot=json.loads(read(ROOT/c['snapshot'],c['snapshot_sha256']));assert not snapshot['errors']
records=[]
for pin in snapshot['shards']:records+=json.loads(read(ROOT/pin['path'],pin['sha256']))
by_id={r['id']:r for r in records};assert len(by_id)==len(records)
closed=[]
for item in c['records']:
    key=item['id'];row=by_id[key]
    assert key not in guard['restricted_ids']
    source=row['original'];body=dict(path=row['body'],sha256=row['clean_text_sha256'])
    assert source['sha256']==item['original_sha256'] and body['sha256']==item['body_sha256']
    assert all(pin['sha256'] not in guard['restricted_hashes'] for pin in [source,body])
    texts=[]
    for pin in [source,body]:
        path=ROOT/pin['path'];assert path.resolve().is_relative_to(BASE)
        texts.append(read(path,pin['sha256']).decode('utf-8'))
    original,after=texts;assert after.strip()
    numeric=numeric_atom_changes(original,after)
    guards=dict(numeric_atoms=not numeric,code=policy.code_preserved(original,after),unicode=policy.unicode_examples_preserved(original,after),style=policy.semantic_style_preserved(original,after),ordered=policy.ordered_deletion(original,after),no_memo=not bool(inv.corpus.MEMOS.search(after)))
    assert [k for k,v in guards.items() if not v]==['ordered'],(key,guards)
    normalized=original
    for old,new in item['exact_substitutions']:
        assert old!=new and normalized.count(old)==1,(key,old)
        normalized=normalized.replace(old,new,1)
    assert policy.ordered_deletion(normalized,after),key
    raw_guards=dict(guards);guards['ordered']=True
    read(ROOT/row['review']['path'],row['review']['sha256'])
    closed.append(dict(id=key,original=source,body=body,review=row['review'],raw_guards=raw_guards,guards=guards,exact_substitutions=item['exact_substitutions'],semantic_reason=item['semantic_reason'],root_source_and_new_body_and_full_diff_read=True,root_approved=True,guard_waiver=False,cache_admitted=False))
receipt=dict(status='EXACT_SOURCE_BODY_GRAMMAR_CONTEXT_ORDER_CLOSURES',records=closed,input_pins=pins,training_TXT_authored_by_root=0,guard_waivers=0,goal_complete=False,training_authorized=False)
pins[str(Path(__file__).relative_to(ROOT))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
out=AUDIT/c['output_basename'];raw=(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode();assert len(raw)<20_000_000
with out.open('xb') as f:f.write(raw)
print(json.dumps(dict(verified=len(closed),sha256=hashlib.sha256(raw).hexdigest().upper())))
