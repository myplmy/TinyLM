"""Join exact complete new review purposes; leave body guards for explicit root closure."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

preview_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW2.json'
snapshot_path=AUDIT/'supplemental_candidates_snapshot_v55.json'
plan_path=AUDIT/'reviewed_selection_plan_v32.json'
out=AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW3.json'
inv.require(not out.exists(),'new immutable purpose join required')
preview,snapshot,plan=map(inv.cache.read,[preview_path,snapshot_path,plan_path])
restricted={'expanded_train:'+str(n) for n in [14760,756966,15695,1216576,1250821,20624,6030]}
for name,digest in preview['input_pins'].items():
    inv.require(inv.file_sha(ROOT/name)==digest,'previous exact purpose join changed')
groups={'root_join_conflict_counter_v1':215,'repeat_local_context_counter_v1':40,
        'nominal_local_alias_counter_v1':223}
fresh={group:{} for group in groups}
for record in snapshot['records']:
    group=record['cohort']
    if group not in groups:
        continue
    inv.require(record['id'] not in fresh[group],'one purpose repeats a source')
    fresh[group][record['id']]=record
for group,expected in groups.items():
    coverage=snapshot['coverage'][group]
    inv.require(coverage['saved']==coverage['expected']==len(fresh[group])==expected
                and coverage['awaiting_review']==0,'all assigned source reviews must be saved')
    inv.require(all(row.get('body') and row['decision']!='NEEDS_ROOT'
        and row['status']!='MECHANICAL_REJECTION_NOT_APPLIED' for row in fresh[group].values()),
        'a new review purpose still lacks an exact materialized body')


def compact(choice):
    keys=['cohort','role','decision','body','clean_text_sha256','original','review','line','reason',
          'author_output','explicit_accept_assigned_input','explicit_accept_body','compare_source']
    return {key:choice[key] for key in keys if key in choice}


def verify(choice,ident):
    if ident in restricted or choice['decision']=='EXCLUDE':
        return
    inv.require(inv.file_sha(ROOT/choice['body'])==choice['clean_text_sha256'],'selected body changed')
    if choice.get('review'):
        inv.require(inv.file_sha(ROOT/choice['review']['path'])==choice['review']['sha256'],'selected review changed')


rows={}
for earlier in preview['rows']:
    ident=earlier['id']
    verify(earlier['selected'],ident)
    rows[ident]=dict(id=ident,original_text_sha256=earlier['original_text_sha256'],
        original_paths=earlier['original_paths'],selected=compact(earlier['selected']),
        selection_rule=earlier['selection_rule'],root_approved=earlier['root_approved'],
        prior_purpose_join=dict(path=str(preview_path.relative_to(ROOT)),id=ident),
        cache_admitted=False,goal_complete=False,training_authorized=False)
conflicts={row['id']:row for row in preview['unresolved']}
inv.require(set(conflicts)==set(fresh['root_join_conflict_counter_v1']),'all215 exact conflict sources must match')
counts=Counter()
for group in groups:
    for ident,row in sorted(fresh[group].items()):
        key=row['original']['sha256']
        verify(row,ident)
        earlier=rows.get(ident)
        if group=='root_join_conflict_counter_v1':
            inv.require(earlier is None and conflicts[ident]['original_text_sha256']==key,
                        'fresh mediation has a different source or bypasses the conflict set')
            rule='EXACT_PREVIOUS_NEW_AND_VARIANT_FULL_CONTEXT_REVIEW_WITH_ROOT_MEDIATIONS'
        elif earlier is None:
            rule='NEW_EXACT_SOURCE_CANDIDATE_FULL_CONTEXT_REVIEW_PENDING_ROOT_GUARDS'
        else:
            inv.require(ident=='expanded_train:1055007' and group=='nominal_local_alias_counter_v1',
                        'another new body overlap requires an explicit new mediation')
            old=earlier['selected']
            inv.require(earlier['original_text_sha256']==key,'overlapping source identity differs')
            raw=(ROOT/row['original']['path']).read_text(encoding='utf-8')
            expected=raw.split('\n\n',1)[0].replace('()','')
            new_body=(ROOT/row['body']).read_text(encoding='utf-8')
            inv.require(new_body.strip()==expected,'DBX mediation must preserve the exact completed first sentence')
            inv.require(row['decision']=='EDIT_TEXT','DBX unresolved reference tail requires an explicit new authored body')
            rule='EXACT_DBX_UNBOUND_REFERENCE_TAIL_QUARANTINE_SUPERSEDES_PRIOR_BODY'
            counts['EXACT_DBX_PRIOR_SOURCE_BODY_REVIEW_SUPERSESSION']+=1
        selected=compact(row)
        selected.update(decision='KEEP' if selected['clean_text_sha256']==key else 'EDIT',
                        original_text_sha256=key,root_approved=False)
        rows[ident]=dict(id=ident,original_text_sha256=key,original_paths=[row['original']['path']],
            selected=selected,selection_rule=rule,root_approved=False,
            exact_source_review=dict(snapshot=str(snapshot_path.relative_to(ROOT)),cohort=group,id=ident),
            cache_admitted=False,goal_complete=False,training_authorized=False)
        counts.update({group:1})
inv.require(set(rows)=={row['id'] for row in plan['records']} and len(rows)==plan['source_ids']==4381,
            'whole purpose source conservation differs')
raw_sources={}
for ident,row in rows.items():
    raw_sources.setdefault(row['original_text_sha256'],[]).append(ident)
same_raw_conflicts=[dict(original_text_sha256=key,ids=ids)
    for key,ids in raw_sources.items() if len({rows[ident]['selected'].get('clean_text_sha256') for ident in ids})>1]
result=dict(status='ALL4381_PURPOSE_CHOICES_JOINED_PENDING_EXPLICIT_ROOT_BODY_GUARD_CLOSURE',
    rows=sorted(rows.values(),key=lambda row:row['id']),source_ids=len(rows),selected_sources=len(rows),
    unresolved_sources=0,unresolved=[],same_raw_body_conflicts=same_raw_conflicts,
    counts=dict(counts),root_guard_closure_required=True,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [preview_path,snapshot_path,plan_path,
        AUDIT/'RESUME_FULL_GOAL_20261102_V3.md',AUDIT/'ROOT_DBX_SOURCE_MEDIATION_V1.md',Path(__file__)]},
    cache_admitted=0,goal_complete=False,training_authorized=False)
inv.require(len(json.dumps(result,ensure_ascii=False).encode())<20_000_000,'purpose join requires ordered shards')
inv.write_json(out,result)
print(json.dumps({key:result[key] for key in ['status','source_ids','counts','same_raw_body_conflicts']},ensure_ascii=False))
