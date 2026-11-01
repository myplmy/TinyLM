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
OUT = AUDIT / "reviewed_selection_plan_v13.json"
inv.require(not OUT.exists(), "selection plan is write-once")
core_path = AUDIT / "authored_body_integrity_v2.json"
supp_path = AUDIT / "supplemental_candidates_snapshot_v36.json"
root_paths = [AUDIT / name for name in [
    "ROOT_CURATED_OVERRIDES_V1.json", "ROOT_READBACK_BODY_SELECTIONS_V1.json",
    "ROOT_STYLE_BODY_SELECTIONS_V1.json", "ROOT_SUPPLEMENTAL_BODY_SELECTIONS_V1.json",
    "ROOT_NEW_READBACK_BODY_SELECTIONS_V2.json", "ROOT_RESTRICTED_SOURCE_EXCLUSIONS_V1.json",
    "ROOT_POSTSIGNAL_BODY_SELECTIONS_V1.json"]]
core, supp = inv.cache.read(core_path), inv.cache.read(supp_path)
restricted = {"expanded_train:14760", "expanded_train:756966", "expanded_train:15695",
              "expanded_train:1216576", "expanded_train:1250821", "expanded_train:20624", "expanded_train:6030"}
clinical_safe_cohorts = {"clinical_source_review_v1", "secondary_body_counter_v1", "limited_biology_views_v2"}
proposals = defaultdict(list)

for row in core["records"]:
    proposals[row["id"]].append(dict(id=row["id"], cohort="CORE2110:" + row["cohort"],
        decision=row["decision"], original=dict(path=row["source"], sha256=row["original_text_sha256"]),
        body=row.get("body"), clean_text_sha256=row.get("clean_text_sha256"), evidence=row["evidence"],
        prior_readback_status=row["status"], prior_post_policy_reasons=row.get("post_body_policy_reasons", [])))
for row in supp["records"]:
    proposals[row["id"]].append(dict(row))

assigned_paths = [BASE / group / "manifest.json" for group in [
    "root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1", "root_selected_literal_counter_v3", "policy_v22_literal_counter_v1", "policy_v23_literal_counter_v1", "policy_v23_structural_counter_v1", "root_selected_literal_counter_v4"]]
saved_pairs = {(row["cohort"], row["id"]) for row in supp["records"]}
assigned_missing_review_placeholders = []
for assigned_path in assigned_paths:
    assigned_manifest = inv.cache.read(assigned_path)
    for assigned in assigned_manifest["rows"]:
        group = assigned_path.parent.name
        if (group, assigned["id"]) in saved_pairs:
            continue
        assigned_source = dict(assigned, **assigned.get("paths", {}))["original"]
        placeholder = dict(id=assigned["id"], cohort=group, decision="NEEDS_ROOT", original=assigned_source,
            status="ASSIGNED_REVIEW_NOT_SAVED_REQUIRES_REPAIR", body=None, clean_text_sha256=None,
            reason="배정된 정확 원문의 저장 검토행이 없어 옛 후보로 우회할 수 없다.",
            root_approved=False, cache_admitted=False)
        proposals[assigned["id"]].append(placeholder)
        assigned_missing_review_placeholders.append(dict(id=assigned["id"], cohort=group,
            source=assigned_source, assigned_manifest=str(assigned_path.relative_to(ROOT))))

root_decisions = defaultdict(list)
superseded_roots = defaultdict(list)
for path in root_paths:
    for row in inv.cache.read(path)["rows"]:
        inv.require(row["root_approved"] is True, "root file contains an unapproved row")
        previous_choices = root_decisions[row["id"]]
        if previous_choices and row.get("supersedes"):
            for earlier in previous_choices:
                matches = [item for item in row["supersedes"] if
                           item["selection_file"] == earlier["exact_decision_source"]
                           and item["selection_file_sha256"] == inv.file_sha(ROOT / earlier["exact_decision_source"])
                           and item["id"] == row["id"]
                           and item["clean_text_sha256"] == earlier.get("clean_text_sha256")
                           and item["decision"] == earlier["decision"]]
                inv.require(len(matches) == 1, "root supersession does not identify its exact predecessor")
            superseded_roots[row["id"]].extend(previous_choices)
            root_decisions[row["id"]] = []
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
            limited = (ident in {"expanded_train:1250821", "expanded_train:15695", "expanded_train:20624"}
                       and row["cohort"] in clinical_safe_cohorts and row.get("compare_source") is not None)
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
            decisions.append(dict(proof, decision="NEEDS_ROOT", reason="LATEST_AUTHOR_MECHANICAL_FAILURE_REQUIRES_REPAIR: " + row["error"]))
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
            if ident in restricted:
                inv.require(ident == "expanded_train:1250821" and selected.get("compare_source"),
                            "restricted root selection needs a separately reviewed safe path")
                verify_pin(selected["compare_source"]["path"], selected["compare_source"]["sha256"])
            verify_pin(selected["body"], selected["clean_text_sha256"])
        record.update(status="EXACT_ROOT_SELECTION_NOT_CACHE_ADMISSION", selected=selected,
                      exact_root_evidence=[row["exact_decision_source"] for row in exact], root_approved=True,
                      superseded_exact_root_choices=superseded_roots.get(ident, []))
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
paths = [core_path, supp_path, *root_paths, *assigned_paths, Path(__file__)]
result = dict(status="SOURCE_PINNED_AUTHORED_SELECTION_PLAN_NOT_ADMISSION", records=records, counts=dict(counts),
              source_ids=len(records), proposal_records=sum(map(len, proposals.values())),
              assigned_missing_review_placeholders=assigned_missing_review_placeholders,
              assigned_missing_review_count=len(assigned_missing_review_placeholders),
              exact_root_selected_sources=sum(row["root_approved"] for row in records),
              pinned_body_files_checked=len(checked), restricted_parent_content_opened=False,
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
              goal_complete=False, training_authorized=False, cache_admitted=0)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "selection plan needs ordered shards")
inv.write_json(OUT, result)
print(json.dumps({key: result[key] for key in ["status", "source_ids", "proposal_records", "counts",
                                             "exact_root_selected_sources", "pinned_body_files_checked"]}, ensure_ascii=False))
