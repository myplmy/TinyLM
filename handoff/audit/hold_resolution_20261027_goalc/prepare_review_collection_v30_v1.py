"""Bind all new review rows to TASK IDs and include the disjoint next cohort."""
from pathlib import Path

BASE = Path(__file__).resolve().parent
source = (BASE / "collect_supplemental_candidates_v29.py").read_text(encoding="utf-8")


def change(before, after):
    global source
    assert source.count(before) == 1, before[:100]
    source = source.replace(before, after)


change('"supplemental_candidates_snapshot_v29.json"', '"supplemental_candidates_snapshot_v30.json"')
change('"root_selected_signal_counter_v2", "policy_v21_literal_counter_v1"]',
       '"root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1"]')
change('from scripts import p106b_hold_resolution_review_safeguards_v1 as safeguards',
       'from scripts import p106b_hold_resolution_review_safeguards_v2 as safeguards')
change('''unparsed_review_history = []''', '''extra_views_path = BASE / "remaining_unreviewed_context_v20_v1/reading_views_manifest_v1.json"
extra_views = inv.cache.read(extra_views_path)
inv.require(inv.file_sha(ROOT / extra_views["source_manifest"]["path"]) == extra_views["source_manifest"]["sha256"],
            "new reading views refer to another assignment")
input_pins[str(extra_views_path.relative_to(ROOT))] = inv.file_sha(extra_views_path)
input_pins["scripts/p106b_hold_resolution_review_safeguards_v2.py"] = inv.file_sha(ROOT / "scripts/p106b_hold_resolution_review_safeguards_v2.py")
views_manifest = dict(rows=views_manifest["rows"] + extra_views["rows"])
unparsed_review_history, invalid_task_rows = [], []
strict_task_cohorts = {"root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1"}''')
change('''            withdrawn = [row for row in retractions if row["id"] == key_id''', '''            if directory.name in strict_task_cohorts:
                batch = review_rank(review)[0]
                task_path = directory / ("TASK_" + str(batch).zfill(3) + ".md")
                inv.require(task_path.is_file(), "new explicit review has no assigned TASK")
                input_pins[str(task_path.relative_to(ROOT))] = inv.file_sha(task_path)
                if not safeguards.review_row_matches_task(key_id, task_path.read_text(encoding="utf-8")):
                    invalid_task_rows.append(dict(id=key_id, review=pin, line=number, review_text=line,
                        task=str(task_path.relative_to(ROOT)), error="REVIEW_ROW_IS_NOT_IN_THIS_TASK_SOURCE_LIST",
                        invalid_as_review_evidence=True))
                    continue
            withdrawn = [row for row in retractions if row["id"] == key_id''')
change('''              unparsed_review_history=unparsed_review_history,''', '''              unparsed_review_history=unparsed_review_history,
              invalid_task_rows=invalid_task_rows, invalid_task_rows_skipped=len(invalid_task_rows),''')
with (BASE / "collect_supplemental_candidates_v30.py").open("x", encoding="utf-8") as out:
    out.write(source)
print("collector30 prepared; old snapshots unchanged and execution separate")
