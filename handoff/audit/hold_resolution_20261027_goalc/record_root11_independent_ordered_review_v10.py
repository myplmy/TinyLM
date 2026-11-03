"""Bind the last of fourteen known repairs after its actual full-body reading."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


prior = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V9.json'
result = json.loads(prior.read_text(encoding='utf-8'))
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
ident = 'expanded_train:129557'
row = next(r for r in result['rows'] if r['id'] == ident)
assert ident not in contract['restricted_ids'] and row['original']['sha256'] not in contract['restricted_hashes']
original, old = ROOT / row['original']['path'], ROOT / row['body']['path']
assert sha(original) == row['original']['sha256'] and sha(old) == row['body']['sha256']
assert '전자기장 텐서 Fμν의 성분은 다음과 같다.' in original.read_text(encoding='utf-8')
directory = BASE / 'agents/context_hangul/root11_flag_129557_correction_v1'
body = directory / 'revise_129557_preserve_Fmunu_notation_v1.txt'
before = old.read_text(encoding='utf-8')
anchor = '공식들을 간단한 형태로 나타낼 수 있게 해준다.'
assert before.count(anchor) == 1 and 'Fμν' not in before
expected = before.replace(anchor, anchor + ' 전자기장 텐서의 기호는 Fμν이다.', 1)
if not expected.endswith(chr(10)):
    expected += chr(10)
assert body.read_text(encoding='utf-8') == expected
result['new_reviewed_nonbirth_corrections'].append({'id': ident,
    'original': row['original'], 'old_body': row['body'],
    'body': {'path': str(body.relative_to(ROOT)), 'sha256': sha(body)},
    'review': {'path': str((directory / 'review_001.md').relative_to(ROOT)), 'sha256': sha(directory / 'review_001.md')},
    'full_corrected_body_root_read_tool_chunk': 'f93b6c',
    'full_old_to_new_diff_root_read_tool_chunk': 'f93b6c',
    'only_exact_approved_symbol_restoration_and_final_newline': True,
    'decision': 'CORRECTION_REVIEWED_NOT_ADOPTED', 'in_new_root_selection': False, 'in_cache3': False})
result.update({'status': 'TWENTY_ONE_ACTUAL_READS_ALL_FOURTEEN_REPLACEMENTS_REVIEWED_NOT_ADOPTED',
    'corrected_semantic_reviewed_sources': 14, 'corrections_still_pending': 0,
    'prior': {'path': str(prior.relative_to(ROOT)), 'sha256': sha(prior)},
    'verification_code': {'path': str(Path(__file__).resolve().relative_to(ROOT)), 'sha256': sha(Path(__file__).resolve())}})
out = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V10.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps({'source_reads': 21, 'known_old_body_defects': 14,
    'replacements_reviewed': 14, 'pending_replacements': 0, 'other_flags_unreviewed': 564, 'adopted': 0}))
