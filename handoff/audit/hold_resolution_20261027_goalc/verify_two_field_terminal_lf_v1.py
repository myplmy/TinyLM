"""Check exact two reviewed text edits, including explicitly retained final LF."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}


def read(path):
    payload = path.read_bytes()
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest().upper()
    return payload


contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract = json.loads(read(contract_path))
assert pins[str(contract_path.relative_to(ROOT))] == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
manifest = json.loads(read(BASE / 'remaining_field_title_page_001_counter_v1/manifest.json'))
directory = BASE / 'agents/context_latin/remaining_field_title_page_001_counter_v1'
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser
resolve, parse, _ = load_parser()
review_path = directory / 'review_008.md'
reviews = {resolve(row['cells'][0]): row for row in parse(read(review_path))}
assert len(reviews) == 5
records = []
for number, alias, empty_block, expected_sha in [
    ('5171', '호키', '문화\n\n', 'D9E007DDA58F096014FCC30FD9EBF8BA809EB3621BB32A403121F7C490B2FA23'),
    ('5181', '엔랴쿠', '문화\n\n탄생\n\n', '5527041970BDCEDBA2D077BD9E3548DAC38CF5FE6292EAF56445734225FCCC5E'),
]:
    ident = 'expanded_train:' + number
    source = next(row for row in manifest['rows'] if row['id'] == ident)
    assert ident not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    original = read(ROOT / source['original']['path'])
    assert hashlib.sha256(original).hexdigest().upper() == source['original']['sha256']
    candidate = read(ROOT / source['candidate']['path'])
    assert candidate == original
    path = directory / f'reviewed_expanded_train_{number}_v1.txt'
    body = read(path)
    assert hashlib.sha256(body).hexdigest().upper() == expected_sha
    old_text = original.decode('utf-8')
    text = body.decode('utf-8')
    assert original.startswith(b'\n\n') and not original.endswith(b'\n')
    assert old_text.count(alias + '()') == old_text.count(empty_block) == 1
    expected = old_text[1:].replace(alias + '()', alias, 1).replace(empty_block, '', 1) + '\n'
    assert expected.encode('utf-8') == body
    assert body.endswith(original[-12:] + b'\n')
    row = reviews[ident]
    assert row['cells'][3].strip('`') in {str(path), str(path.relative_to(ROOT)), path.name}
    assert '끝 LF' in row['raw']
    hold_path = directory / f'hold_expanded_train_{number}_v1.md'
    note = read(hold_path).decode('utf-8')
    assert alias + '()' in note and hold_path.name in row['raw']
    records.append(dict(id=ident, original=source['original'],
                        body=dict(path=str(path.relative_to(ROOT)), sha256=expected_sha),
                        sidecar=dict(path=str(hold_path.relative_to(ROOT)),
                                     sha256=pins[str(hold_path.relative_to(ROOT))]),
                        empty_alias_wrapper_removed=1, leading_blank_lf_removed=1,
                        empty_section_block=empty_block, terminal_lf_added=1,
                        utf8_valid=True, complete_final_unicode_and_parenthesis_retained=True,
                        all_other_body_bytes_unchanged=True,
                        root_read_scope='Full original and new body, full diff, sidecar and EOF; source facts not independently reverified'))
read(Path(__file__).resolve())
result = dict(status='TWO_FIELD_EXACT_EDITS_AND_EXPLICIT_TERMINAL_LF_VERIFIED',
              records=records, review=dict(path=str(review_path.relative_to(ROOT)),
                                         sha256=pins[str(review_path.relative_to(ROOT))]),
              actual_full_read_output='855cd1', new_root_or_cache_adoptions=0,
              specific_followup_pending=0, input_pins=pins,
              whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'ROOT_TWO_FIELD_TERMINAL_LF_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], sources=2, specific_pending=0,
                     valid_utf8=2, explicit_added_terminal_lf=2, root_adopted=0)))
