"""Reuse exact prior-root comparison; every new body conflict remains explicit."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'prepare_authored_root_selection_v9_preview.py').read_text(encoding='utf-8')
changes = [
 ('reviewed_selection_plan_v13.json', 'reviewed_selection_plan_v18.json'),
 ('ROOT_AUTHORED_SELECTIONS_V8.json', 'ROOT_AUTHORED_SELECTIONS_V9.json'),
 ('ROOT_AUTHORED_SELECTION_CONTRACT_V7.md', 'ROOT_AUTHORED_SELECTION_CONTRACT_V8.md'),
 ('ROOT_AUTHORED_SELECTIONS_V9_PREVIEW.json', 'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW.json'),
 ('groups = ["policy_v23_literal_counter_v1", "policy_v23_structural_counter_v1", "root_selected_literal_counter_v4"]',
  'groups = ["root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1"]'),
 ('previous_root8', 'previous_root9'),
 ('ROOT8', 'ROOT9'),
 ('root8', 'root9')
]
for before, after in changes:
    assert source.count(before) >= 1, before
    source = source.replace(before, after)
destination = AUDIT / 'prepare_authored_root_selection_v10_preview.py'
compile(source, str(destination), 'exec')
with destination.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared root10 preview; fresh unresolved rows cannot borrow an earlier body.')
