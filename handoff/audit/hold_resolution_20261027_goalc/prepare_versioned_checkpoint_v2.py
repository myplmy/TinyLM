"""Freeze a checkpoint without staging live CPU process output logs."""
from pathlib import Path
import hashlib

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'prepare_versioned_checkpoint_v1.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '3F14A1F293C5513607AAB8EE4D240C6422A4127BC86D6CB27D1816A64DF269EA'
source = raw.decode('utf-8')
before = 'copies,reused,metadata=[],[],[]'
after = """active_exclusions=c.get('active_audit_paths_excluded',[])
assert len(active_exclusions)==len(set(active_exclusions))
for name in active_exclusions:
    path=ROOT/name
    assert path.parent==AUDIT and path.suffix=='.log'
    assert path.name.startswith(('cache8_','cache_reviewed_partial_v8_'))
copies,reused,metadata=[],[],[]"""
assert source.count(before) == 1
source = source.replace(before,after,1)
before = 'for name in sorted(changed):\n    path=ROOT/name'
after = 'for name in sorted(changed):\n    if name in active_exclusions:continue\n    path=ROOT/name'
assert source.count(before) == 2
source = source.replace(before,after)
before = 'excluded_source_data=True,excluded_large_data=True,foreign_dirty_paths_excluded=True'
after = 'excluded_source_data=True,excluded_large_data=True,foreign_dirty_paths_excluded=True,active_audit_paths_excluded=active_exclusions'
assert source.count(before) == 1
source = source.replace(before,after,1)
exec(compile(source,str(frozen),'exec'),dict(__name__='checkpoint_v2_actual_run',__file__=str(Path(__file__))))
