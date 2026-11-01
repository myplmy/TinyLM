#!/usr/bin/env python3
"""Observed typed metadata, named resources and distinct section repetition.

No category word, resource name, year or contextual repeat is deleted. Unknown
tails and actual missing values still need source-specific authored recovery.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v10 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V11_TYPED_TAIL_AND_DISTINCT_SECTION_CONTEXT"
v9 = previous.previous
v8 = v9.previous
v7 = v8.previous
v4, v2, v1 = previous.v4, previous.v2, previous.v1
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
contextual_repetitions = previous.contextual_repetitions
MISSING_DECLARATION = previous.MISSING_DECLARATION
ORIGINAL_REFERENCES = v7.real_references
ORIGINAL_REPETITION = v7.structured_repetition
EXTRA_APPENDICES = {v1.normalize_heading(value) for value in ["참고", "출처주", "내용주"]}
CATEGORY = re.compile(v7.CATEGORY.pattern.replace(r"\s", r"[\s_]") +
    r"|(?:[가-힣]+어[ _]+가수|.+의[ _]+(?:피겨스케이팅[ _]*선수|심판|여성주의[ _]*단체|"
    r"대통령[ _]*소속[ _]*자문위원회|자문위원회|인물[ _]*박물관|미술관|자선가|억만장자|"
    r"무슬림|로마[ _]*가톨릭교도|소설가|사회[ _]*운동가|아동문학[ _]*작가|천도교[ _]*교역자)|"
    r"(?:국립|도립|시립|군립|공립|사립)병원|병원|축구인|친일단체|"
    r".+[ _]+(?:자치구|자치주)|.+훈장[ _]+수훈자|.+포장[ _]+수훈자|"
    r".+가[ _]+프로듀싱한[ _]+음반|.+(?:세기|에서)[ _]+(?:.+에[ _]+)?거주한[ _]+.+인|"
    r".+(?:권리|인권)[ _]+운동가)")
YEAR = re.compile(v7.YEAR.pattern +
    r"|[12][0-9]{3}년[ _]*(?:설립|해체|해산|폐지|완공|개관|창립|창단)(?:된|한)[ _]*"
    r"(?:단체|기관|기구|정당|학교|도서관|병원|기업|건축물|스포츠[ _]*시설)")
REFERENCE_HEADINGS = {v1.normalize_heading(value) for value in ["외부 링크", "external links", "참고 문헌", "참고자료", "참고"]}
NAMED_RESOURCE = re.compile(r"(?:Daum[ _]+영화|디즈니[ _]+레전드|국제[^.!?。\n]{1,70}연맹|"
                            r"축구[ _]+뉴스그룹[ _]+통계[ _]+협회)", re.I)
SECTION_CONTEXT = {v1.normalize_heading(value) for value in [
    "요약", "정리", "학력", "수상 경력", "저서", "저작", "작품", "작품 목록", "주요 논문",
    "연혁", "지리", "인구", "행정구역", "교통", "철도", "도로", "운행", "운행편",
    "선수", "국가대표팀", "클럽 경력", "기록", "통계", "분포", "역할", "효과", "원리",
    "summary", "overview", "introduction", "things to remember", "structure", "applications",
    "remarks", "examples", "references", "see also", "background"]}


def real_references(text):
    if ORIGINAL_REFERENCES(text):
        return True
    active = False
    for line in text.splitlines():
        label = v1.normalize_heading(line)
        if label in REFERENCE_HEADINGS:
            active = True
        elif label in v4.APPENDICES or YEAR.fullmatch(line.strip()):
            active = False
        elif active and NAMED_RESOURCE.fullmatch(line.strip()):
            return True
    return False


def distinct_sections(text):
    if ORIGINAL_REPETITION(text):
        return True
    plain = "".join(part for protected, part in v1.protected_parts(text)[0] if not protected)
    lines = [line.strip() for line in plain.splitlines() if line.strip()]
    frequency = Counter(line for line in lines if len(line) >= 6)
    contexts, seen_sections = defaultdict(list), set()
    context = "ARTICLE_INTRO"
    for line in lines:
        label = v1.normalize_heading(line)
        if label in SECTION_CONTEXT | v7.SECTION_CONTEXT:
            context = "SECTION:" + label
            seen_sections.add(context)
        elif label in v4.APPENDICES:
            context = "APPENDIX:" + label
        if len(line) >= 6 and label not in v4.LABELS | SECTION_CONTEXT | v7.SECTION_CONTEXT:
            contexts[line].append(context)
    repeated = [values for line, values in contexts.items() if frequency[line] > 1]
    # A line duplicated within one section is not released by an unrelated
    # heading elsewhere. Every repeated line needs distinct source contexts.
    return bool(repeated) and bool(seen_sections) and all(len(set(values)) == len(values) for values in repeated)


def propose(row, individual_hold=False):
    with v2.v2.LOCK, patch.object(v7, "CATEGORY", CATEGORY), patch.object(v7, "YEAR", YEAR), \
            patch.object(v7, "EXTRA_APPENDICES", v7.EXTRA_APPENDICES | EXTRA_APPENDICES), \
            patch.object(v7, "EXTRA_LABELS", v7.EXTRA_LABELS | EXTRA_APPENDICES), \
            patch.object(v7, "real_references", real_references), \
            patch.object(v7, "structured_repetition", distinct_sections), \
            patch.object(v8, "ORIGINAL_REPETITION", distinct_sections):
        return dict(previous.propose(row, individual_hold), rules=RULES)
