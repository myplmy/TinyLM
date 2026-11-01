#!/usr/bin/env python3
"""Add one source-pinned nonprogram Search-UI pair to the ten old cases."""
import json
from scripts import p106b_hold_resolution_literal_guard_v2 as previous

ROOT = previous.ROOT
REGISTRY = "handoff/audit/hold_resolution_20261027_goalc/NONPROGRAM_SEARCH_UI_APPROVAL_V1.json"
REGISTRY_SHA256 = "26A97E2231C72FFE386437EFCD62835C6433DABBF1EEF2750B93CBC225F79558"
require, sha = previous.require, previous.sha
exact_pair_preserved = previous.exact_pair_preserved


def load_registry(root=ROOT):
    cases = previous.load_registry(root)
    payload = (root / REGISTRY).read_bytes()
    require(sha(payload) == REGISTRY_SHA256, "Search UI exact approval changed")
    value = json.loads(payload)
    require(value.get("schema") == "P106B_EXACT_LITERAL_GUARD_APPROVALS_V1"
            and value.get("status") == "ROOT_REVIEWED_EXACT_SOURCE_BODY_PAIRS"
            and value.get("global_code_guard_waiver") is False and len(value["rows"]) == 1,
            "Search UI approval has another scope")
    row = value["rows"][0]
    require(row["id"] == "expanded_train:6773" and row["id"] not in cases
            and row.get("root_approved") is True
            and row.get("kind") == "EXACT_REVIEWED_NONPROGRAM_DELIMITER_PAIR",
            "Search UI is not an approved exact case")
    for pin in [row["evidence"], *row["review_inputs"]]:
        path = (root / pin["path"]).resolve()
        require(path.is_relative_to(root.resolve()) and sha(path.read_bytes()) == pin["sha256"],
                "Search UI source review evidence changed")
    require(sha((root / row["original"]).read_bytes()) == row["original_text_sha256"]
            and sha((root / row["body"]).read_bytes()) == row["clean_text_sha256"], "Search UI exact pair changed")
    cases[row["id"]] = row
    require(len(cases) == 11, "literal exception count differs")
    return cases
