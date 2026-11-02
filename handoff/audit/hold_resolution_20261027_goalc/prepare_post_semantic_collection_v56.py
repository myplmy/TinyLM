"""Collect both complete follow-up purposes with exact output and TASK binding."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / 'collect_supplemental_candidates_v55.py').read_text(encoding='utf-8')


def replace_once(before, after):
    global source
    assert source.count(before) == 1, before
    source = source.replace(before, after, 1)


replace_once('"supplemental_candidates_snapshot_v55.json"', '"supplemental_candidates_snapshot_v56.json"')
replace_once('groups += ["nominal_local_alias_counter_v1"]',
             'groups += ["nominal_local_alias_counter_v1", "post_body_guard_counter_v1", "semantic_field_counter_v1"]')
anchor = '\ndef digest(payload):'
addition = '''
for follow_group, expected_count in [("post_body_guard_counter_v1", 14), ("semantic_field_counter_v1", 12)]:
    follow_path = BASE / follow_group / "manifest.json"
    follow_manifest = inv.cache.read(follow_path)
    inv.require(len(follow_manifest["rows"]) == expected_count, "follow-up exact scope changed")
    input_pins[str(follow_path.relative_to(ROOT))] = inv.file_sha(follow_path)
    strict_task_cohorts.add(follow_group)
    for follow_row in follow_manifest["rows"]:
        follow_views = {}
        for label in ["original", "candidate"]:
            pin = follow_row[label]
            inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "follow-up source bytes changed")
            text = (ROOT / pin["path"]).read_text(encoding="utf-8")
            follow_views[label] = [dict(source_path=pin["path"],
                sha256=inv.sha(text[offset:offset + 6000]),
                source_characters=[offset, min(offset + 6000, len(text))])
                for offset in range(0, len(text), 6000)]
        views_manifest["rows"].append(dict(id=follow_row["id"], role=follow_row["role"], views=follow_views,
            virtual_windows_of_exact_source=True, separate_window_files_created=False))
    for name, expected in follow_manifest["input_pins"].items():
        inv.require(inv.file_sha(ROOT / name) == expected, "follow-up evidence pin changed")
        input_pins[name] = expected
incident_path = BASE / "agents/context_controls/semantic_field_counter_v1/path_error_note_v1.md"
input_pins[str(incident_path.relative_to(ROOT))] = inv.file_sha(incident_path)
'''
replace_once(anchor, '\n' + addition + anchor)
replace_once('"repeat_local_context_counter_v1", "nominal_local_alias_counter_v1"}:\n        absolute_paths',
             '"repeat_local_context_counter_v1", "nominal_local_alias_counter_v1", "post_body_guard_counter_v1", "semantic_field_counter_v1"}:\n        absolute_paths')
with (AUDIT / 'collect_supplemental_candidates_v56.py').open('x', encoding='utf-8') as stream:
    stream.write(source)

plan = (AUDIT / 'materialize_reviewed_selection_plan_v32.py').read_text(encoding='utf-8')
for before, after in [
    ('"reviewed_selection_plan_v32.json"', '"reviewed_selection_plan_v33.json"'),
    ('"supplemental_candidates_snapshot_v55.json"', '"supplemental_candidates_snapshot_v56.json"'),
    ('"nominal_local_alias_counter_v1"]]',
     '"nominal_local_alias_counter_v1", "post_body_guard_counter_v1", "semantic_field_counter_v1"]]'),
]:
    assert plan.count(before) == 1, before
    plan = plan.replace(before, after, 1)
with (AUDIT / 'materialize_reviewed_selection_plan_v33.py').open('x', encoding='utf-8') as stream:
    stream.write(plan)

audit = (AUDIT / 'audit_join_repeat_nominal_bodies_v1.py').read_text(encoding='utf-8')
for before, after in [
    ('supplemental_candidates_snapshot_v55.json', 'supplemental_candidates_snapshot_v56.json'),
    ('JOIN_REPEAT_NOMINAL_BODY_AUDIT_V1.json', 'POST_SEMANTIC_BODY_AUDIT_V1.json'),
    ("{'root_join_conflict_counter_v1':215, 'repeat_local_context_counter_v1':40,\n          'nominal_local_alias_counter_v1':223}",
     "{'post_body_guard_counter_v1':14, 'semantic_field_counter_v1':12}"),
]:
    assert audit.count(before) == 1, before
    audit = audit.replace(before, after, 1)
# Follow-up sidecars use explicit absolute paths as well as hold_ID names.
before = "refs = re.findall(r'(?<![A-Za-z0-9_])(?:hold_[A-Za-z0-9_]+|removal_basis_[A-Za-z0-9_]+)[.]md', row['review_text'])"
after = "refs = re.findall(r'(?<![A-Za-z0-9_])(?:hold_[A-Za-z0-9_]+|removal_basis_[A-Za-z0-9_]+|expanded_train_[0-9]+_(?:hold|original_note)_v[0-9]+)[.]md', row['review_text'])"
assert audit.count(before) == 1
audit = audit.replace(before, after, 1)
with (AUDIT / 'audit_post_semantic_bodies_v1.py').open('x', encoding='utf-8') as stream:
    stream.write(audit)
print('EXACT_POST14_SEMANTIC12_COLLECTION_PREPARED')
