"""Check the 25 frozen rejected rows against the opt-in heading collector."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
FORBIDDEN_IDS = {14760, 756966, 15695, 1216576, 1250821, 20624, 6030}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def pinned(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path),
            'bytes': path.stat().st_size}


def load(version):
    path = BASE / 'remaining_literal_full_counter_v1_snapshots' / version / 'complete.json'
    complete = json.loads(path.read_text(encoding='utf-8'))
    rows = []
    for item in complete['shards']:
        shard = ROOT / item['path']
        assert sha(shard) == item['sha256']
        rows.extend(json.loads(shard.read_text(encoding='utf-8')))
    assert len(rows) == complete['records'] == 1793
    return complete, rows, pinned(path)


def main():
    old, old_rows, old_pin = load('v12')
    new, new_rows, new_pin = load('v13')
    rejected = [r for r in old_rows if r.get('status') == 'MECHANICAL_REJECTION_NOT_APPLIED']
    assert len(rejected) == 25
    index = {r['id']: r for r in new_rows}
    assert len(index) == len(new_rows)
    evidence = []
    for before in rejected:
        numeric_id = int(before['id'].split(':')[1])
        assert numeric_id not in FORBIDDEN_IDS  # Before accessing any body.
        after = index[before['id']]
        assert before['error'] == 'NO_EXACT_BODY_OUTPUT_PATH'
        assert before['review'] == after['review']
        assert before['review_text'] == after['review_text']
        assert before['role'] == after['role'] == 'context_latin'
        assert before['cohort'] == after['cohort']
        assert after['status'] in {'PINNED_BODY_NOT_ROOT_ADMISSION',
                                   'MATERIALIZED_BODY_NOT_ROOT_ADMISSION'}
        assert after['body_reference_scope'] == 'EXPLICIT_OUTPUT_COLUMN'
        assert after['declared_output_cell'].endswith('.txt')
        review = ROOT / after['review']['path']
        assert sha(review) == after['review']['sha256']
        assert '| 출력 TXT |' in review.read_text(encoding='utf-8')
        body = ROOT / after['body']
        assert body.is_relative_to(BASE)
        assert sha(body) == after['clean_text_sha256']
        assert body.stat().st_size < 20_000_000
        assert after['cache_admitted'] is False
        evidence.append({'id': after['id'], 'review': pinned(review),
                         'review_row_bytes_unchanged': True,
                         'old_error': before['error'], 'new_status': after['status'],
                         'declared_output_cell': after['declared_output_cell'],
                         'original': after['original'], 'body': pinned(body)})
    assert not new['errors']
    out = AUDIT / 'OUTPUT_HEADING_25_BINDINGS_VERIFIED_V1.json'
    document = {
        'status': 'TWENTY_FIVE_EXPLICIT_BINDINGS_RECOVERED_WITHOUT_REVIEW_REWRITE',
        'old_snapshot': old_pin, 'new_snapshot': new_pin,
        'old_rejected_count': 25, 'recovered_count': len(evidence),
        'same_review_file_and_row_bytes': 25, 'body_hashes_verified': 25,
        'new_snapshot_counts': new['counts'], 'rows': evidence,
        'verification_code': pinned(Path(__file__).resolve()),
        'targeted_regressions': {'tests': 5, 'exit_code': 0,
                                'observation_tool_chunk': '3bdf1b'},
        'root_adopted': 0, 'cache_admitted': 0, 'training_authorized': False,
        'limits': 'Only explicit heading binding was checked. Saved bodies still require root adjudication and semantic review. Existing snapshots, raw sources and cache3 were not changed.',
    }
    payload = (json.dumps(document, ensure_ascii=False, indent=2) + '\n').encode()
    assert len(payload) < 20_000_000
    with out.open('xb') as stream:
        stream.write(payload)
    print(json.dumps({'receipt': str(out.relative_to(ROOT)), 'sha256': sha(out),
                      'recovered': len(evidence), 'errors': len(new['errors'])}))


if __name__ == '__main__':
    main()
