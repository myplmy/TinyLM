#!/usr/bin/env python3
"""Prove local empty calls and detect source punctuation lost by a renderer.

No program executes. Restoration is limited to an exact, uniquely recoverable
source call anchor; ambiguous or removed whole expressions stay pending.
"""
from collections import Counter
import re
from scripts import p106b_hold_resolution_policy_v20 as previous

OLD_LOCAL_CALLS = previous.local_calls_proven
CALL = re.compile(r"(?<![A-Za-z0-9_:.])(?P<name>[A-Za-z_][A-Za-z0-9_:.]*)\([ \t]*\)")
ASSIGNMENT = re.compile(r"^[ \t]*(?:(?:const|let|var|final|static)[ \t]+)?"
                        r"(?:(?:[A-Za-z_$][A-Za-z0-9_$<>\[\]]*)[ \t*&]+)?"
                        r"[*&]?[A-Za-z_$][A-Za-z0-9_$.\[\]]*[ \t]*=(?!=)")
USAGE_HEADING = re.compile(r"^[ \t]*[A-Za-z_][A-Za-z0-9_]*를 이용하는 프로그래밍 언어[ \t]*$")
LANGUAGE_MEMBER_ROW = re.compile(r"^[ \t]*[A-Za-z][A-Za-z0-9+# .-]*[ \t]+\([^\n]+을 통해\)[ \t]*$")
ROLE = re.compile(r"함수|메서드|메소드|시스템[ ]?콜|\b(?:function|method|system call)\b", re.I)
SQL_REFERENCE = re.compile(r"^[ \t]*Alternative Queries 문제 RECURSIVE\(CTE: Common Table Expressions\) 와 REPEAT\([ \t]*\)[ \t]*$")


def holes(text):
    plain = previous.plain_text(text)
    matches = list(previous.v1.cache.MISSING_FIELD.finditer(plain)) + list(previous.v10.DANGLING_FIELD.finditer(plain))
    return plain, sorted({(match.start(), match.end(), match[0]) for match in matches})


def blank_ranges(text, ranges):
    for lo, hi in reversed(ranges):
        text = text[:lo] + re.sub(r"[^\r\n]", " ", text[lo:hi]) + text[hi:]
    return text


def local_calls_proven(text):
    if OLD_LOCAL_CALLS(text):
        return True
    plain, matches = holes(text)
    if not matches:
        return False
    proved = []
    for lo, hi, value in matches:
        if not re.fullmatch(r"\([ \t]*\)", value):
            continue
        start = plain.rfind(chr(10), 0, lo) + 1
        end = plain.find(chr(10), hi)
        end = len(plain) if end < 0 else end
        before, after = plain[start:lo], plain[hi:end]
        name = previous.v18.CALL_NAME.search(before)
        if name is None:
            continue
        symbol, line = name[0], plain[start:end]
        prefix = before[:name.start()]
        if (ASSIGNMENT.match(before) and before.rstrip().endswith(symbol)
                and re.search(r";[ \t]*(?://[^\n]*)?$", after)):
            proved.append((lo, hi))
            continue
        # The function role belongs to this named source expression, not to
        # an unrelated programming word somewhere else in the document.
        if (ROLE.search(line) and re.search(re.escape(symbol) + r"[ \t]+(?:" + ROLE.pattern + ")", line, re.I)):
            proved.append((lo, hi))
            continue
        heading = False
        for prior in plain[:start].splitlines():
            label = previous.v1.normalize_heading(prior)
            if USAGE_HEADING.fullmatch(prior):
                heading = True
            elif label in previous.v4.APPENDICES | previous.v4.LABELS | previous.v9.SECTION_NAMES:
                heading = False
        if heading and LANGUAGE_MEMBER_ROW.fullmatch(line):
            proved.append((lo, hi))
            continue
        if SQL_REFERENCE.fullmatch(line) and symbol == "REPEAT":
            proved.append((lo, hi))
    remaining = blank_ranges(text, proved)
    if len(proved) == len(matches):
        return True
    return bool(proved and OLD_LOCAL_CALLS(remaining))


def call_counts(text):
    return Counter(match["name"] for match in CALL.finditer(previous.plain_text(text)))


def proven_source_call_losses(original, cleaned):
    before, after = call_counts(original), call_counts(cleaned)
    missing = {name: count - after[name] for name, count in before.items() if after[name] < count}
    if not missing:
        return {}
    plain, matches = holes(original)
    proven = {}
    for name, count in missing.items():
        others = []
        for lo, hi, value in matches:
            start = plain.rfind(chr(10), 0, lo) + 1
            symbol = previous.v18.CALL_NAME.search(plain[start:lo])
            if symbol is None or symbol[0] != name:
                others.append((lo, hi))
        if local_calls_proven(blank_ranges(original, others)):
            proven[name] = count
    return proven


def restore_source_call_anchors(original, cleaned):
    changes = []
    for name, count in proven_source_call_losses(original, cleaned).items():
        boundary = r"(?<![A-Za-z0-9_:.])"
        source = re.compile(boundary + re.escape(name) + r"\([ \t]*\)(?P<particle>[ \t]*(?:은|는|이|가|의|에|을|를))")
        anchors = {(match[0], match["particle"]) for match in source.finditer(original)}
        if len(anchors) != 1:
            continue
        anchor, particle = next(iter(anchors))
        bare = re.compile(boundary + re.escape(name) + re.escape(particle))
        if bare.search(original) or len(list(bare.finditer(cleaned))) != count:
            continue
        cleaned, restored = bare.subn(lambda match: anchor, cleaned)
        changes.append(dict(reason="RESTORE_EXACT_SOURCE_LOCAL_CALL_PARENTHESES_ANCHOR",
                            symbol=name, exact_source_anchor=anchor, restored_count=restored))
    return cleaned, changes, proven_source_call_losses(original, cleaned)
