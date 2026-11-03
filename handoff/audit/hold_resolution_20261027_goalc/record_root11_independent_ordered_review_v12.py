"""Verify the four source-read repeat repairs against their exact allowed edits."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


prior = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V11.json'
result = json.loads(prior.read_text(encoding='utf-8'))
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
cases = {
    '151': ('historical_review', 'expanded_train_151_historical_review_20261103_v1.txt'),
    '261707': ('context_latin', 'reviewed_261707_root11_v2.txt'),
    '327633': ('context_latin', 'reviewed_327633_root11_v2.txt'),
    '937040': ('context_controls', 'expanded_train_937040_reviewed_v2.txt'),
}
new_rows = []
for number, (role, name) in cases.items():
    ident = 'expanded_train:' + number
    row = next(r for r in result['rows'] if r['id'] == ident)
    assert ident not in contract['restricted_ids'] and row['original']['sha256'] not in contract['restricted_hashes']
    assert sha(ROOT / row['original']['path']) == row['original']['sha256']
    old_path = ROOT / row['body']['path']
    assert sha(old_path) == row['body']['sha256']
    old = old_path.read_text(encoding='utf-8')
    expected = old
    if number == '151':
        assert old.count('\n르장드르 다항식\n\n') == 1 and old.count('따라서, 르장드르') == 1
        expected = old.replace('\n르장드르 다항식\n\n', '\n', 1).replace('따라서, 르장드르', '르장드르', 1)
    elif number == '261707':
        before = '이 세 변수에 비례하는 산란 진폭 성분을 s 채널·t 채널·u 채널이라고 부른다.'
        after = '이 세 변수에 비례하는 산란 진폭 성분은 파인먼 도형으로 나타낸다. 파인먼 도형에 해당하는 산란 진폭 성분을 s 채널 · t 채널 · u 채널로 부른다.'
        assert old.count(before) == 1
        expected = old.replace(before, after, 1)
    elif number == '327633':
        assert old.count('즉, 콤팩트 공간 위에서') == 1
        expected = old.replace('즉, 콤팩트 공간 위에서', '콤팩트 공간 위에서', 1)
    else:
        for suffix in [' Create a portrait collage ins', ' These minipeople hold important p',
                       ' These holiday ornaments are light and unbreakable,',
                       " Young writers put the puppet's arms"]:
            assert expected.count(suffix + '\n') == 1
            expected = expected.replace(suffix + '\n', '\n', 1)
    directory = BASE / 'agents' / role / ('root11_flag_' + number + '_correction_v1')
    body, review = directory / name, directory / 'review_001.md'
    assert body.read_text(encoding='utf-8') == expected
    assert ident in review.read_text(encoding='utf-8') and name in review.read_text(encoding='utf-8')
    new_rows.append({
        'id': ident, 'original': row['original'], 'old_body': row['body'],
        'body': {'path': str(body.relative_to(ROOT)), 'sha256': sha(body)},
        'review': {'path': str(review.relative_to(ROOT)), 'sha256': sha(review)},
        'full_corrected_body_root_read_tool_chunk': '6ac79d',
        'full_old_to_new_diff_root_read_tool_chunk': '6ac79d',
        'only_exact_approved_edits_and_other_bytes_unchanged': True,
        'decision': 'CORRECTION_REVIEWED_NOT_ADOPTED', 'in_new_root_selection': False,
    })
result['new_reviewed_repeat_corrections'] = new_rows
result['new_repeat_followups_pending'] = []
result.update({
    'status': 'TWENTY_SIX_ACTUAL_ROOT_READS_ALL_EIGHTEEN_KNOWN_REPLACEMENTS_REVIEWED_NOT_ADOPTED',
    'corrected_semantic_reviewed_sources': 18, 'corrections_still_pending': 0,
    'prior': {'path': str(prior.relative_to(ROOT)), 'sha256': sha(prior)},
    'verification_code': {'path': str(Path(__file__).resolve().relative_to(ROOT)), 'sha256': sha(Path(__file__).resolve())},
})
out = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V12.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'root_read_annotations': 26, 'known_replacement_bodies_reviewed': 18,
                  'known_replacement_pending': 0, 'new_root_or_cache_adoptions': 0}))
