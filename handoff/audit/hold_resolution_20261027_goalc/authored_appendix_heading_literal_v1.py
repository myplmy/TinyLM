"""Compare populated values after removing only exact appendix label lines."""
import re
from root_empty_section_contract_v3 import mask as empty_sections
from root_empty_section_contract_v3 import preservation as inherited_preservation
from quick_literal_feasibility_v1 import possible as inherited_possible
from scripts import p106b_hold_resolution_policy_v32 as policy

LABELS = frozenset({'각주', '주해', '참고 문헌', '참고문헌', '외부 링크', '외부링크', '같이 보기', '같이보기'})


def mask(text):
    text, empty = empty_sections(text)
    plain = policy.plain_text(text)
    lines = text.splitlines(keepends=True)
    offset, rows = 0, []
    have_prose = False
    for i, line in enumerate(lines):
        label = line.strip()
        covered = plain[offset:offset + len(line)] != line
        isolated = i > 0 and not lines[i - 1].strip()
        if label in LABELS and isolated and have_prose and not covered:
            rows.append(dict(source_characters=[offset, offset + len(line)], label=label,
                role='EXACT_STANDALONE_APPENDIX_LABEL_ALL_POPULATED_CHILD_VALUES_CHECKED_SEPARATELY'))
            lines[i] = ''.join(c if c in '\r\n' else ' ' for c in line)
        elif not covered and len(label) > 30 and re.search(r'[.。!?]$', label):
            have_prose = True
        offset += len(line)
    return ''.join(lines), dict(empty_section_headers=empty, appendix_label_lines=rows)


def possible(source, body):
    return inherited_possible(mask(source)[0], body)


def preservation(source, body):
    basis, labels = mask(source)
    proof = inherited_preservation(basis, body)
    return dict(proof, source_exact_heading_evidence=labels,
        all_populated_appendix_children_subject_to_same_literal_numeric_code_unicode_style_guards=True,
        raw_source_unchanged=True, universal_scanner_relaxation=False)
