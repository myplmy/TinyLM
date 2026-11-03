"""Recover five exact prior review pins through the frozen runtime input preview."""
from pathlib import Path
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0, str(AUDIT))
sys.path.insert(0, str(ROOT))
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser, FROZEN
from scripts import p106b_hold_resolution_author_output_bindings_v1 as output_binding

reused = AUDIT / 'audit_remaining_ordered_flag_provenance_v1.py'
tree = ast.parse(reused.read_text(encoding='utf-8'))
names = {'sha', 'read', 'verify', 'role_from_review'}
definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
assert len(definitions) == len(names)
assert all(not node.decorator_list for node in definitions)
pins = {}
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(reused), 'exec'), globals())

prior_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V10_PREVIEW4.json'
current_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json'
runtime_path = BASE / 'runtime_guard_counter_v1/manifest.json'
audit_path = AUDIT / 'ORDERED_FLAG_OLD_PATH_PROVENANCE_AUDIT_V2.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
prior, current, runtime, previous_audit, contract = map(read,
    (prior_path, current_path, runtime_path, audit_path, contract_path))
assert runtime['input_pins'][str(prior_path.relative_to(ROOT))] == pins[str(prior_path.relative_to(ROOT))]
assert pins[str(current_path.relative_to(ROOT))] == '624AE91E66B4104F864E389B001A58E2C67C2D509D78F7E348DABC4FAD30A152'
prior_choices = {row['id']: row['selected'] for row in prior['rows']}
current_choices = {row['id']: row['selected'] for row in current['rows']}
runtime_sources = {row['id']: row for row in runtime['rows']}
old_failures = {row['id']: row for row in previous_audit['rows']
                if row['status'] == 'EXISTING_BINDING_REQUIRES_FURTHER_AUDIT'}
ids = {'expanded_train:1254536', 'expanded_train:255342', 'expanded_train:48585',
       'expanded_train:689736', 'expanded_train:8121'}
assert set(old_failures) == ids
resolve, parse, parser_sha = load_parser()
pins[str(FROZEN.relative_to(ROOT))] = parser_sha
manifests = {}


def exact_output(selected, source, namespace):
    review = verify(selected['review'], archive=True)
    entry = exact_entry(review, source['id'], namespace, resolve, parse)
    assert len(entry['cells']) == 5
    status = {'REVISE_TEXT': 'EDIT_TEXT', 'ACCEPT_CANDIDATE': 'ADOPT_CANDIDATE'}[entry['cells'][1]]
    role = role_from_review(selected['review'])
    assert role == selected['role'] == source['role']
    directory = BASE / 'agents' / role / selected['cohort']
    paths = {label: dict(source[label], path=str(ROOT / source[label]['path']))
             for label in ('original', 'candidate')}
    name = output_binding.declared_txt_basename(entry['cells'][3], source['id'], directory, paths, status)
    output = ROOT / source['candidate']['path'] if status == 'ADOPT_CANDIDATE' else directory / name
    output_pin = dict(path=str(output.relative_to(ROOT)), sha256=selected['clean_text_sha256'])
    verify(output_pin)
    verify(dict(path=selected['body'], sha256=selected['clean_text_sha256']))
    return dict(review=selected['review'], exact_review_row=entry['raw'],
                output=output_pin, declared_status=entry['cells'][1], role=role)


rows = []
for ident in sorted(ids):
    source, older, newer = runtime_sources[ident], prior_choices[ident], current_choices[ident]
    assert ident not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    assert source['original']['sha256'] == older['original']['sha256'] == old_failures[ident]['original_text_sha256']
    assert source['candidate']['sha256'] == older['clean_text_sha256']
    assert source['previous_role'] == older['role'] and source['role'] != older['role']
    assert newer['cohort'] == 'runtime_guard_counter_v1'
    assert newer['clean_text_sha256'] == old_failures[ident]['current_body_sha256']
    assert older['cohort'] in {'resume_guard_independent_20261102_v1', 'root_join_conflict_counter_v1'}
    manifest_path = BASE / older['cohort'] / 'manifest.json'
    if older['cohort'] not in manifests:
        manifests[older['cohort']] = {row['id']: row for row in read(manifest_path)['rows']}
    old_source = manifests[older['cohort']][ident]
    assert old_source['original']['sha256'] == source['original']['sha256']
    verify(source['original'])
    verify(source['candidate'])
    verify(old_source['original'])
    before = exact_output(older, old_source, set(manifests[older['cohort']]))
    after = exact_output(newer, source, set(runtime_sources))
    rows.append(dict(id=ident, status='EXACT_PRIOR_AND_CURRENT_REVIEW_OUTPUT_CHAIN_VERIFIED',
                     original=source['original'], runtime_candidate=source['candidate'],
                     prior=before, current=after, runtime_previous_role=source['previous_role'],
                     runtime_root_note=source.get('review'),
                     root_note_is_not_used_as_author_review=True,
                     input_equals_current_body=source['candidate']['sha256'] == newer['clean_text_sha256'],
                     distinct_named_roles=True, historical_input_emission_proven=False,
                     root_semantic_waiver=False, independent_semantic_pass_granted=False))
known = set(previous_audit['combined_record_scopes'])
assert len(known) == 385 and not (known & ids)
combined = sorted(known | ids)
assert len(combined) == 390
for path in (reused, FROZEN, AUDIT / 'exact_manifest_review_row_binding_v1.py',
             ROOT / 'scripts/p106b_hold_resolution_author_output_bindings_v1.py', Path(__file__).resolve()):
    pins[str(path.relative_to(ROOT))] = sha(path.read_bytes())
result = dict(status='FIVE_RUNTIME_PRIOR_OUTPUT_OWNERSHIP_LINKS_RECOVERED_NOT_SEMANTIC_PASSES',
              rows=rows, prior_linked_record_scopes=385, additional_exact_chain_links=5,
              combined_record_scopes=combined, linked_flag_sources_in_these_scopes=390,
              total_ordered_flags=585, not_linked_in_these_scopes=195,
              reused_function_definitions=sorted(names), reused_top_level_executed=False,
              runtime_manifest_pins_prior_preview=True,
              old_root11_directly_pins_runtime_manifest=False,
              limits=['Exact saved role/output chains were recovered from the preview pinned by the runtime manifest.',
                      'This does not add historical delivery evidence, new full-source semantic reads, or flag waivers.',
                      'The remaining 195 may have additional valid evidence; they are not automatically sent to rereading.'],
              input_pins=pins, root_or_cache_adoptions=0, protected_body_reads=0,
              automatic_flag_waivers=0, whole_goal_complete=False)
target = AUDIT / 'RUNTIME_PRIOR_REVIEW_OUTPUT_CHAIN_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], additional=5, linked=390, unlinked=195,
                     automatic_flag_waivers=0), ensure_ascii=False))
