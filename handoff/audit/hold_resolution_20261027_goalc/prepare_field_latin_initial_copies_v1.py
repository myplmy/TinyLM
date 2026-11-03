"""Reuse the controls bootstrap unchanged except exact role and output namespace."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
SOURCE = AUDIT / 'prepare_field_controls_initial_copies_v1.py'
TEMPLATE = AUDIT / 'prepare_birth_controls_initial_copies_v1.py'


class BindRole(ast.NodeTransformer):
    def visit_Constant(self, node):
        if type(node.value) is int and node.value == 3248:
            return ast.copy_location(ast.Constant(3749), node)
        if isinstance(node.value, str):
            return ast.copy_location(ast.Constant(node.value.replace('context_controls', 'context_latin')
                                                  .replace('CONTROLS', 'LATIN')), node)
        return node


template_tree = BindRole().visit(ast.parse(TEMPLATE.read_text(encoding='utf-8')))
ast.fix_missing_locations(template_tree)
bound_template = ast.unparse(template_tree)
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
assignments = [node for node in tree.body if isinstance(node, ast.Assign) and
               any(isinstance(target, ast.Name) and target.id == 'template' for target in node.targets)]
assert len(assignments) == 1
assignments[0].value = ast.Name(id='bound_template', ctx=ast.Load())
tree = BindRole().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, str(SOURCE), 'exec'), dict(__file__=__file__, __name__='latin_field_initial_copies',
                                          bound_template=bound_template))
