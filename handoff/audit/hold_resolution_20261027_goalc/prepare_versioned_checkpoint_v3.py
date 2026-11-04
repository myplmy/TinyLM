"""Apply current guard4 before reusing disjoint, immutable save primitives."""
from pathlib import Path
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(AUDIT))
from active_guard_v4_preflight_v1 import activate, assert_no_protected_opens
from guarded_reviewed_cache_v6 import checked_contract

activate()
index = sys.argv.index('--config')
config_path = (ROOT/sys.argv[index+1]).resolve()
assert config_path.is_relative_to(AUDIT)
c = json.loads(config_path.read_bytes())
selection = json.loads((AUDIT/c['selection']).read_bytes())
guard = checked_contract()
for row in selection['rows']:
    if row['selected'].get('cohort') != 'root12_independent_admission_counter_v1': continue
    assert row['id'] not in guard['restricted_ids']
    assert row['original_text_sha256'] not in guard['restricted_hashes']
frozen = AUDIT/'prepare_versioned_checkpoint_v1.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '3F14A1F293C5513607AAB8EE4D240C6422A4127BC86D6CB27D1816A64DF269EA'
exec(compile(raw, str(frozen), 'exec'), dict(__name__='current_guard4_owned_checkpoint',
    __file__=str(Path(__file__))))
assert_no_protected_opens()
