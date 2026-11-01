#!/usr/bin/env python3
"""Versioned draft extension for observed empty name slots and real appendices.

No date, name, formula or quantity is generated. All first-version code and
results remain reproducible. New missing-quantity/local-reference guards also
apply to previously plausible draft candidates before any cache admission.
"""
from __future__ import annotations

from collections import Counter
import re
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V2_EMPTY_SLOTS_AND_APPENDICES"
v1 = previous.v1
v2 = previous.v2
old = previous.old
EXTRA_LABELS = {v1.normalize_heading(x) for x in [
    "목록", "역대 선거 결과", "선거 결과", "고득점 무대", "방송 일자",
    "연재작 목록", "홈 구장", "발기인", "국가중요문화재", "인구 통계"]}
LABELS = v1.LABELS | v2.EXTRA_LABELS | EXTRA_LABELS
TECHNICAL = re.compile(previous.TECHNICAL_INTRO.pattern + r"|표기|발음|음운|형태소|전사|행렬|벡터|좌표|매개변수|인수|튜플|인자|호출|국제음성|테이블|배열|CSV|자료형", re.I)
NAME_GROUP = re.compile(r"(?<=[가-힣》〉」』])\(([^()\n]*)\)(?=(?:은|는|이|가|의|에|란|라고|으로|로|와|과|도|을|를|[》〉」』]))")
METADATA_YEAR = re.compile(r"(?:[12][0-9]{3}년\s*.+(?:출생|사망|설립|폐지|해체|개업|음반|영화|노래|소설|축구단|철도 노선)|[12][0-9]{3}년\s*(?:출생|사망|설립|폐지|해체|개업|음반|영화)|살아있는 사람)")
REFERENCE = re.compile(previous.LINK_OR_REFERENCE.pattern + r"|네이버|데이터베이스|웹페이지|IMDb|AllMusic|Discogs|OpenLibrary|Wikisource|Wikimedia", re.I)
LIST_PARENT = re.compile(r"목차|차례|같이\s*보기|관련\s*(?:항목|문서|작품)|관심\s*분야|추천\s*(?:도서|목록)|table of contents", re.I)
PROGRAMMING = re.compile(r"\b(?:Python|JavaScript|Java|pandas|SQL|PHP|Ruby|Matlab|Octave|API|programming|method)\b|프로그래밍|메소드|메서드", re.I)
CALL_END = re.compile(r"[A-Za-z_][A-Za-z0-9_.:]*$")
ORPHAN_LEGEND = re.compile(r"파란색.*최저\s*시청률.*빨간색.*최고\s*시청률")
MISSING_DECLARATION = re.compile(r"(?:기호|값|결과|온도|질량|부피|속도|전압)(?:은|는|이|가)\s*[.。]|\bin\s+the\s+range\s*[.]", re.I)
MISSING_QUANTITY = re.compile(r"(?:평균|최대|최소)\s+의\s+(?:발사\s*)?속도|(?:총열\s*)?(?:길이|지름|직경|두께|무게|질량)\s+(?:인치|mm|cm|kg)(?:의|인|이다)|발사\s*속도는\s+(?:정도|에\s*달)", re.I)
NAVIGATION_BARS = re.compile(r"(?mi)^\s*\|*\s*(?:previous|next)\s+(?:page|chapter)\b[^\n]*\|")
FIGURE_ORPHAN = re.compile(r"아래\s*그림\s*참조|(?:다음|아래)\s*(?:도표|그림|표)에\s*(?:나와|표시되어)\s*있다")
MISSING_KOREAN_SYMBOL = re.compile(r"임의의\s+(?:에|는|를|와|과)\s|(?:정의|조건)에서\s+(?:를|은|가)\s")


def code_preserved(original, cleaned):
    return old.code_preserved(original, cleaned)


def unicode_examples_preserved(original, cleaned):
    return old.unicode_examples_preserved(original, cleaned)


def contextual_repetitions(text):
    return previous.contextual_repetitions(text)


def intro(text):
    """Permit explicit title/byline lines before the first identified prose."""
    for match in re.finditer(r"\S[\s\S]*?(?:\n[ \t]*\n|$)", text):
        paragraph = match[0].strip()
        if (re.search(r"\S[^\n]*?(?:은|는)\s+", paragraph)
                and previous.INTRO_PREDICATE.search(paragraph)):
            return paragraph
        if chr(10) in paragraph or re.search(r"[.!?。]$", paragraph):
            return None
    return None


