#!/usr/bin/env python3
"""Preserve explicit day/direction repeats and filled nested nominal aliases.

No repetition is deleted. Optional leading alias slots can be removed only in
an independently identified first subject, with a balanced outer parenthesis.
Every filled field, nested abbreviation and source literal remains in order.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy_v14 as previous
from scripts.p106b_hold_resolution_refinement import ordered_deletion

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V15_EXPLICIT_DAY_DIRECTION_AND_NESTED_ALIAS"
v12, v10, v9, v4, v2, v1 = (previous.v12, previous.v10, previous.v9,
                             previous.v4, previous.v2, previous.v1)
v11, v7 = v12.previous, v12.previous.v8.previous
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
semantic_style_preserved = previous.semantic_style_preserved
contextual_repetitions = previous.contextual_repetitions
MISSING_DECLARATION = previous.MISSING_DECLARATION
flat_football = previous.flat_football
conflicting_birth_year = previous.conflicting_birth_year
ORIGINAL_CONFLICT = previous.ORIGINAL_CONFLICT
BASE_DISTINCT = v11.distinct_sections
DAYS = {v1.normalize_heading(day + "요일") for day in "월화수목금토일"}
DIRECTION = re.compile(r"(?:[가-힣A-Za-z0-9· ()-]{1,32}[ \t]+(?:방면|방향)|상행|하행)")
LEADING_EMPTY_FIELDS = re.compile(r"^[ \t]*[,，](?:[ \t]*[,，])*[ \t]*")


def explicit_schedule_repetition(text):
    if BASE_DISTINCT(text):
        return True
    plain = "".join(part for protected, part in v1.protected_parts(text)[0] if not protected)
    lines = [line.strip() for line in plain.splitlines() if line.strip()]
    frequencies = Counter(line for line in lines if len(line) >= 6)
    contexts, context = defaultdict(list), "ARTICLE_INTRO"
    observed = False
    headings = v4.LABELS | v11.SECTION_CONTEXT | v7.SECTION_CONTEXT | DAYS
    for line in lines:
        label = v1.normalize_heading(line)
        direction = DIRECTION.fullmatch(line)
        if label in DAYS:
            context, observed = "DAY:" + label, True
        elif direction:
            context, observed = "DIRECTION:" + line, True
        elif label in v11.SECTION_CONTEXT | v7.SECTION_CONTEXT:
            context = "SECTION:" + label
        elif label in v4.APPENDICES:
            context = "APPENDIX:" + label
        if len(line) >= 6 and label not in headings and not direction:
            contexts[line].append(context)
    repeats = [values for line, values in contexts.items() if frequencies[line] > 1]
    # Every repeated content line must have different explicit source contexts.
    # A weekday elsewhere cannot excuse two copies under the same day/section.
    return bool(repeats) and observed and all(len(set(values)) == len(values) for values in repeats)


def initial_balanced_alias(text):
    first = v12.intro(text)
    if first is None or not text.lstrip().startswith(first):
        return text, []
    if v9.MATH_CONTEXT.search(first) or v2.PROGRAMMING.search(first):
        return text, []
    subject = None
    depth = 0
    seen_outer = False
    for index, char in enumerate(first):
        if char == "(":
            depth += 1
            seen_outer = True
        elif char == ")":
            depth -= 1
            if depth < 0:
                return text, []
        if depth == 0 and seen_outer:
            match = v4.v3.SUBJECT.match(first, index)
            if match:
                subject = match
                break
    if subject is None:
        return text, []
    prefix = first[:subject.start()].rstrip()
    start = prefix.find("(")
    if start < 1 or not prefix.endswith(")"):
        return text, []
    name = prefix[:start].rstrip()
    if (len(name) > 300 or v12.VALUE_NAME.search(name) or v9.v6.EMPTY_VALUE_NAME.search(name)
            or re.search(r"[<>{}=\[\]`\\]", prefix)):
        return text, []
    depth = 0
    for index, char in enumerate(prefix[start:]):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and index != len(prefix[start:]) - 1:
                return text, []
            if depth < 0:
                return text, []
    if depth:
        return text, []
    fields = prefix[start + 1:-1]
    if not fields.strip():
        replacement = ""
    else:
        match = LEADING_EMPTY_FIELDS.match(fields)
        if match is None or not fields[match.end():].strip():
            return text, []
        replacement = "(" + fields[match.end():] + ")"
    offset = text.find(first)
    lo, hi = offset + start, offset + len(prefix)
    clean = text[:lo] + replacement + text[hi:]
    if clean == text:
        return text, []
    return clean, [dict(reason="FIRST_SOURCE_SUBJECT_BALANCED_ALIAS_REMOVE_ONLY_EMPTY_LEADING_SLOTS",
                        original=text[lo:hi], replacement=replacement)]


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    prepared, changes = initial_balanced_alias(original)
    with v2.v2.LOCK, patch.object(v11, "distinct_sections", explicit_schedule_repetition):
        result = previous.propose(dict(row, text=prepared), False)
    clean = result.get("candidate", result["text"])
    risks = set(result["reasons"]) if result["decision"] == "PENDING" else set()
    if not code_preserved(original, clean) or not unicode_examples_preserved(original, clean):
        risks.add("CODE_OR_UNICODE_GUARD")
    if not semantic_style_preserved(original, clean):
        risks.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if not ordered_deletion(original, clean):
        risks.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
    changes += result["changes"]
    if risks:
        return dict(decision="PENDING", text=original, candidate=clean, reasons=sorted(risks), changes=changes, rules=RULES)
    return dict(decision="EDIT" if clean != original else "KEEP", text=clean,
                reasons=["ALL_SOURCE_SCHEDULE_REPEATS_AND_FILLED_ALIAS_VALUES_PRESERVED"],
                changes=changes, rules=RULES)
