"""Run the existing CPU build recorder against the verified ROOT12/roster4."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
frozen=AUDIT/'run_guarded_partial_cache_v3.py'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest().upper()
assert sha(frozen)=='098030E9811E363FAC8C1E1A513A7BCC91C5540301C06E0E9E817C75E85F4E84'
verified=AUDIT/'ROOT12_ROSTER_V4_INDEPENDENT_VERIFIED_V1.json'
assert sha(verified)=='84F98826D142D550F65F2C14C6A5E920C5BE2141E3639C29ABFDF70B5ED0D1EB'
proof=json.loads(verified.read_bytes())
assert proof['changed_sources']==123 and proof['expected_cache_HOLD_positions']==109931
for name,expected in proof['input_pins'].items():assert sha(ROOT/name)==expected
code=frozen.read_text(encoding='utf-8')
replacements={
    'cache_reviewed_partial_v3':'cache_reviewed_partial_v4',
    'CACHE_REVIEWED_PARTIAL_V3':'CACHE_REVIEWED_PARTIAL_V4',
    'guarded_reviewed_cache_v4.py':'guarded_reviewed_cache_v5.py',
    'roster_reviewed_partial_v3':'roster_reviewed_partial_v4',
    'reviewed_partial_adoptions_v3':'reviewed_partial_adoptions_v4',
    'ROOT_AUTHORED_SELECTIONS_V11.json':'ROOT_AUTHORED_SELECTIONS_V12.json',
    'guarded_partial_proposals_v3':'guarded_partial_proposals_v4'}
for before,after in replacements.items():
    assert before in code,('frozen CPU recorder anchor changed',before)
    code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='actual_cache4_CPU_build',__file__=str(Path(__file__))))
