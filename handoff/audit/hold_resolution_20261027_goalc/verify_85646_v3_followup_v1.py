"""Verify the bounded v1-v2-v3 repair after the actual full source read."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import exact_entry, load_parser

reused = AUDIT / 'verify_current_birth_followups_v1.py'
names = {'sha', 'read', 'pin', 'verify', 'replace_once'}
nodes = [node for node in ast.parse(reused.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name in names]
assert len(nodes) == len(names) and all(not node.decorator_list for node in nodes)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(reused), 'exec'), globals())
manifest_path = BASE / 'remaining_field_title_page_006_counter_v1/manifest.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
manifest, contract = read(manifest_path), read(contract_path)
sources = {row['id']: row for row in manifest['rows']}
ident = 'expanded_train:85646'
source = sources[ident]
assert ident not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes']
original = verify(source['original'])
assert source['original']['sha256'] == source['candidate']['sha256']
verify(source['candidate'])
directory = BASE / 'agents/context_hangul/remaining_field_title_page_006_counter_v1'
body_pins = [pin(directory / f'expanded_train_85646_task019_v{number}.txt') for number in (1, 2, 3)]
assert [item['sha256'] for item in body_pins] == [
    '490EFE1EAE61D6EC3D9A6AA677A7744D04ACA3268A0889B44BD3320140E89119',
    '27BCBEAABE44166680D9A6261A90A7CAF2C75009EF195D803B987A8C0D697831',
    'CC6F67969296B527E33F293A5F231209487031B65279418046D6D450BBF8712B']
v1, v2, v3 = [verify(item) for item in body_pins]
remove_lines = [
    'The discrete-time Fourier transform (DTFT) describes a window’s frequency-domain behavior.',
    'The zero-phase-window transform, also called the truncated cosine window, has the smallest moment of inertia over all windows.',
    'For example, to implement a zero-phase Hann window,' + chr(10) +
    '- Start with a rectangular window.' + chr(10) +
    '- Take the DFT of the window.' + chr(10) +
    '- Convolve the DFT data with the 3-point smoother',
    'This family configures Blackman-Harris windows to use all degrees of freedom to maximize roll-off rate.',
    "Here M is the desired window length, and alpha is half of the window's time-bandwidth product in ``cycles''. Alternatively, alpha can be interpreted as the highest bin number inside the main lobe of the window transform when the DFT length is equal to the window length. (See the next section on the Kaiser window for more on this point.)",
    'We can formulate an LP problem by adding a vector of optimization parameters which bound derivatives:',
]
expected = v1
for line in remove_lines:
    expected = replace_once(expected, line + chr(10), '')
old = 'In Matlab, the function chebwin(M,ripple) computes a length-M Dolph-Chebyshev window with a side-lobe level set by the ripple parameter. For example,'
new = 'In Matlab, the function chebwin(M,ripple) computes a length-M Dolph-Chebyshev window having a side-lobe level ripple dB below that of the main-lobe peak. For example,'
expected = replace_once(expected, old, new)
assert expected == v2, 'unreviewed v2 bytes beyond seven semantic repair units'
assert replace_once(v2, 'computes a length-M Dolph-Chebyshev window', 'computes a Dolph-Chebyshev window') == v3
assert len(original) == 52391 and len(v3) == 31235
assert 'ripple dB below that of the main-lobe peak' in original and 'ripple dB below that of the main-lobe peak' in v3
assert 'w = chebwin(31,60);' in original and 'w = chebwin(31,60);' in v3
assert 'w = dpss(M,alpha,1); % discrete prolate spheroidal sequence' in v3
assert 'Here M is the desired window length, and alpha' not in v3
sidecar_path = directory / 'hold_85646_task019_v3.md'
sidecar = sidecar_path.read_text(encoding='utf-8')
assert '이전 초안 표현' in sidecar and '원문 직접 인용이 아니다' in sidecar
quotes = ['- Take an -point DFT',
          '- Convolve the DFT data with the 3-point smoother',
          'where is a nonnegative integer.',
          'Thus, windows parametrize -term Blackman-Harris windows (for ) which are configured to use all degrees-of-freedom to maximize roll-off rate.',
          'In Matlab, the function chebwin(M,ripple) computes a length Dolph-Chebyshev window having a side-lobe level ripple dB below that of the main-lobe peak. For example,']
assert all(quote in original and quote in sidecar for quote in quotes)
resolve, parse, parser_sha = load_parser()
old_review = directory / 'review_019_v2.md'
new_review = directory / 'review_019_v4.md'
old_rows = {resolve(entry['cells'][0]): entry['raw'] for entry in parse(old_review.read_bytes())}
new_rows = {resolve(entry['cells'][0]): entry['raw'] for entry in parse(new_review.read_bytes())}
assert set(old_rows) == set(new_rows) and len(new_rows) == 5
assert {key: row for key, row in old_rows.items() if key != ident} == {key: row for key, row in new_rows.items() if key != ident}
entry = exact_entry(new_review.read_bytes(), ident, set(sources), resolve, parse)
assert entry['cells'][1] == 'REVISE_TEXT' and entry['cells'][3] == 'expanded_train_85646_task019_v3.txt'
prior = read(AUDIT / 'EIGHT_MORE_FOLLOWUPS_BYTE_VERIFIED_V1.json')
known = set(prior['previous_explicit_followup_ids']) | {row['id'] for row in prior['rows']}
assert len(known) == 21 and ident not in known
result = dict(status='FULL_READ_SOURCE_AND_EIGHT_BOUNDED_DRAFT_REPAIRS_VERIFIED_NOT_ADOPTED',
              id=ident, original=source['original'], candidate=source['candidate'],
              prior_v1_negative=pin(AUDIT / 'ROOT_85646_V1_NONADMISSION_V1.json'),
              preserved_body_versions=body_pins, selected_body=body_pins[2],
              review=pin(new_review), exact_review_row=entry['raw'], sidecar=pin(sidecar_path),
              v1_to_v2_semantic_edit_units=7,
              v1_to_v2_line_hunks=len(list(difflib.SequenceMatcher(None, v1.splitlines(True), v2.splitlines(True)).get_grouped_opcodes(3))),
              v2_to_v3_exact_edit_units=1, unchanged_bytes_outside_these_repairs_verified=True,
              actual_source_quote_fragments_verified=quotes, remaining_four_review_rows_unchanged=True,
              root_read_scope='Original 52391 characters and v1 32157 characters in full; all v1-v2 and v2-v3 changes/context/EOF; sidecar-v1/v2 full and all v3 changes; no repeated full-v3-read claim.',
              root_read_chunks=['408eaf', '9b0ada', 'cc43ed', 'f6dec4', '8d6d17', 'ec2957', 'e9834b'],
              combined_specific_followups=22, known_pending_in_this_case=0,
              limits=['This closes the named followup, not mathematical truth, code execution, or all new bodies.',
                      'The old v1 rejection is preserved; field006 snapshot v5 is an earlier nonadmitted version.',
                      'New roster selection and cache validation remain separate.'],
              input_pins=[pin(path) for path in (manifest_path, contract_path, reused, old_review, Path(__file__).resolve())],
              reused_parser_sha256=parser_sha, root_authored_corpus_bodies=0,
              root_or_cache_adoptions=0, protected_body_reads=0, code_or_model_execution=0,
              goal_complete=False, training_authorized=False)
target = AUDIT / 'ROOT_85646_V3_FOLLOWUP_VERIFIED_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], combined_specific_followups=22,
                     known_pending_in_this_case=0, root_or_cache_adoptions=0), ensure_ascii=False))
