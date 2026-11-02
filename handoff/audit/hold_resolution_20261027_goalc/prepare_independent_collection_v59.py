"""Freeze final narrow source corrections without changing preceding inputs."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
source=(AUDIT/'collect_supplemental_candidates_v58.py').read_text(encoding='utf-8')
assert source.count('supplemental_candidates_snapshot_v58.json')==1
source=source.replace('supplemental_candidates_snapshot_v58.json','supplemental_candidates_snapshot_v59.json',1)
with (AUDIT/'collect_supplemental_candidates_v59.py').open('x',encoding='utf-8') as stream:
    stream.write(source)
plan=(AUDIT/'materialize_reviewed_selection_plan_v35.py').read_text(encoding='utf-8')
for before,after in [('reviewed_selection_plan_v35.json','reviewed_selection_plan_v36.json'),
                     ('supplemental_candidates_snapshot_v58.json','supplemental_candidates_snapshot_v59.json')]:
    assert plan.count(before)==1,before
    plan=plan.replace(before,after,1)
with (AUDIT/'materialize_reviewed_selection_plan_v36.py').open('x',encoding='utf-8') as stream:
    stream.write(plan)
preview=(AUDIT/'prepare_authored_root_selection_v10_preview5.py').read_text(encoding='utf-8')
for before,after in [('supplemental_candidates_snapshot_v58.json','supplemental_candidates_snapshot_v59.json'),
                     ('reviewed_selection_plan_v35.json','reviewed_selection_plan_v36.json'),
                     ('ROOT_AUTHORED_SELECTIONS_V10_PREVIEW5.json','ROOT_AUTHORED_SELECTIONS_V10_PREVIEW6.json')]:
    assert preview.count(before)==1,before
    preview=preview.replace(before,after,1)
with (AUDIT/'prepare_authored_root_selection_v10_preview6.py').open('x',encoding='utf-8') as stream:
    stream.write(preview)
print('FINAL49_EXACT_REVIEW_PINS_PREPARED')
