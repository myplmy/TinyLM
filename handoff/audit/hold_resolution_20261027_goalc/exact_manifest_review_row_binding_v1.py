"""Reuse canonical review parsing with an exact per-manifest numeric-ID bound."""
from pathlib import Path
import ast
import hashlib
import re

FROZEN = Path(__file__).with_name('collect_supplemental_candidates_v63.py')


def load_parser():
    payload = FROZEN.read_bytes()
    tree = ast.parse(payload.decode('utf-8'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and
             n.name in {'ident', 'review_entries'}]
    assert len(nodes) == 2
    for node in nodes:
        assert not node.decorator_list and all(isinstance(d, ast.Constant) for d in node.args.defaults)
    scope = {'re': re}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(FROZEN), 'exec'), scope)
    return scope['ident'], scope['review_entries'], hashlib.sha256(payload).hexdigest().upper()


def exact_entry(payload, source_id, allowed_source_ids, resolve, parse):
    if source_id not in allowed_source_ids:
        raise ValueError('source is outside the exact manifest')
    entries = [e for e in parse(payload) if resolve(e['cells'][0]) == source_id]
    if len(entries) != 1:
        raise ValueError('canonical source-ID review row is not uniquely bound')
    entry = entries[0]
    cell = entry['cells'][0].strip(' `*')
    if re.fullmatch(r'[0-9]+(?:\s+[(（][^()（）]*[)）])?', cell):
        number = re.match(r'[0-9]+', cell)[0]
        same_number = {key for key in allowed_source_ids if key.rsplit(':', 1)[1] == number}
        if same_number != {source_id}:
            raise ValueError('bare numeric ID has multiple source namespaces in this manifest')
    return entry
