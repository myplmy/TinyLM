"""Pin immutable v17, v19 regressions and actual independent body matches."""
from collections import defaultdict
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_revision_v19 as revision
from scripts import p106b_hold_resolution_policy_v19 as policy
from scripts import p106b_hold_resolution_policy_v17 as baseline_policy

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
OUT = AUDIT / "V19_DRAFT_PREFLIGHT_V1.json"
inv.require(not OUT.exists(), "new immutable execution preflight required")
baseline_path = BASE / "draft_proposals_v17/complete.json"
baseline_receipt = AUDIT / "DRAFT_V17_EXECUTION_RECEIPT_V1.json"
baseline = inv.cache.read(baseline_path)
receipt = inv.cache.read(baseline_receipt)
inv.require(receipt["original_process_exit_code"] == 0 and receipt["remaining_draft_pending"] == 121172,
            "baseline has no verified actual completion")
old_pins = baseline["lineage"]["source_code_sha256"]
inv.require(len(old_pins) == 37, "completed v17 source roster differs")
for name, expected in old_pins.items():
    inv.require(inv.file_sha(ROOT / name) == expected, "frozen v17 source changed")
code_pins = {name: inv.file_sha(ROOT / name) for name in revision.CODE}
inv.require(len(code_pins) == len(revision.CODE) == 43, "v19 production source roster differs")
for name in revision.CODE:
    compile((ROOT / name).read_bytes(), name, "exec")
probe_path = AUDIT / "policy_v19_purpose_probe_v1.json"
snapshot_path = AUDIT / "supplemental_candidates_snapshot_v24.json"
counter_path = BASE / "policy_v18_literal_counter_v1/manifest.json"
probe, snapshot, counter = [inv.cache.read(path) for path in [probe_path, snapshot_path, counter_path]]
for section in ["source_code_pins", "input_pins"]:
    for name, expected in probe[section].items():
        inv.require(inv.file_sha(ROOT / name) == expected, "latest purpose input/source changed")
proofs = defaultdict(list)
for row in snapshot["records"]:
    if row["cohort"] == "policy_v18_literal_counter_v1" and row.get("body"):
        proofs[row["id"]].append(row)
counter_rows = {row["id"]: row for row in counter["rows"]}
checked = []
for row in probe["rows"]:
    if row["decision"] not in {"KEEP", "EDIT"}:
        continue
    inv.require(all(row[name] for name in ["code_guard", "unicode_guard", "semantic_style_guard", "ordered_deletion"]),
                "terminal literal guard differs")
    source = ROOT / row["source"]["path"]
    inv.require(inv.file_sha(source) == row["source"]["sha256"], "purpose original changed")
    raw = source.read_bytes().decode("utf-8")
    earlier = baseline_policy.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
    if earlier["decision"] in {"KEEP", "EDIT"} and inv.sha(earlier.get("candidate", earlier["text"])) == row["clean_text_sha256"]:
        continue
    current = policy.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
    inv.require(current["decision"] == row["decision"] and inv.sha(current["text"]) == row["clean_text_sha256"],
                "purpose result no longer reproduces")
    matches = [proof for proof in proofs[row["id"]] if proof["clean_text_sha256"] == row["clean_text_sha256"]]
    inv.require(len(matches) == 1, "new positive lacks an exact saved independently reviewed body")
    proof = matches[0]
    inv.require(proof["original"]["sha256"] == row["source"]["sha256"], "review source differs")
    inv.require(proof["role"] not in counter_rows[row["id"]]["earlier_author_roles"], "counter reused a known earlier author")
    inv.require(inv.file_sha(ROOT / proof["body"]) == proof["clean_text_sha256"], "reviewed body changed")
    inv.require(inv.file_sha(ROOT / proof["review"]["path"]) == proof["review"]["sha256"], "saved review changed")
    checked.append(dict(id=row["id"], body=proof["body"], sha256=proof["clean_text_sha256"],
                        review=proof["review"], exact_body_match=True, known_earlier_author_reused=False))
observed_counter = next(row for row in probe["rows"] if row["id"] == "expanded_train:411438")
inv.require(observed_counter["decision"] == "PENDING" and
            "ANNOUNCED_FORMAL_DEFINITION_HAS_ONLY_BARE_PUNCTUATION" in observed_counter["reasons"],
            "observed independent formula failure escaped its fresh guard")
tests = []
for filename, expected, tool_chunk in [("test_policy_v19_v1.log", 255, "14a339"),
                                       ("test_refinement_v7_v1.log", 35, "92653c")]:
    path = AUDIT / filename
    log = path.read_text(encoding="utf-8")
    inv.require(log.rstrip().endswith("OK") and re.search(r"Ran " + str(expected) + r" tests", log),
                "required regression log differs")
    tests.append(dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path), tests=expected,
                      observed_tool_chunk=tool_chunk, observed_actual_exit_code=0))
paths = [baseline_path, baseline_receipt, probe_path, snapshot_path, counter_path, Path(__file__)]
result = dict(status="CPU_V19_DRAFT_PREFLIGHT_NOT_CACHE_ADMISSION", previous_37_sources_unchanged=True,
              source_code_sha256=code_pins, syntax_compiled_sources=len(code_pins), tests=tests,
              baseline=str(baseline_path.relative_to(ROOT)), full_v18_execution="NOT_RUN",
              purpose_rows=len(probe["rows"]), purpose_counts=probe["counts"],
              independently_reviewed_new_terminal_pairs=checked, observed_formula_counter_now_pending=True,
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
              full_scope_unique_sources=297539, full_scope_occurrences=460695,
              cache_admitted=0, goal_complete=False, training_authorized=False, gpu_or_model_execution=False)
inv.write_json(OUT, result)
print(json.dumps(dict(status=result["status"], previous_sources_unchanged=True, source_files=len(code_pins),
                      purpose_counts=probe["counts"], new_terminal_pairs=len(checked)), ensure_ascii=False))
