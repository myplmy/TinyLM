"""Reuse the independent all-position join under the current cumulative guard6."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('verify_opaque_hold_contract_v2.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'C756779F03FE2E2A8F2A19932307BCE617A3CAD2437378E250994DDB117A5256'
code = raw.decode('utf-8')
before = 'from active_guard_v4_preflight_v1 import activate, assert_no_protected_opens'
assert code.count(before) == 1
code = code.replace(before, 'from active_guard_v6_preflight_v1 import activate, assert_no_protected_opens')
before = "exec(compile(code, str(frozen), 'exec'), dict(__name__='versioned_opaque_independent_actual_run',"
assert code.count(before) == 1
code = code.replace(before,
    "assert code.count('GUARDED_SOURCE_METADATA_CONTRACT_V4.json') == 2" + chr(10) +
    "code = code.replace('GUARDED_SOURCE_METADATA_CONTRACT_V4.json', 'GUARDED_SOURCE_METADATA_CONTRACT_V6.json')" + chr(10) + before)
exec(compile(code, str(frozen), 'exec'), dict(__name__='guard6_opaque_all_position_verifier',
    __file__=str(Path(__file__))))
