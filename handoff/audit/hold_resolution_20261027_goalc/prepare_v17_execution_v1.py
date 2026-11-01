"""Verify frozen lineage and exact independent context evidence before v17."""
from collections import defaultdict
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_revision_v17 as revision
from scripts import p106b_hold_resolution_policy_v17 as policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = AUDIT / "V17_DRAFT_PREFLIGHT_V1.json"
inv.require(not OUT.exists(), "new immutable execution preflight required")
old_path = BASE / "draft_proposals_v16/complete.json"
old = inv.cache.read(old_path)
old_pins = old["lineage"]["source_code_sha256"]
inv.require(len(old_pins) == 34, "verified v16 source inventory differs")
for name, expected in old_pins.items():
    inv.require(inv.file_sha(ROOT / name) == expected, "frozen v16 production source changed: " + name)
code_pins = {name: inv.file_sha(ROOT / name) for name in revision.CODE}
inv.require(len(code_pins) == len(revision.CODE) == 37, "v17 production inventory differs")
for name in revision.CODE:
    compile((ROOT / name).read_bytes(), name, "exec")
probe_path = AUDIT / "policy_v17_purpose_probe_v5.json"
snapshot_path = AUDIT / "supplemental_candidates_snapshot_v18.json"
probe, snapshot = inv.cache.read(probe_path), inv.cache.read(snapshot_path)
for name, expected in probe["source_code_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == expected, "latest probe source changed")
for name, expected in probe["input_pins"].items():
    inv.require(inv.file_sha(ROOT / name) == expected, "latest purpose source manifest changed")
proofs = defaultdict(list)
for row in snapshot["records"]:
    if row["cohort"] in {"policy_v17_literal_counter_v1", "policy_v17_literal_counter_v2"} and row.get("body"):
        proofs[row["id"]].append(row)
terminal = [row for row in probe["rows"] if row["decision"] in {"KEEP", "EDIT"}]
inv.require(all(row[key] for row in terminal for key in
                ["code_guard", "unicode_guard", "semantic_style_guard", "ordered_deletion"]), "terminal literal guard differs")
checked = []
for row in terminal:
    source = ROOT / row["source"]["path"]
    inv.require(inv.file_sha(source) == row["source"]["sha256"], "purpose original differs")
    raw = source.read_text(encoding="utf-8")
    earlier = policy.previous.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
    if earlier["decision"] in {"KEEP", "EDIT"} and inv.sha(earlier.get("candidate", earlier["text"])) == row["clean_text_sha256"]:
        continue
    current = policy.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
    inv.require(current["decision"] == row["decision"] and inv.sha(current["text"]) == row["clean_text_sha256"], "current purpose body changed")
    matches = [proof for proof in proofs[row["id"]]
               if proof["clean_text_sha256"] == row["clean_text_sha256"]]
    equivalence = None
    if not matches:
        # Root read the entire source, both chart candidates and this authored
        # body. Only this explicit source may reuse equal nonempty text lines;
        # this is not a general whitespace or semantic-approval heuristic.
        inv.require(row["id"] == "expanded_train:290980", "new positive lacks an exact reviewed body")
        candidates = [proof for proof in proofs[row["id"]] if proof["cohort"] == "policy_v17_literal_counter_v1"]
        inv.require(len(candidates) == 1, "explicit Step Up authored proof differs")
        proof = candidates[0]
        authored = (ROOT / proof["body"]).read_text(encoding="utf-8")
        lines = lambda text: [line.strip() for line in text.splitlines() if line.strip()]
        inv.require(lines(authored) == lines(current["text"]), "Step Up nonempty source lines differ")
        inv.require(policy.code_preserved(raw, current["text"]) and policy.unicode_examples_preserved(raw, current["text"])
                    and policy.semantic_style_preserved(raw, current["text"]), "Step Up literal preservation differs")
        matches = [proof]
        equivalence = "ROOT_EXPLICIT_290980_SAME_ORDERED_NONEMPTY_TEXT_LINES_ONLY_BLANK_LAYOUT_DIFFERS"
    proof = matches[0]
    inv.require(proof["original"]["sha256"] == row["source"]["sha256"], "independent review source differs")
    inv.require(inv.file_sha(ROOT / proof["body"]) == proof["clean_text_sha256"], "independent authored body changed")
    review = proof["review"]
    inv.require(inv.file_sha(ROOT / review["path"]) == review["sha256"], "independent review changed")
    checked.append(dict(id=row["id"], candidate_sha256=row["clean_text_sha256"], review=review,
                        reviewed_body=dict(path=proof["body"], sha256=proof["clean_text_sha256"]),
                        reviewed_decision=proof["decision"], exact_body_match=equivalence is None,
                        explicit_root_line_equivalence=equivalence))
result = dict(status="CPU_V17_DRAFT_PREFLIGHT_NOT_CACHE_ADMISSION", baseline=str(old_path.relative_to(ROOT)),
              baseline_sha256=inv.file_sha(old_path), previous_34_sources_unchanged=True,
              source_code_sha256=code_pins, syntax_compiled_sources=len(code_pins),
              purpose_rows=len(probe["rows"]), purpose_counts=probe["counts"],
              independently_reviewed_new_terminal_pairs=checked,
              probe=dict(path=str(probe_path.relative_to(ROOT)), sha256=inv.file_sha(probe_path)),
              snapshot=dict(path=str(snapshot_path.relative_to(ROOT)), sha256=inv.file_sha(snapshot_path)),
              full_scope_unique_sources=297539, full_scope_occurrences=460695,
              cache_admitted=0, goal_complete=False, training_authorized=False, gpu_or_model_execution=False,
              producer_sha256=inv.file_sha(Path(__file__)))
inv.write_json(OUT, result)
print(json.dumps(dict(status=result["status"], previous_sources_unchanged=True, source_files=len(code_pins),
                      purpose_counts=probe["counts"], new_terminal_pairs=len(checked)), ensure_ascii=False))
