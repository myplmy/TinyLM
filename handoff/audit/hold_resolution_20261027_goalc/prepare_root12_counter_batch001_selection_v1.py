"""Approve only source-bound, independently reviewed, mechanically closed rows."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy
from numeric_atom_integrity_v1 import numeric_atom_changes

GROUP='root12_independent_admission_counter_v1'
guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
assert inv.file_sha(guard_path)=='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'
guard=inv.cache.read(guard_path)
previous_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11.json'
assert inv.file_sha(previous_path)=='E07FF5FEB014BC81CC014D66B3DD547A07A57651BCF4745F3729E5EDEBB949DA'
previous=inv.cache.read(previous_path)
snapshot_path=inv.BASE/(GROUP+'_snapshots')/'v3/complete.json'
snapshot=inv.cache.read(snapshot_path)
assert not snapshot['errors'] and not snapshot['invalid_task_rows'] and not snapshot['unparsed_review_history']
assert snapshot['root_adopted']==snapshot['cache_admitted']==0
manifest_path=inv.BASE/GROUP/'manifest.json'
manifest=inv.cache.read(manifest_path);sources={row['id']:row for row in manifest['rows']}
records=[]
for shard in snapshot['shards']:
    assert inv.file_sha(ROOT/shard['path'])==shard['sha256'];records+=inv.cache.read(ROOT/shard['path'])
assert len(records)==snapshot['records'] and len(records)+snapshot['unreviewed_count']==3688
prior_ids={row['id'] for row in previous['rows']};prior_hashes={row['original_text_sha256'] for row in previous['rows']}
selected=[];checks=[];deferred=[];positions=0
for row in records:
    key=row['id'];source=sources[key]
    assert key not in prior_ids and source['original_text_sha256'] not in prior_hashes
    assert key not in guard['restricted_ids']
    assert all(source[label]['sha256'] not in guard['restricted_hashes'] for label in ['original','candidate'])
    assert source['primary_author_role']!=source['role']==row['role']
    if not row.get('body') or row.get('error') or row.get('decision') not in {'ADOPT_CANDIDATE','EDIT_TEXT','KEEP_SOURCE'}:
        deferred.append(dict(id=key,reason='NO_CLOSED_INDEPENDENT_BODY'));continue
    assert row['clean_text_sha256'] not in guard['restricted_hashes']
    assert inv.file_sha(ROOT/source['original']['path'])==source['original']['sha256']
    assert inv.file_sha(ROOT/row['body'])==row['clean_text_sha256']
    for pin in [source['prior_review'],row['review']]:
        assert inv.file_sha(ROOT/pin['path'])==pin['sha256']
    original=(ROOT/source['original']['path']).read_bytes().decode('utf-8')
    body=(ROOT/row['body']).read_bytes().decode('utf-8')
    assert body.strip() and len(body.encode('utf-8'))<20_000_000
    numeric=numeric_atom_changes(original,body)
    guards=dict(numeric_atoms=not numeric,code=policy.code_preserved(original,body),
        unicode=policy.unicode_examples_preserved(original,body),style=policy.semantic_style_preserved(original,body),
        ordered=policy.ordered_deletion(original,body),no_memo=not bool(inv.corpus.MEMOS.search(body)))
    checks.append(dict(id=key,original=source['original'],body=dict(path=row['body'],sha256=row['clean_text_sha256']),
        primary_review=source['prior_review'],counter_review=row['review'],guards=guards,numeric_flags=numeric))
    if not all(guards.values()):
        deferred.append(dict(id=key,reason='EXACT_SOURCE_BODY_GUARD_REQUIRES_INDIVIDUAL_CLOSURE',
            flags=[name for name,value in guards.items() if not value]));continue
    decision='KEEP' if row['clean_text_sha256']==source['original']['sha256'] else 'EDIT'
    choice=dict(cohort=GROUP,decision=decision,body=row['body'],clean_text_sha256=row['clean_text_sha256'],
        original=source['original'],review=row['review'],reason=row['reason'],author_output=row.get('author_output'),
        compare_source=None,root_approved=True,primary_review=source['prior_review'],
        primary_source_cohort=source['primary_source_cohort'])
    selected.append(dict(id=key,original_text_sha256=source['original_text_sha256'],selected=choice,
        original_paths=[source['original']],root_approved=True,cache_admitted=False,
        status='ROOT_CLOSED_INDEPENDENT_COUNTER_PARTIAL_SOURCE_CHOICE',
        guard_closure_id='ROOT12_COUNTER_BATCH001_CLOSURE_V1'))
    positions+=source['occurrences']
assert selected and len(selected)+len(deferred)==len(records)
all_rows=previous['rows']+selected
assert len(all_rows)==len({r['id'] for r in all_rows})==len({r['original_text_sha256'] for r in all_rows})
closure_path=AUDIT/'ROOT12_COUNTER_BATCH001_CLOSURE_V1.json'
out=AUDIT/'ROOT_AUTHORED_SELECTIONS_V12.json'
assert not closure_path.exists() and not out.exists()
input_paths=[previous_path,snapshot_path,manifest_path,guard_path,Path(__file__),
    AUDIT/'numeric_atom_integrity_v1.py',Path(policy.__file__),AUDIT/'ROOT12_COUNTER_BATCH001_ADMISSION_SCOPE_V1.md',
    AUDIT/'ROOT12_INDEPENDENT_COUNTER_INPUTS_VERIFIED_V1.json']
pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in input_paths}
closure=dict(status='ROOT_COUNTER_BATCH_INDEPENDENT_SOURCE_AND_ALL_GUARDS_CLOSED',
    snapshot_review_rows=len(records),root_approved_new_sources=len(selected),root_approved_new_positions=positions,
    remaining_counter_sources=snapshot['unreviewed_count'],individual_deferred=deferred,
    full_source_context_review_by_distinct_Luna_roles=True,root_training_TXT_authored=0,
    guard_failures_waived=0,checks=checks,input_pins=pins,
    root_selected_new=len(selected),cache_admitted=0,goal_complete=False,training_authorized=False,
    limits='Independent per-source context reviews and exact static guards; not all-fact verification, model quality or cache execution.')
inv.write_json(closure_path,closure)
deferred_literal=[key for key in previous['deferred_literal_ids'] if key not in {r['id'] for r in selected}]
document=dict(status='ROOT_AUTHOR_BODY_SELECTIONS_NOT_CACHE_ADMISSION',rows=all_rows,
    source_ids=len(all_rows),selected_sources=len(all_rows),unresolved_sources=0,unresolved=[],
    unresolved_sources_meaning='ZERO_ONLY_WITHIN_SELECTED_ID_SET_NOT_WHOLE_CORPUS',
    selection_scope='PRIOR_ROOT11_UNCHANGED_PLUS_EXACT_INDEPENDENT_COUNTER_BATCH001',
    counts=dict(Counter(row['selected']['decision'] for row in all_rows)),
    deferred_literal_sources=len(deferred_literal),deferred_literal_ids=deferred_literal,
    official_cache_v3_unprocessed_unique_before_this_selection=70192,
    new_approved_sources=len(selected),new_approved_positions=positions,
    pending_independent_counter_sources=snapshot['unreviewed_count'],
    individually_deferred_counter_sources=deferred,root_guard_closure_required=False,
    closure=dict(path=str(closure_path.relative_to(ROOT)),sha256=inv.file_sha(closure_path)),
    prior_selection=dict(path=str(previous_path.relative_to(ROOT)),sha256=inv.file_sha(previous_path)),
    prior_selected_rows_preserved_exactly=True,input_pins=dict(pins,**{str(closure_path.relative_to(ROOT)):inv.file_sha(closure_path)}),
    expected_roster_HOLD_unique=70230-len(selected),expected_roster_HOLD_positions=110173-positions,
    restricted_parent_full_bodies_opened=False,whole_corpus_semantic_completion=False,
    cache_admitted=0,goal_complete=False,training_authorized=False)
inv.write_json(out,document)
print(__import__('json').dumps({key:document[key] for key in ['source_ids','counts','new_approved_sources',
    'new_approved_positions','expected_roster_HOLD_unique','expected_roster_HOLD_positions',
    'individually_deferred_counter_sources']},ensure_ascii=False))
print('ROOT12',inv.file_sha(out))
