"""Run exact per-pair grammatical substitutions under the cumulative guard5."""
from pathlib import Path
import hashlib
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from active_guard_v5_preflight_v1 import activate, assert_no_protected_opens, EXPECTED

activate()
frozen = AUDIT / 'close_exact_order_contexts_v1.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'C8EDA989CAF98D4B755848898ACF89BC0C7627CEE74B9F8DA7D064B1760B3C16'
code = raw.decode('utf-8')
for old, new in [
    ('GUARDED_SOURCE_METADATA_CONTRACT_V3.json', 'GUARDED_SOURCE_METADATA_CONTRACT_V5.json'),
    ('7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306', EXPECTED),
]:
    assert code.count(old) == 1
    code = code.replace(old, new)
anchor = 'receipt=dict(status='
assert code.count(anchor) == 1
code = code.replace(anchor,
    "read(AUDIT/'close_exact_order_contexts_v1.py')" + chr(10) +
    "read(AUDIT/'active_guard_v5_preflight_v1.py')" + chr(10) +
    'assert_no_protected_opens()' + chr(10) + anchor)
exec(compile(code, str(frozen), 'exec'), dict(
    __name__='guard5_exact_order_actual_run', __file__=str(Path(__file__)),
    assert_no_protected_opens=assert_no_protected_opens))
assert_no_protected_opens()
