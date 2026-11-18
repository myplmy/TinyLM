"""Discharge a prose-ending heuristic only for unchanged, explicit list records."""
from collections import Counter
import re
from authored_literal_readiness_v1 import deferrals
from verify_rule27_literal_delta_v1 import literal_stream

PROSE = 'POSSIBLE_UNFINISHED_KOREAN_PROSE_NEEDS_CONTEXT'
RELATED_HEADINGS = frozenset({'같이 보기', '같이보기', '더 보기', '더보기', '관련 항목', '관련항목'})
HEADER = re.compile(r'[^.!?。:;{}\[\]<>`=]{1,50}')
INCOMPLETE_END = re.compile(r'(?:[은는을를의]|에서|으로|위해|위한|하여|하며|하고|이고|이며|지만|때문에|따라서|또는|그리고|및|경우|때|\s인|\s하는|\s되는|\s있는|\s없는|\s같은)$')
ROSTER_HEADER = re.compile(r'.+?휘하\s+원수(?:\s+(\d+)명)?(?:[,，]\s*\d{3,4}[~–-]\d{3,4})?')
APPOINTMENT = re.compile(r'\d{3,4}년\s+(?:프랑스\s+)?원수\s+임명$')


def lines(block):
    return [value.strip() for value in block.splitlines() if value.strip()]


def complete_value(value):
    return len(value.strip()) >= 2 and not INCOMPLETE_END.search(value.strip())


def classify_block(block):
    values = lines(block)
    if len(values) < 2 or any(value.startswith(('```', '~~~', '>', '{|')) for value in values):
        return None
    first, rest = values[0], values[1:]
    if first in RELATED_HEADINGS:
        for value in rest:
            if ' - ' not in value:
                return None
            label, description = value.split(' - ', 1)
            if not complete_value(label) or not complete_value(description):
                return None
        return dict(kind='EXPLICIT_RELATED_ENTRY_WITH_POPULATED_DESCRIPTION', records=len(rest))
    roster = ROSTER_HEADER.fullmatch(first)
    if roster and all(APPOINTMENT.search(value) for value in rest):
        count = roster[1]
        if count is not None and int(count) != len(rest):
            return None
        return dict(kind='SOURCE_NAMED_MARSHAL_APPOINTMENT_ROSTER', records=len(rest),
                    uniform_birth_fields_not_required=True, declared_count_matches=count is None or int(count) == len(rest))
    if HEADER.fullmatch(first) and len(rest) >= 2:
        for value in rest:
            if ':' not in value:
                return None
            name, description = value.split(':', 1)
            if not 1 <= len(name.strip()) <= 80 or not complete_value(description):
                return None
            if re.search(r'[.!?。{}<>`=]', name):
                return None
        return dict(kind='SOURCE_HEADING_AND_POPULATED_TERM_DEFINITION_ROWS', records=len(rest))
    return None


def line_key(block):
    return tuple(literal_stream(value) for value in lines(block))


def context_deferrals(original, body):
    reasons = list(deferrals(body))
    if PROSE not in reasons:
        return reasons, dict(flag_present=False, discharged=False, anchors=[])
    source_blocks = list(re.finditer(r'(?s)\S.*?(?=\n\s*\n|\Z)', original))
    body_blocks = [match for match in re.finditer(r'(?s)\S.*?(?=\n\s*\n|\Z)', body)
                   if PROSE in deferrals(match[0])]
    anchors, previous_source = [], -1
    for block in body_blocks:
        role = classify_block(block[0])
        if role is None:
            return reasons, dict(flag_present=True, discharged=False, anchors=anchors,
                                 unresolved_body_span=list(block.span()), reason='NOT_AN_EXPLICIT_LISTING_ROLE')
        match = next((item for item in source_blocks if item.start() >= previous_source
                      and line_key(item[0]) == line_key(block[0]) and classify_block(item[0]) == role), None)
        if match is None:
            return reasons, dict(flag_present=True, discharged=False, anchors=anchors,
                                 unresolved_body_span=list(block.span()), reason='SOURCE_RECORD_LAYOUT_OR_VALUES_DIFFER')
        previous_source = match.end()
        anchors.append(dict(source_span=list(match.span()), body_span=list(block.span()), **role))
    if not body_blocks:
        return reasons, dict(flag_present=True, discharged=False, anchors=[], reason='NO_EXACT_FLAGGED_BLOCK_FOUND')
    reasons.remove(PROSE)
    return reasons, dict(flag_present=True, discharged=True, anchors=anchors,
                         types=dict(Counter(value['kind'] for value in anchors)),
                         all_flagged_blocks_are_existing_source_lists=True,
                         source_line_values_and_order_preserved=True, source_or_body_edited=False)
