"""Extend independently empty sections; preserve every populated child value."""
from contextlib import contextmanager
import re
import authored_empty_section_literal_v1 as section_v1
import authored_empty_section_literal_v2 as section_v2
from authored_round_closure_preservation_v1 import preservation as core_preservation
from quick_literal_feasibility_v1 import possible as core_possible
from verify_event_metadata_literal_delta_v1 import last_paragraph
from verify_rule27_literal_delta_v1 import empty_eof_appendix
from verify_category_metadata_delta_v1 import category_markers

EXTRA_EMPTY_HEADS = frozenset({'평가', '화보', '자녀'})


def typed_footer(suffix):
    if category_markers(suffix):
        return 'INDEPENDENT_LITERAL_CATEGORY_MARKERS'
    values = [line.strip() for line in suffix.splitlines() if line.strip()]
    if (len(values) >= 3 and all(re.fullmatch(r'[가-힣A-Za-z0-9 ]+게임', value) for value in values)
            and any(re.fullmatch(r'[12][0-9]{3}년 (?:비디오 |아케이드 )?게임', value) for value in values)
            and any(re.match(r'(?:게임큐브|닌텐도|플레이스테이션|엑스박스|윈도|안드로이드)', value) for value in values)):
        return 'LITERAL_YEAR_MEDIUM_AND_NAMED_PLATFORM_GAME_CATEGORIES'
    return None


@contextmanager
def extended():
    before = section_v1.CONTENT_EMPTY
    section_v1.CONTENT_EMPTY = before | EXTRA_EMPTY_HEADS
    try:
        yield
    finally:
        section_v1.CONTENT_EMPTY = before


def mask(text):
    with extended():
        result, removed = section_v2.mask_empty_sections(text)
    # An isolated content heading at EOF has no child. A whole document that
    # consists only of a heading is not admitted by this transform.
    lines = result.splitlines(keepends=True)
    last = len(lines) - 1
    while last >= 0 and not lines[last].strip():
        last -= 1
    if last > 0 and not lines[last - 1].strip():
        label = section_v1.line_label(lines[last])
        if label in section_v1.CONTENT_EMPTY | EXTRA_EMPTY_HEADS:
            prefix = ''.join(lines[:last])
            if prefix.strip() and not re.search(r'(?m)^\s*(?:```|~~~)', prefix):
                removed.append(dict(line=last + 1, label=label,
                    boundary='ISOLATED_EMPTY_CONTENT_HEADING_AT_EOF_WITH_NONEMPTY_PREFIX'))
                result = prefix + ''.join(lines[last + 1:])
    prefix, suffix = last_paragraph(result)
    role = typed_footer(suffix)
    if role:
        clean_prefix, heads = empty_eof_appendix(prefix)
        if heads:
            result = clean_prefix + chr(10) * 2 + suffix + chr(10)
            removed.extend(dict(row, boundary=role) for row in heads)
    return result, removed


def possible(source, body):
    with extended():
        return core_possible(mask(source)[0], body)


def preservation(source, body):
    canonical_source, removed = mask(source)
    with extended():
        proof = core_preservation(canonical_source, body)
    return dict(proof, source_empty_heading_normalization=removed,
        exact_empty_heading_extension=sorted(EXTRA_EMPTY_HEADS),
        raw_source_unchanged=True,
        comparison_basis='EXPLICIT_EMPTY_CONTENT_HEADERS_THEN_' + proof['comparison_basis'])
