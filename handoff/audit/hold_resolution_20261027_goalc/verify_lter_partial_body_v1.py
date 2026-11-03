"""Pin the corrected source/table pair and preserve the actually rejected pair."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from lter_table_identity_v1 import prove_table

manifest_path = inv.BASE / 'remaining_literal_full_counter_v1/manifest.json'
row = next(r for r in inv.cache.read(manifest_path)['rows'] if r['id'] == 'expanded_train:1323187')
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
assert row['id'] not in contract['restricted_ids']
assert row['original']['sha256'] not in contract['restricted_hashes']
assert inv.file_sha(ROOT / row['original']['path']) == row['original']['sha256']
directory = inv.BASE / 'agents/context_latin/remaining_literal_full_counter_v1'
body_path = directory / 'reviewed_1323187_v2.txt'
old_path = directory / 'reviewed_1323187_v1.txt'
review_path = directory / 'review_020_v4.md'
sidecar_path = directory / 'hold_1323187_v1.md'
original = (ROOT / row['original']['path']).read_text(encoding='utf-8')
body = body_path.read_text(encoding='utf-8')
old = old_path.read_text(encoding='utf-8')
review = review_path.read_text(encoding='utf-8')
lines = [line for line in review.splitlines() if line.startswith('| expanded_train:1323187 |')]
assert len(lines) == 1 and body_path.name in lines[0] and 'REVISE_TEXT' in lines[0]
test_path = AUDIT / 'LTER_TABLE_IDENTITY_TEST_RESULT_V1.json'
test = inv.cache.read(test_path)
assert test['process_exit_code'] == 0
assert inv.file_sha(ROOT / test['test']) == test['test_sha256']
assert inv.file_sha(ROOT / test['log']) == test['log_sha256']
try:
    prove_table(original, old)
except ValueError as error:
    negative = dict(status='ACTUAL_PRIOR_BODY_REJECTED', reason=str(error),
        path=str(old_path.relative_to(ROOT)), sha256=inv.file_sha(old_path))
else:
    raise AssertionError('the prior missing-name body must not pass')
proof = prove_table(original, body)
assert proof['rows_checked'] == 27
script_start = original.index('library(maps)')
script = original[script_start:].strip()
sidecar = sidecar_path.read_text(encoding='utf-8')
assert script in sidecar, 'the full original unusable script must be preserved in its sidecar'
assert body.count('Harvard Forest LTER (HFR)') == 1
assert old.replace('Harvard Forest (HFR)', 'Harvard Forest LTER (HFR)') == body
paths = [manifest_path, body_path, old_path, review_path, sidecar_path, test_path,
    AUDIT / 'lter_table_identity_v1.py', Path(__file__)]
result = dict(status='EXACT_SOURCE_TABLE_BODY_VERIFIED_WITH_SCRIPT_HELD_NOT_RECONSTRUCTED',
    id=row['id'], original=row['original'],
    body=dict(path=str(body_path.relative_to(ROOT)), sha256=inv.file_sha(body_path)),
    review=dict(path=str(review_path.relative_to(ROOT)), sha256=inv.file_sha(review_path)),
    sidecar=dict(path=str(sidecar_path.relative_to(ROOT)), sha256=inv.file_sha(sidecar_path)),
    held_original_script_character_range=[script_start,len(original)],
    full_held_script_preserved=True, proof=proof, prior_rejected_body=negative,
    root_approved=True, applies_only_to_original_and_body_sha256=True,
    original_protected_bodies_opened=False, global_code_guard_waiver=False,
    input_pins={str(p.relative_to(ROOT)):inv.file_sha(p) for p in paths},
    code_run=False, geographic_fact_validation=False, cache_admitted=False,
    goal_complete=False, training_authorized=False)
inv.write_json(AUDIT / 'EXACT_LTER_TABLE_BODY_APPROVAL_1323187_V1.json', result)
print(json.dumps(dict(rows_verified=27, source_and_body_exact=True,
    prior_bad_body_rejected=True, original_script_held=True, cache_admitted=False)))
