"""Join the exact reviewed followups into the 34-source context ledger."""
from pathlib import Path
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
pins = {}
reused = AUDIT / 'record_root11_birth_flag_context_v1.py'
nodes = [node for node in ast.parse(reused.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name == 'read']
assert len(nodes) == 1
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(reused), 'exec'), globals())
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser
resolve, parse, _ = load_parser()
prior = json.loads(read(AUDIT / 'ROOT11_BIRTH_FLAG_CONTEXT_ADJUDICATION_V1.json'))
followups = json.loads(read(AUDIT / 'ROOT11_FIVE_CONTEXT_FOLLOWUPS_VERIFIED_V1.json'))
assert followups['source_scoped_followups_pending'] == 0
assert followups['other_birth_review_rows_unchanged'] == 20
assert {row['id'] for row in followups['birth_results']} == set(prior['pending_ids'])
contract = json.loads(read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'))
assert pins[str((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').relative_to(ROOT))] == (
    'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF')
snapshots = {}
for version in ('v28', 'v29'):
    value = json.loads(read(BASE / 'birth_root11_independent_v1_snapshots' / version / 'complete.json'))
    assert not value['errors'] and not value['needs_root']
    records = []
    for shard in value['shards']:
        payload = read(ROOT / shard['path'])
        assert hashlib.sha256(payload).hexdigest().upper() == shard['sha256']
        records += json.loads(payload)
    assert len(records) == len({row['id'] for row in records}) == 2707
    snapshots[version] = {row['id']: row for row in records}
older, latest = snapshots['v28'], snapshots['v29']
assert set(older) == set(latest)
assert all(older[key]['original'] == latest[key]['original'] for key in older)
changed_bodies = sorted(key for key in older if older[key]['clean_text_sha256'] != latest[key]['clean_text_sha256'])
changed_reviews = sorted(key for key in older if older[key]['review']['sha256'] != latest[key]['review']['sha256'])
assert set(changed_bodies) == {'expanded_train:79984', 'expanded_train:81208',
                               'expanded_train:139681', 'expanded_train:355073'}
edited_review_rows = set(prior['pending_ids']) | {'expanded_train:341392'}
assert edited_review_rows <= set(changed_reviews) and len(changed_reviews) == 30
unchanged_rows_in_new_containers = set(changed_reviews) - edited_review_rows
assert len(unchanged_rows_in_new_containers) == 24
for ident in sorted(unchanged_rows_in_new_containers):
    exact_rows = []
    for record in (older[ident], latest[ident]):
        payload = read(ROOT / record['review']['archive'])
        assert hashlib.sha256(payload).hexdigest().upper() == record['review']['sha256']
        matching = [row for row in parse(payload) if resolve(row['cells'][0]) == ident]
        assert len(matching) == 1
        exact_rows.append(matching[0]['raw'])
    assert exact_rows[0] == exact_rows[1]
by_id = {row['id']: row for row in followups['birth_results']}
rows = []
for previous in prior['rows']:
    ident = previous['id']
    current = latest[ident]
    assert current['original'] == previous['original']
    assert ident not in contract['restricted_ids']
    assert current['original']['sha256'] not in contract['restricted_hashes']
    payload = read(ROOT / current['body'])
    assert hashlib.sha256(payload).hexdigest().upper() == current['clean_text_sha256']
    review = read(ROOT / current['review']['archive'])
    assert hashlib.sha256(review).hexdigest().upper() == current['review']['sha256']
    row = dict(previous)
    row['body_at_diagnostic_snapshot'] = row.pop('body')
    row['review_at_diagnostic_snapshot'] = row.pop('review')
    row['body'] = dict(path=current['body'], sha256=current['clean_text_sha256'])
    row['review'] = current['review']
    row['context_scope_closed'] = True
    if ident in by_id:
        verified = by_id[ident]
        assert current['clean_text_sha256'] == verified['body']['sha256']
        assert current['review']['sha256'] == verified['review']['sha256']
        row['prior_context_decision'] = row['context_decision']
        row['context_decision'] = 'SCOPED_AUTHORED_FOLLOWUP_CONTEXT_AND_BYTES_VERIFIED'
        row['followup'] = verified
        row['reason_at_followup_request'] = row['reason']
        row['reason'] = '요청한 좁은 후속의 실제 새본문/리뷰·원형근거·밖바이트 검산을 마쳤고 최신선택에 연결했다. 이전 요청 사유와 원형 진단은 별도 필드에 보존한다.'
    else:
        assert current['clean_text_sha256'] == previous['body']['sha256']
        if ident == 'expanded_train:341392':
            assert current['review']['path'].endswith('/review_137_v4.md')
            assert current['review']['sha256'] == prior['input_pins'][current['review']['path']]
        else:
            assert current['review']['sha256'] == previous['review']['sha256'] or ident in unchanged_rows_in_new_containers
    rows.append(row)
assert len(rows) == 34
delivery = json.loads(read(BASE / 'birth_root11_input_delivery_gated_v1/v19/complete.json'))
assert delivery['raw_errors'] == 0 and not delivery['failures']
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1712
assert delivery['counts']['HISTORICAL_BEFORE_ACTIVATION_NO_RETROSPECTIVE_EMISSION_CLAIM'] == 995
read(reused)
read(Path(__file__).resolve())
result = dict(status='ALL_34_BIRTH_DIAGNOSTIC_SOURCE_CONTEXT_SCOPES_EXPLAINED_AND_FIVE_FOLLOWUPS_BOUND',
              original_diagnostic_sources=34, context_explained_sources=34,
              source_scoped_followups_pending=0, rows=rows,
              independent_birth_saved=2707, unchanged_body_selection_hashes=2703,
              changed_body_ids=changed_bodies, changed_review_ids=changed_reviews,
              actual_edited_review_row_ids=sorted(edited_review_rows),
              unchanged_exact_rows_in_new_review_containers=24,
              current_raw_snapshot='birth_root11_independent_v1_snapshots/v29',
              current_delivery_snapshot='birth_root11_input_delivery_gated_v1/v19',
              original_diagnostic_flags_retained=True, input_pins=pins,
              automatic_flag_waivers=0, new_root_or_cache_adoptions=0,
              independent_whole_2707_semantic_pass_claimed=False,
              all_formatting_in_whole_corpus_claimed_clean=False,
              goal_complete=False, training_authorized=False)
with (AUDIT / 'ROOT11_BIRTH_FLAG_CONTEXT_ADJUDICATION_V2.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], sources=34, pending=0,
                     changed_bodies=4, changed_review_containers_record_scopes=30,
                     edited_review_rows=6, unchanged_review_rows=24, unchanged_body_hashes=2703,
                     new_root_or_cache_adoptions=0), ensure_ascii=False))
