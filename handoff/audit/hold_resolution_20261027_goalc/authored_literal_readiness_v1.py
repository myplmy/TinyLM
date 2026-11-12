"""Conservative deferrals for an already authored, lossless-only admission batch.

These checks do not delete text or establish general semantic correctness.
"""
import re
from scripts import p106b_hold_policy as native
from scripts import p106b_hold_resolution_policy_v30 as policy

CATALOG = re.compile(r'(?im)^\s*[-*]?\s*(?:Item No|Vendor)\s*:')
OCR_AFFILIATION = re.compile(r'(?m)^[A-ZÅÆØ][^\n:]{0,100},[ \t]+/[A-Za-z]')


def deferrals(text):
    plain = policy.plain_text(text)
    reasons = []
    if ((native.DANGLING_FIELD.search(plain) or native.cache.MISSING_FIELD.search(plain))
            and not policy.local_calls_proven(text)):
        reasons.append('NATIVE_UNRESOLVED_FIELD_NOT_LOCALLY_PROVEN')
    for block in re.split(r'\n\s*\n', plain):
        value = block.strip()
        if (len(value) >= 70 and len(value.split()) >= 8
                and re.search(r'[가-힣]$', value)
                and not re.search(r'(?:다|음|임|함|됨|있음|없음|하기|한다|이다)$', value)):
            reasons.append('POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT')
            break
    if text.count('“') != text.count('”'):
        reasons.append('UNBALANCED_CURLY_DOUBLE_QUOTES_NEED_CONTEXT')
    if CATALOG.search(text):
        reasons.append('RETAIL_CATALOG_FIELDS_STILL_NEED_CONTEXT')
    if OCR_AFFILIATION.search(text):
        reasons.append('POSSIBLE_OCR_AFFILIATION_NEEDS_CONTEXT')
    return reasons
