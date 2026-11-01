#!/usr/bin/env python3
"""Local nominal fields and source-proven damaged block quarantine.

Retain actual values, qualified definitions, references and independently
understandable sections. No missing name, expression or quantity is generated.
"""
from __future__ import annotations

from collections import Counter
import re
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy_v8 as previous

RULES="RESIDUAL_CONTEXT_RECOVERY_DRAFT_V9_NOMINAL_AND_PARTIAL_BLOCKS"
v6,v4,v2,v1=previous.v6,previous.v4,previous.v2,previous.v1
code_preserved=previous.code_preserved
unicode_examples_preserved=previous.unicode_examples_preserved
contextual_repetitions=previous.contextual_repetitions
ORIGINAL_INTRO=previous.intro
ORIGINAL_NAME_SLOTS=v6.name_slots
# A station name ending in マチ駅/마치역 is not the mathematical term 치역.
MATH_CONTEXT=re.compile(v6.MATH_CONTEXT.pattern.replace("|치역|",r"|(?<![가-힣])치역|"),re.I)
OPTIONAL_SLOT_LABEL=re.compile(r"^(?:패키지명|일본어명|영어명|한국어명|한자명|로마자명|현지명)\s*[:：]?\s*$")
PUBLISHED=re.compile(r"(?:발매|출시|개봉|연재|공개)되었다[.!?。]?$",re.M)
COMPLETE_WORK=re.compile(r"《[^》\s][^》]*》")
CURRENCY=re.compile(r"통화로\s|화폐로\s")
DISAMBIGUATION=re.compile(r"다음을\s*가리키는\s*말|다음(?:과\s*같은)?\s*(?:뜻|의미)")
DEPENDENT=re.compile(r"^(?:따라서|그러므로|즉,?|이로부터|이때|이를|이것|그것|이러한|그러한|"
                     r"예를\s*들어|예컨대|이\s*(?:경우|식|수식|값|함수|조건)|"
                     r"Thus\b|Therefore\b|Hence\b|So\b|For example\b|This\b|These\b|"
                     r"It\b|They\b|We\b|Consequently\b|Accordingly\b)",re.I)
FORMULA_DEPENDENCY=re.compile(r"수식|공식|방정식|기호|임의의|매개변수|계수|행렬|벡터|"
                              r"\b(?:formula|equation|parameter|coefficient|matrix|defined)\b|[=∈∉∑∫∀∃]",re.I)
BLOCK_REASONS={"UNRESOLVED_FIELD_OR_TITLE","OBSERVED_MISSING_KOREAN_FORMAL_SYMBOL",
               "OBSERVED_EMPTY_KINSHIP_OR_STATISTICAL_VALUE","OBSERVED_MISSING_DECLARATION_OR_PARAMETER_RANGE",
               "MISSING_EXPRESSION_OR_STRAY_FRAGMENT","OBSERVED_MISSING_MEASURED_QUANTITY",
               "MISSING_QUANTITY_IN_SCIENTIFIC_STATEMENT","LOCAL_FIGURE_OR_TABLE_TARGET_NEEDS_CONTEXT"}
EMPTY_LITERAL_CONTEXT=re.compile(r"(?:empty\s+(?:tuple|parentheses|string)|빈\s*(?:튜플|괄호|문자열))",re.I)
MISSING_SIMPLE_QUANTITY=re.compile(r"(?:무게|질량|길이|높이|너비|폭)(?:는|은|이|가)\s*(?:kg|mm|cm|킬로그램|미터)(?:이다|다)[.!?。]",re.I)
UNIT_DEFINITION=re.compile(r"단위|unit|기호|표기",re.I)
SECTION_NAMES={v1.normalize_heading(x) for x in [
    "역사","연혁","생애","생애 초기","경력","독립 역사","유래","기원","발견","개요",
    "외부 링크","참고 문헌","같이 보기","각주","주석","응용","응용 분야","관련 연구",
    "예시","예제","성질","정의","기능","구조","분류","용도","어원","작품 목록",
    "history","background","references","external links","see also","applications",
    "medal table","메달 집계","세부 종목"]}
INDEPENDENT_SECTION={v1.normalize_heading(x) for x in [
    "역사","연혁","생애","생애 초기","유래","기원","어원","참고 문헌","참고자료",
    "외부 링크","같이 보기","각주","주석","history","background","references",
    "external links","see also"]}


def intro(text):
    found=ORIGINAL_INTRO(text)
    if found is not None:
        return found
    for match in v4.v3.PARAGRAPH.finditer(text):
        paragraph=match[0].strip()
        if v4.v3.SUBJECT.search(paragraph) and (CURRENCY.search(paragraph)
                or COMPLETE_WORK.search(paragraph) and PUBLISHED.search(paragraph)):
            return paragraph
        if chr(10) in paragraph or re.search(r"[.!?。]$",paragraph):
            break
    return None


