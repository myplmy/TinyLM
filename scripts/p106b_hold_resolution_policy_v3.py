#!/usr/bin/env python3
"""Equivalent linear subject search for the frozen v2 source-context draft.

The v2 full attempt is preserved as interrupted. This version removes its
quadratic search through long English paragraphs without changing admission
rules, source bodies or code/Unicode protections.
"""
from __future__ import annotations

from functools import lru_cache
import re
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy_v2 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V3_LINEAR_INTRO_SEARCH"
SUBJECT = re.compile(r"(?:은|는)\s+")
PARAGRAPH = re.compile(r"\S[\s\S]*?(?:\n[ \t]*\n|$)")
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
contextual_repetitions = previous.contextual_repetitions


@lru_cache(maxsize=16)
def intro(text):
    for match in PARAGRAPH.finditer(text):
        paragraph = match[0].strip()
        if previous.previous.INTRO_PREDICATE.search(paragraph):
            for subject in SUBJECT.finditer(paragraph):
                prefix = paragraph[:subject.start()].rsplit(chr(10), 1)[-1]
                if prefix.strip():
                    return paragraph
        if chr(10) in paragraph or re.search(r"[.!?。]$", paragraph):
            return None
    return None


def propose(row, individual_hold=False):
    with previous.v2.LOCK, patch.object(previous, "intro", intro):
        result = previous.propose(row, individual_hold)
    return dict(result, rules=RULES)
