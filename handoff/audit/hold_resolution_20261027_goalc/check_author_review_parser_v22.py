"""Regression checks for real saved prose reviews and missing evidence.

Extract parser definitions without importing the snapshot producer, whose
top level deliberately creates immutable provenance output.
"""
import ast
from pathlib import Path
import re
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
source = HERE / "collect_supplemental_candidates_v22.py"
module = ast.parse(source.read_text(encoding="utf-8"))
functions = [node for node in module.body if isinstance(node, ast.FunctionDef)
             and node.name in {"ident", "review_entries"}]


def require(condition, message):
    if not condition:
        raise ValueError(message)


namespace = {"re": re, "inv": SimpleNamespace(require=require)}
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
parse = namespace["review_entries"]
base = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc/agents"
path = base / "context_hangul/root_selected_signal_counter_v1/review_005.md"
payload = path.read_bytes()
entries = parse(payload, True)
require([row["cells"][0] for row in entries] == ["expanded_train:" + value
        for value in ["21295", "2166", "641587", "11885"]], "real prose IDs lost")
require(entries[1]["cells"][1] == "NEEDS_ROOT", "withdrawn status misread")
lines = payload.decode("utf-8").splitlines()
for row in entries:
    require(lines[row["number"] - 1] == "## ID " + row["cells"][0].split(":")[1],
            "actual review start line lost")
    require(row["raw"] == chr(10).join(lines[row["number"] - 1:row["end"]]),
            "raw review line span lost")
require(not parse(payload), "unassigned prose syntax was enabled globally")
path = base / "context_hangul/root_selected_signal_counter_v1/review_004.md"
require(len(parse(path.read_bytes(), True)) == 3, "explicit compound rationale label lost")
path = base / "legacy_review/retracted_review_counter_v1/review.md"
require(len(parse(path.read_bytes(), True)) == 3, "saved independent table lost")
for fields in [
    ["## ID 2166", "- 판정: REVISE_TEXT", "- 실제 범위: EOF", "- 출력: missing.txt"],
    ["## ID 2166", "- 판정: PASS", "- 실제 범위: EOF", "- 출력: missing.txt", "- 근거: x"],
]:
    try:
        parse(chr(10).join(fields).encode("utf-8"), True)
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete or unsupported evidence accepted")
require(not parse("설명에 ID 2166이 나타나지만 판정은 없다.".encode("utf-8"), True),
        "narrative ID became a review")
print("Saved table/prose mapping, real source line spans and invalid-evidence regressions passed.")