def name_slots(text):
    if intro(text) is None:
        return text, []
    changes = []
    result = []
    for protected, part in v1.protected_parts(text)[0]:
        if protected:
            result.append(part)
            continue
        paragraphs = re.split(r"(\n[ \t]*\n)", part)
        for index in range(0, len(paragraphs), 2):
            paragraph = paragraphs[index]
            if TECHNICAL.search(paragraph):
                continue
            def replace(match):
                content = match[1]
                if "←" in content or ";" in content or "；" in content:
                    return match[0]
                fields = re.split(r"[,，]", content)
                if all(field.strip() for field in fields):
                    return match[0]
                retained = [field.strip() for field in fields if field.strip()]
                replacement = "(" + ", ".join(retained) + ")" if retained else ""
                changes.append(dict(reason="REMOVE_ONLY_EMPTY_OPTIONAL_NAME_SLOTS", original=match[0], replacement=replacement))
                return replacement
            paragraphs[index] = NAME_GROUP.sub(replace, paragraph)
        result.append("".join(paragraphs))
    return "".join(result), changes


def empty_sections(text):
    if intro(text) is None or re.search(r"(?mi)^\s*(?:목차|차례|관심\s*분야|추천\s*도서|table of contents)\s*$", text):
        # An actual course/book contents list is not a sequence of empty page
        # sections. Preserve ambiguous list headings for individual review.
        return text, []
    # Reuse the existing populated-appendix and code protections. The new
    # context evidence permits the previously ambiguous empty body labels.
    with v2.LOCK, patch.object(v1, "LABELS", LABELS), patch.object(v1, "AMBIGUOUS_LABELS", set()):
        result, changes = v1.remove_empty_labels(text)
    return result, [dict(change, reason="SOURCE_LABEL_HAS_NO_SECTION_CONTENT") for change in changes]


def metadata_tail(text):
    if intro(text) is None:
        return text, [], False
    lines = text.splitlines(keepends=True)
    nonempty = [i for i, line in enumerate(lines) if line.strip()]
    tail = []
    for index in reversed(nonempty):
        value = lines[index].strip()
        if (v1.normalize_heading(value) in LABELS or len(value) > 100 or REFERENCE.search(value)
                or not re.search(r"[가-힣]", value) or re.search(r"[.!?。]$|[《》\[\]]", value)):
            break
        tail.append(index)
    tail.reverse()
    if not tail:
        return text, [], False
    hard = sum(bool(METADATA_YEAR.fullmatch(lines[i].strip())) for i in tail)
    typed = sum(bool(previous.CATEGORY_FORM.fullmatch(lines[i].strip())) for i in tail)
    topic = intro(text)
    related_type = bool(re.search(r"배우|가수|선수|정치|인물|음반|노래|소설|영화|도시|마을|대학교|축구|철도|단체", topic))
    proven = hard >= 2 or (hard == 1 and related_type and len(tail) >= 2) or (hard == 0 and typed >= 2 and related_type)
    if not proven:
        return text, [], False
    remove = set()
    start = nonempty.index(tail[0])
    for index in reversed(nonempty[:start]):
        if v1.normalize_heading(lines[index]) in previous.old.FOOTERS:
            remove.add(index)
        else:
            break
    return "".join(line for i, line in enumerate(lines) if i not in remove), [
        dict(reason="EMPTY_FOOTER_WITH_SOURCE_LINKED_NOMINAL_CATEGORY_TAIL", line=i + 1, original=lines[i]) for i in sorted(remove)], True


def real_references(text):
    if intro(text) is None:
        return False
    appendix = False
    for line in text.splitlines():
        if v1.normalize_heading(line) in v1.APPENDIX_LABELS:
            appendix = True
            continue
        if appendix and REFERENCE.search(line):
            return True
    return False


def ordinary_empty_calls(text):
    plain = "".join(part for protected, part in v1.protected_parts(text)[0] if not protected)
    if not PROGRAMMING.search(plain) or v1.DANGLING_FIELD.search(plain):
        return False
    matches = list(v1.cache.MISSING_FIELD.finditer(plain))
    if not matches:
        return False
    return all(re.fullmatch(r"\(\s*\)", match[0]) and CALL_END.search(plain[:match.start()]) for match in matches)


def birth_fields_agree(text):
    """Disprove the observed birth-only/year + full death-date false positive.

    All source date strings remain unchanged. A genuine conflicting year or
    an unknown left side cannot be released by this test.
    """
    first = intro(text)
    if not first or not re.search(r"배우|가수|선수|정치|학자|작가|화가|사람|인물|교수|기수", first):
        return False
    categories = re.findall(r"(?m)^\s*([12][0-9]{3})년\s*출생\s*$", text)
    if not categories:
        return False
    for match in re.finditer(r"\(([^()\n]*)\)", first):
        left = re.split(r"~|～|∼|–|—|\s-\s", match[1], maxsplit=1)[0]
        year = re.search(r"([12][0-9]{3})년", left)
        if year:
            return all(value == year[1] for value in categories)
    return False


