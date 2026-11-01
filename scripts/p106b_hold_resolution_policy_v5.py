#!/usr/bin/env python3
"""Preserve nominal metadata after explicit anchors without consuming a link.

The first explicit category anchor and every preceding tail line must justify
the boundary. Unknown nominal prefixes or any actual reference label cannot
be silently consumed. Every metadata word/value remains byte-for-byte intact.
"""
from __future__ import annotations

import re
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy_v4 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V5_EXPLICIT_METADATA_START"
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
contextual_repetitions = previous.contextual_repetitions


def metadata_tail(text):
    if previous.intro(text) is None:
        return text, [], False
    lines = text.splitlines(keepends=True)
    entries = [i for i, line in enumerate(lines) if line.strip()]
    tail = []
    for index in reversed(entries):
        value = lines[index].strip()
        if (previous.v1.normalize_heading(value) in previous.LABELS or len(value) > 100
                or previous.REFERENCE.search(value) or not re.search(r"[가-힣]", value)
                or re.search(r"[.!?。]$|[《》\[\]]", value)):
            break
        tail.append(index)
    tail.reverse()
    anchors = [n for n, i in enumerate(tail) if previous.v2.METADATA_YEAR.fullmatch(lines[i].strip())]
    if not anchors:
        return ORIGINAL_METADATA_TAIL(text)
    # Only a known metadata prefix can precede the first explicit year/birth/
    # alive marker. Unknown named references stay outside this proof.
    first = anchors[0]
    if any(not previous.CATEGORY_LINE.fullmatch(lines[i].strip()) for i in tail[:first]):
        return text, [], False
    remove = set()
    for index in reversed(entries[:entries.index(tail[0])]):
        if previous.v1.normalize_heading(lines[index]) in previous.STRIPPABLE_APPENDICES:
            remove.add(index)
        else:
            break
    return "".join(line for i, line in enumerate(lines) if i not in remove), [
        dict(reason="EMPTY_FOOTER_BEFORE_PROVEN_METADATA_START_PRESERVE_ALL_NOMINAL_SUFFIX_WORDS",
             line=i + 1, original=lines[i]) for i in sorted(remove)], True


ORIGINAL_METADATA_TAIL = previous.metadata_tail


def propose(row, individual_hold=False):
    with previous.v2.v2.LOCK, patch.object(previous, "metadata_tail", metadata_tail):
        value = previous.propose(row, individual_hold)
    return dict(value, rules=RULES)
