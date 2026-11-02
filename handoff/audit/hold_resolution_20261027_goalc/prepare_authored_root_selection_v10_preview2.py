"""Join all six completed review purposes, keeping genuine conflicts explicit."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

plan_path = AUDIT / "reviewed_selection_plan_v28.json"
prior_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V9.json"
nine_path = AUDIT / "ROOT_NINE_GUARD_SELECTIONS_V1.json"
birth_path = AUDIT / "ROOT_BIRTH_BODY_SELECTIONS_V1.json"
contract_path = AUDIT / "RESUME_FULL_GOAL_20261102_V3.md"
output = AUDIT / "ROOT_AUTHORED_SELECTIONS_V10_PREVIEW2.json"
inv.require(not output.exists(), "new immutable selection preview required")
plan, previous, nine, birth = map(inv.cache.read, [plan_path, prior_path, nine_path, birth_path])
inv.require(previous["unresolved_sources"] == 0, "root9 must remain closed")
for record in [previous, nine, birth]:
    for name, digest in record["input_pins"].items():
        inv.require(inv.file_sha(ROOT / name) == digest, "pinned earlier evidence changed")
prior = {row["id"]: row for row in previous["rows"]}
exact_nine = {row["id"]: row for row in nine["rows"]}
exact_birth = {row["id"]: row for row in birth["rows"]}
groups = ["root_selected_lexical_counter_v1", "ordinal_metadata_counter_v26_v1",
    "profile_strata_source_counter_v25_v1", "resume_guard_counter_20261102_v1",
    "resume_guard_independent_20261102_v1", "birth_field_native_counter_v1"]
required_paths = [inv.BASE / group / "manifest.json" for group in groups]
required = {path.parent.name: {row["id"] for row in inv.cache.read(path)["rows"]}
            for path in required_paths}
restricted = {"expanded_train:" + str(n) for n in [14760, 756966, 15695, 1216576, 1250821, 20624, 6030]}
verified_files = {}


def verify_selected(ident, selected):
    if ident in restricted:
        return  # Preserve the already closed safe-view/metadata decision only.
    pins = []
    if selected.get("body"):
        pins.append((selected["body"], selected["clean_text_sha256"]))
    if selected.get("review"):
        pins.append((selected["review"]["path"], selected["review"]["sha256"]))
    for name, digest in pins:
        if name not in verified_files:
            verified_files[name] = inv.file_sha(ROOT / name)
        inv.require(verified_files[name] == digest, "actual selected body/review changed")


def identity(selected):
    return selected["decision"] == "EXCLUDE", selected.get("clean_text_sha256")


def compact(selected):
    return {key: selected[key] for key in ["cohort", "decision", "body", "clean_text_sha256",
        "review", "original", "author_output", "reason"] if key in selected}


rows, unresolved, counts, seen = [], [], Counter(), set()
for source in plan["records"]:
    ident, source_hash = source["id"], source["original_text_sha256"]
    seen.add(ident)
    base = dict(id=ident, original_text_sha256=source_hash, original_paths=source["original_paths"],
        cache_admitted=False, goal_complete=False, training_authorized=False)
    earlier = prior.get(ident)
    if earlier:
        inv.require(earlier["original_text_sha256"] == source_hash, "prior source identity differs")
        verify_selected(ident, earlier["selected"])
    choices = [dict(row) for option in source["body_options"] for row in option["proposals"]]
    choices += [dict(row) for row in source["text_only_decisions"]]
    needed = [group for group, ids in required.items() if ident in ids]
    fresh = [row for row in choices if row["cohort"] in needed]
    missing = [group for group in needed if not any(row["cohort"] == group for row in fresh)]
    bad = bool(missing or any(row["decision"] == "NEEDS_ROOT" for row in fresh))
    if ident in exact_birth:
        value = exact_birth[ident]
        matching = [row for row in fresh if row["cohort"] == "birth_field_native_counter_v1"]
        inv.require(len(matching) == 1 and value["original"]["sha256"] == source_hash
            and matching[0]["clean_text_sha256"] == value["clean_text_sha256"]
            and matching[0]["review"] == value["review"], "exact birth cohort selection differs")
    if ident in exact_nine:
        chosen = dict(exact_nine[ident]["selected"])
        inv.require(exact_nine[ident]["original_text_sha256"] == source_hash and not bad,
                    "exact nine mediation lacks an assigned review")
        inv.require(any(row.get("clean_text_sha256") == chosen["clean_text_sha256"]
            and row["review"] == chosen["review"] for row in fresh), "nine selected review is absent")
        rule = "EXACT_SOURCE_BODY_REVIEW_NINE_ROOT_MEDIATION"
    else:
        identities = {identity(row) for row in fresh}
        bad = bad or len(identities) > 1 or (earlier is None and not fresh)
        if earlier and fresh:
            bad = bad or identities != {identity(earlier["selected"])}
        if bad:
            unresolved.append(dict(base, status="NEW_COMPLETE_REVIEW_SET_REQUIRES_ROOT",
                missing_cohorts=missing, previous_root9=compact(earlier["selected"]) if earlier else None,
                new_proposals=[compact(row) for row in fresh],
                exact_birth_cohort_selected=ident in exact_birth,
                restricted_parent_metadata_only=ident in restricted))
            counts.update(UNRESOLVED_ROOT_ADJUDICATION=1)
            continue
        chosen = dict(earlier["selected"] if earlier else fresh[0])
        rule = "PINNED_ROOT9_AND_ALL_COMPLETED_PURPOSES" if earlier else "ALL_COMPLETED_PURPOSES_AGREE"
    verify_selected(ident, chosen)
    inv.require(chosen.get("body") or chosen["decision"] == "EXCLUDE", "selected body is missing")
    if chosen.get("body"):
        chosen["decision"] = "KEEP" if chosen["clean_text_sha256"] == source_hash else "EDIT"
    chosen.update(original_text_sha256=source_hash, root_approved=True)
    rows.append(dict(base, selected=chosen, root_approved=True,
        status="ROOT_PURPOSE_JOIN_PENDING_INDEPENDENT_READBACK_AND_CACHE", selection_rule=rule,
        prior_selection_path=str(prior_path.relative_to(ROOT)) if earlier else None,
        new_supporting_proposals=[compact(row) for row in fresh],
        restricted_parent_full_content_not_opened=ident in restricted))
    counts.update({rule: 1})
inv.require(set(prior) <= seen and len(rows) + len(unresolved) == plan["source_ids"],
            "whole selection source conservation differs")
result = dict(status="ALL_SIX_PURPOSES_JOINED_PREVIEW_NOT_CACHE_ADMISSION", rows=rows,
    unresolved=unresolved, source_ids=plan["source_ids"], selected_sources=len(rows),
    unresolved_sources=len(unresolved), counts=dict(counts), verified_body_review_files=len(verified_files),
    restricted_parent_full_content_opened=False,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [plan_path, prior_path,
        nine_path, birth_path, contract_path, *required_paths, Path(__file__)]},
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False, indent=2).encode()) < 20_000_000,
            "selection requires explicit ordered shards")
inv.write_json(output, result)
print(json.dumps({key: result[key] for key in ["source_ids", "selected_sources", "unresolved_sources", "counts"]}))
