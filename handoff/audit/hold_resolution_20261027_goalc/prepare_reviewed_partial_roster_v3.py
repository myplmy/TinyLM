"""Join completed author cohorts with the frozen whole roster and exact HOLD partition."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_partial_cache as partial
import guarded_reviewed_cache_v4 as guarded
from reviewed_hold_partition_v1 import SCHEMA as HOLD_SCHEMA, classify_hold

plan_path=inv.BASE/'resolution_join_plan_v4/complete.json'
selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'
approval_path=AUDIT/'ROOT_REVIEWED_PARTIAL_ADMISSIONS_V3.json'
roster_dir=inv.BASE/'roster_reviewed_partial_v3'
census_dir=inv.BASE/'guarded_partial_proposals_v3'
adoptions_path=inv.BASE/'reviewed_partial_adoptions_v3.json'
for path in [approval_path,roster_dir,census_dir,adoptions_path]:assert not path.exists(),path
plan,selection=map(inv.cache.read,[plan_path,selection_path])
assert plan['occurrence_counts']['documents']==460695 and plan['full_restricted_original_bodies_opened'] is False
assert selection['source_ids']==7857 and selection['unresolved_sources']==0
assert selection['unresolved_sources_meaning']=='ZERO_ONLY_WITHIN_SELECTED_ID_SET_NOT_WHOLE_CORPUS'
for doc in [plan,selection]:
    for name,sha in doc['input_pins'].items():assert inv.file_sha(ROOT/name)==sha,name
authored={r['original_text_sha256']:r for r in selection['rows']}
assert len(authored)==7857 and all(r['root_approved'] for r in authored.values())
cases=guarded.previous.hold_cases()
assert len(cases)==38
directory=plan_path.parent/plan['records_directory']
inv.verify(directory,plan['manifest'])
outcomes={};unique=Counter();changes=[]
for source in inv.cache.rows(directory,plan['manifest']):
    key=source['original_text_sha256'];assert key not in outcomes
    selected=authored.get(key)
    decision=selected['selected']['decision'] if selected else source['decision']
    assert decision in {'KEEP','EDIT','EXCLUDE','HOLD'}
    if decision!=source['decision']:
        assert source['decision']=='HOLD' or selected['id']=='expanded_train:1255247'
        changes.append(dict(id=selected['id'],original_text_sha256=key,before=source['decision'],after=decision))
    outcomes[key]=decision;unique[decision]+=1
assert len(outcomes)==297539 and set(authored)<=set(outcomes)
parent=inv.cache.read(inv.PARENT/'built.json')
positions=Counter();partition=Counter();seen_positions=set();observed_keys=set()
for source in inv.cache.rows(inv.PARENT/'hold',parent['manifests']['hold']):
    assert source['id'] not in seen_positions;seen_positions.add(source['id'])
    key=source['original_text_sha256'];observed_keys.add(key);decision=outcomes[key]
    positions.update(documents=1,input_ids=source['input_ids'],**{decision:1})
    positions[decision+'_input_ids']+=source['input_ids']
    if decision=='HOLD':
        kind='reviewed_hold' if key in cases else 'unprocessed'
        partition[kind]+=1;partition[kind+'_input_ids']+=source['input_ids']
assert observed_keys==set(outcomes)
assert positions['documents']==460695 and positions['input_ids']==462874291
assert positions['HOLD']==partition['reviewed_hold']+partition['unprocessed']
assert unique['HOLD']==70230 and len(set(cases)&set(outcomes))==38
paths=[plan_path,selection_path,AUDIT/'ROOT11_COMPLETED_COHORT_ADMISSION_SCOPE_V1.md',
    AUDIT/'ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1.json',AUDIT/'reviewed_hold_partition_v1.py',
    AUDIT/'guarded_reviewed_cache_v4.py',Path(__file__)]
approval=dict(status='ROOT_REVIEWED_PARTIAL_SOURCE_ADMISSIONS_GOAL_INCOMPLETE',root_approved=True,
    counts=dict(unique),occurrence_counts=dict(positions),remaining_hold=positions['HOLD'],
    reviewed_hold=partition['reviewed_hold'],unprocessed=partition['unprocessed'],
    hold_partition_input_ids=dict(partition),changed_unique_dispositions=changes,
    deferred_literal_sources=selection['deferred_literal_sources'],
    independent_birth_second_reading='NOT_COMPLETED',whole_corpus_semantic_completion=False,
    input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in paths},goal_complete=False,training_authorized=False)
inv.write_json(approval_path,approval)
evidence=dict(path=str(approval_path.relative_to(ROOT)),sha256=inv.file_sha(approval_path))
writer=inv.ShardWriter(roster_dir/'records','decisions',limit=19_999_999)
literal_ids=set(guarded.previous.reviewed.literal.load_registry())|guarded.previous.previous.exact.EXPECTED
actual=Counter();bound=set()
for proposed in inv.cache.rows(directory,plan['manifest']):
    row=dict(proposed);key=row['original_text_sha256'];selected=authored.get(key)
    if selected:
        choice=selected['selected'];decision=choice['decision'];bound.add(key)
        row.update(decision=decision,exact_authored_id=selected['id'],
            reason=choice.get('reason') or 'EXACT_PINNED_SOURCE_CONTEXT_REVIEW_AND_ROOT_JUDGMENT')
        row.pop('text',None);row.pop('clean_text_sha256',None);row.pop('manual',None)
        if decision in {'KEEP','EDIT'}:
            assert inv.file_sha(ROOT/choice['body'])==choice['clean_text_sha256']
            row['clean_text_sha256']=choice['clean_text_sha256']
            if decision=='EDIT':
                row['text']=(ROOT/choice['body']).read_text(encoding='utf-8')
                assert inv.sha(row['text'])==row['clean_text_sha256'] and not inv.corpus.MEMOS.search(row['text'])
            else:assert row['clean_text_sha256']==key
            row.pop('review_status',None);row.pop('content_reviewed',None)
            row.pop('root_disposition_approved',None);row.pop('hold_review_evidence',None)
            if selected['id'] in literal_ids or selected['id']=='expanded_train:1291499':
                row['manual']=dict(input_match_sha256=key,literal_guard_case_id=selected['id'],
                    exact_runtime_pair_id=selected['id'],phonetic_stress_pair_id=selected['id'],
                    root_reviewed=True,reason='EXACT_REVIEWED_SOURCE_BODY_PAIR_NOT_GLOBAL_GUARD_WAIVER')
        elif decision=='HOLD':
            case=cases[key]
            assert row['id']==case['id'] and choice['content_reviewed'] is True
            row.update(review_status='REVIEWED_NOT_ADMITTED',content_reviewed=True,
                root_disposition_approved=True,hold_review_evidence=case['authority_pin'])
    row.update(root_approved=row['decision']!='HOLD',cache_admitted=False,evidence=evidence)
    if row['decision']=='HOLD':classify_hold(row,cases)
    writer.append(row);actual[row['decision']]+=1
assert actual==unique and bound==set(authored)
manifest=writer.close(lineage=dict(approval=evidence))
inv.write_json(roster_dir/'complete.json',dict(schema=partial.SCHEMA,
    status='ROOT_REVIEWED_PARTIAL_RESIDUAL_CACHE_ROSTER',hold_partition_schema=HOLD_SCHEMA,
    parent_built_sha256=inv.file_sha(inv.PARENT/'built.json'),records_directory='records',manifest=manifest,
    counts={name:positions[name] for name in ['documents','input_ids']},unique_counts=dict(unique),
    remaining_hold=positions['HOLD'],reviewed_hold=partition['reviewed_hold'],unprocessed=partition['unprocessed'],
    hold_partition_input_ids=dict(partition),approval=evidence,goal_complete=False,training_authorized=False))
inv.write_json(adoptions_path,dict(schema='P106B_ROOT_TEXT_ADOPTIONS_V1',rows=[],reviews=[evidence],
    meaning='EXACT_BODIES_ARE_IN_FULL_SHA_LINKED_ROSTER_NOT_AN_UNPINNED_OVERRIDE_LIST'))
with guarded.runtime(selection_path):
    with guarded.previous.reviewed.reviewed_inputs():
        with partial.revision():pins=partial.engine.code_pins()
writer=inv.ShardWriter(census_dir/'ledger','proposals',limit=19_999_999)
coverage=Counter()
for row in inv.cache.rows(inv.PARENT/'hold',parent['manifests']['hold']):
    writer.append(row);coverage.update(documents=1,input_ids=row['input_ids'])
census_manifest=writer.close(lineage=dict(approval=evidence))
assert dict(coverage)=={name:positions[name] for name in ['documents','input_ids']}
inv.write_json(census_dir/'complete.json',dict(unprocessed=0,enumeration_unprocessed=0,
    meaning='FULL_SOURCE_ENUMERATION_ONLY_NOT_CONTENT_COMPLETION',content_unprocessed=partition['unprocessed'],
    reviewed_hold=partition['reviewed_hold'],remaining_hold=positions['HOLD'],counts=dict(coverage),manifest=census_manifest,
    pin=dict(recovery_revision_source_sha256=pins,parent_built_sha256=inv.file_sha(inv.PARENT/'built.json'),
        parent_verified_sha256=inv.file_sha(inv.PARENT/'verified.json'),scope_sha256=inv.file_sha(inv.BASE/'scope.json')),
    approval=evidence,goal_complete=False,training_authorized=False))
print(json.dumps(dict(status='WHOLE_SOURCE_ROSTER_READY_NOT_CACHE_BUILT',unique_counts=dict(unique),
    positions=dict(positions),hold_partition=dict(partition),runtime_pin_files=len(pins),goal_complete=False)))
