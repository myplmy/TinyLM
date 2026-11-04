"""Verify two numeric-boundary edits and exact field-value recovery in prose."""
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


contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract = json.loads(read(contract_path))
assert pins[str(contract_path.relative_to(ROOT))] == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
manifest = json.loads(read(BASE / 'remaining_field_title_page_004_counter_v1/manifest.json'))
sources = {row['id']: row for row in manifest['rows']}
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser
resolve, parse, _ = load_parser()
records = []
for number, role, old_name, new_name, old_review_name, new_review_name, note_name, expected_sha in [
    ('29112', 'legacy_review', 'expanded_train_29112_revised_task001_v3.txt',
     'expanded_train_29112_root_total_followup_v1.txt', 'review_001.md', 'review_001_v2.md',
     'hold_29112_root_total_followup_v1.md', '3F7E0A49C35BB9617D05B11BF6916C72BFDEEB64449C58920E353DAAAF0DD11E'),
    ('33415', 'legacy_review', 'expanded_train_33415_revised_task004_v1.txt',
     'expanded_train_33415_root_footnote_followup_v1.txt', 'review_004.md', 'review_004_v2.md',
     'hold_33415_root_footnote_followup_v1.md', '154AE090F8D63A07A5E926FF00FA365B156FB6D806F8B26E68D1B808236A60D9'),
    ('47905', 'historical_review', 'expanded_train_47905_historical_review_20261104_v2.txt',
     'expanded_train_47905_historical_review_20261104_v4.txt', 'review_018_v2.md', 'review_018_v4.md',
     'hold_47905_korean_label_correction_20261104_v1.md', 'DEB40511D3B61D654FC67B4E4EC5ECD984DE7DA802638D061D3A7682C23C9C83'),
]:
    ident = 'expanded_train:' + number
    source = sources[ident]
    assert ident not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes']
    original = read(ROOT / source['original']['path'])
    assert hashlib.sha256(original).hexdigest().upper() == source['original']['sha256']
    directory = BASE / 'agents' / role / 'remaining_field_title_page_004_counter_v1'
    before = read(directory / old_name)
    path = directory / new_name
    after = read(path)
    assert hashlib.sha256(after).hexdigest().upper() == expected_sha
    after.decode('utf-8')
    note_path = directory / note_name
    note = read(note_path).decode('utf-8')
    detail = {}
    if number == '29112':
        removed = b' Total = $1431.5 per kW.'
        assert before.count(removed) == 1 and before.replace(removed, b'', 1) == after
        assert b'$1431.\n5 per kW' in original
        assert '$1431.' in note and '5 per kW' in note
        detail.update(exact_unsupported_total_removed=True, removed_bytes=len(removed),
                      original_decimal_join_not_assumed=True)
    elif number == '33415':
        old = b'mm. 8-12.7 In Schenkerian'
        new = b'mm. 8-12. In Schenkerian'
        assert before.count(old) == 1 and before.replace(old, new, 1) == after
        assert b'similar fashion.7 Here the melody' in original and b'mm. 8-12.' in original
        detail.update(one_digit_removed_from_range=True, marker_provenance_refers_to_original=True,
                      no_new_marker_assigned_to_any_other_body_sentence=True)
    else:
        anchor = b'Molecule: Si(C3(COOH)2)4(H2O)7.\n'
        addition = b'\nRuta:\n- atom: "( )"\n- num: 1\n- next: None\n- down: None\n'
        assert before.count(anchor) == 1 and before.replace(anchor, anchor + addition, 1) == after
        assert b'class Ruta: atom="( )" num=1 next=None down=NoneThe funktion' in original
        intermediate_path = directory / 'expanded_train_47905_historical_review_20261104_v3.txt'
        intermediate = read(intermediate_path)
        assert intermediate.replace('Ruta의 필드와 초기값:'.encode('utf-8'), b'Ruta:', 1) == after
        assert not re.search('[가-힣]', original.decode('utf-8'))
        assert not re.search('[가-힣]', after.decode('utf-8'))
        read(directory / 'hold_47905_flattened_code_and_missing_figure_20261104_v3.md')
        detail.update(exact_source_field_values_restored=4,
                      code_class_or_control_flow_reconstructed=False,
                      unintended_hangul_heading_removed=True,
                      old_code_guard_not_automatically_waived=True)
    old_review = {resolve(row['cells'][0]): row for row in parse(read(directory / old_review_name))}
    review_path = directory / new_review_name
    new_review = {resolve(row['cells'][0]): row for row in parse(read(review_path))}
    effective = dict(old_review, **new_review)
    assert len(old_review) == len(effective) == 5 and ident in new_review
    assert all(effective[key]['raw'] == old_review[key]['raw'] for key in old_review if key != ident)
    assert path.name in new_review[ident]['raw'] and note_path.name in new_review[ident]['raw']
    assert before.endswith(b'\n') == after.endswith(b'\n')
    records.append(dict(id=ident, original=source['original'],
                        before=dict(path=str((directory / old_name).relative_to(ROOT)), sha256=pins[str((directory / old_name).relative_to(ROOT))]),
                        body=dict(path=str(path.relative_to(ROOT)), sha256=expected_sha),
                        review=dict(path=str(review_path.relative_to(ROOT)), sha256=pins[str(review_path.relative_to(ROOT))]),
                        sidecar=dict(path=str(note_path.relative_to(ROOT)), sha256=pins[str(note_path.relative_to(ROOT))]),
                        unchanged_other_review_rows=4, unchanged_body_bytes_outside_requested_change=True,
                        eof_lf_state_unchanged=True, details=detail))
read(Path(__file__).resolve())
result = dict(status='THREE_BOUNDED_FIELD_REPAIRS_EXACT_BYTES_AND_REVIEW_ROWS_VERIFIED',
              rows=records, sources=3, root_authored_corpus_bodies=0,
              actual_root_full_47905_v3_body_diff_and_sidecar_read='82e919',
              actual_root_three_diffs_eof_and_sidecars_read='b709a3',
              actual_root_original_numeric_boundary_contexts='4de812',
              source_wide_fact_or_semantic_completion_claimed=False,
              remaining_41069_and_85646_followups_not_closed_here=True,
              root_or_cache_adoptions=0, input_pins=pins,
              whole_goal_complete=False, training_authorized=False)
with (AUDIT / 'ROOT_THREE_FIELD_NARROW_FOLLOWUPS_VERIFIED_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], verified_sources=3, unchanged_other_review_rows=12,
                     source_bodies_authored_by_root=0, root_adopted=0)))
