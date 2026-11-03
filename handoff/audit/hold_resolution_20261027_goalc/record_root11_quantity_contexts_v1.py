"""Record actual root judgments for fifteen quantity flags and one place prefix."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

diagnostic_path=AUDIT/'ROOT11_STATED_QUANTITY_DIAGNOSTICS_V2.json'
qualified_path=AUDIT/'ROOT11_QUALIFIED_DATE_DIAGNOSTICS_V2.json'
rationale=AUDIT/'ROOT11_QUANTITY_AND_QUALIFIED_DATE_REVIEW_V1.md'
document,qualified=map(inv.cache.read,[diagnostic_path,qualified_path])
expected={str(n) for n in [110507,314339,45295,538092,84493,120410,121135,144106,183863,299959,32711,653732,695195,79984,817488]}
assert {r['id'].split(':')[1] for r in document['rows']}==expected
assert len(document['rows'])==15
pin=dict(path=str(rationale.relative_to(ROOT)),sha256=inv.file_sha(rationale))
rows=[]
for r in document['rows']:
    for key in ['original','body','review']:
        item=r[key];assert inv.file_sha(ROOT/item['path'])==item['sha256']
    rows.append(dict(r,needs_context_adjudication=False,root_context_approved=True,
        context_evidence=pin,full_document_fact_approval=False,cache_admitted=False))
assert len(qualified['rows'])==1
q=qualified['rows'][0]
assert q['id']=='expanded_train:38429' and '경북 칠곡군' in q['source_line']
assert q['missing_qualified_date'].endswith('경')
paths=[diagnostic_path,qualified_path,rationale,Path(__file__)]
out=AUDIT/'ROOT11_QUANTITY_AND_QUALIFIED_DATE_CONTEXTS_V1.json'
assert not out.exists()
inv.write_json(out,dict(status='EXACT_QUANTITY_FLAGS_CONTEXT_REVIEWED_NOT_WHOLE_MEANING_APPROVAL',
    rows=rows,qualified_date_false_positive=dict(q,kind='GEOGRAPHIC_NAME_PREFIX_NOT_UNCERTAINTY',
        root_context_approved=True,context_evidence=pin),
    counts=dict(quantity_source_contexts=15,qualified_date_false_positive=1,unresolved_context_flags=0),
    input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in paths},
    goal_complete=False,training_authorized=False))
print(json.dumps(dict(quantity_contexts=15,qualified_date_false_positive=1)))
