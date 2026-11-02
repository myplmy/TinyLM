"""Refresh exact independent review pins after one corrected input reference."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
source=(AUDIT/'collect_supplemental_candidates_v57.py').read_text(encoding='utf-8')
assert source.count('supplemental_candidates_snapshot_v57.json')==1
source=source.replace('supplemental_candidates_snapshot_v57.json','supplemental_candidates_snapshot_v58.json',1)
with (AUDIT/'collect_supplemental_candidates_v58.py').open('x',encoding='utf-8') as stream:
    stream.write(source)
plan=(AUDIT/'materialize_reviewed_selection_plan_v34.py').read_text(encoding='utf-8')
for before,after in [('reviewed_selection_plan_v34.json','reviewed_selection_plan_v35.json'),
                     ('supplemental_candidates_snapshot_v57.json','supplemental_candidates_snapshot_v58.json')]:
    assert plan.count(before)==1,before
    plan=plan.replace(before,after,1)
with (AUDIT/'materialize_reviewed_selection_plan_v35.py').open('x',encoding='utf-8') as stream:
    stream.write(plan)
preview=(AUDIT/'prepare_authored_root_selection_v10_preview4.py').read_text(encoding='utf-8')
for before,after in [
    ("previous_path = AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW3.json'", "previous_path = AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW4.json'"),
    ("output = AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW4.json'", "output = AUDIT/'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW5.json'"),
    ('supplemental_candidates_snapshot_v56.json','supplemental_candidates_snapshot_v58.json'),
    ('reviewed_selection_plan_v33.json','reviewed_selection_plan_v35.json'),
    ("[('post_body_guard_counter_v1',14), ('semantic_field_counter_v1',12)]", "[('post_semantic_independent_v1',26), ('runtime_guard_counter_v1',23)]"),
    ("source['original_text_sha256']", "source['original']['sha256']"),
]:
    assert preview.count(before)==1,before
    preview=preview.replace(before,after,1)
with (AUDIT/'prepare_authored_root_selection_v10_preview5.py').open('x',encoding='utf-8') as stream:
    stream.write(preview)
print('CORRECTED49_SOURCE_BINDINGS_AND_EXACT_PREDECESSOR_JOIN_PREPARED')
