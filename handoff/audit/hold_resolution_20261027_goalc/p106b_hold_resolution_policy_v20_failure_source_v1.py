#!/usr/bin/env python3
"""Keep calls proved by their actual local syntax and preserve filled aliases.

This extension never executes a program, supplies a parameter, or repairs a
formula. Unknown fields retain the existing pending behavior.
"""
from __future__ import annotations

import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v19 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V20_LOCAL_DECLARATION_AND_LITERAL_SOURCE_VALUES"
v18 = previous.previous
v17 = v18.previous
v12, v10, v9, v4, v2, v1 = previous.v12, previous.v10, previous.v9, previous.v4, previous.v2, previous.v1
OLD_LOCAL_CALLS = v18.local_calls_proven
DECLARED_FUNCTION = re.compile(
    r"\b(?:(?:void|int|char|float|double|bool|long|short|String|Object|Class|FILE)"
    r"[ \t*&]+|(?:function|def)[ \t]+)([A-Za-z_$][A-Za-z0-9_$]*)[ \t]*\(")
ASSIGNMENT = re.compile(
    r"^[ \t]*(?:(?:const|let|var|final|static)[ \t]+)?"
    r"(?:(?:[A-Za-z_$][A-Za-z0-9_$<>\[\]]*)[ \t*&]+)?"
    r"[A-Za-z_$][A-Za-z0-9_$.\[\]]*[ \t]*=(?!=)")
LOCAL_MEMBER_ROLE = re.compile(
    r"\b(?:class|object|instance|method|constructor|ClassLoader|FileStream)\b|"
    r"클래스|객체|인스턴스|메서드|메소드|호출", re.I)
CALL_SUFFIX_ROLE = re.compile(
    r"[ \t]*(?:(?:is|was|can be|will be)[ \t]+(?:called|invoked)|"
    r"(?:returns?|calls?|invokes?)[ \t]|(?:함수|메서드|메소드)(?:는|의|를|가|이)?[ \t])", re.I)
QUOTE_CONTEXT = re.compile(
    r"인용|문구|예문|문자열|quoted|quotation|example of|"
    r"following (?:message|text|quote)|(?:banner|advertisement|button) (?:says|reads)", re.I)
UI = re.compile(
    r"(?mi)^[ \t]*(?:Didn't find what you are looking for on this page\? Try search:|"
    r"Sign up for the free IntMath Newsletter\.|Algebra Lessons on DVD|"
    r"Below are some of our articles that explain how and why it is important to support immune health:)")
EXTRA_EMPTY_LEAF = {v1.normalize_heading(value) for value in ["음반외활동", "음반 외 활동", "TV 프로그램", "TV프로그램"]}
CONTRAST_ALIAS = re.compile(r"(?P<cue>반댓말은[ \t]+)(?P<name>[가-힣][가-힣 ·ㆍ-]+)\([ \t]*\)(?=으로,[ \t]+)")


def __getattr__(name):
    return getattr(previous, name)


def plain_text(text):
    return "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                   for protected, part in v1.protected_parts(text)[0])


def local_calls_proven(text):
    if OLD_LOCAL_CALLS(text):
        return True
    plain = plain_text(text)
    hits = sorted(list(v1.cache.MISSING_FIELD.finditer(plain)) + list(v10.DANGLING_FIELD.finditer(plain)),
                  key=lambda value: (value.start(), value.end()))
    if not hits:
        return False
    declared = {match[1] for match in DECLARED_FUNCTION.finditer(text)}
    for match in hits:
        if not re.fullmatch(r"\([ \t]*\)", match[0]):
            return False
        start = plain.rfind(chr(10), 0, match.start()) + 1
        end = plain.find(chr(10), match.end())
        end = len(plain) if end < 0 else end
        before, after = plain[start:match.start()], plain[match.end():end]
        name = v18.CALL_NAME.search(before)
        if name is None:
            return False
        symbol = name[0]
        if v18.CALL_AFTER.match(after) or v18.CALL_BEFORE.search(before[:name.start()]):
            continue
        if symbol in declared or symbol.split(".")[-1] in declared:
            continue
        # A named empty-argument definition has its own actual syntax.
        if (not before[:name.start()].strip() and re.match(r"[ \t]*\{", after)):
            continue
        if re.fullmatch(r"[ \t]*(?:async[ \t]+)?def[ \t]+", before[:name.start()]) and re.match(r"[ \t]*:", after):
            continue
        # An assignment prefix belongs to this same source line; a program
        # word elsewhere cannot establish it for an abbreviation.
        if ASSIGNMENT.match(before) and before.rstrip().endswith(symbol) and re.search(r";[ \t]*$", after):
            continue
        if (re.search(r"\bnew[ \t]+$", before[:name.start()])
                and re.match(r"[ \t]*(?:[;,.\)]|$)", after)):
            continue
        if CALL_SUFFIX_ROLE.match(after):
            continue
        # A source-named lower-case member, together with an explicit local
        # object/class role, is a retained method reference, never an alias.
        if ("." in symbol and re.match(r"[a-z_][A-Za-z0-9_]*$", symbol.rsplit(".", 1)[-1])
                and LOCAL_MEMBER_ROLE.search(plain[start:end])
                and not re.match(r"[ \t]*:", after)):
            continue
        return False
    return True


