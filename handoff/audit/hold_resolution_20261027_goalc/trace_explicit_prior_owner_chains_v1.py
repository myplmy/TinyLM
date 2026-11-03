"""Recover saved prior owners through exact pinned inputs; grant no semantic pass."""
from pathlib import Path
from collections import Counter
import ast
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0, str(AUDIT))
sys.path.insert(0, str(ROOT))
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser, FROZEN
from scripts.p106b_hold_resolution_author_output_bindings_v1 import declared_txt_basename

reused = AUDIT / 'audit_remaining_ordered_flag_provenance_v1.py'
names = {'sha', 'read', 'verify', 'role_from_review'}
definitions = [node for node in ast.parse(reused.read_text(encoding='utf-8')).body
               if isinstance(node, ast.FunctionDef) and node.name in names]
assert len(definitions) == 4 and all(not node.decorator_list for node in definitions)
pins = {}
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(reused), 'exec'), globals())
contract = read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
assert pins['handoff/audit/hold_resolution_20261027_goalc/GUARDED_SOURCE_METADATA_CONTRACT_V1.json'] == \
    'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
root = read(AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json')
assert pins['handoff/audit/hold_resolution_20261027_goalc/ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json'] == \
    '624AE91E66B4104F864E389B001A58E2C67C2D509D78F7E348DABC4FAD30A152'
old = read(AUDIT / 'ORDERED_FLAG_OLD_PATH_PROVENANCE_AUDIT_V2.json')
previous = read(AUDIT / 'RUNTIME_PRIOR_REVIEW_OUTPUT_CHAIN_V1.json')
known = set(previous['combined_record_scopes'])
assert len(known) == 390
selected = {row['id']: row['selected'] for row in root['rows']}
scopes = {'root_join_conflict_counter_v1': 63,
          'authored_postsignal_review_v1': 17, 'root10_quantity_recheck_v1': 1}
pending = [row for row in old['rows'] if row['id'] not in known and row['selected_cohort'] in scopes]
assert Counter(row['selected_cohort'] for row in pending) == Counter(scopes)
resolve, parse, parser_sha = load_parser()
pins[str(FROZEN.relative_to(ROOT))] = parser_sha
manifests = {}


def guard(ident, original_sha):
    if ident in contract['restricted_ids'] or original_sha in contract['restricted_hashes']:
        raise ValueError('RESTRICTED_METADATA_ONLY_NOT_OPENED')


def manifest(cohort):
    assert re.fullmatch(r'[A-Za-z0-9_]+', cohort)
    if cohort not in manifests:
        value = read(BASE / cohort / 'manifest.json')
        rows = {row['id']: row for row in value['rows']}
        assert len(rows) == len(value['rows'])
        manifests[cohort] = (value, rows)
    return manifests[cohort]


def assigned_role(value, ident):
    roles = [role for role, group in value['assignments'].items()
             if ident in (group['ids'] if isinstance(group, dict) else group)]
    assert len(roles) == 1, 'source has no unique exact role assignment'
    return roles[0]


def bind(ident, choice, original_sha):
    value, source_rows = manifest(choice['cohort'])
    source = source_rows[ident]
    assert source['original']['sha256'] == choice['original']['sha256'] == original_sha
    guard(ident, original_sha)
    role = role_from_review(choice['review'])
    assert assigned_role(value, ident) == role
    assert source.get('role', role) == choice.get('role', role) == role
    review = verify(choice['review'], archive=True)
    entry = exact_entry(review, ident, set(source_rows), resolve, parse)
    assert len(entry['cells']) == 5
    status = {'REVISE_TEXT': 'EDIT_TEXT', 'ACCEPT_CANDIDATE': 'ADOPT_CANDIDATE',
              'KEEP_SOURCE': 'KEEP_SOURCE'}[entry['cells'][1]]
    directory = BASE / 'agents' / role / choice['cohort']
    paths = {label: dict(source[label], path=str(ROOT / source[label]['path']))
             for label in ('original', 'candidate')}
    name = declared_txt_basename(entry['cells'][3], ident, directory, paths, status)
    output = ROOT / source['candidate']['path'] if status == 'ADOPT_CANDIDATE' else \
        ROOT / source['original']['path'] if status == 'KEEP_SOURCE' else directory / name
    output_pin = dict(path=str(output.relative_to(ROOT)), sha256=choice['clean_text_sha256'])
    verify(source['original'])
    verify(source['candidate'])
    verify(output_pin)
    verify(dict(path=choice['body'], sha256=choice['clean_text_sha256']))
    if choice.get('author_output'):
        assert choice['author_output']['path'] == output_pin['path']
        assert choice['author_output']['sha256'] == output_pin['sha256']
        verify(choice['author_output'])
    return dict(role=role, review=choice['review'], exact_review_row=entry['raw'],
                output=output_pin, declared_status=entry['cells'][1],
                source_manifest=dict(path=str((BASE / choice['cohort'] / 'manifest.json').relative_to(ROOT)),
                                     sha256=pins[str((BASE / choice['cohort'] / 'manifest.json').relative_to(ROOT))]))


integrity = None


def authored_prior(ident, source, value, original_sha):
    global integrity
    integrity_path = AUDIT / 'authored_body_integrity_v2.json'
    if integrity is None:
        integrity = read(integrity_path)
    assert value['pins'][str(integrity_path.relative_to(ROOT))] == pins[str(integrity_path.relative_to(ROOT))]
    matches = [row for row in integrity['records'] if row['id'] == ident and
               row.get('clean_text_sha256') == source['candidate']['sha256']]
    assert len(matches) == 1, 'prior authored body is not uniquely pinned'
    prior = matches[0]
    assert prior['original_text_sha256'] == original_sha
    guard(ident, original_sha)
    evidence = prior['evidence']
    review_pin = dict(path=evidence['review'], sha256=evidence['review_sha256'])
    role = role_from_review(review_pin)
    assert role == source['original_author']
    review = verify(review_pin)
    entry = exact_entry(review, ident, {row['id'] for row in integrity['records']}, resolve, parse)
    assert len(entry['cells']) == 5 and entry['cells'][1] == 'REVISE_TEXT', \
        'prior integrity evidence requires an explicit authored output'
    review_directory = (ROOT / review_pin['path']).parent
    name = declared_txt_basename(entry['cells'][3], ident, review_directory, {}, 'EDIT_TEXT')
    output_pin = dict(path=str((review_directory / name).relative_to(ROOT)),
                      sha256=source['candidate']['sha256'])
    original_pin = dict(path=prior['source'], sha256=original_sha)
    verify(original_pin)
    verify(output_pin)
    verify(dict(path=prior['body'], sha256=prior['clean_text_sha256']))
    return dict(role=role, review=review_pin, exact_review_row=entry['raw'], output=output_pin,
                original=original_pin, declared_status='REVISE_TEXT',
                pinned_integrity_record_not_new_semantic_pass=True)


# These pure probes must reject before any assigned review/body I/O.
for ident, original_sha in [(contract['restricted_ids'][0], '0' * 64),
                             ('expanded_train:10465', contract['restricted_hashes'][0])]:
    try:
        guard(ident, original_sha)
    except ValueError as error:
        assert str(error) == 'RESTRICTED_METADATA_ONLY_NOT_OPENED'
    else:
        raise AssertionError('dual identity pre-I/O guard failed')

rows = []
successful = set()
for old_row in sorted(pending, key=lambda row: row['id']):
    ident = old_row['id']
    item = dict(id=ident, cohort=old_row['selected_cohort'], automatic_flag_waiver=False,
                independent_semantic_pass_granted=False, historical_input_delivery_proven=False)
    try:
        current = selected[ident]
        assert current['cohort'] == old_row['selected_cohort']
        original_sha = old_row['original_text_sha256']
        guard(ident, original_sha)
        assert current['clean_text_sha256'] == old_row['current_body_sha256']
        value, source_rows = manifest(current['cohort'])
        source = source_rows[ident]
        assert source['original']['sha256'] == original_sha
        if current['cohort'] == 'root_join_conflict_counter_v1':
            proposals = [source.get('previous_root')] + source['new_proposals']
            candidates = [proposal for proposal in proposals if proposal and
                          proposal['clean_text_sha256'] == source['candidate']['sha256']]
            assert len(candidates) == 1, 'assigned candidate owner is ambiguous'
            before = bind(ident, candidates[0], original_sha)
            proof = 'FROZEN_PRIOR_ROOT_OR_NEW_PROPOSAL_EXACT_INPUT_MATCH'
        elif current['cohort'] == 'root10_quantity_recheck_v1':
            prior = source['prior_selection']
            assert prior['id'] == ident and prior['body']['sha256'] == source['candidate']['sha256']
            choice = dict(prior, body=prior['body']['path'], clean_text_sha256=prior['body']['sha256'])
            before = bind(ident, choice, original_sha)
            proof = 'EXACT_PRIOR_SELECTION_BODY_AND_REVIEW'
        else:
            before = authored_prior(ident, source, value, original_sha)
            proof = 'PINNED_AUTHORED_INTEGRITY_EXPLICIT_REVIEW_OUTPUT'
        after = bind(ident, current, original_sha)
        assert before['output']['sha256'] == source['candidate']['sha256']
        assert before['role'] != after['role'], 'current assigned reviewer is the input body author'
        item.update(status='EXACT_PRIOR_AND_CURRENT_REVIEW_OUTPUT_CHAIN_VERIFIED',
                    proof=proof, original=source['original'], candidate=source['candidate'],
                    prior=before, current=after, distinct_named_roles=True,
                    input_equals_current_body=source['candidate']['sha256'] == current['clean_text_sha256'])
        successful.add(ident)
    except (AssertionError, KeyError, OSError, ValueError) as error:
        item.update(status='EXISTING_CHAIN_REQUIRES_FURTHER_AUDIT', error=f'{type(error).__name__}: {error}')
    rows.append(item)

assert len(rows) == 81 and not (successful & known)
combined = sorted(known | successful)
for path in (reused, FROZEN, AUDIT / 'exact_manifest_review_row_binding_v1.py',
             ROOT / 'scripts/p106b_hold_resolution_author_output_bindings_v1.py',
             AUDIT / 'ORDERED_FLAG_PRIOR_OWNER_CHAIN_IMPACT_V1.md', Path(__file__).resolve()):
    pins[str(path.relative_to(ROOT))] = sha(path.read_bytes())
result = dict(status='EXPLICIT_PRIOR_OWNER_CHAINS_NOT_NEW_SEMANTIC_PASSES',
              rows=rows, attempted_sources=81, prior_linked_record_scopes=390,
              additional_exact_chain_links=len(successful), combined_record_scopes=combined,
              linked_flag_sources_in_these_scopes=len(combined), total_ordered_flags=585,
              not_linked_in_these_scopes=585-len(combined), counts=dict(Counter(row['status'] for row in rows)),
              pure_dual_identity_pre_io_rejection_probes=2,
              reused_function_definitions=sorted(names), reused_top_level_executed=False,
              input_pins=pins, automatic_flag_waivers=0, new_semantic_source_reads=0,
              protected_body_reads=0, root_or_cache_adoptions=0, whole_goal_complete=False,
              limits=['Saved roles, exact declared outputs and matching candidate bytes are connected.',
                      'No historical delivery, actual comprehension or semantic flag waiver is inferred.',
                      'Every unsuccessful binding is retained; no duplicate rereading is automatically scheduled.'])
target = AUDIT / 'EXPLICIT_PRIOR_OWNER_CHAINS_V1.json'
payload = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
assert len(payload) < 20_000_000
with target.open('xb') as stream:
    stream.write(payload)
print(json.dumps({key: result[key] for key in ('status', 'attempted_sources', 'additional_exact_chain_links',
                  'linked_flag_sources_in_these_scopes', 'not_linked_in_these_scopes', 'counts')}, ensure_ascii=False))
