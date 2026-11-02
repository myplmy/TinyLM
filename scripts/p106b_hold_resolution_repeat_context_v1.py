"""Describe repeated headings/bylines with distinct complete source paragraphs.

This is a conservative candidate proof, not a cache admission or text editor.
Every repeated unprotected line must have a locally established role.
"""
from collections import defaultdict
import hashlib
import re
from scripts import p106b_hold_resolution_policy_v26 as policy

RULE = "REPEATED_NAMED_HEADERS_OR_BYLINES_WITH_DISTINCT_COMPLETE_PARAGRAPHS_V1"
UI = re.compile(r"(?i)\b(?:read more|back to top|map and directions|subscribe|sign in|log in|"
                r"upgrade|remove ads|like liked|likeliked|previous|next|contents|share|reply|"
                r"contact us|privacy|cookies|buy now|add to cart|ocr for page)\b")
FORMAL = re.compile(r"(?i)\b(?:let|assume|suppose|where|therefore|hence|proof|theorem|lemma)\b|"
                    r"임의|다음|가정|정의|라 하|라고 하|일 때|에 대하여|에 대해서")
QUOTED_CONTEXT = re.compile(r"(?i)\b(?:quote|quotation|lyrics|refrain|poem)\b|인용|후렴|가사|시의 구절")
DATE_LINE = re.compile(r"(?i)^(?:[12][0-9]{3}[-/.]|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b).{0,65}$")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def typed_byline(value):
    match = re.fullmatch(r"(?i:by|written by|author\s*:)\s+(.+)", value)
    if match is None or UI.search(value):
        return False
    names = match[1].split()
    if not 2 <= len(names) <= 8:
        return False
    for word in names:
        letters = [char for char in word if char.isalpha()]
        if not letters or any(not (char.isalpha() or char in ".-'’") for char in word):
            return False
        if not letters[0].isupper() and word not in {"de", "van", "von", "da", "del"}:
            return False
    return True


def complete_paragraph(value):
    if (len(value) < 80 or not re.search(r"[.!?。！？]$", value)
            or not re.match(r"[A-Za-z가-힣]", value)
            or re.search(r"[{}<>|`]|\[\[|\]\]", value)
            or value.lower().startswith(("http:", "https:", "www."))):
        return False
    latin_words = re.findall(r"[A-Za-z]+", value)
    hangul = re.findall(r"[가-힣]", value)
    return len(latin_words) >= 12 or len(hangul) >= 16


def heading_role(value):
    if UI.search(value) or FORMAL.search(value) or re.search(r"[{}<>|`\[\]()]", value):
        return None
    if value.startswith(('"', "'", "“", "‘")) or value.endswith(('"', "'", "”", "’")):
        return None
    explicit = bool(re.fullmatch(r"#{1,6}\s+\S.{1,110}", value)
                    or re.fullmatch(r"={2,6}\s*\S.{1,110}?\s*={2,6}", value))
    if explicit:
        return "EXPLICIT_SOURCE_HEADING"
    if (6 <= len(value) <= 80 and not re.search(r"[.!?。！？,;]$", value)
            and re.match(r"[A-Z가-힣]", value)
            and len(re.findall(r"[A-Za-z가-힣]", value)) >= 4):
        return "ISOLATED_SHORT_SOURCE_HEADING_CANDIDATE"
    return None


def prove(text):
    plain = policy.plain_text(text)
    lines = plain.splitlines()
    actual_lines = text.splitlines()
    places = defaultdict(list)
    for index, line in enumerate(lines):
        value = line.strip()
        if len(value) >= 6 and policy.v1.normalize_heading(value) not in policy.v1.LABELS:
            places[value].append(index)
    repeated = {value: indexes for value, indexes in places.items() if len(indexes) > 1}
    if not repeated:
        return None
    nonempty = [index for index, line in enumerate(actual_lines) if line.strip()]
    next_actual = {index: nonempty[position + 1] if position + 1 < len(nonempty) else None
                   for position, index in enumerate(nonempty)}
    records = []
    for value, indexes in repeated.items():
        byline = typed_byline(value)
        role = "TYPED_NAMED_BYLINE" if byline else heading_role(value)
        if role is None:
            return None
        contexts = []
        for index in indexes:
            if (not byline and ((index and actual_lines[index - 1].strip())
                                or (index + 1 < len(actual_lines) and actual_lines[index + 1].strip()))):
                return None
            before = chr(10).join(actual_lines[max(0, index - 2):index])
            if QUOTED_CONTEXT.search(before):
                return None
            after = next_actual.get(index)
            if after is not None and byline and DATE_LINE.fullmatch(actual_lines[after].strip()):
                after = next_actual.get(after)
            if after is None or after >= len(lines) or not complete_paragraph(lines[after].strip()):
                return None
            contexts.append(dict(source_line=index + 1, paragraph_line=after + 1,
                paragraph_sha256=sha(lines[after].strip())))
        if len({record["paragraph_sha256"] for record in contexts}) != len(contexts):
            return None
        records.append(dict(line_sha256=sha(value), characters=len(value), role=role, contexts=contexts))
    return dict(rule=RULE, source_text_sha256=sha(text), all_repeated_lines=len(records),
        repeated_occurrences=sum(len(record["contexts"]) for record in records),
        records=records, text_modified=False, cache_admitted=False)
