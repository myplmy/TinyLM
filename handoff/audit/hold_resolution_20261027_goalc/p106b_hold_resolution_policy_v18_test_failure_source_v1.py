#!/usr/bin/env python3
"""Source-first nominal aliases with per-literal programming evidence.

Reuse the existing alias renderer, retain every filled source value, and
leave quantities, formula operands, glyph examples and unknown calls pending.
"""
from __future__ import annotations

import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_policy_v17 as previous

RULES = "RESIDUAL_CONTEXT_RECOVERY_DRAFT_V18_SOURCE_FIRST_NOMINAL_AND_LOCAL_CALL_EVIDENCE"
v12, v10, v9, v4, v2, v1 = previous.v12, previous.v10, previous.v9, previous.v4, previous.v2, previous.v1
FIRST = re.compile(
    r"\A(?P<name>(?:《[^》\n]+》|〈[^〉\n]+〉|「[^」\n]+」|『[^』\n]+』|"
    r"[가-힣][가-힣 ·ㆍ-]+))\((?P<fields>[^()\n]*)\)"
    r"(?P<particle>[ \t]*(?:은|는|란)[ \t]+)")
TYPED = re.compile(r"(?:싱글|앨범|음반|기계장치|음악[ ]*장르|음악의[ ]*형식|"
                   r"낙엽교목|가나|서체)(?:이[다자며]|다[.!?。]|(?:으)?로[ ,]|[ ,])")
ENTITY = re.compile(previous.ENTITY.pattern + "|" + TYPED.pattern)
VALUE_NAME = re.compile(v12.VALUE_NAME.pattern + r"|(?:좌표|순서쌍|행렬|수열|인수|원소|"
                        r"미분|적분|도함수|체온|온도|압력|농도)[ \t]*$")
GLYPH_TEACHING = re.compile(r"문장[ ]*부호|쉼표|반점|따옴표|마침표|괄호[ ]*(?:기호|자체)|"
                           r"빈[ ]*(?:튜플|괄호)|\b(?:empty tuple|punctuation|glyph)\b", re.I)
SPELLED = re.compile(r"[가-힣A-Za-z\u3400-\u9fff\u3040-\u30ff .·ㆍ-]+")
HAN = re.compile(r"[\u3400-\u9fff]")
CALL_NAME = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_:.]*$")
CALL_AFTER = re.compile(r"[ \t]*(?:메서드|메소드|함수|생성자|소멸자|"
                        r"(?:function|method|constructor|destructor)\b)", re.I)
CALL_BEFORE = re.compile(r"(?:\b(?:call|calls|calling|invoke|invokes|invoking|function|method)"
                         r"[ \t]+(?:the[ \t]+)?|(?:함수|메서드|메소드)[ \t]+)$", re.I)
DECLARATION = re.compile(r"^[ \t]*(?:(?:public|private|protected|static|virtual|inline|"
                        r"extern|const|unsigned|signed)[ \t]+)*(?:void|int|char|float|double|"
                        r"bool|long|short|string|String)[ \t*&]+[A-Za-z_][A-Za-z0-9_:]*$")


def __getattr__(name):
    return getattr(previous, name)


def first_nominal_alias(text):
    trimmed = text.lstrip()
    first = trimmed.split(chr(10) * 2, 1)[0]
    match = FIRST.match(trimmed)
    if match is None or VALUE_NAME.search(match["name"]) or GLYPH_TEACHING.search(first):
        return text, []
    fields = match["fields"]
    if not re.search(r"[,，]", fields) or re.search(r"[0-9=+*/<>\\{}\[\]←]", fields):
        return text, []
    pieces = v4.DELIMITERS.split(fields)
    populated = [pieces[index].strip() for index in range(0, len(pieces), 2) if pieces[index].strip()]
    if len(populated) == (len(pieces) + 1) // 2:
        return text, []
    if any(not SPELLED.fullmatch(value) for value in populated):
        return text, []
    quoted = match["name"].startswith(tuple("《〈「『"))
    han_alias = bool(populated and all(HAN.search(value) for value in populated))
    if not quoted and not han_alias and not TYPED.search(first):
        return text, []
    if not re.search(r"[.!?。][ \t]*(?:\r?\n)?$", first):
        return text, []
    # The field formatter and all its value/biography checks already exist.
    # Broader math words elsewhere cannot make a proved name field a tuple.
    never = re.compile(r"(?!)")
    with v2.v2.LOCK, patch.object(v12, "INTRO_NAME", FIRST), \
            patch.object(v12, "intro", lambda value: first), \
            patch.object(v9, "MATH_CONTEXT", never):
        clean, changes = v12.initial_optional_alias(trimmed)
    if not changes:
        return text, []
    prefix = text[:len(text) - len(trimmed)]
    return prefix + clean, [dict(change, reason="SOURCE_FIRST_FILLED_NOMINAL_VALUES_EMPTY_COMMA_FIELDS_ONLY")
                            for change in changes]


