"""Exact individually reviewed exceptions; no program or nonempty Unicode waiver."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[3]
REGISTRY=Path(__file__).with_name('ROOT_RUNTIME_PAIR_APPROVALS_V1.json')
EXPECTED={'expanded_train:'+str(n) for n in [1081376,1254536,1276826,48585,513632,6773,689736,8121,940988]}
UNICODE=re.compile(r'(?i)U\+[0-9A-F]{4,6}\s*[(（]([^()（）\n]*)[)）]')


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest().upper()


def require(value,message):
    if not value:
        raise ValueError(message)


def load_registry():
    document=json.loads(REGISTRY.read_text(encoding='utf-8'))
    require(document.get('status')=='ROOT_REVIEWED_EXACT_RUNTIME_SOURCE_BODY_PAIRS' and
            document.get('global_code_guard_waiver') is False,'exact root registry required')
    cases={}
    for row in document['rows']:
        require(row['id'] in EXPECTED and row['id'] not in cases and row.get('root_approved') is True,
                'unexpected or unapproved runtime pair')
        for pin in [row['original'],row['body'],row['review'],row['evidence']]:
            path=(ROOT/pin['path']).resolve()
            require(path.is_relative_to(ROOT) and hashlib.sha256(path.read_bytes()).hexdigest().upper()==pin['sha256'],
                    'exact pair source/body/review/evidence changed')
        cases[row['id']]=row
    require(set(cases)==EXPECTED,'all nine exact runtime pairs required')
    return cases


def exact_pair_preserved(original,cleaned,ident,cases):
    row=cases.get(ident)
    if not row or row.get('root_approved') is not True:
        return False
    if sha(original)!=row['original']['sha256'] or sha(cleaned)!=row['body']['sha256']:
        return False
    # An empty glyph placeholder has no literal example to preserve. Every
    # actual nonempty source example still has to survive with exact counts.
    for match in UNICODE.finditer(original):
        if match[1].strip() and cleaned.count(match[0])!=original.count(match[0]):
            return False
    source_flat=re.sub(r'\s+','',original)
    clean_flat=re.sub(r'\s+','',cleaned)
    return all(source_flat.count(unit)==clean_flat.count(unit) and source_flat.count(unit)>0
               for unit in row['required_nonwhitespace_code_units'])
