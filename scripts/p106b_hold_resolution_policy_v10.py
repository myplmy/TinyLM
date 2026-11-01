#!/usr/bin/env python3
"""Preserve populated arrows, narrative ellipses and independent source lists.

Complex partial recoveries stay proposals for actual authored text. This
version never treats a text-only counter review as automatic root admission.
"""
from __future__ import annotations

import re
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy_v9 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V10_LITERAL_FALSE_POSITIVES_AND_BOUNDED_DAMAGE"
v6, v4, v2, v1 = previous.v6, previous.v4, previous.v2, previous.v1
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
contextual_repetitions = previous.contextual_repetitions
MISSING_DECLARATION = re.compile(
    r"(?:기호|값|결과|온도|질량|부피|속도|전압)(?:은|는|이|가)\s*[.。](?![.。…])|"
    r"\bin\s+the\s+range\s*[.](?![.])", re.I)
DANGLING_FIELD = re.compile(r",\s*\)|\(\s*[,，;]|《\s*》|\(\s*←\s*(?=[,)])")
BIBLIOGRAPHY = {v1.normalize_heading(value) for value in [
    "참고 문헌", "참고자료", "참고 자료", "주요 논문", "논문 목록", "저서",
    "저작", "작품 목록", "작품 리스트", "완결 작품", "앤솔로지", "단행본",
    "bibliography", "publications", "references"]}
FAMILY = {v1.normalize_heading(value) for value in ["가족", "가족 관계", "가족관계"]}
BIB_RECORD = re.compile(r"저널|학회|연구보고|출판|문고|코믹스|키라라|호분샤|"
                        r"\b(?:journal|volume|issue|pages?|press|letters|society)\b|"
                        r"\bp[.]?\s*[0-9]+[-–][0-9]+", re.I)
LINK = re.compile(r"(?<!\[)\[\[([^\[\]|:\n]+)\|([^\[\]|\n]+)\]\](?!\])")
STRONG_DEPENDENT = re.compile(
    r"^(?:따라서|그러므로|이로부터|이때|이를|이것|그것|이러한|그러한|예를\s*들어|예컨대|"
    r"이\s*(?:경우|식|수식|값|함수|조건)|Thus\b|Therefore\b|Hence\b|"
    r"For example\b|Consequently\b|Accordingly\b)", re.I)
ORIGINAL_QUARANTINE = previous.quarantine_values


def local_records(text):
    """Remove only empty records inside explicit, populated source sections."""
    identified = previous.intro(text) is not None
    if not identified:
        return text, []
    output, changes = [], []
    context = None
    for protected, part in v1.protected_parts(text)[0]:
        if protected:
            output.append(part)
            continue
        for line in part.splitlines(keepends=True):
            label = v1.normalize_heading(line)
            if label in BIBLIOGRAPHY:
                context = "BIBLIOGRAPHY"
            elif label in FAMILY:
                context = "FAMILY"
            elif label in v4.LABELS | previous.SECTION_NAMES:
                context = None
            if context == "FAMILY" and v4.EMPTY_KINSHIP.fullmatch(line.rstrip(chr(10)+chr(13))):
                changes.append(dict(reason="EMPTY_KINSHIP_RECORD_ONLY_PRESERVE_POPULATED_RELATIONS", original=line))
                continue
            fixed = line
            if context == "BIBLIOGRAPHY" and BIB_RECORD.search(line) and not previous.MATH_CONTEXT.search(line):
                # Existing title/author/publisher words remain in their source
                # order. A missing title is not supplied from external memory.
                fixed = re.sub(r"《[ \t]*》", "", fixed)
                fixed = re.sub(r"\([ \t]*[,，][ \t]*(?=[^\s,，;)])", "(", fixed)
                if fixed != line:
                    changes.append(dict(reason="SOURCE_BIBLIOGRAPHY_VALUES_RETAINED_EMPTY_TITLE_OR_ALIAS_ONLY",
                                        original=line, replacement=fixed))
            # A date already present after a populated parenthesized nominal
            # alias needs no guessed translation/name. Formal tuples stay out.
            if not previous.MATH_CONTEXT.search(line) and not v2.PROGRAMMING.search(line):
                value, count = re.subn(r"(?<=\))\([ \t]*[,，][ \t]*(?=[12][0-9]{3}년)", "(", fixed)
                if count:
                    changes.append(dict(reason="POPULATED_NOMINAL_ALIAS_AND_EXISTING_DATE_PRESERVED",
                                        original=fixed, replacement=value))
                    fixed = value
            output.append(fixed)
    return "".join(output), changes


def render_complete_links(text):
    output, changes = [], []
    for protected, part in v1.protected_parts(text)[0]:
        if protected or previous.previous.SYNTAX_TOPIC.search(part):
            output.append(part)
            continue
        def replace(match):
            target, display = match[1], match[2]
            if not target.strip() or not display.strip() or re.search(r"[<>{}=\\]", match[0]):
                return match[0]
            changes.append(dict(reason="COMPLETE_ALIASED_LINK_RETAIN_ACTUAL_DISPLAY_AND_TARGET_IN_EVIDENCE",
                                original=match[0], replacement=display, literal_target=target))
            return display
        output.append(LINK.sub(replace, part))
    return "".join(output), changes


def bounded_quarantine(text):
    """Refuse wide deletions and unproven continuation dependencies.

    The old draft is a diagnostic proposal only. Every proposed removal must
    be a short actual damaged block, or an explicit direct premise dependent.
    An unrelated list, complete prose or a long mixed block defeats this
    automated proof and is returned intact for authored recovery.
    """
    candidate, changes = ORIGINAL_QUARANTINE(text)
    if not changes:
        return candidate, changes
    for change in changes:
        block = change["original"].strip()
        if not block:
            continue
        evidence = change.get("evidence", [])
        actual = previous.value_damage(block)
        if actual:
            # The limit restricts automatic editing, never corpus eligibility.
            if len(block) > 400 or len([line for line in block.splitlines() if line.strip()]) > 2:
                return text, []
        elif "DEPENDENT_SECTION_LABEL_AFTER_MISSING_PREMISE" in evidence:
            if v1.normalize_heading(block) not in {"예제", "예시", "증명", "example", "examples", "proof"}:
                return text, []
        elif not STRONG_DEPENDENT.search(block):
            return text, []
    return candidate, changes


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    with v2.v2.LOCK, patch.object(v1, "DANGLING_FIELD", DANGLING_FIELD), \
            patch.object(v2, "MISSING_DECLARATION", MISSING_DECLARATION), \
            patch.object(previous, "quarantine_values", bounded_quarantine):
        prepared, changes = previous.nominal_fields(original)
        prepared, local = local_records(prepared)
        changes += local
        prepared, links = render_complete_links(prepared)
        changes += links
        result = previous.propose(dict(row, text=prepared), False)
    final = result.get("candidate", result["text"])
    risks = set(result["reasons"]) if result["decision"] == "PENDING" else set()
    if not code_preserved(original, final) or not unicode_examples_preserved(original, final):
        risks.add("CODE_OR_UNICODE_GUARD")
    changes += result["changes"]
    if risks:
        return dict(decision="PENDING", text=original, candidate=final, reasons=sorted(risks), changes=changes, rules=RULES)
    return dict(decision="EDIT" if final != original else "KEEP", text=final,
                reasons=["ACTUAL_LITERAL_VALUES_AND_BOUNDED_SOURCE_CONTEXT_PRESERVED"], changes=changes, rules=RULES)
