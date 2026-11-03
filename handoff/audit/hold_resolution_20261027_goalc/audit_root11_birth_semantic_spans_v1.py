"""Reuse existing quantity/field diagnostics on the completed independent cohort."""
from pathlib import Path
import ast

SOURCE = Path(__file__).with_name('audit_birth_semantic_spans_v3.py')
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
mapping = {
    'remaining_birth_full_counter_v1/manifest.json': 'birth_root11_independent_v1/manifest.json',
    'remaining_birth_full_counter_v1_snapshots/v12/complete.json': 'birth_root11_independent_v1_snapshots/v28/complete.json',
    'BIRTH_SEMANTIC_SPAN_DIAGNOSTICS_V3.json': 'ROOT11_BIRTH_SEMANTIC_SPAN_DIAGNOSTICS_V1.json',
}
seen = set()


class BindCompletedCohort(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in mapping:
            seen.add(node.value)
            return ast.copy_location(ast.Constant(mapping[node.value]), node)
        return node


tree = BindCompletedCohort().visit(tree)
assert seen == set(mapping), 'frozen diagnostic source shape changed'
ast.fix_missing_locations(tree)
exec(compile(tree, str(SOURCE), 'exec'), {'__file__': __file__, '__name__': 'completed_root11_birth_diagnostics'})
