#!/usr/bin/env python3
"""Extend seven frozen exact-pair approvals by three reviewed nonprogram pairs."""
import json
from scripts import p106b_hold_resolution_literal_guard_v1 as previous

ROOT, REGISTRY = previous.ROOT, previous.REGISTRY
ADDITIONAL_REGISTRY = "handoff/audit/hold_resolution_20261027_goalc/LITERAL_GUARD_ADDITIONAL_APPROVALS_V1.json"
ADDITIONAL_SHA256 = "6D58D337F793D322F526A6EEF7810050B01043FAD9B9F5FEF5634DBB6911D79D"
ADDITIONAL_IDS = {"expanded_train:36061", "expanded_train:8455", "expanded_train:8121"}
require, sha = previous.require, previous.sha
exact_pair_preserved = previous.exact_pair_preserved


def load_registry(root=ROOT):
    cases = previous.load_registry(root)
    payload = (root / ADDITIONAL_REGISTRY).read_bytes()
    require(sha(payload) == ADDITIONAL_SHA256, "additional literal approval registry changed")
    document = json.loads(payload)
    require(document.get("schema") == "P106B_EXACT_LITERAL_GUARD_APPROVALS_V1"
            and document.get("status") == "ROOT_REVIEWED_EXACT_SOURCE_BODY_PAIRS"
            and document.get("global_code_guard_waiver") is False, "unapproved additional literal registry")
    added = set()
    for row in document["rows"]:
        ident = row["id"]
        require(ident in ADDITIONAL_IDS and ident not in cases and ident not in added
                and row.get("root_approved") is True
                and row.get("kind") == "EXACT_REVIEWED_NONPROGRAM_DELIMITER_PAIR", "invalid additional literal case")
        for pin in [row["evidence"]] + row["review_inputs"]:
            path = (root / pin["path"]).resolve()
            require(path.is_relative_to(root.resolve()), "additional literal evidence escapes workspace")
            require(sha(path.read_bytes()) == pin["sha256"], "additional literal review evidence changed")
        require(sha((root / row["original"]).read_bytes()) == row["original_text_sha256"]
                and sha((root / row["body"]).read_bytes()) == row["clean_text_sha256"], "additional literal text changed")
        cases[ident] = row
        added.add(ident)
    require(added == ADDITIONAL_IDS and len(cases) == 10, "additional literal exception scope differs")
    return cases
