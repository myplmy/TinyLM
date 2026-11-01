#!/usr/bin/env python3
"""Conservative draft rules derived from source-linked text authoring.

Draft admission is not cache admission. Unknown fields, broken formulae,
individual HOLDs and incomplete code remain PENDING for further actual work.
Only empty identified-name shells and provably empty section labels change.
Normal category facts and contextual repetitions stay byte-for-byte intact.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re

from scripts import p106b_hold_policy_v3 as old

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V1"
v1 = old.v2.v1
v2 = old.v2
TECHNICAL_INTRO = re.compile(r"함수|수식|변수|연산|괄호|기호|코드|소스|프로그래밍|메서드|메소드|문법|U\+|\b(?:Python|Java|SQL)\b", re.I)
INTRO_PREDICATE = re.compile(r"(?:이다|이었다|였다|한다|있다)[.!?。]?(?:\s|$)")
EMPTY_NAME = re.compile(r"(?<=[가-힣》〉」』])\(\s*\)(?=(?:은|는|이|가|의|에|[》〉」』]))")
EMPTY_DATE_ALIAS = re.compile(r"\(\s*(?:[,，]\s*)+(?=[12][0-9]{3}년\s*[0-9]{1,2}월)")
YEAR_ANCHOR = re.compile(r"(?:[12][0-9]{3}년|\b[12][0-9]{3}\b|시즌\s*[0-9]+)")
STRUCTURE_ANCHOR = re.compile(r"출처\s*:|통계|차트|노선|취항|시즌|편제|캐스팅|출연|작품|기록|명단|^\s*[0-9]{1,2}월\s*[0-9]{1,2}일")
HARD_CATEGORY = re.compile(r"(?:[12][0-9]{3}년\s*(?:출생|사망|설립|폐지|해체|개업|음반|영화)|살아있는 사람)")
CATEGORY_FORM = re.compile(r"(?:.+의\s+.+|.+출신.*|.+동문|.+계\s*.+인|.+(?:영화|배우|음반|노래|소설|대학교|경기장|건축물|교통|정치인|단체|도시|자치체|문화재)|.+년\s*(?:출생|사망|설립|폐지|해체|개업)|살아있는 사람)")
LINK_OR_REFERENCE = re.compile(r"https?://|www[.]|ISBN|doi:|공식|홈페이지|사이트|인스타그램|트위터|페이스북|profile|website|database|^\s*[*-]", re.I)
CTA = re.compile(r"(?mi)^\s*(?:To get assessed to see what infection you may have, click here!|To order these tests, click here!|Click here to received more great information like this!)\s*$")


def identified_korean_intro(text):
    first = text.split(chr(10) + chr(10), 1)[0]
    return bool(re.search(r"[가-힣].*(?:은|는)", first) and INTRO_PREDICATE.search(first))


def intro_shells(text):
    first, separator, rest = text.partition(chr(10) + chr(10))
    if not identified_korean_intro(first):
        return text, []
    parts, opened = v1.protected_parts(first)
    if opened:
        return text, []
    changes = []
    result = []
    for protected, part in parts:
        if protected:
            result.append(part)
            continue
        fixed = part
        # Empty separators before an already present full birth/date field
        # contain no name or value. No date token or populated alias changes.
        fixed, date_count = EMPTY_DATE_ALIAS.subn("(", fixed)
        name_count = 0
        if not TECHNICAL_INTRO.search(first):
            fixed, name_count = EMPTY_NAME.subn("", fixed)
        if date_count or name_count:
            changes.append(dict(reason="IDENTIFIED_INTRO_EMPTY_ALIAS_SHELL", empty_dates=date_count,
                                empty_names=name_count, original=part, replacement=fixed))
        result.append(fixed)
    return "".join(result) + separator + rest, changes


def empty_ambiguous_sections(text):
    if not identified_korean_intro(text) or re.search(r"(?mi)^\s*(?:목차|table of contents)\s*$", text):
        return text, []
    lines = text.splitlines(keepends=True)
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    blocks, opened = v1.real_code_blocks(text)
    if opened:
        return text, []
    offsets = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)
    remove = set()
    appendix = False
    for position, index in enumerate(nonempty):
        label = v1.normalize_heading(lines[index])
        if label in v1.APPENDIX_LABELS:
            appendix = True
        if appendix or label not in v1.AMBIGUOUS_LABELS:
            continue
        if any(lo <= offsets[index] < hi for lo, hi, _ in blocks):
            continue
        separated = (index == 0 or not lines[index - 1].strip()) and (index + 1 == len(lines) or not lines[index + 1].strip())
        following_label = v1.normalize_heading(lines[nonempty[position + 1]]) if position + 1 < len(nonempty) else None
        if separated and (following_label is None or following_label in v1.LABELS | v2.EXTRA_LABELS):
            remove.add(index)
    changes = [dict(reason="EMPTY_IDENTIFIED_SECTION_WITH_NO_CONTENT", line=i + 1, original=lines[i]) for i in sorted(remove)]
    return "".join(line for i, line in enumerate(lines) if i not in remove), changes


def category_tail(text):
    """Prove a narrow metadata tail using two explicit category anchors.

    A single film/book-like title, actual link labels and bibliographic entries
    cannot establish this boundary. All category words survive unchanged.
    """
    if not identified_korean_intro(text):
        return text, [], False
    lines = text.splitlines(keepends=True)
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    tail = []
    for index in reversed(nonempty):
        value = lines[index].strip()
        if len(value) > 100 or LINK_OR_REFERENCE.search(value) or not CATEGORY_FORM.fullmatch(value):
            break
        tail.append(index)
    tail.reverse()
    if sum(bool(HARD_CATEGORY.fullmatch(lines[i].strip())) for i in tail) < 2:
        return text, [], False
    remove = set()
    start = nonempty.index(tail[0])
    for index in reversed(nonempty[:start]):
        if v1.normalize_heading(lines[index]) in old.FOOTERS:
            remove.add(index)
        else:
            break
    changes = [dict(reason="EMPTY_FOOTER_BEFORE_CONTEXT_PROVEN_CATEGORY_TAIL", line=i + 1, original=lines[i]) for i in sorted(remove)]
    return "".join(line for i, line in enumerate(lines) if i not in remove), changes, True


def contextual_repetitions(text):
    """Retain repeated values only when distinct explicit contexts anchor them."""
    plain = "".join(part for protected, part in v1.protected_parts(text)[0] if not protected)
    values = [line.strip() for line in plain.splitlines() if line.strip()]
    frequencies = Counter(values)
    positions = defaultdict(list)
    context = ""
    for value in values:
        if frequencies[value] == 1 and len(value) <= 100 and (YEAR_ANCHOR.search(value) or STRUCTURE_ANCHOR.search(value)):
            context = value
        if len(value) >= 6 and v1.normalize_heading(value) not in v1.LABELS:
            positions[value].append(context)
    repeated = {line: contexts for line, contexts in positions.items() if len(contexts) > 1}
    if not repeated:
        return False
    return all(all(contexts) and len(set(contexts)) == len(contexts) for contexts in repeated.values())


def propose(row, individual_hold=False):
    original = row["text"]
    if not row["complete_eos"] or row["id"] == "validation:0":
        return dict(decision="EXCLUDE", text=original, reasons=["UNRECOVERABLE_ORIGINAL_SPLIT_BOUNDARY"], changes=[], rules=RULES)
    if individual_hold:
        return dict(decision="PENDING", text=original, reasons=["INDIVIDUAL_SOURCE_REVIEW_NOT_YET_ADOPTED"], changes=[], rules=RULES)
    text, changes = intro_shells(original)
    text, removed = empty_ambiguous_sections(text)
    changes.extend(removed)
    text, removed, category_proven = category_tail(text)
    changes.extend(removed)
    text, removed = v1.remove_empty_labels(text)
    changes.extend(removed)
    result = old.propose(dict(row, text=text), dict(reasons=[], manual_hold=False))
    changes.extend(result["changes"])
    if result["decision"] == "HOLD":
        reasons = set(result["reasons"])
        if category_proven:
            reasons.discard("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT")
        if contextual_repetitions(text):
            reasons.discard("MAIN_BODY_REPETITION_REQUIRES_CONTEXT")
        if reasons:
            return dict(decision="PENDING", text=original, candidate=text, reasons=sorted(reasons), changes=changes, rules=RULES)
        final = text
    else:
        final = result["text"]
    plain = "".join(part for protected, part in v1.protected_parts(final)[0] if not protected)
    if CTA.search(plain):
        return dict(decision="PENDING", text=original, candidate=final, reasons=["OBSERVED_CTA_NEEDS_CONTEXT_EDIT"], changes=changes, rules=RULES)
    if not old.code_preserved(original, final) or not old.unicode_examples_preserved(original, final):
        return dict(decision="PENDING", text=original, candidate=final, reasons=["CODE_OR_UNICODE_GUARD"], changes=changes, rules=RULES)
    return dict(decision="EDIT" if final != original else "KEEP", text=final,
                reasons=["DRAFT_CONTEXT_LINKED_EMPTY_STRUCTURE_REPAIR"], changes=changes, rules=RULES)
