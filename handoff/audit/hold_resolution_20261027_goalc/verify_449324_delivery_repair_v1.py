"""Verify the actual missing-input negative and the author's bounded repair."""
from pathlib import Path
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser, exact_entry

reused = AUDIT / 'verify_current_birth_followups_v1.py'
names = {'sha', 'read', 'pin', 'verify', 'replace_once'}
tree = ast.parse(reused.read_text(encoding='utf-8'))
definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
assert len(definitions) == len(names) and all(not node.decorator_list for node in definitions)
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(reused), 'exec'), globals())

manifest_path = BASE / 'birth_root11_independent_v1/manifest.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
manifest, contract = read(manifest_path), read(contract_path)
sources = {row['id']: row for row in manifest['rows']}
ident = 'expanded_train:449324'
source = sources[ident]
assert source['role'] == 'context_controls'
assert ident not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes']
original, candidate = verify(source['original']), verify(source['candidate'])
assert len(original) == 393 and '몰년 미상' in original and '몰년 미상' not in candidate
assert all(value not in original for value in ('1946년', '1954년', '8월 25일', '음반'))
negative_path = BASE / 'birth_root11_input_delivery_gated_v1/v11/complete.json'
positive_path = BASE / 'birth_root11_input_delivery_gated_v1/v12/complete.json'
negative, positive = read(negative_path), read(positive_path)
failure = next(row for row in negative['failures'] if row['id'] == ident)
assert failure['delivery']['missing_packets'] == [1] and failure['delivery']['late_packets'] == []
assert failure['review']['sha256'] == 'F8E3EACD664D09FB4845D1B7AFAD35771D085A2DB58A9B89670F5AD8B91C4ED7'
assert not positive['failures'] and positive['raw_errors'] == 0


def source_row(view):
    found = []
    for shard in view['shards']:
        data = (ROOT / shard['path']).read_bytes()
        assert sha(data) == shard['sha256']
        found += [row for row in json.loads(data) if row['id'] == ident]
    assert len(found) == 1
    return found[0]


before, after = source_row(negative), source_row(positive)
assert before['status'] == 'BLOCKED_BY_PROSPECTIVE_INPUT_DELIVERY_GUARD'
assert not ({'body', 'clean_text_sha256', 'author_output', 'body_references'} & set(before))
assert after['input_delivery']['status'] == 'INPUT_DELIVERED_BEFORE_REVIEW'
assert after['review']['path'].endswith('/review_162_v3.md')
assert Path(after['author_output']['path']).name == 'expanded_train_449324_reviewed_v2.txt'
selected_pin = dict(path=after['body'], sha256=after['clean_text_sha256'])
selected = verify(selected_pin)
expected = replace_once(candidate, '1909년 ~ 1982년 8월 31일', '1909년 출생, 8월 31일 사망')
expected = expected.rstrip(chr(10)) + chr(10)
assert selected == expected, 'change outside the assigned-candidate date-role edit and final LF'
from_original = replace_once(original, '각주 ' + chr(10), '')
from_original = replace_once(from_original, '몰년 미상' + chr(10), '')
from_original = replace_once(from_original, '1909년 ~ 1982년 8월 31일', '1909년 출생, 8월 31일 사망')
assert from_original.rstrip(chr(10)) + chr(10) == selected
directory = BASE / 'agents/context_controls/birth_root11_independent_v1'
old_review = directory / 'review_162.md'
new_review = directory / 'review_162_v3.md'
assert sha(old_review.read_bytes()) == failure['review']['sha256']
assert sha(new_review.read_bytes()) == after['review']['sha256']
resolve, parse, _ = load_parser()
old_entry = exact_entry(old_review.read_bytes(), ident, set(sources), resolve, parse)
assert all(value in old_entry['raw'] for value in ('1946년', '1954년', '8월 25일', '음반'))
old_other = {resolve(row['cells'][0]): row['raw'] for row in parse(old_review.read_bytes())
             if resolve(row['cells'][0]) != ident}
new_other = {resolve(row['cells'][0]): row['raw'] for row in parse(new_review.read_bytes())
             if resolve(row['cells'][0]) != ident}
assert old_other == new_other and len(old_other) == 4
sidecar = directory / 'hold_449324_v2.md'
note = directory / 'note_449324_delivery_recheck_v2.md'
assert all(value in sidecar.read_text() for value in ('1982년', '몰년 미상', '8월 31일'))
paths = [manifest_path, contract_path, negative_path, positive_path, old_review, new_review, sidecar,
         note, reused, Path(__file__).resolve()]
result = dict(status='ONE_ACTUAL_MISSING_DELIVERY_AND_WRONG_REVIEW_REPAIRED_WITH_BOUNDED_BYTES',
              id=ident, original=source['original'], candidate=source['candidate'],
              rejected_previous_review=failure['review'], previous_exact_review_row=old_entry['raw'],
              negative_guard_row=before, new_review=after['review'], selected_body=selected_pin,
              sidecar=pin(sidecar), incident_note=pin(note),
              prior_review_reason_actually_disagreed_with_original=True,
              unknown_earlier_cause_not_inferred=True, old_false_review_preserved=True,
              actual_one_packet_reread_without_probe=True,
              new_input_delivery_precondition=after['input_delivery'],
              other_four_review_rows_unchanged=True,
              unchanged_assigned_candidate_bytes_outside_one_date_role_edit_and_final_LF=True,
              original_bytes_outside_two_field_edits_empty_heading_and_final_LF_verified=True,
              root_actual_read_scope='원문393자 전체, 후보/선택전문, 모든차이/EOF, sidecar/이력전문과 구/신리뷰행',
              root_read_chunks=['1b7281', 'b6165d', '0b06e2', '510fba'],
              root_or_cache_adoptions=0, protected_body_reads=0, historical_logs_rewritten=False,
              generator_negatives=[dict(tool_chunk='79021f', error='missing hashlib import during initial reuse; corrected before receipt'),
                                   dict(tool_chunk='3226fc', error='assertion rejected an assumption from the same ID in the older remaining_birth_full cohort; current manifest candidate has no unknown-death category')],
              root_stage_correction='Chunk ac75c9 displayed the older remaining_birth_full candidate. It is not the current assigned candidate; only the exact current manifest pins in 510fba are used here.',
              whole_corpus_semantic_pass=False, goal_complete=False, training_authorized=False,
              input_pins=[pin(path) for path in paths])
target = AUDIT / 'DELIVERY_MISSING_449324_REPAIR_VERIFIED_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], known_pending_in_this_case=0,
                     other_rows_unchanged=4, root_or_cache_adoptions=0), ensure_ascii=False))
