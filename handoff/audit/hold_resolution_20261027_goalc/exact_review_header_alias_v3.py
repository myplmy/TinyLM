"""Normalize one exact English review header; preserve original review bytes."""
from exact_review_header_alias_v2 import wrap_review_entries as wrap_v2

ENGLISH=b'| source_id | decision | actual read scope | exact output | evidence |'
KOREAN='| ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거 |'.encode('utf-8')


def wrap_review_entries(original):
    wrapped=wrap_v2(original)

    def exact_english_header(payload,allow_sections=False):
        lines=payload.splitlines(keepends=True)
        first=next((i for i,line in enumerate(lines) if line.strip()),None)
        if first is not None and lines[first].strip()==ENGLISH:
            line=lines[first]
            end=b'\r\n' if line.endswith(b'\r\n') else b'\n' if line.endswith(b'\n') else b''
            lines[first]=KOREAN+end
            payload=b''.join(lines)
        return wrapped(payload,allow_sections=allow_sections)

    return exact_english_header
