"""Reuse the unchanged-copy publisher for Latin's existing1353 inputs."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'prepare_birth_controls_initial_copies_v1.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
count_replacements = 0


class LatinCopies(ast.NodeTransformer):
    def visit_Constant(self, node):
        global count_replacements
        if isinstance(node.value, str):
            value = node.value.replace('context_controls', 'context_latin').replace('CONTROLS', 'LATIN')
            value = value.replace('1354', '1353')
            return ast.copy_location(ast.Constant(value=value), node)
        if isinstance(node.value, int) and not isinstance(node.value, bool) and node.value == 1354:
            count_replacements += 1
            return ast.copy_location(ast.Constant(value=1353), node)
        return node


tree = LatinCopies().visit(tree)
assert count_replacements == 3
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'), {'__file__': __file__, '__name__': 'latin_initial_copies'})
