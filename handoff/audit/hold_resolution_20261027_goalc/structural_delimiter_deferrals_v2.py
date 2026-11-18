"""Recognize mixed-width noncode bracket pairs without changing corpus text."""
import re
from scripts import p106b_hold_resolution_policy_v32 as policy
from structural_delimiter_deferrals_v1 import INTERVAL

WIDTH_PAIRS = str.maketrans('（）［］', '()[]')


def deferrals(text):
    # Only this diagnostic representation is normalized. Code/raw Unicode and
    # every preservation comparison still use the actual unmodified bytes.
    plain = policy.plain_text(text).translate(WIDTH_PAIRS)
    plain = INTERVAL.sub(lambda match: ' ' * len(match[0]), plain)
    plain = re.sub(r'(?m)^[ \t]*(?:[0-9]+|[A-Za-z가-힣])[)](?=[ \t])', ' ', plain)
    stack = []
    for char in plain:
        if char in '([':
            stack.append(char)
        elif char in ')]':
            if not stack or stack.pop() != ('(' if char == ')' else '['):
                return ['UNMATCHED_OR_CROSSED_NONCODE_ROUND_SQUARE_DELIMITER']
    return ['UNMATCHED_NONCODE_OPENING_ROUND_SQUARE_DELIMITER'] if stack else []
