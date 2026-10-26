#!/usr/bin/env python3
"""Draft, information-preserving HOLD recovery proposals, never a training gate.

Only empty labels/optional empty alias shells and existing empty tail headings
may change automatically. Real code, numbers, populated lists and citations are
preserved. Concrete missing fields, UI, broken extraction and inherited human
HOLD remain unresolved unless a separate source-SHA manual decision resolves it.
"""
from __future__ import annotations

from collections import Counter
import re
import unicodedata

from scripts import p106b_hold_recovery as inventory
from scripts import p106b_corpus_cleanup as corpus
from scripts import p106b_corpus_cache as cache
from scripts.p106b_native_text_audit import HEADINGS, normalize_heading, tail_proposal, signals
from scripts.p106b_source_cleanup import FENCE

RULES="HOLD_INFORMATION_PRESERVING_RECOVERY_V1_CANDIDATE"
EMPTY_LABELS=HEADINGS|inventory.EXTRA_SECTIONS|{
    "곡 목록","수록곡","트랙 목록","평가","인증","차트","곡","기년표","관련 기록",
    "방송 시간","시청률","방영 목록","진행자","유명 건축물","구청장","문화","탄생",
    "출생","사망","교통","역 구조","노선","운항 노선","기종","보유 기종",
    "경기 결과","라운드별 순위","최종 순위","승강장 배치","사진","참조"}
LABELS={normalize_heading(x) for x in EMPTY_LABELS}
AMBIGUOUS_LABELS={normalize_heading(x) for x in {
    "문화","교통","탄생","출생","사망","인구","기후","사진","갤러리","역 구조"}}
APPENDIX_LABELS={normalize_heading(x) for x in HEADINGS}
OPTIONAL_ALIAS=re.compile(r"(?<=[가-힣])\(\s*\)(?=[은는이가의에])")
KOREAN_INTRO=re.compile(r"[가-힣].*(?:은|는).*(?:이다[.!]|이었다[.!]|였다[.!]|한다[.!]|있다[.!])")
EMPTY_BIRTH_ALIAS=re.compile(r"(?<=[가-힣])\(\s*[,，]\s*(?=[0-9]{3,4}년)")
DANGLING_FIELD=re.compile(r",\s*\)|\(\s*[,，;]|《\s*》|\(\s*←")
BROKEN_SENTENCE=re.compile(r"(?i)(?:consist of\s*,|subset of\s*[.]|integer mark\s*[.]|defined as\s*$)",re.M)
STRAY_CODE=re.compile(r"(?mi)^\s*[0-9a-f]{4}\s+[0-9]+\s*$")
GENERIC_TAG=re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s+[^<>]*?)?/?>")
PUNCTUATION=re.compile(r"[.!?。！？]$|(?:이다|있다|한다|였다)[.!?。！？]?$",re.M)


def real_code_blocks(text):
    """Return line-fenced blocks and inline code, keeping literal bytes.

    A mid-paragraph run of tildes is decoration, not a fenced code block.
    An unmatched real opening fence is represented through EOF and remains HOLD.
    """
    blocks=[];start=None;marker=None;offset=0
    for line in text.splitlines(keepends=True):
        match=re.match(r"^ {0,3}(`{3,}|~{3,})(.*?)(?:\r?\n)?$",line)
        if match:
            run,rest=match.groups()
            if marker is None:
                start=offset;marker=run
            elif run[0]==marker[0] and len(run)>=len(marker) and not rest.strip():
                blocks.append((start,offset+len(line),text[start:offset+len(line)]));start=marker=None
        offset+=len(line)
    opened=marker is not None
    if opened:blocks.append((start,len(text),text[start:]))
    return blocks,opened


def code_preserved(original,cleaned):
    before,opened=real_code_blocks(original);after,new_opened=real_code_blocks(cleaned)
    if opened or new_opened:return False
    if [x[2] for x in before]!=[x[2] for x in after]:return False
    def inline(text,blocks):
        for lo,hi,_ in reversed(blocks):text=text[:lo]+" "*(hi-lo)+text[hi:]
        return re.findall(r"`[^`\n]+`",text)
    return inline(original,before)==inline(cleaned,after)


def protected_parts(text):
    # Reuse existing inline-code protection while additionally recognizing
    # complete actual line-fenced blocks, including longer fence delimiters.
    blocks,opened=real_code_blocks(text)
    spans=[(lo,hi) for lo,hi,_ in blocks]
    for m in re.finditer(r"`[^`\n]+`",text):
        if not any(lo<=m.start()<hi for lo,hi in spans):spans.append(m.span())
    spans.sort();parts=[];cursor=0
    for lo,hi in spans:
        parts.append((False,text[cursor:lo]));parts.append((True,text[lo:hi]));cursor=hi
    parts.append((False,text[cursor:]))
    return parts,opened


def normalize_outside_code(text):
    parts,opened=protected_parts(text)
    return "".join(part if protected else unicodedata.normalize("NFC",part.replace("\r\n","\n").replace("\r","\n"))
                   for protected,part in parts),opened


