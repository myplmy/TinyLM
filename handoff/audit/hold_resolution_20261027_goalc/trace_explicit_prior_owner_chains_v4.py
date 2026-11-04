"""Recover four exact historical bindings without changing production acceptance."""
from pathlib import Path
import ast
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser, FROZEN
from scripts.p106b_hold_resolution_author_output_bindings_v1 import declared_txt_basename as strict_output
from scripts import p106b_hold_resolution_recipe_frame_v3 as frame
from scripts import p106b_hold_resolution_text_edits_v2 as edits

pins = {}


def definitions(path, names):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(nodes) == len(names) and all(not node.decorator_list for node in nodes)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), globals())
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()


definitions(AUDIT / 'audit_remaining_ordered_flag_provenance_v1.py', {'sha', 'read', 'verify', 'role_from_review'})
definitions(AUDIT / 'trace_explicit_prior_owner_chains_v1.py', {'guard', 'manifest', 'assigned_role', 'bind'})
definitions(AUDIT / 'trace_explicit_prior_owner_chains_v2.py', {'normalized_entry'})
normalize_v2 = normalized_entry
resolve, parse_raw, parser_sha = load_parser()
pins[str(FROZEN.relative_to(ROOT))] = parser_sha


def normalized_entry(entry):
    header = entry.get('header')
    if header:
        entry = dict(entry, header=['출력' if label in {'출력 TXT 전체 경로', '실제 새 출력 파일', '실제 출력 연결'}
                                   else label for label in header])
    return normalize_v2(entry)


def parse(payload):
    return [normalized_entry(entry) for entry in parse_raw(payload, allow_sections=True)]


def historical_accept_cell(source_id, cell, candidate):
    value = cell.strip(' `*')
    if source_id == 'expanded_train:30538':
        assert value == '없음', 'unrecognized historical no-authored-file declaration'
        return dict(rule='EXPLICIT_ACCEPT_CANDIDATE_WITH_NO_NEW_AUTHORED_FILE', declared=value,
                    candidate=candidate)
    assert source_id == 'expanded_train:17705', 'not one of the two audited historical accept cells'
    assert value and not value.startswith('/') and not set(value.split('/')) & {'.', '..'}
    exact_relative = str(Path(candidate['path']).relative_to(BASE))
    assert value == exact_relative, 'relative declaration is not the exact BASE-relative assigned input'
    return dict(rule='EXACT_BASE_RELATIVE_ASSIGNED_CANDIDATE_PATH', declared=value,
                candidate=candidate)


accept_resolutions = {}


def declared_txt_basename(cell, source_id, directory, paths, status):
    if status == 'ADOPT_CANDIDATE' and source_id in {'expanded_train:30538', 'expanded_train:17705'}:
        accept_resolutions[source_id] = historical_accept_cell(source_id, cell, paths['candidate'])
        return Path(paths['candidate']['path']).name
    value = re.sub(r'\[([^\]\n]+)\]\(([^()\s]+)\)', lambda match: match[2], cell)
    names = re.findall(r'/[^\s`|()<>;,]+[.]txt|(?<![A-Za-z0-9_./-])[A-Za-z0-9_.-]+[.]txt', value)
    assert len(names) == 1, 'saved output must have one explicit TXT body'
    return strict_output(names[0], source_id, directory, paths, status)


def explicit_8699_amendment(entries):
    assert len(entries) == 2 and {entry['cells'][1] for entry in entries} == {'NEEDS_ROOT', 'REVISE_TEXT'}
    amended = [entry for entry in entries if entry['cells'][1] == 'REVISE_TEXT' and
               entry['cells'][0].strip(' `*') == '8699 (root 결정 후 정정)']
    assert len(amended) == 1, 'missing unique explicitly marked historical root amendment'
    assert amended[0]['number'] > next(entry['number'] for entry in entries if entry['cells'][1] == 'NEEDS_ROOT')
    return amended[0]


