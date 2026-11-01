"""Reuse hash-checked TASK indexes with the strict single-ID TASK parser."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'make_lexical_task_view_indexes_v2.py').read_text(encoding='utf-8')
changes = [
 ('from scripts import p106b_hold_resolution_inventory as inv',
  'from scripts import p106b_hold_resolution_inventory as inv\nfrom scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards'),
 ("COHORT = 'root_selected_lexical_counter_v1'", "COHORT = 'profile_strata_source_counter_v25_v1'"),
 ("'reading_indexes_v2'", "'reading_indexes_v1'"),
 ("len(by_id) == len(views['rows']) == 579", "len(by_id) == len(views['rows']) == 237"),
 ("inv.require(len(tasks) == 32, 'all32 original TASKs must remain assigned')",
  "inv.require(len(tasks) == len(ids), 'each assigned source must have exactly one TASK')"),
 ('''        assigned = re.findall(r'^## ((?:expanded_train|historical_train|validation):[0-9]+)[ \\t]*$',
                              task.read_text(encoding='utf-8'), re.M)''',
  "        assigned = sorted(safeguards.explicit_task_ids(task.read_text(encoding='utf-8')))"),
 ("sum(role_counts.values()) == 579 and len(seen_views) == 2937",
  "sum(role_counts.values()) == 237 and len(seen_views) == sum(len(parts) for row in views['rows'] for parts in row['views'].values())")
]
for before, after in changes:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
destination = AUDIT / 'make_profile237_task_indexes_v1.py'
compile(source, str(destination), 'exec')
with destination.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared per-TASK exact indexes for all237 source pairs.')
