"""Normalize two explicit MD-table spellings; keep all exact output binding checks."""
import hashlib
import re
from exact_review_header_alias_v2 import wrap_review_entries as parent_wrap

NORMALIZATIONS={}


def normalize_output(cell,source_id):
    if ';' not in cell:
        return cell
    first,separator,note=cell.partition(';')
    first=first.strip(' `*')
    if not first.endswith('.txt') or any(x in first for x in [';',chr(10),chr(13)]):
        return cell
    # Only the explicit one TXT + local same-ID MD note form is recognized.
    if len(re.findall(r'[.]txt\b',cell))!=1 or '/' in note or '\\' in note:
        return cell
    names=re.findall(r'(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]+[.]md)(?![A-Za-z0-9_.-])',note)
    if len(names)!=1 or note.count('.md')!=1:
        return cell
    number=source_id.rsplit(':',1)[-1]
    if not number.isdigit() or not re.search(r'(?:^|_)'+re.escape(number)+r'(?:_|[.]|$)',names[0]):
        return cell
    return first


def wrap_review_entries(original):
    wrapped=parent_wrap(original)

    def explicit_cells(payload,allow_sections=False):
        result=[]
        for entry in wrapped(payload,allow_sections=allow_sections):
            cells=list(entry.get('cells',[]))
            header=entry.get('header')
            if len(cells)>=5 and header:
                before=list(cells)
                status=cells[1].strip(' `*.')
                if status=='REVISE_TEXT_PARTIAL':
                    cells[1]='REVISE_TEXT'
                output=next((n for n,name in enumerate(header) if name in
                             {'출력','정확 출력','정확출력','산출물','출력 (TXT basename)'}),None)
                if output is not None and output<len(cells):
                    source_id=cells[0].strip(' `*')
                    cells[output]=normalize_output(cells[output],source_id)
                if cells!=before:
                    raw=payload.encode() if isinstance(payload,str) else payload
                    digest=hashlib.sha256(raw).hexdigest().upper()
                    key=(digest,entry['number'],before[0])
                    NORMALIZATIONS[key]=dict(review_sha256=digest,line=entry['number'],
                        source_id=before[0],old_status=before[1],new_status=cells[1],
                        old_output=before[output] if output is not None else None,
                        new_output=cells[output] if output is not None else None)
                    entry=dict(entry,cells=cells)
            result.append(entry)
        return result

    return explicit_cells
