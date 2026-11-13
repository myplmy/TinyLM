"""Recognize two exact output headings and one explicit local Markdown TXT link."""
from pathlib import Path
import hashlib
import re
import exact_review_output_cell_alias_v2 as previous

assert hashlib.sha256(Path(previous.__file__).read_bytes()).hexdigest().upper()==\
    '1F4010473EC47147600580AFA9BDECDC3677C6E6A53583C362F7BE35F929C198'
BASE_WRAP=previous.wrap_review_entries
NORMALIZATIONS=previous.NORMALIZATIONS
OUTPUT_HEADERS={'출력','정확 출력','정확출력','산출물','출력 (TXT basename)'}
EXACT_HEADERS=frozenset({'새 본문 / 선택 경로','새 본문'})
LINK=re.compile(r'\[[^\[\]\r\n]+\]\(([A-Za-z0-9_.-]+\.txt)\)')


def wrap_review_entries(original):
    def explicit_header(payload,allow_sections=False):
        result=[]
        for entry in original(payload,allow_sections=allow_sections):
            header=entry.get('header')
            if header is not None:
                header=['출력' if v in EXACT_HEADERS else v for v in header]
                if sum(v in OUTPUT_HEADERS for v in header)>1:raise ValueError('AMBIGUOUS_EXPLICIT_OUTPUT_HEADERS')
                entry=dict(entry,header=header)
            result.append(entry)
        return result
    wrapped=BASE_WRAP(explicit_header)

    def explicit_link(payload,allow_sections=False):
        result=[]
        for entry in wrapped(payload,allow_sections=allow_sections):
            header=entry.get('header');cells=list(entry.get('cells',[]))
            output=next((i for i,v in enumerate(header or []) if v in OUTPUT_HEADERS),None)
            if output is not None and output<len(cells):
                before=cells[output];match=LINK.fullmatch(before.strip(' `*'))
                source_id=cells[0].strip(' `*');number=source_id.rsplit(':',1)[-1]
                if match and number.isdigit() and re.search(r'(?:^|_)'+re.escape(number)+r'(?:_|[.]|$)',match[1]):
                    cells[output]=match[1]
                    raw=payload.encode('utf-8') if isinstance(payload,str) else payload
                    digest=hashlib.sha256(raw).hexdigest().upper();key=(digest,entry['number'],cells[0])
                    record=NORMALIZATIONS.get(key,dict(review_sha256=digest,line=entry['number'],
                        source_id=cells[0],old_status=cells[1],new_status=cells[1],old_output=before))
                    NORMALIZATIONS[key]=dict(record,new_output=cells[output],
                        binding='EXACT_SINGLE_EXPLICIT_LOCAL_MARKDOWN_TXT_TARGET_SAME_SOURCE_ID')
                    entry=dict(entry,cells=cells)
            result.append(entry)
        return result
    return explicit_link
