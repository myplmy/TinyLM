"""Retain prior reads and record the actually observed residual semantic defect."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
prior_path = AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V1.json'
prior = inv.cache.read(prior_path)
source_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
records = {row['id']: row for row in inv.cache.read(source_path)['records']}
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
rows = list(prior['rows'])
decisions = {
    'expanded_train:1018113': ('CORRECTION_REQUIRED_BEFORE_SEMANTIC_CLOSURE', '原형/선택본문전부와전체diff를실제읽었다. arity 링크구문이깨져있고없어진수식의p를직접가리키는문장이남는다. 이웃Union/SetDifference/CartesianProduct 귀속도기존명명으로보완필요하다. SQL원저자결함을추정수리하지않는다. 같은역할Luna에정확새사본/새working/가이드를제공했으며새본문은아직미검산이다.'),
    'expanded_train:1018172': ('REVIEWED_ACCEPTABLE_CHANGES_WITH_STATED_LIMITS', '원문/선택본문전부와전체diff를실제읽었다. 1989년과1992년상충출생연도는두언어/분류에서함께분리하고원래12월5일과배우·작품·배역·연도/살아있음은보존했다. 정확동일한광고업계문장두번중한번만남겼으며개별작품·광고출연자료는삭제하지않았다. 사실판정이나출생연도선택을하지않는다.'),
}
for ident, (decision, finding) in decisions.items():
    row = records[ident]
    assert row['ordered_source_deletion'] is False
    assert ident not in contract['restricted_ids'] and row['original_text_sha256'] not in contract['restricted_hashes']
    assert inv.file_sha(ROOT / row['original_comparison_source']) == row['original_text_sha256']
    assert inv.file_sha(ROOT / row['body']) == row['clean_text_sha256']
    rows.append({'id': ident, 'original': {'path': row['original_comparison_source'], 'sha256': row['original_text_sha256']},
        'body': {'path': row['body'], 'sha256': row['clean_text_sha256']}, 'reviewer': 'root',
        'full_original_and_selected_body_read': True, 'full_diff_read': True,
        'observation_tool_chunk': '538c0c', 'finding': finding.replace('原형', '원형'),
        'decision': decision, 'source_fact_verification': False})
assert len({row['id'] for row in rows}) == len(rows) == 4
inv.write_json(AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V2.json', {
    'status': 'ACTUAL_PARTIAL_INDEPENDENT_REVIEW_WITH_UNRESOLVED_CORRECTION',
    'ordered_flag_sources': 585, 'actually_reviewed_sources': 4, 'acceptable_reviewed_sources': 3,
    'correction_required_sources': 1, 'remaining_unreviewed_flag_sources': 581, 'rows': rows,
    'prior': {'path': str(prior_path.relative_to(ROOT)), 'sha256': inv.file_sha(prior_path)},
    'input_pins': {str(path.relative_to(ROOT)): inv.file_sha(path) for path in (source_path, Path(__file__))},
    'detector_flag_automatically_waived': False, 'source_or_admission_changed': False,
    'birth_independent_whole_second_reading': 'NOT_COMPLETED', 'whole_corpus_semantic_completion': False,
    'goal_complete': False, 'training_authorized': False})
print('independent reviewed 4; acceptable 3; correction pending 1; unread flags 581')
