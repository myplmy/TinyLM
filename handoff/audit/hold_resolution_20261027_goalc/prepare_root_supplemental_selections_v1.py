"""Record explicit root choices after source/body/review and diff adjudication."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT = Path(__file__).resolve().parent
snapshot_path = AUDIT / "supplemental_candidates_snapshot_v7.json"
snapshot = inv.cache.read(snapshot_path)
evidence = AUDIT / "ROOT_SUPPLEMENTAL_ADJUDICATIONS_V1.md"
out = AUDIT / "ROOT_SUPPLEMENTAL_BODY_SELECTIONS_V1.json"
inv.require(not out.exists(), "new root selection receipt required")
choices = {
    233037: "policy_v10_literal_counter_v1", 105801: "policy_v10_literal_counter_v1",
    284636: "policy_v10_literal_counter_v1", 176321: "policy_v10_literal_counter_v1",
    56533: "policy_v13_literal_counter_v1", 200825: "policy_v10_literal_counter_v1",
    302648: "policy_v13_literal_counter_v1", 359683: "policy_v13_literal_counter_v1",
    248793: "policy_v13_literal_counter_v1", 794733: "policy_counter_review_v1",
    733527: "policy_v10_literal_counter_v1", 1062446: "policy_v13_literal_counter_v1",
    188187: "policy_counter_review_v1", 50015: "policy_v11_literal_counter_v1",
    504179: "policy_v11_literal_counter_v1", 936: "policy_v11_literal_counter_v1",
    1175710: "policy_v11_literal_counter_v1", 1080927: "policy_v11_literal_counter_v1",
    1129811: "policy_v11_literal_counter_v1", 155902: "policy_v12_literal_counter_v1",
    211110: "contextual_residual_v11_v1", 233893: "policy_v12_literal_counter_v1",
    236711: "policy_v13_literal_counter_v1", 518256: "contextual_residual_v11_v1",
}
rows = []
for ident, cohort in choices.items():
    key = "expanded_train:" + str(ident)
    matching = [row for row in snapshot["records"] if row["id"] == key and row["cohort"] == cohort]
    inv.require(len(matching) == 1, "explicit root body is ambiguous")
    row = matching[0]
    inv.require(row.get("body") and row["status"] in {"MATERIALIZED_BODY_NOT_ROOT_ADMISSION", "PINNED_BODY_NOT_ROOT_ADMISSION"},
                "explicit selected body was not materialized")
    for pin in [row["original"], dict(path=row["body"], sha256=row["clean_text_sha256"]), row["review"]]:
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "root selection input changed")
    body = ROOT / row["body"]
    decision = "KEEP" if row["original"]["sha256"] == row["clean_text_sha256"] else "EDIT"
    rows.append(dict(id=key, decision=decision, source=row["original"]["path"],
        original_text_sha256=row["original"]["sha256"], body=row["body"],
        clean_text_sha256=row["clean_text_sha256"], selected_cohort=cohort,
        root_approved=True, review_inputs=[row["review"]],
        reason="EXPLICIT_BODY_DIFF_AND_INDEPENDENT_TEXT_REVIEW_ADJUDICATION",
        evidence=dict(path=str(evidence.relative_to(ROOT)), sha256=inv.file_sha(evidence))))
inv.write_json(out, dict(status="ROOT_REVIEWED_EXACT_SUPPLEMENTAL_BODY_SELECTIONS_NOT_CACHE_BUILD",
    rows=rows, pins={str(p.relative_to(ROOT)): inv.file_sha(p) for p in [snapshot_path, Path(__file__)]},
    goal_complete=False, training_authorized=False))
print(json.dumps(dict(rows=len(rows), output=str(out.relative_to(ROOT))), ensure_ascii=False))
