"""Apply exactly the two named follow-up purposes to their pinned predecessors."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

previous_path = AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW4.json'
snapshot_path = AUDIT/'supplemental_candidates_snapshot_v60.json'
plan_path = AUDIT/'reviewed_selection_plan_v37.json'
output = AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW6.json'
inv.require(not output.exists(), 'new exact source-purpose preview required')
previous, snapshot, plan = map(inv.cache.read, [previous_path,snapshot_path,plan_path])
rows = {row['id']:dict(row) for row in previous['rows']}
counts = Counter()
for group, expected in [('post_semantic_independent_v1',26), ('runtime_guard_counter_v1',23)]:
    manifest_path = inv.BASE/group/'manifest.json'
    assigned = inv.cache.read(manifest_path)
    assignment = {row['id']:row for row in assigned['rows']}
    fresh = [row for row in snapshot['records'] if row['cohort'] == group]
    inv.require(len(fresh) == len(assignment) == expected and
                snapshot['coverage'][group]['awaiting_review'] == 0, 'follow-up scope is incomplete')
    for record in fresh:
        ident = record['id']
        old = rows[ident]
        source = assignment[ident]
        inv.require(old['original_text_sha256'] == record['original']['sha256'] == source['original']['sha256'],
                    'follow-up original identity changed')
        inv.require(old['selected']['clean_text_sha256'] == source['candidate']['sha256'],
                    'follow-up is not bound to the exact preceding selected body')
        inv.require(record.get('body') and record['decision'] != 'NEEDS_ROOT' and
                    record['status'] != 'MECHANICAL_REJECTION_NOT_APPLIED', 'new source review is not materialized')
        inv.require(inv.file_sha(ROOT/record['body']) == record['clean_text_sha256'] and
                    inv.file_sha(ROOT/record['review']['path']) == record['review']['sha256'],
                    'follow-up body or review changed')
        choice = {key:record[key] for key in ['cohort','role','body','clean_text_sha256','original','review',
                    'line','reason','author_output'] if key in record}
        choice.update(decision='KEEP' if record['clean_text_sha256'] == old['original_text_sha256'] else 'EDIT',
                      root_approved=False)
        rows[ident] = dict(old, selected=choice, root_approved=False,
            selection_rule='EXACT_ASSIGNED_FOLLOWUP_PURPOSE_AND_FULL_SOURCE_REVIEW_PENDING_INDEPENDENT_CLOSURE',
            prior_exact_body=dict(path=str(previous_path.relative_to(ROOT)),
                                 clean_text_sha256=old['selected']['clean_text_sha256']),
            exact_followup=dict(cohort=group, snapshot=str(snapshot_path.relative_to(ROOT))),
            cache_admitted=False, goal_complete=False)
        counts[group] += 1
inv.require(len(rows) == 4381 and set(rows) == {row['id'] for row in plan['records']}, 'whole source set differs')
result = dict(status='EXACT4381_CHOICES_WITH26_FOLLOWUPS_PENDING_ROOT_AND_RUNTIME_GUARD_CLOSURE',
    rows=sorted(rows.values(), key=lambda row:row['id']), source_ids=len(rows), selected_sources=len(rows),
    unresolved_sources=0, unresolved=[], counts=dict(counts), root_guard_closure_required=True,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [previous_path,snapshot_path,plan_path,Path(__file__)]},
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.write_json(output,result)
print(json.dumps(dict(source_ids=len(rows), exact_followups=dict(counts))))
