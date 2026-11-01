"""Reuse strict full579 coverage and retain every unfinished review placeholder."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'collect_supplemental_candidates_v39.py').read_text(encoding='utf-8')
assert source.count('supplemental_candidates_snapshot_v39.json') == 1
source = source.replace('supplemental_candidates_snapshot_v39.json', 'supplemental_candidates_snapshot_v40.json')
output = AUDIT / 'collect_supplemental_candidates_v40.py'
compile(source, str(output), 'exec')
with output.open('x', encoding='utf-8') as stream:
    stream.write(source)
source = (AUDIT / 'materialize_reviewed_selection_plan_v16.py').read_text(encoding='utf-8')
for before, after in [('reviewed_selection_plan_v16.json', 'reviewed_selection_plan_v17.json'),
                      ('supplemental_candidates_snapshot_v39.json', 'supplemental_candidates_snapshot_v40.json')]:
    assert source.count(before) == 1
    source = source.replace(before, after)
output = AUDIT / 'materialize_reviewed_selection_plan_v17.py'
compile(source, str(output), 'exec')
with output.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared snapshot40 and plan17; strict579 TASK/view guards and missing-review placeholders unchanged.')
