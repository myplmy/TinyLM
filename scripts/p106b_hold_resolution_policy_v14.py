#!/usr/bin/env python3
"""Render source-labelled flat football infoboxes without joining arrays.

Every populated label/value stays in source order. Only the observed flat
template grammar is supported; nested syntax, unmatched boundaries and lost
fields remain pending. Explicit tenure dates never become inferred births.
"""
from __future__ import annotations

import re
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy_v13 as previous
from scripts.p106b_hold_resolution_refinement import ordered_deletion

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V14_FLAT_LABELLED_FIELDS_AND_TYPED_TENURE"
v12, v10, v9, v4, v2, v1 = (previous.previous, previous.v10, previous.v9,
                              previous.v4, previous.v2, previous.v1)
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
semantic_style_preserved = previous.semantic_style_preserved
contextual_repetitions = previous.contextual_repetitions
MISSING_DECLARATION = previous.MISSING_DECLARATION
ORIGINAL_CONFLICT = v2.v2.conflicting_birth_year
FULL_DATE = re.compile(r"([12][0-9]{3})년\s*[0-9]{1,2}월\s*[0-9]{1,2}일")
PAREN = re.compile(r"\(([^()\n]*)\)")
TENURE = re.compile(r"^[ \t]*(?:재위|재임|임기|재직)(?:[ \t]*기간)?[ \t]*[:：][ \t]*")
DOUBLE_TOPIC_ALIAS = re.compile(r"(?:은|는)[ \t]+흔히[^\n.!?]{1,120}\([ \t]*\)[ \t]*(?:은|는)[ \t]+")
TEMPLATE = "축구 선수 정보"
FIELD_NAMES = {
    "이름", "사진", "그림", "사진크기", "설명", "전체 이름", "출생일", "출생지",
    "사망일", "사망지", "키", "포지션", "현 소속팀", "등번호", "청소년 클럽 연도",
    "청소년 클럽", "클럽 연도", "클럽", "출장수(골)", "국가대표팀 연도", "국가대표팀",
    "국가대표팀 출장수(골)", "클럽팀 최신 업데이트 날짜", "국가대표팀 최신 업데이트 날짜",
    "감독 연도", "감독 클럽",
}


def conflicting_birth_year(text):
    if not ORIGINAL_CONFLICT(text):
        return False
    first = text.split(chr(10) + chr(10), 1)[0]
    dated = [match for match in PAREN.finditer(first) if FULL_DATE.search(match[1])]
    categories = set(re.findall(r"(?m)^[ \t]*([12][0-9]{3})년[ \t]*출생[ \t]*$", text))
    # A single source birth category is not a missing value. Release only the
    # precise old false positive in which every dated parenthesis is explicitly
    # a tenure field. Ordinary life spans and conflicting birth labels stay out.
    return not (len(categories) == 1 and dated and all(TENURE.match(match[1]) for match in dated))


def flat_football(text):
    """Return an exact labelled prefix and independent suffix, or no proof."""
    source = text.lstrip()
    opener = "{{" + TEMPLATE
    if not source.startswith(opener + chr(10)):
        return None
    close = source.find("}}", len(opener))
    if close < 0:
        return None
    block, suffix = source[:close + 2], source[close + 2:].lstrip()
    if "{{" in block[2:] or any(token in block[2:-2] for token in ("}}", "[[", "]]", "{|", "|}", "<", ">", "`")):
        return None
    if not suffix or v12.BASE_INTRO(suffix) is None:
        return None
    # A syntax example must remain literal, even if it happens to use this
    # exact template name. A second template is not silently incorporated.
    if previous.previous.v8.SYNTAX_TOPIC.search(suffix) or suffix.startswith("{{"):
        return None
    first = suffix.split(chr(10) + chr(10), 1)[0]
    # The observed counterexample has two topic particles around an empty
    # nickname slot. Removing just () would leave a damaged introduction;
    # source-specific authored repair, rather than field rendering, is needed.
    if DOUBLE_TOPIC_ALIAS.search(first):
        return None
    fields, kept, seen, blank = {}, [], set(), []
    lines = block[len(opener): -2].splitlines()
    for index, line in enumerate(lines, 2):
        if not line.strip():
            continue
        stripped = line.lstrip()
        if not stripped.startswith("|") or stripped.count("|") != 1 or "=" not in stripped:
            return None
        label, value = stripped[1:].split("=", 1)
        label = label.strip()
        if label not in FIELD_NAMES or label in seen:
            return None
        seen.add(label)
        fields[label] = value.strip()
        if value.strip():
            # The source already has one unambiguous line per field. Complete
            # prose, missing values and multiline/nested constructs need text
            # review rather than being mistaken for this flat value grammar.
            if (v1.PUNCTUATION.search(value) or v9.value_damage(value)
                    or v1.cache.MISSING_FIELD.search(value) or v1.DANGLING_FIELD.search(value)):
                return None
            kept.append(stripped[1:].strip())
        else:
            blank.append(dict(line=index, original=line))
    name = fields.get("이름")
    if not name or not first.startswith(name) or not kept:
        return None
    born = FULL_DATE.search(fields.get("출생일", ""))
    categories = set(re.findall(r"(?m)^[ \t]*([12][0-9]{3})년[ \t]*출생[ \t]*$", suffix))
    if born and categories and categories != {born[1]}:
        return None
    prefix = (chr(10) * 2).join([TEMPLATE, *kept]) + chr(10) * 2
    return dict(prefix=prefix, suffix=suffix, populated=kept,
                change=dict(reason="FLAT_SOURCE_LABEL_VALUE_RECORDS_PRESERVED_WITHOUT_ARRAY_BINDING",
                            original=block, replacement=prefix, empty_fields=blank,
                            field_order=list(fields), array_pairing_inferred=False))


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    with v2.v2.LOCK, patch.object(v2.v2, "conflicting_birth_year", conflicting_birth_year):
        flat = flat_football(original)
        if flat is None:
            return dict(previous.propose(row, False), rules=RULES)
        suffix_value = previous.propose(dict(row, text=flat["suffix"]), False)
        suffix = suffix_value.get("candidate", suffix_value["text"])
        prepared = flat["prefix"] + suffix
        value = previous.propose(dict(row, text=prepared), False)
    clean = value.get("candidate", value["text"])
    risks = set()
    for result in [suffix_value, value]:
        if result["decision"] == "PENDING":
            risks.update(result["reasons"])
    if any(record not in clean for record in flat["populated"]):
        risks.add("FLAT_POPULATED_FIELD_NOT_LITERAL_PRESERVED")
    if not code_preserved(original, clean) or not unicode_examples_preserved(original, clean):
        risks.add("CODE_OR_UNICODE_GUARD")
    if not semantic_style_preserved(original, clean):
        risks.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if not ordered_deletion(original, clean):
        risks.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
    changes = [flat["change"], *suffix_value["changes"], *value["changes"]]
    if risks:
        return dict(decision="PENDING", text=original, candidate=clean, reasons=sorted(risks), changes=changes, rules=RULES)
    return dict(decision="EDIT", text=clean, reasons=["SOURCE_LABELLED_FIELDS_AND_INDEPENDENT_BIOGRAPHY_PRESERVED"],
                changes=changes, rules=RULES)
