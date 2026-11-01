#!/usr/bin/env python3
"""Prove boundaries while retaining literal metadata and flat labelled fields."""
from __future__ import annotations

import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v16 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V17_LITERAL_METADATA_AND_FLAT_FIELDS"
v12, v10, v9, v4, v2, v1 = previous.v12, previous.v10, previous.v9, previous.v4, previous.v2, previous.v1
v14 = previous.previous.previous
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
semantic_style_preserved = previous.semantic_style_preserved
contextual_repetitions = previous.contextual_repetitions
MISSING_DECLARATION = previous.MISSING_DECLARATION
ordered_deletion = previous.ordered_deletion
conflicting_birth_year = previous.conflicting_birth_year
ORIGINAL_CONFLICT = previous.ORIGINAL_CONFLICT
initial_balanced_alias = previous.initial_balanced_alias
explicit_schedule_repetition = previous.explicit_schedule_repetition
quoted_nominal_aliases = previous.quoted_nominal_aliases
literal_holes = previous.literal_holes
QUARANTINE = previous.QUARANTINE
YEAR, CATEGORY, BLOCK = previous.YEAR, previous.CATEGORY, previous.BLOCK
intro = previous.intro
ENTITY = re.compile(v12.ENTITY.pattern.replace("로[ ,]", "(?:으)?로[ ,]") +
                    r"|(?:정당|정치[ ]*연합|음악[ ]*그룹|비디오[ ]*게임|텔레비전[ ]*프로그램)"
                    r"(?:이[다자며]|이었다|였다|다[.!?。]|(?:으)?로[ ,]|[,.])")
LABEL = re.compile(r"[가-힣A-Za-z0-9 _()/·-]+")


def separate_metadata_suffix(text):
    # Reuse the narrower v16 proof first. The new proof never edits values.
    old = previous.separate_metadata_suffix(text)
    if old[2] or intro(text) is None:
        return old
    blocks = list(BLOCK.finditer(text))
    if len(blocks) < 2:
        return text, [], False
    last = blocks[-1]
    values = [value.strip() for value in last[0].splitlines() if value.strip()]
    if (len(values) < 3 or any(len(value) > 100 or not re.search(r"[가-힣]", value)
                              or re.search(r"[.!?。《》\[\]<>`{}=]", value) for value in values)):
        return text, [], False
    years = [value for value in values if YEAR.fullmatch(value)]
    categories = [value for value in values if CATEGORY.fullmatch(value)]
    life_pair = (any(re.fullmatch(r"[12][0-9]{2,3}(?:년대|년)[ _]+출생", value) for value in years)
                 and any(re.fullmatch(r"[12][0-9]{2,3}년[ _]+사망|살아있는[ _]+사람", value) for value in years))
    if not life_pair and not (years and len(categories) >= 2):
        return text, [], False
    if not re.fullmatch(r"[ \t\r\n]+", text[blocks[-2].end():last.start()]):
        return text, [], False
    remove = []
    for block in reversed(blocks[:-1]):
        labels = [v1.normalize_heading(value) for value in block[0].splitlines() if value.strip()]
        if not labels or any(label not in v4.STRIPPABLE_APPENDICES for label in labels):
            break
        remove.append(block)
    clean, changes = text, []
    for block in remove:
        clean = clean[:block.start()] + clean[block.end():]
        changes.append(dict(reason="ISOLATED_EMPTY_FOOTER_BEFORE_MULTIPLE_EXPLICIT_METADATA_MARKERS",
                            original=block[0], source_characters=[block.start(), block.end()],
                            metadata_values_deleted=0))
    return clean, changes, True


def flat_labelled_prefix(text):
    source = text.lstrip()
    first = source.split(chr(10), 1)[0]
    if not first.startswith("{{") or not first[2:].strip().endswith("정보"):
        return None
    template = first[2:]
    if template != template.strip() or not LABEL.fullmatch(template):
        return None
    close = source.find("}}", len(first))
    if close < 0:
        return None
    labels = set()
    for line in source[len(first):close].splitlines():
        if not line.strip():
            continue
        value = line.lstrip()
        if not value.startswith("|") or value.count("|") != 1 or "=" not in value:
            return None
        label = value[1:].split("=", 1)[0].strip()
        if not label or not LABEL.fullmatch(label):
            return None
        labels.add(label)
    if "이름" not in labels:
        return None
    with v2.v2.LOCK, patch.object(v14, "TEMPLATE", template), patch.object(v14, "FIELD_NAMES", labels):
        result = v14.flat_football(text)
    if result is not None:
        result["change"] = dict(result["change"], reason="FLAT_NAMED_INFO_RECORDS_LITERAL_ORDER_NO_ARRAY_BINDING")
    return result


flat_football = previous.flat_football


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    with v2.v2.LOCK, patch.object(v12, "ENTITY", ENTITY), patch.object(v4, "ENTITY", ENTITY):
        flat = flat_labelled_prefix(original)
        prepared = flat["prefix"] + flat["suffix"] if flat is not None else original
        value = previous.propose(dict(row, text=prepared), False)
        clean = value.get("candidate", value["text"])
        changes = ([flat["change"]] if flat is not None else []) + value["changes"]
        risks = set(value["reasons"]) if value["decision"] == "PENDING" else set()
        if "APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in risks:
            candidate, added, proven = separate_metadata_suffix(clean)
            if proven and not any(change["reason"] == QUARANTINE for change in changes):
                clean = candidate
                changes.extend(added)
                risks.discard("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT")
            elif proven:
                risks.add("PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE")
    if flat is not None and any(value not in clean for value in flat["populated"]):
        risks.add("FLAT_POPULATED_FIELD_NOT_LITERAL_PRESERVED")
    risks.update(literal_holes(clean))
    if not code_preserved(original, clean) or not unicode_examples_preserved(original, clean):
        risks.add("CODE_OR_UNICODE_GUARD")
    if not semantic_style_preserved(original, clean):
        risks.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if not ordered_deletion(original, clean):
        risks.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
    if risks:
        return dict(decision="PENDING", text=original, candidate=clean, reasons=sorted(risks), changes=changes, rules=RULES)
    return dict(decision="EDIT" if clean != original else "KEEP", text=clean,
                reasons=["EXPLICIT_METADATA_AND_NAMED_LABEL_VALUES_LITERAL_PRESERVED"], changes=changes, rules=RULES)
