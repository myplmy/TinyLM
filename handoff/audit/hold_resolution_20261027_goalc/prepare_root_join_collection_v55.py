"""Refresh the same complete cohort scope after exact review-path corrections."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
source=(AUDIT/'collect_supplemental_candidates_v54.py').read_text(encoding='utf-8')
assert source.count('"supplemental_candidates_snapshot_v54.json"')==1
source=source.replace('"supplemental_candidates_snapshot_v54.json"','"supplemental_candidates_snapshot_v55.json"',1)
with (AUDIT/'collect_supplemental_candidates_v55.py').open('x',encoding='utf-8') as stream:
    stream.write(source)
source=(AUDIT/'materialize_reviewed_selection_plan_v31.py').read_text(encoding='utf-8')
for old,new in [('"reviewed_selection_plan_v31.json"','"reviewed_selection_plan_v32.json"'),
                ('"supplemental_candidates_snapshot_v54.json"','"supplemental_candidates_snapshot_v55.json"')]:
    assert source.count(old)==1
    source=source.replace(old,new,1)
with (AUDIT/'materialize_reviewed_selection_plan_v32.py').open('x',encoding='utf-8') as stream:
    stream.write(source)
print('SAME478_EXACT_REVIEW_SCOPE_REFRESH_PREPARED')
