"""Preserve the eleven old approvals and two additional exact nonprogram pairs."""
import json
from scripts import p106b_hold_resolution_literal_guard_v3 as previous

ROOT = previous.ROOT
REGISTRY = "handoff/audit/hold_resolution_20261027_goalc/NONPROGRAM_LITERAL_APPROVALS_V4.json"
REGISTRY_SHA256 = "14194B36DB88F7D93876ABFDFDD1BD42EC49B5078904DDF611C2CA7AFB633F38"
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
