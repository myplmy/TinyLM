"""Preserve proved source structures and explicitly typed empty name aliases."""
import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v21 as previous
from scripts import p106b_hold_resolution_structure_v2 as structure

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V22_PROVED_WHOLE_CODE_AND_NAMED_TABLE_AXES"
v12, v10, v9, v4, v2, v1 = previous.v12, previous.v10, previous.v9, previous.v4, previous.v2, previous.v1
OLD_STRUCTURAL = previous.structural_reasons
KINDS = r"가산기|알고리즘|정리|공리|법칙|가설|방정식|분포|공간|다양체|학문|이론|기법"
TYPED_ALIAS = re.compile(
    r"\A[ \t]*(?P<name>[가-힣A-Za-z0-9·ㆍ _'’\-]*(?P<kind>" + KINDS + r"))"
    r"(?P<alias>\([ \t]*\))(?P<particle>[ \t]*(?:은|는|란)[ \t]+)")
NOT_ALIAS = re.compile(r"괄호|빈[ \t]*(?:인수|인자|튜플)|문법|코드|호출|인수|인자|U[+]|[=∈∉∀∃]")


def __getattr__(name):
    return getattr(previous, name)


def typed_initial_alias(text):
    match = TYPED_ALIAS.match(text)
    if match is None:
        return text, []
    prefix = match["name"][:-len(match["kind"])].strip()
    if not re.search(r"[가-힣A-Za-z0-9]", prefix):
        return text, []
    remainder = text[match.end():].split(chr(10), 1)[0]
    end = re.search(r"[.!?。](?:[ \t]|\Z)", remainder)
    sentence = remainder[:end.end()] if end else ""
    if (not sentence or NOT_ALIAS.search(sentence)
            or not re.search(re.escape(match["kind"]) + r"(?:이다|의[ \t]+한[ \t]+종류이다)[.!?。]", sentence)):
        return text, []
    lo, hi = match.span("alias")
    return text[:lo] + text[hi:], [dict(
        reason="SOURCE_TYPED_NAMED_DEFINITION_EMPTY_OPTIONAL_ALIAS_ONLY", original=text[lo:hi],
        replacement="", source_characters=[lo, hi], source_name=match["name"], explicit_kind=match["kind"])]


def code_preserved(original, clean):
    if previous.code_preserved(original, clean):
        return True
    prepared, proof = typed_initial_alias(original)
    return bool(proof and previous.code_preserved(prepared, clean))


def structural_reasons(text, reasons):
    with v2.v2.LOCK, patch.object(previous.structure, "complete_wiki_tables_cover_markup", structure.complete_tables_with_explicit_blanks):
        result = OLD_STRUCTURAL(text, reasons)
    if structure.complete_source_program(text):
        result.difference_update({"MAIN_BODY_REPETITION_REQUIRES_CONTEXT", "INDEPENDENT_PROSE_NOT_ESTABLISHED",
                                 "GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL",
                                 "UNRESOLVED_FIELD_OR_TITLE"})
    elif structure.complete_source_table_body(text):
        result.difference_update({"MAIN_BODY_REPETITION_REQUIRES_CONTEXT", "INDEPENDENT_PROSE_NOT_ESTABLISHED"})
    return result


def literal_holes(text):
    with v2.v2.LOCK, patch.object(previous, "structural_reasons", structural_reasons), \
            patch.object(previous.structure, "complete_wiki_tables_cover_markup", structure.complete_tables_with_explicit_blanks):
        return previous.literal_holes(text)


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    prepared, aliases = typed_initial_alias(original)
    with v2.v2.LOCK, patch.object(previous, "structural_reasons", structural_reasons), \
            patch.object(previous.structure, "complete_wiki_tables_cover_markup", structure.complete_tables_with_explicit_blanks):
        value = previous.propose(dict(row, text=prepared), False)
    clean = value.get("candidate", value["text"])
    reasons = set(value["reasons"]) if value["decision"] == "PENDING" else set()
    reasons.update(literal_holes(clean))
    reasons = structural_reasons(clean, reasons)
    if code_preserved(original, clean) and previous.unicode_examples_preserved(original, clean):
        reasons.discard("CODE_OR_UNICODE_GUARD")
    else:
        reasons.add("CODE_OR_UNICODE_GUARD")
    if not previous.semantic_style_preserved(original, clean):
        reasons.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if not previous.ordered_deletion(original, clean):
        reasons.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
    changes = aliases + value["changes"]
    if reasons:
        return dict(decision="PENDING", text=original, candidate=clean, reasons=sorted(reasons), changes=changes, rules=RULES)
    return dict(decision="EDIT" if original != clean else "KEEP", text=clean,
                reasons=["SOURCE_PROGRAM_OR_NAMED_STRUCTURE_VALUES_PRESERVED"], changes=changes, rules=RULES)
