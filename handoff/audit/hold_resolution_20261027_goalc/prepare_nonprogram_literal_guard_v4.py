"""Freeze two additional exact nonprogram pairs without changing old guards."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v25 as policy

AUDIT = Path(__file__).resolve().parent
selection_path = AUDIT / "ROOT_AUTHORED_SELECTIONS_V9.json"
evidence_path = AUDIT / "NONPROGRAM_LITERAL_ADJUDICATIONS_V4.md"
selected = {r["id"]: r for r in inv.cache.read(selection_path)["rows"]}
rows = []
for ident in ["expanded_train:513632", "expanded_train:940988"]:
    source = selected[ident]
    chosen = source["selected"]
    original = chosen.get("compare_source") or dict(path=source["original_paths"][0], sha256=source["original_text_sha256"])
    raw = (ROOT / original["path"]).read_text(encoding="utf-8")
    clean = (ROOT / chosen["body"]).read_text(encoding="utf-8")
    inv.require(inv.sha(raw) == original["sha256"] and inv.sha(clean) == chosen["clean_text_sha256"], "exact pair changed")
    if ident.endswith(":513632"):
        inv.require(raw.count("~~~~~~~ READER COMMENTS:") == 1
                    and raw.replace("~~~~~~~ READER COMMENTS:", " READER COMMENTS:").rstrip() == clean.rstrip(),
                    "reader-comments pair changed more than its nonprogram separator")
        literals = ["READER COMMENTS:", "The second meaning is usually associated with the lowercase dharma"]
    else:
        inv.require(len(clean.splitlines()) == 3 and policy.ordered_deletion(raw, clean), "math source-body is not the exact reviewed three-line subset")
        literals = clean.splitlines()
    inv.require(all(raw.count(value) == clean.count(value) for value in literals), "required actual source literals changed")
    review = chosen["review"]
    inv.require(inv.file_sha(ROOT / review["path"]) == review["sha256"], "saved independent review changed")
    rows.append(dict(id=ident, kind="EXACT_REVIEWED_NONPROGRAM_DELIMITER_PAIR", root_approved=True,
        original=original["path"], original_text_sha256=original["sha256"],
        body=chosen["body"], clean_text_sha256=chosen["clean_text_sha256"],
        evidence=dict(path=str(evidence_path.relative_to(ROOT)), sha256=inv.file_sha(evidence_path)),
        review_inputs=[dict(path=review["path"], sha256=review["sha256"]),
                       dict(path=str(selection_path.relative_to(ROOT)), sha256=inv.file_sha(selection_path))],
        required_literal_segments=literals, global_code_guard_waiver=False))
registry = AUDIT / "NONPROGRAM_LITERAL_APPROVALS_V4.json"
inv.require(not registry.exists(), "new exact approval registry is immutable")
inv.write_json(registry, dict(schema="P106B_EXACT_LITERAL_GUARD_APPROVALS_V1",
    status="ROOT_REVIEWED_EXACT_SOURCE_BODY_PAIRS", global_code_guard_waiver=False, rows=rows,
    producer_sha256=inv.file_sha(Path(__file__)), cache_admitted=0, training_authorized=False))
code = '''
"""Preserve the eleven old approvals and two additional exact nonprogram pairs."""
import json
from scripts import p106b_hold_resolution_literal_guard_v3 as previous

ROOT = previous.ROOT
REGISTRY = "handoff/audit/hold_resolution_20261027_goalc/NONPROGRAM_LITERAL_APPROVALS_V4.json"
REGISTRY_SHA256 = "__REGISTRY_SHA256__"
IDS = {"expanded_train:513632", "expanded_train:940988"}
require, sha = previous.require, previous.sha
exact_pair_preserved = previous.exact_pair_preserved

def load_registry(root=ROOT):
    cases = previous.load_registry(root)
    payload = (root / REGISTRY).read_bytes()
    require(sha(payload) == REGISTRY_SHA256, "new exact nonprogram approval changed")
    value = json.loads(payload)
    require(value.get("schema") == "P106B_EXACT_LITERAL_GUARD_APPROVALS_V1"
            and value.get("status") == "ROOT_REVIEWED_EXACT_SOURCE_BODY_PAIRS"
            and value.get("global_code_guard_waiver") is False,
            "new exact nonprogram approval scope differs")
    added = set()
    for row in value["rows"]:
        ident = row["id"]
        require(ident in IDS and ident not in cases and ident not in added
                and row.get("root_approved") is True
                and row.get("kind") == "EXACT_REVIEWED_NONPROGRAM_DELIMITER_PAIR", "new exact case invalid")
        for pin in [row["evidence"], *row["review_inputs"]]:
            path = (root / pin["path"]).resolve()
            require(path.is_relative_to(root.resolve()) and sha(path.read_bytes()) == pin["sha256"],
                    "new exact nonprogram evidence changed")
        require(sha((root / row["original"]).read_bytes()) == row["original_text_sha256"]
                and sha((root / row["body"]).read_bytes()) == row["clean_text_sha256"], "new exact pair changed")
        cases[ident] = row
        added.add(ident)
    require(added == IDS and len(cases) == 13, "new exact nonprogram case set differs")
    return cases
'''.replace("__REGISTRY_SHA256__", inv.file_sha(registry))
out = ROOT / "scripts/p106b_hold_resolution_literal_guard_v4.py"
with out.open("x", encoding="utf-8") as stream:
    stream.write(code.lstrip())
print(json.dumps(dict(new_cases=len(rows), total_exact_cases=13, registry_sha256=inv.file_sha(registry), global_code_guard_waiver=False)))
