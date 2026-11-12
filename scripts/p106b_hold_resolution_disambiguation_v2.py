"""Reuse proved alias edits for additional explicitly declared name lists."""
import re
from unittest.mock import patch
from scripts import p106b_hold_resolution_disambiguation_v1 as previous

ORIGINAL_DECLARATION=previous.declared_name_list
NAME=r"(?P<name>[가-힣A-Za-z0-9·ㆍ《》〈〉「」『』'’\"“”‘’ _-]+?)"
OPTIONAL=r"(?:\([ \t]*\))?[ \t]*"
PATTERNS=[
    (re.compile(r'\A[ \t]*'+NAME+OPTIONAL+r'(?:은|는)[ \t]+[가-힣]+어권에서[ \t]+쓰이는[ \t]+(?:이름|성씨|성)이다[.!?。][ \t]*\Z'),True),
    (re.compile(r'\A[ \t]*'+NAME+OPTIONAL+r'(?:은|는)[ \t]+[가-힣]+(?:어|의)[ \t]+이름으로[ \t]+다음[ \t]+사람을[ \t]+가리킨다[.!?。][ \t]*\Z'),True),
    (re.compile(r'\A[ \t]*'+NAME+OPTIONAL+r'(?:이?라는)[ \t]+이름을[ \t]+가진[ \t]+사람은[ \t]+다음과[ \t]+같다[.!?。][ \t]*\Z'),True),
    (re.compile(r'\A[ \t]*이름이[ \t]+'+NAME+OPTIONAL+r'인[ \t]+사람으로는[ \t]+다음이[ \t]+있다[.!?。][ \t]*\Z'),True),
    (re.compile(r'\A[ \t]*'+NAME+OPTIONAL+r'의[ \t]+다른[ \t]+뜻은[ \t]+다음과[ \t]+같다[.!?。][ \t]*\Z'),False),
    (re.compile(r'\A[ \t]*'+NAME+OPTIONAL+r'(?:에는|은|는)[ \t]+다음[ \t]+등을[ \t]+가리킨다[.!?。][ \t]*\Z'),False),
    (re.compile(r'\A[ \t]*'+NAME+OPTIONAL+r'에는[ \t]+다음[ \t]+뜻이[ \t]+있다[.!?。][ \t]*\Z'),False),
]


def declared_name_list(text):
    existing=ORIGINAL_DECLARATION(text)
    if existing is not None:return existing
    first=text.lstrip().splitlines()[0] if text.strip() else ''
    for pattern,people in PATTERNS:
        found=pattern.fullmatch(first)
        if found is None:continue
        name=found['name']
        if (not re.search(r'[가-힣]',name) or previous.nominal.MATH_CONTEXT.search(name)
                or previous.nominal.EMPTY_VALUE_NAME.search(name)):
            continue
        return dict(header=first,name=name,people=people)
    return None


def balanced_prose_parentheses(text):
    depth=0
    for protected,part in previous.nominal.v1.protected_parts(text)[0]:
        if protected:continue
        for char in part:
            if char=='(':depth+=1
            elif char==')':
                depth-=1
                if depth<0:return False
    return depth==0


def unnamed_value_row(text):
    for protected,part in previous.nominal.v1.protected_parts(text)[0]:
        if protected:continue
        for line in part.splitlines():
            if re.match(r'^[ \t]*(?:[-*•][ \t]*)?\([ \t]*(?:[0-9?]|[,，])[^()\n]*\)[ \t]*\S',line):
                return True
    return False


def source_named_aliases(text):
    if (declared_name_list(text) is None or not balanced_prose_parentheses(text)
            or unnamed_value_row(text)):
        return text,[]
    with patch.object(previous,'declared_name_list',declared_name_list):
        return previous.source_named_aliases(text)
