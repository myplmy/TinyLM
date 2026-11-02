"""Read back every saved selected body; report diagnostics without admitting it."""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy

BASE=inv.BASE
snapshot_path=AUDIT/'supplemental_candidates_snapshot_v62.json'
receipt_path=AUDIT/'SUPPLEMENTAL_COLLECT62_EXECUTION_V1.json'
manifest_path=BASE/'repeat_named_roles_counter_v2/manifest.json'
contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
OUT=AUDIT/'NAMED_REPEAT_INTERIM_BODY_GUARDS_V1.json'
inv.require(not OUT.exists(),'new immutable body diagnostic required')
snapshot,receipt,manifest,contract=map(inv.cache.read,[snapshot_path,receipt_path,manifest_path,contract_path])
inv.require(receipt['process_exit_code']==0 and
    receipt['snapshot']['sha256']==inv.file_sha(snapshot_path),'actual snapshot completion must match')
inv.require(snapshot['input_pins'][str(manifest_path.relative_to(ROOT))]==inv.file_sha(manifest_path),
            'body snapshot refers to another source assignment')
for name,expected in manifest['source_code_pins'].items():
    inv.require(inv.file_sha(ROOT/name)==expected,'frozen source safety function changed')
blocked_ids=set(contract['restricted_ids'])
blocked_shas=set(contract['restricted_hashes'])
sources={row['id']:row for row in manifest['rows']}
patterns={
 'UNBOUND_CLAIMANT':re.compile(r'(?:^|[|,])[ \t]*(?:가|이)[ \t]+영유권|—[ \t]*이[ \t]+일부[ \t]+영유권',re.M),
 'UNBOUND_DISPUTE_OR_MANAGEMENT':re.compile(r'(?:^|[|,])[ \t]*(?:과|와)[ \t]+(?:의|이)[ \t]+(?:분쟁|관리)',re.M),
 'MISSING_RANGE_START':re.compile(r'[—–][ \t]*부터(?:부터)?'),
 'MISSING_RANGE_ENDPOINTS':re.compile(r'[(][ \t]*부터[ \t]+까지[ \t]*[)]')
}
rows,counts=[],Counter()
for reviewed in snapshot['records']:
    if reviewed['cohort']!='repeat_named_roles_counter_v2':continue
    counts['saved_review_rows']+=1
    if not reviewed.get('body') or reviewed.get('error'):
        counts['unselected_or_mechanically_rejected']+=1
        continue
    source=sources[reviewed['id']]
    inv.require(source['id'] not in blocked_ids and source['original_text_sha256'] not in blocked_shas,
                'restricted original must never enter this body reader')
    original_pin=source['original']
    inv.require(inv.file_sha(ROOT/original_pin['path'])==original_pin['sha256'], 'original input changed')
    inv.require(inv.file_sha(ROOT/reviewed['body'])==reviewed['clean_text_sha256'],'selected body changed')
    original=(ROOT/original_pin['path']).read_text(encoding='utf-8')
    body=(ROOT/reviewed['body']).read_text(encoding='utf-8')
    inv.require(body.strip() and len(body.encode('utf-8'))<20_000_000,'empty or oversized selected body')
    guards=dict(code=policy.code_preserved(original,body),unicode=policy.unicode_examples_preserved(original,body),
        style=policy.semantic_style_preserved(original,body),ordered=policy.ordered_deletion(original,body),
        no_memo=not bool(inv.corpus.MEMOS.search(body)))
    counts['bodies_fully_read_back_by_cpu']+=1
    for name,passed in guards.items():
        counts[name+'_pass' if passed else name+'_review_flag']+=1
    markers=[]
    if re.match(r'^(북위|남위|동경|서경)[ ]*[0-9]+도',original):
        counts['coordinate_bodies']+=1
        for name,pattern in patterns.items():
            for match in pattern.finditer(body):
                lo=body.rfind(chr(10),0,match.start())+1
                hi=body.find(chr(10),match.end())
                hi=len(body) if hi<0 else hi
                markers.append(dict(kind=name,line=body.count(chr(10),0,match.start())+1,
                    preview=body[lo:hi][:240]))
                counts['marker_'+name]+=1
    rows.append(dict(id=reviewed['id'],role=reviewed['role'],source_original_sha256=source['original_text_sha256'],
        body=dict(path=reviewed['body'],sha256=reviewed['clean_text_sha256']),review=reviewed['review'],
        guards=guards,remaining_literal_review_markers=markers,root_approved=False,cache_admitted=False))
result=dict(status='ALL_SAVED_NAMED_REPEAT_BODIES_READ_BACK_DIAGNOSTICS_NOT_MEANING_OR_ADMISSION',
    counts=dict(counts),rows=rows,expected_scope=732,
    pending_review_rows=snapshot['coverage']['repeat_named_roles_counter_v2']['awaiting_review'],
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in
        [snapshot_path,receipt_path,manifest_path,contract_path,Path(__file__)]},
    source_code_pins=manifest['source_code_pins'],
    limits='Flags require source context; clear syntax checks are not independent meaning approval.',
    root_approved=False,cache_admitted=0,goal_complete=False,training_authorized=False)
payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode('utf-8')
inv.require(len(payload)<20_000_000,'body diagnostic must be sharded')
with OUT.open('xb') as stream:
    stream.write(payload)
flagged=[dict(id=row['id'],role=row['role'],failed=[name for name,passed in row['guards'].items() if not passed],
    markers=[m['kind'] for m in row['remaining_literal_review_markers']]) for row in rows
    if not all(row['guards'].values()) or row['remaining_literal_review_markers']]
print(json.dumps(dict(status=result['status'],counts=dict(counts),flagged=flagged),ensure_ascii=False))
