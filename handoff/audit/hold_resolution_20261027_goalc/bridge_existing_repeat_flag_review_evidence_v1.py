"""Reuse exact existing repeat-review provenance, without granting flag waivers."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify(pin):
    path = (ROOT / pin['path']).resolve()
    assert path.is_relative_to(BASE) or path.is_relative_to(AUDIT)
    data = path.read_bytes()
    assert len(data) < 20_000_000 and sha(data) == pin['sha256']
    return data


root_path = AUDIT / 'ROOT_AUTHORED_SELECTIONS_V11_PREVIEW6.json'
guard_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
manifest_path = BASE / 'repeat_named_full_independent_v1/manifest.json'
snapshot_path = BASE / 'repeat_named_full_independent_v1_snapshots/v16/complete.json'
birth_bridge_path = AUDIT / 'ROOT11_AND_BIRTH_SAVED_REVIEW_COVERAGE_BRIDGE_V2.json'
direct_path = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V10.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
root = read(root_path)
assert sha(root_path.read_bytes()) == '624AE91E66B4104F864E389B001A58E2C67C2D509D78F7E348DABC4FAD30A152'
closure = read(AUDIT / 'ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1.json')
assert sha(guard_path.read_bytes()) == closure['input_pins'][str(guard_path.relative_to(ROOT))]
assert sha(root_path.read_bytes()) == closure['input_pins'][str(root_path.relative_to(ROOT))]
for path in (manifest_path, snapshot_path):
    assert sha(path.read_bytes()) == root['input_pins'][str(path.relative_to(ROOT))]
guards = {r['id']: r for r in read(guard_path)['records'] if r.get('ordered_source_deletion') is False}
assert len(guards) == 585
selections = {r['id']: r['selected'] for r in root['rows']}
sources = {r['id']: r for r in read(manifest_path)['rows']}
snapshot = read(snapshot_path)
assert not snapshot['errors'] and not snapshot['needs_root']
records = {}
for pin in snapshot['shards']:
    for row in json.loads(verify(pin)):
        assert row['id'] not in records
        records[row['id']] = row
provenance = {r['id']: r for r in root['independent_repeat_provenance']}
ids = sorted(set(guards) & set(provenance))
assert len(ids) == 80
contract = read(contract_path)
result_rows = []
for ident in ids:
    source, record, old, selected = sources[ident], records[ident], provenance[ident], selections[ident]
    # Both metadata gates precede original/candidate/selected body hashing.
    assert ident not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    assert source['original']['sha256'] == guards[ident]['original_text_sha256'] == selected['original']['sha256']
    assert source['role'] == record['role'] == old['independent_role']
    assert source['role'] != source['previous_editor_role']
    assert old['first_review'] == source['previous_editor_review']
    assert source['candidate']['sha256'] == old['first_clean_text_sha256']
    assert record['clean_text_sha256'] == selected['clean_text_sha256'] == old['selected_clean_text_sha256'] == guards[ident]['clean_text_sha256']
    assert record['read_scope'] and record['review'] == old['independent_review']
    for pin in (source['original'], source['candidate'],
                {'path': record['body'], 'sha256': record['clean_text_sha256']}):
        verify(pin)
    for pin in (old['first_review'], old['independent_review']):
        review = verify({'path': pin['archive'], 'sha256': pin['sha256']}).decode('utf-8')
        source_name, number = ident.split(':')
        matching_rows = [line for line in review.splitlines()
                         if line.startswith('|') and
                         line.split('|')[1].strip().strip('`') in {ident, number}]
        assert len(matching_rows) == 1
        if matching_rows[0].split('|')[1].strip().strip('`') == number:
            # Two historical first reviews use only a numeric row and a bare
            # output basename. Resolve them through the pinned source manifest
            # and prove the numeric ID is unique in that exact review scope.
            same_number_same_review = {
                other_id for other_id, other in sources.items()
                if other_id.split(':')[1] == number and
                other['previous_editor_review']['sha256'] == pin['sha256']
            }
            assert same_number_same_review == {ident}
    result_rows.append({
        'id': ident, 'original': source['original'], 'first_editor_role': source['previous_editor_role'],
        'first_review': old['first_review'], 'independent_role': source['role'],
        'independent_review': old['independent_review'], 'actual_read_scope_declared': record['read_scope'],
        'independent_input': source['candidate'],
        'independent_result_and_current_flagged_body': {'path': record['body'], 'sha256': record['clean_text_sha256']},
        'independent_result_changed_from_its_input': source['candidate']['sha256'] != record['clean_text_sha256'],
        'metadata_and_bytes_verified': True, 'root_semantic_waiver': False,
    })
direct = {r['id'] for r in read(direct_path)['rows']}
birth = {r['id'] for r in read(birth_bridge_path)['rows']} & set(guards)
repeat = set(ids)
union = direct | birth | repeat
inputs = [root_path, guard_path, AUDIT / 'ROOT11_COMPLETED_COHORT_BODY_CLOSURE_V1.json',
          manifest_path, snapshot_path, birth_bridge_path, direct_path,
          contract_path, Path(__file__).resolve()]
result = {
    'status': 'EIGHTY_EXISTING_DISTINCT_ROLE_REVIEW_RECORDS_EXACTLY_BOUND_NOT_SEMANTIC_WAIVERS',
    'existing_repeat_flag_review_sources': len(result_rows),
    'unchanged_from_independent_input': sum(not r['independent_result_changed_from_its_input'] for r in result_rows),
    'changed_by_independent_reviewer': sum(r['independent_result_changed_from_its_input'] for r in result_rows),
    'ordered_flag_sources': 585, 'root_direct_records': len(direct),
    'birth_snapshot4_flag_records': len(birth), 'three_scope_record_union': len(union),
    'flags_without_record_in_these_three_frozen_scopes': 585 - len(union),
    'rows': result_rows,
    'input_pins': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in inputs},
    'new_root_or_cache_adoptions': 0, 'automatic_flag_waivers': 0, 'protected_body_reads': 0,
    'goal_complete': False,
    'limits': ['검토기록과 정확 입력·출력의 연결 검사다. 새 총괄 전문 의미 판독이나 품질승인이 아니다.',
               '45개는 독립검토 입력과 현재본문이 같고35개는 독립검토자가 바꾼 결과다. 둘을 같은 증거로 합치지 않는다.',
               '이 세 범위 외의 과거 리뷰가 없는 것으로 단정하지 않는다. 그 범위의 계보도 추가 대조해야 한다.',
               '기존cache3의 소속과 바이트를 바꾸지 않는다. 발견된 실제 결함 조치와 최종 채택은 별도다.'],
}
out = AUDIT / 'EXISTING_REPEAT_ORDERED_FLAG_REVIEW_BINDINGS_V1.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({k: v for k, v in result.items() if isinstance(v, (int, bool))}))
