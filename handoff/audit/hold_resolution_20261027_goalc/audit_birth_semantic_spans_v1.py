"""Re-read bound birth bodies; flags never restore or admit text automatically."""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from birth_semantic_span_guard_v1 import lost_stated_quantities,suspicious_birth_field_removal

manifest_path=inv.BASE/'remaining_birth_full_counter_v1/manifest.json'
manifest=inv.cache.read(manifest_path);sources={r['id']:r for r in manifest['rows']}
snapshot_path=inv.BASE/'remaining_birth_full_counter_v1_snapshots/v9/complete.json'
snapshot=inv.cache.read(snapshot_path)
assert snapshot['input_pins'][str(manifest_path.relative_to(ROOT))]==inv.file_sha(manifest_path)
contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
counts=Counter();flagged=[]
for shard in snapshot['shards']:
    assert inv.file_sha(ROOT/shard['path'])==shard['sha256']
    for row in inv.cache.read(ROOT/shard['path']):
        if not row.get('body') or row.get('error'):continue
        source=sources[row['id']]
        assert source['id'] not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes']
        assert inv.file_sha(ROOT/source['original']['path'])==source['original']['sha256']
        assert inv.file_sha(ROOT/row['body'])==row['clean_text_sha256']
        original=(ROOT/source['original']['path']).read_text(encoding='utf-8')
        body=(ROOT/row['body']).read_text(encoding='utf-8')
        flags=lost_stated_quantities(original,body)+suspicious_birth_field_removal(original,body)
        counts['selected_bodies_checked']+=1
        if flags:
            counts['flagged_sources']+=1
            counts.update(f['kind'] for f in flags)
            flagged.append(dict(id=row['id'],role=row['role'],original=source['original'],
                body=dict(path=row['body'],sha256=row['clean_text_sha256']),review=row['review'],
                flags=flags,root_approved=False,cache_admitted=False))
result=dict(status='STATED_QUANTITY_AND_FIELD_ROLE_DIAGNOSTIC_NOT_AUTOMATIC_ADJUDICATION',
    counts=dict(counts),rows=flagged,snapshot=dict(path=str(snapshot_path.relative_to(ROOT)),sha256=inv.file_sha(snapshot_path)),
    producer_sha256=inv.file_sha(Path(__file__)),helper_sha256=inv.file_sha(AUDIT/'birth_semantic_span_guard_v1.py'),
    protected_body_reads=0,goal_complete=False,training_authorized=False,
    limits='Counts include conservative flags. Repeated quantity removal may be intentional deduplication; matching lead/category is not independent fact verification. Each flag needs source context.')
out=AUDIT/'BIRTH_SEMANTIC_SPAN_DIAGNOSTICS_V1.json';payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode('utf-8')
assert len(payload)<20_000_000
with out.open('xb') as stream:stream.write(payload)
print(json.dumps(dict(counts=dict(counts),flagged=[dict(id=r['id'],role=r['role'],kinds=[f['kind'] for f in r['flags']]) for r in flagged],result=str(out.relative_to(ROOT))),ensure_ascii=False))
