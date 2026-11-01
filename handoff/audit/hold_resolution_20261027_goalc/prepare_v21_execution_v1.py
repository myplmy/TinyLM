"""Pin v20 and all new source/counter checks before a complete CPU proposal."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_revision_v21 as revision
from scripts import p106b_hold_resolution_policy_v21 as policy

AUDIT, BASE = Path(__file__).resolve().parent, inv.BASE
OUT = AUDIT / "V21_DRAFT_PREFLIGHT_V1.json"
inv.require(not OUT.exists(), "new immutable preflight required")
baseline_path = BASE / "draft_proposals_v20/complete.json"
receipt_path = AUDIT / "DRAFT_V20_EXECUTION_RECEIPT_V1.json"
baseline, receipt = inv.cache.read(baseline_path), inv.cache.read(receipt_path)
inv.require(receipt["original_process_exit_code"] == 0 and receipt["remaining_draft_pending"] == 122620,
            "v20 has no verified actual completion")
inv.require(receipt["completed_artifact"]["sha256"] == inv.file_sha(baseline_path), "baseline receipt changed")
old_pins = baseline["lineage"]["source_code_sha256"]
inv.require(len(old_pins) == 46, "v20 roster differs")
for name, key in old_pins.items():
    inv.require(inv.file_sha(ROOT / name) == key, "old production source changed")
code_pins = {name: inv.file_sha(ROOT / name) for name in revision.CODE}
inv.require(len(code_pins) == len(revision.CODE) == 52, "v21 source roster differs")
for name in code_pins:
    compile((ROOT / name).read_bytes(), name, "exec")
probe_path = AUDIT / "policy_v21_purpose_probe_v3.json"
old_probe_path = AUDIT / "policy_v20_purpose_probe_v1.json"
counter_path = BASE / "policy_v21_literal_counter_v1/manifest.json"
probe, old_probe, counter = [inv.cache.read(path) for path in [probe_path, old_probe_path, counter_path]]
old_rows = {row["id"]: row for row in old_probe["rows"]}
for section in ["source_code_pins", "input_pins"]:
    for name, key in probe[section].items():
        inv.require(inv.file_sha(ROOT / name) == key, "latest probe input/source changed")
choices, evidence = {}, []
directory = BASE / "agents/structure_counter/policy_v21_literal_counter_v1"
for path in directory.glob("review*.md"):
    rank = re.fullmatch(r"review_([0-9]+)(?:_v([0-9]+))?[.]md", path.name)
    inv.require(rank is not None, "unexpected exact counter review filename")
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("|"):
            continue
        cells = [part.strip().strip("`*") for part in line.split("|")[1:-1]]
        if len(cells) < 5 or cells[0] not in {row["id"] for row in counter["rows"]}:
            continue
        order = (int(rank[1]), int(rank[2] or 1), number)
        if cells[0] not in choices or order > choices[cells[0]][0]:
            choices[cells[0]] = order, path, number, cells
counter_rows = {row["id"]: row for row in counter["rows"]}
inv.require(set(choices) == set(counter_rows) and len(choices) == 14, "all 14 actual counter reviews required")
for ident, (_, path, number, cells) in choices.items():
    inv.require(cells[1] in {"ACCEPT_CANDIDATE", "REVISE_TEXT"} and cells[2] and cells[4], "counter lacks scope/rationale or remains unresolved")
    pair = counter_rows[ident]
    for pin in [pair["original"], pair["candidate"]]:
        inv.require(inv.file_sha(ROOT / pin["path"]) == pin["sha256"], "counter exact input changed")
    names = set(re.findall(re.escape(ident.replace(":", "_")) + r"_v[0-9]+[.]txt", cells[3]))
    if cells[1] == "REVISE_TEXT":
        inv.require(len(names) == 1, "revised counter body ambiguous")
        body = directory / next(iter(names))
        inv.require(body.is_file() and 0 < body.stat().st_size < 20_000_000, "revised counter body missing")
    else:
        inv.require(not names or len(names) == 1 and inv.file_sha(directory / next(iter(names))) == pair["candidate"]["sha256"],
                    "accepted counter names a different authored body")
        body = ROOT / pair["candidate"]["path"]
    evidence.append(dict(id=ident, decision=cells[1], original=pair["original"],
                         body=dict(path=str(body.relative_to(ROOT)), sha256=inv.file_sha(body)),
                         review=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path), line=number,
                                     actual_scope=cells[2], reason=cells[4])))
new_terminal = []
for row in probe["rows"]:
    if row["decision"] not in {"KEEP", "EDIT"}:
        continue
    inv.require(all(row[key] for key in ["code_guard", "unicode_guard", "semantic_style_guard", "ordered_deletion"]), "terminal guard differs")
    if old_rows[row["id"]]["decision"] != "PENDING":
        continue
    matches = [item for item in evidence if item["id"] == row["id"] and item["decision"] == "ACCEPT_CANDIDATE"
               and item["body"]["sha256"] == row["clean_text_sha256"]
               and item["original"]["sha256"] == row["source"]["sha256"]]
    inv.require(len(matches) == 1, "new auto terminal lacks an exact independent full-body acceptance")
    pair = counter_rows[row["id"]]
    raw = (ROOT / pair["original"]["path"]).read_bytes().decode("utf-8")
    value = policy.propose(dict(id=row["id"], text=raw, complete_eos=True, valid_utf8=True))
    inv.require(value["decision"] == row["decision"] and inv.sha(value["text"]) == row["clean_text_sha256"], "new body no longer reproduces")
    new_terminal.append(matches[0])
inv.require(len(new_terminal) == 12, "new terminal cohort changed")
for ident, reason in [("expanded_train:940988", "OBSERVED_QUESTION_ANSWER_OR_JOIN_UI_REQUIRES_CONTEXT"),
                      ("expanded_train:166766", "UNBOUND_SOURCE_RECORD_STYLE_LEGEND_REQUIRES_CONTEXT"),
                      ("expanded_train:411438", "ANNOUNCED_FORMAL_DEFINITION_HAS_ONLY_BARE_PUNCTUATION")]:
    row = next(row for row in probe["rows"] if row["id"] == ident)
    inv.require(row["decision"] == "PENDING" and reason in row["reasons"], "independent semantic negative escaped fresh checking")
tests = []
for name, count, chunk in [("test_policy_v21_v4.log", 323, "2cac9c"),
                           ("test_refinement_v9_v2.log", 40, "RECORDED_IN_EXECUTION_TOOL_RESULT"),
                           ("test_review_safeguards_v1.log", 9, "6987ff")]:
    path = AUDIT / name
    log = path.read_text(encoding="utf-8")
    inv.require(log.rstrip().endswith("OK") and re.search(r"Ran " + str(count) + r" tests", log), "required test log differs")
    tests.append(dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path), tests=count,
                      observed_tool_chunk=chunk, observed_actual_exit_code=0))
paths = [baseline_path, receipt_path, probe_path, old_probe_path, counter_path, Path(__file__)]
result = dict(status="CPU_V21_DRAFT_PREFLIGHT_NOT_CACHE_ADMISSION", source_code_sha256=code_pins,
              previous_46_sources_unchanged=True, syntax_compiled_sources=len(code_pins),
              tests=tests, purpose_rows=len(probe["rows"]), purpose_counts=probe["counts"],
              all_independent_counter_pairs=evidence, independently_reviewed_new_auto_terminal_pairs=new_terminal,
              observed_semantic_negatives_pending=True, full_v21_execution="NOT_RUN",
              input_pins={str(path.relative_to(ROOT)): inv.file_sha(path) for path in paths},
              full_scope_unique_sources=297539, full_scope_occurrences=460695,
              cache_admitted=0, goal_complete=False, training_authorized=False, gpu_or_model_execution=False)
inv.write_json(OUT, result)
print(json.dumps(dict(status=result["status"], production_sources=len(code_pins), counter_pairs=len(evidence),
                      exact_new_terminal_pairs=len(new_terminal), purpose_counts=probe["counts"]), ensure_ascii=False))
