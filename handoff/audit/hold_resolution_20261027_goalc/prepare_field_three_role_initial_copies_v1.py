"""Reuse the frozen initial-copy workflow for three exact remaining roles."""
from pathlib import Path
from collections import Counter
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
SOURCE = AUDIT / 'prepare_field_controls_initial_copies_v1.py'
TEMPLATE = AUDIT / 'prepare_birth_controls_initial_copies_v1.py'
ROLES = {'context_hangul': ('HANGUL', 3724),
         'historical_review': ('HISTORICAL', 3757),
         'legacy_review': ('LEGACY', 3759)}
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
assert hashlib.sha256(contract_path.read_bytes()).hexdigest().upper() == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
contract = json.loads(contract_path.read_bytes())
index_path = BASE / 'remaining_field_title_readers_v1/complete.json'
index = json.loads(index_path.read_bytes())
assert len(index['pages']) == 36 and index['sources'] == 18237
output = AUDIT / 'FIELD_THREE_ROLE_INITIAL_COPIES_COMPLETE_V1.json'
assert not output.exists()
counts = Counter()
preflight_pins = {}
for page in index['pages']:
    manifest_path = ROOT / page['path']
    assert manifest_path == BASE / page['group'] / 'manifest.json'
    payload = manifest_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest().upper()
    assert digest == page['sha256']
    preflight_pins[str(manifest_path.relative_to(ROOT))] = digest
    manifest = json.loads(payload)
    for role, (label, _) in ROLES.items():
        directory = BASE / 'agents' / role / page['group']
        assert not (directory / 'ROOT_UNCHANGED_INITIAL_COPIES_V1.md').exists()
        receipt = AUDIT / f'FIELD_{label}_PAGE_{page["page"]:03}_INITIAL_COPIES_VERIFIED_V1.json'
        assert not receipt.exists()
        for row in manifest['rows']:
            if row['role'] != role:
                continue
            assert row['id'] not in contract['restricted_ids']
            assert row['original']['sha256'] not in contract['restricted_hashes']
            target = directory / (row['id'].replace(':', '_') + '_initial_candidate_v1.txt')
            assert not target.exists() and not target.is_symlink()
            counts[role] += 1
assert dict(counts) == {role: value[1] for role, value in ROLES.items()}
assert sum(counts.values()) == 11240

results = []
for role, (label, expected) in ROLES.items():
    assert not (AUDIT / f'FIELD_{label}_INITIAL_COPIES_BUILD_V1.log').exists()
    assert not (AUDIT / f'FIELD_{label}_INITIAL_COPIES_COMPLETE_V1.json').exists()

    class BindRole(ast.NodeTransformer):
        def visit_Constant(self, node):
            if type(node.value) is int and node.value == 3248:
                return ast.copy_location(ast.Constant(expected), node)
            if isinstance(node.value, str):
                return ast.copy_location(ast.Constant(node.value.replace('context_controls', role)
                                                      .replace('CONTROLS', label)), node)
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
    exec(compile(tree, str(SOURCE), 'exec'), dict(__file__=__file__,
          __name__=role + '_field_initial_copies', bound_template=bound_template))
    receipt_path = AUDIT / f'FIELD_{label}_INITIAL_COPIES_COMPLETE_V1.json'
    value = json.loads(receipt_path.read_bytes())
    assert value['sources'] == expected and len(value['pages']) == 36
    assert value['root_authored_cleaned_bodies'] == value['new_reviews'] == value['cache_admitted'] == 0
    results.append(dict(role=role, sources=expected, pages=36,
                        receipt=dict(path=str(receipt_path.relative_to(ROOT)),
                                     sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest().upper())))

for path in (contract_path, index_path, SOURCE, TEMPLATE, Path(__file__).resolve(),
             AUDIT / 'FIELD_THREE_ROLE_INITIAL_COPIES_IMPACT_V1.md'):
    preflight_pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
result = dict(status='THREE_ROLE_EXACT_UNCHANGED_FIELD_INITIAL_COPIES_NOT_REVISIONS',
              roles=results, total_sources=11240, role_page_groups=108,
              metadata_preflight_actual_output='311f54', input_pins=preflight_pins,
              reused_controls_workflow_and_protection_checks=True,
              original_source_code_executed=False, protected_body_reads=0,
              original_or_candidate_changed=False, root_authored_cleaned_bodies=0,
              new_reviews=0, cache_admitted=0, whole_goal_complete=False, training_authorized=False)
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], roles=3, role_page_groups=108,
                     unchanged_copies=11240, new_cleaned_bodies=0, admitted=0), ensure_ascii=False))
