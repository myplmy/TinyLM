"""Collect the entire independent26 plus actual runtime/style23 source purposes."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
source=(AUDIT/'collect_supplemental_candidates_v56.py').read_text(encoding='utf-8')
replacements=[
 ('"supplemental_candidates_snapshot_v56.json"','"supplemental_candidates_snapshot_v57.json"'),
 ('groups = list(dict.fromkeys(groups))',
  'groups += ["post_semantic_independent_v1", "runtime_guard_counter_v1"]\ngroups = list(dict.fromkeys(groups))'),
 ('[("post_body_guard_counter_v1", 14), ("semantic_field_counter_v1", 12)]',
  '[("post_body_guard_counter_v1", 14), ("semantic_field_counter_v1", 12), ("post_semantic_independent_v1", 26), ("runtime_guard_counter_v1", 23)]'),
 ('"post_body_guard_counter_v1", "semantic_field_counter_v1"}:\n        absolute_paths',
  '"post_body_guard_counter_v1", "semantic_field_counter_v1", "post_semantic_independent_v1", "runtime_guard_counter_v1"}:\n        absolute_paths'),
 ('\ndef digest(payload):',
  '\nextra_incident = BASE / "agents/context_latin/runtime_guard_counter_v1/path_error_note_v1.md"\ninput_pins[str(extra_incident.relative_to(ROOT))] = inv.file_sha(extra_incident)\n\ndef digest(payload):'),
]
for before,after in replacements:
    assert source.count(before)==1,before
    source=source.replace(before,after,1)
with (AUDIT/'collect_supplemental_candidates_v57.py').open('x',encoding='utf-8') as stream:
    stream.write(source)
plan=(AUDIT/'materialize_reviewed_selection_plan_v33.py').read_text(encoding='utf-8')
for before,after in [
 ('"reviewed_selection_plan_v33.json"','"reviewed_selection_plan_v34.json"'),
 ('"supplemental_candidates_snapshot_v56.json"','"supplemental_candidates_snapshot_v57.json"'),
 ('"post_body_guard_counter_v1", "semantic_field_counter_v1"]]',
  '"post_body_guard_counter_v1", "semantic_field_counter_v1", "post_semantic_independent_v1", "runtime_guard_counter_v1"]]'),
]:
    assert plan.count(before)==1,before
    plan=plan.replace(before,after,1)
with (AUDIT/'materialize_reviewed_selection_plan_v34.py').open('x',encoding='utf-8') as stream:
    stream.write(plan)
print('ALL49_INDEPENDENT_SOURCE_ROWS_COLLECTION_PREPARED')
