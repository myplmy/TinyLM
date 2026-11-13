"""Preserve one exact partial-review filename through the existing rank checker."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import runpy
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard

guard.activate()
old = AUDIT / 'EXACT_COHORT_LEGACY_REVIEW_RANK_ALIASES_V2.json'
new = AUDIT / 'EXACT_COHORT_LEGACY_REVIEW_RANK_ALIASES_V3.json'
read = guard.inv.cache.read
before, after = read(old), read(new)
assert after['rows'][:-1] == before['rows']
extra = after['rows'][-1]
assert extra['path'].endswith('/context_controls/remaining_field_title_page_016_counter_v1/review_006_partial_v1.md')
assert extra['canonical_review'].endswith('/context_controls/remaining_field_title_page_016_counter_v1/review_006_v2.md')
assert set(extra['ids']) == {'expanded_train:415101', 'expanded_train:416614', 'expanded_train:416842'}
assert extra['legacy_rank'] == [6, False, 1] and extra['root_approved'] is True
frozen = AUDIT / 'collect_exact_reviews_guarded_v15.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper() == 'B3E9E8C8F4969A8F5F5B314FD9DED42CF89C804BB4484012A007C610C2C4A94D'

def adapted_read(path):
    return read(new if Path(path).resolve() == old else path)

with patch.object(guard.inv.cache, 'read', adapted_read):
    runpy.run_path(str(frozen), run_name='__main__')
guard.assert_no_protected_opens()
args = sys.argv[1:]
phase = args[args.index('--phase') + 1]
page = int(args[args.index('--page') + 1])
version = args[args.index('--version') + 1]
out = AUDIT / f'EXACT_RANK_ALIAS_{phase.upper()}_{page:03d}_{version.upper()}_V1.json'
assert not out.exists()
guard.inv.write_json(out, dict(
    status='EXACT_LEGACY_RANK_ALIAS_EXISTING_ID_SHA_AND_ORDER_CHECKS_REUSED',
    original_review_preserved=True, canonical_review_same_decision_IDs=True,
    old_registry_pins_are_preserved_provenance=True,
    input_pins={str(p.relative_to(ROOT)): guard.inv.file_sha(p) for p in [Path(__file__), frozen, old, new]},
    source_reread_credit=0, protected_payload_open_attempts=0,
    root_adopted=0, cache_admitted=0, goal_complete=False, training_authorized=False))
print(json.dumps(dict(status='EXACT_RANK_ALIAS_BOUND', page=page, version=version)))
