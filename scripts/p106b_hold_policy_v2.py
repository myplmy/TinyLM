#!/usr/bin/env python3
"""Recovery revision after independent full-scope proposal counterexamples.

Reuse v1's code/empty-field protections without changing its frozen source or
old results. Preserve every Unicode scalar, including compatibility ideographs
that are the subject of a character-code article. Only line endings outside
code may normalize. New guards quarantine observed ambiguous extraction; they
do not invent missing values, dates, formulas or category relationships.
"""
from __future__ import annotations

import re
import threading
from unittest.mock import patch

from scripts import p106b_hold_policy as v1

RULES="HOLD_INFORMATION_PRESERVING_RECOVERY_V2_UNICODE_LITERAL"
LOCK=threading.RLock()
EXTRA_LABELS={v1.normalize_heading(x) for x in {
    "방출 파장","이용 현황","출처","참고 자료","내용주","인용","문자표",
    "개별 문자에 대한 정보","Failure to register"}}
MORE_UI=re.compile(r"(?mi)^\s*(?:bookmark with\b|word visualiser\b|go and visit our forums\b|"
    r"find a translation\b|select another language\s*:|new\s*-\s*add dictionary search\b|"
    r"pope francis prayer intentions\b|more green news\b|"
    r"click the following link to bring up a new window\b|"
    r"this news release is available in\b)")
BROKEN_STUB=re.compile(r"(?mi)^\s*this\s+species\s+stub\s+needs\s*[.]?\s*$")
MISSING_QUANTITY=re.compile(r"(?i)\b(?:densities|pressures)\s*[–—-]\s*(?:cm|K)\b")
CATEGORY_HINT=re.compile(r"(?:^[12][0-9]{3}년\s*(?:출생|사망|음반|영화|설립|완공|폐지)|"
    r"살아있는 사람|(?:의|계)\s*(?:남자|여자)?\s*(?:영화|배우|축구|가수)|"
    r"(?:음반|영화 작품|경기장|출신 배우|축구 경기 시설|스포츠 시설)$)")


def literal_normalize(text):
    parts,opened=v1.protected_parts(text)
    return "".join(body if protected else body.replace("\r\n","\n").replace("\r","\n")
        for protected,body in parts),opened


def code_preserved(original,cleaned):
    return v1.code_preserved(original,cleaned)


def unicode_examples_preserved(original,cleaned):
    examples=re.findall(r"(?i)U\+[0-9A-F]{4,6}\s*[(（][^()（）\n]*[)）]",original)
    return all(cleaned.count(example)==original.count(example) for example in set(examples))


def appendix_category_ambiguity(plain):
    lines=[line.strip() for line in plain.splitlines() if line.strip()]
    for i,line in enumerate(lines):
        if v1.normalize_heading(line) not in v1.APPENDIX_LABELS:continue
        tail=lines[i+1:]
        if (tail and len(tail)<=24 and all(len(x)<=90 for x in tail)
                and not any(re.search(r"https?://|www[.]|ISBN|doi:|^[*-]",x,re.I) for x in tail)
                and any(CATEGORY_HINT.search(x) for x in tail)):
            return True
    return False


def conflicting_birth_year(plain):
    first=plain.split(chr(10)+chr(10),1)[0]
    born=re.search(r"\([^()\n]*?([12][0-9]{3})년\s*[0-9]{1,2}월\s*[0-9]{1,2}일",first)
    categories=re.findall(r"(?m)^\s*([12][0-9]{3})년\s*출생\s*$",plain)
    return bool(born and categories and any(x!=born[1] for x in categories))


def propose(row,event):
    original=row["text"];parts,_=v1.protected_parts(original);stub_changes=[];prepared=[]
    for protected,body in parts:
        if not protected:
            for line in body.splitlines(keepends=True):
                if BROKEN_STUB.fullmatch(line.strip()):
                    stub_changes.append(dict(reason="REMOVE_BROKEN_EMPTY_STUB_UI",text=line))
                else:prepared.append(line)
        else:prepared.append(body)
    draft=dict(row,text="".join(prepared))
    # The lock/temporary bindings isolate the frozen reusable engine. No file
    # or caller-owned mapping changes, and every binding is restored on failure.
    with LOCK,patch.object(v1,"normalize_outside_code",literal_normalize),\
            patch.object(v1,"LABELS",v1.LABELS|EXTRA_LABELS):
        result=v1.propose(draft,event)
    result=dict(result,rules=RULES,changes=stub_changes+result["changes"])
    if result["decision"]=="HOLD":
        result["text"]=original
        return result
    text=result["text"];plain="".join(s for protected,s in v1.protected_parts(text)[0] if not protected)
    risks=[]
    if MORE_UI.search(plain):risks.append("OBSERVED_PAGE_WIDGET_REQUIRES_CONTEXT_EDIT")
    if "]]" in plain or re.search(r"(?m)^\s*\|",plain):risks.append("UNRESOLVED_RAW_TABLE_OR_CLOSING_WIKI_MARKUP")
    if MISSING_QUANTITY.search(plain):risks.append("MISSING_QUANTITY_IN_SCIENTIFIC_STATEMENT")
    if appendix_category_ambiguity(plain):risks.append("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT")
    if conflicting_birth_year(plain):risks.append("INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED")
    if not unicode_examples_preserved(original,text):risks.append("UNICODE_CODEPOINT_EXAMPLE_CHANGED")
    if not code_preserved(original,text):risks.append("REAL_CODE_BYTES_CHANGED")
    if risks:return dict(decision="HOLD",text=original,reasons=risks,changes=result["changes"],rules=RULES)
    result["decision"]="EDIT" if text!=original else "KEEP"
    return result
