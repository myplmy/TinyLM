"""Select saved source-pinned author bodies under the explicit root contract.

This is an intended body selection, never a cache admission roster. Higher
priority unresolved decisions cannot silently fall back to an older body.
"""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT = Path(__file__).resolve().parent
OUT = AUDIT / "ROOT_AUTHORED_SELECTIONS_V8_PREVIEW.json"
inv.require(not OUT.exists(), "root body selection is write-once")
plan_path = AUDIT / "reviewed_selection_plan_v11.json"
contract_path = AUDIT / "ROOT_AUTHORED_SELECTION_CONTRACT_V5.md"
plan = inv.cache.read(plan_path)
core_path = AUDIT / "authored_body_integrity_v2.json"
curated_path = AUDIT / "authored_candidates_snapshot_v5.json"
core = inv.cache.read(core_path)
inv.require(core["pins"][str(curated_path.relative_to(ROOT))] == inv.file_sha(curated_path), "curated source snapshot changed")
curated = {row["id"]: row for row in inv.cache.read(curated_path)["rows"]}
order = ["policy_v22_literal_counter_v1", "root_selected_literal_counter_v3", "remaining_unreviewed_context_v20_v1", "root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "policy_v20_literal_counter_v1", "legacy_incident_counter_v1", "remaining_candidate_context_v19_v1", "repeat_context_counter_v1", "policy_v18_literal_counter_v1",
         "remaining_candidate_context_v17_v1", "root_selected_signal_counter_v1", "retracted_review_counter_v1",
         "root_mediation_context_v1", "authored_literal_counter_v3", "limited_biology_views_v2", "policy_v17_literal_counter_v2",
         "policy_v17_literal_counter_v1", "remaining_candidate_context_v16_v1", "automatic_partial_counter_v1",
         "exclusion_second_review_v1", "authored_postsignal_review_v1", "materialized_text_repairs_v2",
         "policy_v16_literal_counter_v2", "policy_v16_literal_counter_v1", "policy_v15_literal_counter_v1",
         "secondary_body_counter_v1", "policy_v14_literal_counter_v1", "policy_v13_literal_counter_v1",
         "policy_v12_literal_counter_v1", "policy_v11_literal_counter_v1", "policy_v10_literal_counter_v1",
         "formal_source_second_review_v1", "style_value_counter_v1", "policy_counter_review_v1",
         "remaining_context_v14_v1", "remaining_structure_context_v1", "contextual_residual_v11_v1",
         "CORE2110:CURATED340", "CORE2110:LEGACY1770"]
ranks = {name: index for index, name in enumerate(order)}
specific = {"expanded_train:290980": "policy_v17_literal_counter_v1",
            "expanded_train:936140": "policy_v14_literal_counter_v1",
            "expanded_train:641587": "retracted_review_counter_v1"}
