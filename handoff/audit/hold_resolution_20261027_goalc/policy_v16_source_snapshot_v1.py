#!/usr/bin/env python3
"""Preserve populated appendices before a proven separate metadata suffix.

Every source value remains literal. Only isolated empty footer paragraphs can
be removed. Newly observed empty named values and unmatched closing brackets
remain pending, including when an older draft called the body terminal.
"""
from __future__ import annotations

import re
from scripts import p106b_hold_resolution_policy_v15 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V16_SEPARATE_METADATA_AND_LITERAL_HOLES"
v12, v10, v9, v4, v2, v1 = previous.v12, previous.v10, previous.v9, previous.v4, previous.v2, previous.v1
code_preserved = previous.code_preserved
unicode_examples_preserved = previous.unicode_examples_preserved
semantic_style_preserved = previous.semantic_style_preserved
contextual_repetitions = previous.contextual_repetitions
MISSING_DECLARATION = previous.MISSING_DECLARATION
ordered_deletion = previous.ordered_deletion
flat_football = previous.flat_football
conflicting_birth_year = previous.conflicting_birth_year
ORIGINAL_CONFLICT = previous.ORIGINAL_CONFLICT
initial_balanced_alias = previous.initial_balanced_alias
explicit_schedule_repetition = previous.explicit_schedule_repetition
intro = v12.intro

CATEGORY = re.compile(v12.CATEGORY.pattern +
    r"|(?:.+의[ _]+(?:당원|군인|모델|연예[ _]*기획사|기타공공기관|"
    r"텔레비전[ _]*진행자|e스포츠[ _]*선수|총리|외무장관|국가원수|"
    r"축구|아나운서|텔레비전|정부)|.+[ _]+(?:문화재자료|수록자|참가자)|"
    r".+[ _]+남자[ _]+축구[ _]+국가대표팀[ _]+선수|육군[ _]+군인|"
    r"침례교도|레지스탕스[ _]+관련자|명나라[ _]+사람|명나라의[ _]+승상|"
    r"홍무제[ _]+때의[ _]+재상|K[0-9]+리그[ _]+구단)")
YEAR = re.compile(v12.YEAR.pattern + r"|[12][0-9]{3}년[ _]+설립된[ _]+(?:텔레비전[ _]+방송국과[ _]+채널|축구단)")
BLOCK = re.compile(r"[^\n]+(?:\n(?![ \t]*\n)[^\n]+)*")
EMPTY_NAME = re.compile(
    r"(?:명칭|성명|본명|원어명|별명)[ \t]*[:：][ \t]*(?=[),;，]|\Z)|"
    r"(?:비자|이름|명칭)[^\n.!?]{0,35}[\"“][ \t]*[\"”]|"
    r"(?:블로그|서적|곡|앨범|이름)[ \t]+(?:''|\"\"|“”|‘’)[ \t]*(?:은|는|이|가)", re.M)


def literal_holes(text):
    plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                    for protected, part in v1.protected_parts(text)[0])
    reasons = []
    if EMPTY_NAME.search(plain):
        reasons.append("OBSERVED_EMPTY_NAMED_VALUE_REQUIRES_SOURCE_REVIEW")
    # The guard does not alter brackets or guess where an opener was lost.
    if plain.count("]") > plain.count("["):
        reasons.append("UNMATCHED_CLOSING_SQUARE_BRACKET_REQUIRES_SOURCE_REVIEW")
    return reasons


def separate_metadata_suffix(text):
    if intro(text) is None:
        return text, [], False
    blocks = list(BLOCK.finditer(text))
    if not blocks:
        return text, [], False
    last = blocks[-1]
    values = [line.strip() for line in last[0].splitlines() if line.strip()]
    # An explicit source birth/death/year/alive marker anchors the separate
    # final paragraph. A pair of arbitrary nouns or an unfilled header cannot.
    if (len(values) < 2 or not any(YEAR.fullmatch(value) for value in values)
            or any(len(value) > 100 or re.search(r"[.!?。《》\[\]<>]", value)
                   or not (YEAR.fullmatch(value) or CATEGORY.fullmatch(value)) for value in values)):
        return text, [], False
    if len(blocks) < 2 or not re.fullmatch(r"[ \t\r\n]+", text[blocks[-2].end():last.start()]):
        return text, [], False
    remove = []
    for block in reversed(blocks[:-1]):
        labels = [v1.normalize_heading(line) for line in block[0].splitlines() if line.strip()]
        if not labels or any(label not in v4.STRIPPABLE_APPENDICES for label in labels):
            break
        remove.append(block)
    clean = text
    changes = []
    for block in remove:
        clean = clean[:block.start()] + clean[block.end():]
        changes.append(dict(reason="ISOLATED_EMPTY_FOOTER_BEFORE_SEPARATE_TYPED_METADATA",
                            original=block[0], source_characters=[block.start(), block.end()]))
    return clean, changes, True


def propose(row, individual_hold=False):
    original = row["text"]
    result = previous.propose(row, individual_hold)
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(result, rules=RULES)
    clean = result.get("candidate", result["text"])
    risks = set(result["reasons"]) if result["decision"] == "PENDING" else set()
    changes = list(result["changes"])
    if "APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT" in risks:
        prepared, new_changes, proven = separate_metadata_suffix(clean)
        if proven:
            clean = prepared
            changes.extend(new_changes)
            risks.discard("APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT")
    risks.update(literal_holes(clean))
    if not code_preserved(original, clean) or not unicode_examples_preserved(original, clean):
        risks.add("CODE_OR_UNICODE_GUARD")
    if not semantic_style_preserved(original, clean):
        risks.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if not ordered_deletion(original, clean):
        risks.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
    if risks:
        return dict(decision="PENDING", text=original, candidate=clean, reasons=sorted(risks), changes=changes, rules=RULES)
    return dict(decision="EDIT" if clean != original else "KEEP", text=clean,
                reasons=["POPULATED_APPENDIX_AND_EXPLICIT_METADATA_VALUES_PRESERVED"], changes=changes, rules=RULES)
