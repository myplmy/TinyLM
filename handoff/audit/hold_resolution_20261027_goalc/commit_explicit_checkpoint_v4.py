"""Add exactly one owned review safeguard module to the existing local saver."""
from pathlib import Path
import ast
import hashlib

frozen = Path(__file__).with_name('commit_explicit_checkpoint_v3.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '65367BF2B5D74B4D0EA2D3961ADAB2E9D3274D2454FC5A1DE206A67A27BBF136'
tree = ast.parse(raw.decode('utf-8'))
matches = [n for n in tree.body if isinstance(n, ast.Assign) and
    any(isinstance(t, ast.Name) and t.id == 'OWNED_SCRIPTS' for t in n.targets)]
assert len(matches) == 1
values = matches[0].value.args[0]
assert isinstance(values, ast.Set) and len(values.elts) == 6
values.elts.append(ast.Constant('scripts/p106b_hold_resolution_review_safeguards_v4.py'))
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'), dict(__name__=__name__,__file__=str(Path(__file__))))
