#!/usr/bin/env python3
"""Keep explicit category facts while removing an empty wiki footer label.

The full literal-Unicode and code guards of v2 remain in force. The new rule
applies only when at least two entire trailing lines each have a narrow explicit
category form. Actual reference citations, related-topic lists and URL-bearing
external-link entries are preserved. No category word or value is generated.
"""
from __future__ import annotations
import re
from scripts import p106b_hold_policy_v2 as v2

RULES="HOLD_INFORMATION_PRESERVING_RECOVERY_V3_EXPLICIT_CATEGORY_TAIL"
FOOTERS={"각주","주석","외부 링크","외부링크","external links"}
CATEGORY=re.compile(
    r"(?:[12][0-9]{3}년\s*(?:출생|사망|음반|영화|설립|폐지|해체|개업)|"
    r"[12][0-9]{3}년\s+.+(?:경기장|스포츠 시설)|"
    r"살아있는 사람|[가-힣]+어\s*음반|.+의\s*영화 작품|.+\s*감독 영화|야쿠자 영화|"
    r"[가-힣]+계\s*[가-힣]+인|.+출신\s*(?:배우|가수|축구 선수|야구 선수|인물|정치인)|"
    r".+의\s*(?:(?:남자|여자)\s*)?(?:텔레비전 배우|영화 배우|배우|가수|축구 선수|야구 선수|축구 경기 시설|경기장)|"
    r".+\s*프리미어리그 경기장)")


def strip_category_footers(text):
    lines=text.splitlines(keepends=True);nonempty=[i for i,line in enumerate(lines) if line.strip()]
    blocks,_=v2.v1.real_code_blocks(text);offsets=[];offset=0
    for line in lines:offsets.append(offset);offset+=len(line)
    remove=set()
    for pos,index in enumerate(nonempty):
        if v2.v1.normalize_heading(lines[index]) not in FOOTERS:continue
        if any(lo<=offsets[index]<hi for lo,hi,_ in blocks):continue
        end=pos+1
        while end<len(nonempty) and v2.v1.normalize_heading(lines[nonempty[end]]) in FOOTERS:end+=1
        tail=nonempty[end:]
        if not 2<=len(tail)<=24:continue
        if all(CATEGORY.fullmatch(lines[i].strip()) for i in tail):
            remove.update(nonempty[pos:end])
    changes=[dict(reason="EMPTY_WIKI_FOOTER_BEFORE_EXPLICIT_CATEGORY_LINES",line=i+1,text=lines[i]) for i in sorted(remove)]
    return "".join(line for i,line in enumerate(lines) if i not in remove),changes


def code_preserved(original,cleaned):return v2.code_preserved(original,cleaned)
def unicode_examples_preserved(original,cleaned):return v2.unicode_examples_preserved(original,cleaned)


def propose(row,event):
    original=row["text"];prepared,removed=strip_category_footers(original)
    result=v2.propose(dict(row,text=prepared),event)
    result=dict(result,rules=RULES,changes=removed+result["changes"])
    if result["decision"]=="HOLD":result["text"]=original
    else:result["decision"]="EDIT" if result["text"]!=original else "KEEP"
    return result
