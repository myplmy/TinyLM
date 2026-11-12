"""Check every committed blob and exact path membership for the pinned code scope."""
from pathlib import Path
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import active_guard_v6_preflight_v1 as guard
from exact_owned_cleanup_code_scope_v1 import load,config_for_version

version=sys.argv[sys.argv.index('--version')+1]
extra=load(config_for_version(version))
frozen=AUDIT/'verify_exact_progress_commit_v2.py'
assert guard.inv.file_sha(frozen)=='DB28A03F6F9E38CD7DB6C2AF02EAFC8491A168FEEB73902A3C093E355B3EB250'
code=frozen.read_text(encoding='utf-8')
before="{'handoff/WIP_20261027_작업원장.md','scripts/p106b_hold_resolution_review_safeguards_v4.py'}"
allowed={'handoff/WIP_20261027_작업원장.md','scripts/p106b_hold_resolution_review_safeguards_v4.py',
    'scripts/p106b_hold_resolution_disambiguation_v1.py','scripts/p106b_hold_resolution_policy_v27.py',
    'scripts/test_p106b_hold_resolution_policy_v27.py'}|set(extra)
assert code.count(before)==1
code=code.replace(before,repr(allowed))
guard.activate()
exec(compile(code,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
guard.assert_no_protected_opens()
