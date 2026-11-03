"""Verify both frozen heading failures against source-bound new snapshots."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def pin(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}


def load(cohort, version):
    path = BASE / (cohort + '_snapshots') / version / 'complete.json'
    complete = json.loads(path.read_text(encoding='utf-8'))
    rows = []
    for item in complete['shards']:
        shard = ROOT / item['path']
        assert sha(shard) == item['sha256']
        rows.extend(json.loads(shard.read_text(encoding='utf-8')))
    assert len(rows) == complete['records'] == complete['expected']
    return complete, rows, pin(path)


def main():
    contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    cases, evidence = [], []
    for cohort, before_version, after_version, expected, heading in [
        ('remaining_literal_full_counter_v1', 'v12', 'v13', 25, '출력 TXT'),
        ('remaining_field_title_page_002_counter_v1', 'v2', 'v3', 55, '출력 (TXT basename)')]:
        old, previous, old_pin = load(cohort, before_version)
        new, current, new_pin = load(cohort, after_version)
        rejected = [r for r in previous if r.get('status') == 'MECHANICAL_REJECTION_NOT_APPLIED']
        assert len(rejected) == expected
        index = {r['id']: r for r in current}
        assert len(index) == len(current)
        assert not new['errors']
        for before in rejected:
            after = index[before['id']]
            assert after['id'] not in contract['restricted_ids']
            assert after['original']['sha256'] not in contract['restricted_hashes']
            assert before['error'] == 'NO_EXACT_BODY_OUTPUT_PATH'
            assert before['review'] == after['review']
            assert before['review_text'] == after['review_text']
            assert before['role'] == after['role']
            assert before['cohort'] == after['cohort'] == cohort
            assert after['status'] in {'PINNED_BODY_NOT_ROOT_ADMISSION', 'MATERIALIZED_BODY_NOT_ROOT_ADMISSION'}
            assert after['body_reference_scope'] == 'EXPLICIT_OUTPUT_COLUMN'
            review = ROOT / after['review']['path']
            assert sha(review) == after['review']['sha256']
            assert heading in review.read_text(encoding='utf-8')
            body = ROOT / after['body']
            assert body.is_relative_to(BASE)
            assert sha(body) == after['clean_text_sha256']
            assert body.stat().st_size < 20_000_000
            assert after['cache_admitted'] is False
            evidence.append({'id': after['id'], 'cohort': cohort,
                             'review': pin(review), 'review_row_bytes_unchanged': True,
                             'declared_output_cell': after['declared_output_cell'],
                             'original': after['original'], 'body': pin(body)})
        cases.append({'cohort': cohort, 'before': old_pin, 'after': new_pin,
                      'recovered': expected, 'new_snapshot_errors': len(new['errors'])})
    assert len(evidence) == 80
    result = {'status': 'EIGHTY_EXACT_BINDINGS_RECOVERED_WITH_SAME_REVIEW_BYTES',
              'cases': cases, 'recovered': 80, 'rows': evidence,
              'targeted_regression_tests': 7, 'targeted_regression_exit_code': 0,
              'targeted_regression_tool_chunk': '4a681b',
              'input_pins': [pin(contract_path), pin(Path(__file__).resolve())],
              'root_adopted': 0, 'cache_admitted': 0, 'training_authorized': False,
              'limits': 'Explicit file binding and body hashes only; not semantic completion. Sources, previous snapshots and cache3 remain unchanged.'}
    out = AUDIT / 'OUTPUT_HEADING_80_BINDINGS_VERIFIED_V2.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps({'path': str(out.relative_to(ROOT)), 'sha256': sha(out),
                      'recovered': 80, 'errors': 0}))


if __name__ == '__main__':
    main()
