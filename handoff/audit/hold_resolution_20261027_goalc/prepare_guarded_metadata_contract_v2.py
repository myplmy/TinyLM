"""Freeze only text-free ledger identities for seven restricted sources and aliases."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

output = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
inv.require(not output.exists(), 'new text-free contract required')
restricted = {'expanded_train:' + str(n) for n in [14760,756966,15695,1216576,1250821,20624,6030]}
report_path = inv.PARENT / 'built.json'
report = inv.cache.read(report_path)
directory = inv.PARENT / 'ledger'
inv.verify(directory, report['manifests']['ledger'])
exact = {}
for row in inv.cache.rows(directory, report['manifests']['ledger']):
    inv.require('text' not in row and 'candidate' not in row, 'trusted ledger must contain no source body')
    if row['id'] in restricted:
        inv.require(row['id'] not in exact, 'restricted source ID repeats')
        exact[row['id']] = row
inv.require(set(exact) == restricted, 'seven exact source identities are required')
hashes = {row['original_text_sha256'] for row in exact.values()}
metadata, counts = {}, Counter()
for row in inv.cache.rows(directory, report['manifests']['ledger']):
    if row['id'] not in restricted and row['original_text_sha256'] not in hashes:
        continue
    inv.require(row['decision'] in {'HOLD','EXCLUDE'}, 'restricted alias was already admitted; preserve baseline and require explicit mediation')
    fields = ['id','source','split','source_ids','source_ids_sha256','original_text_sha256','input_ids']
    metadata[row['id']] = {key:row[key] for key in fields}
    metadata[row['id']]['parent_decision'] = row['decision']
    counts[row['decision']] += 1
result = dict(status='TEXT_FREE_FROZEN_LEDGER_IDENTITIES_FOR_RESTRICTED_BYTE_GUARD',
    restricted_ids=sorted(restricted), restricted_hashes=sorted(hashes), trusted_metadata=metadata,
    exact_source_parent_decisions={ident:row['decision'] for ident,row in exact.items()},
    counts=dict(counts), original_or_candidate_bodies_opened=False,
    input_pins={str(path.relative_to(ROOT)):inv.file_sha(path) for path in [report_path,
        Path(__file__)]}, goal_complete=False, training_authorized=False)
inv.write_json(output, result)
print(json.dumps(dict(exact_source_parent_decisions=result['exact_source_parent_decisions'],
                      alias_positions=len(metadata), counts=dict(counts))))
