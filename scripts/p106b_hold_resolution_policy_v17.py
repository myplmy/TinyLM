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
QUARANTINE = previous.QUARANTINE
YEAR, CATEGORY, BLOCK = previous.YEAR, previous.CATEGORY, previous.BLOCK
intro = previous.intro
ENTITY = re.compile(v12.ENTITY.pattern.replace("로[ ,]", "(?:으)?로[ ,]") +
                    r"|(?:정당|정치[ ]*연합|음악[ ]*그룹|비디오[ ]*게임|텔레비전[ ]*프로그램)"
                    r"(?:이[다자며]|이었다|였다|다[.!?。]|(?:으)?로[ ,]|[,.])")
LABEL = re.compile(r"[가-힣A-Za-z0-9 _()/·-]+")
EMPTY_LEAF_LABELS = {v1.normalize_heading(value) for value in [
    "역대 성적", "수록곡", "차트", "수록 곡 목록", "차트 성과", "주간 차트", "연말 차트"]}
FAMILY = re.compile(r"^[ \t]*(?:어머니|아버지|부모|배우자|부인|아내|남편|형|누나|언니|오빠|"
                    r"동생|남동생|여동생|장남|차남|삼남|장녀|차녀|삼녀|아들|딸|자녀|형제|자매)[ \t]*[:：][ \t]*$")
ANY_FAMILY = re.compile(r"^[ \t]*(?:어머니|아버지|부모|배우자|부인|아내|남편|형|누나|언니|오빠|"
                        r"동생|남동생|여동생|장남|차남|삼남|장녀|차녀|삼녀|아들|딸|자녀|형제|자매)[ \t]*[:：]")
DATE = re.compile(r"([12][0-9]{3})(?:년[ \t]*([0-9]{1,2})월[ \t]*([0-9]{1,2})일|"
                  r"[.]([0-9]{1,2})[.]([0-9]{1,2}))")
CALENDAR = re.compile(r"음력|양력|율리우스력|그레고리력|\bJulian\b|\bGregorian\b", re.I)
PERSON_ROLE = re.compile(v12.BIOGRAPHIC_ROLE.pattern + r"|기업인|사업가|성악가|탤런트")
MISSING_QUOTE = re.compile(r"(?:이렇게|다음과[ \t]*같이)[ \t]*(?:말(?:한다|했다|하였다)|"
                           r"이야기(?:한다|했다|하였다))[.:：]?[ \t]*\n[ \t]*\n[ \t]*"
                           r"(?:이|그)[ \t]*(?:말|이야기|발언|말씀|문장)(?:은|는|이|가|을|를)")
LIST_SOURCE = re.compile(r"이[ \t]*목록은[^\n]{0,180}(?:발췌|옮겼|가져왔다)[^\n]*")


def date_value(match):
    return int(match[1]), int(match[2] or match[4]), int(match[3] or match[5])


def life_date_differences(text):
    """Flag explicit conflicting dates; never choose or rewrite a source fact."""
    reasons = []
    first = text.lstrip().split(chr(10) * 2, 1)[0]
    start, depth, end = first.find("("), 0, None
    if start < 1 or not PERSON_ROLE.search(first):
        return reasons
    for index in range(start, len(first)):
        if first[index] == "(":
            depth += 1
        elif first[index] == ")":
            depth -= 1
            if not depth:
                end = index
                break
    if end is None or not re.match(r"[ \t]*(?:은|는|이란)[ \t]+", first[end + 1:]):
        return reasons
    fields = first[start + 1:end]
    if v14.TENURE.match(fields) or CALENDAR.search(fields):
        return reasons
    dates = list(DATE.finditer(fields))
    if not dates:
        return reasons
    marker = re.search(r"[~～∼–—]", fields)
    born = date_value(dates[0]) if not marker or dates[0].start() < marker.start() else None
    death = next((date_value(value) for value in dates if marker and value.start() > marker.start()), None)
    if born:
        for line in text.splitlines():
            if CALENDAR.search(line):
                continue
            explicit = re.match(r"[ \t]*(?:생년월일|출생일)(?:은|는|이|가|[:：])?[ \t]*", line)
            found = DATE.match(line, explicit.end()) if explicit else None
            if found and date_value(found) != born:
                reasons.append("DIFFERENT_EXPLICIT_BIRTH_DATES_REQUIRE_SOURCE_CONTEXT")
                break
    if death:
        for line in text.splitlines():
            if CALENDAR.search(line):
                continue
            found = DATE.match(line.lstrip())
            if not found:
                continue
            following = line.lstrip()[found.end():]
            verb = re.search(r"사망|타계|별세|죽었다", following)
            if verb and not DATE.search(following[:verb.start()]) and date_value(found) != death:
                reasons.append("DIFFERENT_EXPLICIT_DEATH_DATES_REQUIRE_SOURCE_CONTEXT")
                break
    return reasons


