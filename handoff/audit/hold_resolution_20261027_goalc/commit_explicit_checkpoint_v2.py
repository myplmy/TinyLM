"""Extend the existing exact-path save guard to four owned recovery modules."""
from pathlib import Path
import ast

SOURCE = Path(__file__).with_name("commit_explicit_checkpoint_v1.py")
OWNED_SCRIPTS = frozenset({
    "scripts/p106b_hold_resolution_birth_conflicts_v1.py",
    "scripts/test_p106b_hold_resolution_birth_conflicts_v1.py",
    "scripts/p106b_hold_resolution_author_output_bindings_v1.py",
    "scripts/test_p106b_hold_resolution_author_output_bindings_v1.py",
})

# Reuse the fully verified commit procedure. Only its path authorization
# assertion changes; staging, --only, parent/set/blob checks stay identical.
tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
matched = []
for node in ast.walk(tree):
    if isinstance(node, ast.Assert) and ast.unparse(node.test).startswith("name == WIP or "):
        matched.append(node)
assert len(matched) == 1, "the original exact-path guard contract changed"
matched[0].test = ast.parse(
    "not path.is_symlink() and (name == WIP or name in OWNED_SCRIPTS or "
    "path.resolve().is_relative_to(AUDIT))", mode="eval").body
ast.fix_missing_locations(tree)
scope = dict(__name__=__name__, __file__=__file__, OWNED_SCRIPTS=OWNED_SCRIPTS)
exec(compile(tree, str(SOURCE), "exec"), scope)
