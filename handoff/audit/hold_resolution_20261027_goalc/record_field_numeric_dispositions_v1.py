"""Record source-bound numeric review outcomes without changing any guard."""
from collections import Counter
from pathlib import Path
import hashlib
import json

A = Path(__file__).resolve().parent
ROOT = A.parents[2]
B = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}

def load(path):
    path = Path(path)
    raw = path.read_bytes()
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest().upper()
    return json.loads(raw)

guard_path = A / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
guard = load(guard_path)
assert pins[str(guard_path.relative_to(ROOT))] == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
proof = load(A / 'FIELD_BOUND_NUMERIC_LOCAL_PROOFS_V1.json')
rootrefs = {}
names = ['FIELD_NUMERIC_FIVE_CONTEXT_ADJUDICATIONS_V1.json'] + [
    f'FIELD_NUMERIC_CONTEXT_BATCH{i:03}_ADJUDICATIONS_V1.json' for i in range(2, 14)]
for name in names:
    for row in load(A / name)['records']:
        rootrefs[row['id']] = name
independent = load(A / 'NUMERIC_INDEPENDENT_20_REVIEW_BINDINGS_VERIFIED_V1.json')
assert independent['errors'] == 0 and len(independent['rows']) == 20
crefs = {row['id']: row for row in independent['rows']}
versions = {1:'v20', 2:'v15', 3:'v10', 4:'v13', 5:'v12', 6:'v15', 7:'v13', 8:'v9', 9:'v3'}
current = {}
for page, version in versions.items():
    complete = load(B / f'remaining_field_title_page_{page:03}_counter_v1_snapshots' / version / 'complete.json')
    assert not complete['errors']
    for shard in complete['shards']:
        path = ROOT / shard['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == shard['sha256']
        values = load(path)
        rows = values if isinstance(values, list) else values.get('records', values.get('rows', []))
        current.update({row['id']: row for row in rows})
bridges = {
    '69':'ROOT_POST_HOLD_HEADERS_AND_APPLICATION_VERIFIED_V1.json',
    '399':'ROOT_POST_HOLD_HEADERS_AND_APPLICATION_VERIFIED_V1.json',
    '207':'ROOT_POST_HOLD_HEADERS_AND_APPLICATION_VERIFIED_V1.json',
    '29112':'ROOT_THREE_FIELD_NARROW_FOLLOWUPS_VERIFIED_V1.json',
    '33415':'ROOT_THREE_FIELD_NARROW_FOLLOWUPS_VERIFIED_V1.json',
    '85646':'ROOT_TWO_FIELD_CODE_FOLLOWUPS_VERIFIED_V1.json',
    '50533':'ROOT_50533_EXACT_DECIMAL_FOLLOWUP_VERIFIED_V1.json',
    '79622':'ROOT_FOUR_NUMERIC_CONTEXT_FOLLOWUPS_VERIFIED_V1.json',
    '72091':'ROOT_FOUR_NUMERIC_CONTEXT_FOLLOWUPS_VERIFIED_V1.json',
    '60001':'ROOT_FOUR_NUMERIC_CONTEXT_FOLLOWUPS_VERIFIED_V1.json',
    '113011':'ROOT_FOUR_NUMERIC_CONTEXT_FOLLOWUPS_VERIFIED_V1.json',
}
for name in set(bridges.values()):
    load(A / name)
counts = Counter()
records = []
unmapped = []
for row in proof['rows']:
    identity = row['id']
    number = identity.split(':')[1]
    assert identity not in guard['restricted_ids'] and row['original']['sha256'] not in guard['restricted_hashes']
    selected = current[identity]
    assert selected['original']['sha256'] == row['original']['sha256']
    manual = [p['flag'] for p in row['proofs'] if p['status'] == 'MANUAL_CONTEXT_REQUIRED']
    local = [p for p in row['proofs'] if p['status'] == 'EXACT_LOCAL_ATOM_AND_UNIT']
    outcomes = Counter()
    special = []
    for flag in manual:
        kind = 'CONTEXT_RETAINED'
        if number in {'207', '79622'} or number == '29112' and flag['body_token'] == '1431.5':
            kind = 'PARTIAL_HOLD_REMOVED'
        elif number == '33415':
            assert flag['body_token'] == '-12.7'
            kind = 'SUPPORTED_TOKEN_REPAIR'
            special.append(dict(old_span=flag['body_span'], old_token='-12.7', new_token='-12',
                                reason='citation 7 separated from the actual measure range'))
        elif number == '50533' and flag['body_token'] == '2.438191288':
            kind = 'SUPPORTED_TOKEN_REPAIR'
            special.append(dict(old_span=flag['body_span'], old_token='2.438191288',
                                new_token='32.438191288', reason='adjacent example and exact decimal equality'))
        if identity not in rootrefs and identity not in crefs:
            unmapped.append(dict(id=identity, flag=flag))
        outcomes[kind] += 1
        counts[kind] += 1
    counts['EXACT_LOCAL_ATOM_AND_UNIT'] += len(local)
    changed = selected['clean_text_sha256'] != row['body']['sha256']
    assert not changed or number in bridges, (identity, 'missing verified body-version bridge')
    records.append(dict(
        id=identity, original_sha256=row['original']['sha256'],
        V1_body_sha256=row['body']['sha256'], current_body_sha256=selected['clean_text_sha256'],
        current_review=selected['review'], manual_flags=len(manual), local_exact_proofs=len(local),
        manual_dispositions=dict(outcomes), special_repaired_tokens=special,
        context_receipt='NUMERIC_INDEPENDENT_20_REVIEW_BINDINGS_VERIFIED_V1.json'
        if identity in crefs else rootrefs.get(identity),
        body_version_bridge=bridges[number] if changed else None,
        whole_document_fact_pass=False))
assert not unmapped and len(records) == 79
assert sum(len(row['proofs']) for row in proof['rows']) == 425
assert dict(counts) == dict(CONTEXT_RETAINED=406, PARTIAL_HOLD_REMOVED=4,
                           SUPPORTED_TOKEN_REPAIR=2, EXACT_LOCAL_ATOM_AND_UNIT=13), dict(counts)
pins[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()
result = dict(
    status='V1_NUMERIC_SIGNALS_HAVE_SOURCE_BOUND_OUTCOMES_NOT_GENERIC_ACCEPTANCE',
    V1_documents=79, V1_atoms=425, V1_manual_atoms=412, dispositions=dict(counts),
    unmapped_manual_atoms=0, root_context_source_count=len(set(rootrefs) & {r['id'] for r in records}),
    independent_existing_C_source_count=20,
    local_proof_only_sources=[row['id'] for row in records if row['manual_flags'] == 0],
    records=records, input_pins=pins, new_first_review_unique_added=0,
    does_not_replace_V2_or_V3_flags=True, source_wide_fact_or_semantic_pass=False,
    generic_guards_changed=False, new_root_or_cache_admissions=0,
    whole_goal_complete=False, training_authorized=False)
target = A / 'FIELD_NUMERIC_V1_CONTEXT_DISPOSITIONS_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(path=str(target.relative_to(ROOT)), sha256=hashlib.sha256(target.read_bytes()).hexdigest().upper(),
                     documents=len(records), dispositions=dict(counts), unmapped=0,
                     local_only_sources=len(result['local_proof_only_sources'])), ensure_ascii=False))

