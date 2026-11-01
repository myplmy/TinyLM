#!/usr/bin/env python3
"""Seven immutable, source-reviewed nonprogram delimiter exceptions.

No global fence/backtick rule changes. Any other source/body version remains
subject to the existing guard, and actual literal program segments must stay.
"""
from pathlib import Path
import hashlib
import json

from scripts import p106b_hold_policy_v3 as policy

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "handoff/audit/hold_resolution_20261027_goalc/LITERAL_GUARD_APPROVALS_V2.json"
REGISTRY_SHA256 = "0A5EEBE33810ED1F208F5A9219DF4DE53B93BF94E6FDB976D747B0FB5CE6DC0E"


def sha(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def require(value, message):
    if not value:
        raise ValueError(message)


def load_registry(root=ROOT):
    payload = (root / REGISTRY).read_bytes()
    require(sha(payload) == REGISTRY_SHA256, "literal approval registry changed")
    value = json.loads(payload)
    require(value.get("schema") == "P106B_EXACT_LITERAL_GUARD_APPROVALS_V1"
            and value.get("status") == "ROOT_REVIEWED_EXACT_SOURCE_BODY_PAIRS"
            and value.get("global_code_guard_waiver") is False, "unapproved literal registry")
    cases = {}
    for row in value["rows"]:
        require(row["id"] not in cases and row.get("root_approved") is True
                and row.get("kind") == "EXACT_REVIEWED_NONPROGRAM_DELIMITER_PAIR", "invalid exact literal case")
        for pin in [row["evidence"]] + row["review_inputs"]:
            path = (root / pin["path"]).resolve()
            require(path.is_relative_to(root.resolve()), "literal evidence escapes workspace")
            require(sha(path.read_bytes()) == pin["sha256"], "literal review evidence changed")
        require(sha((root / row["original"]).read_bytes()) == row["original_text_sha256"]
                and sha((root / row["body"]).read_bytes()) == row["clean_text_sha256"], "reviewed literal text changed")
        cases[row["id"]] = row
    require(len(cases) == 7, "literal exception scope differs")
    return cases


def exact_pair_preserved(original, cleaned, case_id, cases):
    if not policy.unicode_examples_preserved(original, cleaned):
        return False
    row = cases.get(case_id)
    if row is None or row.get("root_approved") is not True:
        return False
    if (sha(original.encode("utf-8")) != row["original_text_sha256"]
            or sha(cleaned.encode("utf-8")) != row["clean_text_sha256"]):
        return False
    return all(segment in original and cleaned.count(segment) == original.count(segment)
               for segment in row["required_literal_segments"])
