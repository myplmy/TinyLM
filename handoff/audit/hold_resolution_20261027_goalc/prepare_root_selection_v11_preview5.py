"""Limit this cache checkpoint to completed cohorts; retain every deferred ID."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

source = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW4.json'
scope = AUDIT / 'ROOT11_COMPLETED_COHORT_ADMISSION_SCOPE_V1.md'
document = inv.cache.read(source)
manifest = inv.BASE / 'remaining_literal_full_counter_v1/manifest.json'
literal_ids = {row['id'] for row in inv.cache.read(manifest)['rows']}
assert len(literal_ids) == 1793
selected, deferred = [], []
for row in document['rows']:
    if row['id'] in literal_ids and row['selected']['decision'] != 'HOLD':
        deferred.append(dict(id=row['id'], reason='LITERAL_WHOLE_COHORT_AND_EARLY_ACCEPT_REAUDIT_STILL_IN_PROGRESS',
            prior_preview_selected=True, original_text_sha256=row['original_text_sha256']))
    else:
        selected.append(row)
included = {row['id'] for row in selected}
assert included & literal_ids == {'expanded_train:1046282'}
for row in document['unresolved']:
    assert row['id'] in literal_ids
    deferred.append(dict(row, reason='LITERAL_REVIEW_OR_ROOT_MEDIATION_STILL_IN_PROGRESS',
        prior_preview_selected=False))
assert len(selected) == 7857
assert len(deferred) == len({r['id'] for r in deferred}) == 1792
assert {r['id'] for r in deferred} == literal_ids - included
result = dict(document, rows=selected, source_ids=len(selected), selected_sources=len(selected),
    status='COMPLETED_COHORT_EXACT_CHOICES_PENDING_NUMERIC_AND_ROOT_CLOSURE',
    counts=dict(Counter(r['selected']['decision'] for r in selected)),
    unresolved_sources=len(deferred), unresolved=deferred,
    new_selected_by_cohort={'repeat_named_full_independent_v1':732,
        'remaining_birth_full_counter_v1':2743,'remaining_literal_full_counter_v1':1},
    literal_body_adoptions=0, reviewed_literal_nonadmissions=1,
    assigned_literal_sources=1793, deferred_literal_sources=1792,
    selection_scope='PRIOR_ROOT10_PLUS_COMPLETED_BIRTH_REPEAT_QUANTITY_AND_ONE_REVIEWED_LITERAL_HOLD',
    scope_complete=False, numeric_context_closure='NOT_RUN_ON_THIS_PREVIEW',
    goal_complete=False, training_authorized=False)
result['input_pins'] = dict(document['input_pins'], **{
    str(p.relative_to(ROOT)): inv.file_sha(p) for p in [source,scope,manifest,Path(__file__)]})
target = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW5.json'
payload = (json.dumps(result,ensure_ascii=False,indent=2) + chr(10)).encode('utf-8')
assert len(payload) < 20_000_000
with target.open('xb') as f:f.write(payload)
print(json.dumps(dict(sources=len(selected),counts=result['counts'],deferred=len(deferred),
    bytes=len(payload),cache_admitted=0)))
