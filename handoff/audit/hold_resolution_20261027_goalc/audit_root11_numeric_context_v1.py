"""Check every new selected pair and reuse only exact prior numerical evidence."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from numeric_atom_integrity_v1 import numeric_atom_changes
from numeric_local_atom_proof_v1 import prove_flagged_atoms

source = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW5.json'
prior_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V10.json'
clear_path = AUDIT / 'EXACT_NUMERIC_CONTEXT_CLEARANCES_V1.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
document, prior, cleared, contract = map(inv.cache.read,[source,prior_path,clear_path,contract_path])
prior_rows = {r['id']:r for r in prior['rows']}
clearances = {(r['id'],r['original']['sha256'],r['body']['sha256']):r for r in cleared['rows']}
blocked_ids = set(contract['restricted_ids'])
blocked_sha = set(contract['restricted_hashes'])
counts, rows, pins = Counter(), [], {}
for selected in document['rows']:
    ident = selected['id']
    key = selected['original_text_sha256']
    choice = selected['selected']
    counts['selected_sources'] += 1
    if choice['decision'] not in {'KEEP','EDIT'}:
        counts['nonadmitted_sources'] += 1
        continue
    old = prior_rows.get(ident)
    if old and old['original_text_sha256'] == key and old['selected']['decision'] == choice['decision'] and old['selected'].get('clean_text_sha256') == choice['clean_text_sha256']:
        assert old['root_approved'] is True and old['selected']['root_approved'] is True
        counts['exact_prior_root10_pairs_reused'] += 1
        continue
    assert ident not in blocked_ids and key not in blocked_sha
    original = choice['original']
    body = dict(path=choice['body'],sha256=choice['clean_text_sha256'])
    for pin in [original,body,choice['review']]:
        assert inv.file_sha(ROOT/pin['path']) == pin['sha256']
        pins[pin['path']] = pin['sha256']
    raw = (ROOT/original['path']).read_text(encoding='utf-8')
    clean = (ROOT/body['path']).read_text(encoding='utf-8')
    flags = numeric_atom_changes(raw,clean)
    proofs = prove_flagged_atoms(raw,clean,flags)
    counts['new_or_changed_body_pairs_checked'] += 1
    if not flags:
        counts['new_pairs_without_added_atom_flag'] += 1
        continue
    clearance = clearances.get((ident,key,body['sha256']))
    unresolved = []
    for p in proofs:
        if p['status'] == 'MANUAL_CONTEXT_REQUIRED':
            if clearance and p['flag'] in clearance['reviewed_flags']:
                p['status'] = 'EXACT_PRIOR_ROOT_CONTEXT_CLEARANCE_REUSED'
                p['clearance_pin'] = dict(path=str(clear_path.relative_to(ROOT)),sha256=inv.file_sha(clear_path))
            else:
                unresolved.append(p['flag'])
        counts[p['status']] += 1
    rows.append(dict(id=ident,cohort=choice['cohort'],original=original,body=body,
        review=choice['review'],proofs=proofs,unresolved_flags=unresolved,
        numeric_context_closed=not unresolved,root_body_approved=False,cache_admitted=False))
for name,expected in pins.items():assert inv.file_sha(ROOT/name)==expected
for p in [source,prior_path,clear_path,contract_path,Path(__file__),
        AUDIT/'numeric_atom_integrity_v1.py',AUDIT/'numeric_local_atom_proof_v1.py']:
    pins[str(p.relative_to(ROOT))] = inv.file_sha(p)
result = dict(status='EXACT_ROOT11_NUMERICAL_PROVENANCE_PENDING_INDIVIDUAL_CONTEXT',
    counts=dict(counts),rows=rows,input_pins=pins,restricted_original_bodies_opened=False,
    limits='No missing-atom detector proves deletions or whole document facts. Actual source meaning, stated quantities, negatives, uncertainty and independent review remain separate.',
    goal_complete=False,training_authorized=False)
out = AUDIT/'ROOT11_NUMERIC_CONTEXT_DIAGNOSTICS_V1.json'
payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode()
assert len(payload)<20_000_000
with out.open('xb') as f:f.write(payload)
pending=[dict(id=r['id'],values=[p['body_token'] for p in r['unresolved_flags']]) for r in rows if r['unresolved_flags']]
print(json.dumps(dict(counts=dict(counts),pending=pending,bytes=len(payload)),ensure_ascii=False))
