"""Pin the explicitly adjudicated 23 source decisions, preserving old choices."""
from collections import Counter
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v16 as policy
from scripts import p106b_hold_resolution_literal_guard_v2 as literal

AUDIT = Path(__file__).resolve().parent
OUT = AUDIT / "ROOT_NEW_READBACK_BODY_SELECTIONS_V1.json"
inv.require(not OUT.exists(), "exact root decisions must be new")
snapshot_path = AUDIT / "supplemental_candidates_snapshot_v14.json"
snapshot = inv.cache.read(snapshot_path)
evidence = AUDIT / "ROOT_NEW_READBACK_ADJUDICATIONS_V1.md"
old_root = AUDIT / "ROOT_SUPPLEMENTAL_BODY_SELECTIONS_V1.json"
old = {row["id"]: row for row in inv.cache.read(old_root)["rows"]}
targets = [(row["id"], row["cohort"]) for row in snapshot["records"]
           if row["cohort"] in {"policy_v15_literal_counter_v1", "secondary_body_counter_v1", "policy_v16_literal_counter_v2"}]
targets.append(("expanded_train:27348", "exclusion_second_review_v1"))
inv.require(len(targets) == len(set(targets)) == 23, "adjudicated source set differs")
records = []
cases = literal.load_registry()
numeric = re.compile(r"(?<![A-Za-z0-9_])[-+−]?[0-9]+(?:[.,][0-9]+)*(?:%|°[CF])?")
for ident, cohort in targets:
    candidates = [row for row in snapshot["records"] if row["id"] == ident and row["cohort"] == cohort]
    inv.require(len(candidates) == 1, "explicit cohort source is not unique")
    row = candidates[0]
    source = row["original"]
    compare = row.get("compare_source", source)
    inv.require(inv.file_sha(ROOT / compare["path"]) == compare["sha256"], "comparison source changed")
    decision = "EXCLUDE" if ident == "expanded_train:27348" else "EDIT"
    value = dict(id=ident, decision=decision, source=source["path"], original_text_sha256=source["sha256"],
                 selected_cohort=cohort, root_approved=True, cache_admitted=False,
                 review_inputs=[row["review"]], reason="EXPLICIT_ROOT_SOURCE_DIFF_AND_INDEPENDENT_REVIEW_ADJUDICATION",
                 evidence=dict(path=str(evidence.relative_to(ROOT)), sha256=inv.file_sha(evidence)))
    if decision == "EXCLUDE":
        inv.require(row["decision"] == "EXCLUDE", "source exclusion differs from root addendum")
    else:
        inv.require(row["status"] in {"PINNED_BODY_NOT_ROOT_ADMISSION", "MATERIALIZED_BODY_NOT_ROOT_ADMISSION"},
                    "no actual materialized body for root selection")
        body = ROOT / row["body"]
        inv.require(inv.file_sha(body) == row["clean_text_sha256"], "root body changed")
        raw = (ROOT / compare["path"]).read_bytes().decode("utf-8")
        clean = body.read_bytes().decode("utf-8")
        code = policy.code_preserved(raw, clean)
        exact_literal = False if code else literal.exact_pair_preserved(raw, clean, ident, cases)
        value.update(body=row["body"], clean_text_sha256=row["clean_text_sha256"],
                     code_guard=code, exact_reviewed_literal_exception=exact_literal,
                     unicode_guard=policy.unicode_examples_preserved(raw, clean),
                     semantic_style_guard=policy.semantic_style_preserved(raw, clean),
                     ordered_nonwhitespace_deletion_only=policy.ordered_deletion(raw, clean),
                     introduced_numeric_occurrences=dict(Counter(numeric.findall(clean)) - Counter(numeric.findall(raw))),
                     newly_added_editor_memo=bool(inv.corpus.MEMOS.search(clean) and not inv.corpus.MEMOS.search(raw)))
        inv.require(value["unicode_guard"] and (code or exact_literal) and value["semantic_style_guard"],
                    "exact decision has an unreviewed literal or style loss")
        inv.require(not value["introduced_numeric_occurrences"] and not value["newly_added_editor_memo"],
                    "exact decision introduces a number or editor memo")
        if compare != source:
            value.update(compare_source=compare, restricted_parent_full_content_not_opened=True,
                         excluded_original_line_range_metadata_only=[43, 45])
        if ident in old and old[ident]["clean_text_sha256"] != value["clean_text_sha256"]:
            value["supersedes"] = [dict(selection_file=str(old_root.relative_to(ROOT)),
                selection_file_sha256=inv.file_sha(old_root), id=ident,
                clean_text_sha256=old[ident]["clean_text_sha256"], decision=old[ident]["decision"])]
    records.append(value)
paths = [snapshot_path, evidence, old_root, Path(__file__)]
inv.write_json(OUT, dict(status="EXACT_ROOT_NEW_BODY_SELECTIONS_NOT_CACHE_ADMISSION", rows=records,
    pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in paths},
    cache_admitted=0, goal_complete=False, training_authorized=False))
print(json.dumps(dict(rows=len(records), decisions=dict(Counter(row["decision"] for row in records)),
    superseded_exact_choices=[row["id"] for row in records if row.get("supersedes")]), ensure_ascii=False))