def structured_repetition(text):
    if previous.contextual_repetitions(text):
        return True
    plain = "".join(part for protected, part in v1.protected_parts(text)[0] if not protected)
    lines = [line.strip() for line in plain.splitlines() if line.strip()]
    anchors = {line for line in lines if len(line) <= 100 and
               (previous.YEAR_ANCHOR.search(line) or previous.STRUCTURE_ANCHOR.search(line))}
    if len(anchors) < 2:
        return False
    repeated = {line for line, count in Counter(lines).items() if count > 1 and len(line) >= 6
                and v1.normalize_heading(line) not in LABELS}
    return bool(repeated) and all(not re.search(r"[.!?。]$|(?:이다|했다|한다|있다)[.!?。]?$", line) for line in repeated)


def extra_risks(text):
    plain = "".join(part for protected, part in v1.protected_parts(text)[0] if not protected)
    risks = []
    for expression, reason in [
        (ORPHAN_LEGEND, "RATING_LEGEND_REQUIRES_ACTUAL_VALUE_ROWS"),
        (MISSING_DECLARATION, "OBSERVED_MISSING_DECLARATION_OR_PARAMETER_RANGE"),
        (MISSING_QUANTITY, "OBSERVED_MISSING_MEASURED_QUANTITY"),
        (NAVIGATION_BARS, "EXTRACTED_PAGE_OR_CHAPTER_NAVIGATION"),
        (FIGURE_ORPHAN, "LOCAL_FIGURE_OR_TABLE_TARGET_NEEDS_CONTEXT"),
        (MISSING_KOREAN_SYMBOL, "OBSERVED_MISSING_KOREAN_FORMAL_SYMBOL"),
        (previous.CTA, "OBSERVED_CTA_NEEDS_CONTEXT_EDIT")]:
        if expression.search(plain):
            risks.append(reason)
    return risks


def propose(row, individual_hold=False):
    original = row["text"]
    if not row["complete_eos"] or row["id"] == "validation:0":
        return previous.propose(row, individual_hold)
    if individual_hold or row.get("previous_holds"):
        return dict(decision="PENDING", text=original, reasons=["PRIOR_INDIVIDUAL_OR_SPAN_REVIEW_REQUIRES_ROOT_ADOPTION"], changes=[], rules=RULES)
    text, opened = v2.literal_normalize(original)
    if opened:
        return dict(decision="PENDING", text=original, reasons=["OPEN_ACTUAL_CODE_FENCE"], changes=[], rules=RULES)
    text, changes = name_slots(text)
    text, removed = empty_sections(text)
    changes.extend(removed)
    text, removed, categories = metadata_tail(text)
    changes.extend(removed)
    # Only this version's context-guarded repairs may change names/headings.
    # Retain all frozen detection, code, Unicode and scientific-hole checks.
    never = re.compile(r"(?!)")
    with v2.LOCK, patch.object(v1, "remove_empty_labels", lambda value: (value, [])), \
            patch.object(v1, "OPTIONAL_ALIAS", never), patch.object(v1, "EMPTY_BIRTH_ALIAS", never):
        result = old.propose(dict(row, text=text), dict(reasons=[], manual_hold=False))
    changes.extend(result["changes"])
    risks = set(result["reasons"]) if result["decision"] == "HOLD" else set()
    if categories or real_references(text):
        risks.discard("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT")
    if ordinary_empty_calls(text):
        risks.discard("UNRESOLVED_FIELD_OR_TITLE")
    if birth_fields_agree(text):
        risks.discard("INTERNAL_BIRTH_YEAR_CONFLICT_UNRESOLVED")
    if structured_repetition(text):
        risks.discard("MAIN_BODY_REPETITION_REQUIRES_CONTEXT")
    risks.update(extra_risks(text))
    final = result["text"] if result["decision"] != "HOLD" else text
    if not code_preserved(original, final) or not unicode_examples_preserved(original, final):
        risks.add("CODE_OR_UNICODE_GUARD")
    if risks:
        return dict(decision="PENDING", text=original, candidate=final, reasons=sorted(risks), changes=changes, rules=RULES)
    return dict(decision="EDIT" if final != original else "KEEP", text=final,
                reasons=["DRAFT_SOURCE_LINKED_OPTIONAL_FIELDS_AND_REAL_APPENDICES"], changes=changes, rules=RULES)
