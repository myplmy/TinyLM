"""Use the same standard Git add/commit-only with exact pinned owned code."""
from pathlib import Path
import ast
import re
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import active_guard_v6_preflight_v1 as guard
from exact_owned_cleanup_code_scope_v1 import load,config_for_version

manifest_path=Path(sys.argv[sys.argv.index('--manifest')+1]).resolve()
assert manifest_path.parent==AUDIT
match=re.fullmatch(r'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V([1-9][0-9]*)\.json',manifest_path.name)
assert match is not None
extra=load(config_for_version(match[1]))
frozen=AUDIT/'commit_explicit_checkpoint_v3.py'
assert guard.inv.file_sha(frozen)=='65367BF2B5D74B4D0EA2D3961ADAB2E9D3274D2454FC5A1DE206A67A27BBF136'
tree=ast.parse(frozen.read_text(encoding='utf-8'))
matches=[n for n in tree.body if isinstance(n,ast.Assign) and
         any(isinstance(t,ast.Name) and t.id=='OWNED_SCRIPTS' for t in n.targets)]
assert len(matches)==1
values=matches[0].value.args[0]
assert isinstance(values,ast.Set)
old={n.value for n in values.elts}
inherited={'scripts/p106b_hold_resolution_review_safeguards_v4.py',
    'scripts/p106b_hold_resolution_disambiguation_v1.py','scripts/p106b_hold_resolution_policy_v27.py',
    'scripts/test_p106b_hold_resolution_policy_v27.py'}
values.elts=[ast.Constant(v) for v in sorted(old|inherited|set(extra))]
ast.fix_missing_locations(tree)
guard.activate()
exec(compile(tree,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__))))
guard.assert_no_protected_opens()
