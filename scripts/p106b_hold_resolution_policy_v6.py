#!/usr/bin/env python3
"""Local nominal aliases and actual named references with literal call guards.

Every filled field stays literal. Empty names can be optional aliases only in
an identified Korean article/list and outside mathematical/value contexts.
Unknown quantities, book titles, former names and inherited holds stay pending.
"""
from __future__ import annotations

import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v5 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V6_LOCAL_NOMINAL_FIELDS"
v4 = previous.previous
v2 = v4.v2
v1 = v4.v1
ORIGINAL_NAME_SLOTS = v4.name_slots
ORIGINAL_REFERENCES = v4.real_references
ORIGINAL_CALLS = v2.ordinary_empty_calls
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
contextual_repetitions = previous.contextual_repetitions
NOMINAL_GROUP = re.compile(r"(?<=[가-힣A-Za-z0-9》〉」』‘’“”'\"])[ \t]*\(([^()\n]*)\)")
MATH_CONTEXT = re.compile(
    r"수식|방정식|임의의|계수|행렬|벡터|미분|적분|플랑크\s*상수|진동수|운동량|"
    r"매개변수|독립\s*변수|종속\s*변수|변숫값|함숫값|함수|연산자|정의역|공역|치역|"
    r"국제음성|IPA|\b(?:equation|parameter|argument|tuple|matrix|formula)\b|[=∈∉∑∫∀∃]", re.I)
EMPTY_VALUE_NAME = re.compile(r"(?:이름|성명|기호|값|계수|변수|수량|수도|출생|사망|길이|높이|무게|질량|"
                              r"인구|면적|효율|날짜|각도|경도|위도|합계|순위|용량|주파수|광속|"
                              r"배우자|출연|수록곡|그림|도표|아래|다음|표기)\s*$")
KOREAN_LIST_INTRO = re.compile(r"(?:다음\s*뜻으로\s*쓰인다|다음(?:과\s*같은)?\s*(?:뜻|의미)(?:이|가)?\s*있다)")
REFERENCE_RECORD = re.compile(r"\S[^\n]*\s[-–—]\s\S|Taekwondo Data|Olympedia|Sports Reference|"
                              r"국제\s*스키\s*연맹|KBS|MBC|SBS|경향신문|BBC|Ning|"
                              r"[a-z0-9-]+[.](?:pl|com|org|net)\b|블로그|팬카페|신문|"
                              r"(?:역사|총재|경기장|엽서)\s*소개|학교법인|도서관|일본\s*기원", re.I)
CALL_CONTEXT = re.compile(v2.PROGRAMMING.pattern + r"|\b(?:function|functions|calling|calls|invoke|constructor|IPython|sprintf|"
                          r"ImageMagick|RectangleGeometry|MathJax|Lisp|C\+\+|C#)\b|함수\s*(?:호출|이름)",re.I)
CALL_BEFORE = re.compile(r"[A-Za-z_][A-Za-z0-9_.:]*$")


def identified(text):
    return v4.intro(text) is not None or bool(KOREAN_LIST_INTRO.search(text.split(chr(10)+chr(10),1)[0]))


def nominal_context(part, match):
    left = part[max(0,match.start()-256):match.start()]
    token = re.search(r"([가-힣A-Za-z0-9][가-힣A-Za-z0-9_·ㆍ-]*)[》〉」』‘’“”'\"]?\s*$", left)
    if not token:
        return False
    # ASCII names need an explicit Korean article particle immediately after
    # the parenthesis; an English call can never become an alias deletion.
    if not re.search(r"[가-힣]",token[1]) and not re.match(r"\s*(?:은|는|이|가|의|란|라고)",part[match.end():]):
        return False
    if EMPTY_VALUE_NAME.search(token[1]):
        return False
    return True


