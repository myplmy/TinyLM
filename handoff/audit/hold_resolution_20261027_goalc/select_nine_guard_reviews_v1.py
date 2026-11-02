"""Pin the nine root-mediated independent reviews without approving a cache."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

snapshot_path = AUDIT / "supplemental_candidates_snapshot_v48.json"
plan_path = AUDIT / "reviewed_selection_plan_v25.json"
prior_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V9.json"
rationale = AUDIT / "ROOT_NINE_GUARD_RATIONALE_V1.md"
code_proof = AUDIT / "GUARD_RESTORATION_CODE_PROOF_V1.json"
output = AUDIT / "ROOT_NINE_GUARD_SELECTIONS_V1.json"
inv.require(not output.exists(), "new immutable root mediation required")
snapshot, plan, prior = map(inv.cache.read, [snapshot_path, plan_path, prior_path])
ids = {"expanded_train:" + str(n) for n in [8121,255342,1239923,1081376,1276826,689736,1254536,852538,71604]}
independent = [row for row in snapshot["records"] if row["cohort"] == "resume_guard_independent_20261102_v1"]
inv.require(len(independent) == 9 and {row["id"] for row in independent} == ids, "nine exact independent rows differ")
prior_map = {row["id"]: row for row in prior["rows"]}
plan_map = {row["id"]: row for row in plan["records"]}
records = []
for row in independent:
    key, source_hash = row["id"], row["original"]["sha256"]
    inv.require(row["decision"] in {"ADOPT_CANDIDATE", "EDIT_TEXT"} and row.get("body"), "incomplete independent source")
    inv.require(plan_map[key]["original_text_sha256"] == source_hash, "plan original differs")
    for pin in [row["original"], row["review"]]:
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "source/review bytes differ")
    inv.require(inv.file_sha(ROOT / row["body"]) == row["clean_text_sha256"], "root selected body changed")
    if key in prior_map:
        inv.require(prior_map[key]["original_text_sha256"] == source_hash, "earlier root source differs")
    alternatives = [value for value in snapshot["records"] if value["id"] == key and value["cohort"] in {
        "resume_guard_counter_20261102_v1", "resume_guard_independent_20261102_v1"}]
    inv.require(len(alternatives) == 2 and all(value.get("body") and value["decision"] != "NEEDS_ROOT"
                and value["original"]["sha256"] == source_hash for value in alternatives), "both exact review purposes required")
    selected = dict(row, decision="KEEP" if row["clean_text_sha256"] == source_hash else "EDIT",
                    original_text_sha256=source_hash, root_approved=True)
    records.append(dict(id=key, original_text_sha256=source_hash, original_paths=plan_map[key]["original_paths"],
        selected=selected, root_approved=True, status="EXACT_GUARD_MEDIATION_PENDING_CACHE",
        selection_rule="EXACT_ID_SOURCE_BODY_REVIEW_ROOT_MEDIATION_NOT_VERSION_RANKING",
        prior_exact_selection=prior_map.get(key), new_supporting_proposals=alternatives,
        rationale=dict(path=str(rationale.relative_to(ROOT)), sha256=inv.file_sha(rationale)),
        code_source_proof=dict(path=str(code_proof.relative_to(ROOT)), sha256=inv.file_sha(code_proof)),
        cache_admitted=False, goal_complete=False, training_authorized=False))
inv.write_json(output, dict(status="EXACT_NINE_GUARD_ROOT_SELECTIONS_NOT_CACHE_ADMISSION", rows=records,
    source_ids=9, selected_sources=9, unresolved_sources=0,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [snapshot_path,plan_path,prior_path,rationale,code_proof,Path(__file__)]},
    cache_admitted=0, goal_complete=False, training_authorized=False))
print(json.dumps(dict(selected_sources=9, revised_after_independent_reading=2, current_candidates_confirmed=7)))
