"""Collect exact conflict and independently read repeat cohorts without admission."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent


def once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)


source = (AUDIT / "collect_supplemental_candidates_v52.py").read_text(encoding="utf-8")
source = once(source, '"supplemental_candidates_snapshot_v52.json"', '"supplemental_candidates_snapshot_v53.json"')
source = once(source, "groups = list(dict.fromkeys(groups))",
    'groups += ["repeat_local_context_counter_v1"]\ngroups = list(dict.fromkeys(groups))')
source = once(source,
    'if directory.name in {"birth_field_native_counter_v1", "root_join_conflict_counter_v1"}:',
    'if directory.name in {"birth_field_native_counter_v1", "root_join_conflict_counter_v1", "repeat_local_context_counter_v1"}:')
source = once(source, '            columns = {label: cells[index]',
    '            if directory.name == "repeat_local_context_counter_v1" and status == "REVISE_CANDIDATE":\n'
    '                status = "EDIT_TEXT"\n'
    '            columns = {label: cells[index]')
extension = '''repeat_path = BASE / "repeat_local_context_counter_v1/manifest.json"
repeat_manifest = inv.cache.read(repeat_path)
inv.require(len(repeat_manifest["rows"]) == 40, "all40 independent repeat assignments are required")
input_pins[str(repeat_path.relative_to(ROOT))] = inv.file_sha(repeat_path)
strict_task_cohorts.add("repeat_local_context_counter_v1")
for repeat_row in repeat_manifest["rows"]:
    repeat_views = {}
    for label in ["original", "candidate"]:
        pin = repeat_row[label]
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "repeat input bytes changed")
        text = (ROOT / pin["path"]).read_text(encoding="utf-8")
        repeat_views[label] = [dict(source_path=pin["path"],
            sha256=inv.sha(text[offset:offset + 6000]),
            source_characters=[offset, min(offset + 6000, len(text))])
            for offset in range(0, len(text), 6000)]
    views_manifest["rows"].append(dict(id=repeat_row["id"], role=repeat_row["role"], views=repeat_views,
        virtual_windows_of_exact_source=True, separate_window_files_created=False))
for guidance_name in ["ADJUDICATION_BOUNDARIES_V2.md", "ROOT_DECISION_PROTOCOL_V3.md",
                      "EVIDENCE_EXPLICIT_CODEPOINT_IDENTITIES_V1.md", "ROOT_MEDIATION_V4.md", "ROOT_MEDIATION_V5.md"]:
    guidance_path = BASE / "root_join_conflict_counter_v1" / guidance_name
    inv.require(guidance_path.is_file(), "review guidance must be preserved")
    input_pins[str(guidance_path.relative_to(ROOT))] = inv.file_sha(guidance_path)
'''
source = once(source, "def digest(payload):", extension + "\ndef digest(payload):")
source = once(source, "for detail in coverage.values():",
    'inv.require(coverage["repeat_local_context_counter_v1"]["expected"] == 40, "all40 independent assignments must remain visible")\nfor detail in coverage.values():')
# Keep the full historical error list in the JSON, but bound terminal output.
source = once(source, 'counts=result["counts"], errors=errors,',
    'counts=result["counts"], error_count=len(errors), errors_by_message=dict(Counter(row["error"] for row in errors)),')
source = once(source, 'conflicts=[row["id"] for row in conflicts], coverage=coverage,',
    'conflict_count=len(conflicts), coverage=coverage,')
with (AUDIT / "collect_supplemental_candidates_v53.py").open("x", encoding="utf-8") as stream:
    stream.write(source)

source = (AUDIT / "materialize_reviewed_selection_plan_v29.py").read_text(encoding="utf-8")
source = once(source, '"reviewed_selection_plan_v29.json"', '"reviewed_selection_plan_v30.json"')
source = once(source, '"supplemental_candidates_snapshot_v52.json"', '"supplemental_candidates_snapshot_v53.json"')
source = once(source, '"birth_field_native_counter_v1", "root_join_conflict_counter_v1"]]',
    '"birth_field_native_counter_v1", "root_join_conflict_counter_v1", "repeat_local_context_counter_v1"]]')
with (AUDIT / "materialize_reviewed_selection_plan_v30.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
print("EXACT215_PLUS40_COLLECTION_AND_SELECTION_PLAN_PREPARED_NOT_ADMISSION")
