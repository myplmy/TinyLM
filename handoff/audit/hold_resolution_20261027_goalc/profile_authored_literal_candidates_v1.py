"""Find narrow all-value-preserving primary reviews; do not approve or copy bodies."""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib
import json
import re
import sys
import time

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate,checked_contract,assert_no_protected_opens
from selection_metadata_store_v1 import SelectionStore
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v30 as policy
from verify_rule27_literal_delta_v1 import empty_eof_appendix,literal_stream,evaluate

activate()
guard=checked_contract()
pins={}
started=time.monotonic()


def read(path,expected=None):
    raw=path.read_bytes()
    digest=hashlib.sha256(raw).hexdigest().upper()
    assert expected is None or digest==expected,str(path)
    pins[str(path.relative_to(ROOT))]=digest
    return json.loads(raw)


stage=read(AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V15.json',
           'EF7B424C5B9FBD6231F9C78A958DC18C8DE503F414A3827018D73A879B6CC82E')
opaque=read(AUDIT/'OPAQUE_UNADOPTED_HOLD_ROOT32_ROSTER23_V1.json',
            '87EB0550B9F11BC3EC4E6CBF6B75673A8785633B0522762F7E4277849292EFEF')
selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V35.json'
selection_sha='DF7AA25488D2F8694588E98F866DCA61FDA66A62E8D8BB0395159B0287559BC3'
selection=SelectionStore(AUDIT).read(selection_path,selection_sha)
pins[str(selection_path.relative_to(ROOT))]=selection_sha
prior_hashes={r['original_text_sha256'] for r in selection['rows']}
remaining=set(opaque['hold_hashes'])-prior_hashes
overrides={12:'v16',13:'v11',14:'v12',15:'v7',16:'v5'}
specs=[dict(r) for r in stage['coverage']]
for spec in specs:
    for n,v in overrides.items():
        if spec['cohort']==f'remaining_field_title_page_{n:03d}_counter_v1':
            spec['version']=v
all_reviews=defaultdict(list)
sources={}
blocked_ids=set(guard['restricted_ids'])|set(guard['trusted_metadata'])
blocked_hashes=set(guard['restricted_hashes'])
for spec in specs+[dict(cohort='root12_independent_admission_counter_v1',version='v39')]:
    summary=read(inv.BASE/(spec['cohort']+'_snapshots')/spec['version']/'complete.json')
    assert not summary['errors']
    manifest_path=inv.BASE/spec['cohort']/'manifest.json'
    manifest=read(manifest_path)
    by_id={r['id']:r for r in manifest['rows']}
    if spec['cohort']!='root12_independent_admission_counter_v1':
        sources.update(by_id)
    for shard in summary['shards']:
        for row in read(ROOT/shard['path'],shard['sha256']):
            if row.get('decision')=='NEEDS_ROOT':
                blocked_ids.add(row['id'])
                if row.get('original'):
                    blocked_hashes.add(row['original']['sha256'])
            if row.get('original') and row.get('review'):
                all_reviews[row['original']['sha256']].append(row)

