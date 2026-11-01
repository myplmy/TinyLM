#!/usr/bin/env python3
"""Reject announced empty formulae and missing variables in a where-block.

This counter-driven extension never writes a formula or deletes prose. It
keeps the v18 nominal repair while requiring fresh source-context handling
for the observed empty component/tensor definitions.
"""
from __future__ import annotations

import re
from scripts import p106b_hold_resolution_policy_v18 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V19_OBSERVED_EMPTY_FORMULA_AND_WHERE_VARIABLE"
v12, v10, v9, v4, v2, v1 = previous.v12, previous.v10, previous.v9, previous.v4, previous.v2, previous.v1
FORMAL = r"(?:성분|텐서|변수|벡터|행렬|계수|함수|수식|방정식|정의식)"
EMPTY_ANNOUNCED_FORMULA = re.compile(
    FORMAL + r"[^\n.!?。]*(?:다음과[ \t]*같다|다음과[ \t]*같이[ \t]*(?:정의된다|주어진다))"
    r"[.。][ \t]*\r?\n(?:[ \t]*\r?\n)*[ \t]*[.。][ \t]*(?:\r?\n|$)")
MISSING_WHERE_VARIABLE = re.compile(
    r"(?m)^[ \t]*여기서[ \t]*\r?\n(?:[ \t]*\r?\n)*[ \t]*(?:는|은|이|가)[ \t]+"
    r"(?:스칼라|벡터|상수|변수|행렬|텐서|빛의[ \t]*속도)")


def __getattr__(name):
    return getattr(previous, name)


def new_formula_holes(text):
    plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                    for protected, part in v1.protected_parts(text)[0])
    reasons = []
    if EMPTY_ANNOUNCED_FORMULA.search(plain):
        reasons.append("ANNOUNCED_FORMAL_DEFINITION_HAS_ONLY_BARE_PUNCTUATION")
    if MISSING_WHERE_VARIABLE.search(plain):
        reasons.append("WHERE_BLOCK_FORMAL_VARIABLE_IS_ACTUALLY_ABSENT")
    return reasons


def literal_holes(text):
    return sorted(set(previous.literal_holes(text)) | set(new_formula_holes(text)))


def propose(row, individual_hold=False):
    value = previous.propose(row, individual_hold)
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(value, rules=RULES)
    clean = value.get("candidate", value["text"])
    risks = set(value["reasons"]) if value["decision"] == "PENDING" else set()
    risks.update(new_formula_holes(clean))
    if ("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in risks
            and any(change["reason"] == previous.QUARANTINE for change in value["changes"])
            and previous.separate_metadata_suffix(clean)[2]):
        risks.add("PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE")
    if risks:
        return dict(decision="PENDING", text=row["text"], candidate=clean,
                    reasons=sorted(risks), changes=value["changes"], rules=RULES)
    return dict(value, rules=RULES)
