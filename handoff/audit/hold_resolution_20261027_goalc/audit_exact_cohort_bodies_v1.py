"""Read every currently bound body from both immutable cohort snapshots."""
from collections import Counter
from pathlib import Path
import difflib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy

PATTERNS={
 'UNBOUND_CLAIMANT':re.compile(r'(?:^|[|,])[ \t]*(?:가|이)[ \t]+영유권|—[ \t]*이[ \t]+일부[ \t]+영유권',re.M),
 'UNBOUND_OWNER':re.compile(r'(?:^|[|,])[ \t]*의[ \t]+영토인',re.M),
 'UNBOUND_DISPUTE_OR_MANAGEMENT':re.compile(r'(?:^|[|,])[ \t]*(?:과|와)[ \t]+(?:의|이)[ \t]+(?:분쟁|관리)',re.M),
 'MISSING_RANGE_START':re.compile(r'[—–][ \t]*부터(?:부터)?'),
 'MISSING_RANGE_ENDPOINTS':re.compile(r'[(][ \t]*부터[ \t]+까지[ \t]*[)]'),
 'NAMELESS_OPENING':re.compile(r'\A[ \t]*[(][ \t,;:]*[0-9년월일 ~～∼–—?？.-]+[)][은는이가]'),
}

contract_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract=inv.cache.read(contract_path)
blocked_ids=set(contract['restricted_ids'])
blocked_hashes=set(contract['restricted_hashes'])
all_rows=[]
counts=Counter()
cohorts={}
for cohort in ('repeat_named_roles_counter_v2','remaining_birth_full_counter_v1'):
    snapshot_path=inv.BASE/(cohort+'_snapshots')/'v1/complete.json'
    snapshot=inv.cache.read(snapshot_path)
    manifest_path=inv.BASE/cohort/'manifest.json'
    inv.require(snapshot['input_pins'][str(manifest_path.relative_to(ROOT))]==inv.file_sha(manifest_path),
                'diagnostic source assignment changed')
    manifest=inv.cache.read(manifest_path)
    sources={row['id']:row for row in manifest['rows']}
    summary=Counter()
    for shard in snapshot['shards']:
        inv.require(inv.file_sha(ROOT/shard['path'])==shard['sha256'],'snapshot shard changed')
        for row in inv.cache.read(ROOT/shard['path']):
            if not row.get('body') or row.get('error'):continue
            source=sources[row['id']]
            inv.require(source['id'] not in blocked_ids and source['original']['sha256'] not in blocked_hashes,
                        'restricted body must never be read')
            inv.require(inv.file_sha(ROOT/source['original']['path'])==source['original']['sha256'],
                        'original bytes changed')
            inv.require(inv.file_sha(ROOT/row['body'])==row['clean_text_sha256'],'selected bytes changed')
            original=(ROOT/source['original']['path']).read_text(encoding='utf-8')
            body=(ROOT/row['body']).read_text(encoding='utf-8')
            guards=dict(code=policy.code_preserved(original,body),
                unicode=policy.unicode_examples_preserved(original,body),
                style=policy.semantic_style_preserved(original,body),
                ordered=policy.ordered_deletion(original,body),
                no_memo=not bool(inv.corpus.MEMOS.search(body)))
            summary['bodies_fully_read_back_by_cpu']+=1
            for name,passed in guards.items():summary[name+('_pass' if passed else '_review_flag')]+=1
            markers=[]
            coordinate=bool(re.match(r'^(북위|남위|동경|서경)[ ]*[0-9]+도',original))
            for name,pattern in PATTERNS.items():
                if name!='NAMELESS_OPENING' and not coordinate:continue
                for match in pattern.finditer(body):
                    lo=body.rfind(chr(10),0,match.start())+1
                    hi=body.find(chr(10),match.end())
                    hi=len(body) if hi<0 else hi
                    markers.append(dict(kind=name,line=body.count(chr(10),0,match.start())+1,
                        preview=body[lo:hi][:250]))
                    summary['marker_'+name]+=1
            candidate=(ROOT/source['candidate']['path']).read_text(encoding='utf-8')
            changes=[]
            for tag,a,b,c,d in difflib.SequenceMatcher(None,candidate.splitlines(),body.splitlines(),autojunk=False).get_opcodes():
                if tag=='equal':continue
                before=candidate.splitlines()[a:b]
                after=body.splitlines()[c:d]
                changes.append(dict(tag=tag,candidate_lines=[a+1,b],body_lines=[c+1,d],
                    before_preview=chr(10).join(before)[:300],after_preview=chr(10).join(after)[:300]))
            all_rows.append(dict(id=row['id'],role=row['role'],cohort=cohort,original=source['original'],
                body=dict(path=row['body'],sha256=row['clean_text_sha256']),review=row['review'],
                guards=guards,remaining_literal_review_markers=markers,candidate_body_changed_blocks=changes,
                root_approved=False,cache_admitted=False))
    cohorts[cohort]=dict(summary)
    counts.update(summary)
out=AUDIT/'EXACT_COHORT_BODY_DIAGNOSTICS_V1.json'
result=dict(status='ALL_BOUND_COHORT_BODIES_READ_BACK_NOT_MEANING_APPROVAL',counts=dict(counts),
    cohorts=cohorts,rows=all_rows,producer_sha256=inv.file_sha(Path(__file__)),
    root_adopted=0,cache_admitted=0,goal_complete=False,training_authorized=False,
    limits='Literal and deletion flags require source context. No flag is automatically waived or admitted.')
payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode('utf-8')
inv.require(len(payload)<20_000_000,'diagnostic needs another shard')
with out.open('xb') as stream:stream.write(payload)
print(json.dumps(dict(counts=dict(counts),cohorts=cohorts,flagged=[dict(id=r['id'],role=r['role'],cohort=r['cohort'],
    failed=[k for k,v in r['guards'].items() if not v],markers=[m['kind'] for m in r['remaining_literal_review_markers']])
    for r in all_rows if not all(r['guards'].values()) or r['remaining_literal_review_markers']]),ensure_ascii=False))
