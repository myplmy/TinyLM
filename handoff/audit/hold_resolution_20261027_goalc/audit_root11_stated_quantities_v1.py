"""Check previously selected bodies for stated quantity loss, without modifying them."""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from birth_semantic_span_guard_v1 import lost_stated_quantities, suspicious_birth_field_removal

selection_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW5.json'
selection = inv.cache.read(selection_path)
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
blocked_ids, blocked_hashes = set(contract['restricted_ids']), set(contract['restricted_hashes'])
counts, rows = Counter(), []
prior = {r['id']:r for r in inv.cache.read(AUDIT/'ROOT_AUTHORED_SELECTIONS_V10.json')['rows']}
for row in selection['rows']:
    before = prior.get(row['id'])
    if before and before['selected'].get('clean_text_sha256') == row['selected'].get('clean_text_sha256') and before['selected']['decision'] == row['selected']['decision']:
        counts['exact_prior_pairs_reused'] += 1
        continue
    if row['id'] in blocked_ids or row['original_text_sha256'] in blocked_hashes:
        counts['restricted_metadata_only'] += 1
        continue
    chosen = row['selected']
    if not chosen.get('body'):
        counts['without_selected_body'] += 1
        continue
    original = chosen.get('original') or dict(path=row['original_paths'][0], sha256=row['original_text_sha256'])
    inv.require(original['sha256'] == row['original_text_sha256'], 'source pin differs')
    inv.require(inv.file_sha(ROOT / original['path']) == original['sha256'], 'source bytes changed')
    inv.require(inv.file_sha(ROOT / chosen['body']) == chosen['clean_text_sha256'], 'body bytes changed')
    raw = (ROOT / original['path']).read_text(encoding='utf-8')
    body = (ROOT / chosen['body']).read_text(encoding='utf-8')
    flags = lost_stated_quantities(raw, body) + suspicious_birth_field_removal(raw, body)
    counts['selected_bodies_checked'] += 1
    if flags:
        counts['flagged_sources'] += 1
        counts.update(flag['kind'] for flag in flags)
        rows.append(dict(id=row['id'], cohort=chosen.get('cohort', 'PRIOR_EXACT_SELECTION'), original=original,
            body=dict(path=chosen['body'], sha256=chosen['clean_text_sha256']),
            review=chosen.get('review'), flags=flags, needs_context_adjudication=True,
            root_approved=False, cache_admitted=False))
result = dict(status='ROOT11_STATED_QUANTITY_DIAGNOSTIC_NOT_CONFIRMED_ERRORS',
    counts=dict(counts), rows=rows,
    selection=dict(path=str(selection_path.relative_to(ROOT)), sha256=inv.file_sha(selection_path)),
    helper_sha256=inv.file_sha(AUDIT / 'birth_semantic_span_guard_v1.py'),
    producer_sha256=inv.file_sha(Path(__file__)),
    limits='Conservative count and field flags require source context. No automatic change or admission.',
    protected_body_reads=0, goal_complete=False, training_authorized=False)
out = AUDIT / 'ROOT11_STATED_QUANTITY_DIAGNOSTICS_V1.json'
payload = (json.dumps(result, ensure_ascii=False, indent=2) + chr(10)).encode('utf-8')
assert len(payload) < 20_000_000
with out.open('xb') as stream:
    stream.write(payload)
print(json.dumps(dict(counts=dict(counts), rows=[dict(id=r['id'], cohort=r['cohort'],
    kinds=[f['kind'] for f in r['flags']]) for r in rows]), ensure_ascii=False))
