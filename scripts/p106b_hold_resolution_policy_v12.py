#!/usr/bin/env python3
"""Observed source metadata and first-subject optional aliases, preserving values.

No missing quantity, date, former name, formula or source title is supplied.
All inherited individual decisions and literal protections remain in force.
"""
from __future__ import annotations

import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v11 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V12_NAMED_SOURCE_AND_NOMINAL_INTRO"
v10 = previous.previous
v9 = v10.previous
v8 = v9.previous
v7 = v8.previous
v6, v4, v2, v1 = previous.v4.v2, previous.v4, previous.v2, previous.v1
BASE_INTRO = v4.intro
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
contextual_repetitions = previous.contextual_repetitions
MISSING_DECLARATION = previous.MISSING_DECLARATION
ENTITY = re.compile(v4.ENTITY.pattern +
    r"|(?:경찰서|버스\s*회사|컴퓨터\s*과학자|화학자|발명가|술탄|문헌|시대|기간|도서|책)"
    r"(?:이[다자며]|이었다|였다|다[.!?。]|로[ ,]|[,.])")
CATEGORY = re.compile(previous.CATEGORY.pattern +
    r"|(?:생년[ _]*미상|몰년[ _]*미상|병사한[ _]*사람|음서|과거[ _]*급제자|"
    r".+의[ _]+(?:없어진[ _]+)?경찰서|"
    r".+의[ _]+(?:남자[ _]+|여자[ _]+)?(?:연극[ _]*배우|뮤지컬[ _]*배우|"
    r"대학[ _]*교수|전자[ _]*음악가|음악가|성소수자[ _]*인물|방송인|"
    r"시인|작곡가|작사가|저술가|목회자|텔레비전[ _]*드라마[ _]*감독|"
    r"개신교도|불교도|장로교도|무신|왕족|동)|"
    r".+의[ _]+(?:(?:시내|농어촌|시외|고속|마을)버스[ _]*)?(?:기업|교통)|"
    r".+의[ _]+폐지된[ _]+(?:선거구|행정[ _]*구역)|"
    r"[12][0-9]{3}년[ _]+(?:신설된|폐지된)[ _]+대한민국[ _]+선거구|"
    r"[12][0-9]{3}년대[ _]+가수|한국어[ _]+EP|게이[ _]+음악가|"
    r"U-21[ _]+축구|.+의[ _]+축구상)")
YEAR = re.compile(previous.YEAR.pattern + r"|[12][0-9]{3}년[ _]+(?:설치|신설)")
NAMED_RESOURCE = re.compile(previous.NAMED_RESOURCE.pattern +
    r"|(?:playDB[ _]+인물정보|중앙선거관리위원회[ _]+선거통계시스템|"
    r"통일연구원,[ _]+[12][0-9]{3}[ _]+북한[ _]+기관별[ _]+주요[ _]+인물정보|"
    r"국제[ _]+탁구[ _]+연맹[ _]+기록)", re.I)
DEFINED_SUBJECT = re.compile(r"(?:은|는|란)\s+")
NARRATIVE_DEFINITION = re.compile(r"기간을\s*말한다[.!?。]?$|시기를\s*말한다[.!?。]?$|문헌으로,|문헌이다[.!?。]?$", re.M)
INTRO_NAME = re.compile(
    r"\A(?P<name>[ \t]*[가-힣A-Za-z0-9《》〈〉·ㆍ'’\" -]+)\((?P<fields>[^()\n]*)\)"
    r"(?P<particle>[ \t]*(?:은|는|란)\s+)")
VALUE_NAME = re.compile(r"(?:함수|식|공식|기호|값|계수|변수|수량|인구|면적|효율|"
                        r"길이|높이|무게|질량|날짜|각도|경도|위도|합계|순위|용량|주파수|광속)[ \t]*$")
BIOGRAPHIC_ROLE = re.compile(r"(?:과학자|학자|발명가|배우|가수|작가|정치인|술탄|국왕|군주|군인|선수)")


def intro(text):
    found = BASE_INTRO(text)
    if found is not None:
        return found
    for match in v4.v3.PARAGRAPH.finditer(text):
        paragraph = match[0].strip()
        subject = DEFINED_SUBJECT.search(paragraph)
        if subject and paragraph[:subject.start()].strip() and NARRATIVE_DEFINITION.search(paragraph):
            return paragraph
        if chr(10) in paragraph or re.search(r"[.!?。]$", paragraph):
            break
    return None


def initial_optional_alias(text):
    first = intro(text)
    if first is None:
        return text, []
    match = INTRO_NAME.match(text)
    if match is None or VALUE_NAME.search(match["name"]) or v9.MATH_CONTEXT.search(first):
        return text, []
    # A computer scientist's prose can name programming without becoming a
    # function call. It needs an actual personal role and source birth date.
    biography = bool(BIOGRAPHIC_ROLE.search(first) and re.search(r"[12][0-9]{3}년", match["fields"]))
    if v2.PROGRAMMING.search(first) and not biography:
        return text, []
    fields = match["fields"]
    if "←" in fields or re.search(r"[=+*<>\\{}\[\]]", fields):
        return text, []
    pieces = v4.DELIMITERS.split(fields)
    filled = [(index, value) for index, value in enumerate(pieces) if index % 2 == 0 and value.strip()]
    if len(filled) == (len(pieces) + 1) // 2:
        return text, []
    if re.search(r"[0-9/~～∼]", fields) and not biography:
        return text, []
    if not filled:
        replacement = ""
    else:
        retained = filled[0][1].strip()
        for (prior, _), (_, value) in zip(filled, filled[1:]):
            retained += pieces[prior + 1] + value
        replacement = "(" + retained.rstrip() + ")"
    lo, hi = match.start("fields") - 1, match.end("fields") + 1
    result = text[:lo] + replacement + text[hi:]
    return result, [dict(reason="FIRST_IDENTIFIED_NOMINAL_EMPTY_OPTIONAL_FIELDS_ONLY", original=text[lo:hi], replacement=replacement)]


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    with v2.v2.LOCK, patch.object(v4, "ENTITY", ENTITY), patch.object(v7, "ORIGINAL_INTRO", intro), \
            patch.object(previous, "CATEGORY", CATEGORY), patch.object(previous, "YEAR", YEAR), \
            patch.object(previous, "NAMED_RESOURCE", NAMED_RESOURCE):
        prepared, changes = initial_optional_alias(original)
        result = previous.propose(dict(row, text=prepared), False)
    final = result.get("candidate", result["text"])
    risks = set(result["reasons"]) if result["decision"] == "PENDING" else set()
    if not code_preserved(original, final) or not unicode_examples_preserved(original, final):
        risks.add("CODE_OR_UNICODE_GUARD")
    changes += result["changes"]
    if risks:
        return dict(decision="PENDING", text=original, candidate=final, reasons=sorted(risks), changes=changes, rules=RULES)
    return dict(decision="EDIT" if final != original else "KEEP", text=final,
                reasons=["NAMED_SOURCE_AND_LITERAL_NOMINAL_DEFINITION_PRESERVED"], changes=changes, rules=RULES)
