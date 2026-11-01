#!/usr/bin/env python3
"""Retain named references and repeats with distinct source section contexts."""
from __future__ import annotations

from collections import Counter, defaultdict
import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v6 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V7_TYPED_METADATA_AND_REFERENCE"
v4, v2, v1, v5 = previous.v4, previous.v2, previous.v1, previous.previous
ORIGINAL_INTRO = v4.intro
ORIGINAL_REFERENCES = previous.real_references
ORIGINAL_METADATA = v5.metadata_tail
ORIGINAL_SECTIONS = v4.empty_sections
ORIGINAL_REPETITION = v2.structured_repetition
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
contextual_repetitions = previous.contextual_repetitions
EXTRA_APPENDICES = {v1.normalize_heading(x) for x in ["참고주", "내용주", "인용주", "참고 자료"]}
EXTRA_LABELS = {v1.normalize_heading(x) for x in ["제작참여", "제작 참여", "역대 우승자", "역대 우승팀", "참고주", "내용주"]}
CATEGORY = re.compile(v4.CATEGORY_LINE.pattern + r"|(?:.+의\s+(?:정치\s+작가|정치철학자|정치학자|정치\s+평론가|경제학자|사회학자|과학자|교수|교육인|관료|기업인|문신|변호사|독립운동가|카투니스트|성우|수필가|소설가|도서관|기업)|[가-힣]+\s+[가-힣]+씨|과거\s*급제자|개봉\s*예정\s*영화|리부트\s*영화|로드\s*무비|.+(?:의\s+|에서\s*촬영한\s*|를\s*소재로\s*한\s*|을\s*소재로\s*한\s*|를\s*배경으로\s*한\s*|을\s*배경으로\s*한\s*)[^.!?。]*영화|.+상\s*수상작)")
YEAR = re.compile(v2.METADATA_YEAR.pattern + r"|[12][0-9]{3}년\s*(?:설립된\s*(?:기업|단체|기관|정당|학교|도서관|스포츠 리그)|완공된\s*(?:스포츠 시설|건축물)|개관한\s*도서관)")
BIOGRAPHICAL = re.compile(r"교육인|기업인|관료|문신|정치인|독립운동가|총독|대통령|학자|교수|선수|가수|배우|작가")
PAST_PREDICATE = re.compile(r"지냈다[.!?。]?$|역임했다[.!?。]?$|재직했다[.!?。]?$|활동했다[.!?。]?$", re.M)
REFERENCE_SUFFIX = re.compile(r"^(?:[-–—]\s+\S|.*(?:공식|프로필|연구소|자료|학회|소개|웹사이트|홈페이지|박물관|도서관))")
SECTION_CONTEXT = {v1.normalize_heading(x) for x in ["구조", "발생", "기능", "분류", "역사", "생애", "경력", "활동", "수상", "증상", "변이", "원인", "검사", "손상", "개요", "정의", "성질", "예시", "예제", "응용", "차트 성적", "미디어에서의 사용"]}
CITY = re.compile(r"도시|시정촌|마을|자치체|행정구역|지명")
CITY_SIBLINGS = {v1.normalize_heading(x) for x in ["인구", "기후", "자매 도시", "연혁", "지리", "역사", "행정구역", "경제", "교통", "교육"]}
REFERENCE_CHILDREN = {v1.normalize_heading(x) for x in ["책", "단행본", "논문", "웹", "서적", "저널"]}


def intro(text):
    found = ORIGINAL_INTRO(text)
    if found is not None:
        return found
    for match in v4.v3.PARAGRAPH.finditer(text):
        paragraph = match[0].strip()
        if v4.v3.SUBJECT.search(paragraph) and BIOGRAPHICAL.search(paragraph) and PAST_PREDICATE.search(paragraph):
            return paragraph
        if chr(10) in paragraph or re.search(r"[.!?。]$", paragraph):
            break
    return None


