"""Bind five newly reread replacement bodies and check their exact approved edits."""
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
    prior_path = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V6.json'
    result = json.loads(prior_path.read_text(encoding='utf-8'))
    contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
    source_rows = {r['id']: r for r in result['rows']}
    cases = [
        ('104207', 'revise_104207_birth_conflict_v1.txt', [('임달식은', '임달식(林達植)은'), ('1964년 출생' + chr(10), '')], ('1963', '1964')),
        ('1056327', 'revise_1056327_birth_conflict_v1.txt', [('1978년 출생' + chr(10), '')], ('1987', '1978')),
        ('1056993', 'revise_1056993_birth_conflict_v1.txt', [('하킴은 1959년 2월 12일 뉴욕에서 태어났다.', '하킴은 2월 12일 뉴욕에서 태어났다.')], ('1959', '1958')),
        ('1060163', 'revise_1060163_birth_conflict_v1.txt', [('1981년 출생' + chr(10), '')], ('1985', '1981')),
        ('106989', 'revise_106989_birthplace_and_conflict_v1.txt', [('샤오자이(4월 10일 생일)', '샤오자이(4월 10일 생일, 중국 베이징 출생)')], ('1980', '1977')),
    ]
    verified = []
    for digits, name, edits, years in cases:
        ident = 'expanded_train:' + digits
        row = source_rows[ident]
        assert ident not in contract['restricted_ids']
        assert row['original']['sha256'] not in contract['restricted_hashes']
        original, old = ROOT / row['original']['path'], ROOT / row['body']['path']
        assert sha(original) == row['original']['sha256']
        assert sha(old) == row['body']['sha256']
        directory = BASE / 'agents/context_hangul' / ('root11_birth_' + digits + '_correction_v2')
        body = directory / name
        expected = old.read_text(encoding='utf-8')
        for before, after in edits:
            assert expected.count(before) == 1
            expected = expected.replace(before, after, 1)
        actual = body.read_text(encoding='utf-8')
        assert expected == actual  # No other old-body byte was changed.
        assert all(year not in actual for year in years)
        assert '살아있는 사람' in actual and '살아있는 사람' in original.read_text(encoding='utf-8')
        assert body.stat().st_size < 20_000_000
        verified.append({'id': ident, 'original': row['original'], 'old_body': row['body'],
                         'body': pin(body), 'review': pin(directory / 'review_001.md'),
                         'full_corrected_body_root_read_tool_chunk': '5e9caa',
                         'full_old_to_new_diff_root_read_tool_chunk': '5e9caa',
                         'only_exact_approved_old_body_edits': True,
                         'both_conflicting_year_values_absent': True,
                         'living_person_category_preserved': True,
                         'decision': 'SEMANTIC_CORRECTION_REVIEWED_NOT_ADOPTED',
                         'in_new_root_selection': False, 'in_cache3': False})
    result.update({'status': 'FIFTEEN_ACTUAL_READS_ALL_TEN_REPLACEMENTS_REVIEWED_NOT_ADOPTED',
                   'corrected_semantic_reviewed_sources': 10, 'corrections_still_pending': 0,
                   'new_reviewed_followup_corrections': verified,
                   'prior': pin(prior_path), 'verification_code': pin(Path(__file__).resolve())})
    out = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps({'path': str(out.relative_to(ROOT)), 'sha256': sha(out),
                      'old_body_defects': 10, 'replacements_reviewed': 10, 'other_flags_unread': 570,
                      'adopted': 0}))


if __name__ == '__main__':
    main()
