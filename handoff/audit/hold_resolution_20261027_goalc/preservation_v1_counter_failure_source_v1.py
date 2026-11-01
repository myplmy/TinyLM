#!/usr/bin/env python3
"""Protect actual Unicode examples and their values, not an absent glyph."""
from collections import Counter
import re
from scripts import p106b_hold_resolution_policy_v20 as previous

EXAMPLE = re.compile(r"(?i)(U\+[0-9A-F]{4,6})\s*[(（]([^()（）\n]*)[)）]")


def unicode_examples_preserved(original, cleaned):
    if previous.unicode_examples_preserved(original, cleaned):
        return True
    filled = Counter(match[0] for match in EXAMPLE.finditer(original) if match[2].strip())
    actual = Counter(match[0] for match in EXAMPLE.finditer(cleaned) if match[2].strip())
    if any(actual[value] != count for value, count in filled.items()):
        return False
    removed_empty = {match[1] for match in EXAMPLE.finditer(original)
                     if not match[2].strip() and cleaned.count(match[0]) != original.count(match[0])}
    if not removed_empty:
        return False
    # Even an empty example's codepoint value may not disappear or acquire
    # a fabricated glyph. Each such literal value must retain its count.
    for codepoint in removed_empty:
        pattern = re.compile(re.escape(codepoint) + r"(?![0-9A-Fa-f])")
        if len(pattern.findall(original)) != len(pattern.findall(cleaned)):
            return False
        if any(match[1] == codepoint and match[2].strip() for match in EXAMPLE.finditer(cleaned)):
            if not any(match[1] == codepoint and match[2].strip() for match in EXAMPLE.finditer(original)):
                return False
    return True