def name_slots(text):
    # Apply the local value/symbol guard before any older alias transform.
    # Calling V4 first would erase the evidence needed to reject a missing
    # population value or physical symbol in a nontechnical-looking article.
    changes = []
    if not identified(text):
        return text, changes
    output = []
    for protected, part in v1.protected_parts(text)[0]:
        if protected:
            output.append(part)
            continue
        paragraphs = re.split(r"(\n[ \t]*\n)",part)
        for index in range(0,len(paragraphs),2):
            paragraph = paragraphs[index]
            # Check each complete paragraph once; large name lists must not
            # repeatedly scan/copy their entire prefix for every parenthesis.
            if MATH_CONTEXT.search(paragraph) or v2.PROGRAMMING.search(paragraph):
                continue
            def replace(match):
                if not nominal_context(paragraph,match):
                    return match[0]
                content = match[1]
                if "←" in content or re.search(r"[=+*/<>\\{}\[\]]",content):
                    return match[0]
                pieces = v4.DELIMITERS.split(content)
                fields = [(j,pieces[j]) for j in range(0,len(pieces),2)]
                filled = [(j,value) for j,value in fields if value.strip()]
                if len(filled)==len(fields):
                    return match[0]
                # Numerical tuple holes cannot be mistaken for alias/date slots.
                if any(re.search(r"[0-9]",value) and not re.search(r"[0-9](?:년|月|年)",value)
                       and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_. -]*",value.strip()) for _,value in filled):
                    return match[0]
                if filled:
                    retained = filled[0][1].strip()
                    for (prior,_),(j,value) in zip(filled,filled[1:]):
                        retained += pieces[prior+1]+value
                    replacement = "("+retained.rstrip()+")"
                else:
                    replacement = ""
                changes.append(dict(reason="IDENTIFIED_NOMINAL_CONTEXT_REMOVE_ONLY_EMPTY_OPTIONAL_FIELDS",
                                    original=match[0],replacement=replacement))
                return replacement
            paragraphs[index] = NOMINAL_GROUP.sub(replace,paragraph)
        output.append("".join(paragraphs))
    return "".join(output),changes


def empty_reference_slots(text):
    lines = text.splitlines(keepends=True)
    appendix = False
    changes = []
    output = []
    blocks,_ = v1.real_code_blocks(text)
    offset = 0
    # Only an actually empty reference record is removed. A complete label,
    # value, code line or standalone mathematical tuple is never this case.
    for index,line in enumerate(lines):
        label = v1.normalize_heading(line)
        if label in v4.APPENDICES:
            appendix = True
        protected = any(lo <= offset < hi for lo,hi,_ in blocks)
        empty = appendix and not protected and re.fullmatch(r"[ \t]*\([ \t]*\)[ \t]*(?:\r?\n)?",line)
        metadata_tail = False
        if empty:
            tail = [item.strip() for item in lines[index+1:] if item.strip()]
            metadata_tail = all(v4.v2.METADATA_YEAR.fullmatch(item) or v4.CATEGORY_LINE.fullmatch(item)
                                or v1.normalize_heading(item) in v4.LABELS or len(item)<70 and
                                not re.search(r"[.!?。()=]",item) for item in tail)
        if empty and metadata_tail:
            changes.append(dict(reason="EMPTY_REFERENCE_RECORD_WITH_NO_NAME_OR_VALUE",original=line))
        else:
            output.append(line)
        offset += len(line)
    return "".join(output),changes


def real_references(text):
    if ORIGINAL_REFERENCES(text):
        return True
    appendix = False
    for line in text.splitlines():
        if v1.normalize_heading(line) in v4.APPENDICES:
            appendix = True
        elif appendix and REFERENCE_RECORD.search(line):
            return True
    return False


def ordinary_empty_calls(text):
    if ORIGINAL_CALLS(text):
        return True
    plain = "".join(part for protected,part in v1.protected_parts(text)[0] if not protected)
    if not CALL_CONTEXT.search(plain) or v1.DANGLING_FIELD.search(plain):
        return False
    hits = list(v1.cache.MISSING_FIELD.finditer(plain))
    return bool(hits) and all(re.fullmatch(r"\(\s*\)",m[0]) and CALL_BEFORE.search(plain[:m.start()]) for m in hits)


def propose(row,individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"]=="validation:0":
        return dict(previous.propose(row,individual_hold),rules=RULES)
    prepared,changes = empty_reference_slots(original)
    with v2.v2.LOCK,patch.object(v4,"name_slots",name_slots),patch.object(v4,"real_references",real_references),\
            patch.object(v2,"ordinary_empty_calls",ordinary_empty_calls):
        result = previous.propose(dict(row,text=prepared),False)
    candidate = result.get("candidate",result["text"])
    if not code_preserved(original,candidate) or not unicode_examples_preserved(original,candidate):
        reasons = sorted(set(result.get("reasons",[]))|{"CODE_OR_UNICODE_GUARD"})
        return dict(decision="PENDING",text=original,candidate=candidate,reasons=reasons,
                    changes=changes+result["changes"],rules=RULES)
    if result["decision"]=="PENDING":
        return dict(result,text=original,changes=changes+result["changes"],rules=RULES)
    return dict(result,decision="EDIT" if candidate!=original else "KEEP",text=candidate,
                changes=changes+result["changes"],rules=RULES)
