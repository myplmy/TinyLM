"""Record a real immutable cache5 build after the exact ROOT13 roster proof."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest().upper()
frozen=AUDIT/'run_guarded_partial_cache_v3.py'
assert sha(frozen)=='098030E9811E363FAC8C1E1A513A7BCC91C5540301C06E0E9E817C75E85F4E84'
verified=AUDIT/'ROOT13_ROSTER_V5_INDEPENDENT_VERIFIED_V1.json'
assert sha(verified)=='7C513E7EC62064F2255D3781C828639AF51E073A3CD857AFEA92BA65BE57CF7F'
proof=json.loads(verified.read_bytes())
assert proof['changed_sources']==436 and proof['expected_cache_HOLD_positions']==109064
for name,expected in proof['input_pins'].items():assert sha(ROOT/name)==expected
code=frozen.read_text(encoding='utf-8')
for before,after in {
    'cache_reviewed_partial_v3':'cache_reviewed_partial_v5',
    'CACHE_REVIEWED_PARTIAL_V3':'CACHE_REVIEWED_PARTIAL_V5',
    'guarded_reviewed_cache_v4.py':'guarded_reviewed_cache_v5.py',
    'roster_reviewed_partial_v3':'roster_reviewed_partial_v5',
    'reviewed_partial_adoptions_v3':'reviewed_partial_adoptions_v5',
    'ROOT_AUTHORED_SELECTIONS_V11.json':'ROOT_AUTHORED_SELECTIONS_V13.json',
    'guarded_partial_proposals_v3':'guarded_partial_proposals_v5'}.items():
    assert before in code;code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='actual_cache5_CPU_build',__file__=str(Path(__file__))))
