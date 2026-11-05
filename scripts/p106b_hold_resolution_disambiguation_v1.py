"""Narrow source proofs for empty aliases in declared Korean name lists.

Reuse existing nominal/value/code guards.  Only blank optional fields change;
filled names, lifespan endpoints and every other source character remain.
"""
import re
from unittest.mock import patch

from scripts import p106b_hold_resolution_policy_v6 as nominal
from scripts import p106b_hold_resolution_policy_v26 as safeguards

DECLARATION = re.compile(
    r"\A[ \t]*(?P<name>[가-힣A-Za-z0-9·ㆍ《》〈〉「」『』'’\"“”‘’ _-]+?)"
    r"(?:\([ \t]*\))?[ \t]*(?:은|는)[ \t]+다음(?:과[ \t]*같은)?[ \t]*"
    r"(?P<claim>사람(?:들)?을[ \t]*가리킨다|을[ \t]*가리킨다|"
    r"뜻으로[ \t]*쓰인다|(?:뜻|의미)(?:이|가)?[ \t]*있다)[.!?。][ \t]*\Z")
LIFESPAN_EMPTY_ALIAS = re.compile(
    r"\A(?P<empty>[ \t]*[,，][ \t]*)(?P<dates>[0-9]{1,4}(?:년)?[ \t]*"
    r"[~〜–-][ \t]*(?:[0-9]{1,4}(?:년)?)?[ \t]*)\Z")
LITERAL_OR_VALUE = re.compile(
    r"빈[ \t]*(?:괄호|튜플|문자열|인수|인자)|괄호[ \t]*(?:표기|문법)|"
    r"튜플|표현식|구문|문법|호출|인수|인자|전사|좌표|"
    r"\b(?:def|function|return|class|lambda|tuple|syntax|call)\b", re.I)
NAME_TOKEN = re.compile(r"([가-힣A-Za-z0-9][가-힣A-Za-z0-9_·ㆍ-]*)[》〉」』‘’“”'\"]?[ \t]*$")
OLD_NOMINAL_CONTEXT = nominal.nominal_context


def declared_name_list(text):
    first = text.lstrip().splitlines()[0] if text.strip() else ''
    match = DECLARATION.fullmatch(first)
    if match is None or not re.search(r'[가-힣]', match['name']):
        return None
    if nominal.MATH_CONTEXT.search(match['name']) or nominal.EMPTY_VALUE_NAME.search(match['name']):
        return None
    return dict(header=first, name=match['name'], people=match['claim'].startswith('사람'))


def source_named_aliases(text):
    declaration = declared_name_list(text)
    parts, opened = nominal.v1.protected_parts(text)
    if declaration is None or opened or safeguards.QUOTE_CONTEXT.search(text):
        return text, []
    output, changes = [], []
    header_seen = False
    for protected, part in parts:
        if protected:
            output.append(part)
            continue
        for line in part.splitlines(keepends=True):
            is_header = not header_seen and bool(line.strip())
            if line.strip():
                header_seen = True
            if (line.lstrip().startswith('>') or nominal.MATH_CONTEXT.search(line)
                    or nominal.v2.PROGRAMMING.search(line) or LITERAL_OR_VALUE.search(line)):
                output.append(line)
                continue

            def permitted(value, match):
                if not OLD_NOMINAL_CONTEXT(value, match):
                    return False
                token = NAME_TOKEN.search(value[:match.start()])
                if token is None or not re.search(r'[가-힣]', token[1]):
                    return False
                after = value[match.end():]
                # A populated description or an explicit people-list sentence
                # binds the already present name.  Bare unknown fields stay.
                return bool(is_header or re.match(r'[ \t]*[:：][ \t]*\S', after)
                    or declaration['people'] and re.match(r'[ \t]*(?:은|는|이|가)[ \t]+\S', after))

            with nominal.v2.v2.LOCK, patch.object(nominal, 'identified', lambda value: True), \
                    patch.object(nominal, 'nominal_context', permitted):
                clean, ordinary = nominal.name_slots(line)
            for change in ordinary:
                changes.append(dict(change, source_declared_list=declaration['header']))

            def lifespan(match):
                if not permitted(clean, match):
                    return match[0]
                found = LIFESPAN_EMPTY_ALIAS.fullmatch(match[1])
                if found is None:
                    return match[0]
                replacement = '(' + found['dates'] + ')'
                changes.append(dict(reason='DECLARED_NAME_LIST_EMPTY_ALIAS_BEFORE_LITERAL_LIFESPAN',
                    original=match[0], replacement=replacement,
                    source_declared_list=declaration['header'],
                    filled_lifespan_literal=found['dates'], inferred_name_or_date_added=False))
                return replacement

            output.append(nominal.NOMINAL_GROUP.sub(lifespan, clean))
    return ''.join(output), changes
