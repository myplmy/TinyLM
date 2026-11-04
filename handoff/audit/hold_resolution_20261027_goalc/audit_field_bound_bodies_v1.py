"""Reuse exact-body diagnostics on eight frozen field pages; never admit them."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
VERSIONS = {1: 'v17', 2: 'v8', 3: 'v6', 4: 'v12', 5: 'v9', 6: 'v13', 7: 'v8', 8: 'v6'}
sources = [(f'remaining_field_title_page_{page:03}_counter_v1', version) for page, version in VERSIONS.items()]
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
assert hashlib.sha256(contract_path.read_bytes()).hexdigest().upper() == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
source = AUDIT / 'audit_exact_cohort_bodies_v6.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
loops = [node for node in tree.body if isinstance(node, ast.For) and
         isinstance(node.target, ast.Tuple) and [part.id for part in node.target.elts] == ['cohort', 'version']]
assert len(loops) == 1
loops[0].iter = ast.parse(repr(sources), mode='eval').body
out_index = [index for index, node in enumerate(tree.body) if isinstance(node, ast.Assign) and
             any(isinstance(target, ast.Name) and target.id == 'out' for target in node.targets)]
assert len(out_index) == 1
tree.body = tree.body[:out_index[0]]
row_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and
             isinstance(node.func, ast.Name) and node.func.id == 'dict' and
             any(item.arg == 'candidate_body_changed_blocks' for item in node.keywords)]
assert len(row_calls) == 1
row_calls[0].keywords.append(ast.keyword(arg='endings', value=ast.parse(
    "ending_metadata(ROOT/source['original']['path'], ROOT/row['body'])", mode='eval').body))
ast.fix_missing_locations(tree)


def ending_metadata(original_path, body_path):
    original = original_path.read_bytes()
    body = body_path.read_bytes()
    body.decode('utf-8')
    return dict(original_bytes=len(original), body_bytes=len(body),
                original_ends_lf=original.endswith(b'\n'), body_ends_lf=body.endswith(b'\n'),
                original_last_12_bytes_hex=original[-12:].hex().upper(),
                body_last_12_bytes_hex=body[-12:].hex().upper(), utf8_valid=True)


target = BASE / 'field_bound_body_diagnostics_v1'
assert not target.exists()
pins = {str(contract_path.relative_to(ROOT)): hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()}
reviewed_rows = 0
for cohort, version in sources:
    path = BASE / (cohort + '_snapshots') / version / 'complete.json'
    snapshot = json.loads(path.read_text(encoding='utf-8'))
    assert not snapshot['errors'] and snapshot['root_adopted'] == snapshot['cache_admitted'] == 0
    reviewed_rows += sum(row['saved'] for row in snapshot['coverage'].values())
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    manifest_path = BASE / cohort / 'manifest.json'
    pins[str(manifest_path.relative_to(ROOT))] = hashlib.sha256(manifest_path.read_bytes()).hexdigest().upper()
    for shard in snapshot['shards']:
        payload = (ROOT / shard['path']).read_bytes()
        assert hashlib.sha256(payload).hexdigest().upper() == shard['sha256']
        pins[shard['path']] = shard['sha256']
assert reviewed_rows == 2224
environment = {'__name__': 'field_body_diagnostics_reused_library', '__file__': str(source),
               'ending_metadata': ending_metadata}
exec(compile(tree, str(source), 'exec'), environment)
rows = environment['all_rows']
assert len(rows) == len({row['id'] for row in rows}) == 2220
assert reviewed_rows - len(rows) == 4
ending_counts = Counter()
for row in rows:
    values = row['endings']
    ending_counts['valid_utf8'] += values['utf8_valid']
    ending_counts['original_ends_lf'] += values['original_ends_lf']
    ending_counts['body_ends_lf'] += values['body_ends_lf']
    ending_counts['no_original_lf_to_body_lf'] += not values['original_ends_lf'] and values['body_ends_lf']
collector = AUDIT / 'collect_exact_cohort_reviews_v5.py'
names = {'write_json_new', 'shard_records'}
nodes = [node for node in ast.parse(collector.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name in names]
assert len(nodes) == 2
scope = dict(ROOT=ROOT, inv=environment['inv'], json=json, LIMIT=5_000_000)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(collector), 'exec'), scope)
shards = scope['shard_records'](target, rows)
for path in (source, collector, Path(__file__).resolve(), AUDIT / 'numeric_atom_integrity_v1.py',
             AUDIT / 'FIELD_BODY_DIAGNOSTICS_REUSE_IMPACT_V1.md',
             AUDIT / 'POST_HOLD_EMPTY_SECTION_BOUNDARY_V1.md'):
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
for name, module in list(sys.modules.items()):
    if name.startswith('scripts.p106b_hold_resolution_') and getattr(module, '__file__', None):
        path = Path(module.__file__).resolve()
        if path.suffix == '.py' and path.is_relative_to(ROOT / 'scripts'):
            pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
for name, expected in pins.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest().upper() == expected, name
result = dict(status='ALL_2220_BOUND_FIELD_BODIES_CPU_READBACK_NOT_SEMANTIC_APPROVAL',
              recorded_at=datetime.now(timezone.utc).isoformat(), versions=VERSIONS,
              saved_review_rows=reviewed_rows, body_pairs_checked=len(rows), reviewed_bodyless_whole_holds=4,
              counts=dict(environment['counts']), cohorts=environment['cohorts'], ending_counts=dict(ending_counts),
              shards=shards, input_pins=pins, restricted_body_reads=0,
              reused_numeric_code_unicode_style_order_and_memo_guards=True,
              original_and_selected_body_changes=0, root_or_cache_adoptions=0,
              whole_goal_complete=False, training_authorized=False,
              limits='Diagnostic flags require source context; zero flags are not semantic acceptance. Final LF counts record actual byte differences and do not waive other body changes.')
receipt = scope['write_json_new'](target / 'complete.json', result)
scope['write_json_new'](AUDIT / 'FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json', result)
print(json.dumps(dict(status=result['status'], body_pairs=len(rows), counts=result['counts'],
                     ending_counts=dict(ending_counts), shards=len(shards), receipt=receipt), ensure_ascii=False))