def source_nominal_separators(text):
    trimmed = text.lstrip()
    first = trimmed.split(chr(10) * 2, 1)[0]
    match = v18.FIRST.match(trimmed)
    if (match is None or v18.VALUE_NAME.search(match["name"]) or v18.GLYPH_TEACHING.search(first)
            or not re.search(r"[.!?。][ \t]*(?:\r?\n)?$", first)):
        return text, []
    fields = match["fields"]
    if re.search(r"[0-9=+*/<>\\{}\[\]←]", fields):
        return text, []
    populated = [value.strip() for value in re.split(r"[,，;；]", fields) if value.strip()]
    if (len(populated) < 2 or not any(v18.HAN.search(value) for value in populated)
            or not any(re.search(r"[가-힣]", value) for value in populated)
            or any(not v18.SPELLED.fullmatch(value) for value in populated)):
        return text, []
    cleaned = re.sub(r"[,，](?=[ \t]*[;；])", "", fields)
    if cleaned == fields:
        return text, []
    prefix = len(text) - len(trimmed)
    lo, hi = prefix + match.start("fields"), prefix + match.end("fields")
    result = text[:lo] + cleaned + text[hi:]
    changes = [dict(reason="FILLED_HAN_AND_HANGUL_ALIAS_VALUES_RETAIN_LITERAL_SEMICOLON",
                    original=fields, replacement=cleaned, source_characters=[lo, hi])]
    # Only the explicit opposite-name definition in the very same completed
    # introductory paragraph obtains this optional-empty-alias proof.
    end = len(result.split(chr(10) * 2, 1)[0])
    head, tail = result[:end], result[end:]
    def opposite(value):
        if v18.VALUE_NAME.search(value["name"]):
            return value[0]
        replacement = value["cue"] + value["name"]
        changes.append(dict(reason="EXPLICIT_OPPOSITE_NOMINAL_NAME_EMPTY_OPTIONAL_ALIAS_ONLY",
                            original=value[0], replacement=replacement))
        return replacement
    return CONTRAST_ALIAS.sub(opposite, head) + tail, changes


def source_cta(text):
    output, changes = [], []
    for protected, part in v1.protected_parts(text)[0]:
        if protected:
            output.append(part)
            continue
        preceding = ""
        for line in part.splitlines(keepends=True):
            # Reuse the original exact full-line CTA recognizer.
            if v2.previous.CTA.fullmatch(line.strip()) and not QUOTE_CONTEXT.search(preceding[-1000:]):
                changes.append(dict(reason="UNQUOTED_EXACT_ASSESSMENT_OR_ORDER_CTA_SOURCE_LINE", original=line))
            else:
                output.append(line)
            preceding += line
    return "".join(output), changes


def literal_holes(text):
    with v2.v2.LOCK, patch.object(v18, "local_calls_proven", local_calls_proven):
        reasons = set(previous.literal_holes(text))
    plain = plain_text(text)
    if any(not QUOTE_CONTEXT.search(plain[max(0, match.start() - 400):match.end()])
           for match in UI.finditer(plain)):
        reasons.add("OBSERVED_SEARCH_SUBSCRIPTION_OR_PROMOTIONAL_PREVIEW_REQUIRES_CONTEXT")
    return sorted(reasons)


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    prepared, alias_changes = source_nominal_separators(original)
    prepared, cta_changes = source_cta(prepared)
    with v2.v2.LOCK, patch.object(v18, "local_calls_proven", local_calls_proven), \
            patch.object(v17, "EMPTY_LEAF_LABELS", v17.EMPTY_LEAF_LABELS | EXTRA_EMPTY_LEAF):
        value = previous.propose(dict(row, text=prepared), False)
    clean = value.get("candidate", value["text"])
    reasons = set(value["reasons"]) if value["decision"] == "PENDING" else set()
    reasons.update(literal_holes(clean))
    if not previous.code_preserved(original, clean) or not previous.unicode_examples_preserved(original, clean):
        reasons.add("CODE_OR_UNICODE_GUARD")
    if not previous.semantic_style_preserved(original, clean):
        reasons.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if not previous.ordered_deletion(original, clean):
        reasons.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
    changes = alias_changes + cta_changes + value["changes"]
    if reasons:
        return dict(decision="PENDING", text=original, candidate=clean, reasons=sorted(reasons), changes=changes, rules=RULES)
    return dict(decision="EDIT" if original != clean else "KEEP", text=clean,
                reasons=["SOURCE_LOCAL_CALL_DECLARATIONS_AND_FILLED_VALUES_PRESERVED"], changes=changes, rules=RULES)
