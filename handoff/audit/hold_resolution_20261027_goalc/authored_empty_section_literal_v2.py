"""Extend empty-section proof only to explicit neighboring geography headings."""
from pathlib import Path
import hashlib
import re
import authored_empty_section_literal_v1 as previous

assert hashlib.sha256(Path(previous.__file__).read_bytes()).hexdigest().upper()==\
    'A20BE5111C18231437FABA344560EB14CF174ABE4FFC246926DA09122696C207'
NEXT_BODY_HEADINGS=frozenset({'교통','철도','도로','역사','기후','자매 도시','자매도시'})


def mask_empty_sections(text):
    _old,removed=previous.mask_empty_sections(text)
    lines=text.splitlines(keepends=True)
    labels=[previous.line_label(line) for line in lines]
    excluded={row['line']-1 for row in removed}
    protected=set();inside=False
    for i,line in enumerate(lines):
        if re.match(r'^ {0,3}(?:`{3,}|~{3,})',line):inside=not inside;protected.add(i)
        elif inside:protected.add(i)
    for i,label in enumerate(labels):
        if i in excluded or i in protected or label not in previous.CONTENT_EMPTY:continue
        if i and lines[i-1].strip():continue
        j=i+1
        while j<len(lines) and not lines[j].strip():j+=1
        if j<=i+1 or j==len(lines) or j in protected or labels[j] not in NEXT_BODY_HEADINGS:continue
        removed.append(dict(line=i+1,label=label,boundary='EMPTY_SECTION_BEFORE_EXPLICIT_GEOGRAPHY_BODY_HEADING',
            next_nonempty_line=j+1,next_heading=labels[j]))
        excluded.add(i)
    return ''.join(line for i,line in enumerate(lines) if i not in excluded),sorted(removed,key=lambda r:r['line'])


def preservation(original,body):
    result=previous.preservation(original,body)
    if result['eligible_narrow_literal_delta']:return result
    source,removed_source=mask_empty_sections(original)
    target,removed_target=mask_empty_sections(body)
    proof=previous.prior_preservation(source,target)
    proof['guards'].update({name:result['guards'][name]
        for name in ['numeric_atoms','code','unicode','style','ordered','no_memo']})
    proof['eligible_narrow_literal_delta']=bool(removed_source) and all(proof['guards'].values())
    proof['comparison_basis']='PROVEN_EMPTY_SECTION_BEFORE_EXPLICIT_APPENDIX_OR_GEOGRAPHY_HEADING_ALL_OTHER_VALUES_PRESERVED'
    proof['source_independently_empty_section_lines']=removed_source
    proof['candidate_independently_empty_section_lines']=removed_target
    return proof
