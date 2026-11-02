"""Add every independently read nominal candidate to the source-pinned collector."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent


def once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new, 1)


source = (AUDIT / 'collect_supplemental_candidates_v53.py').read_text(encoding='utf-8')
source = once(source, '"supplemental_candidates_snapshot_v53.json"', '"supplemental_candidates_snapshot_v54.json"')
source = once(source, 'groups = list(dict.fromkeys(groups))',
    'groups += ["nominal_local_alias_counter_v1"]\ngroups = list(dict.fromkeys(groups))')
source = once(source,
    'if directory.name in {"birth_field_native_counter_v1", "root_join_conflict_counter_v1", "repeat_local_context_counter_v1"}:',
    'if directory.name in {"birth_field_native_counter_v1", "root_join_conflict_counter_v1", "repeat_local_context_counter_v1", "nominal_local_alias_counter_v1"}:')
source = once(source,
    'if directory.name == "repeat_local_context_counter_v1" and status == "REVISE_CANDIDATE":',
    'if directory.name in {"repeat_local_context_counter_v1", "nominal_local_alias_counter_v1"} and status == "REVISE_CANDIDATE":')
extension = '''nominal_path = BASE / "nominal_local_alias_counter_v1/manifest.json"
nominal_manifest = inv.cache.read(nominal_path)
inv.require(len(nominal_manifest["rows"]) == 223, "all223 native nominal assignments are required")
input_pins[str(nominal_path.relative_to(ROOT))] = inv.file_sha(nominal_path)
strict_task_cohorts.add("nominal_local_alias_counter_v1")
for nominal_row in nominal_manifest["rows"]:
    nominal_views = {}
    for label in ["original", "candidate"]:
        pin = nominal_row[label]
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "nominal input bytes changed")
        text = (ROOT / pin["path"]).read_text(encoding="utf-8")
        nominal_views[label] = [dict(source_path=pin["path"],
            sha256=inv.sha(text[offset:offset + 6000]),
            source_characters=[offset, min(offset + 6000, len(text))])
            for offset in range(0, len(text), 6000)]
    views_manifest["rows"].append(dict(id=nominal_row["id"], role=nominal_row["role"], views=nominal_views,
        virtual_windows_of_exact_source=True, separate_window_files_created=False))
for audit_name in ["TYPED_NOMINAL_LOCAL_ALIAS_SCOPE_V1.md", "NOMINAL_LOCAL_ALIAS_COUNTER_FINDINGS_V1.md"]:
    audit_path = AUDIT / audit_name
    input_pins[str(audit_path.relative_to(ROOT))] = inv.file_sha(audit_path)
for guidance_path in [BASE / "root_join_conflict_counter_v1/ROOT_MEDIATION_V6.md",
                      BASE / "nominal_local_alias_counter_v1/ROOT_GRAMMAR_AND_DAMAGE_GUIDANCE_V1.md"]:
    input_pins[str(guidance_path.relative_to(ROOT))] = inv.file_sha(guidance_path)
'''
source = once(source, 'def digest(payload):', extension + '\ndef digest(payload):')
source = once(source, 'for detail in coverage.values():',
    'inv.require(coverage["nominal_local_alias_counter_v1"]["expected"] == 223, "all223 nominal source assignments must remain visible")\nfor detail in coverage.values():')
with (AUDIT / 'collect_supplemental_candidates_v54.py').open('x', encoding='utf-8') as stream:
    stream.write(source)

source = (AUDIT / 'materialize_reviewed_selection_plan_v30.py').read_text(encoding='utf-8')
source = once(source, '"reviewed_selection_plan_v30.json"', '"reviewed_selection_plan_v31.json"')
source = once(source, '"supplemental_candidates_snapshot_v53.json"', '"supplemental_candidates_snapshot_v54.json"')
source = once(source, '"root_join_conflict_counter_v1", "repeat_local_context_counter_v1"]]',
    '"root_join_conflict_counter_v1", "repeat_local_context_counter_v1", "nominal_local_alias_counter_v1"]]')
with (AUDIT / 'materialize_reviewed_selection_plan_v31.py').open('x', encoding='utf-8') as stream:
    stream.write(source)
print('ALL215_PLUS40_PLUS223_COLLECTOR_AND_PLAN_PREPARED_NOT_ADMISSION')
