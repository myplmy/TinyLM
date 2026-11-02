"""Extend the frozen collector to the exact215 conflict assignment."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent


def once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)


source = (AUDIT / "collect_supplemental_candidates_v51.py").read_text(encoding="utf-8")
source = once(source, '"supplemental_candidates_snapshot_v51.json"', '"supplemental_candidates_snapshot_v52.json"')
source = once(source, "groups = list(dict.fromkeys(groups))",
    'groups += ["root_join_conflict_counter_v1"]' + chr(10) + "groups = list(dict.fromkeys(groups))")
source = once(source, 'if directory.name == "birth_field_native_counter_v1":',
    'if directory.name in {"birth_field_native_counter_v1", "root_join_conflict_counter_v1"}:')
extension = '''join_path = BASE / "root_join_conflict_counter_v1/manifest.json"
join_manifest = inv.cache.read(join_path)
inv.require(len(join_manifest["rows"]) == 215, "all215 source assignments are required")
input_pins[str(join_path.relative_to(ROOT))] = inv.file_sha(join_path)
strict_task_cohorts.add("root_join_conflict_counter_v1")
for join_row in join_manifest["rows"]:
    join_views = {}
    for label in ["original", "candidate"]:
        pin = join_row[label]
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "join input bytes changed")
        text = (ROOT / pin["path"]).read_text(encoding="utf-8")
        join_views[label] = [dict(source_path=pin["path"],
            sha256=inv.sha(text[offset:offset + 6000]),
            source_characters=[offset, min(offset + 6000, len(text))])
            for offset in range(0, len(text), 6000)]
    views_manifest["rows"].append(dict(id=join_row["id"], role=join_row["role"], views=join_views,
        virtual_windows_of_exact_source=True, separate_window_files_created=False))
'''
source = once(source, "def digest(payload):", extension + chr(10) + "def digest(payload):")
source = once(source, "for detail in coverage.values():",
    'inv.require(coverage["root_join_conflict_counter_v1"]["expected"] == 215, "all215 conflict assignments must remain visible")' + chr(10) +
    "for detail in coverage.values():")
with (AUDIT / "collect_supplemental_candidates_v52.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
source = (AUDIT / "materialize_reviewed_selection_plan_v28.py").read_text(encoding="utf-8")
source = once(source, '"reviewed_selection_plan_v28.json"', '"reviewed_selection_plan_v29.json"')
source = once(source, '"supplemental_candidates_snapshot_v51.json"', '"supplemental_candidates_snapshot_v52.json"')
source = once(source, '"birth_field_native_counter_v1"]]',
    '"birth_field_native_counter_v1", "root_join_conflict_counter_v1"]]')
with (AUDIT / "materialize_reviewed_selection_plan_v29.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
print("EXACT215_JOIN_COLLECTION_AND_OUTPUT_BINDINGS_PREPARED")
