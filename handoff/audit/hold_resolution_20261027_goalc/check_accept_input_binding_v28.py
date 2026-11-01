"""Check real assigned inputs and reject same-name paths outside their pins."""
from pathlib import Path
import ast
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
producer = AUDIT / "collect_supplemental_candidates_v28.py"
tree = ast.parse(producer.read_text(encoding="utf-8"))
definition = [node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == "exact_assigned_input_reference"]
assert len(definition) == 1
namespace = dict(Path=Path, ROOT=ROOT, re=re)
exec(compile(ast.Module(body=definition, type_ignores=[]), str(producer), "exec"), namespace)
bind = namespace["exact_assigned_input_reference"]
base = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
manifest = json.loads((base / "remaining_context_v14_v1/manifest.json").read_text())
cases = {row["id"]: row for row in manifest["rows"]}
snapshot = json.loads((AUDIT / "supplemental_candidates_snapshot_v27.json").read_text())
checked = []
for ident in ["expanded_train:1215625", "expanded_train:1251307", "expanded_train:474106", "expanded_train:842241"]:
    row = next(row for row in snapshot["records"] if row["id"] == ident)
    source = cases[ident]
    chosen = source.get("candidate") or source["paths"]["candidate"]
    actual = hashlib.sha256((ROOT / chosen["path"]).read_bytes()).hexdigest().upper()
    assert actual == chosen["sha256"]
    reference = row["body_references"][0]
    assert bind(row["review_text"], reference, chosen)
    assert not bind("/tmp/another-source/" + reference, reference, chosen)
    assert not bind("different-folder/" + reference, reference, chosen)
    assert not bind("https://example.invalid/" + reference, reference, chosen)
    assert not bind(reference.replace(".txt", "_v2.txt"), reference.replace(".txt", "_v2.txt"), chosen)
    checked.append(dict(id=ident, actual_assigned_candidate=chosen,
                        source_candidate_pin_verified=True, forged_same_name_paths_rejected=True,
                        different_authored_version_requires_actual_file=True))
print(json.dumps(dict(status="REAL_ASSIGNED_INPUT_BINDINGS_AND_FORGED_PATH_COUNTERS_VERIFIED",
                      actual_cases=len(checked), positive_and_negative_assertions=len(checked) * 6,
                      records=checked), ensure_ascii=False))
