"""Reuse the collector with exact output bindings for all753 birth reviews."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent


def once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)


source = (AUDIT / "collect_supplemental_candidates_v48.py").read_text(encoding="utf-8")
source = once(source, '"supplemental_candidates_snapshot_v48.json"', '"supplemental_candidates_snapshot_v49.json"')
source = once(source, "from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards",
    "from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards" + chr(10) +
    "from scripts import p106b_hold_resolution_author_output_bindings_v1 as explicit_output")
source = once(source, "groups = list(dict.fromkeys(groups))", 'groups += ["birth_field_native_counter_v1"]' + chr(10) + "groups = list(dict.fromkeys(groups))")
extension = '''birth_views_path = BASE / "birth_field_native_counter_v1/reading_views_manifest_v1.json"
birth_views = inv.cache.read(birth_views_path)
inv.require(inv.file_sha(ROOT / birth_views["source_manifest"]["path"]) == birth_views["source_manifest"]["sha256"],
            "birth reading views refer to another assignment")
input_pins[str(birth_views_path.relative_to(ROOT))] = inv.file_sha(birth_views_path)
input_pins["scripts/p106b_hold_resolution_author_output_bindings_v1.py"] = inv.file_sha(ROOT / "scripts/p106b_hold_resolution_author_output_bindings_v1.py")
views_manifest["rows"].extend(birth_views["rows"])
strict_task_cohorts.add("birth_field_native_counter_v1")
'''
source = once(source, "def digest(payload):", extension + chr(10) + "def digest(payload):")
anchor = '    if status in {"KEEP_SOURCE", "ADOPT_CANDIDATE"}:'
extension = '''    if directory.name == "birth_field_native_counter_v1":
        absolute_paths = {label: dict(pin, path=str(ROOT / pin["path"])) for label, pin in paths.items()}
        reference = explicit_output.declared_txt_basename(row["declared_output_cell"], row["id"], directory,
                                                        absolute_paths, status)
        row["body_references"] = [reference]
        row["body_reference_scope"] = "EXACT_EXPLICIT_OWNED_OUTPUT_OR_ASSIGNED_INPUT_PATH"
'''
source = once(source, anchor, extension + anchor)
source = once(source, "for detail in coverage.values():",
    'inv.require(coverage["birth_field_native_counter_v1"]["expected"] == 753, "all753 assignments must remain visible")' + chr(10) +
    "for detail in coverage.values():")
with (AUDIT / "collect_supplemental_candidates_v49.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
source = (AUDIT / "materialize_reviewed_selection_plan_v25.py").read_text(encoding="utf-8")
source = once(source, '"reviewed_selection_plan_v25.json"', '"reviewed_selection_plan_v26.json"')
source = once(source, '"supplemental_candidates_snapshot_v48.json"', '"supplemental_candidates_snapshot_v49.json"')
source = once(source, '"resume_guard_independent_20261102_v1"]]',
    '"resume_guard_independent_20261102_v1", "birth_field_native_counter_v1"]]')
with (AUDIT / "materialize_reviewed_selection_plan_v26.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
print("NEW753_COHORT_AND_EXACT_OUTPUT_BINDING_PREPARED")
