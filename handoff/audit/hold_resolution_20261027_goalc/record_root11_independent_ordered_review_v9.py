"""Bind three actual replacement readings and verify only the approved edits."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


prior = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V8.json'
result = json.loads(prior.read_text(encoding='utf-8'))
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
sources = {r['id']: r for r in result['rows']}
verified = []
for digits in ('1075729', '1198608', '1251896'):
    ident = 'expanded_train:' + digits
    row = sources[ident]
    assert ident not in contract['restricted_ids'] and row['original']['sha256'] not in contract['restricted_hashes']
    original, old = ROOT / row['original']['path'], ROOT / row['body']['path']
    assert sha(original) == row['original']['sha256'] and sha(old) == row['body']['sha256']
    directory = BASE / 'agents/legacy_review' / ('root11_flag_' + digits + '_correction_v1')
    body = directory / ('expanded_train_' + digits + '_revised_v1.txt')
    before = old.read_text(encoding='utf-8')
    if digits == '1075729':
        lines = before.splitlines(keepends=True)
        repeated = [i for i, line in enumerate(lines) if line.rstrip(chr(13) + chr(10)) == '296 GTB']
        assert len(repeated) == 5
        assert all(not line.strip() or line.rstrip(chr(13) + chr(10)) == '296 GTB'
                   for line in lines[repeated[0]:])
        expected = ''.join(line for i, line in enumerate(lines) if i not in set(repeated))
    elif digits == '1198608':
        empty = '연혁' + chr(10)
        assert before.count(empty) == 1
        expected = before.replace(empty, '', 1)
    else:
        flat = ">>> input( 'What is your number: ' ) '32' >>> number = input( 'What is your number: ' ) >>> number '32'"
        fixed = chr(10).join([">>> input( 'What is your number: ' )", "'32'",
            ">>> number = input( 'What is your number: ' )", '>>> number', "'32'"])
        assert before.count(flat) == 1
        expected = before.replace(flat, fixed, 1)
    assert body.read_text(encoding='utf-8') == expected
    verified.append({'id': ident, 'original': row['original'], 'old_body': row['body'],
        'body': {'path': str(body.relative_to(ROOT)), 'sha256': sha(body)},
        'review': {'path': str((directory / 'review_001.md').relative_to(ROOT)), 'sha256': sha(directory / 'review_001.md')},
        'full_corrected_body_root_read_tool_chunk': 'be4042',
        'full_old_to_new_diff_root_read_tool_chunk': 'be4042',
        'only_exact_approved_old_body_edits': True,
        'decision': 'CORRECTION_REVIEWED_NOT_ADOPTED', 'in_new_root_selection': False, 'in_cache3': False})
result.update({'status': 'TWENTY_ONE_ACTUAL_READS_THIRTEEN_REPLACEMENTS_REVIEWED_ONE_PENDING',
    'corrected_semantic_reviewed_sources': 13, 'corrections_still_pending': 1,
    'new_reviewed_nonbirth_corrections': verified,
    'prior': {'path': str(prior.relative_to(ROOT)), 'sha256': sha(prior)},
    'verification_code': {'path': str(Path(__file__).resolve().relative_to(ROOT)), 'sha256': sha(Path(__file__).resolve())}})
out = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V9.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps({'source_reads': 21, 'known_old_body_defects': 14,
    'replacements_reviewed': 13, 'pending_replacements': 1, 'other_flags_unreviewed': 564, 'adopted': 0}))
