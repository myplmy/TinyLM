"""Reuse the strict collector for all579 lexical and all27 ordinal assignments."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'collect_supplemental_candidates_v40.py').read_text(encoding='utf-8')
changes = [
    ('supplemental_candidates_snapshot_v40.json', 'supplemental_candidates_snapshot_v41.json'),
    ('groups += ["root_selected_lexical_counter_v1"]',
     'groups += ["root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1"]'),
    ('strict_task_cohorts.add("root_selected_lexical_counter_v1")',
     'strict_task_cohorts.update({"root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1"})')
]
for before, after in changes:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
anchor = 'views_manifest["rows"].extend(lexical_views["rows"])'
assert source.count(anchor) == 1
source = source.replace(anchor, anchor + '''
ordinal_views_path = BASE / "ordinal_metadata_counter_v26_v1/reading_views_manifest_v1.json"
ordinal_views = inv.cache.read(ordinal_views_path)
inv.require(inv.file_sha(ROOT / ordinal_views["source_manifest"]["path"]) == ordinal_views["source_manifest"]["sha256"],
            "all27 ordinal views must refer to their exact assignment")
input_pins[str(ordinal_views_path.relative_to(ROOT))] = inv.file_sha(ordinal_views_path)
views_manifest["rows"].extend(ordinal_views["rows"])
''')
anchor = 'inv.require(coverage["root_selected_lexical_counter_v1"]["expected"] == 579,'
assert source.count(anchor) == 1
source = source.replace(anchor, '''inv.require(coverage["ordinal_metadata_counter_v26_v1"]["expected"] == 27,
            "every ordinal census source must remain visible even before review")
''' + anchor)
destination = AUDIT / 'collect_supplemental_candidates_v41.py'
compile(source, str(destination), 'exec')
with destination.open('x', encoding='utf-8') as stream:
    stream.write(source)
source = (AUDIT / 'materialize_reviewed_selection_plan_v17.py').read_text(encoding='utf-8')
changes = [
    ('reviewed_selection_plan_v17.json', 'reviewed_selection_plan_v18.json'),
    ('supplemental_candidates_snapshot_v40.json', 'supplemental_candidates_snapshot_v41.json'),
    ('"root_selected_literal_counter_v4", "root_selected_lexical_counter_v1"]]',
     '"root_selected_literal_counter_v4", "root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1"]]')
]
for before, after in changes:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
destination = AUDIT / 'materialize_reviewed_selection_plan_v18.py'
compile(source, str(destination), 'exec')
with destination.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared strict snapshot41 and plan18; no automatic root/cache admission.')