# Pure negative probes fail without assigned review/body I/O.
probe_candidate = dict(path=str(BASE / 'legacy_rendered_v3/AA/exact.txt'), sha256='A' * 64)
assert historical_accept_cell('expanded_train:30538', '없음', probe_candidate)['candidate'] == probe_candidate
assert historical_accept_cell('expanded_train:17705', 'legacy_rendered_v3/AA/exact.txt', probe_candidate)['candidate'] == probe_candidate
rejected = 0
for ident, cell in [('expanded_train:30538', 'other.txt'), ('expanded_train:17705', 'other/exact.txt'),
                    ('expanded_train:17705', '../legacy_rendered_v3/AA/exact.txt'),
                    ('expanded_train:17705', 'legacy_rendered_v3/AA/wrong.txt'),
                    ('expanded_train:3902', '없음')]:
    try:
        historical_accept_cell(ident, cell, probe_candidate)
    except (AssertionError, ValueError):
        rejected += 1
    else:
        raise AssertionError('historical output negative probe was accepted')
assert rejected == 5
contract = read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
assert pins[str((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').relative_to(ROOT))] == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
for ident, original_sha in [(contract['restricted_ids'][0], '0' * 64),
                             ('expanded_train:30538', contract['restricted_hashes'][0])]:
    try:
        guard(ident, original_sha)
    except ValueError:
        rejected += 1
    else:
        raise AssertionError('restricted identity guard did not reject')
previous = read(AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V3.json')
known = set(previous['combined_record_scopes'])
assert len(known) == 464
root = read(AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json')
assert pins[str((AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json').relative_to(ROOT))] == '624AE91E66B4104F864E389B001A58E2C67C2D509D78F7E348DABC4FAD30A152'
selected = {row['id']: row['selected'] for row in root['rows']}
integrity_path = AUDIT / 'authored_body_integrity_v2.json'
integrity = read(integrity_path)
manifests = {}
value, source_rows = manifest('authored_postsignal_review_v1')
assert value['pins'][str(integrity_path.relative_to(ROOT))] == pins[str(integrity_path.relative_to(ROOT))]
legacy_path = BASE / 'legacy_span_review_v2/manifest.json'
legacy = read(legacy_path)
assert pins[str(legacy_path.relative_to(ROOT))] == '6C01EC133BB105E7DC7E6B5A762F6F9F9E2E4ACE6AF3F478807026FE1392E7FA'
legacy_rows = {row['id']: row for row in legacy['rows']}
rows = []
for ident in ('expanded_train:30538', 'expanded_train:3902', 'expanded_train:8699', 'expanded_train:17705'):
    source = source_rows[ident]
    original_sha = source['original']['sha256']
    guard(ident, original_sha)
    prior_records = [row for row in integrity['records'] if row['id'] == ident and
                     row['clean_text_sha256'] == source['candidate']['sha256']]
    assert len(prior_records) == 1
    prior = prior_records[0]
    assert prior['original_text_sha256'] == original_sha
    evidence = prior['evidence']
    review_pin = dict(path=evidence['review'], sha256=evidence['review_sha256'])
    role = role_from_review(review_pin)
    assert role == source['original_author'] == assigned_role(legacy, ident)
    review = verify(review_pin)
    prior_entries = [entry for entry in parse(review) if resolve(entry['cells'][0]) == ident]
    entry = explicit_8699_amendment(prior_entries) if ident == 'expanded_train:8699' else \
        exact_entry(review, ident, set(legacy_rows), resolve, parse)
    directory = (ROOT / review_pin['path']).parent
    output_pin = dict(path=prior['body'], sha256=source['candidate']['sha256'])
    verify(dict(path=prior['source'], sha256=original_sha))
    verify(output_pin)
    proof = {}
    if prior['decision'] == 'EDIT_RECIPE':
        assert entry['cells'][1] == 'EDIT_RECIPE'
        references = re.findall(r'(?<![A-Za-z0-9_./-])' + re.escape(ident.replace(':', '_')) +
                                r'(?:_v[0-9]+)?[._]edits(?:_v[0-9]+)?[.]md', entry['cells'][3])
        assert len(references) == 1
        path = directory / references[0]
        recipe = path.read_bytes()
        recipe_pin = dict(path=str(path.relative_to(ROOT)), sha256=sha(recipe))
        old_paths = legacy_rows[ident]['paths']
        assert old_paths['original']['sha256'] == original_sha
        assert old_paths['candidate']['sha256'] not in contract['restricted_hashes']
        canonical, compiler = frame.canonicalize(recipe.decode('utf-8'), source_id=ident,
                                                 paths=old_paths, root=ROOT)
        base = compiler['base']
        assert base in {'original', 'candidate'}
        base_bytes = verify(old_paths[base])
        rendered, application = edits.apply_recipe(base_bytes.decode('utf-8'), canonical,
                                                    source_id=ident, base=base)
        assert sha(rendered.encode('utf-8')) == output_pin['sha256']
        proof.update(recipe=recipe_pin, assigned_recipe_base=old_paths[base],
                     literal_output_sha256=output_pin['sha256'], compiler=compiler, application=application,
                     historical_recipe_bytes_or_delivery_time_proven=False)
    else:
        assert prior['decision'] == 'EDIT_TEXT' and entry['cells'][1] == 'REVISE_TEXT'
        name = declared_txt_basename(entry['cells'][3], ident, directory, {}, 'EDIT_TEXT')
        authored_pin = dict(path=str((directory / name).relative_to(ROOT)), sha256=output_pin['sha256'])
        verify(authored_pin)
        proof.update(authored_output=authored_pin,
                     explicitly_superseded_row_history=[item['raw'] for item in prior_entries if item is not entry],
                     explicit_root_amendment_not_last_row_guess=True)
    current = selected[ident]
    assert current['original']['sha256'] == original_sha
    after = bind(ident, current, original_sha)
    assert role != after['role']
    if ident in accept_resolutions:
        proof['current_historical_accept_resolution'] = accept_resolutions[ident]
    rows.append(dict(id=ident, status='EXACT_PRIOR_AND_CURRENT_REVIEW_OUTPUT_CHAIN_VERIFIED',
                     original=source['original'], candidate=source['candidate'],
                     prior=dict(role=role, review=review_pin, exact_review_row=entry['raw'], output=output_pin,
                                exact_prior_output_proof=proof), current=after, distinct_named_roles=True,
                     automatic_flag_waiver=False, independent_semantic_pass_granted=False,
                     historical_input_delivery_proven=False))
combined = sorted(known | {row['id'] for row in rows})
assert len(rows) == 4 and len(combined) == 468
for path in (Path(__file__).resolve(), AUDIT / 'HISTORICAL_REVIEW_BINDING_FOUR_CASES_IMPACT_V1.md',
             AUDIT / 'exact_manifest_review_row_binding_v1.py',
             ROOT / 'scripts/p106b_hold_resolution_author_output_bindings_v1.py',
             ROOT / 'scripts/p106b_hold_resolution_recipe_frame_v3.py',
             ROOT / 'scripts/p106b_hold_resolution_text_edits_v2.py'):
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest().upper()
result = dict(status='FOUR_EXACT_HISTORICAL_REVIEW_BINDINGS_NOT_NEW_SEMANTIC_PASSES',
              rows=rows, prior_linked_record_scopes=464, additional_exact_chain_links=4,
              combined_record_scopes=combined, linked_flag_sources_in_these_scopes=468,
              total_ordered_flags=585, not_linked_in_these_scopes=117,
              pure_output_positive_probes=2, pure_output_and_identity_negative_probes=rejected,
              prior_failures_preserved=True, production_output_binder_changed=False,
              current_hashes_retrofilled_as_historical=False, source_data_changed=False,
              source_semantic_rereads=0, root_or_cache_adoptions=0, automatic_flag_waivers=0,
              whole_goal_complete=False, training_authorized=False, input_pins=pins)
with (AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V4.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], additional_links=4, linked=468, unlinked=117,
                     positive_probes=2, negative_probes=rejected, root_adopted=0), ensure_ascii=False))
