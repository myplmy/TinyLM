"""Independently check four recovered rows, declared inputs and recipe output."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser
from scripts import p106b_hold_resolution_recipe_frame_v3 as frame
from scripts import p106b_hold_resolution_text_edits_v2 as edits
pins = {}
CODE_NAMES = {'p106b_hold_resolution_author_output_bindings_v1.py',
              'p106b_hold_resolution_recipe_frame_v1.py', 'p106b_hold_resolution_recipe_frame_v2.py',
              'p106b_hold_resolution_recipe_frame_v3.py', 'p106b_hold_resolution_text_edits.py',
              'p106b_hold_resolution_text_edits_v2.py'}
CODE_PATHS = {ROOT / 'scripts' / name for name in CODE_NAMES}


def checked(pin):
    path = ROOT / pin['path']
    assert not path.is_symlink() and (path.resolve().is_relative_to(BASE) or
                                     path.resolve().is_relative_to(AUDIT) or path in CODE_PATHS)
    payload = path.read_bytes()
    assert 0 < len(payload) < 20_000_000
    value = hashlib.sha256(payload).hexdigest().upper()
    assert value == pin['sha256']
    pins[pin['path']] = value
    return payload


path = AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V4.json'
result_pin = dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper())
result = json.loads(checked(result_pin))
for name, value in result['input_pins'].items():
    checked(dict(path=name, sha256=value))
for name in CODE_NAMES:
    path = ROOT / 'scripts' / name
    relative = str(path.relative_to(ROOT))
    assert path.read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + relative], cwd=ROOT)
    checked(dict(path=relative, sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper()))
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text(encoding='utf-8'))
legacy = json.loads((BASE / 'legacy_span_review_v2/manifest.json').read_text(encoding='utf-8'))
legacy_rows = {row['id']: row for row in legacy['rows']}
current_manifest = json.loads((BASE / 'authored_postsignal_review_v1/manifest.json').read_text(encoding='utf-8'))
source_rows = {row['id']: row for row in current_manifest['rows']}
previous = json.loads((AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V3.json').read_text(encoding='utf-8'))
assert {row['id'] for row in result['rows']} == {'expanded_train:30538', 'expanded_train:3902', 'expanded_train:8699', 'expanded_train:17705'}
assert set(result['combined_record_scopes']) == set(previous['combined_record_scopes']) | {row['id'] for row in result['rows']}
assert len(result['combined_record_scopes']) == 468 and result['not_linked_in_these_scopes'] == 117
resolve, parse, _ = load_parser()
recipes = 0
for row in result['rows']:
    ident = row['id']
    source = source_rows[ident]
    assert ident not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes']
    assert row['original'] == source['original'] and row['candidate'] == source['candidate']
    checked(row['original'])
    candidate = checked(row['candidate'])
    prior, current = row['prior'], row['current']
    assert prior['role'] == source['original_author'] and prior['role'] != current['role']
    assert checked(prior['output']) == candidate
    checked(current['output'])
    current_review = checked(current['review'])
    if current['review'].get('archive'):
        assert checked(dict(path=current['review']['archive'], sha256=current['review']['sha256'])) == current_review
    prior_review = checked(prior['review'])
    pentries = [entry for entry in parse(prior_review, allow_sections=True) if resolve(entry['cells'][0]) == ident]
    assert sum(entry['raw'] == prior['exact_review_row'] for entry in pentries) == 1
    centries = [entry for entry in parse(current_review, allow_sections=True) if resolve(entry['cells'][0]) == ident]
    assert len(centries) == 1 and centries[0]['raw'] == current['exact_review_row']
    proof = prior['exact_prior_output_proof']
    if 'recipe' in proof:
        recipe = checked(proof['recipe'])
        assigned = legacy_rows[ident]['paths']
        canonical, compiler = frame.canonicalize(recipe.decode('utf-8'), source_id=ident, paths=assigned, root=ROOT)
        assert proof['assigned_recipe_base'] == assigned[compiler['base']]
        rendered, _ = edits.apply_recipe(checked(assigned[compiler['base']]).decode('utf-8'), canonical,
                                         source_id=ident, base=compiler['base'])
        assert rendered.encode('utf-8') == candidate
        assert not proof['historical_recipe_bytes_or_delivery_time_proven']
        recipes += 1
    else:
        assert ident == 'expanded_train:8699' and len(pentries) == 2
        assert [entry['cells'][1] for entry in pentries] == ['NEEDS_ROOT', 'EDIT_TEXT']
        assert pentries[1]['cells'][0] == '8699 (root 결정 후 정정)'
        assert proof['explicitly_superseded_row_history'] == [pentries[0]['raw']]
        assert checked(proof['authored_output']) == candidate
    if ident in {'expanded_train:30538', 'expanded_train:17705'}:
        entry = centries[0]
        assert entry['cells'][1] == 'ACCEPT_CANDIDATE' and entry['header'][3] == '정확 출력'
        declared = entry['cells'][3].strip(' `*')
        if ident == 'expanded_train:30538':
            assert declared == '없음'
        else:
            assert not set(declared.split('/')) & {'.', '..'}
            assert (BASE / declared).resolve() == (ROOT / row['candidate']['path']).resolve()
        assert candidate == checked(current['output'])
    assert row['automatic_flag_waiver'] is row['independent_semantic_pass_granted'] is False
assert recipes == 3

# Reject ambiguous, unmarked and chronologically reversed amendment fixtures.
producer = AUDIT / 'trace_explicit_prior_owner_chains_v4.py'
nodes = [node for node in ast.parse(producer.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name == 'explicit_8699_amendment']
scope = {}
assert len(nodes) == 1
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(producer), 'exec'), scope)
choose = scope['explicit_8699_amendment']
old = dict(cells=['8699', 'NEEDS_ROOT'], number=1)
new = dict(cells=['8699 (root 결정 후 정정)', 'REVISE_TEXT'], number=2)
assert choose([old, new]) is new
negative = 0
for fixture in [[old, new, dict(new)],
                [old, dict(cells=['8699', 'REVISE_TEXT'], number=2)],
                [old, dict(cells=new['cells'], number=0)]]:
    try:
        choose(fixture)
    except AssertionError:
        negative += 1
    else:
        raise AssertionError('invalid amendment fixture accepted')
assert negative == 3
pins[str(Path(__file__).resolve().relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
report = dict(status='FOUR_PRIOR_LINKS_INDEPENDENTLY_VERIFIED_WITH_LITERAL_REGENERATION',
              actual_linked_rows=4, linked_flag_scopes=468, unlinked_flag_scopes=117,
              literal_recipes_independently_regenerated=3,
              explicit_old_needs_root_row_preserved=1, current_accept_is_exact_assigned_candidate=2,
              pure_amendment_positive_probe=1, pure_amendment_negative_probes=3,
              producer_output_positive_probes=result['pure_output_positive_probes'],
              producer_output_and_identity_negative_probes=result['pure_output_and_identity_negative_probes'],
              exact_owned_code_paths_checked_unchanged_from_HEAD=6,
              production_output_binder_changed=False, historical_hashes_retrofilled=False,
              source_semantic_rereads=0, automatic_flag_waivers=0, root_or_cache_adoptions=0,
              input_pins=pins, whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_INDEPENDENT_VERIFIED_V4.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=report['status'], verified_links=4, recipes=3, linked=468, unlinked=117,
                     amendment_negative_probes=3, source_changed=False, root_adopted=0)))
