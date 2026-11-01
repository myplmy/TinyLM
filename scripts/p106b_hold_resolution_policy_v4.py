#!/usr/bin/env python3
"""Source-observed entity aliases, populated references and heading boundaries.

No legacy individual/span HOLD is released by these draft rules. They retain
all filled fields, literal code and Unicode and run downstream risks even when
the frozen engine first stopped at a different reason.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy_v2 as v2
from scripts import p106b_hold_resolution_policy_v3 as v3

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V4_ENTITY_AND_REFERENCE_CONTEXT"
v1 = v2.v1
old = v2.old
code_preserved = v2.code_preserved
unicode_examples_preserved = v2.unicode_examples_preserved
contextual_repetitions = v2.contextual_repetitions
ENTITY = re.compile(r"(?:선수|배우|가수|작가|시인|소설가|정치인|교수|학자|감독|가문|왕|황제|군주|군인|기수|사진가|기업|브랜드|기관|학교|대학교|도시|마을|행정동|법정동|국가|단체|밴드|음반|앨범|노래|영화|소설|만화|애니메이션|방송|항공기|전투기|철도|철도역|노선|병원|공원|경기장|건축물)(?:이[다자며]|이었다|였다|다[.!?。]|로[ ,]|[,.])")
ALIAS = re.compile(r"(?<=[가-힣A-Za-z0-9》〉」』])\s*\(([^()\n]*)\)(?=\s*(?:은|는|이|가|의|에|란|라고|으로|로|와|과|도|을|를|또는|혹은|때때로|일명|약칭|[,，》〉」』]))")
DELIMITERS = re.compile(r"([,，;；])")
REFERENCE = re.compile(v2.REFERENCE.pattern + r"|프로필|바이오그래피|biography|필모그래피", re.I)
EXTRA_LABELS = {v1.normalize_heading(x) for x in [
    "인접역", "승강장", "승차홈", "가사", "참고자료", "발기인", "역대 공관장",
    "연도별 타격 성적", "활동 내역", "싱글", "앨범", "출연", "시청률",
    "도시 경관", "배우자", "출처", "참조주", "주해", "국가대표팀 기록", "클럽 기록"]}
LABELS = v2.LABELS | EXTRA_LABELS
APPENDICES = v1.APPENDIX_LABELS | {v1.normalize_heading(x) for x in ["참고자료", "참고 자료", "참조주", "내용주", "주해", "출처"]}
STRIPPABLE_APPENDICES = old.FOOTERS | {v1.normalize_heading(x) for x in ["참고 문헌", "참고자료", "참고 자료", "참조주", "내용주", "주해", "출처"]}
CATEGORY_LINE = re.compile(r"(?:.+동문|.+출신(?:\s*(?:인물|배우|가수|선수))?|[0-9]+세기\s+.+사람|[가-힣]+계\s*[가-힣]+인|(?:.+의\s+)?(?:(?:남자|여자)\s+)?(?:텔레비전 배우|영화 배우|배우|가수|싱어송라이터|축구 선수|야구 선수|축구 감독|축구 수비수|축구 미드필더|정치인|사진가|작가|음반|영화|영화 작품|드라마 영화|전기 영화|애니메이션 영화|노래|소설|도시|자치체|행정동|법정동|학교|대학교|병원|건축물|경기장|단체)|.+의\s+(?:라이브|컴필레이션|사운드트랙|정규|미니|스튜디오|데뷔|합동|솔로)\s*음반|.+(?:감독 영화|어 영화 작품|어 음반|공공병원))")
EMPTY_KINSHIP = re.compile(r"(?m)^\s*(?:고모|이모|삼촌|부모|아버지|어머니)\s*:\s*$")
MISSING_STATISTIC = re.compile(r"년\s*월\s*일|(?:총|약)\s*개(?:의|[ .])|(?:의\s*전원,\s*의\s*해안선|토지는\s*약\s*로\s*해안선|해안선은\s*로\s)")
ORIGINAL_NAME_SLOTS = v2.name_slots


def intro(text):
    for match in v3.PARAGRAPH.finditer(text):
        paragraph = match[0].strip()
        if v3.SUBJECT.search(paragraph) and ENTITY.search(paragraph):
            return paragraph
        if chr(10) in paragraph or re.search(r"[.!?。]$", paragraph):
            break
    return v3.intro(text)


def name_slots(text):
    topic = intro(text)
    if not topic or not ENTITY.search(topic):
        return ORIGINAL_NAME_SLOTS(text)
    changes = []
    out = []
    for protected, part in v1.protected_parts(text)[0]:
        if protected:
            out.append(part)
            continue
        paragraphs = re.split(r"(\n[ \t]*\n)", part)
        for i in range(0, len(paragraphs), 2):
            if v2.TECHNICAL.search(paragraphs[i]):
                continue
            def replace(match):
                content = match[1]
                if "←" in content:
                    return match[0]
                pieces = DELIMITERS.split(content)
                fields = [(j, pieces[j]) for j in range(0, len(pieces), 2)]
                filled = [(j, value) for j, value in fields if value.strip()]
                if len(filled) == len(fields):
                    return match[0]
                if not filled:
                    replacement = ""
                else:
                    retained = filled[0][1].strip()
                    for (previous_index, _), (j, value) in zip(filled, filled[1:]):
                        retained += pieces[previous_index + 1] + value
                    replacement = "(" + retained.rstrip() + ")"
                changes.append(dict(reason="ENTITY_IDENTIFIED_REMOVE_ONLY_EMPTY_ALIAS_FIELDS",
                                    original=match[0], replacement=replacement))
                return replacement
            paragraphs[i] = ALIAS.sub(replace, paragraphs[i])
        out.append("".join(paragraphs))
    return "".join(out), changes


def empty_sections(text):
    if re.search(r"(?mi)^\s*(?:목차|차례|관심\s*분야|추천\s*도서|table of contents)\s*$", text):
        return text, []
    lines = text.splitlines(keepends=True)
    entries = [i for i, line in enumerate(lines) if line.strip()]
    blocks, _ = v1.real_code_blocks(text)
    offsets = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line)
    protected = {i for i in entries if any(lo <= offsets[i] < hi for lo, hi, _ in blocks)}
    remove = set()
    populated_appendix = False
    for n, index in enumerate(entries):
        label = v1.normalize_heading(lines[index])
        if index in protected:
            continue
        if label in APPENDICES:
            populated_appendix = n + 1 < len(entries) and v1.normalize_heading(lines[entries[n + 1]]) not in APPENDICES
            if populated_appendix:
                continue
        elif populated_appendix:
            continue
        if label not in LABELS:
            continue
        cursor = n + 1
        boundary = label in APPENDICES
        while cursor < len(entries) and entries[cursor] not in protected:
            following = v1.normalize_heading(lines[entries[cursor]])
            if following not in LABELS:
                break
            boundary |= following in APPENDICES
            cursor += 1
        # A parent before a populated child is retained. An appendix boundary
        # or EOF proves that the preceding body section has no own content.
        if cursor == len(entries) or (boundary and label not in APPENDICES):
            remove.add(index)
        elif label in APPENDICES and n + 1 < len(entries) and v1.normalize_heading(lines[entries[n + 1]]) in APPENDICES:
            remove.add(index)
        elif (label == v1.normalize_heading("기후") and n + 1 < len(entries)
              and v1.normalize_heading(lines[entries[n + 1]]) == v1.normalize_heading("교통")
              and intro(text) and "도시" in intro(text)
              and index + 1 < len(lines) and not lines[index + 1].strip()):
            remove.add(index)
    return "".join(line for i, line in enumerate(lines) if i not in remove), [
        dict(reason="EMPTY_SECTION_PROVEN_BY_APPENDIX_OR_EOF_PRESERVE_POPULATED_CHILD", line=i + 1, original=lines[i]) for i in sorted(remove)]


def metadata_tail(text):
    if intro(text) is None:
        return text, [], False
    lines = text.splitlines(keepends=True)
    entries = [i for i, line in enumerate(lines) if line.strip()]
    tail = []
    for index in reversed(entries):
        value = lines[index].strip()
        if (v1.normalize_heading(value) in LABELS or len(value) > 100 or REFERENCE.search(value)
                or not re.search(r"[가-힣]", value) or re.search(r"[.!?。]$|[《》\[\]]", value)
                or not (v2.METADATA_YEAR.fullmatch(value) or CATEGORY_LINE.fullmatch(value))):
            break
        tail.append(index)
    tail.reverse()
    hard = sum(bool(v2.METADATA_YEAR.fullmatch(lines[i].strip())) for i in tail)
    typed = sum(bool(v2.previous.CATEGORY_FORM.fullmatch(lines[i].strip())) for i in tail)
    proven = hard >= 1 or (typed >= 2 and bool(ENTITY.search(intro(text))))
    if not proven:
        return text, [], False
    remove = set()
    for index in reversed(entries[:entries.index(tail[0])]):
        if v1.normalize_heading(lines[index]) in STRIPPABLE_APPENDICES:
            remove.add(index)
        else:
            break
    return "".join(line for i, line in enumerate(lines) if i not in remove), [
        dict(reason="EMPTY_FOOTER_BEFORE_EXPLICIT_SOURCE_METADATA_ANCHOR", line=i + 1, original=lines[i]) for i in sorted(remove)], True


def real_references(text):
    appendix = False
    for line in text.splitlines():
        if v1.normalize_heading(line) in APPENDICES:
            appendix = True
        elif appendix and REFERENCE.search(line):
            return True
    return False


def hierarchy(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    found = []
    for n, line in enumerate(lines):
        label = v1.normalize_heading(line)
        if label in APPENDICES:
            break
        if label not in v1.AMBIGUOUS_LABELS or (n + 1 < len(lines) and v1.normalize_heading(lines[n + 1]) not in LABELS):
            continue
        cursor = n + 1
        while cursor < len(lines) and v1.normalize_heading(lines[cursor]) in LABELS:
            if v1.normalize_heading(lines[cursor]) in APPENDICES:
                return False
            cursor += 1
        found.append(cursor < len(lines) and bool(v1.PUNCTUATION.search(lines[cursor])))
    return bool(found) and all(found)


def surface(text):
    lines = text.splitlines(keepends=True)
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    remove = set()
    protected_parts, _ = v1.protected_parts(text)
    masked = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part for protected, part in protected_parts)
    plain_lines = masked.splitlines(keepends=True)
    for n, index in enumerate(nonempty):
        value = plain_lines[index].strip()
        if v2.NAVIGATION_BARS.search(value):
            remove.add(index)
        if re.fullmatch(r"(?i)\|?\s*table of contents\s*\|?", value):
            following = nonempty[n + 1:n + 3]
            if not following or any(v1.PUNCTUATION.search(plain_lines[i].strip()) and len(plain_lines[i]) > 120 for i in following):
                remove.add(index)
    return "".join(line for i, line in enumerate(lines) if i not in remove), [
        dict(reason="EMPTY_WEB_CONTENTS_MARKER_OR_EXPLICIT_PAGE_NAVIGATION", line=i + 1, original=lines[i]) for i in sorted(remove)]


def draft_without_inherited_release(row):
    original = row["text"]
    text, changes = surface(original)
    with v2.v2.LOCK, patch.object(v2, "intro", intro), patch.object(v2, "name_slots", name_slots), \
            patch.object(v2, "empty_sections", empty_sections), patch.object(v2, "metadata_tail", metadata_tail), \
            patch.object(v2, "real_references", real_references), patch.object(v1, "APPENDIX_LABELS", APPENDICES):
        result = v2.propose(dict(row, text=text, previous_holds=[]), False)
    final = result.get("candidate", result["text"])
    risks = set(result["reasons"]) if result["decision"] == "PENDING" else set()
    plain = "".join(part for protected, part in v1.protected_parts(final)[0] if not protected)
    if v2.v2.MORE_UI.search(plain):
        risks.add("OBSERVED_PAGE_WIDGET_REQUIRES_CONTEXT_EDIT")
    if v2.v2.MISSING_QUANTITY.search(plain):
        risks.add("MISSING_QUANTITY_IN_SCIENTIFIC_STATEMENT")
    if v2.v2.conflicting_birth_year(plain) and not v2.birth_fields_agree(final):
        risks.add("INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED")
    if EMPTY_KINSHIP.search(plain) or MISSING_STATISTIC.search(plain):
        risks.add("OBSERVED_EMPTY_KINSHIP_OR_STATISTICAL_VALUE")
    if hierarchy(final):
        risks.discard("AMBIGUOUS_STRUCTURE_LABEL_REQUIRES_CONTEXT")
    if not code_preserved(original, final) or not unicode_examples_preserved(original, final):
        risks.add("CODE_OR_UNICODE_GUARD")
    changes += result["changes"]
    if risks:
        return dict(decision="PENDING", text=original, candidate=final, reasons=sorted(risks), changes=changes, rules=RULES)
    return dict(decision="EDIT" if final != original else "KEEP", text=final,
                reasons=["DRAFT_SOURCE_ENTITY_AND_APPENDIX_CONTEXT_PRESERVED"], changes=changes, rules=RULES)


def propose(row, individual_hold=False):
    if not row["complete_eos"] or row["id"] == "validation:0":
        return v2.propose(row, individual_hold)
    if individual_hold or row.get("previous_holds"):
        return dict(decision="PENDING", text=row["text"], reasons=["PRIOR_INDIVIDUAL_OR_SPAN_REVIEW_REQUIRES_ROOT_ADOPTION"], changes=[], rules=RULES)
    return draft_without_inherited_release(row)
