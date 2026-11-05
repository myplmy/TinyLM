"""Compare rule27 candidates against independent, already saved source reviews."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from active_guard_v5_preflight_v1 import activate,checked_contract,assert_no_protected_opens
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v27 as policy

activate();guard=checked_contract();pins={}


def read(path,expected=None):
    raw=path.read_bytes();actual=hashlib.sha256(raw).hexdigest().upper()
    assert expected is None or actual==expected,str(path)
    pins[str(path.relative_to(ROOT))]=actual
    return json.loads(raw)


census=read(AUDIT/'RULE27_DECLARED_NAME_LIST_CENSUS_V1.json')
for name,expected in census['input_pins'].items():assert inv.file_sha(ROOT/name)==expected,name
directory=ROOT/census['metadata_directory']
inv.verify(directory,census['metadata_manifest'])
candidates={row['id']:row for row in inv.cache.rows(directory,census['metadata_manifest'])
            if row['eligible_rule_candidate']}
assert len(candidates)==census['counts']['new_terminal_rule_candidates']==478
stage=read(AUDIT/'HOLD_110173_STAGNATION_DIAGNOSIS_V12.json')
specs=[dict(row) for row in stage['coverage']]
overrides={12:'v12',14:'v7',16:'v2'}
for spec in specs:
    for page,version in overrides.items():
        if spec['cohort']==f'remaining_field_title_page_{page:03d}_counter_v1':spec['version']=version
specs.append(dict(cohort='root12_independent_admission_counter_v1',version='v39'))
reviews=defaultdict(list)
for spec in specs:
    summary=read(inv.BASE/(spec['cohort']+'_snapshots')/spec['version']/'complete.json')
    assert not summary['errors']
    for pin in summary['shards']:
        for row in read(ROOT/pin['path'],pin['sha256']):
            if row['id'] in candidates and row.get('review'):
                reviews[row['id']].append(row)

counts=Counter();rows=[]
for key,items in sorted(reviews.items()):
    candidate=candidates[key]
    original_pin=candidate['original'];assert original_pin['sha256'] not in guard['restricted_hashes']
    original=(ROOT/original_pin['path']).read_bytes()
    assert hashlib.sha256(original).hexdigest().upper()==original_pin['sha256']
    result=policy.propose(dict(id=key,text=original.decode('utf-8'),complete_eos=True,valid_utf8=True))
    body=result.get('candidate',result['text']).encode('utf-8')
    assert result['decision']==candidate['proposed_decision']
    assert hashlib.sha256(body).hexdigest().upper()==candidate['proposed_body_sha256']
    for item in items:
        pin=item['review'];assert inv.file_sha(ROOT/pin['path'])==pin['sha256']
        if item.get('body') and item.get('clean_text_sha256'):
            manual_path=ROOT/item['body'];assert manual_path.resolve().is_relative_to(inv.BASE)
            assert item['clean_text_sha256'] not in guard['restricted_hashes']
            manual=manual_path.read_bytes();assert hashlib.sha256(manual).hexdigest().upper()==item['clean_text_sha256']
            if manual==body:
                outcome='EXACT_BYTES_AGREE_WITH_SAVED_FULL_CONTEXT_REVIEW'
            elif manual.rstrip(b'\r\n')==body.rstrip(b'\r\n'):
                outcome='ONLY_TERMINAL_LINE_ENDINGS_DIFFER_FROM_SAVED_REVIEW'
            else:
                outcome='DIFFERENT_BODY_REQUIRES_ROOT_CONTEXT_REVIEW'
        else:
            outcome='SAVED_NONADMISSION_REQUIRES_ROOT_CONTEXT_REVIEW'
        counts[outcome]+=1
        rows.append(dict(id=key,outcome=outcome,original=original_pin,
            rule_body_sha256=candidate['proposed_body_sha256'],saved_decision=item['decision'],
            saved_body=item.get('body'),saved_body_sha256=item.get('clean_text_sha256'),
            saved_review=pin,read_scope=item.get('read_scope'),rule_approved=False,cache_admitted=False))
assert_no_protected_opens()
pins[str(Path(__file__).relative_to(ROOT))]=inv.file_sha(Path(__file__))
receipt=dict(status='RULE27_VS_INDEPENDENT_SAVED_FULL_CONTEXT_REVIEW_COMPARISON_NOT_ADMISSION',
    eligible_rule_candidates=len(candidates),candidates_with_saved_review=len(reviews),
    candidates_without_saved_review=len(candidates)-len(reviews),comparison_instances=len(rows),
    counts=dict(counts),rows=rows,input_pins=pins,source_original_or_candidate_modified=False,
    regenerated_candidate_payload_stored=False,automatic_root_admissions=0,
    goal_complete=False,training_authorized=False)
inv.write_json(AUDIT/'RULE27_SAVED_CONTEXT_REVIEW_COMPARISON_V1.json',receipt)
print(json.dumps({key:receipt[key] for key in ['status','eligible_rule_candidates','candidates_with_saved_review',
    'candidates_without_saved_review','comparison_instances','counts','automatic_root_admissions']},ensure_ascii=False))
