"""Independently check the same commit including exact rule27 owned scripts."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('verify_exact_progress_commit_v2.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'DB28A03F6F9E38CD7DB6C2AF02EAFC8491A168FEEB73902A3C093E355B3EB250'
code = raw.decode('utf-8')
before = "{'handoff/WIP_20261027_작업원장.md','scripts/p106b_hold_resolution_review_safeguards_v4.py'}"
after = repr({'handoff/WIP_20261027_작업원장.md',
    'scripts/p106b_hold_resolution_review_safeguards_v4.py',
    'scripts/p106b_hold_resolution_disambiguation_v1.py',
    'scripts/p106b_hold_resolution_policy_v27.py',
    'scripts/test_p106b_hold_resolution_policy_v27.py'})
assert code.count(before) == 1
code = code.replace(before, after)
exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__))))
