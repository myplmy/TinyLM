"""Check only newly prepared other-type inputs, reusing the field file checker."""
from pathlib import Path
import ast
import sys

source = Path(__file__).with_name('record_field_reader_preparation_v1.py')
tree = ast.parse(source.read_text(encoding='utf-8'))
class Adapt(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            value = node.value.replace('remaining_field_title', 'remaining_other_types').replace('REMAINING_FIELD_TITLE', 'REMAINING_OTHER_TYPES')
            value = value.replace('ALL_FIELD_INPUTS', 'ALL_OTHER_TYPE_INPUTS')
            if node.value == 'cef422': value = '4c2d25_step_1'
            if node.value == 'fb818a': value = '4c2d25_step_2'
            return ast.copy_location(ast.Constant(value=value), node)
        if isinstance(node.value, int):
            mapping = {18237: 50162, 29659: 77879, 36: 98}
            return ast.copy_location(ast.Constant(value=mapping.get(node.value, node.value)), node)
        return node
tree = Adapt().visit(tree)
ast.fix_missing_locations(tree)
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
receipt = inv.cache.read(Path(__file__).with_name('OTHER_TYPE_READING_PREPARATION_PROCESS_EXIT_V1.json'))
assert receipt['process_exit_code'] == 0 and len(receipt['results']) == 3
assert all(row['process_exit_code'] == 0 for row in receipt['results'])
exec(compile(tree, str(source), 'exec'), {'__file__': __file__, '__name__': __name__})
