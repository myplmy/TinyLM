"""Preserve the failed guard5 transform; keep the frozen history anchor intact."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('collect_root12_counter_v5.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '034DF673AC5019316F40438D2C279F380A6BA61F7C7292B41FF8D9ED37280ABD'
code = raw.decode('utf-8')
before = '''        'for path in [manifest_path,guard_path,reused,Path(__file__),':
            "for path in [AUDIT/'active_guard_v4_preflight_v1.py',AUDIT/'guarded_reviewed_cache_v6.py',manifest_path,guard_path,reused,Path(__file__),"}'''
after = '''        "AUDIT/'ROOT12_COUNTER_COLLECTION_SCOPE_V1.md']:":
            "AUDIT/'ROOT12_COUNTER_COLLECTION_SCOPE_V1.md',AUDIT/'active_guard_v4_preflight_v1.py',AUDIT/'guarded_reviewed_cache_v6.py',AUDIT/'collect_root12_counter_v5.py']:"}'''
assert code.count(before) == 1
code = code.replace(before, after)
exec(compile(code, str(frozen), 'exec'), dict(__name__='guard4_counter6_actual_run',
    __file__=str(Path(__file__))))
