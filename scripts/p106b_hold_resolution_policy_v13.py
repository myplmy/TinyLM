#!/usr/bin/env python3
"""Preserve complete clauses, date words and meaningful source presentation.

The v12 counterexamples remain frozen. A family-history paragraph containing
the word '생년월일' has no missing date merely because it contains 년월일. Colour
and source-declared emphasis cannot be discarded as presentation-only noise.
"""
from __future__ import annotations

from collections import Counter
import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v12 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V13_SOURCE_CLAUSES_AND_STYLE_VALUES"
v10, v9, v4, v2, v1 = previous.v10, previous.v9, previous.v4, previous.v2, previous.v1
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
contextual_repetitions = previous.contextual_repetitions
MISSING_DECLARATION = previous.MISSING_DECLARATION
ORIGINAL_QUARANTINE = v10.ORIGINAL_QUARANTINE
MISSING_STATISTIC = re.compile(v4.MISSING_STATISTIC.pattern.replace(
    r"년\s*월\s*일", r"(?<![가-힣])년[ \t]+월[ \t]+일"))
OPEN_TAG = re.compile(r"<[A-Za-z][^<>\n]*>")
STYLE_ATTRIBUTE = re.compile(r"\b(?:style|color)\s*=", re.I)
STYLED_ELEMENT = re.compile(r"<(?P<tag>span|font|b|strong|i|em|u)\b(?P<attrs>[^<>]*)>"
                            r"[^<>]*</(?P=tag)\s*>", re.I)
EMPHASIS = re.compile(r"<\s*/?\s*(?:b|strong|i|em|u)\s*>", re.I)
LEGEND = re.compile(r"굵은\s*글씨|굵게|기울임|이탤릭|색상|파란색|빨간색|초록색|"
                    r"\b(?:bold|italics?|highlight|colou?r)\b", re.I)


def semantic_style_preserved(original, cleaned):
    """Exact source styling is retained unless separately authored and reviewed.

    This only rejects an automatic loss. A valid source HTML span is not an
    error merely because it appears in a pattern count.
    """
    def fragments(text, emphasis):
        found = [match[0] for match in OPEN_TAG.finditer(text) if STYLE_ATTRIBUTE.search(match[0])]
        found += [match[0] for match in STYLED_ELEMENT.finditer(text) if STYLE_ATTRIBUTE.search(match["attrs"])]
        if emphasis:
            found += EMPHASIS.findall(text)
            found += [match[0] for match in STYLED_ELEMENT.finditer(text) if match["tag"].lower() in {"b", "strong", "i", "em", "u"}]
        return Counter(found)
    emphasis = bool(LEGEND.search(original))
    return fragments(original, emphasis) == fragments(cleaned, emphasis)


def source_clause_quarantine(text):
    candidate, changes = ORIGINAL_QUARANTINE(text)
    for change in changes:
        block = change["original"].strip()
        if not block or not v9.value_damage(block):
            continue
        # A short paragraph can contain both a real hole and complete source
        # statements. Length/line limits alone cannot justify losing the latter.
        pieces = [piece.strip() for piece in re.split(r"(?<=[.!?。])(?:[ \t]+|\n+)", block) if piece.strip()]
        for piece in pieces:
            if (not v9.value_damage(piece) and not v9.section_label(piece)
                    and not v10.STRONG_DEPENDENT.search(piece)):
                return text, []
    return candidate, changes


def propose(row, individual_hold=False):
    original = row["text"]
    with v2.v2.LOCK, patch.object(v4, "MISSING_STATISTIC", MISSING_STATISTIC), \
            patch.object(v10, "ORIGINAL_QUARANTINE", source_clause_quarantine):
        result = previous.propose(row, individual_hold)
    final = result.get("candidate", result["text"])
    risks = set(result["reasons"]) if result["decision"] == "PENDING" else set()
    if result["decision"] in {"KEEP", "EDIT", "PENDING"} and not semantic_style_preserved(original, final):
        risks.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if risks:
        return dict(decision="PENDING", text=original, candidate=final, reasons=sorted(risks),
                    changes=result["changes"], rules=RULES)
    return dict(result, rules=RULES)
