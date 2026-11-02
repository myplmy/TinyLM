"""Materialize the full source roster with explicit unresolved counts and guards."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_partial_cache as partial
import guarded_reviewed_cache_v2 as guarded

plan_path=inv.BASE/'resolution_join_plan_v4/complete.json'
selection_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V10.json'
scope_path=AUDIT/'ROOT_PARTIAL_CACHE_V2_SCOPE_V1.md'
approval_path=AUDIT/'ROOT_REVIEWED_PARTIAL_ADMISSIONS_V2.json'
roster_dir=inv.BASE/'roster_reviewed_partial_v2'
census_dir=inv.BASE/'guarded_partial_proposals_v2'
adoptions_path=inv.BASE/'reviewed_partial_adoptions_v2.json'
inv.require(not roster_dir.exists() and not census_dir.exists() and not approval_path.exists()
            and not adoptions_path.exists(),'new immutable reviewed partial namespace required')
plan,selection=map(inv.cache.read,[plan_path,selection_path])
inv.require(plan['occurrence_counts']['documents']==460695 and plan['remaining_hold']==115526
            and selection['source_ids']==4381 and selection['unresolved_sources']==0,'whole source coverage differs')
for name,expected in plan['input_pins'].items():
    inv.require(inv.file_sha(ROOT/name)==expected,'full source plan input changed')
for name,expected in selection['input_pins'].items():
    inv.require(inv.file_sha(ROOT/name)==expected,'exact root selection changed')
authored={row['original_text_sha256']:row for row in selection['rows']}
inv.require(len(authored)==4381 and all(row['root_approved'] for row in authored.values()),'exact authored source set differs')
before=inv.cache.read(ROOT/next(name for name in plan['input_pins'] if name.endswith('PREVIEW5.json')))
old={row['original_text_sha256']:row for row in before['rows']}
changed=[]
for key,row in authored.items():
    prior=old[key]
    inv.require(row['selected']['decision']==prior['selected']['decision'],'a final correction changes prospective disposition')
    if row['selected'].get('clean_text_sha256')!=prior['selected'].get('clean_text_sha256'):
        changed.append(dict(id=row['id'],original_text_sha256=key,
            previous_clean_text_sha256=prior['selected'].get('clean_text_sha256'),
            clean_text_sha256=row['selected'].get('clean_text_sha256'),review=row['selected'].get('review')))
inv.require({row['id'] for row in changed}=={'expanded_train:'+str(n) for n in [1254536,467565,48585,77559]},
            'the four final source corrections differ')
approval=dict(status='ROOT_REVIEWED_PARTIAL_SOURCE_ADMISSIONS_GOAL_INCOMPLETE',root_approved=True,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [plan_path,selection_path,scope_path,
        AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V3.json',AUDIT/'ACTUAL_GUARDED_SOURCE_ROWS_V1.json',
        AUDIT/'ROOT_RUNTIME_PAIR_APPROVALS_V1.json',Path(__file__)]},
    counts=plan['counts'],occurrence_counts=plan['occurrence_counts'],final_exact_body_corrections=changed,
    remaining_hold=115526,unprocessed=115526,goal_complete=False,training_authorized=False)
inv.write_json(approval_path,approval)
evidence=dict(path=str(approval_path.relative_to(ROOT)),sha256=inv.file_sha(approval_path))
inv.verify(plan_path.parent/'records',plan['manifest'])
writer=inv.ShardWriter(roster_dir/'records','decisions',limit=19_999_999)
counts,seen=Counter(),set()
literal_ids=set(guarded.previous.reviewed.literal.load_registry())|guarded.exact.EXPECTED
for proposed in inv.cache.rows(plan_path.parent/'records',plan['manifest']):
    row=dict(proposed)
    key=row['original_text_sha256']
    inv.require(key not in seen,'whole source roster repeats an original SHA')
    seen.add(key)
    if key in authored:
        selected=authored[key]
        choice=selected['selected']
        inv.require(choice['decision']==row['decision'],'final authored outcome differs from the whole plan')
        if row['decision'] in {'KEEP','EDIT'}:
            inv.require(inv.file_sha(ROOT/choice['body'])==choice['clean_text_sha256'],'final authored body changed')
            row['clean_text_sha256']=choice['clean_text_sha256']
            if row['decision']=='EDIT':
                row['text']=(ROOT/choice['body']).read_text(encoding='utf-8')
        if selected['id'] in literal_ids:
            row['manual']=dict(input_match_sha256=key,literal_guard_case_id=selected['id'],
                exact_runtime_pair_id=selected['id'],root_reviewed=True,
                reason='EXACT_REVIEWED_SOURCE_BODY_PAIR_NOT_GLOBAL_GUARD_WAIVER')
    row.update(root_approved=row['decision']!='HOLD',cache_admitted=False,evidence=evidence)
    if row['decision']=='HOLD':
        inv.require(row.get('review_status')=='UNRESOLVED_NOT_ADMITTED' and
                    not row.get('text') and not row.get('clean_text_sha256'),'unresolved candidate leaked into roster')
    writer.append(row)
    counts[row['decision']]+=1
inv.require(len(seen)==297539 and dict(counts)==plan['counts'],'whole approved source conservation differs')
manifest=writer.close(lineage=dict(approval=evidence))
positions=plan['occurrence_counts']
inv.write_json(roster_dir/'complete.json',dict(schema=partial.SCHEMA,status='ROOT_REVIEWED_PARTIAL_RESIDUAL_CACHE_ROSTER',
    parent_built_sha256=inv.file_sha(inv.PARENT/'built.json'),records_directory='records',manifest=manifest,
    counts={name:positions[name] for name in ['documents','input_ids']},remaining_hold=115526,unprocessed=115526,
    approval=evidence,goal_complete=False,training_authorized=False))
inv.write_json(adoptions_path,dict(schema='P106B_ROOT_TEXT_ADOPTIONS_V1',rows=[],reviews=[evidence],
    meaning='EXACT_BODIES_ARE_IN_FULL_SHA_LINKED_ROSTER_NOT_AN_UNPINNED_OVERRIDE_LIST'))
# Reproduce the same code-pin context used by the actual frozen partial build.
with guarded.runtime(selection_path):
    with guarded.previous.reviewed.reviewed_inputs():
        with partial.revision():
            pins=partial.engine.code_pins()
parent=inv.cache.read(inv.PARENT/'built.json')
writer=inv.ShardWriter(census_dir/'ledger','proposals',limit=19_999_999)
coverage=Counter()
for row in inv.cache.rows(inv.PARENT/'hold',parent['manifests']['hold']):
    writer.append(row)
    coverage.update(documents=1,input_ids=row['input_ids'])
census_manifest=writer.close(lineage=dict(approval=evidence))
inv.require(dict(coverage)=={name:positions[name] for name in ['documents','input_ids']},'full source census differs')
inv.write_json(census_dir/'complete.json',dict(unprocessed=0,
    meaning='FULL_SOURCE_ENUMERATION_ONLY_NOT_CONTENT_COMPLETION',content_unprocessed=115526,
    counts=dict(coverage),manifest=census_manifest,
    pin=dict(recovery_revision_source_sha256=pins,parent_built_sha256=inv.file_sha(inv.PARENT/'built.json'),
             parent_verified_sha256=inv.file_sha(inv.PARENT/'verified.json'),scope_sha256=inv.file_sha(inv.BASE/'scope.json')),
    approval=evidence,goal_complete=False,training_authorized=False))
print(json.dumps(dict(status='WHOLE_REVIEWED_PARTIAL_ROSTER_READY_NOT_CACHE_BUILT',counts=dict(counts),
    remaining_hold=115526,unique_sources=len(seen),runtime_input_files=len(pins),final_corrected_bodies=len(changed))))
