"""Keep owned workers and reference census while selecting guard5 runtime8."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('run_versioned_guarded_cache_v4.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'C301BD7D75FC08363FAD49ECDBC3209513531D550B7801887EEFC93DAC934F11'
code = raw.decode('utf-8')
for before, after in [
    ('from guarded_reviewed_cache_v7 import verify_configuration',
     'from guarded_reviewed_cache_v8 import verify_configuration'),
    ('import guarded_reviewed_cache_v7 as guarded', 'import guarded_reviewed_cache_v8 as guarded'),
]:
    assert code.count(before) == 1
    code = code.replace(before, after)
exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__))))
