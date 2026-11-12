"""Also strip the exact 'final file/body' prefix before one explicit TXT path."""
import hashlib
import re
import exact_review_output_cell_alias_v1 as previous
NORMALIZATIONS=previous.NORMALIZATIONS


def wrap_review_entries(original):
    wrapped=previous.wrap_review_entries(original)

    def explicit_final_prefix(payload,allow_sections=False):
        result=[]
        for entry in wrapped(payload,allow_sections=allow_sections):
            cells=list(entry.get('cells',[]))
            header=entry.get('header')
            if len(cells)>=5 and header:
                output=next((n for n,name in enumerate(header) if name in
                             {'출력','정확 출력','정확출력','산출물','출력 (TXT basename)'}),None)
                if output is not None and output<len(cells):
                    before=cells[output]
                    clean=re.sub(r'\A최종[ \t]+(?:파일|본문)[ \t]+','',before.strip(' `*'),count=1).strip(' `*')
                    if clean!=before and clean.endswith('.txt') and ';' not in clean:
                        cells[output]=clean
                        raw=payload.encode() if isinstance(payload,str) else payload
                        digest=hashlib.sha256(raw).hexdigest().upper()
                        key=(digest,entry['number'],cells[0])
                        record=previous.NORMALIZATIONS.get(key,dict(review_sha256=digest,
                            line=entry['number'],source_id=cells[0],old_status=cells[1],
                            new_status=cells[1],old_output=before))
                        previous.NORMALIZATIONS[key]=dict(record,new_output=clean)
                        entry=dict(entry,cells=cells)
            result.append(entry)
        return result

    return explicit_final_prefix
