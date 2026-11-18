"""Cheap necessary condition before numeric/code/style preservation work.

True only means the expensive contract may pass. It is never admission.
False skips expensive checks and records them as NOT_RUN, not PASS.
"""
from verify_rule27_literal_delta_v1 import literal_stream, empty_eof_appendix
from verify_event_metadata_literal_delta_v1 import last_paragraph
from authored_empty_section_literal_v1 import mask_empty_sections as appendix_mask
from authored_empty_section_literal_v2 import mask_empty_sections as geography_mask


def core_possible(source, body):
    a = empty_eof_appendix(source)[0]
    b = empty_eof_appendix(body)[0]
    if literal_stream(a) == literal_stream(b):
        return True
    before, source_suffix = last_paragraph(source)
    after, body_suffix = last_paragraph(body)
    a = empty_eof_appendix(before)[0] + chr(10) * 2 + source_suffix
    b = empty_eof_appendix(after)[0] + chr(10) * 2 + body_suffix
    return literal_stream(a) == literal_stream(b)


def possible(source, body):
    if core_possible(source, body):
        return True
    for mask in [appendix_mask, geography_mask]:
        if core_possible(mask(source)[0], mask(body)[0]):
            return True
    return False
