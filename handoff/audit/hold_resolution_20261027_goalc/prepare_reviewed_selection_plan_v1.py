"""Join source-pinned authored proposals without approving unresolved choices.

A singleton body is still a draft. Only an existing exact root decision is
labelled as selected, and no result is a cache-builder admission roster.
Restricted parent bodies are kept as metadata and never reopened by this tool.
"""
from collections import Counter, defaultdict
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = AUDIT / "reviewed_selection_plan_v1.json"
inv.require(not OUT.exists(), "selection plan is write-once")
core_path = AUDIT / "authored_body_integrity_v2.json"
supp_path = AUDIT / "supplemental_candidates_snapshot_v12.json"
root_paths = [AUDIT / name for name in [
    "ROOT_CURATED_OVERRIDES_V1.json", "ROOT_READBACK_BODY_SELECTIONS_V1.json",
    "ROOT_STYLE_BODY_SELECTIONS_V1.json", "ROOT_SUPPLEMENTAL_BODY_SELECTIONS_V1.json"]]
core, supp = inv.cache.read(core_path), inv.cache.read(supp_path)
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:15695",
              "expanded_train:1216576", "expanded_train:1250821"}
clinical_safe_cohorts = {"clinical_source_review_v1", "secondary_body_counter_v1"}
proposals = defaultdict(list)

for row in core["records"]:
    proposals[row["id"]].append(dict(id=row["id"], cohort="CORE2110:" + row["cohort"],
        decision=row["decision"], original=dict(path=row["source"], sha256=row["original_text_sha256"]),
        body=row.get("body"), clean_text_sha256=row.get("clean_text_sha256"), evidence=row["evidence"],
        prior_readback_status=row["status"], prior_post_policy_reasons=row.get("post_body_policy_reasons", [])))
for row in supp["records"]:
    proposals[row["id"]].append(dict(row))

root_decisions = defaultdict(list)
for path in root_paths:
    for row in inv.cache.read(path)["rows"]:
        inv.require(row["root_approved"] is True, "root file contains an unapproved row")
        root_decisions[row["id"]].append(dict(row, exact_decision_source=str(path.relative_to(ROOT))))

records, counts = [], Counter()
checked = {}


def verify_pin(path, expected):
    if path not in checked:
        checked[path] = inv.file_sha(ROOT / path)
    inv.require(checked[path] == expected, "selected or candidate body pin changed: " + path)


for ident, candidates in sorted(proposals.items()):
    source_hashes = {row["original"]["sha256"] for row in candidates}
    inv.require(len(source_hashes) == 1, "one source ID has conflicting original identities: " + ident)
    source_sha = next(iter(source_hashes))
    bodies, decisions, stale_errors = defaultdict(list), [], []
    record = dict(id=ident, original_text_sha256=source_sha,
                  original_paths=sorted({row["original"]["path"] for row in candidates}),
                  root_approved=False, cache_admitted=False)
    for row in candidates:
        proof = dict(cohort=row["cohort"], decision=row["decision"], review=row.get("review"),
                     review_line=row.get("line"), evidence=row.get("evidence"),
                     original=row["original"], compare_source=row.get("compare_source"),
                     candidate_status=row.get("status", row.get("prior_readback_status")),
                     author_output=row.get("author_output"), reason=row.get("reason"))
        if row.get("body") and row.get("clean_text_sha256"):
            body, body_sha = row["body"], row["clean_text_sha256"]
            limited = ident == "expanded_train:1250821" and row["cohort"] in clinical_safe_cohorts
            inspectable = ident not in restricted or limited
            if inspectable:
                verify_pin(body, body_sha)
                if limited:
                    inv.require(row.get("compare_source") is not None, "clinical safe body needs a source view")
                    verify_pin(row["compare_source"]["path"], row["compare_source"]["sha256"])
            proof.update(body=body, clean_text_sha256=body_sha,
                         restricted_parent_body_metadata_only=not inspectable)
            bodies[body_sha].append(proof)
        elif row.get("status") == "MECHANICAL_REJECTION_NOT_APPLIED":
            stale_errors.append(dict(proof, error=row["error"]))
        else:
            decisions.append(proof)
    exact = root_decisions.get(ident, [])
    for selected in exact:
        inv.require(selected["original_text_sha256"] == source_sha, "root original identity differs")
    identities = {(row["decision"], row.get("clean_text_sha256")) for row in exact}
    inv.require(len(identities) <= 1, "conflicting exact root decisions require an explicit supersession")
    if exact:
        selected = exact[0]
        if selected.get("body"):
            inv.require(ident not in restricted, "restricted root selection needs a separately reviewed safe path")
            verify_pin(selected["body"], selected["clean_text_sha256"])
        record.update(status="EXACT_ROOT_SELECTION_NOT_CACHE_ADMISSION", selected=selected,
                      exact_root_evidence=[row["exact_decision_source"] for row in exact], root_approved=True)
    elif ident in restricted:
        record["status"] = "RESTRICTED_PARENT_METADATA_ONLY_REQUIRES_EXACT_ROOT_DISPOSITION"
    elif len(bodies) > 1:
        record["status"] = "MULTIPLE_AUTHORED_BODIES_REQUIRE_EXPLICIT_ROOT_SELECTION"
    elif bodies and decisions:
        record["status"] = "BODY_AND_PRIOR_EXCLUSION_OR_HOLD_REQUIRE_ROOT_ADJUDICATION"
    elif len(bodies) == 1:
        record["status"] = "UNIQUE_AUTHORED_BODY_NOT_ROOT_OR_CACHE_APPROVAL"
    elif decisions:
        record["status"] = "TEXT_ONLY_EXCLUSION_OR_HOLD_NOT_ROOT_OR_CACHE_APPROVAL"
    else:
        record["status"] = "NO_MATERIALIZED_BODY_REQUIRES_REPAIR"
    record.update(body_options=[dict(clean_text_sha256=key, proposals=values) for key, values in sorted(bodies.items())],
                  text_only_decisions=decisions, mechanical_history=stale_errors)
    counts.update([record["status"]])
    records.append(record)

inv.require(set(root_decisions) <= set(proposals), "root decision has no source-pinned proposal")
paths = [core_path, supp_path, *root_paths, Path(__file__)]
result = dict(status="SOURCE_PINNED_AUTHORED_SELECTION_PLAN_NOT_ADMISSION", records=records, counts=dict(counts),
              source_ids=len(records), proposal_records=sum(map(len, proposals.values())),
              exact_root_selected_sources=sum(row["root_approved"] for row in records),
              pinned_body_files_checked=len(checked), restricted_parent_content_opened=False,
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
              goal_complete=False, training_authorized=False, cache_admitted=0)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "selection plan needs ordered shards")
inv.write_json(OUT, result)
print(json.dumps({key: result[key] for key in ["status", "source_ids", "proposal_records", "counts",
                                             "exact_root_selected_sources", "pinned_body_files_checked"]}, ensure_ascii=False))
