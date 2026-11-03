"""Extend the individually read HOLD ledger by one source; no corpus admission."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    previous_path = AUDIT / 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V1.json'
    result = json.loads(previous_path.read_text(encoding='utf-8'))
    manifest_path = BASE / 'remaining_literal_full_counter_v1/manifest.json'
    source = next(r for r in json.loads(manifest_path.read_text())['rows'] if r['id'] == 'expanded_train:789648')
    contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
    assert source['id'] not in contract['restricted_ids']
    assert source['original']['sha256'] not in contract['restricted_hashes']
    assert sha(ROOT / source['original']['path']) == source['original']['sha256']
    directory = BASE / 'agents/context_latin/remaining_literal_full_counter_v1'
    sidecar = directory / 'hold_789648_task058_v1.md'
    assert sidecar.is_file()
    assert len(result['rows']) == 7 and source['id'] not in {r['id'] for r in result['rows']}
    result['rows'].append({
        'id': source['id'], 'role': source['role'], 'original': source['original'],
        'source_ids': source['source_ids'], 'source_ids_sha256': source['source_ids_sha256'],
        'occurrences': source['occurrences'], 'reviewer': 'root', 'full_original_actually_read': True,
        'observation_tool_chunk': '0137a5', 'decision': 'HOLD',
        'reviewed_disposition': 'INDIVIDUALLY_REVIEWED_UNRECOVERABLE_MIXED_CONTEXT',
        'reason': '워크시트/Excel/수식 안내·여러 광고와 STUDENT MONTH YEAR 빈 양식이 서로 교차해 원래 문장/출처/입력과 결과의 귀속을 복원할 수 없다. 완결된 새 글로 재조립하지 않는다.',
        'sidecar': {'path': str(sidecar.relative_to(ROOT)), 'sha256': sha(sidecar)},
        'raw_original_preserved': True, 'unread_bulk_disposition': False,
        'new_prose_authored_by_root': False, 'root_approved_nonadmission': True, 'cache_admitted': False,
    })
    result.update({'status': 'EIGHT_INDIVIDUAL_FULL_SOURCE_READINGS_NOT_UNREAD_HOLD_RENAMING',
                   'unique_sources': 8, 'positions': sum(r['occurrences'] for r in result['rows']),
                   'prior': {'path': str(previous_path.relative_to(ROOT)), 'sha256': sha(previous_path)},
                   'new_roster_or_cache_adoption': 0})
    out = AUDIT / 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V2.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps({'path': str(out.relative_to(ROOT)), 'sources': 8, 'positions': result['positions'], 'adopted': 0}))


if __name__ == '__main__':
    main()
