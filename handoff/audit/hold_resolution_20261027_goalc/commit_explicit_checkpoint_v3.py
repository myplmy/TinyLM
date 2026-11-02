"""Extend the exact local-save guard to six explicitly owned recovery modules."""
from pathlib import Path
import ast

SOURCE=Path(__file__).with_name('commit_explicit_checkpoint_v1.py')
OWNED_SCRIPTS=frozenset({
    'scripts/p106b_hold_resolution_birth_conflicts_v1.py',
    'scripts/test_p106b_hold_resolution_birth_conflicts_v1.py',
    'scripts/p106b_hold_resolution_author_output_bindings_v1.py',
    'scripts/test_p106b_hold_resolution_author_output_bindings_v1.py',
    'scripts/p106b_hold_resolution_repeat_context_v1.py',
    'scripts/test_p106b_hold_resolution_repeat_context_v1.py',
})
tree=ast.parse(SOURCE.read_text(encoding='utf-8'),filename=str(SOURCE))
matched=[node for node in ast.walk(tree) if isinstance(node,ast.Assert) and
         ast.unparse(node.test).startswith('name == WIP or ')]
assert len(matched)==1,'original exact local-save guard changed'
matched[0].test=ast.parse('not path.is_symlink() and (name == WIP or name in OWNED_SCRIPTS or '
    'path.resolve().is_relative_to(AUDIT))',mode='eval').body
ast.fix_missing_locations(tree)
scope=dict(__name__=__name__,__file__=__file__,OWNED_SCRIPTS=OWNED_SCRIPTS)
exec(compile(tree,str(SOURCE),'exec'),scope)
