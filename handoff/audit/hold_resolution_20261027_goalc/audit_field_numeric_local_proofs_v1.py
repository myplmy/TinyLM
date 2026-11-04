"""Apply the existing local atom proofs only to flagged new field pairs."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
contract = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
assert hashlib.sha256(contract.read_bytes()).hexdigest().upper() == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
FROZEN = AUDIT / 'audit_numeric_local_proofs_v1.py'
tree = ast.parse(FROZEN.read_text(encoding='utf-8'))
source_assignments = [node for node in tree.body if isinstance(node, ast.Assign) and
                      any(isinstance(target, ast.Name) and target.id == 'source_path' for target in node.targets)]
assert len(source_assignments) == 1
source_assignments[0].value = ast.parse("AUDIT / 'FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json'", mode='eval').body
diagnostic_assignments = [node for node in tree.body if isinstance(node, ast.Assign) and
                          any(isinstance(target, ast.Name) and target.id == 'diagnostic' for target in node.targets)]
assert len(diagnostic_assignments) == 1
diagnostic_assignments[0].value = ast.parse('load_sharded(source_path)', mode='eval').body
outputs = [node for node in ast.walk(tree) if isinstance(node, ast.Constant) and
           node.value == 'EXACT_COHORT_NUMERIC_LOCAL_PROOFS_V1.json']
assert len(outputs) == 1
outputs[0].value = 'FIELD_BOUND_NUMERIC_LOCAL_PROOFS_V1.json'
reports = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
           isinstance(node.func, ast.Name) and node.func.id == 'dict' and
           any(keyword.arg == 'producer_sha256' for keyword in node.keywords)]
assert len(reports) == 1
reports[0].keywords.append(ast.keyword(arg='reused_producer_sha256',
    value=ast.Constant(value=hashlib.sha256(FROZEN.read_bytes()).hexdigest().upper())))
ast.fix_missing_locations(tree)


def load_sharded(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    rows = []
    for pin in value['shards']:
        payload = (ROOT / pin['path']).read_bytes()
        assert hashlib.sha256(payload).hexdigest().upper() == pin['sha256']
        rows += json.loads(payload)
    assert len(rows) == value['body_pairs_checked'] == 2220
    assert sum(bool(row['numeric_atom_flags']) for row in rows) == 79
    return dict(value, rows=rows)


exec(compile(tree, str(FROZEN), 'exec'),
     dict(__name__='field_numeric_local_proofs_reused_library', __file__=__file__, load_sharded=load_sharded))
