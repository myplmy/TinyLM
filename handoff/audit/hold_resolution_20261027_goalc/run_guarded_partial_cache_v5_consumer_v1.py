"""Reuse the successful library-only consumer recorder with cache5 inputs."""
from pathlib import Path
import hashlib

AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'run_guarded_partial_cache_v4_consumer_v1.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='C7E7FC46394EB9954B36FB95CC5F3E2EAADB8F81262DE3659531B5EA1992596F'
code=frozen.read_text(encoding='utf-8')
for before,after in {
    'cache_reviewed_partial_v4':'cache_reviewed_partial_v5',
    'CACHE_REVIEWED_PARTIAL_V4':'CACHE_REVIEWED_PARTIAL_V5',
    'roster_reviewed_partial_v4':'roster_reviewed_partial_v5',
    'ROOT_AUTHORED_SELECTIONS_V12.json':'ROOT_AUTHORED_SELECTIONS_V13.json'}.items():
    assert before in code;code=code.replace(before,after)
# consume_guarded_partial_cache_v4_library_v1.py is a generic argparse library
# adapter. Reuse it with the new paths rather than re-entering CLI aliases.
exec(compile(code,str(frozen),'exec'),dict(__name__='actual_cache5_independent_consumer',__file__=str(Path(__file__))))
