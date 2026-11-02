"""Narrow the previous full census using verified native pairs, without admission."""
from collections import Counter
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

helper_path = AUDIT/'typed_nominal_local_alias_v2.py'
spec = importlib.util.spec_from_file_location('nominal_alias_v2',helper_path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
native_path = inv.BASE/'nominal_local_native_proofs_v1/complete.json'
census_path = inv.BASE/'nominal_local_alias_candidates_v1/complete.json'
native,census = map(inv.cache.read,[native_path,census_path])
inv.require(len(native['rows']) == native['counts']['fresh_regeneration_and_proof_match'] == 223,
            'all223 native pairs required')
inv.require(census['counts']['field_sources'] == 19123,'full preceding field census required')
for name,digest in native['input_pins'].items():
    inv.require(inv.file_sha(ROOT/name) == digest,'native proof input changed')
counts,records = Counter(),[]
for row in native['rows']:
    for label in ['original','candidate']:
        inv.require(inv.file_sha(ROOT/row[label]['path']) == row[label]['sha256'],'native pair changed')
    previous = row['proof']
    clean = previous['candidate']
    lo,hi = previous['source_characters']
    baseline = clean[:lo] + previous['original'] + clean[lo:]
    inv.require(hi-lo == len(previous['original']) and inv.sha(baseline) == previous['source_text_sha256'],
                'exact pre-edit candidate reconstruction differs')
    proof = helper.prove(baseline)
    status = 'NARROW_V2_PROOF_CANDIDATE_NOT_ADMISSION' if proof else 'V1_ROLE_INSUFFICIENT_REQUIRES_INDIVIDUAL_SOURCE_REVIEW'
    counts.update({status:1})
    records.append(dict(id=row['id'],original_text_sha256=row['original_text_sha256'],
        original=row['original'],candidate=row['candidate'],status=status,
        proof={key:value for key,value in proof.items() if key!='candidate'} if proof else None,
        prior_v1_role=previous['role'],occurrences=row['occurrences'],
        automatic_admission_allowed=False,root_approved=False))
inv.require(any(row['id']=='expanded_train:1077081' and row['proof'] is None for row in records),
            'actual chemical-role false positive must be rejected')
result = dict(status='FULL19123_CENSUS_NARROWED_OVER_ALL223_NATIVE_MATCHES_NOT_ADMISSION',
    full_field_sources=19123,prior_v1_matches=223,counts=dict(counts),records=records,
    existing_native_source_proofs_reused=True,new_native_decode=False,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [native_path,census_path,helper_path,
        AUDIT/'typed_nominal_local_alias_v1.py',AUDIT/'NOMINAL_LOCAL_ALIAS_COUNTER_FINDINGS_V1.md',Path(__file__)]},
    cache_admitted=0,goal_complete=False,training_authorized=False)
out=AUDIT/'NOMINAL_LOCAL_ALIAS_V2_COUNTER_CENSUS_V1.json'
inv.require(not out.exists(),'new immutable counter census required')
inv.write_json(out,result)
print(json.dumps({key:result[key] for key in ['status','full_field_sources','prior_v1_matches','counts']},ensure_ascii=False))
