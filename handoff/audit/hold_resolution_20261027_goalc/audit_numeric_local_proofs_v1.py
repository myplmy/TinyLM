"""Apply narrow local atom proofs to saved immutable diagnostic pairs."""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from numeric_local_atom_proof_v1 import prove_flagged_atoms

source_path = AUDIT / 'EXACT_COHORT_BODY_DIAGNOSTICS_V5.json'
diagnostic = inv.cache.read(source_path)
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
rows, counts = [], Counter()
for row in diagnostic['rows']:
    if not row['numeric_atom_flags']:
        continue
    assert row['id'] not in contract['restricted_ids']
    assert row['original']['sha256'] not in contract['restricted_hashes']
    for key in ('original', 'body'):
        pin = row[key]
        assert inv.file_sha(ROOT / pin['path']) == pin['sha256']
    raw = (ROOT / row['original']['path']).read_text(encoding='utf-8')
    body = (ROOT / row['body']['path']).read_text(encoding='utf-8')
    proofs = prove_flagged_atoms(raw, body, row['numeric_atom_flags'])
    counts['body_pairs'] += 1
    counts.update(proof['status'] for proof in proofs)
    rows.append(dict(id=row['id'], cohort=row['cohort'], original=row['original'], body=row['body'],
        review=row['review'], proofs=proofs, root_approved=False, cache_admitted=False))
result = dict(status='EXACT_LOCAL_NUMERIC_PROVENANCE_NOT_SEMANTIC_OR_FACT_APPROVAL',
    counts=dict(counts), rows=rows,
    source=dict(path=str(source_path.relative_to(ROOT)), sha256=inv.file_sha(source_path)),
    producer_sha256=inv.file_sha(Path(__file__)),
    helper_sha256=inv.file_sha(AUDIT / 'numeric_local_atom_proof_v1.py'),
    limits='No general waiver; source/body SHA and changed-block spans are exact. Object, event, uncertainty and fact correction still require review.',
    production_policy_changed=False, goal_complete=False, training_authorized=False)
inv.write_json(AUDIT / 'EXACT_COHORT_NUMERIC_LOCAL_PROOFS_V1.json', result)
pending = [dict(id=row['id'], cohort=row['cohort'], values=[p['flag']['body_token'] for p in row['proofs'] if
    p['status'] == 'MANUAL_CONTEXT_REQUIRED']) for row in rows if any(
        p['status'] == 'MANUAL_CONTEXT_REQUIRED' for p in row['proofs'])]
print(json.dumps(dict(counts=dict(counts), pending=pending), ensure_ascii=False))