def topic_name(text):
    first = intro(text)
    subject = v4.v3.SUBJECT.search(first) if first else None
    if not subject:
        return None
    return first[:subject.start()].split("(", 1)[0].strip("《》〈〉‘’“”'\" ") or None


def real_references(text):
    if ORIGINAL_REFERENCES(text):
        return True
    topic = topic_name(text)
    active = False
    for line in text.splitlines():
        label = v1.normalize_heading(line)
        if label in v4.APPENDICES:
            active = True
            continue
        value = line.strip()
        if active and value:
            if re.match(r"^[-–—]\s+\S", value):
                return True
            if topic and (value == topic or value.startswith(topic + " ") and REFERENCE_SUFFIX.search(value[len(topic):].lstrip())):
                return True
    return False


def metadata_tail(text):
    if real_references(text):
        return text, [], False
    return ORIGINAL_METADATA(text)


def empty_sections(text):
    text, changes = ORIGINAL_SECTIONS(text)
    lines = text.splitlines(keepends=True)
    entries = [i for i, line in enumerate(lines) if line.strip()]
    blocks, _ = v1.real_code_blocks(text)
    offsets, position = [], 0
    for line in lines:
        offsets.append(position)
        position += len(line)
    protected = {i for i in entries if any(lo <= offsets[i] < hi for lo, hi, _ in blocks)}
    remove, parent = set(), None
    city = bool(intro(text) and CITY.search(intro(text)))
    for n, index in enumerate(entries):
        if index in protected:
            continue
        label = v1.normalize_heading(lines[index])
        following = v1.normalize_heading(lines[entries[n + 1]]) if n + 1 < len(entries) else None
        if label in v4.APPENDICES:
            parent = label
        if parent in {v1.normalize_heading("참고 문헌"), v1.normalize_heading("참고자료")} and label in REFERENCE_CHILDREN and (following is None or following in v4.APPENDICES):
            remove.add(index)
        if city and parent is None and label in {v1.normalize_heading("인구"), v1.normalize_heading("기후")} and following in CITY_SIBLINGS:
            remove.add(index)
    changes.extend(dict(reason="EMPTY_TYPED_SIBLING_OR_REFERENCE_CHILD", line=i + 1, original=lines[i]) for i in sorted(remove))
    return "".join(line for i, line in enumerate(lines) if i not in remove), changes


def structured_repetition(text):
    if ORIGINAL_REPETITION(text):
        return True
    if intro(text) is None:
        return False
    plain = "".join(part for protected, part in v1.protected_parts(text)[0] if not protected)
    lines = [line.strip() for line in plain.splitlines() if line.strip()]
    frequency, contexts, context = Counter(lines), defaultdict(list), "ARTICLE_INTRO"
    for line in lines:
        label = v1.normalize_heading(line)
        if label in SECTION_CONTEXT:
            context = "SECTION:" + label
        if len(line) >= 6 and label not in v4.LABELS | SECTION_CONTEXT:
            contexts[line].append(context)
    repeated = [values for line, values in contexts.items() if frequency[line] > 1]
    return bool(repeated) and all(all(values) and len(set(values)) == len(values) for values in repeated)


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    with v2.v2.LOCK, patch.object(v4, "intro", intro), patch.object(v4, "CATEGORY_LINE", CATEGORY), \
            patch.object(v2, "METADATA_YEAR", YEAR), patch.object(previous, "real_references", real_references), \
            patch.object(v5, "metadata_tail", metadata_tail), patch.object(v4, "empty_sections", empty_sections), \
            patch.object(v2, "structured_repetition", structured_repetition), \
            patch.object(v4, "LABELS", v4.LABELS | EXTRA_LABELS), \
            patch.object(v4, "APPENDICES", v4.APPENDICES | EXTRA_APPENDICES), \
            patch.object(v4, "STRIPPABLE_APPENDICES", v4.STRIPPABLE_APPENDICES | EXTRA_APPENDICES):
        result = previous.propose(row, False)
    return dict(result, rules=RULES)
