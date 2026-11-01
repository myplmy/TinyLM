"""Quarantine source-proved empty leaves and pointers, never filled values."""
import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v22 as policy
from scripts import p106b_hold_resolution_policy_v17 as records

REASON = "QUARANTINE_SOURCE_PROVED_EMPTY_STRUCTURE_WITH_NO_POPULATED_VALUE"
LEAF_PAIRS = {
    policy.v1.normalize_heading("줄거리"): {policy.v1.normalize_heading(value) for value in ["배역", "출연진"]},
    policy.v1.normalize_heading("수록 소프트"): {policy.v1.normalize_heading("기타")},
}
GROUP_FAMILY = {"부모", "자녀", "형제", "자매"}
STAFF = re.compile(r"staff|musicians", re.I)
CREDIT_HEADINGS = {policy.v1.normalize_heading(value) for value in ["참여", "제작 참여", "제작참여", "제작진"]}
CONTENTS = re.compile(r"(?mi)^[ \t]*(?:목차|차례|table of contents)[ \t]*$")


def named_intro(text):
    with policy.v2.v2.LOCK, patch.object(policy.v12, "ENTITY", records.ENTITY), \
            patch.object(policy.v4, "ENTITY", records.ENTITY):
        return records.intro(text)


def clean_empty_structures(text):
    parts, opened = policy.v1.protected_parts(text)
    if opened or CONTENTS.search(text) or policy.v12.v8.SYNTAX_TOPIC.search(text) or named_intro(text) is None:
        return text, []
    plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part for protected, part in parts)
    assert len(plain) == len(text)
    lines, raw_lines = plain.splitlines(keepends=True), text.splitlines(keepends=True)
    offsets, cursor = [], 0
    for line in raw_lines:
        offsets.append(cursor)
        cursor += len(line)
    entries = [index for index, line in enumerate(lines) if line.strip()]
    removed = {}

    def add(index, subtype):
        lo, hi = offsets[index], offsets[index] + len(raw_lines[index])
        removed[index] = dict(reason=REASON, subtype=subtype, original=text[lo:hi],
                              source_characters=[lo, hi], inferred_value_added=False)

    metadata_proven = records.separate_metadata_suffix(text)[2]
    for position, index in enumerate(entries):
        value = lines[index].strip()
        if policy.QUOTE_CONTEXT.search(plain[max(0, offsets[index] - 400):offsets[index] + len(lines[index])]):
            continue
        following_index = entries[position + 1] if position + 1 < len(entries) else None
        following = lines[following_index].strip() if following_index is not None else ""
        gap_empty = (following_index is None or not text[offsets[index] + len(raw_lines[index]):offsets[following_index]].strip())
        if not gap_empty:
            continue
        label = policy.v1.normalize_heading(value)
        if label in LEAF_PAIRS and policy.v1.normalize_heading(following) in LEAF_PAIRS[label]:
            add(index, "EMPTY_KNOWN_LEAF_BEFORE_ITS_ACTUAL_SIBLING")
        family = records.FAMILY.fullmatch(value)
        family_label = re.split(r"[:：]", value, 1)[0].strip() if family else ""
        next_family = records.ANY_FAMILY.match(following) if following else None
        same_indent = (following_index is None or
                       re.match(r"[ \t]*", raw_lines[index])[0] == re.match(r"[ \t]*", raw_lines[following_index])[0])
        if (family and family_label not in GROUP_FAMILY and "<" not in raw_lines[index]
                and same_indent and (following_index is None or next_family)):
            add(index, "EMPTY_SINGLE_PERSON_FAMILY_VALUE_NO_NAME_INFERRED")
        if (metadata_proven and records.LIST_SOURCE.fullmatch(value) and STAFF.search(value)
                and (records.YEAR.fullmatch(following) or records.CATEGORY.fullmatch(following))):
            add(index, "ANNOUNCED_CREDIT_LIST_HAS_NO_ACTUAL_ENTRIES_BEFORE_PROVED_METADATA")
            if position:
                before = entries[position - 1]
                between = text[offsets[before] + len(raw_lines[before]):offsets[index]]
                if policy.v1.normalize_heading(lines[before]) in CREDIT_HEADINGS and not between.strip():
                    add(before, "EMPTY_CREDIT_HEADING_WITH_THE_SAME_UNFILLED_LIST_POINTER")
    changes = [removed[index] for index in sorted(removed)]
    clean = text
    for change in reversed(changes):
        lo, hi = change["source_characters"]
        assert clean[lo:hi] == change["original"]
        clean = clean[:lo] + clean[hi:]
    return clean, changes
