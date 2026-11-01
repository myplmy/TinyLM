"""Add all579 assignments, including explicit missing-review placeholders."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'prepare_reviewed_selection_plan_v15.py').read_text(encoding='utf-8')
for before, after in [
    ('reviewed_selection_plan_v15.json', 'reviewed_selection_plan_v16.json'),
    ('supplemental_candidates_snapshot_v38.json', 'supplemental_candidates_snapshot_v39.json'),
    ('"policy_v23_structural_counter_v1", "root_selected_literal_counter_v4"]]',
     '"policy_v23_structural_counter_v1", "root_selected_literal_counter_v4", "root_selected_lexical_counter_v1"]]')
]:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
output = AUDIT / 'materialize_reviewed_selection_plan_v16.py'
compile(source, str(output), 'exec')
with output.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared plan16: missing current579 reviews cannot fall back to old selected bodies.')
