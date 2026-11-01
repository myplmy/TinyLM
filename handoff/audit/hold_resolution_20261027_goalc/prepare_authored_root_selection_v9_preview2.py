"""Reuse pinned root8 decisions, and expose every genuinely new conflict."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT = Path(__file__).resolve().parent
plan_path = AUDIT / "reviewed_selection_plan_v14.json"
previous_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V8.json"
contract_path = AUDIT / "ROOT_AUTHORED_SELECTION_CONTRACT_V7.md"
OUT = AUDIT / "ROOT_AUTHORED_SELECTIONS_V9_PREVIEW2.json"
inv.require(not OUT.exists(), "selection preview is immutable")
plan, previous = inv.cache.read(plan_path), inv.cache.read(previous_path)
inv.require(previous["unresolved_sources"] == 0, "previous root8 selection is not closed")
for name, sha in previous["input_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == sha, "previous root8 input changed")
prior = {r["id"]: r for r in previous["rows"]}
groups = ["policy_v23_literal_counter_v1", "policy_v23_structural_counter_v1", "root_selected_literal_counter_v4"]
required_paths = [inv.BASE / group / "manifest.json" for group in groups]
required = {p.parent.name: {r["id"] for r in inv.cache.read(p)["rows"]} for p in required_paths}
rows, unresolved, counts, seen = [], [], Counter(), set()


def verify_body(selected):
    if selected.get("body"):
        inv.require(inv.file_sha(ROOT / selected["body"]) == selected["clean_text_sha256"], "root body changed")
    if selected.get("review"):
        inv.require(inv.file_sha(ROOT / selected["review"]["path"]) == selected["review"]["sha256"], "review changed")


for source in plan["records"]:
    ident, key = source["id"], source["original_text_sha256"]
    seen.add(ident)
    base = dict(id=ident, original_text_sha256=key, original_paths=source["original_paths"],
                cache_admitted=False, goal_complete=False, training_authorized=False)
    earlier = prior.get(ident)
    if earlier:
        inv.require(earlier["original_text_sha256"] == key, "new plan changed an earlier source")
        verify_body(earlier["selected"])
    choices = [dict(c) for option in source["body_options"] for c in option["proposals"]]
    choices += [dict(c) for c in source["text_only_decisions"]]
    needed = [group for group, ids in required.items() if ident in ids]
    fresh = [c for c in choices if c["cohort"] in needed]
    missing = [group for group in needed if not any(c["cohort"] == group for c in fresh)]
    identities = {(c["decision"] == "EXCLUDE", c.get("clean_text_sha256")) for c in fresh}
    bad = missing or any(c["decision"] == "NEEDS_ROOT" for c in fresh) or len(identities) > 1
    if not earlier and not fresh:
        bad = True
    if earlier and fresh:
        old_identity = (earlier["selected"]["decision"] == "EXCLUDE", earlier["selected"].get("clean_text_sha256"))
        bad = bad or identities != {old_identity}
    if bad:
        unresolved.append(dict(base, status="NEW_EXACT_REVIEW_SET_REQUIRES_ROOT", missing_cohorts=missing,
            previous_root8=earlier, new_proposals=fresh))
        counts.update(UNRESOLVED_ROOT_ADJUDICATION=1)
        continue
    if earlier:
        rows.append(dict(earlier, original_paths=base["original_paths"],
            selection_rule="PINNED_ROOT8_AND_ALL_NEW_ASSIGNED_REVIEWS",
            previous_selection=dict(path=str(previous_path.relative_to(ROOT)), sha256=inv.file_sha(previous_path)),
            new_supporting_proposals=fresh))
        counts.update(REUSED_EXACT_ROOT8=1)
        continue
    chosen = dict(fresh[0])
    verify_body(chosen)
    inv.require(chosen.get("body") or chosen["decision"] == "EXCLUDE", "new selected source lacks an actual body")
    if chosen.get("body"):
        chosen["decision"] = "KEEP" if chosen["clean_text_sha256"] == key else "EDIT"
    chosen.update(original_text_sha256=key, root_approved=True)
    rows.append(dict(base, selected=chosen, root_approved=True,
        status="NEW_SAVED_BODY_PENDING_POST_READBACK_AND_CACHE",
        selection_rule="EXPLICIT_NEW_REVIEW_PURPOSE_WITH_ALL_ASSIGNED_IDENTITIES", new_supporting_proposals=fresh))
    counts.update([chosen["decision"]])
inv.require(set(prior) <= seen and len(rows) + len(unresolved) == plan["source_ids"], "selection source conservation differs")
result = dict(status="NEW_REVIEW_SELECTION_PREVIEW_NOT_CACHE_ADMISSION", rows=rows, unresolved=unresolved,
    source_ids=plan["source_ids"], selected_sources=len(rows), unresolved_sources=len(unresolved), counts=dict(counts),
    input_pins={str(p.relative_to(ROOT)): inv.file_sha(p) for p in [
        plan_path, previous_path, contract_path, *required_paths, Path(__file__)]},
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "selection needs ordered shards")
inv.write_json(OUT, result)
print(json.dumps({k: result[k] for k in ["source_ids", "selected_sources", "unresolved_sources", "counts"]}))
