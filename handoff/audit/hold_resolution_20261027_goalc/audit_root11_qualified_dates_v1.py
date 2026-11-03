"""Flag removed qualified date strings for context review, without changing text."""
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

source=AUDIT/'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW5.json'
document=inv.cache.read(source)
contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
date=re.compile(r'[0-9]{2,4}년(?:[ \t]*[0-9]{1,2}월(?:[ \t]*[0-9]{1,2}일)?)?[ \t]*(?:이전|이후|전후|무렵|경)|(?:circa|ca\.|c\.)[ \t]*[0-9]{3,4}',re.I)
rows=[]
for selected in document['rows']:
    choice=selected['selected']
    if choice.get('cohort')!='remaining_birth_full_counter_v1' or choice['decision'] not in {'KEEP','EDIT'}:continue
    assert selected['id'] not in contract['restricted_ids'] and selected['original_text_sha256'] not in contract['restricted_hashes']
    original=choice['original'];body=dict(path=choice['body'],sha256=choice['clean_text_sha256'])
    assert inv.file_sha(ROOT/original['path'])==original['sha256'] and inv.file_sha(ROOT/body['path'])==body['sha256']
    raw=(ROOT/original['path']).read_text(encoding='utf-8')
    clean=(ROOT/body['path']).read_text(encoding='utf-8')
    normalized=re.sub(r'\s+','',clean)
    for match in date.finditer(raw):
        value=match.group()
        if re.sub(r'\s+','',value) in normalized:continue
        # These are place or job word prefixes, not uncertainty qualifiers.
        tail=raw[match.end():match.end()+8]
        if value.endswith('경') and re.match(r'기도|상(?:남|북)?도|찰|력|험|성|주|제',tail):continue
        a=raw.rfind(chr(10),0,match.start())+1
        b=raw.find(chr(10),match.end());b=len(raw) if b<0 else b
        rows.append(dict(id=selected['id'],missing_qualified_date=value,source_span=list(match.span()),
            original_line=raw.count(chr(10),0,match.start())+1,source_line=raw[a:b],
            original=original,body=body,review=choice['review'],confirmed_error=False))
result=dict(status='REMOVED_QUALIFIED_DATES_REQUIRE_INDIVIDUAL_CONTEXT_NOT_AUTOMATIC_ERRORS',rows=rows,
    selection=dict(path=str(source.relative_to(ROOT)),sha256=inv.file_sha(source)),
    producer_sha256=inv.file_sha(Path(__file__)),protected_body_reads=0,goal_complete=False,training_authorized=False)
out=AUDIT/'ROOT11_QUALIFIED_DATE_DIAGNOSTICS_V1.json'
payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode()
assert len(payload)<20_000_000
with out.open('xb') as f:f.write(payload)
print(json.dumps(dict(flags=len(rows),rows=[dict(id=r['id'],missing=r['missing_qualified_date'],
    source_line=r['source_line'][:500]) for r in rows]),ensure_ascii=False))
