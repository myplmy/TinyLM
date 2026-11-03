"""Record two actual birth-profile rereads without adopting any new body."""
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


def main():
    prior_path = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V4.json'
    result = json.loads(prior_path.read_text(encoding='utf-8'))
    contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
    rows = {r['id']: r for r in result['rows']}
    fixes = []
    for numeric_id, chunk, years in [(1031233, 'af11a9', ('1962', '1961')),
                                      (1052119, '7daea0', ('1952', '1968'))]:
        ident = 'expanded_train:' + str(numeric_id)
        source_pin = rows[ident]['original']
        assert ident not in contract['restricted_ids']
        assert source_pin['sha256'] not in contract['restricted_hashes']
        source = ROOT / source_pin['path']
        assert sha(source) == source_pin['sha256']
        directory = BASE / 'agents/legacy_review' / ('root11_birth_' + str(numeric_id) + '_correction_v1')
        body = directory / ('expanded_train_' + str(numeric_id) + '_revised_v3.txt')
        original = source.read_text(encoding='utf-8')
        text = body.read_text(encoding='utf-8')
        assert '살아있는 사람' in original and '살아있는 사람' in text
        assert all(year in original and year not in text for year in years)
        checks = {'both_conflicting_birth_years_omitted': True,
                  'original_living_person_category_preserved': True}
        if numeric_id == 1031233:
            assert '6월 14일' in original and '6월 14일' in text
            for value in ["[강상준의 7080사람들] '가슴앓이'의 주인공 양하영",
                          'https://entertain.naver.com/read?oid=022&aid=0002501689',
                          '세계일보', '뉴스팀', '2013-03-06', '2022-03-18']:
                assert value in original and value in text
            assert not any(line.lstrip().startswith('|') for line in text.splitlines())
            expected = original.split('학력', 1)[1].replace('1961년 출생' + chr(10), '')
            assert expected.rstrip() == text.split('학력', 1)[1].rstrip()
            checks.update({'all_filled_bibliographic_values_preserved': True,
                           'broken_template_markers_removed': True,
                           'remaining_profile_lines_preserved': True})
        else:
            assert '姜志勇' in original and '姜志勇' in text
            assert '8월 27일' in original and '8월 27일' in text
            assert '제주도 남제주군 서귀면' in original and '제주도 남제주군 서귀면' in text
            ignored = {'역대 선거 결과', '외부 링크', '1968년 출생'}
            before = [line for line in original.splitlines()[1:] if line.strip() and line.strip() not in ignored]
            after = [line for line in text.splitlines()[1:] if line.strip()]
            assert before == after
            checks.update({'actual_hanja_name_preserved': True,
                           'remaining_filled_profile_lines_preserved': True})
        assert body.stat().st_size < 20_000_000
        fixes.append({'id': ident, 'original': source_pin, 'body': pin(body),
                      'full_corrected_body_root_read_tool_chunks': [chunk] if numeric_id == 1031233 else ['c16b95', chunk],
                      'full_original_to_new_diff_root_read_tool_chunk': chunk,
                      'actual_specific_static_checks': checks,
                      'decision': 'SEMANTIC_CORRECTION_REVIEWED_NOT_ADOPTED',
                      'in_new_root_selection': False, 'in_cache3': False})
    result.update({'status': 'NINE_ACTUAL_READS_ALL_FIVE_REPLACEMENT_BODIES_REVIEWED_NOT_ADOPTED',
                   'corrected_semantic_reviewed_sources': 5, 'corrections_still_pending': 0,
                   'new_reviewed_birth_corrections': fixes, 'prior': pin(prior_path),
                   'verification_code': pin(Path(__file__).resolve())})
    assert result['old_root11_sources_requiring_replacement'] == 5
    assert result['remaining_unreviewed_flag_sources'] == 576
    out = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V5.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps({'path': str(out.relative_to(ROOT)), 'sha256': sha(out),
                      'corrected_bodies_reviewed': 5, 'adopted': 0, 'other_flags_unreviewed': 576}))


if __name__ == '__main__':
    main()
