"""Version the existing collector with explicit missing-review/window guards."""
from pathlib import Path
from textwrap import dedent

BASE = Path(__file__).resolve().parent
source = (BASE / "collect_supplemental_candidates_v28.py").read_text(encoding="utf-8")


def replace_once(before, after):
    global source
    assert source.count(before) == 1, before[:100]
    source = source.replace(before, after)


replace_once('"supplemental_candidates_snapshot_v28.json"', '"supplemental_candidates_snapshot_v29.json"')
replace_once('"legacy_incident_counter_v1", "policy_v20_literal_counter_v1"]',
             '"legacy_incident_counter_v1", "policy_v20_literal_counter_v1", "root_selected_signal_counter_v2", "policy_v21_literal_counter_v1"]')
replace_once('from scripts import p106b_hold_resolution_recipe_frame_v3 as frame',
             'from scripts import p106b_hold_resolution_recipe_frame_v3 as frame\nfrom scripts import p106b_hold_resolution_review_safeguards_v1 as safeguards')
replace_once('\ndef digest(payload):', dedent('''
views_path = BASE / "root_selected_signal_counter_v2/reading_views_manifest_v1.json"
views_manifest = inv.cache.read(views_path)
inv.require(inv.file_sha(ROOT / views_manifest["source_manifest"]["path"]) == views_manifest["source_manifest"]["sha256"],
            "reading views refer to another assignment")
input_pins[str(views_path.relative_to(ROOT))] = inv.file_sha(views_path)
input_pins["scripts/p106b_hold_resolution_review_safeguards_v1.py"] = inv.file_sha(ROOT / "scripts/p106b_hold_resolution_review_safeguards_v1.py")
unparsed_review_history = []


def digest(payload):'''))
replace_once('''                               error="INVALID_REVIEW_SYNTAX_NOT_EVIDENCE", detail=str(exc)))
            continue
        for entry in entries:''', '''                               error="INVALID_REVIEW_SYNTAX_NOT_EVIDENCE", detail=str(exc)))
            entries = []
        parsed_ids = {ident(entry["cells"][0]) for entry in entries}
        unsupported = safeguards.unparsed_declared_review_ids(payload, parsed_ids, expected)
        for missing_id in sorted(unsupported):
            historical = dict(id=missing_id, review=pin, group=directory.name, role=directory.parent.name,
                              error="EXPLICIT_NEW_REVIEW_NOT_PARSED_OLDER_BODY_MUST_NOT_FALL_BACK")
            unparsed_review_history.append(historical)
            found[missing_id] = dict(id=missing_id, decision="NEEDS_ROOT", original_status="UNPARSED_EXPLICIT_REVIEW",
                read_scope="", reason=historical["error"], review=pin, line=1, review_line_end=len(payload.decode("utf-8").splitlines()),
                review_source_format="UNPARSED_DECLARATION_IS_MISSING_EVIDENCE_ONLY", review_text="",
                body_references=[], declared_output_cell="", body_reference_scope="NO_PARSED_BODY_REFERENCE",
                author_precedence=[*review_rank(review), 0], root_approved=False)
        for entry in entries:''')
replace_once('''    body, key = save_content(rendered_dir, payload, ".txt")''', '''    collisions = safeguards.partial_reading_view_collisions(row["id"], digest(payload), views_manifest)
    inv.require(not collisions, "AUTHOR_BODY_MATCHES_A_PARTIAL_READING_VIEW_NOT_A_FULL_CANDIDATE")
    body, key = save_content(rendered_dir, payload, ".txt")''')
replace_once('''              coverage=coverage, retracted_history=retracted_history,''',
             '''              coverage=coverage, retracted_history=retracted_history,
              unparsed_review_history=unparsed_review_history,
              active_unparsed_review_rows=[dict(id=row["id"], cohort=row["cohort"], review=row["review"])
                    for row in records if row.get("original_status") == "UNPARSED_EXPLICIT_REVIEW"],''')
with (BASE / "collect_supplemental_candidates_v29.py").open("x", encoding="utf-8") as stream:
    stream.write(source)

plan = (BASE / "prepare_reviewed_selection_plan_v8.py").read_text(encoding="utf-8")
assert plan.count('"reviewed_selection_plan_v8.json"') == 1
assert plan.count('"supplemental_candidates_snapshot_v28.json"') == 1
plan = plan.replace('"reviewed_selection_plan_v8.json"', '"reviewed_selection_plan_v9.json"')
plan = plan.replace('"supplemental_candidates_snapshot_v28.json"', '"supplemental_candidates_snapshot_v29.json"')
needle = '''            stale_errors.append(dict(proof, error=row["error"]))'''
assert plan.count(needle) == 1
plan = plan.replace(needle, needle + '''
            decisions.append(dict(proof, decision="NEEDS_ROOT", reason="LATEST_AUTHOR_MECHANICAL_FAILURE_REQUIRES_REPAIR: " + row["error"]))''')
with (BASE / "prepare_reviewed_selection_plan_v9.py").open("x", encoding="utf-8") as stream:
    stream.write(plan)
print("new collector29/plan9 written; neither executed by this preparer")
