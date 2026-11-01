#!/usr/bin/env python3
"""Preserve source calls, styled values and proved complete source structures."""
import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v20 as previous
from scripts import p106b_hold_resolution_preservation_v1 as preservation
from scripts import p106b_hold_resolution_source_calls_v1 as calls
from scripts import p106b_hold_resolution_structure_v1 as structure

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V21_LOCAL_RECORD_STRUCTURES_AND_SOURCE_CALL_PRESERVATION"
v18, v17 = previous.v18, previous.v17
v12, v10, v9, v4, v2, v1 = previous.v12, previous.v10, previous.v9, previous.v4, previous.v2, previous.v1
local_calls_proven = calls.local_calls_proven
proven_source_call_losses = calls.proven_source_call_losses
unicode_examples_preserved = preservation.unicode_examples_preserved
OLD_RENDER = v12.v8.render_presentation
API_NAME = re.compile(r"\A(?P<name>[가-힣][가-힣A-Za-z ·ㆍ-]*[ \t]+(?P<kind>API|SDK))\([ \t]*\)(?P<particle>[ \t]*(?:은|는)[ \t]+)")
QUESTION_UI = re.compile(r"(?mi)^[ \t]*(?:[0-9]+ Answers?[ \t]*\|[ \t]*add yours|"
                         r"Join to answer this question|Join a community of thousands of dedicated teachers and students[.])[ \t]*$")


def __getattr__(name):
    return getattr(previous, name)


def source_api_definition(text):
    first = text.lstrip().split(chr(10) * 2, 1)[0]
    match = API_NAME.match(text.lstrip())
    if (not match or re.search(r"함수|메서드|메소드|변수|호출|인수|수식|표현식", match["name"])
            or not re.search(re.escape(match["kind"]) + r"(?:이다|다)[.!?。]", first)):
        return text, []
    prefix = len(text) - len(text.lstrip())
    lo, hi = prefix + match.start(), prefix + match.end()
    replacement = match["name"] + match["particle"]
    clean = text[:lo] + replacement + text[hi:]
    return clean, [dict(reason="SOURCE_NAMED_API_OR_SDK_DEFINITION_EMPTY_OPTIONAL_ALIAS_ONLY",
                        original=text[lo:hi], replacement=replacement)]


def render_with_source_styles(text):
    clean, changes = OLD_RENDER(text)
    if not previous.semantic_style_preserved(text, clean):
        return text, []
    return clean, changes


def structural_reasons(text, reasons):
    result = set(reasons)
    if structure.actual_repeat_contexts(text):
        result.discard("MAIN_BODY_REPETITION_REQUIRES_CONTEXT")
    if structure.complete_fenced_code_body(text) or structure.complete_markdown_table_body(text):
        result.discard("INDEPENDENT_PROSE_NOT_ESTABLISHED")
    if structure.complete_wiki_tables_cover_markup(text):
        result.discard("BROKEN_TABLE_OR_WIKI_MARKUP")
        result.discard("UNRESOLVED_RAW_TABLE_OR_CLOSING_WIKI_MARKUP")
    if structure.complete_semantic_inline_markup(text):
        result.discard("MARKUP_OR_TRANSCRIPTION_REQUIRES_CONTEXT")
    if local_calls_proven(text):
        result.discard("GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL")
        # Only every actually detected field obtaining a local call proof can
        # remove this generic empty-field diagnosis.
        result.discard("UNRESOLVED_FIELD_OR_TITLE")
    return result


def literal_holes(text):
    with v2.v2.LOCK, patch.object(previous, "local_calls_proven", local_calls_proven):
        reasons = previous.literal_holes(text)
    plain = previous.plain_text(text)
    if any(not previous.QUOTE_CONTEXT.search(plain[max(0, match.start() - 400):match.end()])
           for match in QUESTION_UI.finditer(plain)):
        reasons = set(reasons) | {"OBSERVED_QUESTION_ANSWER_OR_JOIN_UI_REQUIRES_CONTEXT"}
    return sorted(structural_reasons(text, reasons))


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    prepared, api_changes = source_api_definition(original)
    with v2.v2.LOCK, patch.object(previous, "local_calls_proven", local_calls_proven), \
            patch.object(v12.v8, "render_presentation", render_with_source_styles):
        value = previous.propose(dict(row, text=prepared), False)
    clean = value.get("candidate", value["text"])
    clean, restored, losses = calls.restore_source_call_anchors(original, clean)
    reasons = set(value["reasons"]) if value["decision"] == "PENDING" else set()
    reasons.update(literal_holes(clean))
    reasons = structural_reasons(clean, reasons)
    if losses:
        reasons.add("PROVEN_SOURCE_FUNCTION_PARENTHESES_LOST_REQUIRES_CONTEXT_RECOVERY")
    if previous.code_preserved(original, clean) and unicode_examples_preserved(original, clean):
        reasons.discard("CODE_OR_UNICODE_GUARD")
    else:
        reasons.add("CODE_OR_UNICODE_GUARD")
    if not previous.semantic_style_preserved(original, clean):
        reasons.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if not previous.ordered_deletion(original, clean):
        reasons.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
    changes = api_changes + value["changes"] + restored
    if ("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in reasons
            and any(change["reason"] == previous.QUARANTINE for change in changes)
            and previous.separate_metadata_suffix(clean)[2]):
        reasons.add("PARTIAL_QUARANTINE_CANNOT_BORROW_A_METADATA_BOUNDARY_RELEASE")
    if reasons:
        return dict(decision="PENDING", text=original, candidate=clean, reasons=sorted(reasons), changes=changes, rules=RULES)
    return dict(decision="EDIT" if original != clean else "KEEP", text=clean,
                reasons=["ACTUAL_SOURCE_CALLS_VALUES_AND_DISTINCT_RECORD_CONTEXTS_PRESERVED"], changes=changes, rules=RULES)
