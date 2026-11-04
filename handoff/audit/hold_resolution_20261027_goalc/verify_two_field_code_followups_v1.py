"""Verify two authored followups without reopening previously closed edit scopes."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}


def read(path):
    payload = path.read_bytes()
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest().upper()
    return payload


guard_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
guard = json.loads(read(guard_path))
assert pins[str(guard_path.relative_to(ROOT))] == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser
resolve, parse, _ = load_parser()
records = []
for page, number, role, old_name, new_name, old_review_name, new_review_name, note_name, expected_sha in [
    (4, '41069', 'legacy_review', 'expanded_train_41069_revised_task013_v3.txt',
     'expanded_train_41069_revised_task013_v4.txt', 'review_013_v3.md', 'review_013_v4.md',
     'hold_41069_task013_v4_addendum.md', 'CFA3A9852D6676732BFAC1CC52767618B875D7DDDAEF95F8DF574FE1B3C64FB0'),
    (6, '85646', 'context_hangul', 'expanded_train_85646_task019_v3.txt',
     'expanded_train_85646_task019_v4.txt', 'review_019_v4.md', 'review_019_v5.md',
     'hold_85646_task019_v4.md', '13236873B58BD318C7F70D53DB599311A40B91B05DA21765BB670B8B1CD1D580'),
]:
    ident = 'expanded_train:' + number
    manifest_path = BASE / f'remaining_field_title_page_{page:03}_counter_v1/manifest.json'
    source = next(row for row in json.loads(read(manifest_path))['rows'] if row['id'] == ident)
    assert ident not in guard['restricted_ids']
    assert source['original']['sha256'] not in guard['restricted_hashes']
    original = read(ROOT / source['original']['path'])
    assert hashlib.sha256(original).hexdigest().upper() == source['original']['sha256']
    directory = BASE / 'agents' / role / f'remaining_field_title_page_{page:03}_counter_v1'
    before = read(directory / old_name)
    body_path = directory / new_name
    after = read(body_path)
    assert hashlib.sha256(after).hexdigest().upper() == expected_sha
    after.decode('utf-8')
    note_path = directory / note_name
    note = read(note_path).decode('utf-8')
    if number == '41069':
        assert before.count(b'left plot, ') == before.count(b'right plot, ') == 1
        assert before.replace(b'left plot, ', b'', 1).replace(b'right plot, ', b'', 1) == after
        actual_literals = [
            b'ID <- 1:200', b'values <- rnorm(200, mean=65, sd=15)',
            b'df <- data.frame(ID, values)',
            b'ggplot(df, aes(values)) + geom_freqpoly()',
            b'ggplot(df, aes(values)) + geom_freqpoly(bins = 60, size = 1.5, color = "darkblue", linetype = "dotted")',
        ]
        assert all(value in original and value in before and value in after for value in actual_literals)
        assert all(value in after for value in (b'bins = 30', b'bins = 60', b'binwidth = 10'))
        assert not re.search('[가-힣]', after.decode('utf-8'))
        assert 'hold_41069_task013_v3.md' in note
        read(directory / 'hold_41069_task013_v3.md')
        detail = dict(only_two_missing_figure_position_phrases_removed=True,
                      preserved_source_assignments=3, preserved_complete_source_plot_calls=2,
                      source_parameter_values_preserved=True,
                      prior_histogram_frequency_polygon_correction_unchanged=True,
                      missing_code_or_graphic_results_reconstructed=False)
    else:
        removed = b'The use of M-1 is necessary to include zeros at both endpoints.'
        assert before.count(removed) == 1 and before.replace(removed, b'', 1) == after
        assert b'The use of is necessary to include zeros at both endpoints.' in original
        assert b'w = .5*(1 - cos(2*pi*(0:M-1)\'/(M-1)));' in after
        assert b'The Matlab hann function is a special case' in after
        assert 'hold_85646_task019_v3.md' in note and '이전 v3 표현' in note
        previous_receipt = json.loads(read(AUDIT / 'ROOT_85646_V3_FOLLOWUP_VERIFIED_V1.json'))
        assert not previous_receipt.get('goal_complete', False)
        detail = dict(only_unsupported_operand_sentence_removed=True, removed_bytes=len(removed),
                      original_gap_not_filled_from_adjacent_code=True,
                      actual_matlab_code_and_next_sentence_preserved=True,
                      earlier_eight_repairs_and_twenty_two_followups_not_reopened=True)
    old_review = {resolve(row['cells'][0]): row for row in parse(read(directory / old_review_name))}
    new_review_path = directory / new_review_name
    amendment = {resolve(row['cells'][0]): row for row in parse(read(new_review_path))}
    effective = dict(old_review, **amendment)
    assert len(old_review) == len(effective) == 5 and set(amendment) == {ident}
    assert all(effective[key]['raw'] == old_review[key]['raw'] for key in old_review if key != ident)
    assert body_path.name in amendment[ident]['raw'] and note_path.name in amendment[ident]['raw']
    assert before.endswith(b'\n') == after.endswith(b'\n')
    records.append(dict(id=ident, original=source['original'],
                        body=dict(path=str(body_path.relative_to(ROOT)), sha256=expected_sha),
                        review=dict(path=str(new_review_path.relative_to(ROOT)), sha256=pins[str(new_review_path.relative_to(ROOT))]),
                        sidecar=dict(path=str(note_path.relative_to(ROOT)), sha256=pins[str(note_path.relative_to(ROOT))]),
                        unchanged_other_review_rows=4,
                        unchanged_bytes_outside_requested_changes=True,
                        eof_lf_state_unchanged=True, details=detail))
read(Path(__file__).resolve())
result = dict(status='TWO_AUTHORED_FIELD_FOLLOWUPS_EXACT_BYTES_AND_REVIEW_AMENDMENTS_VERIFIED',
              records=records, verified_sources=2, unchanged_other_review_rows=8,
              actual_root_new_body_diff_sidecar_and_eof_read='b10467',
              actual_root_prior_five_row_review_read='6443c1',
              generic_code_guard_automatically_waived=False,
              source_wide_semantic_or_fact_verification_claimed=False,
              root_authored_corpus_bodies=0, root_or_cache_adoptions=0,
              input_pins=pins, whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'ROOT_TWO_FIELD_CODE_FOLLOWUPS_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({key: result[key] for key in ('status', 'verified_sources', 'unchanged_other_review_rows', 'root_or_cache_adoptions')}))
