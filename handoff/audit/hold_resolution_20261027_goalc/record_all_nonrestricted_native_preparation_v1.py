"""Reconcile prepared metadata sets without conflating them with content review."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
blocked_ids=set(contract['restricted_ids']);blocked_sha=set(contract['restricted_hashes'])
seen_ids=set();seen_sha=set();groups=[];pins={}
for name,expected in [('remaining_literal_native_proofs_v1',1793),
                      ('remaining_field_title_native_proofs_v1',18237),
                      ('remaining_other_types_native_proofs_v1',50162)]:
    path=inv.BASE/name/'complete.json'
    proof=inv.cache.read(path)
    pins[str(path.relative_to(ROOT))]=inv.file_sha(path)
    if 'rows' in proof:
        rows=proof['rows']
    else:
        rows=[]
        for page in proof['pages']:
            current=ROOT/page['path']
            assert inv.file_sha(current)==page['sha256']
            rows.extend(inv.cache.read(current)['rows'])
    ids={row['id'] for row in rows};hashes={row['original_text_sha256'] for row in rows}
    assert len(rows)==len(ids)==len(hashes)==expected
    assert not (ids&seen_ids) and not (hashes&seen_sha)
    assert not (ids&blocked_ids) and not (hashes&blocked_sha)
    assert all(row['native_proof_agrees'] for row in rows)
    assert all(row['complete_eos'] and row['valid_utf8'] for row in rows)
    seen_ids.update(ids);seen_sha.update(hashes)
    groups.append(dict(group=name,unique_sources=expected,positions=sum(row['occurrences'] for row in rows)))
assert len(seen_ids)==len(seen_sha)==70192
assert 'expanded_train:1046282' in seen_ids
for name in ['REMAINING_OTHER_TYPES_NATIVE_PROCESS_EXIT_V1.json','OTHER_TYPE_READING_PREPARATION_PROCESS_EXIT_V1.json']:
    path=AUDIT/name;value=inv.cache.read(path)
    assert value['process_exit_code']==0
    pins[str(path.relative_to(ROOT))]=inv.file_sha(path)
indices={}
for label,expected in [('FIELD',18237),('OTHER_TYPES',50162)]:
    path=AUDIT/('COMPLETE_'+label+'_PAGE_TASK_INDEX_V1.json')
    value=inv.cache.read(path)
    assert value['sources']==expected and sum(row['sources'] for row in value['roles'])==expected
    indices[label]=dict(sources=expected,pages=value['pages'],
        role_sources={row['role']:row['sources'] for row in value['roles']},
        role_tasks={row['role']:row['tasks'] for row in value['roles']})
    pins[str(path.relative_to(ROOT))]=inv.file_sha(path)
output=AUDIT/'ALL_NONRESTRICTED_NATIVE_PREPARATION_STATUS_V1.json'
assert not output.exists()
inv.write_json(output,dict(status='ALL_NONRESTRICTED_QUEUED_NATIVE_INPUTS_READY_NOT_CONTENT_COMPLETION',
    prepared_cohorts=groups,prepared_unique_sources=70192,
    previously_reviewed_literal_in_prepared_set=1,
    official_cache3_unprocessed_unique=70192,
    official_unprocessed_nonrestricted_unique_with_native_proof=70191,
    official_unprocessed_restricted_metadata_only_unique=1,
    same_number_does_not_mean_same_membership=True,
    current_content_review_or_admission_complete=False,phase_task_indices=indices,
    restricted_parent_bodies_decoded=0,cleaned_prose_authored_by_root=0,
    input_pins=dict(pins,**{str(Path(__file__).relative_to(ROOT)):inv.file_sha(Path(__file__))}),
    goal_complete=False,training_authorized=False))
print(json.dumps(dict(prepared=70192,unprocessed_nonrestricted_ready=70191,
    restricted_unprocessed=1,content_review_complete=False,phase_indices=indices)))
