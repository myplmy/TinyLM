"""Reuse the same field preparer for two additional, already assigned roles."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'prepare_field_short_readers_v1.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
matches = 0
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'roles' for target in node.targets):
        node.value = ast.parse(repr({'context_controls': 'c', 'context_latin': 'l'}), mode='eval').body
        matches += 1
assert matches == 1
mapping = {
    'field_short_reader_registries_v1': 'field_birth_roles_short_reader_registries_v1',
    'FIELD_SHORT_READER_CONFIG_V1.json': 'FIELD_BIRTH_ROLES_SHORT_READER_CONFIG_V1.json',
    'FIELD_SHORT_READERS_PREPARED_V1.json': 'FIELD_BIRTH_ROLES_SHORT_READERS_PREPARED_V1.json',
}


class Namespace(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in mapping:
            return ast.copy_location(ast.Constant(mapping[node.value]), node)
        return node


tree = Namespace().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'), {'__file__': __file__, '__name__': '__main__'})
