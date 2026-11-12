"""Defer malformed noncode delimiters; preserve typed intervals and list markers."""
import re
from scripts import p106b_hold_resolution_policy_v32 as policy

BOUND=r'(?:[-+−]?(?:\d+(?:[.]\d+)?|∞|[A-Za-z][A-Za-z0-9_]*))'
INTERVAL=re.compile(r'\([ \t]*'+BOUND+r'[ \t]*,[ \t]*'+BOUND+r'[ \t]*\]|\[[ \t]*'+BOUND+r'[ \t]*,[ \t]*'+BOUND+r'[ \t]*\)')


def deferrals(text):
    plain=policy.plain_text(text)
    plain=INTERVAL.sub(lambda m:' '*len(m[0]),plain)
    plain=re.sub(r'(?m)^[ \t]*(?:[0-9]+|[A-Za-z가-힣])[)](?=[ \t])',' ',plain)
    stack=[]
    for char in plain:
        if char in '([':
            stack.append(char)
        elif char in ')]':
            if not stack or stack.pop()!=('(' if char==')' else '['):
                return ['UNMATCHED_OR_CROSSED_NONCODE_ROUND_SQUARE_DELIMITER']
    return ['UNMATCHED_NONCODE_OPENING_ROUND_SQUARE_DELIMITER'] if stack else []
