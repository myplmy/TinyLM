"""Verify the same whole commit with the one additional explicit owned module."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('verify_exact_progress_commit_v1.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '0E35880091A85A266F3E7800D2773D059E577D871F76CCE5A6525C71EDA5E759'
code = raw.decode('utf-8')
old = "assert name=='handoff/WIP_20261027_작업원장.md' or path.resolve().is_relative_to(AUDIT)"
assert code.count(old) == 1
code = code.replace(old,
    "assert name in {'handoff/WIP_20261027_작업원장.md','scripts/p106b_hold_resolution_review_safeguards_v4.py'} or path.resolve().is_relative_to(AUDIT)")
exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__,__file__=str(Path(__file__))))