def nominal_fields(text):
    """Fix the proven substring false positive; keep every populated field."""
    with v2.v2.LOCK,patch.object(v4,"intro",intro),patch.object(v6,"MATH_CONTEXT",MATH_CONTEXT):
        text,changes=ORIGINAL_NAME_SLOTS(text)
    if intro(text) is None:
        return text,changes
    listing=bool(DISAMBIGUATION.search(text.split(chr(10),1)[0]))
    result=[]
    for protected,part in v1.protected_parts(text)[0]:
        if protected:
            result.append(part)
            continue
        lines=part.splitlines(keepends=True)
        for i,line in enumerate(lines):
            if MATH_CONTEXT.search(line) or v2.PROGRAMMING.search(line):
                continue
            if listing:
                with patch.object(v6,"identified",lambda value:True),patch.object(v6,"MATH_CONTEXT",MATH_CONTEXT):
                    line,more=ORIGINAL_NAME_SLOTS(line)
                changes+=more
                # Nested name alternatives can retain a leading separator once
                # the inner empty alias was removed. All actual names survive.
                fixed,count=re.subn(r"(?<=\()[ \t]*[,，][ \t]*(?=(?:또는|혹은)\s)","",line)
                if count:
                    changes.append(dict(reason="EMPTY_LEADING_SLOT_BEFORE_LITERAL_NAMED_ALTERNATIVE",count=count,
                                        original=line,replacement=fixed))
                    line=fixed
            def replace(match):
                if not v6.nominal_context(line,match):
                    return match[0]
                content=match[1]
                if re.search(r"[=+*/<>\\{}\[\]]",content):
                    return match[0]
                pieces=v4.DELIMITERS.split(content)
                fields=[(j,pieces[j]) for j in range(0,len(pieces),2)]
                populated=[]
                for j,value in fields:
                    stripped=value.strip()
                    if OPTIONAL_SLOT_LABEL.fullmatch(stripped) and COMPLETE_WORK.search(line):
                        continue
                    if stripped:
                        populated.append((j,value))
                if len(populated)==len(fields):
                    return match[0]
                # A missing former-name arrow remains unresolved; a fully
                # provided arrow+name is preserved as an actual value.
                if "←" in content and any("←" in value and not re.search(r"←\s*[^\s,，;；←]",value)
                                           for _,value in populated):
                    return match[0]
                if any(re.search(r"[0-9]",value) and not re.search(r"[0-9](?:년|月|年)",value)
                       and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_. -]*",value.strip()) for _,value in populated):
                    return match[0]
                if populated:
                    retained=populated[0][1].strip()
                    for (prior,_),(j,value) in zip(populated,populated[1:]):
                        retained+=pieces[prior+1]+value
                    replacement="("+retained.rstrip()+")"
                else:
                    replacement=""
                changes.append(dict(reason="ACTUAL_NOMINAL_VALUE_RETAINED_EMPTY_OPTIONAL_SLOTS_ONLY",
                                    original=match[0],replacement=replacement))
                return replacement
            lines[i]=v6.NOMINAL_GROUP.sub(replace,line)
        result.append("".join(lines))
    return "".join(result),changes


def section_label(value):
    return v1.normalize_heading(value) in SECTION_NAMES | v4.LABELS | previous.previous.EXTRA_LABELS


def independent_paragraph(value,topic=None):
    stripped=value.strip()
    if not stripped or DEPENDENT.search(stripped) or EMPTY_LITERAL_CONTEXT.search(stripped):
        return False
    if any(v1.cache.MISSING_FIELD.search(part) or v1.DANGLING_FIELD.search(part)
           for protected,part in v1.protected_parts(stripped)[0] if not protected):
        return False
    if FORMULA_DEPENDENCY.search(stripped) or MATH_CONTEXT.search(stripped):
        return False
    if intro(stripped) is not None:
        return True
    return bool(topic and stripped.startswith(topic) and v1.PUNCTUATION.search(stripped))


def value_damage(paragraph):
    plain="".join(part for protected,part in v1.protected_parts(paragraph)[0] if not protected)
    if EMPTY_LITERAL_CONTEXT.search(plain) and previous.TEACHING_FRAME.search(plain):
        return []
    reasons=[]
    if v1.cache.MISSING_FIELD.search(plain) or v1.DANGLING_FIELD.search(plain):
        with patch.object(v6,"CALL_CONTEXT",previous.CALL_CONTEXT):
            ordinary=v6.ordinary_empty_calls(paragraph)
        if not ordinary:
            reasons.append("ACTUAL_UNFILLED_NAME_TITLE_OR_VALUE")
    for pattern,reason in [(v2.MISSING_DECLARATION,"ACTUAL_MISSING_DECLARATION"),
                           (v2.MISSING_QUANTITY,"ACTUAL_MISSING_QUANTITY"),
                           (v2.MISSING_KOREAN_SYMBOL,"ACTUAL_MISSING_FORMAL_SYMBOL"),
                           (v4.MISSING_STATISTIC,"ACTUAL_MISSING_STATISTICAL_VALUE"),
                           (v4.EMPTY_KINSHIP,"ACTUAL_EMPTY_KINSHIP_RECORD"),
                           (v1.BROKEN_SENTENCE,"ACTUAL_BROKEN_EXPRESSION"),
                           (v2.FIGURE_ORPHAN,"ACTUAL_UNAVAILABLE_FIGURE_TARGET")]:
        if pattern.search(plain):
            reasons.append(reason)
    if MISSING_SIMPLE_QUANTITY.search(plain) and not UNIT_DEFINITION.search(plain):
        reasons.append("ACTUAL_UNIT_WITHOUT_A_MEASURED_VALUE")
    return reasons


