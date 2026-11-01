"""Track every assigned237 source, including unsaved or unresolved reviews."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'collect_supplemental_candidates_v41.py').read_text(encoding='utf-8')
changes = [
 ('supplemental_candidates_snapshot_v41.json', 'supplemental_candidates_snapshot_v42.json'),
 ('groups += ["root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1"]',
  'groups += ["root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1", "profile_strata_source_counter_v25_v1"]'),
 ('strict_task_cohorts.update({"root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1"})',
  'strict_task_cohorts.update({"root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1", "profile_strata_source_counter_v25_v1"})')
]
for before, after in changes:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
anchor = 'views_manifest["rows"].extend(ordinal_views["rows"])'
assert source.count(anchor) == 1
source = source.replace(anchor, anchor + '''
profile_views_path = BASE / "profile_strata_source_counter_v25_v1/reading_views_manifest_v1.json"
profile_views = inv.cache.read(profile_views_path)
inv.require(inv.file_sha(ROOT / profile_views["source_manifest"]["path"]) == profile_views["source_manifest"]["sha256"],
            "all237 full-source views must refer to their exact assignment")
input_pins[str(profile_views_path.relative_to(ROOT))] = inv.file_sha(profile_views_path)
views_manifest["rows"].extend(profile_views["rows"])
''')
anchor = 'inv.require(coverage["ordinal_metadata_counter_v26_v1"]["expected"] == 27,'
assert source.count(anchor) == 1
source = source.replace(anchor, '''inv.require(coverage["profile_strata_source_counter_v25_v1"]["expected"] == 237,
            "all237 new assignments must remain visible before their reviews finish")
''' + anchor)
destination = AUDIT / 'collect_supplemental_candidates_v42.py'
compile(source, str(destination), 'exec')
with destination.open('x', encoding='utf-8') as stream:
    stream.write(source)
source = (AUDIT / 'materialize_reviewed_selection_plan_v18.py').read_text(encoding='utf-8')
for before, after in [
 ('reviewed_selection_plan_v18.json', 'reviewed_selection_plan_v19.json'),
 ('supplemental_candidates_snapshot_v41.json', 'supplemental_candidates_snapshot_v42.json'),
 ('"root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1"]]',
  '"root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1", "profile_strata_source_counter_v25_v1"]]')]:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
destination = AUDIT / 'materialize_reviewed_selection_plan_v19.py'
compile(source, str(destination), 'exec')
with destination.open('x', encoding='utf-8') as stream:
    stream.write(source)
print('Prepared snapshot42 and plan19 with strict579/27/237 coverage and missing-review placeholders.')