def remove_empty_labels(text):
    lines=text.splitlines(keepends=True);offset=0;protected=[]
    blocks,_=real_code_blocks(text)
    for line in lines:
        protected.append(any(lo<=offset<hi for lo,hi,_ in blocks));offset+=len(line)
    nonempty=[i for i,line in enumerate(lines) if line.strip()]
    remove=[];populated_appendix=False
    for n,i in enumerate(nonempty):
        label=normalize_heading(lines[i])
        if protected[i]:continue
        if label in APPENDIX_LABELS:
            populated_appendix=(n+1<len(nonempty) and normalize_heading(lines[nonempty[n+1]]) not in APPENDIX_LABELS)
            if populated_appendix:continue
        elif populated_appendix:
            # e.g. See also -> Transport -> Culture are actual related topics,
            # even though those words can also be page section headings.
            continue
        if label not in LABELS or label in AMBIGUOUS_LABELS:continue
        if n+1==len(nonempty):remove.append(i)
        else:
            following=nonempty[n+1]
            if not protected[following] and normalize_heading(lines[following]) in LABELS:remove.append(i)
    chosen=set(remove)
    return "".join(line for i,line in enumerate(lines) if i not in chosen),[
        dict(line=i+1,text=lines[i],reason="EMPTY_CONSECUTIVE_OR_TERMINAL_LABEL") for i in remove]


def propose(row,event):
    original=row["text"];text,opened=normalize_outside_code(original)
    if opened:return dict(decision="HOLD",text=original,reasons=["OPEN_ACTUAL_CODE_FENCE"],changes=[],rules=RULES)
    changes=[]
    # Optional empty foreign-name shells in an already identified Korean topic
    # introduction carry no value to reconstruct. Never apply this to functions
    # or an arbitrary empty field elsewhere in the article.
    parts,_=protected_parts(text)
    first=True;updated=[]
    for protected,part in parts:
        if first and not protected:
            paragraph=part.split(chr(10)+chr(10),1)[0]
            if KOREAN_INTRO.search(paragraph) and not re.search(r"수식|함수|변수|방정식|연산",paragraph):
                fixed,n=OPTIONAL_ALIAS.subn("",paragraph)
                fixed,m=EMPTY_BIRTH_ALIAS.subn("(",fixed)
                if n or m:
                    changes.append(dict(reason="EMPTY_OPTIONAL_ALIAS_IN_IDENTIFIED_INTRO",empty_shells=n,empty_birth_fields=m))
                    part=fixed+part[len(paragraph):]
            first=False
        updated.append(part)
    text="".join(updated)
    text,removed=remove_empty_labels(text);changes.extend(removed)
    parts,_=protected_parts(text);plain="".join(part for protected,part in parts if not protected)
    reasons=[]
    if not row["complete_eos"] or not row["valid_utf8"] or row["id"]=="validation:0":reasons.append("SOURCE_BOUNDARY_NOT_RECOVERABLE")
    if event.get("manual_hold") or event.get("previous_holds") or "PRESERVED_PREVIOUS_EXPLICIT_HOLD" in event["reasons"]:
        reasons.append("INHERITED_INDIVIDUAL_HOLD_REQUIRES_SOURCE_SHA_REVIEW")
    if DANGLING_FIELD.search(plain) or cache.MISSING_FIELD.search(plain):reasons.append("UNRESOLVED_FIELD_OR_TITLE")
    if corpus.BROKEN.search(plain) or "[[" in plain or "{{" in plain:reasons.append("BROKEN_TABLE_OR_WIKI_MARKUP")
    if corpus.UI.search(plain) or cache.PAGE_UI.search(plain):reasons.append("NONBODY_UI_REQUIRES_CONTEXT_EDIT")
    if "_x000D_" in plain:reasons.append("ESCAPED_EXTRACTION_BOUNDARY")
    if re.search(r"(?mi)^\s*(?:table of contents|목차)\s*$",plain):
        reasons.append("POPULATED_NAVIGATION_REQUIRES_CONTEXT_EDIT")
    plain_lines=[x for x in plain.splitlines() if x.strip()]
    appendix=False
    for i,line in enumerate(plain_lines):
        label=normalize_heading(line)
        if label in APPENDIX_LABELS:appendix=True
        if (not appendix and label in AMBIGUOUS_LABELS and
                (i+1==len(plain_lines) or normalize_heading(plain_lines[i+1]) in LABELS)):
            reasons.append("AMBIGUOUS_STRUCTURE_LABEL_REQUIRES_CONTEXT")
    if BROKEN_SENTENCE.search(plain) or STRAY_CODE.search(plain):reasons.append("MISSING_EXPRESSION_OR_STRAY_FRAGMENT")
    if GENERIC_TAG.search(plain) or "<!--" in plain:reasons.append("MARKUP_OR_TRANSCRIPTION_REQUIRES_CONTEXT")
    if not text.strip() or not PUNCTUATION.search(plain):reasons.append("INDEPENDENT_PROSE_NOT_ESTABLISHED")
    # Preserve normal repeated appendix lines, but do not release repetitions
    # embedded in the main body merely because they were left unchanged.
    repeated=Counter(x.strip() for x in plain.splitlines() if len(x.strip())>=6)
    duplicates={x for x,n in repeated.items() if n>1}
    appendix=False;main_repeat=False
    for line in plain.splitlines():
        label=normalize_heading(line)
        if label in APPENDIX_LABELS:appendix=True
        if line.strip() in duplicates and not appendix and label not in LABELS:main_repeat=True
    if main_repeat:reasons.append("MAIN_BODY_REPETITION_REQUIRES_CONTEXT")
    if not code_preserved(original,text):reasons.append("REAL_CODE_BYTES_CHANGED")
    if reasons:return dict(decision="HOLD",text=original,reasons=sorted(set(reasons)),changes=changes,rules=RULES)
    return dict(decision="EDIT" if text!=original else "KEEP",text=text,
        reasons=["RECOVER_IDENTIFIED_CONTENT_PRESERVE_POPULATED_APPENDICES"],changes=changes,rules=RULES)
