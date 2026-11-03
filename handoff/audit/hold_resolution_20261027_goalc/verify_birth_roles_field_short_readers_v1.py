"""Reuse actual field-call verification with the two exact new role registries."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
prepared_path = AUDIT / 'FIELD_BIRTH_ROLES_SHORT_READERS_PREPARED_V1.json'
prepared = json.loads(prepared_path.read_bytes())
config_path = ROOT / prepared['config']['path']
assert hashlib.sha256(config_path.read_bytes()).hexdigest().upper() == prepared['config']['sha256']
config = json.loads(config_path.read_bytes())
cases = {}
for role in ('context_controls', 'context_latin'):
    item = config['roles'][role]['1']
    path = ROOT / item['path']
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest().upper() == item['sha256']
    registry = json.loads(data)
    cases[role] = (1, next(iter(registry['sources'])))
control_id, other_id = cases['context_controls'][1], cases['context_latin'][1]
negative = [(1, other_id, 1, None, 'other role source'),
            (2, control_id, 1, None, 'wrong page source'),
            (1, control_id, 1000000, None, 'packet outside sequence'),
            (1, control_id, 1, 0, 'piece outside sequence'),
            (1, 'expanded_train:756966', 1, None, 'restricted source ID')]
frozen = AUDIT / 'verify_field_short_readers_v1.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
counts = dict(cases=0, negative=0, paths=0)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'cases' for target in node.targets):
        node.value = ast.parse(repr(cases), mode='eval').body
        counts['cases'] += 1
    if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and [ast.unparse(value) for value in node.target.elts] == ['page', 'ident', 'packet', 'piece', 'reason']:
        node.iter = ast.parse(repr(negative), mode='eval').body
        counts['negative'] += 1
    if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'paths' for target in node.targets):
        node.value.elts += [ast.parse("AUDIT / 'prepare_birth_roles_field_short_readers_v1.py'", mode='eval').body,
                           ast.parse("AUDIT / 'verify_field_short_readers_v1.py'", mode='eval').body]
        counts['paths'] += 1
assert set(counts.values()) == {1}
mapping = {'FIELD_SHORT_READERS_PREPARED_V1.json': 'FIELD_BIRTH_ROLES_SHORT_READERS_PREPARED_V1.json',
           'FIELD_SHORT_READERS_RUNTIME_VERIFIED_V1.json': 'FIELD_BIRTH_ROLES_SHORT_READERS_RUNTIME_VERIFIED_V1.json',
           'context_hangul': 'context_controls'}


class Namespace(ast.NodeTransformer):
    def visit_Constant(self, node):
        if type(node.value) is int and node.value == 108:
            return ast.copy_location(ast.Constant(72), node)
        if isinstance(node.value, str) and node.value in mapping:
            return ast.copy_location(ast.Constant(mapping[node.value]), node)
        return node


tree = Namespace().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'), {'__file__': __file__, '__name__': '__main__'})
