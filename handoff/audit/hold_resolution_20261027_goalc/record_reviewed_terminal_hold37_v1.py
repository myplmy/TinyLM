"""Add one fully read damaged preview to the exact reviewed non-admission ledger."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

prior_path = AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD36_V1.json'
manifest_path = inv.BASE / 'remaining_literal_full_counter_v1/manifest.json'
snapshot_path = inv.BASE / 'remaining_literal_full_counter_v1_snapshots/v3/complete.json'
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
source = next(r for r in inv.cache.read(manifest_path)['rows'] if r['id'] == 'expanded_train:1046282')
assert source['id'] not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']
assert inv.file_sha(ROOT / source['original']['path']) == source['original']['sha256']
raw = (ROOT / source['original']['path']).read_text(encoding='utf-8')
assert len(raw) == 697
snapshot = inv.cache.read(snapshot_path)
saved = []
for shard in snapshot['shards']:
    assert inv.file_sha(ROOT / shard['path']) == shard['sha256']
    saved.extend(r for r in inv.cache.read(ROOT / shard['path']) if r['id'] == source['id'])
assert len(saved) == 1 and saved[0]['decision'] == 'NEEDS_ROOT' and not saved[0].get('body')
review = saved[0]
hold_path = inv.BASE / 'agents/context_hangul/remaining_literal_full_counter_v1/hold_1046282.md'
hold_text = hold_path.read_text(encoding='utf-8')
assert raw.strip() in hold_text
row = dict(id=source['id'], source=source['source'], source_ids=source['source_ids'],
    source_ids_sha256=source['source_ids_sha256'], occurrences=source['occurrences'],
    input_ids=source['input_ids'], original=source['original'], candidate=source['candidate'],
    original_character_range=[0, len(raw)], original_characters=len(raw),
    decision='HOLD', reviewed=True, root_approved=True,
    reason_code='FROZEN_PREVIEW_FORMULA_AND_LOGICAL_CONNECTORS_DAMAGED',
    reason='HLT/VLT 미리보기의 RHS 없는 x=, fy() 표기와 ± 연결자의 관계를 원문만으로 안전하게 복구하지 못했다. 독립 단문도 있지만 이 고정 발췌 전체의 설명 관계를 확정할 근거가 부족하다. 원형 전체를 보존하고 학습 후보에서 분리한다.',
    author_first_review=review['review'], author_reason=review['reason'],
    sidecar=dict(path=str(hold_path.relative_to(ROOT)), sha256=inv.file_sha(hold_path)),
    second_review=dict(reviewer='root', full_original_read=True,
        method='697자 실제 원문 전체와 Luna의 전체 원형 sidecar를 각각 읽고 대조했다.'),
    clean_text_path=None, clean_text_sha256=None, cache_admitted=False,
    status='REVIEWED_TERMINAL_HOLD_FOR_THIS_FROZEN_SOURCE_PENDING_NEW_ROSTER_JOIN',
    raw_source_preserved=True, permanent_recovery_impossible_claim=False,
    all_web_or_original_dumps_exhausted=False)
rows = [*inv.cache.read(prior_path)['rows'], row]
assert len(rows) == len({r['id'] for r in rows}) == 37
result = dict(status='INDIVIDUALLY_REVIEWED_NONADMISSIONS_NOT_UNREAD_SOURCE_RENAMING', rows=rows,
    unique_sources=37, source_positions=sum(r['occurrences'] for r in rows),
    raw_input_ids=sum(r['occurrences'] * r['input_ids'] for r in rows),
    input_pins={str(p.relative_to(ROOT)): inv.file_sha(p) for p in
        [prior_path, manifest_path, snapshot_path, hold_path, Path(__file__)]},
    original_protected_bodies_opened=False, new_roster_joined=False,
    official_verified_cache_hold_positions_unchanged=115526,
    goal_complete=False, training_authorized=False)
inv.write_json(AUDIT / 'ROOT_REVIEWED_TERMINAL_HOLD37_V1.json', result)
print(json.dumps(dict(reviewed_unique=37, positions=result['source_positions'], new_roster_joined=False)))
