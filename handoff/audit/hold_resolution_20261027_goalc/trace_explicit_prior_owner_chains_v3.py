"""Replay saved literal recipes and bind explicit Markdown output links."""
from pathlib import Path
import ast
import re

AUDIT = Path(__file__).resolve().parent
SOURCE = AUDIT / 'trace_explicit_prior_owner_chains_v1.py'
NORMALIZER_SOURCE = AUDIT / 'trace_explicit_prior_owner_chains_v2.py'
definition = [node for node in ast.parse(NORMALIZER_SOURCE.read_text(encoding='utf-8')).body
              if isinstance(node, ast.FunctionDef) and node.name == 'normalized_entry']
assert len(definition) == 1
exec(compile(ast.Module(body=definition, type_ignores=[]), str(NORMALIZER_SOURCE), 'exec'), globals())
normalize_v2 = normalized_entry


def normalized_entry(entry):
    header = entry.get('header')
    if header:
        entry = dict(entry, header=['출력' if label in {'출력 TXT 전체 경로', '실제 새 출력 파일', '실제 출력 연결'}
                                   else label for label in header])
    return normalize_v2(entry)


def link_targets(cell):
    # Preserve the one explicit Markdown target instead of counting label twice.
    return re.sub(r'\[([^\]\n]+)\]\(([^()\s]+)\)', lambda match: match[2], cell)


def declared_txt_basename(cell, source_id, directory, paths, status):
    matches = re.findall(r'/[^\s`|()<>;,]+[.]txt|(?<![A-Za-z0-9_./-])[A-Za-z0-9_.-]+[.]txt', link_targets(cell))
    if len(matches) != 1:
        raise ValueError('MISSING_OR_MULTIPLE_EXPLICIT_TXT_BODY_TOKENS')
    return original_declared_txt_basename(matches[0], source_id, directory, paths, status)


def authored_prior(ident, source, value, original_sha):
    global integrity
    integrity_path = AUDIT / 'authored_body_integrity_v2.json'
    if integrity is None:
        integrity = read(integrity_path)
    assert value['pins'][str(integrity_path.relative_to(ROOT))] == pins[str(integrity_path.relative_to(ROOT))]
    matches = [row for row in integrity['records'] if row['id'] == ident and
               row.get('clean_text_sha256') == source['candidate']['sha256']]
    assert len(matches) == 1, 'prior body is not uniquely pinned'
    prior = matches[0]
    assert prior['original_text_sha256'] == original_sha
    guard(ident, original_sha)
    evidence = prior['evidence']
    review_pin = dict(path=evidence['review'], sha256=evidence['review_sha256'])
    role = role_from_review(review_pin)
    assert role == source['original_author']
    entry = normalized_entry(exact_entry(verify(review_pin), ident,
                             {row['id'] for row in integrity['records']}, resolve, parse))
    directory = (ROOT / review_pin['path']).parent
    original_pin = dict(path=prior['source'], sha256=original_sha)
    original_bytes = verify(original_pin)
    output_pin = dict(path=prior['body'], sha256=source['candidate']['sha256'])
    proof = {}
    status = entry['cells'][1]
    if status == 'REVISE_TEXT':
        name = declared_txt_basename(entry['cells'][3], ident, directory, {}, 'EDIT_TEXT')
        authored = dict(path=str((directory / name).relative_to(ROOT)), sha256=output_pin['sha256'])
        verify(authored)
        proof['authored_output'] = authored
    elif status == 'KEEP_SOURCE':
        assert output_pin['sha256'] == original_sha
        assert prior['decision'] == 'KEEP_SOURCE'
        proof['exact_original_acceptance_no_authored_file'] = True
    elif status == 'EDIT_RECIPE':
        from scripts import p106b_hold_resolution_recipe_frame_v3 as frame
        from scripts import p106b_hold_resolution_text_edits_v2 as edits
        references = re.findall(r'(?<![A-Za-z0-9_./-])' + re.escape(ident.replace(':', '_')) +
                      r'(?:_v[0-9]+)?[._]edits(?:_v[0-9]+)?[.]md', link_targets(entry['cells'][3]))
        assert len(references) == 1, 'saved review has no unique exact-source recipe'
        path = directory / references[0]
        assert not path.is_symlink() and path.resolve().is_relative_to(BASE)
        recipe = path.read_bytes()
        assert 0 < len(recipe) < 20_000_000
        recipe_pin = dict(path=str(path.relative_to(ROOT)), sha256=sha(recipe))
        canonical, compiler = frame.canonicalize(recipe.decode('utf-8'), source_id=ident,
                          paths={'original': original_pin, 'candidate': source['candidate']}, root=ROOT)
        assert compiler['base'] == 'original', 'prior recipe base not recovered by this audit'
        rendered, application = edits.apply_recipe(original_bytes.decode('utf-8'), canonical,
                                                  source_id=ident, base='original')
        assert sha(rendered.encode('utf-8')) == output_pin['sha256']
        proof.update(recipe=recipe_pin, literal_application_output_sha256=output_pin['sha256'],
                     compiler=compiler, application=application,
                     historical_recipe_bytes_or_delivery_time_proven=False)
    else:
        raise ValueError('prior saved action has no exact supported body/recipe binding: ' + status)
    verify(output_pin)
    verify(source['candidate'])
    return dict(role=role, review=review_pin, exact_review_row=entry['raw'], output=output_pin,
                original=original_pin, declared_status=status, exact_prior_output_proof=proof,
                pinned_integrity_record_not_new_semantic_pass=True)