def quarantine_values(text):
    """Keep a complete introduction and independent sections around damage.

    Once a premise is missing, later paragraphs stay quarantined until an
    actual section boundary or explicit independent named definition. This is
    deliberately stricter than dropping only a visibly empty equation line.
    """
    first=intro(text)
    if first is None or value_damage(first):
        return text,[]
    subject=v4.v3.SUBJECT.search(first)
    topic=first[:subject.start()].split("(",1)[0].strip("《》〈〉‘’“”'\" ") if subject else None
    lines=text.splitlines(keepends=True)
    blocks=[]
    current=[]
    for line in lines:
        if section_label(line.strip()):
            if current:
                blocks.append("".join(current));current=[]
            blocks.append(line)
        else:
            current.append(line)
            if not line.strip():
                blocks.append("".join(current));current=[]
    if current:
        blocks.append("".join(current))
    output,changes=[],[]
    dependent=False
    recovered_boundary=False
    for block in blocks:
        if section_label(block.strip()):
            if v1.normalize_heading(block) in INDEPENDENT_SECTION:
                recovered_boundary |= dependent
                dependent=False
            if dependent:
                changes.append(dict(reason="QUARANTINE_ACTUAL_VALUE_HOLE_AND_PREMISE_DEPENDENTS",
                                    evidence=["DEPENDENT_SECTION_LABEL_AFTER_MISSING_PREMISE"],original=block))
            else:
                output.append(block)
            continue
        reasons=value_damage(block)
        if reasons:
            dependent=True
        elif dependent and independent_paragraph(block,topic):
            recovered_boundary=True
            dependent=False
        if dependent and block.strip():
            changes.append(dict(reason="QUARANTINE_ACTUAL_VALUE_HOLE_AND_PREMISE_DEPENDENTS",
                                evidence=reasons or ["DEPENDS_ON_PRECEDING_MISSING_PREMISE"],original=block))
        else:
            output.append(block)
    candidate="".join(output)
    if not changes or not recovered_boundary or not candidate.strip() or intro(candidate) is None:
        return text,[]
    # Fenced/inline code and Unicode examples cannot disappear in an automated
    # block quarantine. Cases requiring that judgment stay for authored review.
    if not code_preserved(text,candidate) or not unicode_examples_preserved(text,candidate):
        return text,[]
    return candidate,changes


def propose(row,individual_hold=False):
    original=row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"]=="validation:0":
        return dict(previous.propose(row,individual_hold),rules=RULES)
    with v2.v2.LOCK:
        prepared,changes=nominal_fields(original)
        with patch.object(previous,"intro",intro):
            result=previous.propose(dict(row,text=prepared),False)
        final=result.get("candidate",result["text"])
        changes+=result["changes"]
        new_quantity=bool(MISSING_SIMPLE_QUANTITY.search(final) and not UNIT_DEFINITION.search(final))
        if new_quantity or result["decision"]=="PENDING" and BLOCK_REASONS.intersection(result["reasons"]):
            repaired,removed=quarantine_values(final)
            if repaired!=final:
                with patch.object(previous,"intro",intro):
                    result=previous.propose(dict(row,text=repaired),False)
                changes+=removed
                final=result.get("candidate",result["text"])
                changes+=result["changes"]
        risks=set(result["reasons"]) if result["decision"]=="PENDING" else set()
        if MISSING_SIMPLE_QUANTITY.search(final) and not UNIT_DEFINITION.search(final):
            risks.add("ACTUAL_UNIT_WITHOUT_A_MEASURED_VALUE")
        if not code_preserved(original,final) or not unicode_examples_preserved(original,final):
            risks.add("CODE_OR_UNICODE_GUARD")
        if risks:
            return dict(decision="PENDING",text=original,candidate=final,reasons=sorted(risks),changes=changes,rules=RULES)
        return dict(decision="EDIT" if final!=original else "KEEP",text=final,
                    reasons=["SOURCE_NOMINAL_AND_INDEPENDENT_BLOCK_CONTEXT_RETAINED"],changes=changes,rules=RULES)