def local_calls_proven(text):
    plain = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                    for protected, part in v1.protected_parts(text)[0])
    matches = sorted(list(v1.cache.MISSING_FIELD.finditer(plain)) + list(v10.DANGLING_FIELD.finditer(plain)),
                     key=lambda value: (value.start(), value.end()))
    if not matches:
        return False
    for match in matches:
        if not re.fullmatch(r"\([ \t]*\)", match[0]):
            return False
        line_start = plain.rfind(chr(10), 0, match.start()) + 1
        before = plain[line_start:match.start()]
        name = CALL_NAME.search(before)
        if name is None:
            return False
        right = plain[match.end():]
        if CALL_AFTER.match(right) or CALL_BEFORE.search(before[:name.start()]):
            continue
        # A full typed declaration or standalone terminated call is literal
        # program syntax. A prose abbreviation 'ABC(): agency' is neither.
        if DECLARATION.fullmatch(before) and re.match(r"[ \t]*(?:;|\{)", right):
            continue
        if (not before[:name.start()].strip() and re.match(r"[ \t]*;", right)
                and v9.v6.CALL_CONTEXT.search(plain)):
            continue
        return False
    return True


def literal_holes(text):
    reasons = set(previous.literal_holes(text))
    if v9.v6.ordinary_empty_calls(text) and not local_calls_proven(text):
        reasons.add("GLOBAL_PROGRAM_WORD_DOES_NOT_PROVE_EACH_EMPTY_PAREN_LITERAL")
    return sorted(reasons)


def propose(row, individual_hold=False):
    original = row["text"]
    if individual_hold or row.get("previous_holds") or not row["complete_eos"] or row["id"] == "validation:0":
        return dict(previous.propose(row, individual_hold), rules=RULES)
    prepared, changes = first_nominal_alias(original)
    with v2.v2.LOCK, patch.object(previous, "ENTITY", ENTITY if changes else previous.ENTITY):
        value = previous.propose(dict(row, text=prepared), False)
    clean = value.get("candidate", value["text"])
    risks = set(value["reasons"]) if value["decision"] == "PENDING" else set()
    risks.update(literal_holes(clean))
    if local_calls_proven(clean):
        risks.discard("UNRESOLVED_FIELD_OR_TITLE")
    if not previous.code_preserved(original, clean) or not previous.unicode_examples_preserved(original, clean):
        risks.add("CODE_OR_UNICODE_GUARD")
    if not previous.semantic_style_preserved(original, clean):
        risks.add("SOURCE_STYLE_VALUE_REQUIRES_LITERAL_OR_AUTHORED_PRESERVATION")
    if not previous.ordered_deletion(original, clean):
        risks.add("NONWHITESPACE_ADDITION_OR_REORDER_REQUIRES_AUTHORED_REVIEW")
    changes += value["changes"]
    if risks:
        return dict(decision="PENDING", text=original, candidate=clean, reasons=sorted(risks), changes=changes, rules=RULES)
    return dict(decision="EDIT" if original != clean else "KEEP", text=clean,
                reasons=["SOURCE_NOMINAL_VALUES_AND_LOCALLY_PROVEN_CALL_LITERALS_PRESERVED"],
                changes=changes, rules=RULES)