def literal_holes(text):
    plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                    for protected, part in v1.protected_parts(text)[0])
    reasons = set(previous.literal_holes(text))
    reasons.update(life_date_differences(plain))
    lines = [line for line in plain.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if FAMILY.fullmatch(line):
            following = lines[index + 1] if index + 1 < len(lines) else ""
            if not following or ANY_FAMILY.match(following) or v1.normalize_heading(following) in v4.LABELS:
                reasons.add("EMPTY_FAMILY_RELATION_VALUE_REQUIRES_SOURCE_CONTEXT")
        if (v1.normalize_heading(line) == v1.normalize_heading("수록 소프트") and index + 1 < len(lines)
                and v1.normalize_heading(lines[index + 1]) == v1.normalize_heading("기타")):
            reasons.add("UNFILLED_OPTIONAL_LEAF_SECTION_REQUIRES_SOURCE_CONTEXT")
        if (v1.normalize_heading(line) == v1.normalize_heading("줄거리") and index + 1 < len(lines)
                and v1.normalize_heading(lines[index + 1]) in {v1.normalize_heading("배역"), v1.normalize_heading("출연진")}):
            reasons.add("UNFILLED_PLOT_SECTION_BEFORE_POPULATED_CAST_REQUIRES_SOURCE_CONTEXT")
        if LIST_SOURCE.fullmatch(line.strip()) and index + 1 < len(lines):
            following = lines[index + 1].strip()
            if YEAR.fullmatch(following) or CATEGORY.fullmatch(following):
                reasons.add("ANNOUNCED_LIST_SOURCE_WITHOUT_LIST_BEFORE_METADATA")
    if MISSING_QUOTE.search(plain):
        reasons.add("MISSING_ANNOUNCED_QUOTATION_AND_EXPLICIT_DEPENDENT")
    if separate_metadata_suffix(text)[1]:
        reasons.add("PROVEN_EMPTY_FOOTER_REQUIRES_FRESH_BOUNDARY_CLEANUP")
    return sorted(reasons)


def separate_metadata_suffix(text):
    # Reuse the narrower v16 proof first. The new proof never edits values.
    old = previous.separate_metadata_suffix(text)
    if intro(text) is None:
        return old
    # Whitespace-only lines cannot hide an actually empty footer paragraph.
    blocks = [block for block in BLOCK.finditer(text) if block[0].strip()]
    if len(blocks) < 2:
        return old
    last = blocks[-1]
    values = [value.strip() for value in last[0].splitlines() if value.strip()]
    if (len(values) < 2 or any(len(value) > 100 or not re.search(r"[가-힣]", value)
                              or re.search(r"[.!?。《》\[\]<>`{}=]", value) for value in values)):
        return old
    years = [value for value in values if YEAR.fullmatch(value)]
    categories = [value for value in values if CATEGORY.fullmatch(value)]
    life_pair = (any(re.fullmatch(r"[12][0-9]{2,3}(?:년대|년)[ _]+출생", value) for value in years)
                 and any(re.fullmatch(r"[12][0-9]{2,3}년[ _]+사망|살아있는[ _]+사람", value) for value in years))
    if not old[2] and not life_pair and not (years and len(categories) >= 2):
        return text, [], False
    if not re.fullmatch(r"[ \t\r\n]+", text[blocks[-2].end():last.start()]):
        return text, [], False
    remove = []
    for block in reversed(blocks[:-1]):
        labels = [v1.normalize_heading(value) for value in block[0].splitlines() if value.strip()]
        if not labels or any(label not in v4.STRIPPABLE_APPENDICES | EMPTY_LEAF_LABELS for label in labels):
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
        candidate, added, proven = separate_metadata_suffix(clean)
        if proven:
            clean = candidate
            changes.extend(added)
            if not any(change["reason"] == QUARANTINE for change in changes):
                risks.discard("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT")
            elif "APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in risks:
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