required_paths = [inv.BASE / group / "manifest.json" for group in ["root_selected_signal_counter_v2", "policy_v21_literal_counter_v1", "remaining_unreviewed_context_v20_v1", "root_selected_literal_counter_v3", "policy_v22_literal_counter_v1"]]
required = {path.parent.name: {row["id"] for row in inv.cache.read(path)["rows"]} for path in required_paths}
rows, counts, pending = [], Counter(), []
for source in plan["records"]:
    ident, key = source["id"], source["original_text_sha256"]
    base = dict(id=ident, original_text_sha256=key, original_paths=source["original_paths"],
                cache_admitted=False, goal_complete=False, training_authorized=False)
    fresh_choices = [dict(proposal) for option in source["body_options"] for proposal in option["proposals"]]
    fresh_choices += [dict(proposal) for proposal in source["text_only_decisions"]]
    needed = [group for group, ids in required.items() if ident in ids]
    groups_missing = [group for group in needed if not any(choice["cohort"] == group for choice in fresh_choices)]
    fresh = [choice for choice in fresh_choices if choice["cohort"] in needed]
    unresolved_fresh = any(choice["decision"] == "NEEDS_ROOT" for choice in fresh)
    fresh_identities = {(choice["decision"] in {"EXCLUDE"}, choice.get("clean_text_sha256")) for choice in fresh}
    if groups_missing or unresolved_fresh or len(fresh_identities) > 1:
        pending.append(dict(base, status="NEW_ASSIGNED_REVIEW_MISSING_FAILED_OR_CONFLICTING_REQUIRES_ROOT",
                            missing_cohorts=groups_missing, new_proposals=fresh))
        counts.update(["UNRESOLVED_ROOT_ADJUDICATION"])
        continue
    if source["root_approved"] and fresh:
        chosen_root = source["selected"]
        root_identity = (chosen_root["decision"] == "EXCLUDE", chosen_root.get("clean_text_sha256"))
        if fresh_identities != {root_identity}:
            pending.append(dict(base, status="NEW_REVIEW_DIFFERS_FROM_EXACT_ROOT_REQUIRES_EXPLICIT_SUPERSESSION",
                                existing_exact_root=chosen_root, new_proposals=fresh))
            counts.update(["UNRESOLVED_ROOT_ADJUDICATION"])
            continue
    if source["root_approved"]:
        chosen = dict(source["selected"])
        rows.append(dict(base, status="EXISTING_EXACT_ROOT_BODY_PENDING_CACHE_VERIFICATION", selected=chosen,
                         root_approved=True, selection_rule="EXISTING_EXACT_ROOT_DECISIONS",
                         exact_root_evidence=source["exact_root_evidence"]))
        counts.update(["EXISTING_EXACT_ROOT_SELECTION"])
        continue
    choices = [dict(proposal) for option in source["body_options"] for proposal in option["proposals"]]
    choices += [dict(proposal) for proposal in source["text_only_decisions"]]
    if not choices:
        pending.append(dict(base, status="NO_ACTUAL_SAVED_BODY_REQUIRES_REPAIR",
                            historical_mechanical_failures_preserved=source["mechanical_history"]))
        counts.update(["UNRESOLVED_ROOT_ADJUDICATION"])
        continue
    inv.require(all(choice["cohort"] in ranks for choice in choices), "source lacks a contracted author decision")
    explicit = specific.get(ident) if not needed else None
    if explicit:
        eligible = [choice for choice in choices if choice["cohort"] == explicit]
        inv.require(eligible, "explicit source cohort missing")
    else:
        highest = min(ranks[choice["cohort"]] for choice in choices)
        eligible = [choice for choice in choices if ranks[choice["cohort"]] == highest]
    identities = {(choice["decision"], choice.get("clean_text_sha256")) for choice in eligible}
    if len(identities) != 1:
        pending.append(dict(base, status="SAME_PURPOSE_AUTHOR_CONFLICT_REQUIRES_ROOT", proposals=eligible))
        counts.update(["UNRESOLVED_ROOT_ADJUDICATION"])
        continue
    chosen = eligible[0]
    if chosen["decision"] == "NEEDS_ROOT":
        pending.append(dict(base, status="EXPLICIT_HIGHER_PURPOSE_REVIEW_STILL_NEEDS_ROOT", selected=chosen,
                            alternatives_not_silently_admitted=len(choices) - len(eligible)))
        counts.update(["UNRESOLVED_ROOT_ADJUDICATION"])
        continue
    if chosen.get("body"):
        body = ROOT / chosen["body"]
        inv.require(inv.file_sha(body) == chosen["clean_text_sha256"], "chosen saved body changed")
        decision = "KEEP" if chosen["clean_text_sha256"] == key else "EDIT"
    else:
        inv.require(chosen["decision"] == "EXCLUDE", "author decision has no actual body or explicit exclusion")
        decision = "EXCLUDE"
    review = chosen.get("review")
    evidence = chosen.get("evidence")
    if review:
        inv.require(inv.file_sha(ROOT / review["path"]) == review["sha256"], "selected explicit author review changed")
    else:
        if evidence and evidence.get("review") and not evidence.get("review_sha256"):
            original_record = curated[ident]
            inv.require(original_record["original_text_sha256"] == key and original_record["review"] == evidence["review"],
                        "curated review recovery is not linked to this exact source")
            expected_body_sha = original_record.get("clean_text_sha256") or original_record["original_text_sha256"]
            inv.require(decision == "EXCLUDE" or expected_body_sha == chosen["clean_text_sha256"], "curated recovery body differs")
            evidence = dict(evidence, review_sha256=original_record["review_sha256"],
                            review_line=original_record["review_line"],
                            recovered_from_curated_snapshot=str(curated_path.relative_to(ROOT)),
                            recovered_snapshot_sha256=inv.file_sha(curated_path))
            chosen["evidence"] = evidence
        inv.require(evidence and evidence.get("review") and evidence.get("review_sha256"), "core selection lacks saved review evidence")
        inv.require(inv.file_sha(ROOT / evidence["review"]) == evidence["review_sha256"], "selected original author evidence changed")
    chosen = dict(chosen, decision=decision, original_text_sha256=key, root_approved=True)
    rows.append(dict(base, status="ROOT_INTENDED_AUTHORED_BODY_PENDING_POST_READBACK_AND_CACHE", selected=chosen,
                     root_approved=True, selection_rule="EXPLICIT_SOURCE_COHORT" if explicit else "CONTRACTED_REVIEW_PURPOSE",
                     higher_purpose=chosen["cohort"], alternatives_preserved=len(choices) - len(eligible),
                     historical_mechanical_failures_preserved=source["mechanical_history"]))
    counts.update([decision])
inv.require(len(rows) + len(pending) == plan["source_ids"], "source selection conservation differs")
result = dict(status="ROOT_AUTHOR_BODY_SELECTIONS_NOT_CACHE_ADMISSION", rows=rows, unresolved=pending,
              source_ids=plan["source_ids"], selected_sources=len(rows), unresolved_sources=len(pending), counts=dict(counts),
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [plan_path, core_path, curated_path, contract_path, *required_paths, Path(__file__)]},
              cache_admitted=0, goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "root selections need ordered shards")
inv.write_json(OUT, result)
print(json.dumps({key:result[key] for key in ["status", "source_ids", "selected_sources", "unresolved_sources", "counts"]},ensure_ascii=False))
