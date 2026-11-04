"""Capture the actual independent consumer process after the real build exit."""
from pathlib import Path
import hashlib

AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'verify_guarded_partial_cache_v2_retry_v2.py'
assert hashlib.sha256(frozen.read_bytes()).hexdigest().upper()=='7170B4FAE635C9980D3D7C4EC8607FB930CA3233C293AE0485A4701B7B5D2FB4'
code=frozen.read_text(encoding='utf-8')
replacements={
    'cache_reviewed_partial_v2':'cache_reviewed_partial_v4',
    'CACHE_REVIEWED_PARTIAL_V2':'CACHE_REVIEWED_PARTIAL_V4',
    'consume_guarded_partial_cache_v2_library_v1.py':'consume_guarded_partial_cache_v4_library_v1.py',
    'roster_reviewed_partial_v2':'roster_reviewed_partial_v4',
    'ROOT_AUTHORED_SELECTIONS_V10.json':'ROOT_AUTHORED_SELECTIONS_V12.json',
    'cache_reviewed_partial_v4_verify_v2.log':'cache_reviewed_partial_v4_verify_v1.log',
    'CACHE_REVIEWED_PARTIAL_V4_VERIFY_EXIT_V2.json':'CACHE_REVIEWED_PARTIAL_V4_VERIFY_EXIT_V1.json',
    'CACHE_REVIEWED_PARTIAL_V4_VERIFY_STARTED_V2.json':'CACHE_REVIEWED_PARTIAL_V4_VERIFY_STARTED_V1.json'}
for before,after in replacements.items():
    assert before in code,('frozen independent recorder anchor changed',before)
    code=code.replace(before,after)
before="['verified.json','recovery_verified.json','partial_resolution_verified.json','restricted_metadata_verified.json']"
assert code.count(before)==2
code=code.replace(before,"['verified.json','recovery_verified.json','partial_resolution_verified.json','restricted_metadata_verified.json','baseline_preservation_scope.json']")
exec(compile(code,str(frozen),'exec'),dict(__name__='actual_cache4_independent_consumer',__file__=str(Path(__file__))))
