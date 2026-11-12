"""Recognize only empty section lines at independently explicit appendix boundaries."""
import re
from verify_rule27_literal_delta_v1 import EMPTY_APPENDIX_HEADINGS
from authored_literal_metadata_readiness_v2 import preservation as prior_preservation

CONTENT_EMPTY = frozenset({'인구', '기후', '갤러리', '사진'})


def line_label(line):
    value = line.rstrip(chr(10) + chr(13))
    if not value.strip() or value.startswith(('    ', '\t', '>', '*', '-', '#', ':', ';')):
        return None
    return ' '.join(value.strip().split()).casefold()


def mask_empty_sections(text):
    lines = text.splitlines(keepends=True)
    labels = [line_label(line) for line in lines]
    protected = set()
    inside = False
    for i, line in enumerate(lines):
        if re.match(r'^ {0,3}(?:`{3,}|~{3,})', line):
            inside = not inside
            protected.add(i)
        elif inside:
            protected.add(i)
    removed = []
    for i, label in enumerate(labels):
        if i in protected or label not in EMPTY_APPENDIX_HEADINGS | CONTENT_EMPTY:
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        at_eof = j == len(lines)
        explicit_next = not at_eof and j not in protected and labels[j] in EMPTY_APPENDIX_HEADINGS
        if (at_eof and label in EMPTY_APPENDIX_HEADINGS) or explicit_next:
            removed.append(dict(line=i + 1, label=label,
                boundary='ACTUAL_EMPTY_EOF_APPENDIX' if at_eof else 'NEXT_EXPLICIT_APPENDIX_HEADING',
                next_nonempty_line=None if at_eof else j + 1))
    omitted = {row['line'] - 1 for row in removed}
    return ''.join(line for i, line in enumerate(lines) if i not in omitted), removed


def preservation(original, body):
    result = prior_preservation(original, body)
    if result['eligible_narrow_literal_delta']:
        return result
    source, removed_source = mask_empty_sections(original)
    target, removed_target = mask_empty_sections(body)
    proof = prior_preservation(source, target)
    # Original code/unicode/style and numeric checks must still compare actual texts.
    proof['guards'].update({name: result['guards'][name]
        for name in ['numeric_atoms', 'code', 'unicode', 'style', 'ordered', 'no_memo']})
    proof['eligible_narrow_literal_delta'] = bool(removed_source) and all(proof['guards'].values())
    proof['comparison_basis'] = 'PROVEN_EMPTY_SECTION_BEFORE_EXPLICIT_APPENDIX_AND_ALL_OTHER_LITERAL_VALUES'
    proof['source_independently_empty_section_lines'] = removed_source
    proof['candidate_independently_empty_section_lines'] = removed_target
    return proof
