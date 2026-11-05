"""Keep exact local saving and allow only the three owned rule27 script paths."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('commit_explicit_checkpoint_v4.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'C49A70FF1B7C18EB9008FE39CB9B132A5B43486C29D236B404F3C3A19EC42A40'
code = raw.decode('utf-8')
anchor = 'ast.fix_missing_locations(tree)'
assert code.count(anchor) == 1
addition = ''.join('values.elts.append(ast.Constant(' + repr(name) + '))' + chr(10)
    for name in ['scripts/p106b_hold_resolution_disambiguation_v1.py',
                 'scripts/p106b_hold_resolution_policy_v27.py',
                 'scripts/test_p106b_hold_resolution_policy_v27.py'])
code = code.replace(anchor, addition + anchor)
exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__))))
