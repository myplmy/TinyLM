"""Bind every individually adjudicated conflict to its complete exact set."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT = Path(__file__).resolve().parent
preview_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V8_PREVIEW2.json"
plan_path = AUDIT / "reviewed_selection_plan_v12.json"
rationale_path = AUDIT / "ROOT_LITERAL_MEDIATION_RATIONALE_V1.md"
contract_path = AUDIT / "ROOT_AUTHORED_SELECTION_CONTRACT_V6.md"
preview = inv.cache.read(preview_path)
special = {
    "1257055": "policy_v21_literal_counter_v1", "146452": "policy_v22_literal_counter_v1",
    "166766": "policy_v21_literal_counter_v1", "233893": "policy_v21_literal_counter_v1",
    "293331": "policy_v21_literal_counter_v1", "940988": "policy_v21_literal_counter_v1"}
expected = {"1031652", "1034905", "1047633", "1257055", "1307813", "1318235", "146452",
            "166766", "167814", "233893", "255342", "277085", "293331", "32158", "59479",
            "627193", "929270", "940988"}
inv.require({r["id"].split(":")[1] for r in preview["unresolved"]} == expected, "unexpected mediation set")


def fingerprints(choices):
    values = [dict(cohort=c["cohort"], decision=c["decision"], body=c.get("body"),
        clean_text_sha256=c.get("clean_text_sha256"), review=c.get("review"), original=c["original"],
        review_line=c.get("review_line")) for c in choices]
    return sorted(values, key=lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False))


rows = []
for source in preview["unresolved"]:
    ident = source["id"]
    choices = source["new_proposals"]
    inv.require(not source.get("missing_cohorts") and all(c["decision"] != "NEEDS_ROOT" for c in choices),
                "an incomplete review cannot be adjudicated as an exact saved body")
    group = special.get(ident.split(":")[1], "root_selected_literal_counter_v3")
    eligible = [c for c in choices if c["cohort"] == group]
    inv.require(len(eligible) == 1, "selected review purpose is not unique")
    chosen = eligible[0]
    inv.require(inv.file_sha(ROOT / chosen["body"]) == chosen["clean_text_sha256"], "selected body changed")
    inv.require(inv.file_sha(ROOT / chosen["review"]["path"]) == chosen["review"]["sha256"], "selected review changed")
    previous = source.get("existing_exact_root")
    supersedes = []
    if previous:
        path = previous["exact_decision_source"]
        supersedes.append(dict(selection_file=path, selection_file_sha256=inv.file_sha(ROOT / path),
            id=ident, original_text_sha256=source["original_text_sha256"], decision=previous["decision"],
            clean_text_sha256=previous.get("clean_text_sha256"), prior_exact_record=previous))
    rows.append(dict(id=ident, original_text_sha256=source["original_text_sha256"],
        all_fresh_proposal_fingerprints=fingerprints(choices), selected=chosen, supersedes=supersedes,
        root_approved=True, scope="ONLY_THIS_EXACT_SOURCE_AND_ALL_SAVED_FRESH_REVIEW_IDENTITIES",
        evidence=dict(path=str(rationale_path.relative_to(ROOT)), sha256=inv.file_sha(rationale_path)),
        cache_admitted=0, training_authorized=False))
result = dict(status="EXPLICIT_ROOT_LITERAL_MEDIATIONS_NOT_CACHE_ADMISSION", rows=rows,
    input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in [
        preview_path, plan_path, rationale_path, contract_path, Path(__file__)]},
    root_adjudicated_sources=len(rows), cache_admitted=0, goal_complete=False, training_authorized=False)
out = AUDIT / "ROOT_LITERAL_MEDIATIONS_V1.json"
inv.require(not out.exists(), "mediation receipt is immutable")
inv.write_json(out, result)
source = (AUDIT / "prepare_authored_root_selection_v8_preview2.py").read_text(encoding="utf-8")
source = source.replace("ROOT_AUTHORED_SELECTIONS_V8_PREVIEW2.json", "ROOT_AUTHORED_SELECTIONS_V8.json")
source = source.replace("ROOT_AUTHORED_SELECTION_CONTRACT_V5.md", "ROOT_AUTHORED_SELECTION_CONTRACT_V6.md")
anchor = 'rows, counts, pending = [], Counter(), []'
assert source.count(anchor) == 1
source = source.replace(anchor, '''
mediation_path = AUDIT / "ROOT_LITERAL_MEDIATIONS_V1.json"
mediation_document = inv.cache.read(mediation_path)
for name, sha in mediation_document["input_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == sha, "explicit mediation input changed")
mediations = {row["id"]: row for row in mediation_document["rows"]}
consumed_mediations = set()

def fingerprints(choices):
    values = [dict(cohort=c["cohort"], decision=c["decision"], body=c.get("body"),
        clean_text_sha256=c.get("clean_text_sha256"), review=c.get("review"), original=c["original"],
        review_line=c.get("review_line")) for c in choices]
    return sorted(values, key=lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False))

''' + anchor)
anchor = '    if groups_missing or unresolved_fresh or len(fresh_identities) > 1:'
assert source.count(anchor) == 1
source = source.replace(anchor, '''
    mediation = mediations.get(ident)
    if mediation:
        inv.require(not groups_missing and not unresolved_fresh, "a missing or failed new review cannot borrow a mediation")
        inv.require(mediation["root_approved"] is True and mediation["original_text_sha256"] == key,
                    "explicit mediation has a different source or no approval")
        inv.require(mediation["all_fresh_proposal_fingerprints"] == fingerprints(fresh),
                    "the complete fresh review set differs from the explicit mediation")
        supersedes = mediation["supersedes"]
        if source["root_approved"]:
            inv.require(len(supersedes) == 1 and source["selected"] == supersedes[0]["prior_exact_record"],
                        "supersession did not identify the exact previous root record")
            prior = supersedes[0]
            inv.require(inv.file_sha(ROOT / prior["selection_file"]) == prior["selection_file_sha256"],
                        "superseded root decision file changed")
        else:
            inv.require(not supersedes, "supersession claims an absent exact root record")
        chosen = dict(mediation["selected"])
        inv.require(chosen in fresh and inv.file_sha(ROOT / chosen["body"]) == chosen["clean_text_sha256"],
                    "mediated saved body is not the reviewed exact choice")
        inv.require(inv.file_sha(ROOT / chosen["review"]["path"]) == chosen["review"]["sha256"],
                    "mediated exact review changed")
        chosen.update(decision="KEEP" if chosen["clean_text_sha256"] == key else "EDIT",
                      original_text_sha256=key, root_approved=True)
        rows.append(dict(base, status="EXPLICIT_MEDIATED_BODY_PENDING_POST_READBACK_AND_CACHE", selected=chosen,
            root_approved=True, selection_rule="EXPLICIT_COMPLETE_FRESH_SET_ROOT_MEDIATION",
            mediation_file=str(mediation_path.relative_to(ROOT)), mediation_sha256=inv.file_sha(mediation_path),
            superseded_exact_root_choices=supersedes, alternatives_preserved=len(fresh_choices)-1))
        counts.update([chosen["decision"]])
        consumed_mediations.add(ident)
        continue
''' + anchor)
anchor = 'inv.require(len(rows) + len(pending) == plan["source_ids"],'
assert source.count(anchor) == 1
source = source.replace(anchor, 'inv.require(consumed_mediations == set(mediations), "not all explicit mediations were consumed")' + chr(10) + anchor)
source = source.replace('[plan_path, core_path, curated_path, contract_path, *required_paths, Path(__file__)]',
    '[plan_path, core_path, curated_path, contract_path, mediation_path, *required_paths, Path(__file__)]')
with (AUDIT / "prepare_authored_root_selection_v8.py").open("x", encoding="utf-8") as stream:
    stream.write(source)
print(json.dumps(dict(root_adjudicated_sources=len(rows), prior_exact_supersessions=sum(bool(r["supersedes"]) for r in rows),
    cache_admitted=0, prepared_selection8=True)))
