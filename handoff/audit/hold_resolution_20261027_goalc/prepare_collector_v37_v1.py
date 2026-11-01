"""Preserve failed36 and add the exact declared structural TASK layout."""
from pathlib import Path
import hashlib
import json

AUDIT = Path(__file__).resolve().parent
source = (AUDIT / "collect_supplemental_candidates_v36.py").read_text(encoding="utf-8")
out = AUDIT / "COLLECTOR_V36_TASK_LAYOUT_FAILURE_V1.json"
receipt = dict(actual_exit_code=1, completion_snapshot_written=False,
    source_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest().upper(),
    failed_log_sha256=hashlib.sha256((AUDIT / "collect_supplemental_candidates_v36.log").read_bytes()).hexdigest().upper(),
    cause="The generated structural TASK has a bare exact ID immediately after its TASK header; old v2 parser only accepts heading IDs.",
    dependent_failed_without_source_inputs=["prepare_reviewed_selection_plan_v13", "prepare_authored_root_selection_v9_preview"],
    old_sources_and_logs_preserved=True, old_task_binding_checks_retained=True, cache_admitted=0)
with out.open("x", encoding="utf-8") as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
source = source.replace("supplemental_candidates_snapshot_v36.json", "supplemental_candidates_snapshot_v37.json")
source = source.replace("p106b_hold_resolution_review_safeguards_v2", "p106b_hold_resolution_review_safeguards_v3")
with (AUDIT / "collect_supplemental_candidates_v37.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
source = (AUDIT / "prepare_reviewed_selection_plan_v13.py").read_text(encoding="utf-8")
source = source.replace("reviewed_selection_plan_v13.json", "reviewed_selection_plan_v14.json")
source = source.replace("supplemental_candidates_snapshot_v36.json", "supplemental_candidates_snapshot_v37.json")
with (AUDIT / "prepare_reviewed_selection_plan_v14.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
source = (AUDIT / "prepare_authored_root_selection_v9_preview.py").read_text(encoding="utf-8")
source = source.replace("reviewed_selection_plan_v13.json", "reviewed_selection_plan_v14.json")
source = source.replace("ROOT_AUTHORED_SELECTIONS_V9_PREVIEW.json", "ROOT_AUTHORED_SELECTIONS_V9_PREVIEW2.json")
with (AUDIT / "prepare_authored_root_selection_v9_preview2.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
print("Prepared new collector37/plan14/preview2; failed36 and downstream failure logs retained.")