code = SOURCE.read_text(encoding='utf-8')
replacements = [
    ('import declared_txt_basename', 'import declared_txt_basename as original_declared_txt_basename'),
    ("previous = read(AUDIT / 'RUNTIME_PRIOR_REVIEW_OUTPUT_CHAIN_V1.json')",
     "previous = read(AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V2.json')"),
    ('assert len(known) == 390', 'assert len(known) == 456'),
    ("scopes = {'root_join_conflict_counter_v1': 63,\n          'authored_postsignal_review_v1': 17, 'root10_quantity_recheck_v1': 1}",
     "scopes = {'root_join_conflict_counter_v1': 3, 'authored_postsignal_review_v1': 12}"),
    ('resolve, parse, parser_sha = load_parser()',
     'resolve, parse_original, parser_sha = load_parser()\nparse = lambda payload: parse_original(payload, allow_sections=True)'),
    ("entry = exact_entry(review, ident, set(source_rows), resolve, parse)",
     "entry = normalized_entry(exact_entry(review, ident, set(source_rows), resolve, parse))"),
    ('assert len(rows) == 81', 'assert len(rows) == 15'),
    ('attempted_sources=81, prior_linked_record_scopes=390', 'attempted_sources=15, prior_linked_record_scopes=456'),
    ("target = AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V1.json'", "target = AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V3.json'"),
    ("pins[str(path.relative_to(ROOT))] = sha(path.read_bytes())\nresult = dict(",
     "pins[str(path.relative_to(ROOT))] = sha(path.read_bytes())\npins[str(SOURCE.relative_to(ROOT))] = sha(SOURCE.read_bytes())\npins[str(NORMALIZER_SOURCE.relative_to(ROOT))] = sha(NORMALIZER_SOURCE.read_bytes())\nfor name in ['p106b_hold_resolution_recipe_frame_v1.py','p106b_hold_resolution_recipe_frame_v2.py','p106b_hold_resolution_recipe_frame_v3.py','p106b_hold_resolution_text_edits.py','p106b_hold_resolution_text_edits_v2.py']:\n    path = ROOT / 'scripts' / name\n    pins[str(path.relative_to(ROOT))] = sha(path.read_bytes())\nresult = dict("),
]
for before, after in replacements:
    assert code.count(before) == 1, 'frozen v1 shape changed'
    code = code.replace(before, after)
tree = ast.parse(code, filename=str(SOURCE))
prior_functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'authored_prior']
assert len(prior_functions) == 1
tree.body = [node for node in tree.body if node is not prior_functions[0]]
ast.fix_missing_locations(tree)
exec(compile(tree, str(SOURCE), 'exec'), globals())
