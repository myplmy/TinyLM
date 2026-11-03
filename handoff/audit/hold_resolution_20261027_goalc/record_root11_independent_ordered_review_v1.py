"""Record two actually read semantic decisions without waiving the other flags."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

source_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
source = inv.cache.read(source_path)
flags = {row['id']: row for row in source['records'] if row.get('ordered_source_deletion') is False}
assert len(flags) == 585
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
findings = {
    'expanded_train:1006080': '원문과선택본문전부및전체diff를실제읽었다. 모친의실제이름·생몰날짜뒤닫힘괄호하나만복원했고빈각주표제만제거했다. 숫자/관계/직책/불확실성과나머지목록은보존돼있다. 사실정정이나인물사전량검증으로해석하지않는다.',
    'expanded_train:1012093': '원문과선택본문전부및전체diff를실제읽었다. 도입1950년과분류1933년이라는상충출생연도를둘다채택본문에서제외했고어느연도가참인지선택하지않았다. 사망일2018년10월9일과배우/작품명·연도/다른분류는보존돼있다. 상충원형은해당원문SHA에그대로남는다.',
}
rows = []
for ident, finding in findings.items():
    row = flags[ident]
    assert ident not in contract['restricted_ids'] and row['original_text_sha256'] not in contract['restricted_hashes']
    original, body = ROOT / row['original_comparison_source'], ROOT / row['body']
    assert inv.file_sha(original) == row['original_text_sha256']
    assert inv.file_sha(body) == row['clean_text_sha256']
    rows.append({'id': ident, 'original': {'path': str(original.relative_to(ROOT)), 'sha256': row['original_text_sha256']},
        'body': {'path': row['body'], 'sha256': row['clean_text_sha256']},
        'reviewer': 'root', 'full_original_and_selected_body_read': True, 'full_diff_read': True,
        'observation_tool_chunk': '8d5d4b', 'finding': finding,
        'decision': 'REVIEWED_ACCEPTABLE_CHANGES_WITH_STATED_LIMITS', 'source_fact_verification': False})
inv.write_json(AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V1.json', {
    'status': 'ACTUAL_INDEPENDENT_SEMANTIC_REVIEW_PARTIAL_NOT_WHOLE_CORPUS_COMPLETION',
    'ordered_flag_sources': 585, 'actually_reviewed_sources': len(rows), 'remaining_flag_sources': 585 - len(rows),
    'rows': rows, 'input_pins': {str(path.relative_to(ROOT)): inv.file_sha(path) for path in (source_path, Path(__file__))},
    'detector_flag_automatically_waived': False, 'source_or_admission_changed': False,
    'birth_independent_whole_second_reading': 'NOT_COMPLETED',
    'whole_corpus_semantic_completion': False, 'goal_complete': False, 'training_authorized': False})
print('actual independent full source/body/diff reviews:', len(rows), '; remaining flagged:', 585 - len(rows))