counts,weights=Counter(),Counter()
rows=[]
uncertain=re.compile(r'결손|미완|누락|불명|불완전|판단이 어렵|경계가 불확실|경계가 명확하지|해결되지|깨진')
for digest,items in all_reviews.items():
    if digest not in remaining:
        continue
    primary=[r for r in items if r['cohort']!='root12_independent_admission_counter_v1'
             and r.get('decision') in {'EDIT_TEXT','EDIT_RECIPE','KEEP_SOURCE','ADOPT_CANDIDATE'}
             and r.get('body') and r.get('clean_text_sha256')]
    if not primary:
        counts['no_eligible_primary_body']+=1
        continue
    source=sources[primary[0]['id']]
    if (source['id'] in blocked_ids or digest in blocked_hashes
            or any(source[k]['sha256'] in guard['restricted_hashes'] for k in ['original','candidate'])):
        counts['individual_or_protected_no_payload_read']+=1
        continue
    if not source['complete_eos'] or not source['valid_utf8']:
        counts['incomplete_source_boundary']+=1
        continue
    body_hashes={r.get('clean_text_sha256') for r in items if r.get('body')}
    if len(body_hashes)!=1:
        counts['saved_body_conflict_requires_context']+=1
        continue
    row=primary[0]
    if not re.search(r'EOF|전체|전문|전량|끝|full|FULL|모든',row.get('read_scope','')):
        counts['full_read_claim_not_established']+=1
        continue
    if any(uncertain.search(r.get('reason','')) for r in items):
        counts['source_content_uncertainty_requires_context']+=1
        continue
    original_pin=row['original']
    original_path=(ROOT/original_pin['path']).resolve()
    body_path=(ROOT/row['body']).resolve()
    assert original_path.is_relative_to(inv.BASE) and body_path.is_relative_to(inv.BASE)
    assert not original_path.is_symlink() and not body_path.is_symlink()
    original_raw=original_path.read_bytes()
    body_raw=body_path.read_bytes()
    assert hashlib.sha256(original_raw).hexdigest().upper()==original_pin['sha256']==digest
    assert hashlib.sha256(body_raw).hexdigest().upper()==row['clean_text_sha256']
    assert row['clean_text_sha256'] not in guard['restricted_hashes']
    original,body=original_raw.decode('utf-8'),body_raw.decode('utf-8')
    # Avoid a costly character diff for ordinary partial edits that cannot
    # belong to this strictly lossless class in the first place.
    if literal_stream(empty_eof_appendix(original)[0])!=literal_stream(empty_eof_appendix(body)[0]):
        counts['populated_word_change_requires_context']+=1
        continue
    proof=evaluate(original,body)
    if not proof['eligible_narrow_literal_delta']:
        counts['numeric_code_unicode_style_order_or_memo_requires_context']+=1
        continue
    holes=policy.literal_holes(body)
    if holes:
        counts['remaining_formal_or_structural_holes']+=1
        continue
    for item in items:
        assert inv.file_sha(ROOT/item['review']['path'])==item['review']['sha256']
    counts['eligible_for_ROOT_stratified_context_review']+=1
    weights['eligible_positions']+=source['occurrences']
    rows.append(dict(id=source['id'],original=original_pin,original_text_sha256=digest,
        body=dict(path=row['body'],sha256=row['clean_text_sha256'],bytes=len(body_raw)),
        decision='KEEP' if original_raw==body_raw else 'EDIT',occurrences=source['occurrences'],
        primary_review=row['review'],primary_source_cohort=row['cohort'],
        read_scope=row['read_scope'],reason=row['reason'],all_saved_reviews=[r['review'] for r in items],
        proof=proof,full_source_read_by_primary_author_claimed=True,
        additional_human_full_text_read_claimed=False,root_approved=False,cache_admitted=False))
assert_no_protected_opens()
for path in [Path(__file__),AUDIT/'AUTHORED_LITERAL_BATCH_F3_F4_V1.md',
             AUDIT/'verify_rule27_literal_delta_v1.py',AUDIT/'active_guard_v5_preflight_v1.py',
             ROOT/'scripts/p106b_hold_resolution_policy_v30.py']:
    pins[str(path.relative_to(ROOT))]=inv.file_sha(path)
result=dict(status='EXISTING_AUTHORED_FULL_READ_AND_ALL_LITERAL_PROOFS_CANDIDATES_NOT_ADMISSION',
    rows=rows,counts=dict(counts),weights=dict(weights),coverage=specs,
    input_pins=pins,elapsed_seconds=time.monotonic()-started,corpus_payload_copies_written=0,
    source_original_candidate_or_author_body_modified=False,root_admissions=0,cache_admitted=0,
    goal_complete=False,training_authorized=False)
out=AUDIT/'AUTHORED_LITERAL_PRESERVATION_CANDIDATES_V1.json'
payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode()
assert len(payload)<20_000_000
with out.open('xb') as stream:
    stream.write(payload)
print(json.dumps({k:result[k] for k in ['status','counts','weights','elapsed_seconds','corpus_payload_copies_written']},ensure_ascii=False))
