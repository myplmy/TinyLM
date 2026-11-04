"""Verify four exact body bridges left by the V3 numeric evidence audit."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import ast
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
A = Path(__file__).resolve().parent
pins = {}
helper = A / 'audit_field_numeric_v3_review_links_v1.py'
helper_raw = helper.read_bytes()
nodes = [node for node in ast.parse(helper_raw.decode()).body
         if isinstance(node, ast.FunctionDef) and node.name in {'read', 'flag_key'}]
assert len(nodes) == 2 and all(not node.decorator_list for node in nodes)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(helper), 'exec'), globals())
pins[str(helper.relative_to(ROOT))] = hashlib.sha256(helper_raw).hexdigest().upper()
guard = read(A / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json',
             'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF')
prior = read(A / 'FIELD_NUMERIC_V3_REVIEW_LINKS_V1.json')
proofs = read(A / 'FIELD_BOUND_NUMERIC_LOCAL_PROOFS_V1.json')
contexts = read(A / 'FIELD_NUMERIC_V1_CONTEXT_DISPOSITIONS_V1.json')
follow = read(A / 'ROOT_FOUR_NUMERIC_CONTEXT_FOLLOWUPS_VERIFIED_V1.json')
decimal = read(A / 'ROOT_50533_EXACT_DECIMAL_FOLLOWUP_VERIFIED_V1.json')
headers = read(A / 'ROOT_POST_HOLD_HEADERS_AND_APPLICATION_VERIFIED_V1.json')
batch016 = read(A / 'FIELD_NUMERIC_CONTEXT_BATCH016_BINDINGS_VERIFIED_V1.json')
assert batch016['flag_occurrences'] == 16 and batch016['partial_HOLD'] == 3
old = {row['id']: row for row in proofs['rows']}
manual = {row['id']: row for row in contexts['records']}
receipts = {row['id']: row for row in follow['records']}
receipts[decimal['id']] = decimal
receipts['expanded_train:69'] = next(row for row in headers['records'] if row['id'] == 'expanded_train:69')
assert {row['id'] for row in prior['pending']} == set(receipts) - {'expanded_train:79622', 'expanded_train:60001'}

def pinned_text(pin):
    raw = (ROOT / pin['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == pin['sha256']
    pins[pin['path']] = pin['sha256']
    return raw.decode('utf-8')

bridges = []
for row in prior['rows']:
    if not any(item['status'].startswith('UNLINKED') for item in row['targets']):
        continue
    identity = row['id']
    assert identity not in guard['restricted_ids']
    assert row['original']['sha256'] not in guard['restricted_hashes']
    source = old[identity]
    receipt = receipts[identity]
    assert source['original'] == row['original'] == receipt['original']
    before = pinned_text(source['body'])
    after = pinned_text(row['body'])
    expected = before
    if identity == 'expanded_train:69':
        assert row['body']['sha256'] == receipt['body']['sha256']
        for name in receipt['details']['header_names']:
            token = name + chr(10)
            assert expected.count(token) == 1
            expected = expected.replace(token, '', 1)
    else:
        assert source['body']['sha256'] == receipt['old_body']['sha256']
        assert row['body']['sha256'] == receipt['new_body']['sha256']
        for x, y in receipt['exact_edits']:
            assert expected.count(x) == 1
            expected = expected.replace(x, y, 1)
    assert expected == after
    blocks = difflib.SequenceMatcher(None, before, after, autojunk=False).get_matching_blocks()
    mapped = {}
    for proof in source['proofs']:
        flag = proof['flag']
        start, end = flag['body_span']
        assert before[start:end] == flag['body_token']
        for block in blocks:
            if block.a <= start and end <= block.a + block.size:
                new_start = block.b + start - block.a
                mapped[(new_start, new_start + end - start, flag['body_token'])] = proof
                break
    counts = Counter()
    for item in row['targets']:
        assert item['status'].startswith('UNLINKED')
        flag = item['flag']
        start, end = flag['body_span']
        assert after[start:end] == flag['body_token']
        key = (start, end, flag['body_token'])
        if identity == 'expanded_train:50533' and start == 1183:
            assert flag['body_token'] == '32.438191288' and end == 1195
            assert Decimal('32.4381') + Decimal('0.000091288') == Decimal(flag['body_token'])
            assert manual[identity]['special_repaired_tokens'] == [
                dict(old_span=[1183,1194], old_token='2.438191288',
                     new_token='32.438191288', reason='adjacent example and exact decimal equality')]
            item.update(status='EXACT_SUPPORTED_DECIMAL_REPAIR_BRIDGE',
                        disposition='SUPPORTED_TOKEN_REPAIR',
                        evidence=['ROOT_50533_EXACT_DECIMAL_FOLLOWUP_VERIFIED_V1.json'])
        elif identity == 'expanded_train:69' and key == (336, 337, '2'):
            original = pinned_text(row['original'])
            phrase = '아래 공식들은 배각의 공식에서 x를 2x로 두고 전개하여 풀면 얻을 수 있다.'
            assert original.count(phrase) == 1
            assert '네배각 공식은 배각 공식에서 x를 2x로 두고 전개하여 얻을 수 있다.' in after
            item.update(status='EXACT_ADDITIONAL_SOURCE_CONTEXT_ACTUALLY_READ',
                        disposition='CONTEXT_RETAINED',
                        evidence=[dict(actual_read='c8d34a',
                                       source_span=[original.index(phrase), original.index(phrase)+len(phrase)],
                                       reason='Named four-angle substitution x to 2x is explicit; no exponent or formula invented.')])
        else:
            assert key in mapped, (identity, key)
            proof = mapped[key]
            assert proof['status'] == 'MANUAL_CONTEXT_REQUIRED'
            assert manual[identity]['manual_dispositions'].get('CONTEXT_RETAINED', 0) >= 1
            assert not (identity == 'expanded_train:50533' and proof['flag']['body_token'] == '2.438191288')
            item.update(status='EXACT_REVIEWED_UNCHANGED_TARGET_THROUGH_NARROW_BODY_BRIDGE',
                        disposition='CONTEXT_RETAINED',
                        evidence=[manual[identity]['context_receipt']])
        counts[item['status']] += 1
    bridges.append(dict(id=identity, old_body=source['body'], new_body=row['body'],
                        full_expected_body_matches=True,
                        mapped_target_counts=dict(counts),
                        actual_prior_exact_diff_read='bbd3c5',
                        additional_69_header_only_diff_read='b6e35c',
                        current_72091_and_113011_context_read='c8d34a'))

dispositions = Counter()
statuses = Counter()
for row in prior['rows']:
    for item in row['targets']:
        assert not item['status'].startswith('UNLINKED')
        if 'disposition' not in item:
            if item['status'] == 'EXACT_V1_LOCAL_ATOM_PROOF_REUSED_NOT_MANUAL_CONTEXT':
                item['disposition'] = 'LOCAL_ATOM_PROOF_ONLY'
            elif row['id'] == 'expanded_train:149559' and item['flag']['body_token'] == '0':
                item['disposition'] = 'PARTIAL_HOLD_REMOVED_IN_BOUND_FOLLOWUP'
            else:
                item['disposition'] = 'CONTEXT_RETAINED'
        dispositions[item['disposition']] += 1
        statuses[item['status']] += 1
assert dict(dispositions) == dict(CONTEXT_RETAINED=425, LOCAL_ATOM_PROOF_ONLY=12,
                                SUPPORTED_TOKEN_REPAIR=1,
                                PARTIAL_HOLD_REMOVED_IN_BOUND_FOLLOWUP=3)
assert sum(dispositions.values()) == 441
result = dict(status='V3_441_FLAG_REVIEW_EVIDENCE_CONNECTED_NOT_CORPUS_ADMISSION',
              documents=87, targets=441, rows=prior['rows'], bridges=bridges,
              statuses=dict(statuses), dispositions=dict(dispositions), pending=[],
              prior_V1_unlinked_55_preserved=True,
              original_source_payloads_read_for_bridge=['expanded_train:69'],
              source_body_pair_guards_checked_before_payload=True, input_pins=pins,
              generic_guards_changed=False, diagnostic_flags_still_441_not_rewritten=True,
              numeric_signal_evidence_is_not_all_math_or_semantic_fact_verification=True,
              current_2882_field_reviews_not_all_covered_by_older_V3=True,
              root_or_cache_admissions=0, whole_goal_complete=False, training_authorized=False)
target = A / 'FIELD_NUMERIC_V3_REVIEW_LINKS_V2.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(path=str(target.relative_to(ROOT)), documents=87, targets=441,
                     dispositions=dict(dispositions), bridged_targets=55, pending=0,
                     sha256=hashlib.sha256(target.read_bytes()).hexdigest().upper(),
                     bytes=target.stat().st_size), ensure_ascii=False))
