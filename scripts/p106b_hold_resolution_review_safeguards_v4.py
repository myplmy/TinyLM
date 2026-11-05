"""A table declares its first-cell ID; reason-cell references are not decisions."""
import re
from scripts import p106b_hold_resolution_review_safeguards_v3 as previous


def __getattr__(name):
    return getattr(previous, name)


def unparsed_declared_review_ids(payload, parsed_ids, expected):
    text = payload.decode('utf-8') if isinstance(payload, bytes) else payload
    if not previous.DECISION.search(text):
        return set()
    declared = set()
    for line in text.splitlines():
        label = bool(re.match(r'^#{1,6}[ \t]+', line) or
                     re.match(r'^[ \t]*[-*]?[ \t]*\*{0,2}ID\b', line, re.I))
        table = line.startswith('|') and previous.DECISION.search(line)
        if label:
            declared.update(previous.canonical_id(value) for value in previous.EXPLICIT_ID.findall(line))
            bare = re.search(r'\bID[ \t:：]+([0-9]+)\b', line, re.I)
            if bare:
                declared.add('expanded_train:' + bare[1])
        elif table:
            first = line.split('|', 2)[1]
            declared.update(previous.canonical_id(value) for value in previous.EXPLICIT_ID.findall(first))
    return (declared & set(expected)) - set(parsed_ids)
