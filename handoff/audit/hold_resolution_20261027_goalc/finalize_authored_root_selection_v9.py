"""Apply exactly seven source/fresh-set mediations, with no general fallback."""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT = Path(__file__).resolve().parent
preview_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V9_PREVIEW3.json"
prior_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V8.json"
rationale_path = AUDIT / "ROOT_LITERAL_MEDIATION_RATIONALE_V2.md"
preview, prior = inv.cache.read(preview_path), inv.cache.read(prior_path)
for name, sha in preview["input_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == sha, "new preview input changed")
for name, sha in prior["input_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == sha, "earlier root8 input changed")
new_choices = {"expanded_train:1134427": "policy_v23_literal_counter_v1",
               "expanded_train:1239923": "root_selected_literal_counter_v4",
               "expanded_train:529487": "root_selected_literal_counter_v4"}
old_choices = {"expanded_train:1242246", "expanded_train:146452", "expanded_train:81898", "expanded_train:887841"}
expected = set(new_choices) | old_choices
inv.require({r["id"] for r in preview["unresolved"]} == expected, "the seven exact conflicts differ")
rows = list(preview["rows"])
mediations, counts = [], Counter()
for source in preview["unresolved"]:
    ident, key = source["id"], source["original_text_sha256"]
    earlier, fresh = source["previous_root8"], source["new_proposals"]
    inv.require(earlier and not source["missing_cohorts"] and fresh, "missing saved review cannot borrow mediation")
    inv.require(all(r["decision"] != "NEEDS_ROOT" and r["original"]["sha256"] == key for r in fresh),
                "new review is incomplete or has a different source")
    for choice in fresh:
        inv.require(inv.file_sha(ROOT / choice["body"]) == choice["clean_text_sha256"], "fresh body changed")
        inv.require(inv.file_sha(ROOT / choice["review"]["path"]) == choice["review"]["sha256"], "fresh review changed")
    if ident in new_choices:
        matches = [r for r in fresh if r["cohort"] == new_choices[ident]]
        inv.require(len(matches) == 1, "root selected purpose is not unique")
        chosen, disposition = dict(matches[0]), "EXACT_NEW_BODY_SUPERSEDES_ROOT8_BODY"
    else:
        chosen, disposition = dict(earlier["selected"]), "EXACT_ROOT8_BODY_CONFIRMED_AFTER_NEW_REVIEW_DIFF"
    inv.require(inv.file_sha(ROOT / chosen["body"]) == chosen["clean_text_sha256"], "root chosen body changed")
    chosen.update(decision="KEEP" if chosen["clean_text_sha256"] == key else "EDIT",
                  root_approved=True, original_text_sha256=key)
    prior_pin = dict(path=str(prior_path.relative_to(ROOT)), sha256=inv.file_sha(prior_path),
        id=ident, original_text_sha256=key, previous_decision=earlier["selected"]["decision"],
        previous_clean_text_sha256=earlier["selected"]["clean_text_sha256"])
    mediation = dict(id=ident, original_text_sha256=key, prior_exact_selection=prior_pin,
        all_new_proposals=fresh, selected=chosen, disposition=disposition, root_approved=True,
        evidence=dict(path=str(rationale_path.relative_to(ROOT)), sha256=inv.file_sha(rationale_path)),
        cache_admitted=0, training_authorized=False)
    mediations.append(mediation)
    rows.append(dict(id=ident, original_text_sha256=key, original_paths=source["original_paths"],
        selected=chosen, root_approved=True, status="EXACT_MEDIATED_NEW_BODY_PENDING_CACHE",
        selection_rule=disposition, prior_exact_selection=prior_pin, new_supporting_proposals=fresh,
        cache_admitted=False, goal_complete=False, training_authorized=False))
    counts.update([disposition])
inv.require(len(rows) == len({r["id"] for r in rows}) == preview["source_ids"] == 3116, "final selection conservation differs")
mediation_path = AUDIT / "ROOT_LITERAL_MEDIATIONS_V2.json"
out = AUDIT / "ROOT_AUTHORED_SELECTIONS_V9.json"
inv.require(not mediation_path.exists() and not out.exists(), "new exact root outputs are immutable")
inv.write_json(mediation_path, dict(status="EXPLICIT_SEVEN_NEW_REVIEW_ROOT_MEDIATIONS_NOT_ADMISSION",
    rows=mediations, counts=dict(counts), input_pins={str(p.relative_to(ROOT)): inv.file_sha(p) for p in [
        preview_path, prior_path, rationale_path, Path(__file__)]}, cache_admitted=0, goal_complete=False, training_authorized=False))
result = dict(status="ROOT_AUTHOR_BODY_SELECTIONS_NOT_CACHE_ADMISSION", rows=sorted(rows, key=lambda r: r["id"]),
    unresolved=[], source_ids=len(rows), selected_sources=len(rows), unresolved_sources=0,
    counts=dict(Counter(r["selected"]["decision"] for r in rows)), input_pins=dict(preview["input_pins"],
        **{str(p.relative_to(ROOT)): inv.file_sha(p) for p in [preview_path, prior_path, rationale_path, mediation_path, Path(__file__)]}),
    cache_admitted=0, goal_complete=False, training_authorized=False)
inv.require(len(json.dumps(result, ensure_ascii=False).encode("utf-8")) < 20_000_000, "root selections need ordered shards")
inv.write_json(out, result)
print(json.dumps({k: result[k] for k in ["source_ids", "selected_sources", "unresolved_sources", "counts"]}))
